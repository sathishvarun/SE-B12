import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { DealStage } from "@/types"

import { STAGE_LABELS } from "./format"

const STAGE_CLASSES: Record<DealStage, string> = {
  prospect: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-200",
  proposal: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200",
  negotiation: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  won: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  lost: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200",
}

interface StageBadgeProps {
  stage: DealStage
  className?: string
}

export function StageBadge({ stage, className }: StageBadgeProps) {
  useTranslation() // re-render when the language changes
  return <Badge className={cn("rounded-full font-bold", STAGE_CLASSES[stage], className)}>{STAGE_LABELS[stage]}</Badge>
}
