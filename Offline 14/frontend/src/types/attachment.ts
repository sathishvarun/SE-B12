export interface Attachment {
  id: number
  filename: string
  content_type: string
  size_bytes: number
  contact_id: number | null
  deal_id: number | null
  created_at: string
}
