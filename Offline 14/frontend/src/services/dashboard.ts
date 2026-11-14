import api from "@/services/api"
import type { DashboardAnalytics, DashboardSummary } from "@/types"

export const dashboardService = {
  async summary(): Promise<DashboardSummary> {
    const { data } = await api.get<DashboardSummary>("/dashboard/summary")
    return data
  },

  async analytics(): Promise<DashboardAnalytics> {
    const { data } = await api.get<DashboardAnalytics>("/dashboard/analytics")
    return data
  },
}
