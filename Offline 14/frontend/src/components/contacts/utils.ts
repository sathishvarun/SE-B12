import { formatLocale } from "@/i18n"
import axios from "axios"

import type { DealStage } from "@/types"

const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/

/** Parse "YYYY-MM-DD" as a local date (not UTC) so it doesn't shift a day; ISO datetimes as-is. */
export function parseDate(value: string): Date {
  if (DATE_ONLY.test(value)) {
    const [year, month, day] = value.split("-").map(Number)
    return new Date(year, month - 1, day)
  }
  return new Date(value)
}


export function formatDate(value: string | null | undefined): string {
  if (!value) return "-"
  const date = parseDate(value)
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(formatLocale(), { dateStyle: "medium" }).format(date)
}

/** Format a decimal string (e.g. "1500.00") in the given currency, e.g. "$1,500.00". */
export function formatMoney(value: string | number, currency = "USD"): string {
  const amount = Number(value)
  try {
    return new Intl.NumberFormat(formatLocale(), { style: "currency", currency }).format(amount)
  } catch {
    // Unknown currency code - fall back to a plain number plus the code.
    return `${new Intl.NumberFormat(formatLocale()).format(amount)} ${currency}`
  }
}

/** 1536 -> "1.5 KB" */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ["KB", "MB", "GB"]
  let size = bytes / 1024
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${size.toFixed(size < 10 ? 1 : 0)} ${units[unit]}`
}

/** True when the backend refused because the free plan limit was reached (HTTP 402). */
export function isPlanLimitError(err: unknown): boolean {
  return axios.isAxiosError(err) && err.response?.status === 402
}

export const DEAL_STAGE_CLASSES: Record<DealStage, string> = {
  prospect: "bg-violet-100 text-violet-700",
  proposal: "bg-sky-100 text-sky-700",
  negotiation: "bg-amber-100 text-amber-700",
  won: "bg-emerald-100 text-emerald-700",
  lost: "bg-rose-100 text-rose-700",
}

/** "" -> null, otherwise trimmed text. Used when turning form values into API input. */
export function emptyToNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === "" ? null : trimmed
}
