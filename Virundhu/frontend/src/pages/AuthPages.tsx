import { takeNext } from "@/lib/next";
import { AnimatePresence, LazyMotion, domAnimation, m, useReducedMotion } from "motion/react";
import { Kolam } from "@/components/motion/Kolam";
import { RiseWords } from "@/components/motion/Reveal";
import { Building2, Lock, Mail, MapPin, User, Phone } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { LiveBoard } from "@/components/landing/LiveBoard";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/input";
import { Spinner } from "@/components/ui/misc";
import { useAuth } from "@/context/AuthContext";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { cn } from "@/lib/utils";
import { API_URL, api, authApi, errorMessage } from "@/services/api";

/** Split screen: form on the left, the live board on the right (desktop). */
const PANEL_LINES = [
  ["Every review read.", "The urgent ones first."],
  ["Tamil, Tanglish, English.", "Read like a local."],
  ["Hair in the biryani?", "Your phone knows in a minute."],
  ["Happy guests thanked.", "While you cook."],
];

function AuthPanel() {
  const [i, setI] = useState(0);
  const reduce = useReducedMotion();
  useEffect(() => {
    if (reduce) return;
    const t = setInterval(() => setI((x) => (x + 1) % PANEL_LINES.length), 3800);
    return () => clearInterval(t);
  }, [reduce]);
  const [a, b] = PANEL_LINES[i] ?? ["Every review read.", "The urgent ones first."];
  return (
    <aside className="kolam-dark relative hidden overflow-hidden lg:flex lg:flex-col lg:justify-center lg:px-12 xl:px-16">
      <div aria-hidden="true" className="pointer-events-none absolute -right-32 -top-32 h-[420px] w-[420px] rounded-full bg-turmeric/20 blur-[110px]" />
      <div aria-hidden="true" className="pointer-events-none absolute -bottom-40 -left-24 h-[380px] w-[380px] rounded-full bg-lotus/15 blur-[110px]" />
      <Kolam size={560} className="pointer-events-none absolute -bottom-24 -right-24 opacity-30" loop delay={0.4} />
      <div className="relative mx-auto w-full max-w-[540px]">
        <LazyMotion features={domAnimation}>
          <div className="h-[6.5rem]" aria-live="polite">
            <AnimatePresence mode="wait">
              <m.p key={i} className="font-display text-[2.3rem] font-extrabold leading-[1.05] text-jasmine [font-variation-settings:'wdth'_118]"
                initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -18 }} transition={{ duration: 0.45 }}>
                {a}<br /><span className="text-turmeric">{b}</span>
              </m.p>
            </AnimatePresence>
          </div>
          <div className="mt-2 flex gap-1.5" aria-hidden="true">
            {PANEL_LINES.map((_, k) => <span key={k} className={cn("h-1.5 rounded-full transition-all duration-500", k === i ? "w-8 bg-turmeric" : "w-1.5 bg-white/25")} />)}
          </div>
        </LazyMotion>
        <p className="mt-5 text-mist">This is what your team sees: each review sorted the moment it arrives, in any language your guests write in.</p>
        <div className="mt-8"><LiveBoard compact /></div>
      </div>
    </aside>
  );
}

function AuthShell({ title, intro, children, footer }: { title: string; intro: string; children: ReactNode; footer: ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      <div className="relative flex flex-col overflow-hidden px-5 py-6 sm:px-12">
        <Kolam size={300} color="var(--color-turmeric-deep)" className="pointer-events-none absolute -left-24 -top-24 opacity-20 lg:hidden" />
        <Link to="/" aria-label="Virundhu home" className="relative w-fit"><Logo /></Link>
        <div className="relative mx-auto my-auto w-full max-w-[420px] py-10">
          <h1 className="text-[2.6rem] leading-none"><RiseWords text={title} /></h1>
          <p className="mt-3 text-lg text-ink-soft animate-rise [animation-delay:250ms]">{intro}</p>
          <div className="mt-8 animate-rise [animation-delay:380ms]">{children}</div>
          <div className="mt-8 text-ink-soft animate-rise [animation-delay:500ms]">{footer}</div>
        </div>
      </div>
      <AuthPanel />
    </div>
  );
}

interface GoogleId {
  initialize: (o: { client_id: string; callback: (r: { credential: string }) => void; ux_mode?: string; context?: string }) => void;
  renderButton: (el: HTMLElement, o: Record<string, string | number>) => void;
}
type GoogleWindow = Window & { google?: { accounts?: { id?: GoogleId } } };
const GIS_SRC = "https://accounts.google.com/gsi/client";

/** "Continue with Google": Google Identity Services button (needs only the public client ID). */
function GoogleButton() {
  const { data } = usePublicConfig();
  const navigate = useNavigate();
  const box = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const clientId = data?.google_client_id ?? null;

  useEffect(() => {
    const el = box.current;
    if (!clientId || !el) return;
    const render = () => {
      const gid = (window as GoogleWindow).google?.accounts?.id;
      if (!gid) return;
      gid.initialize({
        client_id: clientId,
        ux_mode: "popup",
        callback: ({ credential }) => {
          setError(null);
          api
            .post<{ access_token: string }>("/api/v1/auth/google/id-token", { credential })
            .then((r) => navigate(`/auth/callback#access=${encodeURIComponent(r.data.access_token)}`, { replace: true }))
            .catch((e: unknown) => setError(errorMessage(e)));
        },
      });
      el.innerHTML = "";
      gid.renderButton(el, { theme: "outline", size: "large", text: "continue_with", shape: "rectangular", logo_alignment: "center", width: Math.min(el.offsetWidth || 360, 400) });
    };
    if ((window as GoogleWindow).google?.accounts?.id) { render(); return; }
    let script = document.querySelector<HTMLScriptElement>(`script[src="${GIS_SRC}"]`);
    if (!script) {
      script = document.createElement("script");
      script.src = GIS_SRC; script.async = true; script.defer = true;
      document.head.appendChild(script);
    }
    script.addEventListener("load", render);
    return () => script?.removeEventListener("load", render);
  }, [clientId, navigate]);

  if (!clientId) {
    if (!data?.google_enabled) return null; // hidden until a Google client ID is in .env
    return (
      <>
        <a href={`${API_URL}/api/v1/auth/google`} className="flex h-12 w-full items-center justify-center gap-2 rounded-[12px] border-2 border-line bg-white font-semibold hover:border-night">Continue with Google</a>
        <Divider label="or with email" />
      </>
    );
  }
  return (
    <>
      <div ref={box} className="flex min-h-11 w-full justify-center" aria-label="Continue with Google" />
      {error ? <p role="alert" className="mt-2 text-center text-sm font-medium text-[#b32f12]">{error}</p> : null}
      <p className="mt-2 text-center text-xs text-ink-soft">By continuing with Google you agree to our <Link to="/terms" className="underline">Terms</Link> and <Link to="/privacy" className="underline">Privacy Policy</Link>.</p>
      <Divider label="or with email" />
    </>
  );
}

function Divider({ label }: { label: string }) {
  return (
    <div className="my-6 flex items-center gap-3 text-sm text-ink-soft">
      <span className="h-px flex-1 bg-line" />{label}<span className="h-px flex-1 bg-line" />
    </div>
  );
}

function ErrorBox({ message }: { message: string | null }) {
  if (!message) return null;
  return <p role="alert" className="rounded-[12px] border-2 border-chilli/30 bg-chilli-soft px-4 py-3 text-sm font-medium text-[#b32f12]">{message}</p>;
}

function useAfterLogin() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;
  // Back to the page they were trying to open; otherwise the Admin console (admin) or the dashboard (restaurants).
  return (user?: { is_superadmin: boolean }) => navigate(takeNext(from, user?.is_superadmin), { replace: true });
}

export function LoginPage() {
  const { login } = useAuth();
  const afterLogin = useAfterLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"login" | null>(null);
  const [params] = useSearchParams();
  const justReset = params.get("reset") === "1";
  const timedOut = params.get("timeout");
  const confirmed = params.get("email_confirmed");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email || !password) { setError("Enter your email and password."); return; }
    setBusy("login"); setError(null);
    try { const u = await login(email.trim(), password); afterLogin(u); } catch (err) { setError(errorMessage(err)); setBusy(null); }
  }

  return (
    <AuthShell title="Welcome back" intro="Sign in to see what your guests said today."
      footer={<>New to Virundhu? <Link to="/register" className="font-semibold text-night underline decoration-turmeric decoration-2 underline-offset-4">Start a free trial</Link></>}>
      {confirmed === "1" ? <p className="mb-5 rounded-[12px] bg-leaf-soft px-4 py-3 font-medium text-[#16784a]">Email confirmed. Thank you. Sign in to continue.</p> : null}
      {confirmed === "0" ? <p className="mb-5 rounded-[12px] bg-chilli-soft px-4 py-3 font-medium text-[#b32f12]">That confirmation link didn't work. Sign in and contact us from the Contact page if you need a new one.</p> : null}
      {justReset ? <p className="mb-5 rounded-[12px] bg-leaf-soft px-4 py-3 font-medium text-[#16784a]">Password changed. Sign in with your new password.</p> : null}
      {timedOut ? <p role="status" className="mb-5 rounded-[12px] bg-jasmine-2 px-4 py-3 font-medium">You were signed out after {timedOut === "5" ? "5" : "15"} minutes without activity, to keep your account safe. Sign in again to carry on.</p> : null}
      <GoogleButton />
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field id="email" label="Email" type="email" autoComplete="email" icon={<Mail className="h-[18px] w-[18px]" />}
          placeholder="you@restaurant.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field id="password" label="Password" type="password" autoComplete="current-password" icon={<Lock className="h-[18px] w-[18px]" />}
          value={password} onChange={(e) => setPassword(e.target.value)} />
        <p className="-mt-1 text-right text-sm"><Link to="/forgot-password" className="font-semibold text-ink-soft underline-offset-4 hover:text-ink hover:underline">Forgot password?</Link></p>
        <ErrorBox message={error} />
        <Button type="submit" size="lg" className="w-full" disabled={busy !== null}>
          {busy === "login" ? <><Spinner /> Signing in...</> : "Sign in"}
        </Button>
      </form>
    </AuthShell>
  );
}

function passwordStrength(pw: string): { score: number; label: string } {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw) || /[^A-Za-z0-9]/.test(pw)) score++;
  return { score, label: ["Too short", "Weak", "Okay", "Good", "Strong"][score] ?? "Strong" };
}

export function RegisterPage() {
  const { register } = useAuth();
  const afterLogin = useAfterLogin();
  const [form, setForm] = useState({ full_name: "", organization_name: "", city: "", email: "", password: "", phone: "", outlets: "" });
  const [agree, setAgree] = useState(false);
  const [errors, setErrors] = useState<Partial<Record<keyof typeof form, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const strength = passwordStrength(form.password);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const next: typeof errors = {};
    if (form.full_name.trim().length < 2) next.full_name = "Enter your name.";
    if (form.organization_name.trim().length < 2) next.organization_name = "Enter your restaurant or brand name.";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) next.email = "Enter a valid email address.";
    if (form.password.length < 8) next.password = "Use at least 8 characters.";
    setErrors(next);
    if (Object.keys(next).length) return;
    if (!agree) { setError("Please accept the Terms and the Privacy Policy to continue."); return; }
    setBusy(true); setError(null);
    try {
      const u = await register({ ...form, city: form.city || undefined, phone: form.phone.trim() || undefined, outlets: Number(form.outlets) || undefined, email: form.email.trim(), accept_terms: agree });
      afterLogin(u);
    } catch (err) { setError(errorMessage(err)); setBusy(false); }
  }

  return (
    <AuthShell title="Start your free trial" intro="14 days free. No card needed. Your restaurant is ready in a minute."
      footer={<>Already using Virundhu? <Link to="/login" className="font-semibold text-night underline decoration-turmeric decoration-2 underline-offset-4">Sign in</Link></>}>
      <GoogleButton />
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field id="full_name" label="Your name" autoComplete="name" icon={<User className="h-[18px] w-[18px]" />}
          value={form.full_name} onChange={set("full_name")} error={errors.full_name} />
        <div className="grid gap-4 sm:grid-cols-[1.4fr_1fr]">
          <Field id="org" label="Restaurant or brand" icon={<Building2 className="h-[18px] w-[18px]" />} placeholder="Vaasam Biryani House"
            value={form.organization_name} onChange={set("organization_name")} error={errors.organization_name} />
          <Field id="city" label="City" icon={<MapPin className="h-[18px] w-[18px]" />} placeholder="Chennai" value={form.city} onChange={set("city")} />
        </div>
        <div className="grid gap-4 sm:grid-cols-[1.4fr_1fr]">
          <Field id="r_phone" label="Mobile (WhatsApp)" type="tel" autoComplete="tel" icon={<Phone className="h-[18px] w-[18px]" />} placeholder="98765 43210"
            value={form.phone} onChange={set("phone")} />
          <Field id="r_outlets" label="Outlets" type="number" inputMode="numeric" min={1} placeholder="1" value={form.outlets} onChange={set("outlets")} />
        </div>
        <Field id="r_email" label="Work email" type="email" autoComplete="email" icon={<Mail className="h-[18px] w-[18px]" />}
          value={form.email} onChange={set("email")} error={errors.email} />
        <div>
          <Field id="r_password" label="Password" type="password" autoComplete="new-password" icon={<Lock className="h-[18px] w-[18px]" />}
            value={form.password} onChange={set("password")} error={errors.password}
            hint="At least 8 characters. Not a common password, and not your name, email or restaurant name." />
          {form.password ? (
            <div className="mt-2 flex items-center gap-3">
              <div className="flex flex-1 gap-1" aria-hidden="true">
                {[1, 2, 3, 4].map((i) => (
                  <span key={i} className={cn("h-1.5 flex-1 rounded-full transition-colors",
                    i <= strength.score ? (strength.score <= 1 ? "bg-chilli" : strength.score === 2 ? "bg-turmeric" : "bg-leaf") : "bg-jasmine-2")} />
                ))}
              </div>
              <span className="text-sm font-medium text-ink-soft">{strength.label}</span>
            </div>
          ) : null}
        </div>
        <label className="flex items-start gap-3 rounded-[12px] bg-jasmine-2 p-3 text-sm">
          <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} className="mt-0.5 h-5 w-5 shrink-0 accent-[#0c3b2e]" />
          <span>I agree to the <Link to="/terms" target="_blank" className="font-semibold underline">Terms of Service</Link> and the <Link to="/privacy" target="_blank" className="font-semibold underline">Privacy Policy</Link>, including how Virundhu processes my restaurant's reviews.</span>
        </label>
        <ErrorBox message={error} />
        <Button type="submit" size="lg" className="w-full" disabled={busy}>{busy ? <><Spinner /> Setting up your restaurant...</> : "Create my account"}</Button>
      </form>
    </AuthShell>
  );
}


export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) { setError("Enter the email you signed up with."); return; }
    setBusy(true); setError(null);
    try { setDone((await authApi.forgot(email.trim())).message); } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }
  return (
    <AuthShell title="Forgot your password?" intro="Enter your email and we'll send you a link to choose a new one."
      footer={<>Remembered it? <Link to="/login" className="font-semibold text-night underline decoration-turmeric decoration-2 underline-offset-4">Sign in</Link></>}>
      {done ? <p className="rounded-[12px] bg-leaf-soft px-4 py-3 font-medium text-[#16784a]">{done} Check your inbox (and spam). The link works for 30 minutes.</p> : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <Field id="f_email" label="Email" type="email" autoComplete="email" icon={<Mail className="h-[18px] w-[18px]" />} value={email} onChange={(e) => setEmail(e.target.value)} />
          <ErrorBox message={error} />
          <Button type="submit" size="lg" className="w-full" disabled={busy}>{busy ? <><Spinner /> Sending...</> : "Send reset link"}</Button>
        </form>
      )}
    </AuthShell>
  );
}

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (password.length < 8) { setError("Use at least 8 characters."); return; }
    setBusy(true); setError(null);
    try { await authApi.reset(token, password); navigate("/login?reset=1", { replace: true }); }
    catch (err) { setError(errorMessage(err)); setBusy(false); }
  }
  return (
    <AuthShell title="Choose a new password" intro="You'll be signed out on every other device, for safety."
      footer={<Link to="/forgot-password" className="font-semibold text-night underline decoration-turmeric decoration-2 underline-offset-4">Ask for a new link</Link>}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field id="n_password" label="New password" type="password" autoComplete="new-password" hint="At least 8 characters. Not a common password, and not your name or email." icon={<Lock className="h-[18px] w-[18px]" />} value={password} onChange={(e) => setPassword(e.target.value)} />
        <ErrorBox message={!token ? "This link is incomplete. Open the link from the email again." : error} />
        <Button type="submit" size="lg" className="w-full" disabled={busy || !token}>{busy ? <><Spinner /> Saving...</> : "Save new password"}</Button>
      </form>
    </AuthShell>
  );
}
