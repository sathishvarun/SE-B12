// App-wide translations (English + Tamil) using i18next.
// Components use `const { t } = useTranslation()`; plain functions (hooks, formatters)
// can import `i18n` from here and call `i18n.t(...)`.
import i18n from "i18next"
import { initReactI18next } from "react-i18next"

import { en } from "./locales/en"
import { ta } from "./locales/ta"

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "ta", label: "தமிழ்" },
] as const

export type LanguageCode = (typeof LANGUAGES)[number]["code"]

const STORAGE_KEY = "sathish-crm.language"

function isLanguageCode(value: string | null): value is LanguageCode {
  return LANGUAGES.some((lang) => lang.code === value)
}

/** The language picked last time on this browser, or English. */
function savedLanguage(): LanguageCode {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    if (isLanguageCode(value)) return value
  } catch {
    // Storage blocked (private mode etc.): just use the default.
  }
  return "en"
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ta: { translation: ta } },
  lng: savedLanguage(),
  fallbackLng: "en",
  initAsync: false,
  // React already escapes text, so i18next doesn't need to.
  interpolation: { escapeValue: false },
})

document.documentElement.lang = i18n.language

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng
  try {
    localStorage.setItem(STORAGE_KEY, lng)
  } catch {
    // Not fatal: the choice just won't be remembered.
  }
})

/** Locale for Intl date and number formatting, e.g. "ta-IN" when Tamil is selected. */
export function formatLocale(): string {
  return i18n.language === "ta" ? "ta-IN" : "en-IN"
}

export default i18n
