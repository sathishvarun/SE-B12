import i18n from "@/i18n"
import { useTranslation } from "react-i18next"
import { Link, useSearchParams } from "react-router-dom"
import { ChevronLeft, ChevronRight, Plus } from "lucide-react"

import { EmptyState, GlassCard, GradientButton, LoadingSpinner, PageWrapper } from "@/components/common"
import { TaskList } from "@/components/tasks/TaskList"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useTaskCounts, useTasks } from "@/hooks/useTasks"
import { getErrorMessage } from "@/services/api"
import type { TaskView } from "@/types"

// Getters, so the tab labels always use the current language.
const VIEWS: { value: TaskView; label: string; empty: string }[] = [
  { value: "today", get label() { return i18n.t("tasks.views.today") }, get empty() { return i18n.t("tasks.empty.today") } },
  { value: "upcoming", get label() { return i18n.t("tasks.views.upcoming") }, get empty() { return i18n.t("tasks.empty.upcoming") } },
  { value: "overdue", get label() { return i18n.t("tasks.views.overdue") }, get empty() { return i18n.t("tasks.empty.overdue") } },
  { value: "done", get label() { return i18n.t("tasks.views.done") }, get empty() { return i18n.t("tasks.empty.done") } },
]

const PAGE_SIZE = 20

function isTaskView(value: string | null): value is TaskView {
  return VIEWS.some((view) => view.value === value)
}

export default function TasksPage() {
  const { t } = useTranslation()
  // Keep the tab and page in the URL so back/refresh keep your place.
  const [searchParams, setSearchParams] = useSearchParams()
  const viewParam = searchParams.get("view")
  const view: TaskView = isTaskView(viewParam) ? viewParam : "today"
  const page = Math.max(1, Number(searchParams.get("page")) || 1)

  const { data, isLoading, isError, error } = useTasks({ view, page, page_size: PAGE_SIZE })
  const counts = useTaskCounts(VIEWS.map((item) => item.value))
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1
  const current = VIEWS.find((item) => item.value === view) ?? VIEWS[0]

  function goTo(nextView: TaskView, nextPage = 1) {
    setSearchParams({ view: nextView, page: String(nextPage) })
  }

  return (
    <PageWrapper
      title={t("nav.tasks")}
      actions={
        <GradientButton asChild>
          <Link to="/tasks/new">
            <Plus /> {t("tasks.new")}
          </Link>
        </GradientButton>
      }
    >
      <Tabs value={view} onValueChange={(value) => isTaskView(value) && goTo(value)}>
        <div className="-mx-4 overflow-x-auto px-4">
          <TabsList>
            {VIEWS.map((item) => (
              <TabsTrigger key={item.value} value={item.value} className="px-3">
                {item.label}
                {counts[item.value] !== undefined && (
                  <span className="rounded-full bg-muted-foreground/15 px-1.5 text-xs tabular-nums">
                    {counts[item.value]}
                  </span>
                )}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
      </Tabs>

      <GlassCard hoverable={false} className="p-4 sm:p-6 dark:border-white/10 dark:bg-card/70">
        {isLoading && <LoadingSpinner className="py-10" />}
        {isError && <EmptyState title={t("tasks.listError")} description={getErrorMessage(error)} />}
        {data && <TaskList key={`${view}-${page}`} tasks={data.items} emptyTitle={current.empty} />}

        {data && totalPages > 1 && (
          <nav aria-label={t("common.pagination")} className="mt-6 flex items-center justify-between gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => goTo(view, page - 1)}>
              <ChevronLeft /> {t("common.previous")}
            </Button>
            <span className="text-sm text-muted-foreground">
              {t("common.pageOf", { page, total: totalPages })}
            </span>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => goTo(view, page + 1)}>
              {t("common.next")} <ChevronRight />
            </Button>
          </nav>
        )}
      </GlassCard>
    </PageWrapper>
  )
}
