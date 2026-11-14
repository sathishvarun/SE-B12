import { LanguageSwitcher } from "@/components/common/LanguageSwitcher"
import { formatLocale } from "@/i18n"
import { useTranslation } from "react-i18next"
import type { ReactNode } from "react"
import { CreditCard, Crown, ShieldCheck, UserRound } from "lucide-react"
import { Link } from "react-router-dom"

import { GlassCard, GradientButton, PageWrapper } from "@/components/common"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAuth } from "@/hooks/useAuth"

function InfoRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 border-b py-3 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{children}</span>
    </div>
  )
}

export default function SettingsPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  if (!user) return null

  const isPro = user.plan === "pro"
  const signInMethod =
    user.oauth_provider === "google"
      ? user.has_password
        ? t("settings.googleAndPassword")
        : t("settings.google")
      : t("settings.emailAndPassword")

  return (
    <PageWrapper title={t("nav.settings")}>
      <Tabs defaultValue="profile" className="gap-4">
        <TabsList>
          <TabsTrigger value="profile">{t("nav.profile")}</TabsTrigger>
          <TabsTrigger value="billing">{t("nav.billing")}</TabsTrigger>
          <TabsTrigger value="account">{t("settings.account")}</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <GlassCard hoverable={false} className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-violet-100 p-2">
                <UserRound className="size-5 text-violet-600" />
              </div>
              <div>
                <h2 className="font-semibold">{t("nav.profile")}</h2>
                <p className="text-sm text-muted-foreground">{t("settings.profileText")}</p>
              </div>
            </div>
            <div>
              <InfoRow label={t("common.name")}>{user.full_name ?? "—"}</InfoRow>
              <InfoRow label={t("common.email")}>{user.email}</InfoRow>
            </div>
            <div>
              <GradientButton asChild>
                <Link to="/profile">{t("settings.editProfile")}</Link>
              </GradientButton>
            </div>
          </GlassCard>
        </TabsContent>

        <TabsContent value="billing">
          <GlassCard hoverable={false} className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-fuchsia-100 p-2">
                {isPro ? <Crown className="size-5 text-fuchsia-600" /> : <CreditCard className="size-5 text-fuchsia-600" />}
              </div>
              <div className="flex-1">
                <h2 className="font-semibold">{t("nav.billing")}</h2>
                <p className="text-sm text-muted-foreground">
                  {isPro ? t("settings.billingPro") : t("settings.billingFree")}
                </p>
              </div>
              <Badge variant={isPro ? "default" : "secondary"}>{isPro ? t("common.pro") : t("common.free")}</Badge>
            </div>
            <div className="flex flex-wrap gap-3">
              {isPro ? (
                <GradientButton asChild>
                  <Link to="/billing">{t("common.manageSubscription")}</Link>
                </GradientButton>
              ) : (
                <GradientButton asChild>
                  <Link to="/billing">{t("common.upgradeToPro")}</Link>
                </GradientButton>
              )}
              <Button variant="outline" asChild>
                <Link to="/pricing">{t("settings.viewPlans")}</Link>
              </Button>
            </div>
          </GlassCard>
        </TabsContent>

        <TabsContent value="account">
          <GlassCard hoverable={false} className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-violet-100 p-2">
                <ShieldCheck className="size-5 text-violet-600" />
              </div>
              <div>
                <h2 className="font-semibold">{t("settings.account")}</h2>
                <p className="text-sm text-muted-foreground">{t("settings.accountText")}</p>
              </div>
            </div>
            <div>
              <InfoRow label={t("settings.signInMethod")}>{signInMethod}</InfoRow>
              <InfoRow label={t("settings.emailVerified")}>{user.is_verified ? t("common.yes") : t("common.no")}</InfoRow>
              <InfoRow label={t("settings.role")}>{user.is_admin ? t("nav.admin") : t("settings.member")}</InfoRow>
              <InfoRow label={t("settings.memberSince")}>
                {new Date(user.created_at).toLocaleDateString(formatLocale(), {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </InfoRow>
              <InfoRow label={t("common.language")}>
                <LanguageSwitcher />
              </InfoRow>
            </div>
          </GlassCard>
        </TabsContent>
      </Tabs>
    </PageWrapper>
  )
}
