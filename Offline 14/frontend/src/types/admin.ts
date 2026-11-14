import type { Plan } from "./auth"

export interface AdminUser {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  is_admin: boolean
  plan: Plan
  created_at: string
}

export interface AdminStats {
  total_users: number
  active_users: number
  pro_subscriptions: number
  signups_last_30_days: number
  total_contacts: number
  total_deals: number
}

export interface AdminUserUpdate {
  is_active?: boolean
  is_admin?: boolean
}
