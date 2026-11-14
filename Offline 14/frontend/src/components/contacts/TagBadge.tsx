import { useTranslation } from "react-i18next"
import { X } from "lucide-react"

import { cn } from "@/lib/utils"
import type { Tag } from "@/types"

interface TagBadgeProps {
  tag: Tag
  /** If given, shows a small remove button. */
  onRemove?: () => void
  className?: string
}

export function TagBadge({ tag, onRemove, className }: TagBadgeProps) {
  const { t } = useTranslation()
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700",
        className,
      )}
    >
      {tag.name}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label={t("contacts.removeTag", { name: tag.name })}
          className="rounded-full hover:bg-violet-200"
        >
          <X className="size-3" />
        </button>
      )}
    </span>
  )
}
