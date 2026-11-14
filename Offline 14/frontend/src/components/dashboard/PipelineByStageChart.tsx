import { useTranslation } from "react-i18next"
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { STAGE_LABELS, formatMoney } from "@/components/deals/format"
import type { DashboardAnalytics } from "@/types"

import { ChartCard, ChartTooltip, chartThemeClasses } from "./ChartCard"
import { STAGE_COLORS } from "./chartColors"

interface Row {
  stage: string
  label: string
  value: number
  count: number
}

export function PipelineByStageChart({ data }: { data: DashboardAnalytics["pipeline_by_stage"] }) {
  const { t } = useTranslation()
  const rows: Row[] = data.map((item) => ({
    stage: item.stage,
    label: STAGE_LABELS[item.stage],
    value: Number(item.value) || 0,
    count: item.count,
  }))
  const summary = rows.map((row) => `${row.label}: ${formatMoney(row.value)} (${row.count})`).join(", ")

  return (
    <ChartCard title={t("dashboard.pipelineTitle")} description={t("dashboard.pipelineText")}>
      <div className={chartThemeClasses} role="img" aria-label={t("dashboard.pipelineAria", { summary })}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              interval={0}
              // Short label so five stages fit side by side on a phone
              tickFormatter={(label: string) => (label === STAGE_LABELS.negotiation ? t("dashboard.negotiationShort") : label)}
            />
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
                      { label: t("nav.deals"), value: String(row.count) },
                    ]}
                  />
                )
              }}
            />
            <Bar dataKey="value" radius={[10, 10, 4, 4]} maxBarSize={48}>
              {rows.map((row) => (
                <Cell key={row.stage} fill={STAGE_COLORS[row.stage]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  )
}
