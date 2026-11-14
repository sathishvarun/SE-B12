import i18n from "@/i18n"
import { useTranslation } from "react-i18next"
import { Check, Crown, Rocket } from "lucide-react"
import { Link } from "react-router-dom"

import { GlassCard, GradientButton, MeshBackground, PageWrapper } from "@/components/common"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/useAuth"
import { cn } from "@/lib/utils"

interface PlanInfo {
  id: "free" | "pro"
  name: string
  tagline: string
  icon: typeof Rocket
  features: string[]
  highlighted: boolean
}

/** Plan cards, built on each render so the text follows the current language. */
function getPlans(): PlanInfo[] {
  const shared = [
    i18n.t("pricing.leadsPipeline"),
    i18n.t("pricing.tasksReminders"),
    i18n.t("pricing.files"),
    i18n.t("pricing.analytics"),
  ]
  return [
    {
      id: "free",
      name: i18n.t("common.free"),
      tagline: i18n.t("pricing.freeTagline"),
      icon: Rocket,
      features: [i18n.t("pricing.upTo100Contacts"), i18n.t("pricing.upTo20Deals"), ...shared],
      highlighted: false,
    },
    {
      id: "pro",
      name: i18n.t("common.pro"),
      tagline: i18n.t("pricing.proTagline"),
      icon: Crown,
      features: [i18n.t("billing.perkContacts"), i18n.t("billing.perkDeals"), ...shared],
      highlighted: true,
    },
  ]
}


export default function PricingPage() {
  const { t } = useTranslation()
  const { user } = useAuth()

  const ctaFor = (plan: PlanInfo): { label: string; to: string } => {
    if (!user) {
      return { label: plan.highlighted ? t("pricing.startFreeUpgrade") : t("pricing.getStartedFree"), to: "/register" }
    }
    if (plan.highlighted) {
      return { label: user.plan === "pro" ? t("common.manageSubscription") : t("common.upgradeToPro"), to: "/billing" }
    }
    return { label: t("pricing.goToDashboard"), to: "/dashboard" }
  }

  return (
    <div className="min-h-screen">
      <MeshBackground />
      <header className="mx-auto flex max-w-5xl items-center justify-between gap-4 p-4">
        <Link to="/" className="flex items-center gap-2">
          <div className="flex size-9 rotate-[-6deg] items-center justify-center rounded-2xl bg-primary font-black text-primary-foreground">
            S
          </div>
          <span className="font-bold tracking-tight">Sathish CRM</span>
        </Link>
        <div className="flex items-center gap-2">
          {user ? (
            <Button variant="ghost" asChild>
              <Link to="/dashboard">{t("nav.dashboard")}</Link>
            </Button>
          ) : (
            <>
              <Button variant="ghost" asChild>
                <Link to="/login">{t("auth.login.submit")}</Link>
              </Button>
              <GradientButton asChild>
                <Link to="/register">{t("auth.login.signUp")}</Link>
              </GradientButton>
            </>
          )}
        </div>
      </header>

      <PageWrapper className="mx-auto max-w-5xl items-center px-4 py-10 text-center">
        <div className="flex flex-col gap-3">
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            {t("pricing.headlineStart")}{" "}
            <span className="bg-gradient-to-r from-violet-500 via-pink-500 to-orange-400 bg-clip-text text-transparent">
              {t("pricing.headlineHighlight")}
            </span>
          </h1>
          <p className="text-muted-foreground">{t("pricing.subtitle")}</p>
        </div>

        <div className="grid w-full gap-6 text-left md:grid-cols-2">
          {getPlans().map((plan) => {
            const cta = ctaFor(plan)
            const Icon = plan.icon
            const isCurrent = user?.plan === plan.id
            return (
              <GlassCard
                key={plan.id}
                className={cn("flex flex-col gap-5", plan.highlighted && "border-violet-300 ring-2 ring-violet-500/30")}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "rounded-xl p-3",
                        plan.highlighted
                          ? "bg-gradient-to-br from-violet-500 to-pink-500 text-white"
                          : "bg-violet-100 text-violet-600",
                      )}
                    >
                      <Icon className="size-6" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold">{plan.name}</h2>
                      <p className="text-sm text-muted-foreground">{plan.tagline}</p>
                    </div>
                  </div>
                  {isCurrent ? (
                    <Badge variant="secondary">{t("billing.currentPlan")}</Badge>
                  ) : (
                    plan.highlighted && <Badge>{t("pricing.mostPopular")}</Badge>
                  )}
                </div>
                <p className="text-3xl font-extrabold">
                  {plan.highlighted ? t("pricing.monthly") : "₹0"}
                  <span className="ml-1 text-sm font-normal text-muted-foreground">
                    {plan.highlighted ? t("pricing.billedVia") : t("pricing.forever")}
                  </span>
                </p>
                <ul className="flex flex-1 flex-col gap-2">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-sm">
                      <Check className="size-4 shrink-0 text-violet-600" />
                      {feature}
                    </li>
                  ))}
                </ul>
                {plan.highlighted ? (
                  <GradientButton asChild className="h-10 w-full">
                    <Link to={cta.to}>{cta.label}</Link>
                  </GradientButton>
                ) : (
                  <Button variant="outline" asChild className="h-10 w-full">
                    <Link to={cta.to}>{cta.label}</Link>
                  </Button>
                )}
              </GlassCard>
            )
          })}
        </div>
      </PageWrapper>
    </div>
  )
}
