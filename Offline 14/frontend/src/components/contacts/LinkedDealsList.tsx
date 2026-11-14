import { STAGE_LABELS } from "@/components/deals/format"
import { useTranslation } from "react-i18next"
import { Briefcase } from "lucide-react"
import { Link } from "react-router-dom"

import { AnimatedList } from "@/components/common"
import { cn } from "@/lib/utils"
import type { DealSummary } from "@/types"

import { DEAL_STAGE_CLASSES, formatDate, formatMoney } from "./utils"

export function LinkedDealsList({ deals }: { deals: DealSummary[] }) {
  const { t } = useTranslation()
  if (deals.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("contacts.noDeals")}</p>
  }

  return (
    <AnimatedList className="gap-2">
      {deals.map((deal) => (
        <Link
          key={deal.id}
          to={`/deals/${deal.id}`}
          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border bg-white/60 p-3 transition-colors hover:bg-violet-50"
        >
          <div className="flex min-w-0 items-center gap-2">
            <Briefcase className="size-4 shrink-0 text-muted-foreground" />
            <span className="truncate font-medium">{deal.title}</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            {deal.expected_close_date && (
              <span className="text-muted-foreground">
                {t("contacts.closeDate", { date: formatDate(deal.expected_close_date) })}
              </span>
            )}
            <span className="font-semibold">{formatMoney(deal.value, deal.currency)}</span>
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-medium",
                DEAL_STAGE_CLASSES[deal.stage],
              )}
            >
              {STAGE_LABELS[deal.stage]}
            </span>
          </div>
        </Link>
      ))}
    </AnimatedList>
  )
}
