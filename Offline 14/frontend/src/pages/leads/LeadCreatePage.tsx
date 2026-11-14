import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"

import { GlassCard, PageWrapper } from "@/components/common"
import { LeadForm } from "@/components/leads/LeadForm"
import { useCreateLead } from "@/hooks/useLeads"
import type { LeadInput } from "@/types"

export default function LeadCreatePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const createLead = useCreateLead()

  const handleSubmit = (input: LeadInput) => {
    createLead.mutate(input, {
      onSuccess: (lead) => navigate(`/leads/${lead.id}`),
    })
  }

  return (
    <PageWrapper title={t("leads.newTitle")}>
      <GlassCard hoverable={false}>
        <LeadForm onSubmit={handleSubmit} isSubmitting={createLead.isPending} submitLabel={t("leads.create")} />
      </GlassCard>
    </PageWrapper>
  )
}
