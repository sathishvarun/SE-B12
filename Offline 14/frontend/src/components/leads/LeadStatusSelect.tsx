import { useTranslation } from "react-i18next"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useUpdateLeadStatus } from "@/hooks/useLeads"
import type { Lead } from "@/types"

import { EDITABLE_LEAD_STATUSES, LEAD_STATUS_LABELS } from "./constants"

type EditableStatus = (typeof EDITABLE_LEAD_STATUSES)[number]

function isEditableStatus(value: string): value is EditableStatus {
  return (EDITABLE_LEAD_STATUSES as readonly string[]).includes(value)
}

/** Change a lead's status. Disabled once the lead is converted. */
export function LeadStatusSelect({ lead }: { lead: Lead }) {
  const { t } = useTranslation()
  const updateStatus = useUpdateLeadStatus(lead.id)
  const converted = lead.status === "converted"

  return (
    <Select
      value={lead.status}
      disabled={converted || updateStatus.isPending}
      onValueChange={(value) => {
        if (isEditableStatus(value) && value !== lead.status) updateStatus.mutate(value)
      }}
    >
      <SelectTrigger className="w-40" aria-label={t("leads.statusAria")}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {EDITABLE_LEAD_STATUSES.map((status) => (
          <SelectItem key={status} value={status}>
            {LEAD_STATUS_LABELS[status]}
          </SelectItem>
        ))}
        {/* Only present so the trigger can show "Converted"; never selectable. */}
        {converted && (
          <SelectItem value="converted" disabled>
            {LEAD_STATUS_LABELS.converted}
          </SelectItem>
        )}
      </SelectContent>
    </Select>
  )
}
