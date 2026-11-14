import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"
import type { LeadStatus } from "@/types"

import { LEAD_STATUS_LABELS } from "./constants"

const STATUS_CLASSES: Record<LeadStatus, string> = {
  new: "bg-sky-100 text-sky-700",
  contacted: "bg-amber-100 text-amber-700",
  qualified: "bg-violet-100 text-violet-700",
  lost: "bg-rose-100 text-rose-700",
  converted: "bg-emerald-100 text-emerald-700",
}

export function LeadStatusBadge({ status, className }: { status: LeadStatus; className?: string }) {
  useTranslation() // re-render when the language changes
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        STATUS_CLASSES[status],
        className,
      )}
    >
      {LEAD_STATUS_LABELS[status]}
    </span>
  )
}
