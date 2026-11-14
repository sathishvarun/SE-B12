import { useTranslation } from "react-i18next"
import { lazy, Suspense } from "react"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

import { AdminRoute } from "@/components/auth/AdminRoute"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { PublicOnlyRoute } from "@/components/auth/PublicOnlyRoute"
import { LoadingSpinner } from "@/components/common"
import { AppLayout } from "@/components/layout/AppLayout"
import { Toaster } from "@/components/ui/sonner"
import { AuthProvider } from "@/context/AuthContext"
import { useAuth } from "@/hooks/useAuth"

// Pages are loaded on demand (code splitting) so the first download stays small.
const AdminDashboardPage = lazy(() => import("@/pages/admin/AdminDashboardPage"))
const AdminUsersPage = lazy(() => import("@/pages/admin/AdminUsersPage"))
const ForgotPasswordPage = lazy(() => import("@/pages/auth/ForgotPasswordPage"))
const LoginPage = lazy(() => import("@/pages/auth/LoginPage"))
const OAuthCallbackPage = lazy(() => import("@/pages/auth/OAuthCallbackPage"))
const ProfilePage = lazy(() => import("@/pages/auth/ProfilePage"))
const RegisterPage = lazy(() => import("@/pages/auth/RegisterPage"))
const ResetPasswordPage = lazy(() => import("@/pages/auth/ResetPasswordPage"))
const BillingPage = lazy(() => import("@/pages/billing/BillingPage"))
const PricingPage = lazy(() => import("@/pages/billing/PricingPage"))
const ContactCreatePage = lazy(() => import("@/pages/contacts/ContactCreatePage"))
const ContactDetailPage = lazy(() => import("@/pages/contacts/ContactDetailPage"))
const ContactEditPage = lazy(() => import("@/pages/contacts/ContactEditPage"))
const ContactsListPage = lazy(() => import("@/pages/contacts/ContactsListPage"))
const DashboardPage = lazy(() => import("@/pages/dashboard/DashboardPage"))
const DealCreatePage = lazy(() => import("@/pages/deals/DealCreatePage"))
const DealDetailPage = lazy(() => import("@/pages/deals/DealDetailPage"))
const DealEditPage = lazy(() => import("@/pages/deals/DealEditPage"))
const DealsBoardPage = lazy(() => import("@/pages/deals/DealsBoardPage"))
const LeadCreatePage = lazy(() => import("@/pages/leads/LeadCreatePage"))
const LeadDetailPage = lazy(() => import("@/pages/leads/LeadDetailPage"))
const LeadEditPage = lazy(() => import("@/pages/leads/LeadEditPage"))
const LeadsListPage = lazy(() => import("@/pages/leads/LeadsListPage"))
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage"))
const SettingsPage = lazy(() => import("@/pages/settings/SettingsPage"))
const TaskCreatePage = lazy(() => import("@/pages/tasks/TaskCreatePage"))
const TaskEditPage = lazy(() => import("@/pages/tasks/TaskEditPage"))
const TasksPage = lazy(() => import("@/pages/tasks/TasksPage"))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 },
  },
})

/** The sidebar layout, filled in with the logged-in user's details. */
function AuthedLayout() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  return (
    <AppLayout
      isAdmin={user?.is_admin ?? false}
      userName={user?.full_name || user?.email || t("layout.user")}
      userEmail={user?.email ?? ""}
      plan={user?.plan}
      onLogout={logout}
    />
  )
}

export function AppRoutes() {
  return (
    <Suspense fallback={<LoadingSpinner fullPage className="min-h-screen" />}>
      <Routes>
        {/* Public routes */}
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/oauth/callback" element={<OAuthCallbackPage />} />

        {/* App routes: logged-in users only, inside the sidebar layout */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AuthedLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/profile" element={<ProfilePage />} />

            <Route path="/contacts" element={<ContactsListPage />} />
            <Route path="/contacts/new" element={<ContactCreatePage />} />
            <Route path="/contacts/:id" element={<ContactDetailPage />} />
            <Route path="/contacts/:id/edit" element={<ContactEditPage />} />

            <Route path="/leads" element={<LeadsListPage />} />
            <Route path="/leads/new" element={<LeadCreatePage />} />
            <Route path="/leads/:id" element={<LeadDetailPage />} />
            <Route path="/leads/:id/edit" element={<LeadEditPage />} />

            <Route path="/deals" element={<DealsBoardPage />} />
            <Route path="/deals/new" element={<DealCreatePage />} />
            <Route path="/deals/:id" element={<DealDetailPage />} />
            <Route path="/deals/:id/edit" element={<DealEditPage />} />

            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/tasks/new" element={<TaskCreatePage />} />
            <Route path="/tasks/:id/edit" element={<TaskEditPage />} />

            <Route path="/billing" element={<BillingPage />} />
            <Route path="/settings" element={<SettingsPage />} />

            {/* Admin-only routes */}
            <Route element={<AdminRoute />}>
              <Route path="/admin" element={<AdminDashboardPage />} />
              <Route path="/admin/users" element={<AdminUsersPage />} />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  )
}
