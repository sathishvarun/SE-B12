import { useTranslation } from "react-i18next"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { MailCheck } from "lucide-react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { z } from "zod"

import { AuthShell } from "@/components/auth/AuthShell"
import { GradientButton } from "@/components/common"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import i18n from "@/i18n"
import { getErrorMessage } from "@/services/api"
import { authService } from "@/services/auth"

const forgotSchema = z.object({
  email: z.email({ error: () => i18n.t("validation.emailInvalid") }),
})

type ForgotValues = z.infer<typeof forgotSchema>

export default function ForgotPasswordPage() {
  const { t } = useTranslation()
  const [sentMessage, setSentMessage] = useState<string | null>(null)
  const form = useForm<ForgotValues>({
    resolver: zodResolver(forgotSchema),
    defaultValues: { email: "" },
  })

  const mutation = useMutation({
    mutationFn: (values: ForgotValues) => authService.forgotPassword(values.email),
    onSuccess: (data) => setSentMessage(data.message),
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <AuthShell
      title={t("auth.forgot.title")}
      subtitle={t("auth.forgot.subtitle")}
      footer={
        <Link to="/login" className="font-medium text-violet-600 hover:underline">
          {t("common.backToLogin")}
        </Link>
      }
    >
      {sentMessage ? (
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="rounded-full bg-violet-100 p-3">
            <MailCheck className="size-6 text-violet-600" />
          </div>
          <p className="text-sm">{sentMessage}</p>
          <p className="text-xs text-muted-foreground">{t("auth.forgot.expires")}</p>
        </div>
      ) : (
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
            className="flex flex-col gap-4"
            noValidate
          >
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("common.email")}</FormLabel>
                  <FormControl>
                    <Input type="email" autoComplete="email" placeholder="you@example.com" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <GradientButton type="submit" className="h-10 w-full" disabled={mutation.isPending}>
              {mutation.isPending ? t("auth.forgot.submitting") : t("auth.forgot.submit")}
            </GradientButton>
          </form>
        </Form>
      )}
    </AuthShell>
  )
}
