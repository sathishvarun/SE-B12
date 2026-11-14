import api from "@/services/api"
import type { CheckoutResponse, Subscription } from "@/types"

export const billingService = {
  getSubscription: async (): Promise<Subscription> => {
    const { data } = await api.get<Subscription>("/billing/subscription")
    return data
  },

  createCheckout: async (): Promise<CheckoutResponse> => {
    const { data } = await api.post<CheckoutResponse>("/billing/checkout")
    return data
  },

  cancel: async (): Promise<Subscription> => {
    const { data } = await api.post<Subscription>("/billing/cancel")
    return data
  },
}
