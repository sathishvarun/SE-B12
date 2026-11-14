import { useTranslation } from "react-i18next"
import type { ReactNode } from "react"
import { Navigate, Outlet } from "react-router-dom"

import { LoadingSpinner } from "@/components/common"
import { useAuth } from "@/hooks/useAuth"

/** For /login and /register: logged-in users are sent to the dashboard instead. */
export function PublicOnlyRoute({ children }: { children?: ReactNode }) {
  const { t } = useTranslation()
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <LoadingSpinner fullPage label={t("common.loading")} className="min-h-screen" />
  }
  if (user) {
    return <Navigate to="/dashboard" replace />
  }
  return <>{children ?? <Outlet />}</>
}
