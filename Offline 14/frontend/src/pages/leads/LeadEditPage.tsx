import { useTranslation } from "react-i18next"
import { useNavigate, useParams } from "react-router-dom"

import { EmptyState, GlassCard, PageWrapper } from "@/components/common"
import { FormSkeleton } from "@/components/contacts/PageSkeletons"
import { LeadForm } from "@/components/leads/LeadForm"
import { useLead, useUpdateLead } from "@/hooks/useLeads"
import { getErrorMessage } from "@/services/api"
import type { LeadInput } from "@/types"

export default function LeadEditPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const leadId = Number(id)
  const navigate = useNavigate()
  const { data: lead, isLoading, isError, error } = useLead(leadId)
  const updateLead = useUpdateLead(leadId)

  const handleSubmit = (input: LeadInput) => {
    updateLead.mutate(input, {
      onSuccess: () => navigate(`/leads/${leadId}`),
    })
  }

  return (
    <PageWrapper title={t("leads.editTitle")}>
      {isLoading ? (
        <FormSkeleton />
      ) : isError || !lead ? (
        <EmptyState title={t("leads.notFound")} description={getErrorMessage(error)} />
      ) : (
        <GlassCard hoverable={false}>
          <LeadForm
            key={lead.id}
            lead={lead}
            onSubmit={handleSubmit}
            isSubmitting={updateLead.isPending}
            submitLabel={t("common.saveChanges")}
          />
        </GlassCard>
      )}
    </PageWrapper>
  )
}
