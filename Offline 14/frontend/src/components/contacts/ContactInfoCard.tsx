import { useTranslation } from "react-i18next"
import type { ReactNode } from "react"
import { Building2, Calendar, Mail, MapPin, Phone } from "lucide-react"

import { GlassCard } from "@/components/common"
import type { Contact } from "@/types"

import { TagBadge } from "./TagBadge"
import { formatDate } from "./utils"

function InfoRow({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 text-sm">
      <span className="mt-0.5 text-muted-foreground">{icon}</span>
      <span className="min-w-0 break-words">{children}</span>
    </div>
  )
}

export function ContactInfoCard({ contact }: { contact: Contact }) {
  const { t } = useTranslation()
  return (
    <GlassCard hoverable={false} className="flex flex-col gap-4">
      <div>
        <h2 className="text-xl font-semibold">{contact.name}</h2>
        {contact.company && <p className="text-sm text-muted-foreground">{contact.company}</p>}
      </div>

      {contact.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {contact.tags.map((tag) => (
            <TagBadge key={tag.id} tag={tag} />
          ))}
        </div>
      )}

      <div className="flex flex-col gap-3">
        {contact.email && (
          <InfoRow icon={<Mail className="size-4" />}>
            <a href={`mailto:${contact.email}`} className="text-violet-700 hover:underline">
              {contact.email}
            </a>
          </InfoRow>
        )}
        {contact.phone && (
          <InfoRow icon={<Phone className="size-4" />}>
            <a href={`tel:${contact.phone}`} className="hover:underline">
              {contact.phone}
            </a>
          </InfoRow>
        )}
        {contact.company && <InfoRow icon={<Building2 className="size-4" />}>{contact.company}</InfoRow>}
        {contact.address && <InfoRow icon={<MapPin className="size-4" />}>{contact.address}</InfoRow>}
        <InfoRow icon={<Calendar className="size-4" />}>{t("common.added", { date: formatDate(contact.created_at) })}</InfoRow>
      </div>

      {contact.notes && (
        <div className="flex flex-col gap-1">
          <h3 className="text-sm font-semibold">{t("common.notes")}</h3>
          <p className="text-sm whitespace-pre-wrap text-muted-foreground">{contact.notes}</p>
        </div>
      )}
    </GlassCard>
  )
}
