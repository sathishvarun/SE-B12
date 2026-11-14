import { useTranslation } from "react-i18next"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { toast } from "sonner"
import { z } from "zod"

import { AuthShell } from "@/components/auth/AuthShell"
import { GradientButton } from "@/components/common"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import i18n from "@/i18n"
import { getErrorMessage } from "@/services/api"
import { authService } from "@/services/auth"

const resetSchema = z
  .object({
    new_password: z.string().min(8, { error: () => i18n.t("validation.passwordMin") }),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    error: () => i18n.t("validation.passwordsMismatch"),
    path: ["confirm_password"],
  })

type ResetValues = z.infer<typeof resetSchema>

export default function ResetPasswordPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get("token")

  const form = useForm<ResetValues>({
    resolver: zodResolver(resetSchema),
    defaultValues: { new_password: "", confirm_password: "" },
  })

  const mutation = useMutation({
    mutationFn: (values: ResetValues) => authService.resetPassword(token ?? "", values.new_password),
    onSuccess: () => {
      toast.success(t("auth.reset.updated"))
      navigate("/login", { replace: true })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const backToLogin = (
    <Link to="/login" className="font-medium text-violet-600 hover:underline">
      {t("common.backToLogin")}
    </Link>
  )

  if (!token) {
    return (
      <AuthShell title={t("auth.reset.invalidTitle")} footer={backToLogin}>
        <p className="text-sm text-muted-foreground">
          {t("auth.reset.invalidText")}
        </p>
        <GradientButton asChild className="h-10 w-full">
          <Link to="/forgot-password">{t("auth.reset.requestNew")}</Link>
        </GradientButton>
      </AuthShell>
    )
  }

  return (
    <AuthShell title={t("auth.reset.title")} subtitle={t("auth.reset.subtitle")} footer={backToLogin}>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          className="flex flex-col gap-4"
          noValidate
        >
          <FormField
            control={form.control}
            name="new_password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("auth.reset.newPassword")}</FormLabel>
                <FormControl>
                  <Input type="password" autoComplete="new-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="confirm_password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("auth.reset.confirmNewPassword")}</FormLabel>
                <FormControl>
                  <Input type="password" autoComplete="new-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <GradientButton type="submit" className="h-10 w-full" disabled={mutation.isPending}>
            {mutation.isPending ? t("common.saving") : t("auth.reset.submit")}
          </GradientButton>
        </form>
      </Form>
    </AuthShell>
  )
}
