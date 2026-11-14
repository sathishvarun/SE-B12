import type { ReactNode } from "react"

import { GlassCard } from "@/components/common"
import { cn } from "@/lib/utils"

interface ChartCardProps {
  title: string
  description?: string
  children: ReactNode
  className?: string
}

/** Card frame for a dashboard chart. */
export function ChartCard({ title, description, children, className }: ChartCardProps) {
  return (
    <GlassCard hoverable={false} className={cn("p-5", className)}>
      <h2 className="text-lg font-extrabold">{title}</h2>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
      <div className="mt-4">{children}</div>
    </GlassCard>
  )
}

/**
 * Tailwind selectors that theme Recharts' SVG: one violet accent for the bars
 * (via currentColor), muted axis labels and a recessive grid. Works in light and dark.
 */
export const chartThemeClasses =
  "h-64 w-full text-violet-500 [&_.recharts-cartesian-axis-tick-value]:fill-muted-foreground [&_.recharts-cartesian-axis-tick-value]:text-xs [&_.recharts-cartesian-grid_line]:stroke-border [&_.recharts-surface]:outline-none"

interface ChartTooltipProps {
  title: string
  rows: { label: string; value: string }[]
}

/** Tooltip body used by every dashboard chart. */
export function ChartTooltip({ title, rows }: ChartTooltipProps) {
  return (
    <div className="rounded-2xl border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-lg">
      <p className="font-medium">{title}</p>
      {rows.map((row) => (
        <p key={row.label} className="flex justify-between gap-4 text-muted-foreground">
          <span>{row.label}</span>
          <span className="font-medium text-foreground tabular-nums">{row.value}</span>
        </p>
      ))}
    </div>
  )
}
