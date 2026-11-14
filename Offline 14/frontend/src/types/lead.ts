import type { Contact } from "./contact"
import type { Deal } from "./deal"

export type LeadSource = "website" | "referral" | "social" | "other"
export type LeadStatus = "new" | "contacted" | "qualified" | "lost" | "converted"

export interface Lead {
  id: number
  name: string
  email: string | null
  phone: string | null
  company: string | null
  source: LeadSource
  status: LeadStatus
  notes: string | null
  converted_contact_id: number | null
  created_at: string
  updated_at: string
}

export interface LeadInput {
  name: string
  email?: string | null
  phone?: string | null
  company?: string | null
  source?: LeadSource
  notes?: string | null
}

export interface ConvertLeadInput {
  deal_title: string
  deal_value: string | number
  expected_close_date?: string | null
}

export interface ConvertLeadResult {
  lead: Lead
  contact: Contact
  deal: Deal
}
