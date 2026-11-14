import { useTranslation } from "react-i18next"
import { ChartCard } from "./ChartCard"

/** Lead conversion rate (0..1) as a big percentage with a progress bar. */
export function ConversionRateCard({ rate }: { rate: number }) {
  const { t } = useTranslation()
  const percent = Math.round(Math.min(Math.max(rate, 0), 1) * 1000) / 10

  return (
    <ChartCard title={t("dashboard.conversionTitle")} description={t("dashboard.conversionText")}>
      <p className="text-5xl font-black tracking-tight text-pink-600 tabular-nums">{percent}%</p>
      <progress
        value={percent}
        max={100}
        aria-label={t("dashboard.conversionTitle")}
        className="mt-4 h-4 w-full appearance-none overflow-hidden rounded-full [&::-moz-progress-bar]:rounded-full [&::-moz-progress-bar]:bg-gradient-to-r [&::-moz-progress-bar]:from-pink-400 [&::-moz-progress-bar]:to-orange-300 [&::-webkit-progress-bar]:bg-pink-50 [&::-webkit-progress-value]:rounded-full [&::-webkit-progress-value]:bg-gradient-to-r [&::-webkit-progress-value]:from-pink-400 [&::-webkit-progress-value]:to-orange-300"
      />
    </ChartCard>
  )
}
