import { useTranslation } from "react-i18next"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { Tag } from "@/types"

interface TagFilterProps {
  tags: Tag[]
  value: number | undefined
  onChange: (tagId: number | undefined) => void
}

const ALL = "all"

export function TagFilter({ tags, value, onChange }: TagFilterProps) {
  const { t } = useTranslation()
  return (
    <Select
      value={value === undefined ? ALL : String(value)}
      onValueChange={(v) => onChange(v === ALL ? undefined : Number(v))}
    >
      <SelectTrigger className="w-full sm:w-44" aria-label={t("contacts.filterByTag")}>
        <SelectValue placeholder={t("contacts.allTags")} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={ALL}>{t("contacts.allTags")}</SelectItem>
        {tags.map((tag) => (
          <SelectItem key={tag.id} value={String(tag.id)}>
            {tag.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
