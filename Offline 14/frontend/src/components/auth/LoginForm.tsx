import { useTranslation } from "react-i18next"
import axios from "axios"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { z } from "zod"

import { GradientButton } from "@/components/common"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/hooks/useAuth"
import i18n from "@/i18n"
import { getErrorMessage } from "@/services/api"
import type { User } from "@/types"

const loginSchema = z.object({
  email: z.email({ error: () => i18n.t("validation.emailInvalid") }),
  password: z.string().min(1, { error: () => i18n.t("validation.passwordRequired") }),
})

type LoginValues = z.infer<typeof loginSchema>

interface LoginFormProps {
  onSuccess: (user: User) => void
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const { t } = useTranslation()
  const { login } = useAuth()
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  })

  const onSubmit = async (values: LoginValues) => {
    try {
      const user = await login(values)
      toast.success(
        user.full_name ? t("auth.login.welcomeName", { name: user.full_name }) : t("auth.login.welcome"),
      )
      onSuccess(user)
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        toast.error(t("auth.login.invalid"))
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
              <div className="flex items-center justify-between">
                <FormLabel>{t("auth.password")}</FormLabel>
                <Link to="/forgot-password" className="text-xs text-violet-600 hover:underline">
                  {t("auth.login.forgot")}
                </Link>
              </div>
              <FormControl>
                <Input type="password" autoComplete="current-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <GradientButton type="submit" className="h-10 w-full" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? t("auth.login.submitting") : t("auth.login.submit")}
        </GradientButton>
      </form>
    </Form>
  )
}
