import { useTranslation } from "react-i18next"
import { useState } from "react"
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
  type UniqueIdentifier,
} from "@dnd-kit/core"
import { arrayMove, sortableKeyboardCoordinates } from "@dnd-kit/sortable"

import { DEAL_STAGES, type Deal, type DealBoard, type DealStage } from "@/types"

import { DealCard } from "./DealCard"
import { STAGE_LABELS } from "./format"
import { KanbanColumn } from "./KanbanColumn"

interface KanbanBoardProps {
  board: DealBoard
  /** Called after a drop that changed a deal's stage or position. `nextBoard` is the board after the move. */
  onMove: (dealId: number, stage: DealStage, position: number, nextBoard: DealBoard) => void
}

function isStage(id: UniqueIdentifier): id is DealStage {
  return typeof id === "string" && (DEAL_STAGES as string[]).includes(id)
}

/** Which column holds this deal (or the column itself if `id` is a stage). */
function findStage(board: DealBoard, id: UniqueIdentifier): DealStage | undefined {
  if (isStage(id)) return id
  return DEAL_STAGES.find((stage) => board[stage].some((deal) => deal.id === id))
}

export function KanbanBoard({ board, onMove }: KanbanBoardProps) {
  const { t } = useTranslation()
  // While dragging (and until the parent passes the updated board) we render a local copy.
  const [localBoard, setLocalBoard] = useState<DealBoard | null>(null)
  const [activeDeal, setActiveDeal] = useState<Deal | null>(null)
  const [origin, setOrigin] = useState<{ stage: DealStage; index: number } | null>(null)
  const [prevBoard, setPrevBoard] = useState(board)

  // New board from the server/cache: drop the local copy (unless a drag is in progress).
  if (board !== prevBoard) {
    setPrevBoard(board)
    if (!activeDeal) setLocalBoard(null)
  }

  const current = localBoard ?? board

  const sensors = useSensors(
    // A small distance lets clicks on the title link still work.
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  function handleDragStart({ active }: DragStartEvent) {
    const stage = findStage(board, active.id)
    if (!stage) return
    const index = board[stage].findIndex((deal) => deal.id === active.id)
    setActiveDeal(board[stage][index] ?? null)
    setOrigin({ stage, index })
    setLocalBoard(board)
  }

  // Moving across columns: move the card into the new column as soon as it hovers there.
  function handleDragOver({ active, over }: DragOverEvent) {
    if (!over) return
    const from = findStage(current, active.id)
    const to = findStage(current, over.id)
    if (!from || !to || from === to) return

    const fromDeals = current[from]
    const toDeals = current[to]
    const deal = fromDeals.find((item) => item.id === active.id)
    if (!deal) return

    let newIndex = toDeals.length
    if (!isStage(over.id)) {
      const overIndex = toDeals.findIndex((item) => item.id === over.id)
      const translated = active.rect.current.translated
      const isBelow = translated !== null && translated.top > over.rect.top + over.rect.height / 2
      if (overIndex >= 0) newIndex = overIndex + (isBelow ? 1 : 0)
    }

    setLocalBoard({
      ...current,
      [from]: fromDeals.filter((item) => item.id !== active.id),
      [to]: [...toDeals.slice(0, newIndex), { ...deal, stage: to }, ...toDeals.slice(newIndex)],
    })
  }

  function handleDragEnd({ active, over }: DragEndEvent) {
    const start = origin
    setActiveDeal(null)
    setOrigin(null)

    const stage = findStage(current, active.id)
    if (!over || !stage || !start) {
      setLocalBoard(null)
      return
    }

    // Reordering inside the final column.
    let next = current
    if (findStage(current, over.id) === stage) {
      const deals = current[stage]
      const oldIndex = deals.findIndex((deal) => deal.id === active.id)
      const newIndex = isStage(over.id) ? deals.length - 1 : deals.findIndex((deal) => deal.id === over.id)
      if (newIndex >= 0 && oldIndex !== newIndex) {
        next = { ...current, [stage]: arrayMove(deals, oldIndex, newIndex) }
      }
    }

    const position = next[stage].findIndex((deal) => deal.id === active.id)
    if (stage === start.stage && position === start.index) {
      setLocalBoard(null)
      return
    }
    setLocalBoard(next)
    onMove(Number(active.id), stage, position, next)
  }

  function handleDragCancel() {
    setActiveDeal(null)
    setOrigin(null)
    setLocalBoard(null)
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
      accessibility={{
        screenReaderInstructions: {
          draggable: t("deals.dnd.instructions"),
        },
        announcements: {
          onDragStart: ({ active }) => t("deals.dnd.pickedUp", { id: String(active.id) }),
          onDragOver: ({ over }) =>
            over
              ? t("deals.dnd.over", { stage: STAGE_LABELS[findStage(current, over.id) ?? "prospect"] })
              : t("deals.dnd.notOver"),
          onDragEnd: ({ over }) =>
            over
              ? t("deals.dnd.droppedIn", { stage: STAGE_LABELS[findStage(current, over.id) ?? "prospect"] })
              : t("deals.dnd.dropped"),
          onDragCancel: () => t("deals.dnd.cancelled"),
        },
      }}
    >
      <div className="-mx-4 flex snap-x gap-4 overflow-x-auto px-4 pb-4 xl:mx-0 xl:px-0">
        {DEAL_STAGES.map((stage) => (
          <KanbanColumn key={stage} stage={stage} deals={current[stage] ?? []} />
        ))}
      </div>
      <DragOverlay>{activeDeal ? <DealCard deal={activeDeal} dragging /> : null}</DragOverlay>
    </DndContext>
  )
}
