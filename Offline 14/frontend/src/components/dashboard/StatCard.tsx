import type { ReactNode } from "react"
import { Link } from "react-router-dom"
import type { LucideIcon } from "lucide-react"
import { motion } from "framer-motion"

import { TONES, type ToneName } from "@/lib/sections"
import { cn } from "@/lib/utils"

interface StatCardProps {
  label: string
  value: ReactNode
  icon: LucideIcon
  /** Secondary line under the number, e.g. pipeline value. */
  hint?: ReactNode
  to?: string
  /** Pastel colour of the card (matches the section it links to). */
  tone?: ToneName
}

/** One headline number on the dashboard, on a pastel card. */
export function StatCard({ label, value, icon: Icon, hint, to, tone = "grape" }: StatCardProps) {
  const t = TONES[tone]
  const content = (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3 }}
      className={cn("flex h-full flex-col gap-1 rounded-3xl border-2 p-4 sm:p-5", t.soft, t.border)}
    >
      <div className="flex items-center justify-between gap-2">
        <p className={cn("text-sm font-bold", t.text)}>{label}</p>
        <div className={cn("hidden rounded-2xl p-2.5 sm:block", t.tile)}>
          <Icon className="size-5" />
        </div>
      </div>
      <p className="text-3xl font-black tracking-tight tabular-nums sm:text-4xl">{value}</p>
      {hint && <div className="text-sm font-semibold text-muted-foreground">{hint}</div>}
    </motion.div>
  )
  return to ? (
    <Link to={to} className="block rounded-3xl outline-none focus-visible:ring-2 focus-visible:ring-ring">
      {content}
    </Link>
  ) : (
    content
  )
}
