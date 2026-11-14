import { useTranslation } from "react-i18next"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { formatMonth, formatMoney } from "@/components/deals/format"
import type { DashboardAnalytics } from "@/types"

import { ChartCard, ChartTooltip, chartThemeClasses } from "./ChartCard"

interface Row {
  label: string
  value: number
  count: number
}

export function DealsWonChart({ data }: { data: DashboardAnalytics["deals_won_by_month"] }) {
  const { t } = useTranslation()
  const rows: Row[] = data.map((item) => ({
    label: formatMonth(item.month),
    value: Number(item.value) || 0,
    count: item.count,
  }))
  const summary = rows.map((row) => t("dashboard.dealsWonSummary", { label: row.label, value: formatMoney(row.value), count: row.count })).join(", ")

  return (
    <ChartCard title={t("dashboard.dealsWonTitle")} description={t("dashboard.dealsWonText")}>
      <div className={chartThemeClasses} role="img" aria-label={t("dashboard.dealsWonAria", { summary })}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis dataKey="label" tickLine={false} axisLine={false} interval={0} />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={64}
              tickFormatter={(v: number) => formatMoney(v, "INR", true)}
            />
            <Tooltip
              cursor={{ fill: "currentColor", fillOpacity: 0.08 }}
              content={({ active, payload }) => {
                const row = payload?.[0]?.payload as Row | undefined
                if (!active || !row) return null
                return (
                  <ChartTooltip
                    title={row.label}
                    rows={[
                      { label: t("dashboard.value"), value: formatMoney(row.value) },
                      { label: t("dashboard.dealsWonTitle"), value: String(row.count) },
                    ]}
                  />
                )
              }}
            />
            <Bar dataKey="value" fill="#34d399" radius={[10, 10, 4, 4]} maxBarSize={40} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  )
}
