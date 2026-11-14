import { Languages } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { LANGUAGES } from "@/i18n"
import { cn } from "@/lib/utils"

interface LanguageSwitcherProps {
  className?: string
}

/** Dropdown to switch the app language. The choice is remembered on this browser. */
export function LanguageSwitcher({ className }: LanguageSwitcherProps) {
  const { t, i18n } = useTranslation()

  return (
    <Select value={i18n.resolvedLanguage} onValueChange={(code) => void i18n.changeLanguage(code)}>
      <SelectTrigger className={cn("w-auto gap-2 rounded-full", className)} aria-label={t("common.language")}>
        <Languages className="size-4 text-muted-foreground" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {LANGUAGES.map((lang) => (
          <SelectItem key={lang.code} value={lang.code} lang={lang.code}>
            {lang.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
