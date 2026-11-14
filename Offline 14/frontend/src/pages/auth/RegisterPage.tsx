import { useTranslation } from "react-i18next"
import { Link, useNavigate } from "react-router-dom"

import { AuthShell, OrDivider } from "@/components/auth/AuthShell"
import { GoogleButton } from "@/components/auth/GoogleButton"
import { RegisterForm } from "@/components/auth/RegisterForm"

export default function RegisterPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <AuthShell
      title={t("auth.register.title")}
      subtitle={t("auth.register.subtitle")}
      footer={
        <>
          {t("auth.register.haveAccount")}{" "}
          <Link to="/login" className="font-medium text-violet-600 hover:underline">
            {t("auth.register.logIn")}
          </Link>
        </>
      }
    >
      <RegisterForm onSuccess={() => navigate("/dashboard", { replace: true })} />
      <OrDivider />
      <GoogleButton label={t("auth.signUpWithGoogle")} />
    </AuthShell>
  )
}
