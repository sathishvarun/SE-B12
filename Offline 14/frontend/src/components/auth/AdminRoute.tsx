import type { ReactNode } from "react"
import { Navigate, Outlet } from "react-router-dom"

import { LoadingSpinner } from "@/components/common"
import { useAuth } from "@/hooks/useAuth"

/** Only lets admins through; everyone else is sent to the dashboard. */
export function AdminRoute({ children }: { children?: ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <LoadingSpinner fullPage />
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  if (!user.is_admin) {
    return <Navigate to="/dashboard" replace />
  }
  return <>{children ?? <Outlet />}</>
}
