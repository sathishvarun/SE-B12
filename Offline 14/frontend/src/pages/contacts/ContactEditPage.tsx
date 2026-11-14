import { useTranslation } from "react-i18next"
import { useNavigate, useParams } from "react-router-dom"

import { EmptyState, GlassCard, PageWrapper } from "@/components/common"
import { ContactForm } from "@/components/contacts/ContactForm"
import { FormSkeleton } from "@/components/contacts/PageSkeletons"
import { useContact, useUpdateContact } from "@/hooks/useContacts"
import { getErrorMessage } from "@/services/api"
import type { ContactInput } from "@/types"

export default function ContactEditPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const contactId = Number(id)
  const navigate = useNavigate()
  const { data: contact, isLoading, isError, error } = useContact(contactId)
  const updateContact = useUpdateContact(contactId)

  const handleSubmit = (input: ContactInput) => {
    updateContact.mutate(input, {
      onSuccess: () => navigate(`/contacts/${contactId}`),
    })
  }

  return (
    <PageWrapper title={t("contacts.editTitle")}>
      {isLoading ? (
        <FormSkeleton />
      ) : isError || !contact ? (
        <EmptyState title={t("contacts.notFound")} description={getErrorMessage(error)} />
      ) : (
        <GlassCard hoverable={false}>
          {/* key resets the form if a different contact loads */}
          <ContactForm
            key={contact.id}
            contact={contact}
            onSubmit={handleSubmit}
            isSubmitting={updateContact.isPending}
            submitLabel={t("common.saveChanges")}
          />
        </GlassCard>
      )}
    </PageWrapper>
  )
}
