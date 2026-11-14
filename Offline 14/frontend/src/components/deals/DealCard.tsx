import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { CalendarClock, User } from "lucide-react"

import { cn } from "@/lib/utils"
import type { Deal } from "@/types"

import { formatDate, formatMoney, isBeforeToday } from "./format"

interface DealCardProps {
  deal: Deal
  /** Visual state while the card is being dragged (or shown in the drag overlay). */
  dragging?: boolean
  className?: string
}

/** Compact card shown in a Kanban column. */
export function DealCard({ deal, dragging = false, className }: DealCardProps) {
  const { t } = useTranslation()
  const isClosed = deal.stage === "won" || deal.stage === "lost"
  const closeOverdue = !isClosed && isBeforeToday(deal.expected_close_date)

  return (
    <div
      className={cn(
        "rounded-2xl border border-white bg-card p-3.5 text-card-foreground shadow-[0_2px_8px_-2px_oklch(0.55_0.21_292/0.15)] transition-shadow hover:shadow-[0_6px_16px_-4px_oklch(0.55_0.21_292/0.25)]",
        closeOverdue && "border-rose-300 dark:border-rose-800",
        dragging && "shadow-xl ring-2 ring-violet-400",
        className,
      )}
    >
      <Link
        to={`/deals/${deal.id}`}
        className="line-clamp-2 font-bold hover:text-violet-700 hover:underline"
      >
        {deal.title}
      </Link>
      <p className="mt-1 flex items-center gap-1 truncate text-xs text-muted-foreground">
        <User className="size-3 shrink-0" />
        {deal.contact.name}
      </p>
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="text-sm font-semibold tabular-nums">{formatMoney(deal.value, deal.currency)}</span>
        {deal.expected_close_date && (
          <span
            className={cn(
              "flex items-center gap-1 text-xs",
              closeOverdue ? "font-medium text-rose-600 dark:text-rose-400" : "text-muted-foreground",
            )}
            title={closeOverdue ? t("deals.closeDatePassed") : t("common.expectedCloseDate")}
          >
            <CalendarClock className="size-3" />
            {formatDate(deal.expected_close_date)}
          </span>
        )}
      </div>
    </div>
  )
}
