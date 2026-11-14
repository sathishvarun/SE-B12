import { useTranslation } from "react-i18next"
import { useState, type ReactNode } from "react"
import { ArrowLeft, ArrowRightLeft, Building2, Calendar, Mail, Pencil, Phone, Plus, Trash2, UserCheck } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"

import { EmptyState, GlassCard, GradientButton, PageWrapper } from "@/components/common"
import { ConfirmDialog } from "@/components/contacts/ConfirmDialog"
import { DetailSkeleton } from "@/components/contacts/PageSkeletons"
import { formatDate } from "@/components/contacts/utils"
import { ConvertLeadDialog } from "@/components/leads/ConvertLeadDialog"
import { LEAD_SOURCE_LABELS } from "@/components/leads/constants"
import { LeadStatusBadge } from "@/components/leads/LeadStatusBadge"
import { LeadStatusSelect } from "@/components/leads/LeadStatusSelect"
import { Button } from "@/components/ui/button"
import { useDeleteLead, useLead } from "@/hooks/useLeads"
import { getErrorMessage } from "@/services/api"

function InfoRow({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 text-sm">
      <span className="mt-0.5 text-muted-foreground">{icon}</span>
      <span className="min-w-0 break-words">{children}</span>
    </div>
  )
}

export default function LeadDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const leadId = Number(id)
  const navigate = useNavigate()
  const { data: lead, isLoading, isError, error } = useLead(leadId)
  const deleteLead = useDeleteLead()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [convertOpen, setConvertOpen] = useState(false)

  if (isLoading) {
    return (
      <PageWrapper title={t("leads.detailTitle")}>
        <DetailSkeleton />
      </PageWrapper>
    )
  }

  if (isError || !lead) {
    return (
      <PageWrapper title={t("leads.detailTitle")}>
        <EmptyState
          title={t("leads.notFound")}
          description={getErrorMessage(error)}
          action={
            <Button variant="outline" asChild>
              <Link to="/leads">
                <ArrowLeft /> {t("leads.backToList")}
              </Link>
            </Button>
          }
        />
      </PageWrapper>
    )
  }

  const converted = lead.status === "converted"

  const handleDelete = () => {
    deleteLead.mutate(leadId, {
      onSuccess: () => {
        setConfirmOpen(false)
        navigate("/leads")
      },
    })
  }

  const actions = (
    <div className="flex flex-wrap gap-2">
      {!converted && (
        <GradientButton onClick={() => setConvertOpen(true)}>
          <ArrowRightLeft /> {t("leads.convert")}
        </GradientButton>
      )}
      <Button variant="outline" asChild>
        <Link to={`/leads/${leadId}/edit`}>
          <Pencil /> {t("common.edit")}
        </Link>
      </Button>
      <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
        <Trash2 /> {t("common.delete")}
      </Button>
    </div>
  )

  return (
    <PageWrapper title={lead.name} actions={actions}>
      <Link to="/leads" className="-mt-4 flex items-center gap-1 text-sm text-muted-foreground hover:underline">
        <ArrowLeft className="size-4" /> {t("leads.allLeads")}
      </Link>

      {converted && lead.converted_contact_id !== null && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-900">
          <span className="flex items-center gap-2">
            <UserCheck className="size-4" /> {t("leads.convertedBanner")}
          </span>
          <Link
            to={`/contacts/${lead.converted_contact_id}`}
            className="font-semibold text-emerald-800 underline-offset-4 hover:underline"
          >
            {t("leads.viewContact")}
          </Link>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <GlassCard hoverable={false} className="flex flex-col gap-4 lg:col-span-2">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="text-xl font-semibold">{lead.name}</h2>
              {lead.company && <p className="text-sm text-muted-foreground">{lead.company}</p>}
            </div>
            <LeadStatusBadge status={lead.status} />
          </div>
          <div className="flex flex-col gap-3">
            {lead.email && (
              <InfoRow icon={<Mail className="size-4" />}>
                <a href={`mailto:${lead.email}`} className="text-violet-700 hover:underline">
                  {lead.email}
                </a>
              </InfoRow>
            )}
            {lead.phone && (
              <InfoRow icon={<Phone className="size-4" />}>
                <a href={`tel:${lead.phone}`} className="hover:underline">
                  {lead.phone}
                </a>
              </InfoRow>
            )}
            {lead.company && <InfoRow icon={<Building2 className="size-4" />}>{lead.company}</InfoRow>}
            <InfoRow icon={<Calendar className="size-4" />}>
              {t("leads.addedVia", { date: formatDate(lead.created_at), source: LEAD_SOURCE_LABELS[lead.source] })}
            </InfoRow>
          </div>
          {lead.notes && (
            <div className="flex flex-col gap-1">
              <h3 className="text-sm font-semibold">{t("common.notes")}</h3>
              <p className="text-sm whitespace-pre-wrap text-muted-foreground">{lead.notes}</p>
            </div>
          )}
        </GlassCard>

        <GlassCard hoverable={false} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <h2 className="text-sm font-semibold">{t("common.status")}</h2>
            <LeadStatusSelect lead={lead} />
            {converted && (
              <p className="text-xs text-muted-foreground">{t("leads.convertedNote")}</p>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <h2 className="text-sm font-semibold">{t("leads.followUp")}</h2>
            <Button variant="outline" asChild>
              <Link to={`/tasks/new?lead_id=${leadId}`}>
                <Plus /> {t("common.addTask")}
              </Link>
            </Button>
          </div>
        </GlassCard>
      </div>

      {!converted && <ConvertLeadDialog lead={lead} open={convertOpen} onOpenChange={setConvertOpen} />}

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("leads.deleteTitle")}
        description={t("leads.deleteText", { name: lead.name })}
        isPending={deleteLead.isPending}
        onConfirm={handleDelete}
      />
    </PageWrapper>
  )
}
