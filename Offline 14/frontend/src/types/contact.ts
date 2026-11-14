import type { Attachment } from "./attachment"
import type { DealSummary } from "./deal"
import type { Task } from "./task"

export interface Tag {
  id: number
  name: string
}

export interface Contact {
  id: number
  name: string
  email: string | null
  phone: string | null
  company: string | null
  address: string | null
  notes: string | null
  tags: Tag[]
  created_at: string
  updated_at: string
}

export interface ContactDetail extends Contact {
  deals: DealSummary[]
  tasks: Task[]
  attachments: Attachment[]
}

export interface ContactInput {
  name: string
  email?: string | null
  phone?: string | null
  company?: string | null
  address?: string | null
  notes?: string | null
  tag_ids?: number[]
}

export interface ContactOption {
  id: number
  name: string
  company: string | null
}
