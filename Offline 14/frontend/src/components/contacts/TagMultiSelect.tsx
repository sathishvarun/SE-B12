import { useTranslation } from "react-i18next"
import { useState } from "react"
import { Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useCreateTag, useTags } from "@/hooks/useContacts"
import { cn } from "@/lib/utils"

interface TagMultiSelectProps {
  value: number[]
  onChange: (tagIds: number[]) => void
}

/** Click tags to toggle them; type a name to create a new tag (it is selected right away). */
export function TagMultiSelect({ value, onChange }: TagMultiSelectProps) {
  const { t } = useTranslation()
  const { data: tags = [], isLoading } = useTags()
  const createTag = useCreateTag()
  const [newTag, setNewTag] = useState("")

  const toggle = (id: number) => {
    onChange(value.includes(id) ? value.filter((v) => v !== id) : [...value, id])
  }

  const handleCreate = () => {
    const name = newTag.trim()
    if (!name) return
    createTag.mutate(name, {
      onSuccess: (tag) => {
        onChange([...value, tag.id])
        setNewTag("")
      },
    })
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {isLoading && <span className="text-sm text-muted-foreground">{t("contacts.loadingTags")}</span>}
        {!isLoading && tags.length === 0 && (
          <span className="text-sm text-muted-foreground">{t("contacts.noTags")}</span>
        )}
        {tags.map((tag) => {
          const selected = value.includes(tag.id)
          return (
            <button
              key={tag.id}
              type="button"
              aria-pressed={selected}
              onClick={() => toggle(tag.id)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                selected
                  ? "border-violet-500 bg-violet-600 text-white"
                  : "border-border bg-background text-foreground hover:bg-violet-50",
              )}
            >
              {tag.name}
            </button>
          )
        })}
      </div>
      <div className="flex gap-2">
        <Input
          value={newTag}
          onChange={(e) => setNewTag(e.target.value)}
          onKeyDown={(e) => {
            // Enter would otherwise submit the whole contact form.
            if (e.key === "Enter") {
              e.preventDefault()
              handleCreate()
            }
          }}
          id="new-tag-name"
          name="new_tag_name"
          placeholder={t("contacts.newTagName")}
          aria-label={t("contacts.newTagName")}
          className="max-w-xs"
        />
        <Button
          type="button"
          variant="outline"
          onClick={handleCreate}
          disabled={!newTag.trim() || createTag.isPending}
        >
          <Plus /> {t("contacts.createTag")}
        </Button>
      </div>
    </div>
  )
}
