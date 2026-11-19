import { QuickHelp } from "@/components/help/QuickHelp";
import { Kolam } from "@/components/motion/Kolam";
import { RiseWords } from "@/components/motion/Reveal";
import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Logo } from "@/components/layout/Logo";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { useAuth } from "@/context/AuthContext";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SITE_LINKS = [
  { to: "/", label: "Home" },
  { to: "/how-it-works", label: "How it works" },
  { to: "/about", label: "Why Virundhu" },
  { to: "/compare", label: "Compare" },
  { to: "/whats-next", label: "What's next" },
  { to: "/pricing", label: "Pricing" },
  { to: "/contact", label: "Contact" },
] as const;

/** Header + footer shared by every public page. */
export function SiteLayout() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const company = usePublicConfig().data?.company;
  const { user, logout } = useAuth();
  const appHome = user?.is_superadmin ? "/app/admin" : "/app";
  async function signOut() { await logout(); setOpen(false); }
  useEffect(() => { window.scrollTo({ top: 0 }); }, [pathname]);

  return (
    <div className="min-h-dvh">
      <header className="kolam-dark sticky top-0 z-40 border-b border-white/10 text-jasmine">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3.5 sm:px-8">
          <Link to="/" aria-label="Virundhu home" onClick={() => setOpen(false)}><Logo onDark /></Link>
          <nav className="hidden items-center gap-1 lg:flex" aria-label="Site">
            {SITE_LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} end
                className={({ isActive }) => cn("whitespace-nowrap rounded-[10px] px-3 py-2 text-[0.95rem] font-medium transition-colors",
                  isActive ? "bg-white/10 text-white" : "text-mist hover:text-white")}>
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            {user ? (
              <>
                <button onClick={() => void signOut()} className={cn(buttonVariants({ variant: "ghostDark", size: "sm" }), "hidden sm:inline-flex cursor-pointer")}>Sign out</button>
                <Link to={appHome} className={cn(buttonVariants({ size: "sm" }), "hidden sm:inline-flex")}>Open my dashboard</Link>
              </>
            ) : (
              <>
                <Link to="/login" className={cn(buttonVariants({ variant: "ghostDark", size: "sm" }), "hidden sm:inline-flex")}>Sign in</Link>
                <Link to="/register" className={cn(buttonVariants({ size: "sm" }), "hidden sm:inline-flex")}>Start free trial</Link>
              </>
            )}
            <button onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-label={open ? "Close menu" : "Open menu"}
              className="rounded-[10px] p-2 text-jasmine hover:bg-white/10 lg:hidden cursor-pointer">
              {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
        {open ? (
          <nav className="border-t border-white/10 px-5 pb-5 pt-2 lg:hidden" aria-label="Site, mobile">
            {SITE_LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} end onClick={() => setOpen(false)}
                className={({ isActive }) => cn("block rounded-[10px] px-3 py-3 text-lg font-medium", isActive ? "bg-white/10 text-white" : "text-mist")}>
                {l.label}
              </NavLink>
            ))}
            <div className="mt-3 grid grid-cols-2 gap-2">
              {user ? (
                <>
                  <button onClick={() => void signOut()} className={cn(buttonVariants({ variant: "outlineDark" }), "cursor-pointer")}>Sign out</button>
                  <Link to={appHome} onClick={() => setOpen(false)} className={buttonVariants()}>Open my dashboard</Link>
                </>
              ) : (
                <>
                  <Link to="/login" onClick={() => setOpen(false)} className={buttonVariants({ variant: "outlineDark" })}>Sign in</Link>
                  <Link to="/register" onClick={() => setOpen(false)} className={buttonVariants()}>Start free trial</Link>
                </>
              )}
            </div>
          </nav>
        ) : null}
      </header>

      <main><Outlet /></main>
      <QuickHelp signedIn={false} />
      <WhatsAppButton phone={company?.phone} />

      <footer className="kolam-dark text-mist">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 py-12 sm:px-8 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div>
            <Logo onDark />
            <p className="mt-3 max-w-sm">Every guest, heard. Review care for restaurants and cloud kitchens, made in Tamil Nadu.</p>
            {company?.email ? <p className="mt-3"><a href={`mailto:${company.email}`} className="hover:text-white">{company.email}</a></p> : null}
            {company?.demo_email ? <p><a href={`mailto:${company.demo_email}`} className="hover:text-white">{company.demo_email}</a> (demos)</p> : null}
            {company?.address ? <p className="mt-2">{company.address}</p> : null}
            {company?.phone ? <p><a href={`tel:${company.phone.replace(/\s/g, "")}`} className="hover:text-white">{company.phone}</a></p> : null}
          </div>
          <div>
            <p className="font-semibold text-jasmine">Explore</p>
            <ul className="mt-3 space-y-2">
              {SITE_LINKS.map((l) => <li key={l.to}><Link to={l.to} className="hover:text-white">{l.label}</Link></li>)}
            </ul>
          </div>
          <div>
            <p className="font-semibold text-jasmine">Get started</p>
            <ul className="mt-3 space-y-2">
              <li><Link to="/register" className="hover:text-white">Start free trial</Link></li>
              <li><Link to="/login" className="hover:text-white">Sign in</Link></li>
              <li><Link to="/contact" className="hover:text-white">Book a 10-minute demo</Link></li>
            </ul>
          </div>
          <div>
            <p className="font-semibold text-jasmine">Trust</p>
            <ul className="mt-3 space-y-2">
              <li><Link to="/security" className="hover:text-white">Security</Link></li>
              <li><Link to="/privacy" className="hover:text-white">Privacy Policy</Link></li>
              <li><Link to="/terms" className="hover:text-white">Terms of Service</Link></li>
              <li><Link to="/data-processing" className="hover:text-white">Data processing</Link></li>
              <li><Link to="/refunds" className="hover:text-white">Refunds and cancellation</Link></li>
            </ul>
          </div>
        </div>
        <p className="mx-auto max-w-7xl border-t border-white/10 px-5 py-5 text-sm sm:px-8">
          © 2026 {company?.name ?? "Virundhu"}. All rights reserved.
          {company?.parent ? <> {company.name ?? "Virundhu"} is a product of {company.parent}, our parent company. We make software for restaurants; we don't run restaurants.</> : null}
        </p>
      </footer>
    </div>
  );
}

/** Dark band that opens every inner page. */
export function PageHero({ title, intro, children }: { title: string; intro: string; children?: React.ReactNode }) {
  return (
    <section className="kolam-dark relative overflow-hidden text-jasmine">
      <div aria-hidden="true" className="pointer-events-none absolute -right-32 -top-40 h-[420px] w-[420px] rounded-full bg-turmeric/15 blur-[110px]" />
      <Kolam size={420} className="pointer-events-none absolute -right-20 -top-16 hidden opacity-30 md:block" delay={0.3} />
      <div className="relative mx-auto max-w-7xl px-5 pb-16 pt-14 sm:px-8 lg:pb-20 lg:pt-20">
        <h1 className="type-hero max-w-4xl"><RiseWords text={title} /></h1>
        <p className="type-lead mt-5 max-w-2xl text-mist animate-rise [animation-delay:450ms]">{intro}</p>
        {children}
      </div>
    </section>
  );
}

/** Turmeric closing band with the two actions. */
/** Floating "Chat on WhatsApp" button, shown once CONTACT_PHONE is set. */
export function WhatsAppButton({ phone }: { phone: string | null | undefined }) {
  if (!phone) return null;
  const digits = phone.replace(/[^0-9]/g, "");
  const number = digits.length === 10 ? `91${digits}` : digits;
  const text = encodeURIComponent("Hi, I'd like to know more about Virundhu for my restaurant.");
  return (
    <a href={`https://wa.me/${number}?text=${text}`} target="_blank" rel="noreferrer" aria-label="Chat with us on WhatsApp"
      className="fixed bottom-20 right-4 z-50 inline-flex items-center gap-2 rounded-full bg-[#1F8F4E] px-4 py-3 font-semibold text-white shadow-[0_8px_24px_rgba(12,59,46,0.25)] hover:bg-[#187a41]">
      <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 fill-current"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.7.8-.8 1-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.7-1.3a.4.4 0 0 0 0-.4l-.8-1.9c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.1.6a2.7 2.7 0 0 0 1.8-1.2 2.2 2.2 0 0 0 .1-1.2c0-.1-.2-.2-.4-.3Z" /></svg>
      <span className="hidden sm:inline">Chat with us</span>
    </a>
  );
}

export function ClosingCta({ title = "Your guests are already talking. Start listening this week." }: { title?: string }) {
  return (
    <section className="bg-turmeric">
      <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 px-5 py-14 sm:px-8 md:flex-row md:items-center">
        <h2 className="type-section max-w-2xl text-night">{title}</h2>
        <div className="flex flex-wrap gap-3">
          <Link to="/register" className={buttonVariants({ variant: "dark", size: "lg" })}>Start 14-day free trial</Link>
          <Link to="/contact" className={cn(buttonVariants({ variant: "outline", size: "lg" }), "border-night/30 bg-transparent")}>Book a demo</Link>
        </div>
      </div>
    </section>
  );
}
