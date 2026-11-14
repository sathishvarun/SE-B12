import { useTranslation } from "react-i18next"
import { Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"

interface LoadingSpinnerProps {
  /** Optional text shown next to the spinner. */
  label?: string
  /** Fill the available area and centre the spinner (default: false). */
  fullPage?: boolean
  className?: string
}

/** Spinning loader for pending queries and route loading states. */
export function LoadingSpinner({ label, fullPage = false, className }: LoadingSpinnerProps) {
  const { t } = useTranslation()
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex items-center justify-center gap-2 text-muted-foreground",
        fullPage && "min-h-[50vh] w-full",
        className,
      )}
    >
      <Loader2 className="size-5 animate-spin" />
      <span className={cn(!label && "sr-only")}>{label ?? t("common.loading")}</span>
    </div>
  )
}
