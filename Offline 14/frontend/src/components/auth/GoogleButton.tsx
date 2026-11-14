import { useTranslation } from "react-i18next"
import { motion } from "framer-motion"

import { Button } from "@/components/ui/button"
import { authService } from "@/services/auth"

interface GoogleButtonProps {
  label?: string
}

/** Starts Google sign-in by sending the browser to the backend's /auth/google route. */
export function GoogleButton({ label }: GoogleButtonProps) {
  const { t } = useTranslation()
  const handleClick = () => {
    window.location.href = authService.googleLoginUrl
  }

  return (
    <motion.div whileHover={{ scale: 1.01, y: -1 }} whileTap={{ scale: 0.98 }}>
      <Button type="button" variant="outline" className="h-10 w-full gap-2" onClick={handleClick}>
        <svg viewBox="0 0 24 24" aria-hidden="true" className="size-4">
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.56c2.08-1.92 3.28-4.74 3.28-8.1z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.77c-.98.66-2.23 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.1A6.6 6.6 0 0 1 5.49 12c0-.73.13-1.44.35-2.1V7.06H2.18A11 11 0 0 0 1 12c0 1.78.43 3.45 1.18 4.94l3.66-2.84z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"
          />
        </svg>
        {label ?? t("auth.continueWithGoogle")}
      </Button>
    </motion.div>
  )
}
