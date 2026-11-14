import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { Briefcase, CheckSquare, Sparkles, Target, UserPlus, Users } from "lucide-react"

import { ConversionRateCard } from "@/components/dashboard/ConversionRateCard"
import { DealsWonChart } from "@/components/dashboard/DealsWonChart"
import { LeadsBySourceChart } from "@/components/dashboard/LeadsBySourceChart"
import { PipelineByStageChart } from "@/components/dashboard/PipelineByStageChart"
import { StatCard } from "@/components/dashboard/StatCard"
import { TodayTasksList } from "@/components/dashboard/TodayTasksList"
import { formatMoney } from "@/components/deals/format"
import { EmptyState, GradientButton, PageWrapper } from "@/components/common"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useDashboardAnalytics, useDashboardSummary } from "@/hooks/useDashboard"
import { getErrorMessage } from "@/services/api"

function StatSkeletons() {
  return (
    <>
      {Array.from({ length: 4 }, (_, i) => (
        <Skeleton key={i} className="h-36 rounded-3xl" />
      ))}
    </>
  )
}

export default function DashboardPage() {
  const { t } = useTranslation()
  const summary = useDashboardSummary()
  const analytics = useDashboardAnalytics()
  const s = summary.data

  const isNewUser = s !== undefined && s.contacts === 0 && s.open_leads === 0 && s.open_deals === 0

  return (
    <PageWrapper title={t("nav.dashboard")}>
      {summary.isError && (
        <EmptyState
          title={t("dashboard.loadError")}
          description={getErrorMessage(summary.error)}
          action={
            <Button variant="outline" onClick={() => void summary.refetch()}>
              {t("common.tryAgain")}
            </Button>
          }
        />
      )}

      <section aria-label={t("dashboard.keyNumbers")} className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        {summary.isLoading && <StatSkeletons />}
        {s && (
          <>
            <StatCard label={t("nav.contacts")} value={s.contacts} icon={Users} to="/contacts" tone="mint" />
            <StatCard label={t("dashboard.openLeads")} value={s.open_leads} icon={Target} to="/leads" tone="peach" />
            <StatCard
              label={t("dashboard.openDeals")}
              value={s.open_deals}
              icon={Briefcase}
              to="/deals"
              tone="sky"
              hint={t("dashboard.inPipeline", { value: formatMoney(s.open_pipeline_value) })}
            />
            <StatCard
              label={t("dashboard.tasksDueToday")}
              value={s.tasks_due_today}
              icon={CheckSquare}
              to="/tasks"
              tone="sun"
              hint={
                s.tasks_overdue > 0 ? (
                  <Link to="/tasks?view=overdue" className="font-medium text-rose-600 hover:underline dark:text-rose-400">
                    {t("dashboard.overdueCount", { count: s.tasks_overdue })}
                  </Link>
                ) : (
                  t("dashboard.nothingOverdue")
                )
              }
            />
          </>
        )}
      </section>

      {isNewUser ? (
        <EmptyState
          icon={Sparkles}
          title={t("dashboard.welcomeTitle")}
          description={t("dashboard.welcomeText")}
          action={
            <div className="flex flex-wrap justify-center gap-3">
              <GradientButton asChild>
                <Link to="/contacts/new">
                  <UserPlus /> {t("dashboard.addContact")}
                </Link>
              </GradientButton>
              <Button variant="outline" asChild>
                <Link to="/leads/new">
                  <Target /> {t("dashboard.addLead")}
                </Link>
              </Button>
            </div>
          }
        />
      ) : (
        <>
          {analytics.isLoading && (
            <div className="grid gap-4 lg:grid-cols-2">
              {Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} className="h-80 rounded-3xl" />
              ))}
            </div>
          )}
          {analytics.isError && (
            <p className="text-sm text-destructive">
              {t("dashboard.chartsError", { message: getErrorMessage(analytics.error) })}
            </p>
          )}
          {analytics.data && (
            <div className="grid gap-4 lg:grid-cols-2">
              <PipelineByStageChart data={analytics.data.pipeline_by_stage} />
              <DealsWonChart data={analytics.data.deals_won_by_month} />
              <LeadsBySourceChart data={analytics.data.leads_by_source} />
              <ConversionRateCard rate={analytics.data.lead_conversion_rate} />
            </div>
          )}
          <TodayTasksList />
        </>
      )}
    </PageWrapper>
  )
}
