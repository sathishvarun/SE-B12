import { useTranslation } from "react-i18next"
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { SOURCE_LABELS } from "@/components/deals/format"
import type { DashboardAnalytics } from "@/types"

import { ChartCard, ChartTooltip, chartThemeClasses } from "./ChartCard"
import { SOURCE_COLORS } from "./chartColors"

interface Row {
  source: string
  label: string
  count: number
}

export function LeadsBySourceChart({ data }: { data: DashboardAnalytics["leads_by_source"] }) {
  const { t } = useTranslation()
  const rows: Row[] = data
    .map((item) => ({ source: item.source, label: SOURCE_LABELS[item.source] ?? item.source, count: item.count }))
    .sort((a, b) => b.count - a.count)
  const summary = rows.map((row) => `${row.label}: ${row.count}`).join(", ")

  return (
    <ChartCard title={t("dashboard.leadsBySourceTitle")} description={t("dashboard.leadsBySourceText")}>
      {rows.every((row) => row.count === 0) ? (
        <p className="py-10 text-center text-sm text-muted-foreground">{t("dashboard.noLeads")}</p>
      ) : (
        <div className={chartThemeClasses} role="img" aria-label={t("dashboard.leadsBySourceAria", { summary })}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid horizontal={false} strokeDasharray="3 3" />
              <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="label" tickLine={false} axisLine={false} width={72} />
              <Tooltip
                cursor={{ fill: "currentColor", fillOpacity: 0.08 }}
                content={({ active, payload }) => {
                  const row = payload?.[0]?.payload as Row | undefined
                  if (!active || !row) return null
                  return <ChartTooltip title={row.label} rows={[{ label: t("nav.leads"), value: String(row.count) }]} />
                }}
              />
              <Bar dataKey="count" radius={[4, 10, 10, 4]} maxBarSize={28}>
                {rows.map((row) => (
                  <Cell key={row.source} fill={SOURCE_COLORS[row.source]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  )
}
