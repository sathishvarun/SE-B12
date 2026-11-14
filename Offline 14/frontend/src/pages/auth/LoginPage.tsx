import { useTranslation } from "react-i18next"
import { useEffect } from "react"
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom"
import { toast } from "sonner"

import { AuthShell, OrDivider } from "@/components/auth/AuthShell"
import { GoogleButton } from "@/components/auth/GoogleButton"
import { LoginForm } from "@/components/auth/LoginForm"

interface LoginLocationState {
  from?: string
}

export default function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const from = (location.state as LoginLocationState | null)?.from ?? "/dashboard"
  const oauthError = searchParams.get("error")

  // The backend redirects here with ?error=oauth_failed if Google sign-in fails.
  useEffect(() => {
    if (oauthError) {
      toast.error(t("auth.login.googleFailed"), { id: "oauth-error" })
    }
  }, [oauthError, t])

  return (
    <AuthShell
      title={t("auth.login.title")}
      subtitle={t("auth.login.subtitle")}
      footer={
        <>
          {t("auth.login.noAccount")}{" "}
          <Link to="/register" className="font-medium text-violet-600 hover:underline">
            {t("auth.login.signUp")}
          </Link>
        </>
      }
    >
      <LoginForm onSuccess={() => navigate(from, { replace: true })} />
      <OrDivider />
      <GoogleButton />
    </AuthShell>
  )
}
