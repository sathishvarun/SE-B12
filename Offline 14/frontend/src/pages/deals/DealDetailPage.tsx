import { useTranslation } from "react-i18next"
import type { ReactNode } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { ArrowLeft, Pencil, Plus } from "lucide-react"

import AttachmentsPanel from "@/components/attachments/AttachmentsPanel"
import { EmptyState, GlassCard, LoadingSpinner, PageWrapper } from "@/components/common"
import { ConfirmDeleteButton } from "@/components/deals/ConfirmDeleteButton"
import { STAGE_LABELS, formatDate, formatMoney, isBeforeToday } from "@/components/deals/format"
import { StageBadge } from "@/components/deals/StageBadge"
import { TaskList } from "@/components/tasks/TaskList"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useDeal, useDeleteDeal, useMoveDeal } from "@/hooks/useDeals"
import { getErrorMessage } from "@/services/api"
import { DEAL_STAGES, type DealStage } from "@/types"

const cardClass = "dark:border-white/10 dark:bg-card/70"

function InfoRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</dt>
      <dd className="mt-1 text-sm">{children}</dd>
    </div>
  )
}

export default function DealDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const dealId = Number(id)
  const navigate = useNavigate()
  const { data: deal, isLoading, isError, error, refetch } = useDeal(dealId)
  const { move, isPending: isMoving } = useMoveDeal()
  const deleteDeal = useDeleteDeal()

  if (isLoading) {
    return (
      <PageWrapper title={t("deals.detailTitle")}>
        <LoadingSpinner fullPage />
      </PageWrapper>
    )
  }

  if (isError || !deal) {
    return (
      <PageWrapper title={t("deals.detailTitle")}>
        <EmptyState
          title={t("deals.loadError")}
          description={isError ? getErrorMessage(error) : undefined}
          action={
            <Button variant="outline" asChild>
              <Link to="/deals">{t("deals.backToPipeline")}</Link>
            </Button>
          }
        />
      </PageWrapper>
    )
  }

  const isClosed = deal.stage === "won" || deal.stage === "lost"
  const closeOverdue = !isClosed && isBeforeToday(deal.expected_close_date)

  const actions = (
    <div className="flex flex-wrap gap-2">
      <Button variant="outline" asChild>
        <Link to="/deals">
          <ArrowLeft /> {t("deals.pipeline")}
        </Link>
      </Button>
      <Button variant="outline" asChild>
        <Link to={`/deals/${deal.id}/edit`}>
          <Pencil /> {t("common.edit")}
        </Link>
      </Button>
      <ConfirmDeleteButton
        itemName={t("deals.itemName")}
        isDeleting={deleteDeal.isPending}
        onConfirm={() => deleteDeal.mutate(deal.id, { onSuccess: () => navigate("/deals") })}
      />
    </div>
  )

  return (
    <PageWrapper title={deal.title} actions={actions}>
      <div className="grid gap-6 lg:grid-cols-3">
        <GlassCard hoverable={false} className={`lg:col-span-2 ${cardClass}`}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-3xl font-bold tracking-tight tabular-nums">{formatMoney(deal.value, deal.currency)}</p>
              <div className="mt-2">
                <StageBadge stage={deal.stage} />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="deal-stage-select">{t("deals.moveToStage")}</Label>
              <Select
                value={deal.stage}
                disabled={isMoving}
                onValueChange={(stage) => move(deal.id, stage as DealStage, 0)}
              >
                <SelectTrigger id="deal-stage-select" className="w-44">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DEAL_STAGES.map((stage) => (
                    <SelectItem key={stage} value={stage}>
                      {STAGE_LABELS[stage]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <dl className="mt-6 grid gap-5 sm:grid-cols-2">
            <InfoRow label={t("common.contact")}>
              <Link
                to={`/contacts/${deal.contact.id}`}
                className="font-medium text-violet-700 hover:underline dark:text-violet-300"
              >
                {deal.contact.name}
              </Link>
              {deal.contact.company && <span className="text-muted-foreground"> · {deal.contact.company}</span>}
            </InfoRow>
            <InfoRow label={t("deals.expectedClose")}>
              <span className={closeOverdue ? "font-medium text-rose-600 dark:text-rose-400" : undefined}>
                {formatDate(deal.expected_close_date)}
                {closeOverdue && t("deals.pastDue")}
              </span>
            </InfoRow>
            {deal.closed_at && <InfoRow label={t("deals.closed")}>{formatDate(deal.closed_at)}</InfoRow>}
            <InfoRow label={t("common.created")}>{formatDate(deal.created_at)}</InfoRow>
            <div className="sm:col-span-2">
              <InfoRow label={t("common.notes")}>
                <p className="whitespace-pre-wrap text-muted-foreground">{deal.notes || t("deals.noNotes")}</p>
              </InfoRow>
            </div>
          </dl>
        </GlassCard>

        <GlassCard hoverable={false} className={cardClass}>
          <h2 className="mb-4 font-semibold">{t("deals.attachments")}</h2>
          <AttachmentsPanel dealId={deal.id} attachments={deal.attachments} onChange={() => void refetch()} />
        </GlassCard>

        <GlassCard hoverable={false} className={`lg:col-span-3 ${cardClass}`}>
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="font-semibold">{t("nav.tasks")}</h2>
            <Button variant="outline" size="sm" asChild>
              <Link to={`/tasks/new?deal_id=${deal.id}`}>
                <Plus /> {t("common.addTask")}
              </Link>
            </Button>
          </div>
          <TaskList tasks={deal.tasks} hideLinks emptyTitle={t("deals.noTasksForDeal")} />
        </GlassCard>
      </div>
    </PageWrapper>
  )
}
