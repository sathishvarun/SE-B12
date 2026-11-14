import { useTranslation } from "react-i18next"
import { Suspense, useState } from "react"
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom"
import { AnimatePresence, motion } from "framer-motion"
import { toast } from "sonner"
import { CreditCard, Crown, Hand, LogOut, Menu, Settings, Shield, Sparkles, User, X } from "lucide-react"

import { LoadingSpinner } from "@/components/common"
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ADMIN_SECTION, MAIN_SECTIONS, type Section } from "@/lib/sections"
import i18n from "@/i18n"
import { cn } from "@/lib/utils"
import { getErrorMessage } from "@/services/api"
import type { Plan } from "@/types"

interface AppLayoutProps {
  /** Show the Admin link (`user.is_admin`). */
  isAdmin?: boolean
  /** Name/email shown in the user menu. */
  userName?: string
  userEmail?: string
  /** Current plan: shows a badge, and an "Upgrade" link on the free plan. */
  plan?: Plan
  /** Called from the user menu's "Log out" item. */
  onLogout?: () => Promise<void>
}

function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return i18n.t("layout.goodMorning")
  if (hour < 17) return i18n.t("layout.goodAfternoon")
  return i18n.t("layout.goodEvening")
}

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
}

function SidebarNav({ items, onNavigate }: { items: Section[]; onNavigate?: () => void }) {
  const { t } = useTranslation()
  return (
    <nav className="flex flex-col gap-1" aria-label={t("nav.main")}>
      {items.map(({ path, label, icon: Icon, tone }) => (
        <NavLink
          key={path}
          to={path}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "group flex items-center gap-3 rounded-2xl px-2.5 py-2 text-[0.95rem] font-semibold transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring",
              isActive ? cn(tone.soft, tone.text, "font-extrabold") : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )
          }
        >
          <span
            className={cn(
              "flex size-8 items-center justify-center rounded-xl transition-transform group-hover:scale-105",
              tone.tile,
            )}
          >
            <Icon className="size-4" />
          </span>
          {label}
        </NavLink>
      ))}
    </nav>
  )
}

function Brand() {
  const { t } = useTranslation()
  return (
    <div className="flex items-center gap-2.5 px-2 py-4">
      <div className="flex size-10 rotate-[-6deg] items-center justify-center rounded-2xl bg-primary text-lg font-black text-primary-foreground shadow-[0_3px_0_0_oklch(0.42_0.2_292)]">
        S
      </div>
      <div className="leading-tight">
        <span className="block text-lg font-black tracking-tight">Sathish CRM</span>
        <span className="block text-xs font-semibold text-muted-foreground">{t("layout.tagline")}</span>
      </div>
    </div>
  )
}

/** Friendly nudge at the bottom of the sidebar for free-plan users. */
function UpgradeCard({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation()
  return (
    <div className="mt-auto rounded-3xl bg-gradient-to-br from-violet-100 via-pink-50 to-orange-100 p-4">
      <div className="flex size-9 items-center justify-center rounded-xl bg-white text-violet-700 shadow-sm">
        <Sparkles className="size-4" />
      </div>
      <p className="mt-3 font-extrabold">{t("layout.goPro")}</p>
      <p className="text-sm text-muted-foreground">{t("layout.goProText")}</p>
      <Button asChild size="sm" className="mt-3 w-full rounded-full font-bold">
        <Link to="/billing" onClick={onNavigate}>
          {t("layout.upgrade")}
        </Link>
      </Button>
    </div>
  )
}

/** Shell for all logged-in pages: sidebar + top bar + routed content via <Outlet />. */
function PlanBadge({ plan }: { plan: Plan }) {
  const { t } = useTranslation()
  return plan === "pro" ? (
    <Badge className="gap-1 bg-amber-100 font-bold text-amber-800">
      <Crown /> Pro
    </Badge>
  ) : (
    <Badge variant="secondary">{t("common.free")}</Badge>
  )
}

export function AppLayout({
  isAdmin = false,
  userName: userNameProp,
  userEmail = "",
  plan,
  onLogout,
}: AppLayoutProps) {
  const { t } = useTranslation()
  const userName = userNameProp ?? t("layout.guestUser")
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigate = useNavigate()
  const items = isAdmin ? [...MAIN_SECTIONS, ADMIN_SECTION] : MAIN_SECTIONS
  const closeMobile = () => setMobileOpen(false)

  const handleLogout = async () => {
    try {
      await onLogout?.()
      toast.success(t("layout.loggedOut"))
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      navigate("/login", { replace: true })
    }
  }

  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col gap-4 border-r bg-card p-3 md:flex">
        <Brand />
        <SidebarNav items={items} />
        {plan === "free" && <UpgradeCard />}
      </aside>

      {/* Mobile sidebar (slide-in drawer) */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              key="backdrop"
              className="fixed inset-0 z-40 bg-black/40 md:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={closeMobile}
            />
            <motion.aside
              key="drawer"
              className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col gap-4 border-r bg-card p-3 md:hidden"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "tween", duration: 0.2 }}
            >
              <div className="flex items-center justify-between">
                <Brand />
                <Button variant="ghost" size="icon" onClick={closeMobile} aria-label={t("layout.closeMenu")}>
                  <X className="size-5" />
                </Button>
              </div>
              <SidebarNav items={items} onNavigate={closeMobile} />
              {plan === "free" && <UpgradeCard onNavigate={closeMobile} />}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 bg-background/80 px-4 backdrop-blur md:px-8">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label={t("layout.openMenu")}
          >
            <Menu className="size-5" />
          </Button>
          <p className="hidden text-sm font-semibold text-muted-foreground md:block">
            {greeting()}, <span className="text-foreground">{userName.split(" ")[0]}</span>{" "}
            <Hand aria-hidden="true" className="inline size-4 -rotate-12 align-[-2px] text-violet-600" />
          </p>
          <div className="flex-1" />
          <LanguageSwitcher />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="gap-2 rounded-full px-2" aria-label={t("layout.userMenu")}>
                <Avatar className="size-8">
                  <AvatarFallback className="bg-teal-100 font-bold text-teal-700">{initials(userName)}</AvatarFallback>
                </Avatar>
                <span className="hidden text-sm font-medium sm:inline">{userName}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="flex flex-col">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate">{userName}</span>
                    {plan && <PlanBadge plan={plan} />}
                  </div>
                  {userEmail && (
                    <span className="truncate text-xs font-normal text-muted-foreground">{userEmail}</span>
                  )}
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => navigate("/profile")}>
                <User className="size-4" /> {t("nav.profile")}
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => navigate("/settings")}>
                <Settings className="size-4" /> {t("nav.settings")}
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => navigate("/billing")}>
                <CreditCard className="size-4" /> {t("nav.billing")}
              </DropdownMenuItem>
              {isAdmin && (
                <DropdownMenuItem onSelect={() => navigate("/admin")}>
                  <Shield className="size-4" /> {t("nav.admin")}
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => void handleLogout()}>
                <LogOut className="size-4" /> {t("layout.logOut")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <main className="flex-1 px-4 pt-2 pb-10 md:px-8">
          {/* Pages are lazy-loaded: keep the sidebar visible while one loads. */}
          <Suspense fallback={<LoadingSpinner fullPage />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  )
}
