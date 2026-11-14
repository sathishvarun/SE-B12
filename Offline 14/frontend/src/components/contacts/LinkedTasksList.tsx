import { useTranslation } from "react-i18next"
import { CheckCircle2, Circle } from "lucide-react"
import { Link } from "react-router-dom"

import { AnimatedList } from "@/components/common"
import { cn } from "@/lib/utils"
import type { Task } from "@/types"

import { formatDate } from "./utils"

export function LinkedTasksList({ tasks }: { tasks: Task[] }) {
  const { t } = useTranslation()
  if (tasks.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("contacts.noTasks")}</p>
  }

  return (
    <AnimatedList className="gap-2">
      {tasks.map((task) => {
        const done = task.status === "done"
        return (
          <Link
            key={task.id}
            to={`/tasks/${task.id}/edit`}
            className={cn(
              "flex flex-wrap items-center justify-between gap-2 rounded-xl border bg-white/60 p-3 transition-colors hover:bg-violet-50",
              task.is_overdue && !done && "border-rose-300 bg-rose-50/70",
            )}
          >
            <div className="flex min-w-0 items-center gap-2">
              {done ? (
                <CheckCircle2 className="size-4 shrink-0 text-emerald-600" />
              ) : (
                <Circle className="size-4 shrink-0 text-muted-foreground" />
              )}
              <span className={cn("truncate font-medium", done && "text-muted-foreground line-through")}>
                {task.title}
              </span>
            </div>
            <span
              className={cn(
                "text-sm",
                task.is_overdue && !done ? "font-semibold text-rose-600" : "text-muted-foreground",
              )}
            >
              {task.due_date ? t("contacts.due", { date: formatDate(task.due_date) }) : t("common.noDueDate")}
              {task.is_overdue && !done && t("contacts.overdueSuffix")}
            </span>
          </Link>
        )
      })}
    </AnimatedList>
  )
}
