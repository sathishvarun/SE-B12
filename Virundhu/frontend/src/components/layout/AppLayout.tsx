import { IdleSignOut } from "@/components/layout/IdleSignOut";
import { EasePrompt } from "@/components/feedback/EaseCheck";
import { QuickHelp } from "@/components/help/QuickHelp";
import { useQueryClient } from "@tanstack/react-query";
import { BarChart3, Bell, CreditCard, Inbox, MessageCircleQuestion,
  UtensilsCrossed,
  LifeBuoy, Workflow, LogOut, MapPin, Menu, Plug, Settings, ShieldCheck, Upload,
  LayoutDashboard, MailOpen, Lock, UsersRound, Building2, Users, ScrollText, Mail, LogIn, Quote, Database, MessageSquareHeart, HeartHandshake, IndianRupee, CalendarClock, Gauge, Coins, FileSpreadsheet } from "lucide-react";
import { useEffect, useState } from "react";
import { AnimatePresence, LazyMotion, domMax, m, useReducedMotion } from "motion/react";
import { Link, Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { AdminBell } from "@/components/layout/AdminBell";
import { Logo, LogoMark } from "@/components/layout/Logo";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { useAuth } from "@/context/AuthContext";
import { useOverview } from "@/hooks/useOverview";
import { cn } from "@/lib/utils";
import { useWorkspace } from "@/lib/workspace";
import { viewAs } from "@/services/api";

interface NavItem { to: string; label: string; icon: typeof Inbox; badge?: number; end?: boolean; hint?: string; short?: string }
interface NavGroup { title: string; items: NavItem[] }

function TrialBanner({ endsAt }: { endsAt: string }) {
  const [now] = useState(() => Date.now());
  const days = Math.ceil((new Date(endsAt).getTime() - now) / 86_400_000);
  const ended = days <= 0;
  return (
    <div className={cn("mb-5 flex flex-wrap items-center justify-between gap-3 rounded-[14px] px-4 py-3", ended ? "bg-chilli text-white" : "bg-turmeric/25")}>
      <p className="text-sm font-medium">{ended ? "Your free trial has ended. You can still look around, but adding and replying to reviews is paused." : `Free trial: ${days} day${days === 1 ? "" : "s"} left.`}</p>
      <Link to="/app/billing" className={cn("rounded-full px-3 py-1 text-sm font-bold", ended ? "bg-white text-chilli" : "bg-night text-jasmine")}>Choose a plan</Link>
    </div>
  );
}

/** Signed-in shell. The menu depends on who you are (see lib/workspace.ts). */
export function AppLayout() {
  const { logout, refreshUser } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [moreOpen, setMoreOpen] = useState(false);
  const { pathname } = useLocation();
  const reduce = useReducedMotion();
  const { user, viewing, adminHome, org, outletNames, isOwner } = useWorkspace();
  const { data } = useOverview(undefined, !adminHome && !user?.organization?.locked_since);
  const urgent = data?.kpis.urgent_pending ?? 0;

  function stopViewing() {
    viewAs.set(null);
    qc.clear();
    navigate("/app/admin");
  }
  async function signOut() {
    await logout();
    navigate("/login", { replace: true });
  }

  // Grouped by how often owners use them: daily work first, then insights, then setup, then account.
  const groups: NavGroup[] = adminHome
    ? [
        { title: "Overview", items: [
          { to: "/app/admin", label: "Today", icon: LayoutDashboard, end: true },
          { to: "/app/admin/autopilot", label: "Autopilot", icon: Workflow, hint: "Your AI agents at work" },
        ] },
        { title: "Money", items: [
          { to: "/app/admin/money", label: "Payments", icon: IndianRupee, hint: "Per day, per week, refunds" },
          { to: "/app/admin/renewals", label: "Renewals", icon: CalendarClock, hint: "Revenue and plans due" },
          { to: "/app/admin/accounts", label: "Accounts and audit", icon: FileSpreadsheet, hint: "Excel for your auditor and GST" },
          { to: "/app/admin/tokens", label: "AI tokens", icon: Gauge, hint: "Total tokens and AI cost" },
          { to: "/app/admin/tokens-by-restaurant", label: "Tokens by restaurant", icon: Coins, hint: "Each restaurant's AI use and cost" },
        ] },
        { title: "Customers", items: [
          { to: "/app/admin/restaurants", label: "Restaurants", icon: Building2 },
          { to: "/app/admin/users", label: "Users", icon: Users },
          { to: "/app/admin/leads", label: "Demo requests", icon: Inbox },
        ] },
        { title: "Help desk", items: [
          { to: "/app/admin/support", label: "Support", icon: LifeBuoy },
          { to: "/app/admin/feedback", label: "Feedback", icon: HeartHandshake, hint: "Ideas and ease of use" },
          { to: "/app/admin/testimonials", label: "Testimonials", icon: Quote },
          { to: "/app/admin/mailbox", label: "Mailbox", icon: MailOpen },
        ] },
        { title: "Logs", items: [
          { to: "/app/admin/activity", label: "Activity", icon: ScrollText },
          { to: "/app/admin/emails", label: "Emails sent", icon: Mail },
          { to: "/app/admin/signins", label: "Sign-ins", icon: LogIn },
        ] },
        { title: "System", items: [{ to: "/app/admin/data", label: "Data and backups", icon: Database }] },
      ]
    : [
        { title: "Every day", items: [
          { to: "/app", label: "Dashboard", icon: BarChart3, end: true, hint: "Today at a glance" },
          { to: "/app/ai-staff", label: "Your AI staff", icon: UsersRound, hint: "What your AI team did and today's 3 moves" },
          { to: "/app/inbox", label: "Inbox", icon: Inbox, badge: urgent, hint: "Reviews to reply" },
          { to: "/app/import", label: "Add reviews", icon: Upload, hint: "Zomato, Swiggy, screenshots" },
          { to: "/app/alerts", label: "Alerts", icon: Bell, hint: "Problems that need you" },
        ] },
        { title: "Understand your guests", items: [
          { to: "/app/insights", label: "Dishes and staff", icon: UtensilsCrossed, hint: "What guests praise or complain about" },
          { to: "/app/ask", label: "Ask Virundhu", icon: MessageCircleQuestion, hint: "Ask questions about your reviews" },
        ] },
        { title: "Set up", items: [
          { to: "/app/connections", label: "Connections", icon: Plug, hint: "Google, QR codes, website" },
          ...(isOwner ? [{ to: "/app/automation", label: "Automation", icon: Workflow, hint: "Automatic replies and alerts" }] : []),
        ] },
        { title: "Account", items: [
          ...(isOwner ? [{ to: "/app/billing", label: "Plan and billing", icon: CreditCard }] : []),
          { to: "/app/usage", label: "AI usage", icon: Gauge, hint: "Tokens the AI used for you" },
          { to: "/app/settings", label: "Settings", icon: Settings },
          { to: "/app/support", label: "Help and support", icon: LifeBuoy },
          { to: "/app/feedback", label: "Share feedback", icon: MessageSquareHeart, hint: "Ideas, problems, how easy it is" },
        ] },
      ];
  const items = groups.flatMap((g) => g.items);
  const mobileMain = adminHome ? [0, 2, 7, 10].map((i) => items[i]).filter((x): x is NavItem => Boolean(x)) : items.slice(0, 4);
  const bell = adminHome ? <AdminBell align="left" /> : <NotificationBell onDark align="left" />;
  const trialEnds = !viewing && user?.organization?.plan === "trial" && !user.organization.is_demo ? user.organization.trial_ends_at : null;
  // Unpaid: the account stays signed in, but only Plan and billing (and Help) open until the payment lands.
  const lockedSince = !viewing && !adminHome ? (user?.organization?.locked_since ?? null) : null;
  const payPage = isOwner ? "/app/billing" : "/app/support";
  const isLocked = (to: string) => Boolean(lockedSince) && !["/app/billing", "/app/support"].some((o) => to.startsWith(o));
  const goPay = () => { setMoreOpen(false); navigate(payPage); };
  // The plan can run out while the app is open: the first refused call (402) refreshes the account and locks the menus.
  useEffect(() => {
    const onLocked = () => { void refreshUser(); };
    window.addEventListener("virundhu:locked", onLocked);
    return () => window.removeEventListener("virundhu:locked", onLocked);
  }, [refreshUser]);

  return (
    <LazyMotion features={domMax}>
    <div className="min-h-dvh lg:grid lg:grid-cols-[264px_minmax(0,1fr)]">
      <aside className="kolam-dark sticky top-0 z-40 hidden h-dvh flex-col px-4 py-6 text-jasmine lg:flex">
        <div className="flex items-center justify-between px-2">
          <Link to={adminHome ? "/app/admin" : "/app"}><Logo onDark /></Link>
          {bell}
        </div>
        <p className="mt-5 px-3 text-xs font-semibold text-turmeric">{adminHome ? "Platform admin" : org?.name}</p>
        <nav className="-mx-1 mt-3 min-h-0 flex-1 overflow-y-auto px-1 pb-2" aria-label="Main">
          {groups.map((g) => (
            <div key={g.title} className="mb-3">
              {g.title ? <p className="mb-1 px-3 text-[0.72rem] font-semibold text-mist/70">{g.title}</p> : null}
              <div className="flex flex-col gap-0.5">
                {g.items.map(({ to, label, icon: Icon, badge, end, hint }) => isLocked(to) ? (
                  <button key={to} onClick={goPay} title="Locked until the plan is paid" aria-disabled="true"
                    className="flex w-full cursor-pointer items-center gap-3 rounded-[12px] px-3 py-2 text-left font-medium text-mist/45 hover:bg-white/[0.04]">
                    <Icon className="h-[19px] w-[19px]" strokeWidth={1.9} />
                    <span className="flex-1">{label}</span>
                    <Lock className="h-3.5 w-3.5" aria-label="Locked" />
                  </button>
                ) : (
                  <NavLink key={to} to={to} end={end} title={hint}
                    className={({ isActive }) => cn("group relative flex items-center gap-3 rounded-[12px] px-3 py-2 font-medium text-mist transition-colors hover:bg-white/[0.07] hover:text-white", isActive && "text-white")}>
                    {({ isActive }) => (
                      <>
                        {isActive ? <m.span layoutId="nav-pill" className="absolute inset-0 rounded-[12px] bg-white/[0.1]" transition={{ type: "spring", stiffness: 420, damping: 34 }}>
                          <span className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-turmeric" />
                        </m.span> : null}
                        <Icon className={cn("relative h-[19px] w-[19px] transition-transform group-hover:scale-110", isActive && "text-turmeric")} strokeWidth={1.9} />
                        <span className="relative flex-1">{label}</span>
                        {badge ? <span className="relative rounded-full bg-chilli px-2 text-xs font-bold leading-5 text-white">{badge}</span> : null}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        {viewing ? (
          <button onClick={stopViewing} className="mt-2 w-full rounded-[12px] bg-turmeric px-3 py-2.5 text-left text-sm font-bold text-night cursor-pointer">
            <ShieldCheck className="mb-1 h-4 w-4" />Back to Admin console
          </button>
        ) : null}
        {org?.is_demo ? (
          <div className="mt-4 rounded-[14px] bg-turmeric/15 p-3.5 text-sm">
            <p className="font-semibold text-turmeric">Demo restaurant (sample data)</p>
            <p className="mt-1 text-mist">Nothing here is a real review. Changes are switched off.</p>
            <Link to="/register" className="mt-2 inline-block font-semibold text-white underline decoration-turmeric underline-offset-4">Start your own trial</Link>
          </div>
        ) : null}
        </nav>
        <div className="shrink-0 border-t border-white/10 pt-4">
          <div className="flex items-center gap-3 px-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-turmeric font-display font-bold text-night">{(user?.full_name ?? "?").charAt(0).toUpperCase()}</span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{user?.full_name}</p>
              <p className="truncate text-xs text-mist">{adminHome ? "Virundhu admin" : user?.role === "owner" ? "Owner" : user?.role === "manager" ? "Manager" : "Staff"}{outletNames ? `, ${outletNames.join(", ")}` : ""}</p>
            </div>
          </div>
          <button onClick={signOut} className="mt-3 flex w-full items-center justify-center gap-2 rounded-[12px] border border-white/15 px-3 py-2 text-sm font-semibold text-jasmine hover:border-chilli hover:bg-chilli/20 cursor-pointer"><LogOut className="h-4 w-4" /> Sign out</button>
        </div>
      </aside>

      <header className="kolam-dark sticky top-0 z-30 flex items-center justify-between px-4 py-3 text-jasmine lg:hidden">
        <Link to={adminHome ? "/app/admin" : "/app"} className="flex items-center gap-2"><LogoMark onDark className="h-8 w-8" /><span className="font-display text-lg font-bold">Virundhu</span></Link>
        <div className="flex items-center gap-1">{adminHome ? <AdminBell /> : <NotificationBell onDark />}
          <button onClick={signOut} aria-label="Sign out" className="rounded-[10px] p-2 text-mist hover:bg-white/10 hover:text-white cursor-pointer"><LogOut className="h-5 w-5" /></button></div>
      </header>

      <main className="relative min-w-0 px-4 pb-28 pt-6 sm:px-6 lg:px-10 lg:pb-12 lg:pt-9">
        {viewing ? (
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-[14px] bg-night px-4 py-3 text-jasmine">
            <p className="text-sm"><span className="font-semibold text-turmeric">Admin view:</span> you're looking at <span className="font-semibold">{viewing.name}</span> exactly as its owner sees it.</p>
            <button onClick={stopViewing} className="rounded-full bg-turmeric px-3 py-1 text-sm font-bold text-night cursor-pointer">Back to Admin console</button>
          </div>
        ) : null}
        {outletNames ? (
          <p className="mb-5 flex items-center gap-2 rounded-[14px] bg-sky-soft px-4 py-2.5 text-sm font-medium text-[#1f5f9e]">
            <MapPin className="h-4 w-4" /> You see reviews for {outletNames.join(", ")} only.
          </p>
        ) : null}
        {org?.is_demo ? <p className="mb-5 rounded-[12px] bg-turmeric/25 px-4 py-2.5 text-sm font-medium lg:hidden">Demo restaurant: everything here is sample data.</p> : null}
        {lockedSince ? <SuspendedBanner since={lockedSince} isOwner={isOwner} /> : trialEnds ? <TrialBanner endsAt={trialEnds} /> : null}
        {lockedSince && isLocked(pathname) ? <Navigate to={payPage} replace /> : null}
        <AnimatePresence mode="wait" initial={false}>
          <m.div key={pathname} initial={reduce ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={reduce ? undefined : { opacity: 0, y: -6 }}
            transition={{ duration: 0.28, ease: [0.2, 0.8, 0.2, 1] }}>
            <Outlet />
            <IdleSignOut />
            {!adminHome ? <EasePrompt /> : null}
            {!adminHome ? <QuickHelp signedIn /> : null}
          </m.div>
        </AnimatePresence>
      </main>

      {moreOpen ? (
        <div className="fixed inset-0 z-[70] bg-night/60 lg:hidden" onClick={() => setMoreOpen(false)}>
          <div className="absolute inset-x-3 bottom-20 max-h-[75dvh] overflow-y-auto rounded-[18px] bg-night-2 p-2 text-jasmine" onClick={(e) => e.stopPropagation()}>
            {groups.map((g) => {
              const rest = g.items.filter((it) => !mobileMain.includes(it));
              return rest.length ? (
                <div key={g.title} className="mb-1">
                  <p className="px-4 pb-1 pt-2 text-[0.72rem] font-semibold text-mist/70">{g.title}</p>
                  {rest.map(({ to, label, icon: Icon, hint }) => isLocked(to) ? (
                    <button key={to} onClick={goPay} aria-disabled="true" className="flex w-full cursor-pointer items-center gap-3 rounded-[12px] px-4 py-2.5 text-left font-medium text-mist/45">
                      <Icon className="h-5 w-5 shrink-0" /><span className="flex-1">{label}</span><Lock className="h-4 w-4" aria-label="Locked" />
                    </button>
                  ) : (
                    <NavLink key={to} to={to} onClick={() => setMoreOpen(false)} className="flex items-center gap-3 rounded-[12px] px-4 py-2.5 font-medium hover:bg-white/10">
                      <Icon className="h-5 w-5 shrink-0 text-turmeric" /><span>{label}{hint ? <span className="block text-xs font-normal text-mist">{hint}</span> : null}</span>
                    </NavLink>
                  ))}
                </div>
              ) : null;
            })}
            {viewing ? <button onClick={stopViewing} className="flex w-full items-center gap-3 rounded-[12px] px-4 py-3 font-medium hover:bg-white/10 cursor-pointer"><ShieldCheck className="h-5 w-5 text-turmeric" />Back to Admin console</button> : null}
            <button onClick={signOut} className="flex w-full items-center gap-3 rounded-[12px] px-4 py-3 font-medium text-mist hover:bg-white/10 cursor-pointer"><LogOut className="h-5 w-5" />Sign out</button>
          </div>
        </div>
      ) : null}
      <nav className={cn("fixed inset-x-0 bottom-0 z-30 grid border-t border-white/10 bg-night/95 text-jasmine backdrop-blur lg:hidden", "grid-cols-5")} aria-label="Main">
        {mobileMain.map(({ to, label, short, icon: Icon, badge, end }) => isLocked(to) ? (
          <button key={to} onClick={goPay} aria-disabled="true" className="relative flex cursor-pointer flex-col items-center gap-1 py-2.5 text-[0.72rem] text-mist/40">
            <Icon className="h-5 w-5" strokeWidth={1.9} />{short ?? label}
            <Lock className="absolute right-[26%] top-1.5 h-3 w-3" aria-label="Locked" />
          </button>
        ) : (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => cn("relative flex flex-col items-center gap-1 py-2.5 text-[0.72rem] text-mist", isActive && "font-semibold text-turmeric")}>
            <Icon className="h-5 w-5" strokeWidth={1.9} />{short ?? label}
            {badge ? <span className="absolute right-[24%] top-1.5 min-w-4 rounded-full bg-chilli px-1 text-[0.65rem] font-bold leading-4 text-white">{badge}</span> : null}
          </NavLink>
        ))}
        <button onClick={() => setMoreOpen((o) => !o)} className="flex flex-col items-center gap-1 py-2.5 text-[0.72rem] text-mist cursor-pointer" aria-expanded={moreOpen}><Menu className="h-5 w-5" strokeWidth={1.9} />More</button>
      </nav>
    </div>
    </LazyMotion>
  );
}

function SuspendedBanner({ since, isOwner }: { since: string; isOwner: boolean }) {
  const navigate = useNavigate();
  const toPlans = () => {
    const el = document.getElementById("choose-plan");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    else navigate("/app/billing");
  };
  const day = new Date(since).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  return (
    <div role="alert" className="mb-5 flex flex-col gap-3 rounded-[18px] border-2 border-chilli bg-chilli/10 p-4 sm:flex-row sm:items-center">
      <Lock className="h-6 w-6 shrink-0 text-chilli" />
      <div className="flex-1">
        <p className="font-display text-lg font-bold text-chilli">Your account is suspended since {day}</p>
        <p className="text-sm text-ink-soft">
          {isOwner
            ? "Your reviews and settings are safe. Pay for a plan below and every menu unlocks straight away."
            : "Your reviews and settings are safe. Ask the restaurant owner to pay for a plan; everything unlocks straight away."}
        </p>
      </div>
      {isOwner ? <button type="button" onClick={toPlans} className="cursor-pointer rounded-[12px] bg-chilli px-4 py-2.5 text-center font-bold text-white hover:opacity-90">Pay and unlock</button> : null}
    </div>
  );
}
