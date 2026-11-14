import type { DealStage } from "./deal"
import type { LeadSource } from "./lead"

export interface DashboardSummary {
  contacts: number
  open_leads: number
  open_deals: number
  open_pipeline_value: string
  tasks_due_today: number
  tasks_overdue: number
}

export interface DashboardAnalytics {
  pipeline_by_stage: { stage: DealStage; count: number; value: string }[]
  deals_won_by_month: { month: string; count: number; value: string }[]
  lead_conversion_rate: number
  leads_by_source: { source: LeadSource; count: number }[]
}
