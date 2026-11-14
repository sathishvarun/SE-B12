import { useTranslation } from "react-i18next"
import { Link, useLocation } from "react-router-dom"
import { CalendarDays, Link2 } from "lucide-react"

import { formatDate, isBeforeToday } from "@/components/deals/format"
import { Checkbox } from "@/components/ui/checkbox"
import { useCompleteTask } from "@/hooks/useTasks"
import { cn } from "@/lib/utils"
import type { Task } from "@/types"

import { PriorityBadge } from "./PriorityBadge"

const LINK_PATHS = { contact: "/contacts", lead: "/leads", deal: "/deals" } as const

function linkedRecordPath(task: Task): string | null {
  if (task.linked_type === "contact" && task.contact_id) return `${LINK_PATHS.contact}/${task.contact_id}`
  if (task.linked_type === "lead" && task.lead_id) return `${LINK_PATHS.lead}/${task.lead_id}`
  if (task.linked_type === "deal" && task.deal_id) return `${LINK_PATHS.deal}/${task.deal_id}`
  return null
}

interface TaskItemProps {
  task: Task
  /** Hide the linked-record link (e.g. when already on that record's page). */
  hideLink?: boolean
}

export function TaskItem({ task, hideLink = false }: TaskItemProps) {
  const { t } = useTranslation()
  const location = useLocation()
  const complete = useCompleteTask()
  const done = task.status === "done"
  const overdue = !done && (task.is_overdue || isBeforeToday(task.due_date))
  const linkPath = linkedRecordPath(task)
  const editPath = `/tasks/${task.id}/edit?returnTo=${encodeURIComponent(location.pathname + location.search)}`

  return (
    <div className="flex items-start gap-3 rounded-xl border bg-card p-3 text-card-foreground shadow-sm transition-shadow hover:shadow-md">
      <Checkbox
        className="mt-1"
        checked={done}
        disabled={done || complete.isPending}
        onCheckedChange={(checked) => {
          if (checked === true) complete.mutate(task.id)
        }}
        aria-label={done ? t("tasks.isDone", { title: task.title }) : t("tasks.markDone", { title: task.title })}
      />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to={editPath}
            className={cn(
              "font-medium hover:text-violet-600 hover:underline dark:hover:text-violet-400",
              done && "text-muted-foreground line-through",
            )}
          >
            {task.title}
          </Link>
          <PriorityBadge priority={task.priority} />
        </div>
        {task.description && <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{task.description}</p>}
        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span className={cn("flex items-center gap-1", overdue && "font-medium text-rose-600 dark:text-rose-400")}>
            <CalendarDays className="size-3" />
            {task.due_date ? formatDate(task.due_date) : t("common.noDueDate")}
            {overdue && t("tasks.overdueSuffix")}
          </span>
          {!hideLink && linkPath && task.linked_type && (
            <Link to={linkPath} className="flex items-center gap-1 hover:text-foreground hover:underline">
              <Link2 className="size-3" />
              <span>{t(`tasks.linkType.${task.linked_type}`)}:</span> {task.linked_name ?? t("common.view")}
            </Link>
          )}
          {done && task.completed_at && <span>{t("tasks.doneOn", { date: formatDate(task.completed_at) })}</span>}
        </div>
      </div>
    </div>
  )
}
