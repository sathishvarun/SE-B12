import { useTranslation } from "react-i18next"
import type { ReactNode } from "react"
import { motion } from "framer-motion"
import { useLocation } from "react-router-dom"

import { sectionForPath } from "@/lib/sections"
import { cn } from "@/lib/utils"

interface PageWrapperProps {
  children: ReactNode
  /** Optional page heading rendered above the content. */
  title?: string
  /** Optional element shown on the right of the heading (e.g. a "New" button). */
  actions?: ReactNode
  className?: string
}

/**
 * Wrap every page in this: fades the page in and renders an optional header.
 * The header shows the section's coloured icon (Contacts = mint, Deals = sky, ...).
 */
export function PageWrapper({ children, title, actions, className }: PageWrapperProps) {
  // Re-render on language change so the section label updates too.
  useTranslation()
  const section = sectionForPath(useLocation().pathname)
  const Icon = section?.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.3 }}
      className={cn("flex flex-col gap-6", className)}
    >
      {(title || actions) && (
        <div className="flex flex-wrap items-center justify-between gap-4">
          {title && (
            <div className="flex min-w-0 items-center gap-3">
              {Icon && section && (
                <div className={cn("flex size-11 shrink-0 items-center justify-center rounded-2xl", section.tone.tile)}>
                  <Icon className="size-5" />
                </div>
              )}
              <div className="min-w-0">
                {section && section.label !== title && (
                  <p className={cn("text-xs font-bold tracking-wider uppercase", section.tone.text)}>
                    {section.label}
                  </p>
                )}
                <h1 className="truncate text-2xl font-extrabold tracking-tight sm:text-3xl">{title}</h1>
              </div>
            </div>
          )}
          {actions}
        </div>
      )}
      {children}
    </motion.div>
  )
}
