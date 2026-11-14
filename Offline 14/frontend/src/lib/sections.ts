import i18n from "@/i18n"
import {
  Briefcase,
  CheckSquare,
  CreditCard,
  LayoutDashboard,
  Settings,
  Shield,
  Target,
  User,
  Users,
  type LucideIcon,
} from "lucide-react"

/**
 * Each part of the app has its own friendly colour.
 * Class names are written out in full so Tailwind can find them.
 */
export interface SectionTone {
  /** Small rounded icon square: pastel background + strong icon colour. */
  tile: string
  /** Very soft background for highlighted areas (active nav item, stat cards). */
  soft: string
  /** Text colour for the section's accent. */
  text: string
  /** Border that matches the soft background. */
  border: string
}

export interface Section {
  path: string
  label: string
  icon: LucideIcon
  tone: SectionTone
}

export const TONES = {
  grape: {
    tile: "bg-violet-100 text-violet-700",
    soft: "bg-violet-50",
    text: "text-violet-700",
    border: "border-violet-100",
  },
  mint: {
    tile: "bg-emerald-100 text-emerald-700",
    soft: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-100",
  },
  peach: {
    tile: "bg-orange-100 text-orange-700",
    soft: "bg-orange-50",
    text: "text-orange-700",
    border: "border-orange-100",
  },
  sky: {
    tile: "bg-sky-100 text-sky-700",
    soft: "bg-sky-50",
    text: "text-sky-700",
    border: "border-sky-100",
  },
  sun: {
    tile: "bg-amber-100 text-amber-700",
    soft: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-100",
  },
  pink: {
    tile: "bg-pink-100 text-pink-700",
    soft: "bg-pink-50",
    text: "text-pink-700",
    border: "border-pink-100",
  },
  rose: {
    tile: "bg-rose-100 text-rose-700",
    soft: "bg-rose-50",
    text: "text-rose-700",
    border: "border-rose-100",
  },
  teal: {
    tile: "bg-teal-100 text-teal-700",
    soft: "bg-teal-50",
    text: "text-teal-700",
    border: "border-teal-100",
  },
} satisfies Record<string, SectionTone>

export type ToneName = keyof typeof TONES

// Labels are getters so they always use the current language.
/** Main sidebar sections, in display order. */
export const MAIN_SECTIONS: Section[] = [
  { path: "/dashboard", get label() { return i18n.t("nav.dashboard") }, icon: LayoutDashboard, tone: TONES.grape },
  { path: "/contacts", get label() { return i18n.t("nav.contacts") }, icon: Users, tone: TONES.mint },
  { path: "/leads", get label() { return i18n.t("nav.leads") }, icon: Target, tone: TONES.peach },
  { path: "/deals", get label() { return i18n.t("nav.deals") }, icon: Briefcase, tone: TONES.sky },
  { path: "/tasks", get label() { return i18n.t("nav.tasks") }, icon: CheckSquare, tone: TONES.sun },
  { path: "/settings", get label() { return i18n.t("nav.settings") }, icon: Settings, tone: TONES.pink },
]

export const ADMIN_SECTION: Section = { path: "/admin", get label() { return i18n.t("nav.admin") }, icon: Shield, tone: TONES.rose }

const OTHER_SECTIONS: Section[] = [
  ADMIN_SECTION,
  { path: "/billing", get label() { return i18n.t("nav.billing") }, icon: CreditCard, tone: TONES.pink },
  { path: "/profile", get label() { return i18n.t("nav.profile") }, icon: User, tone: TONES.teal },
]

/** Find the section a URL belongs to (e.g. "/contacts/12/edit" -> Contacts). */
export function sectionForPath(pathname: string): Section | undefined {
  return [...MAIN_SECTIONS, ...OTHER_SECTIONS].find(
    (section) => pathname === section.path || pathname.startsWith(`${section.path}/`),
  )
}
