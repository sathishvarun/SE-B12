import { useTranslation } from "react-i18next"
import { useNavigate, useParams } from "react-router-dom"

import { EmptyState, GlassCard, LoadingSpinner, PageWrapper } from "@/components/common"
import { DealForm } from "@/components/deals/DealForm"
import { useDeal, useUpdateDeal } from "@/hooks/useDeals"
import { getErrorMessage } from "@/services/api"

export default function DealEditPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const dealId = Number(id)
  const navigate = useNavigate()
  const { data: deal, isLoading, isError, error } = useDeal(dealId)
  const updateDeal = useUpdateDeal(dealId)

  return (
    <PageWrapper title={t("deals.editTitle")}>
      {isLoading && <LoadingSpinner fullPage />}
      {isError && <EmptyState title={t("deals.loadError")} description={getErrorMessage(error)} />}
      {deal && (
        <GlassCard hoverable={false} className="dark:border-white/10 dark:bg-card/70">
          <DealForm
            deal={deal}
            submitLabel={t("common.saveChanges")}
            isSubmitting={updateDeal.isPending}
            onSubmit={(input) => updateDeal.mutate(input, { onSuccess: () => navigate(`/deals/${dealId}`) })}
          />
        </GlassCard>
      )}
    </PageWrapper>
  )
}
