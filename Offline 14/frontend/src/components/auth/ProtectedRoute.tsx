import { useTranslation } from "react-i18next"
import type { ReactNode } from "react"
import { Navigate, Outlet, useLocation } from "react-router-dom"

import { LoadingSpinner } from "@/components/common"
import { useAuth } from "@/hooks/useAuth"

/** Only lets logged-in users through; others go to /login (and come back after). */
export function ProtectedRoute({ children }: { children?: ReactNode }) {
  const { t } = useTranslation()
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <LoadingSpinner fullPage label={t("common.loading")} className="min-h-screen" />
  }
  if (!user) {
    const from = `${location.pathname}${location.search}`
    return <Navigate to="/login" replace state={{ from }} />
  }
  return <>{children ?? <Outlet />}</>
}
