// Small formatting helpers shared by the deals, tasks and dashboard UI.
import i18n, { formatLocale } from "@/i18n"
import type { DealStage, LeadSource, TaskPriority } from "@/types"

// The label maps use getters so they always return text in the current language.
export const STAGE_LABELS: Record<DealStage, string> = {
  get prospect() { return i18n.t("deals.stage.prospect") },
  get proposal() { return i18n.t("deals.stage.proposal") },
  get negotiation() { return i18n.t("deals.stage.negotiation") },
  get won() { return i18n.t("deals.stage.won") },
  get lost() { return i18n.t("deals.stage.lost") },
}

export const PRIORITY_LABELS: Record<TaskPriority, string> = {
  get low() { return i18n.t("tasks.priority.low") },
  get medium() { return i18n.t("tasks.priority.medium") },
  get high() { return i18n.t("tasks.priority.high") },
}

export const SOURCE_LABELS: Record<LeadSource, string> = {
  get website() { return i18n.t("leads.source.website") },
  get referral() { return i18n.t("leads.source.referral") },
  get social() { return i18n.t("leads.source.social") },
  get other() { return i18n.t("leads.source.other") },
}

/** Format a money amount (the API sends decimals as strings). */
export function formatMoney(value: string | number, currency = "INR", compact = false): string {
  const amount = Number(value)
  try {
    return new Intl.NumberFormat(formatLocale(), {
      style: "currency",
      currency,
      notation: compact ? "compact" : "standard",
      maximumFractionDigits: compact ? 1 : 0,
    }).format(Number.isFinite(amount) ? amount : 0)
  } catch {
    // Unknown currency code: fall back to a plain number.
    return `${currency} ${amount.toLocaleString(formatLocale())}`
  }
}

/** Today's date in the user's local timezone as "YYYY-MM-DD". */
export function todayISO(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, "0")
  const day = String(now.getDate()).padStart(2, "0")
  return `${now.getFullYear()}-${month}-${day}`
}

/** True if a "YYYY-MM-DD" date is before today (string compare avoids timezone shifts). */
export function isBeforeToday(date: string | null | undefined): boolean {
  return Boolean(date) && (date as string).slice(0, 10) < todayISO()
}

/**
 * Format a "YYYY-MM-DD" date or an ISO datetime for display.
 * Date-only strings are built from their parts so they don't shift a day in some timezones.
 */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "—"
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  const date = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
    : new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(formatLocale(), { day: "numeric", month: "short", year: "numeric" }).format(date)
}

/** "2026-06" -> "Jun 26" */
export function formatMonth(value: string): string {
  const [year, month] = value.split("-").map(Number)
  if (!year || !month) return value
  return new Intl.DateTimeFormat(formatLocale(), { month: "short", year: "2-digit" }).format(new Date(year, month - 1, 1))
}

/** Sum of deal values (strings) as a number. */
export function sumValues(items: { value: string }[]): number {
  return items.reduce((total, item) => total + (Number(item.value) || 0), 0)
}
