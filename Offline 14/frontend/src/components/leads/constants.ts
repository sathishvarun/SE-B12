import i18n from "@/i18n"
import type { LeadSource, LeadStatus } from "@/types"

export const LEAD_STATUSES: LeadStatus[] = ["new", "contacted", "qualified", "lost", "converted"]

/** Statuses a user can pick by hand ("converted" only happens through Convert). */
export const EDITABLE_LEAD_STATUSES = ["new", "contacted", "qualified", "lost"] as const satisfies readonly LeadStatus[]

export const LEAD_SOURCES: LeadSource[] = ["website", "referral", "social", "other"]

// Getters, so the labels always use the current language.
export const LEAD_STATUS_LABELS: Record<LeadStatus, string> = {
  get new() { return i18n.t("leads.status.new") },
  get contacted() { return i18n.t("leads.status.contacted") },
  get qualified() { return i18n.t("leads.status.qualified") },
  get lost() { return i18n.t("leads.status.lost") },
  get converted() { return i18n.t("leads.status.converted") },
}

export const LEAD_SOURCE_LABELS: Record<LeadSource, string> = {
  get website() { return i18n.t("leads.source.website") },
  get referral() { return i18n.t("leads.source.referral") },
  get social() { return i18n.t("leads.source.social") },
  get other() { return i18n.t("leads.source.other") },
}
