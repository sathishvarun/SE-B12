import { formatLocale } from "@/i18n"
import { useTranslation } from "react-i18next"
import { useQuery } from "@tanstack/react-query"
import { Activity, Briefcase, Contact, Crown, UserPlus, Users, type LucideIcon } from "lucide-react"
import { Link } from "react-router-dom"

import { GlassCard, GradientButton, LoadingSpinner, PageWrapper } from "@/components/common"
import { Button } from "@/components/ui/button"
import { getErrorMessage } from "@/services/api"
import { adminService } from "@/services/admin"
import type { AdminStats } from "@/types"

interface StatDef {
  key: keyof AdminStats
  icon: LucideIcon
}

const STATS: StatDef[] = [
  { key: "total_users", icon: Users },
  { key: "active_users", icon: Activity },
  { key: "pro_subscriptions", icon: Crown },
  { key: "signups_last_30_days", icon: UserPlus },
  { key: "total_contacts", icon: Contact },
  { key: "total_deals", icon: Briefcase },
]

export default function AdminDashboardPage() {
  const { t } = useTranslation()
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["admin", "stats"],
    queryFn: adminService.getStats,
  })

  return (
    <PageWrapper
      title={t("admin.dashboardTitle")}
      actions={
        <GradientButton asChild>
          <Link to="/admin/users">
            <Users className="size-4" /> {t("admin.manageUsers")}
          </Link>
        </GradientButton>
      }
    >
      {isLoading && <LoadingSpinner fullPage label={t("admin.loadingStats")} />}

      {isError && (
        <GlassCard hoverable={false} className="flex flex-col items-start gap-3">
          <p className="text-sm text-destructive">{getErrorMessage(error)}</p>
          <Button variant="outline" onClick={() => refetch()}>
            {t("common.tryAgain")}
          </Button>
        </GlassCard>
      )}

      {data && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STATS.map(({ key, icon: Icon }) => (
            <GlassCard key={key} className="flex items-center gap-4">
              <div className="rounded-2xl bg-rose-100 p-3 text-rose-700">
                <Icon className="size-5" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t(`admin.stats.${key}`)}</p>
                <p className="text-2xl font-bold">{data[key].toLocaleString(formatLocale())}</p>
              </div>
            </GlassCard>
          ))}
        </div>
      )}
    </PageWrapper>
  )
}
