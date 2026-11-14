import i18n from "@/i18n"
import { useTranslation } from "react-i18next"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { KeyRound, UserRound } from "lucide-react"
import { toast } from "sonner"
import { z } from "zod"

import { GlassCard, GradientButton, PageWrapper } from "@/components/common"
import { Badge } from "@/components/ui/badge"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/hooks/useAuth"
import { getErrorMessage } from "@/services/api"
import { authService } from "@/services/auth"
import type { UpdateProfileInput, User } from "@/types"

const profileSchema = z.object({
  full_name: z.string().trim().min(1, { error: () => i18n.t("validation.nameRequired") }).max(255),
})

type ProfileValues = z.infer<typeof profileSchema>

const passwordSchema = z
  .object({
    current_password: z.string(),
    new_password: z.string().min(8, { error: () => i18n.t("validation.passwordMin") }),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    error: () => i18n.t("validation.passwordsMismatch"),
    path: ["confirm_password"],
  })

type PasswordValues = z.infer<typeof passwordSchema>

function ProfileForm({ user, onSaved }: { user: User; onSaved: () => Promise<unknown> }) {
  const { t } = useTranslation()
  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: user.full_name ?? "" },
  })

  const mutation = useMutation({
    mutationFn: (values: ProfileValues) => authService.updateMe({ full_name: values.full_name }),
    onSuccess: async (updated) => {
      toast.success(t("profile.updated"))
      form.reset({ full_name: updated.full_name ?? "" })
      await onSaved()
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))} className="flex flex-col gap-4" noValidate>
        <FormField
          control={form.control}
          name="full_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("auth.fullName")}</FormLabel>
              <FormControl>
                <Input autoComplete="name" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="grid gap-2">
          <label htmlFor="profile-email" className="text-sm font-medium">
            {t("common.email")}
          </label>
          <Input id="profile-email" name="email" value={user.email} disabled readOnly />
          <p className="text-xs text-muted-foreground">{t("profile.emailFixed")}</p>
        </div>
        <div>
          <GradientButton type="submit" disabled={mutation.isPending || !form.formState.isDirty}>
            {mutation.isPending ? t("common.saving") : t("common.saveChanges")}
          </GradientButton>
        </div>
      </form>
    </Form>
  )
}

function PasswordForm({ user, onSaved }: { user: User; onSaved: () => Promise<unknown> }) {
  const { t } = useTranslation()
  // Google-only users have no password yet, so they "set" one without the current password.
  const needsCurrent = user.has_password
  const form = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  })

  const mutation = useMutation({
    mutationFn: (values: PasswordValues) => {
      const input: UpdateProfileInput = { new_password: values.new_password }
      if (needsCurrent) input.current_password = values.current_password
      return authService.updateMe(input)
    },
    onSuccess: async () => {
      toast.success(needsCurrent ? t("profile.passwordChanged") : t("profile.passwordSet"))
      form.reset()
      await onSaved()
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const onSubmit = (values: PasswordValues) => {
    if (needsCurrent && !values.current_password) {
      form.setError("current_password", { message: t("validation.currentPasswordRequired") })
      return
    }
    mutation.mutate(values)
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        {needsCurrent && (
          <FormField
            control={form.control}
            name="current_password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("profile.currentPassword")}</FormLabel>
                <FormControl>
                  <Input type="password" autoComplete="current-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        )}
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
        <div>
          <GradientButton type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? t("common.saving") : needsCurrent ? t("profile.changePassword") : t("profile.setPassword")}
          </GradientButton>
        </div>
      </form>
    </Form>
  )
}

export default function ProfilePage() {
  const { t } = useTranslation()
  const { user, refreshUser } = useAuth()

  if (!user) return null

  return (
    <PageWrapper title={t("nav.profile")}>
      <div className="grid gap-6 lg:grid-cols-2">
        <GlassCard hoverable={false} className="flex flex-col gap-5">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-violet-100 p-2">
              <UserRound className="size-5 text-violet-600" />
            </div>
            <div>
              <h2 className="font-semibold">{t("profile.personalDetails")}</h2>
              <p className="text-sm text-muted-foreground">{t("profile.personalText")}</p>
            </div>
          </div>
          <ProfileForm user={user} onSaved={refreshUser} />
        </GlassCard>

        <GlassCard hoverable={false} className="flex flex-col gap-5">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-fuchsia-100 p-2">
              <KeyRound className="size-5 text-fuchsia-600" />
            </div>
            <div className="flex-1">
              <h2 className="font-semibold">{user.has_password ? t("profile.changePassword") : t("profile.setAPassword")}</h2>
              <p className="text-sm text-muted-foreground">
                {user.has_password
                  ? t("profile.useAtLeast8")
                  : t("profile.googleOnly")}
              </p>
            </div>
            {user.oauth_provider === "google" && <Badge variant="secondary">Google</Badge>}
          </div>
          <PasswordForm user={user} onSaved={refreshUser} />
        </GlassCard>
      </div>
    </PageWrapper>
  )
}
