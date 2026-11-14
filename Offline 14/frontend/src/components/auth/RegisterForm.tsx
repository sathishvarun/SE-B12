import { useTranslation } from "react-i18next"
import axios from "axios"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { toast } from "sonner"
import { z } from "zod"

import { GradientButton } from "@/components/common"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/hooks/useAuth"
import i18n from "@/i18n"
import { getErrorMessage } from "@/services/api"
import type { User } from "@/types"

const registerSchema = z
  .object({
    full_name: z.string().trim().min(1, { error: () => i18n.t("validation.nameRequired") }).max(255),
    email: z.email({ error: () => i18n.t("validation.emailInvalid") }),
    password: z.string().min(8, { error: () => i18n.t("validation.passwordMin") }),
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    error: () => i18n.t("validation.passwordsMismatch"),
    path: ["confirm_password"],
  })

type RegisterValues = z.infer<typeof registerSchema>

interface RegisterFormProps {
  onSuccess: (user: User) => void
}

export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const { t } = useTranslation()
  const { register } = useAuth()
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: "", email: "", password: "", confirm_password: "" },
  })

  const onSubmit = async ({ full_name, email, password }: RegisterValues) => {
    try {
      const user = await register({ full_name, email, password })
      toast.success(t("auth.register.created"))
      onSuccess(user)
    } catch (err) {
      // 409 = this email already has an account: say so next to the email field.
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        form.setError("email", { message: t("auth.register.emailTaken") }, { shouldFocus: true })
        return
      }
      toast.error(getErrorMessage(err))
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField
          control={form.control}
          name="full_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("auth.fullName")}</FormLabel>
              <FormControl>
                <Input autoComplete="name" placeholder={t("auth.namePlaceholder")} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
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
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("auth.password")}</FormLabel>
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
              <FormLabel>{t("auth.register.confirmPassword")}</FormLabel>
              <FormControl>
                <Input type="password" autoComplete="new-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <GradientButton type="submit" className="h-10 w-full" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? t("auth.register.submitting") : t("auth.register.submit")}
        </GradientButton>
      </form>
    </Form>
  )
}
