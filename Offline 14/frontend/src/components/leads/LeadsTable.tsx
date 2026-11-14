import { useTranslation } from "react-i18next"
import { Building2, Mail } from "lucide-react"
import { Link } from "react-router-dom"

import { AnimatedList, GlassCard } from "@/components/common"
import { formatDate } from "@/components/contacts/utils"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Lead } from "@/types"

import { LEAD_SOURCE_LABELS } from "./constants"
import { LeadStatusBadge } from "./LeadStatusBadge"

/** Table on desktop, stacked cards on mobile. */
export function LeadsTable({ leads }: { leads: Lead[] }) {
  const { t } = useTranslation()
  return (
    <>
      <GlassCard hoverable={false} className="hidden p-0 md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="pl-6">{t("common.name")}</TableHead>
              <TableHead>{t("common.company")}</TableHead>
              <TableHead>{t("common.email")}</TableHead>
              <TableHead>{t("common.source")}</TableHead>
              <TableHead>{t("common.status")}</TableHead>
              <TableHead className="pr-6">{t("common.created")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {leads.map((lead) => (
              <TableRow key={lead.id}>
                <TableCell className="pl-6 font-medium">
                  <Link to={`/leads/${lead.id}`} className="text-violet-700 hover:underline">
                    {lead.name}
                  </Link>
                </TableCell>
                <TableCell>{lead.company ?? "-"}</TableCell>
                <TableCell>{lead.email ?? "-"}</TableCell>
                <TableCell>{LEAD_SOURCE_LABELS[lead.source]}</TableCell>
                <TableCell>
                  <LeadStatusBadge status={lead.status} />
                </TableCell>
                <TableCell className="pr-6 text-muted-foreground">{formatDate(lead.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </GlassCard>

      <AnimatedList className="md:hidden">
        {leads.map((lead) => (
          <Link key={lead.id} to={`/leads/${lead.id}`} className="block">
            <GlassCard className="flex flex-col gap-2 p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-violet-700">{lead.name}</span>
                <LeadStatusBadge status={lead.status} />
              </div>
              {lead.company && (
                <span className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Building2 className="size-4" /> {lead.company}
                </span>
              )}
              {lead.email && (
                <span className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Mail className="size-4" /> {lead.email}
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                {LEAD_SOURCE_LABELS[lead.source]} - {formatDate(lead.created_at)}
              </span>
            </GlassCard>
          </Link>
        ))}
      </AnimatedList>
    </>
  )
}
