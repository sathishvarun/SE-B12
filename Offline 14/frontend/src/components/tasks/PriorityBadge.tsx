import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import { PRIORITY_LABELS } from "@/components/deals/format"
import { cn } from "@/lib/utils"
import type { TaskPriority } from "@/types"

const PRIORITY_CLASSES: Record<TaskPriority, string> = {
  low: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  high: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200",
}

export function PriorityBadge({ priority, className }: { priority: TaskPriority; className?: string }) {
  useTranslation() // re-render when the language changes
  return <Badge className={cn(PRIORITY_CLASSES[priority], className)}>{PRIORITY_LABELS[priority]}</Badge>
}
