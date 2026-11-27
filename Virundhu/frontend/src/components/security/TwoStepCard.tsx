import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Download, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/input";
import { Chip, Spinner } from "@/components/ui/misc";
import { useAuth } from "@/context/AuthContext";
import { accountApi, errorMessage } from "@/services/api";

/**
 * Two-step sign-in with an authenticator app: scan, type the first code, keep the recovery codes.
 * Used in Settings, in the admin's password dialog, and as the admin's first screen when it is required.
 */
export function TwoStepCard({ compact = false }: { compact?: boolean }) {
  const qc = useQueryClient();
  const { refreshUser } = useAuth();
  const { data, refetch } = useQuery({ queryKey: ["two-step"], queryFn: accountApi.twoStep });
  const [setup, setSetup] = useState<{ secret: string; qr: string } | null>(null);
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [offPw, setOffPw] = useState("");
  const [offCode, setOffCode] = useState("");
  const [busy, setBusy] = useState(false);

  async function begin() {
    setBusy(true);
    try { const r = await accountApi.twoStepStart(); setSetup({ secret: r.secret, qr: `data:image/svg+xml;base64,${r.qr_svg_base64}` }); }
    catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }
  async function confirm(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await accountApi.twoStepConfirm(code.trim());
      setCodes(r.recovery_codes); setSetup(null); setCode("");
      toast.success("Two-step sign-in is on. Other devices were signed out.");
      await refetch();
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }
  async function savedCodes() {
    setCodes(null);
    await refreshUser();
    void qc.invalidateQueries();
  }
  async function turnOff(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try { await accountApi.twoStepOff(offPw, offCode.trim()); toast.success("Two-step sign-in switched off"); setOffPw(""); setOffCode(""); await refetch(); await refreshUser(); }
    catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }
  function download() {
    const blob = new Blob([`Virundhu recovery codes (each works once)\n\n${(codes ?? []).join("\n")}\n`], { type: "text/plain" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "virundhu-recovery-codes.txt"; a.click();
  }

  return (
    <section className={compact ? "" : "rounded-[20px] border-2 border-line bg-white p-5 sm:p-6"} aria-labelledby="two-step">
      <div className="flex flex-wrap items-center gap-3">
        <h2 id="two-step" className="flex items-center gap-2 font-display text-xl font-bold"><ShieldCheck className="h-5 w-5" /> Two-step sign-in</h2>
        {data?.enabled ? <Chip tone="leaf">On</Chip> : <Chip tone="turmeric">Off</Chip>}
      </div>
      <p className="mt-1 max-w-2xl text-sm text-ink-soft">
        After your password, Virundhu asks for a 6-digit code from an app on your phone (Google Authenticator, Microsoft
        Authenticator or Authy). Someone who steals your password still can't get in.
      </p>

      {codes ? (
        <div className="mt-4 rounded-[14px] border-2 border-turmeric bg-jasmine p-4">
          <p className="font-semibold">Save these recovery codes now. They're shown only once.</p>
          <p className="text-sm text-ink-soft">If you lose your phone, each code lets you sign in one time.</p>
          <ul className="mt-3 grid grid-cols-2 gap-1.5 font-mono text-sm sm:grid-cols-4">{codes.map((c) => <li key={c} className="rounded-[8px] bg-white px-2 py-1 text-center">{c}</li>)}</ul>
          <div className="mt-3 flex flex-wrap gap-3">
            <Button size="sm" variant="outline" onClick={() => { void navigator.clipboard.writeText(codes.join("\n")); toast.success("Copied"); }}><Copy className="h-4 w-4" /> Copy</Button>
            <Button size="sm" variant="outline" onClick={download}><Download className="h-4 w-4" /> Download</Button>
            <Button size="sm" variant="dark" onClick={() => void savedCodes()}>I've saved them</Button>
          </div>
        </div>
      ) : data?.enabled ? (
        <form onSubmit={turnOff} className="mt-4 grid max-w-2xl gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
          <p className="text-sm text-ink-soft sm:col-span-3">On since {data.enabled_at ? new Date(data.enabled_at).toLocaleDateString("en-IN", { dateStyle: "medium" }) : "-"}. {data.recovery_left} recovery codes left. To switch it off:</p>
          <Field id="off-pw" label="Password" type="password" autoComplete="current-password" value={offPw} onChange={(e) => setOffPw(e.target.value)} />
          <Field id="off-code" label="Code from the app" inputMode="numeric" autoComplete="one-time-code" value={offCode} onChange={(e) => setOffCode(e.target.value)} />
          <Button type="submit" variant="outline" disabled={busy || offCode.length < 6}>Switch off</Button>
        </form>
      ) : setup ? (
        <form onSubmit={confirm} className="mt-4 grid gap-5 sm:grid-cols-[auto_1fr]">
          <img src={setup.qr} alt="QR code to scan with your authenticator app" className="h-44 w-44 rounded-[12px] border-2 border-line bg-white p-1" />
          <div className="space-y-3">
            <ol className="list-decimal space-y-1 pl-5 text-sm">
              <li>Open your authenticator app and tap <b>+</b>, then <b>Scan a QR code</b>.</li>
              <li>Can't scan? Choose <b>Enter a setup key</b> and type: <code className="break-all rounded bg-jasmine-2 px-1.5 py-0.5">{setup.secret}</code></li>
              <li>Type the 6-digit code the app shows.</li>
            </ol>
            <div className="flex max-w-md items-end gap-3">
              <Field id="setup-code" label="Code" inputMode="numeric" autoComplete="one-time-code" autoFocus value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} />
              <Button type="submit" variant="dark" disabled={busy || code.trim().length !== 6}>{busy ? <Spinner /> : null} Switch on</Button>
            </div>
          </div>
        </form>
      ) : (
        <Button className="mt-4" variant="dark" onClick={() => void begin()} disabled={busy}>{busy ? <Spinner /> : null} Set up two-step sign-in</Button>
      )}
    </section>
  );
}
