import { useTranslation } from "react-i18next"
import { useEffect, useRef, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { AuthShell } from "@/components/auth/AuthShell"
import { GradientButton, LoadingSpinner } from "@/components/common"
import { useAuth } from "@/hooks/useAuth"
import { getErrorMessage } from "@/services/api"

/** Google sign-in lands here with `#access_token=...&refresh_token=...` in the URL. */
export default function OAuthCallbackPage() {
  const { t } = useTranslation()
  const { loginWithTokens } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  // Read the tokens once: the hash disappears after we navigate away.
  const [tokens] = useState(() => {
    const params = new URLSearchParams(location.hash.replace(/^#/, ""))
    const accessToken = params.get("access_token")
    const refreshToken = params.get("refresh_token")
    return accessToken && refreshToken ? { accessToken, refreshToken } : null
  })
  const [error, setError] = useState<string | null>(null)
  // React StrictMode runs effects twice in dev; only handle the tokens once.
  const handled = useRef(false)

  // Remove the tokens from the address bar and browser history straight away,
  // whether sign-in succeeds or fails.
  useEffect(() => {
    if (window.location.hash) {
      window.history.replaceState(null, "", window.location.pathname)
    }
  }, [])

  useEffect(() => {
    if (handled.current || !tokens) return
    handled.current = true

    loginWithTokens(tokens.accessToken, tokens.refreshToken)
      .then(() => {
        toast.success(t("auth.oauth.success"))
        // `replace` also removes the tokens from the browser history.
        navigate("/dashboard", { replace: true })
      })
      .catch((err: unknown) => setError(getErrorMessage(err)))
  }, [tokens, loginWithTokens, navigate, t])

  const message = tokens ? error : t("auth.oauth.missingTokens")
  if (message) {
    return (
      <AuthShell title={t("auth.oauth.failedTitle")}>
        <p className="text-sm text-muted-foreground">{message}</p>
        <GradientButton asChild className="h-10 w-full">
          <Link to="/login">{t("common.backToLogin")}</Link>
        </GradientButton>
      </AuthShell>
    )
  }

  return <LoadingSpinner fullPage label={t("auth.oauth.signingIn")} className="min-h-screen" />
}
