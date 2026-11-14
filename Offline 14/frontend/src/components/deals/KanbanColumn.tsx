import { useTranslation } from "react-i18next"
import { useDroppable } from "@dnd-kit/core"
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"

import { cn } from "@/lib/utils"
import type { Deal, DealStage } from "@/types"

import { DealCard } from "./DealCard"
import { STAGE_LABELS, formatMoney, sumValues } from "./format"
import { StageBadge } from "./StageBadge"

function SortableDealCard({ deal }: { deal: Deal }) {
  const { t } = useTranslation()
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: deal.id })

  return (
    <li
      ref={setNodeRef}
      // dnd-kit computes the drag transform every frame; it can only be applied through the style prop.
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "cursor-grab touch-manipulation rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-ring active:cursor-grabbing",
        isDragging && "opacity-40",
      )}
      aria-label={t("deals.cardAria", { title: deal.title })}
      {...attributes}
      {...listeners}
    >
      <DealCard deal={deal} />
    </li>
  )
}

/** Soft background tint per stage column. */
const COLUMN_TINT: Record<DealStage, string> = {
  prospect: "bg-violet-50 border-violet-100",
  proposal: "bg-sky-50 border-sky-100",
  negotiation: "bg-amber-50 border-amber-100",
  won: "bg-emerald-50 border-emerald-100",
  lost: "bg-rose-50 border-rose-100",
}

interface KanbanColumnProps {
  stage: DealStage
  deals: Deal[]
}

export function KanbanColumn({ stage, deals }: KanbanColumnProps) {
  const { t } = useTranslation()
  const { setNodeRef, isOver } = useDroppable({ id: stage })

  return (
    <section
      aria-label={t("deals.columnAria", { stage: STAGE_LABELS[stage] })}
      className={cn(
        "flex w-72 shrink-0 snap-start flex-col rounded-3xl border-2 p-3 xl:w-auto xl:min-w-0 xl:flex-1",
        COLUMN_TINT[stage],
      )}
    >
      <header className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <StageBadge stage={stage} />
          <span className="rounded-full bg-white px-2 text-xs font-bold text-muted-foreground" aria-label={t("deals.dealsInColumn", { count: deals.length })}>
            {deals.length}
          </span>
        </div>
        <span className="text-sm font-extrabold tabular-nums">{formatMoney(sumValues(deals), "INR", true)}</span>
      </header>
      <SortableContext items={deals.map((deal) => deal.id)} strategy={verticalListSortingStrategy}>
        <ul
          ref={setNodeRef}
          className={cn(
            "flex min-h-32 flex-1 flex-col gap-2 rounded-xl p-1 transition-colors",
            isOver && "bg-white/70",
          )}
        >
          {deals.map((deal) => (
            <SortableDealCard key={deal.id} deal={deal} />
          ))}
          {deals.length === 0 && (
            <li className="flex flex-1 items-center justify-center rounded-2xl border-2 border-dashed border-white bg-white/50 p-4 text-xs font-semibold text-muted-foreground">
              {t("deals.dropHere")}
            </li>
          )}
        </ul>
      </SortableContext>
    </section>
  )
}
