import { useTranslation } from "react-i18next"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useContactOptions } from "@/hooks/useContactOptions"
import { cn } from "@/lib/utils"

interface ContactSelectProps {
  id?: string
  /** Contact id as a string ("" = nothing selected). */
  value: string
  onChange: (value: string) => void
  invalid?: boolean
  className?: string
}

/** Dropdown of all the user's contacts (GET /contacts/options). */
export function ContactSelect({ id, value, onChange, invalid, className }: ContactSelectProps) {
  const { t } = useTranslation()
  const { data: contacts = [], isLoading } = useContactOptions()

  return (
    <Select name={id} value={value} onValueChange={onChange}>
      <SelectTrigger id={id} aria-invalid={invalid || undefined} className={cn("w-full", className)}>
        <SelectValue placeholder={isLoading ? t("deals.loadingContacts") : t("deals.chooseContact")} />
      </SelectTrigger>
      <SelectContent>
        {contacts.length === 0 && !isLoading && (
          <div className="px-2 py-1.5 text-sm text-muted-foreground">{t("deals.noContacts")}</div>
        )}
        {contacts.map((contact) => (
          <SelectItem key={contact.id} value={String(contact.id)}>
            {contact.name}
            {contact.company && <span className="text-muted-foreground"> · {contact.company}</span>}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
