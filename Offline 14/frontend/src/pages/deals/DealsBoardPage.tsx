import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { Briefcase, Plus } from "lucide-react"

import { EmptyState, GradientButton, LoadingSpinner, PageWrapper } from "@/components/common"
import { KanbanBoard } from "@/components/deals/KanbanBoard"
import { formatMoney, sumValues } from "@/components/deals/format"
import { Button } from "@/components/ui/button"
import { useDealBoard, useMoveDeal } from "@/hooks/useDeals"
import { getErrorMessage } from "@/services/api"
import { DEAL_STAGES } from "@/types"

export default function DealsBoardPage() {
  const { t } = useTranslation()
  const { data: board, isLoading, isError, error, refetch } = useDealBoard()
  const { move } = useMoveDeal()

  const allDeals = board ? DEAL_STAGES.flatMap((stage) => board[stage]) : []
  const openDeals = board ? [...board.prospect, ...board.proposal, ...board.negotiation] : []

  const newDealButton = (
    <GradientButton asChild>
      <Link to="/deals/new">
        <Plus /> {t("deals.new")}
      </Link>
    </GradientButton>
  )

  return (
    <PageWrapper title={t("deals.boardTitle")} actions={newDealButton}>
      {isLoading && <LoadingSpinner fullPage label={t("deals.loadingPipeline")} />}

      {isError && (
        <EmptyState
          title={t("deals.loadDealsError")}
          description={getErrorMessage(error)}
          action={
            <Button variant="outline" onClick={() => void refetch()}>
              {t("common.tryAgain")}
            </Button>
          }
        />
      )}

      {board && allDeals.length === 0 && (
        <EmptyState
          icon={Briefcase}
          title={t("deals.emptyTitle")}
          description={t("deals.emptyText")}
          action={newDealButton}
        />
      )}

      {board && allDeals.length > 0 && (
        <>
          <p className="text-sm text-muted-foreground">
            {t("deals.openSummary", { count: openDeals.length })}{" "}
            <span className="font-semibold text-foreground">{formatMoney(sumValues(openDeals))}</span>
            {t("deals.dragHint")}
          </p>
          <KanbanBoard board={board} onMove={move} />
        </>
      )}
    </PageWrapper>
  )
}
