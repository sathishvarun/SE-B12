import { useTranslation } from "react-i18next"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import axios from "axios"
import { Sparkles } from "lucide-react"

import { GlassCard, PageWrapper } from "@/components/common"
import { DealForm } from "@/components/deals/DealForm"
import { useCreateDeal } from "@/hooks/useDeals"

export default function DealCreatePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const createDeal = useCreateDeal()
  const hitPlanLimit = axios.isAxiosError(createDeal.error) && createDeal.error.response?.status === 402
  const fromContact = searchParams.get("contact_id")

  return (
    <PageWrapper title={t("deals.newTitle")}>
      {hitPlanLimit && (
        <GlassCard
          hoverable={false}
          role="alert"
          className="flex flex-col gap-3 border-amber-300 bg-amber-50/80 p-5 sm:flex-row sm:items-center sm:justify-between dark:border-amber-800 dark:bg-amber-950/40"
        >
          <div className="flex items-start gap-3">
            <Sparkles className="mt-0.5 size-5 shrink-0 text-amber-600" />
            <p className="text-sm">
              {t("deals.planLimit")}
            </p>
          </div>
          <Link to="/billing" className="text-sm font-semibold text-violet-700 hover:underline dark:text-violet-300">
            {t("deals.upgradePlan")}
          </Link>
        </GlassCard>
      )}
      <GlassCard hoverable={false} className="dark:border-white/10 dark:bg-card/70">
        <DealForm
          submitLabel={t("deals.create")}
          isSubmitting={createDeal.isPending}
          onSubmit={(input) =>
            createDeal.mutate(input, {
              onSuccess: (deal) => navigate(fromContact ? `/contacts/${fromContact}` : `/deals/${deal.id}`),
            })
          }
        />
      </GlassCard>
    </PageWrapper>
  )
}
