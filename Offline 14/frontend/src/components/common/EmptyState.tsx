import type { ReactNode } from "react"
import { motion } from "framer-motion"
import { Inbox, type LucideIcon } from "lucide-react"
import { useLocation } from "react-router-dom"

import { TONES, sectionForPath } from "@/lib/sections"
import { cn } from "@/lib/utils"

interface EmptyStateProps {
  title: string
  description?: string
  icon?: LucideIcon
  /** Optional call to action, e.g. a GradientButton linking to a create page. */
  action?: ReactNode
  className?: string
}

/** Friendly placeholder shown when a list has no items, tinted with the section's colour. */
export function EmptyState({ title, description, icon: Icon = Inbox, action, className }: EmptyStateProps) {
  const tone = sectionForPath(useLocation().pathname)?.tone ?? TONES.grape
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-3xl border-2 border-dashed p-10 text-center",
        tone.border,
        tone.soft,
        className,
      )}
    >
      <div className={cn("rounded-2xl p-4", tone.tile)}>
        <Icon className="size-7" />
      </div>
      <h3 className="text-lg font-extrabold">{title}</h3>
      {description && <p className="max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action}
    </motion.div>
  )
}
