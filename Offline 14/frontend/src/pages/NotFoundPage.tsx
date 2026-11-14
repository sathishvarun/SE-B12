import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { GradientButton, MeshBackground, PageWrapper } from "@/components/common"

export default function NotFoundPage() {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <MeshBackground />
      <PageWrapper className="items-center text-center">
        <p className="bg-gradient-to-r from-violet-500 via-pink-500 to-orange-400 bg-clip-text text-8xl font-black text-transparent">
          404
        </p>
        <h1 className="text-2xl font-bold tracking-tight">{t("notFound.title")}</h1>
        <p className="text-muted-foreground">{t("notFound.text")}</p>
        <GradientButton asChild>
          <Link to="/dashboard">{t("notFound.back")}</Link>
        </GradientButton>
      </PageWrapper>
    </div>
  )
}
