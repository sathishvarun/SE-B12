import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { LoadingSpinner } from "@/components/common"
import { TaskList } from "@/components/tasks/TaskList"
import { useTasks } from "@/hooks/useTasks"

import { ChartCard } from "./ChartCard"

/** Tasks due today (first 5) with a link to the full list. */
export function TodayTasksList() {
  const { t } = useTranslation()
  const { data, isLoading, isError } = useTasks({ view: "today", page: 1, page_size: 5 })

  return (
    <ChartCard
      title={t("dashboard.dueToday")}
      description={data ? t("dashboard.taskCount", { count: data.total }) : undefined}
    >
      {isLoading && <LoadingSpinner className="py-6" />}
      {isError && <p className="text-sm text-destructive">{t("dashboard.todayError")}</p>}
      {data && (
        <TaskList tasks={data.items} emptyTitle={t("dashboard.nothingDueToday")} emptyDescription={t("dashboard.enjoyCalm")} />
      )}
      <Link to="/tasks" className="mt-4 inline-block text-sm font-bold text-amber-700 hover:underline">
        {t("dashboard.viewAllTasks")}
      </Link>
    </ChartCard>
  )
}
