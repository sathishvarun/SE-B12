import { useTranslation } from "react-i18next"
import type { ReactNode } from "react"
import { Link } from "react-router-dom"

import { GlassCard, MeshBackground, PageWrapper } from "@/components/common"
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher"

interface AuthShellProps {
  title: string
  subtitle?: string
  children: ReactNode
  /** Small text under the card, e.g. "No account? Sign up". */
  footer?: ReactNode
}

/** Centered glass card on the mesh background, shared by all auth pages. */
export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <MeshBackground />
      <PageWrapper className="w-full max-w-md">
        <div className="flex flex-col items-center gap-2 text-center">
          <Link to="/" className="flex flex-col items-center gap-2 rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <div className="flex size-12 rotate-[-6deg] items-center justify-center rounded-2xl bg-primary text-xl font-black text-primary-foreground shadow-[0_3px_0_0_oklch(0.42_0.2_292)]">
              S
            </div>
            <span className="text-2xl font-black tracking-tight">Sathish CRM</span>
          </Link>
          <p className="flex flex-wrap justify-center gap-1.5 text-xs font-bold" aria-label={t("auth.tagsAria")}>
            <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-emerald-700">{t("nav.contacts")}</span>
            <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-orange-700">{t("nav.leads")}</span>
            <span className="rounded-full bg-sky-100 px-2.5 py-0.5 text-sky-700">{t("nav.deals")}</span>
            <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-amber-700">{t("auth.followUps")}</span>
          </p>
        </div>
        <GlassCard hoverable={false} className="flex flex-col gap-5">
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-black tracking-tight">{title}</h1>
            {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
          </div>
          {children}
        </GlassCard>
        {footer && <div className="text-center text-sm text-muted-foreground">{footer}</div>}
        <div className="flex justify-center">
          <LanguageSwitcher />
        </div>
      </PageWrapper>
    </div>
  )
}

/** "or" divider between the email form and the Google button. */
export function OrDivider() {
  const { t } = useTranslation()
  return (
    <div className="flex items-center gap-3 text-xs text-muted-foreground uppercase">
      <span className="h-px flex-1 bg-border" />
      {t("common.or")}
      <span className="h-px flex-1 bg-border" />
    </div>
  )
}
