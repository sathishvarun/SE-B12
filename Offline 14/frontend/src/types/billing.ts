import type { Plan } from "./auth"

export type SubscriptionStatus = "active" | "trialing" | "past_due" | "cancelled"

export interface Subscription {
  plan: Plan
  status: SubscriptionStatus
  current_period_end: string | null
  limits: { max_contacts: number | null; max_open_deals: number | null }
  usage: { contacts: number; open_deals: number }
}

export interface CheckoutResponse {
  checkout_url: string
}
