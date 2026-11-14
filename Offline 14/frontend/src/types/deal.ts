import type { Attachment } from "./attachment"
import type { Task } from "./task"

export type DealStage = "prospect" | "proposal" | "negotiation" | "won" | "lost"

export const DEAL_STAGES: DealStage[] = ["prospect", "proposal", "negotiation", "won", "lost"]

export interface DealSummary {
  id: number
  title: string
  /** Decimal serialized as a string, e.g. "1500.00" */
  value: string
  currency: string
  stage: DealStage
  expected_close_date: string | null
}

export interface Deal extends DealSummary {
  contact_id: number
  contact: { id: number; name: string; company: string | null }
  position: number
  notes: string | null
  closed_at: string | null
  created_at: string
  updated_at: string
}

export interface DealDetail extends Deal {
  tasks: Task[]
  attachments: Attachment[]
}

export interface DealInput {
  title: string
  contact_id: number
  value: string | number
  currency?: string
  stage?: DealStage
  expected_close_date?: string | null
  notes?: string | null
}

export type DealBoard = Record<DealStage, Deal[]>

export interface MoveDealInput {
  stage: DealStage
  position: number
}
