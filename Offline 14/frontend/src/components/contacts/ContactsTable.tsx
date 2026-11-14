import { useTranslation } from "react-i18next"
import { Building2, Mail, Phone } from "lucide-react"
import { Link } from "react-router-dom"

import { AnimatedList, GlassCard } from "@/components/common"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Contact } from "@/types"

import { ContactAvatar } from "./ContactAvatar"
import { TagBadge } from "./TagBadge"

interface ContactsTableProps {
  contacts: Contact[]
}

function TagList({ contact }: { contact: Contact }) {
  if (contact.tags.length === 0) return <span className="text-muted-foreground">-</span>
  return (
    <div className="flex flex-wrap gap-1">
      {contact.tags.map((tag) => (
        <TagBadge key={tag.id} tag={tag} />
      ))}
    </div>
  )
}

/** Table on desktop, stacked cards on mobile. */
export function ContactsTable({ contacts }: ContactsTableProps) {
  const { t } = useTranslation()
  return (
    <>
      {/* Desktop */}
      <GlassCard hoverable={false} className="hidden p-0 md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="pl-6">{t("common.name")}</TableHead>
              <TableHead>{t("common.email")}</TableHead>
              <TableHead>{t("common.phone")}</TableHead>
              <TableHead>{t("common.company")}</TableHead>
              <TableHead className="pr-6">{t("common.tags")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {contacts.map((contact) => (
              <TableRow key={contact.id}>
                <TableCell className="pl-6 font-medium">
                  <Link
                    to={`/contacts/${contact.id}`}
                    className="flex items-center gap-3 font-bold text-foreground hover:text-emerald-700 hover:underline"
                  >
                    <ContactAvatar id={contact.id} name={contact.name} />
                    {contact.name}
                  </Link>
                </TableCell>
                <TableCell>{contact.email ?? "-"}</TableCell>
                <TableCell>{contact.phone ?? "-"}</TableCell>
                <TableCell>{contact.company ?? "-"}</TableCell>
                <TableCell className="pr-6">
                  <TagList contact={contact} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </GlassCard>

      {/* Mobile */}
      <AnimatedList className="md:hidden">
        {contacts.map((contact) => (
          <Link key={contact.id} to={`/contacts/${contact.id}`} className="block">
            <GlassCard className="flex flex-col gap-2 p-4">
              <span className="flex items-center gap-2 font-bold">
                <ContactAvatar id={contact.id} name={contact.name} />
                {contact.name}
              </span>
              {contact.company && (
                <span className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Building2 className="size-4" /> {contact.company}
                </span>
              )}
              {contact.email && (
                <span className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Mail className="size-4" /> {contact.email}
                </span>
              )}
              {contact.phone && (
                <span className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Phone className="size-4" /> {contact.phone}
                </span>
              )}
              {contact.tags.length > 0 && <TagList contact={contact} />}
            </GlassCard>
          </Link>
        ))}
      </AnimatedList>
    </>
  )
}
