import { useTranslation } from "react-i18next"
import { useState } from "react"
import { ArrowLeft, Pencil, Plus, Trash2 } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"

import AttachmentsPanel from "@/components/attachments/AttachmentsPanel"
import { EmptyState, GlassCard, GradientButton, PageWrapper } from "@/components/common"
import { ConfirmDialog } from "@/components/contacts/ConfirmDialog"
import { ContactInfoCard } from "@/components/contacts/ContactInfoCard"
import { LinkedDealsList } from "@/components/contacts/LinkedDealsList"
import { LinkedTasksList } from "@/components/contacts/LinkedTasksList"
import { DetailSkeleton } from "@/components/contacts/PageSkeletons"
import { Button } from "@/components/ui/button"
import { useContact, useDeleteContact } from "@/hooks/useContacts"
import { getErrorMessage } from "@/services/api"

export default function ContactDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const contactId = Number(id)
  const navigate = useNavigate()
  const { data: contact, isLoading, isError, error, refetch } = useContact(contactId)
  const deleteContact = useDeleteContact()
  const [confirmOpen, setConfirmOpen] = useState(false)

  const handleDelete = () => {
    deleteContact.mutate(contactId, {
      onSuccess: () => {
        setConfirmOpen(false)
        navigate("/contacts")
      },
    })
  }

  if (isLoading) {
    return (
      <PageWrapper title={t("contacts.detailTitle")}>
        <DetailSkeleton />
      </PageWrapper>
    )
  }

  if (isError || !contact) {
    return (
      <PageWrapper title={t("contacts.detailTitle")}>
        <EmptyState
          title={t("contacts.notFound")}
          description={getErrorMessage(error)}
          action={
            <Button variant="outline" asChild>
              <Link to="/contacts">
                <ArrowLeft /> {t("contacts.backToList")}
              </Link>
            </Button>
          }
        />
      </PageWrapper>
    )
  }

  const actions = (
    <div className="flex flex-wrap gap-2">
      <Button variant="outline" asChild>
        <Link to={`/contacts/${contactId}/edit`}>
          <Pencil /> {t("common.edit")}
        </Link>
      </Button>
      <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
        <Trash2 /> {t("common.delete")}
      </Button>
    </div>
  )

  return (
    <PageWrapper title={contact.name} actions={actions}>
      <Link to="/contacts" className="-mt-4 flex items-center gap-1 text-sm text-muted-foreground hover:underline">
        <ArrowLeft className="size-4" /> {t("contacts.allContacts")}
      </Link>

      <div className="grid gap-6 lg:grid-cols-3">
        <ContactInfoCard contact={contact} />

        <div className="flex flex-col gap-6 lg:col-span-2">
          <GlassCard hoverable={false} className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-semibold">{t("contacts.dealsCount", { count: contact.deals.length })}</h2>
              <GradientButton size="sm" asChild>
                <Link to={`/deals/new?contact_id=${contactId}`}>
                  <Plus /> {t("contacts.addDeal")}
                </Link>
              </GradientButton>
            </div>
            <LinkedDealsList deals={contact.deals} />
          </GlassCard>

          <GlassCard hoverable={false} className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-semibold">{t("contacts.tasksCount", { count: contact.tasks.length })}</h2>
              <Button size="sm" variant="outline" asChild>
                <Link to={`/tasks/new?contact_id=${contactId}`}>
                  <Plus /> {t("common.addTask")}
                </Link>
              </Button>
            </div>
            <LinkedTasksList tasks={contact.tasks} />
          </GlassCard>

          <GlassCard hoverable={false} className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold">{t("contacts.filesCount", { count: contact.attachments.length })}</h2>
            <AttachmentsPanel
              contactId={contactId}
              attachments={contact.attachments}
              onChange={() => void refetch()}
            />
          </GlassCard>
        </div>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("contacts.deleteTitle")}
        description={t("contacts.deleteText", { name: contact.name })}
        isPending={deleteContact.isPending}
        onConfirm={handleDelete}
      />
    </PageWrapper>
  )
}
