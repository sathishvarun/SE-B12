import { useQuery } from "@tanstack/react-query"

import { dashboardService } from "@/services/dashboard"

export const dashboardKeys = {
  all: ["dashboard"] as const,
  summary: ["dashboard", "summary"] as const,
  analytics: ["dashboard", "analytics"] as const,
}

export function useDashboardSummary() {
  return useQuery({ queryKey: dashboardKeys.summary, queryFn: dashboardService.summary })
}

export function useDashboardAnalytics() {
  return useQuery({ queryKey: dashboardKeys.analytics, queryFn: dashboardService.analytics })
}
