import { useQuery } from "@tanstack/react-query";
import { Lock, User } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Logo, LogoMark } from "@/components/layout/Logo";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/input";
import { Spinner } from "@/components/ui/misc";
import { useAuth } from "@/context/AuthContext";
import { errorMessage, inviteApi } from "@/services/api";

const ROLE = { owner: "an owner", manager: "a manager", agent: "a team member" } as const;

/** /invite/:token - a teammate joins a restaurant. */
export function InvitePage() {
  const { token = "" } = useParams();
  const navigate = useNavigate();
  const { acceptTokens } = useAuth();
  const { data, isLoading, error } = useQuery({ queryKey: ["invite", token], queryFn: () => inviteApi.info(token), retry: false });
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      const t = await inviteApi.accept(token, { full_name: name || (data?.email.split("@")[0] ?? "Team member"), password });
      await acceptTokens(t);
      navigate("/app/inbox", { replace: true });
    } catch (ex) { setErr(errorMessage(ex)); setBusy(false); }
  }

  return (
    <div className="kolam-dark flex min-h-dvh items-center justify-center px-4 py-10">
      <div className="w-full max-w-[460px] rounded-[24px] bg-jasmine p-6 sm:p-8">
        <Logo />
        {isLoading ? <div className="mt-8 flex justify-center"><Spinner className="h-6 w-6" /></div> : null}
        {error ? <p className="mt-8 rounded-[12px] bg-chilli-soft p-4 font-medium text-[#b32f12]">{errorMessage(error)}</p> : null}
        {data ? (
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <h1 className="text-[2rem] font-bold">Join {data.organization_name}</h1>
            <p className="text-ink-soft">You've been invited as {ROLE[data.role]} to reply to guest reviews. Your email: <b className="text-ink">{data.email}</b></p>
            {!data.has_account ? <Field id="j-name" label="Your name" icon={<User className="h-[18px] w-[18px]" />} value={name} onChange={(e) => setName(e.target.value)} /> : null}
            <Field id="j-pw" type="password" label={data.has_account ? "Your Virundhu password" : "Choose a password"} hint={data.has_account ? undefined : "At least 8 characters. Not a common password, and not your name or email."}
              icon={<Lock className="h-[18px] w-[18px]" />} value={password} onChange={(e) => setPassword(e.target.value)} />
            {err ? <p role="alert" className="rounded-[12px] bg-chilli-soft px-4 py-3 text-sm font-medium text-[#b32f12]">{err}</p> : null}
            <Button type="submit" size="lg" className="w-full" disabled={busy || password.length < 8}>{busy ? <><Spinner /> Joining...</> : "Join the team"}</Button>
          </form>
        ) : null}
        <p className="mt-6 text-sm text-ink-soft"><Link to="/" className="underline underline-offset-4">Back to Virundhu</Link></p>
      </div>
    </div>
  );
}

/** /auth/callback - Google sign-in lands here with tokens in the URL fragment. */
export function AuthCallbackPage() {
  const navigate = useNavigate();
  const { acceptTokens } = useAuth();
  const [parsed] = useState(() => {
    const params = new URLSearchParams(window.location.hash.slice(1));
    return { access: params.get("access") };
  });
  const [err, setErr] = useState<string | null>(parsed.access ? null : "Google sign-in didn't finish. Please try again.");
  useEffect(() => {
    const { access } = parsed;
    window.history.replaceState(null, "", "/auth/callback");
    if (!access) return;
    acceptTokens({ access_token: access })
      .then(() => navigate("/app", { replace: true }))
      .catch((e: unknown) => setErr(errorMessage(e)));
  }, [acceptTokens, navigate, parsed]);
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center">
      <LogoMark className="h-12 w-12 animate-pulse" />
      {err ? <><p className="font-medium text-chilli">{err}</p><Link to="/login" className="underline">Back to sign in</Link></> : <p className="text-ink-soft">Signing you in with Google...</p>}
    </div>
  );
}
