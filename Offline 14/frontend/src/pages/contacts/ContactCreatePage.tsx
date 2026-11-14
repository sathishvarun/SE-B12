import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"

import { GlassCard, PageWrapper } from "@/components/common"
import { ContactForm } from "@/components/contacts/ContactForm"
import { PlanLimitNotice } from "@/components/contacts/PlanLimitNotice"
import { isPlanLimitError } from "@/components/contacts/utils"
import { useCreateContact } from "@/hooks/useContacts"
import { getErrorMessage } from "@/services/api"
import type { ContactInput } from "@/types"

export default function ContactCreatePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const createContact = useCreateContact()

  const handleSubmit = (input: ContactInput) => {
    createContact.mutate(input, {
      onSuccess: (contact) => navigate(`/contacts/${contact.id}`),
    })
  }

  return (
    <PageWrapper title={t("contacts.newTitle")}>
      {isPlanLimitError(createContact.error) && (
        <PlanLimitNotice message={getErrorMessage(createContact.error)} />
      )}
      <GlassCard hoverable={false}>
        <ContactForm onSubmit={handleSubmit} isSubmitting={createContact.isPending} submitLabel={t("contacts.create")} />
      </GlassCard>
    </PageWrapper>
  )
}
