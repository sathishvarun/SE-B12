import { useTranslation } from "react-i18next"
import { Sparkles } from "lucide-react"
import { Link } from "react-router-dom"

interface PlanLimitNoticeProps {
  message: string
}

/** Shown when the backend answers 402: the free plan limit was reached. */
export function PlanLimitNotice({ message }: PlanLimitNoticeProps) {
  const { t } = useTranslation()
  return (
    <div
      role="alert"
      className="flex flex-col gap-2 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex items-start gap-2">
        <Sparkles className="mt-0.5 size-4 shrink-0" />
        <span>{message}</span>
      </div>
      <Link to="/billing" className="font-semibold text-violet-700 underline-offset-4 hover:underline">
        {t("common.upgradeToPro")}
      </Link>
    </div>
  )
}
