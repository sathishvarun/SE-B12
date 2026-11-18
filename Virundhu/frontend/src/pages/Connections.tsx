import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ClipboardPaste, LogOut, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Button, buttonVariants } from "@/components/ui/button";
import { Chip, Skeleton, Spinner } from "@/components/ui/misc";
import { timeAgo } from "@/lib/time";
import { cn } from "@/lib/utils";
import { useWorkspace } from "@/lib/workspace";
import { appApi, errorMessage } from "@/services/api";
import type { Connection } from "@/types";

const BRAND = {
  google: { name: "Google reviews", color: "bg-sky", letter: "G" },
  zomato: { name: "Zomato", color: "bg-chilli", letter: "Z" },
  swiggy: { name: "Swiggy", color: "bg-turmeric", letter: "S" },
} as const;

function GoogleCard({ c, canManage }: { c: Connection; canManage: boolean }) {
  const qc = useQueryClient();
  const [busy, setBusy] = useState<"connect" | "sync" | "off" | null>(null);
  const connected = c.status === "connected";

  async function connect() {
    setBusy("connect");
    try { window.location.href = (await appApi.googleStart()).url; } catch (err) { toast.error(errorMessage(err)); setBusy(null); }
  }
  async function sync() {
    setBusy("sync");
    try { await appApi.googleSync(); toast.success("Checking Google for new reviews. New ones appear in the inbox within a minute."); }
    catch (err) { toast.error(errorMessage(err)); }
    finally { setBusy(null); setTimeout(() => void qc.invalidateQueries({ queryKey: ["connections"] }), 4000); }
  }
  async function disconnect() {
    setBusy("off");
    try { await appApi.googleDisconnect(); toast.success("Google disconnected"); void qc.invalidateQueries({ queryKey: ["connections"] }); }
    catch (err) { toast.error(errorMessage(err)); } finally { setBusy(null); }
  }

  return (
    <section className="rounded-[22px] border-2 border-night bg-white p-5 shadow-[6px_6px_0_#0c3b2e] sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <span className="flex h-14 w-14 items-center justify-center rounded-[16px] bg-sky font-display text-2xl font-bold text-night">G</span>
          <div>
            <h2 className="font-display text-2xl font-bold">Google reviews</h2>
            <div className="mt-1 flex flex-wrap gap-2">
              <Chip tone="leaf">Live, official</Chip>
              {connected ? <Chip tone="leaf"><CheckCircle2 className="h-3.5 w-3.5" />Connected{c.account_email ? ` as ${c.account_email}` : ""}</Chip> : <Chip>Not connected</Chip>}
            </div>
          </div>
        </div>
        {canManage ? (
          connected ? (
            <div className="flex flex-wrap gap-2">
              <Button onClick={sync} disabled={busy !== null}>{busy === "sync" ? <Spinner /> : <RefreshCw className="h-4 w-4" />} Check for new reviews</Button>
              <Button variant="ghost" onClick={disconnect} disabled={busy !== null}><LogOut className="h-4 w-4" /> Disconnect</Button>
            </div>
          ) : (
            <Button size="lg" onClick={connect} disabled={busy !== null}>{busy === "connect" ? <Spinner /> : null} Connect Google</Button>
          )
        ) : <p className="text-sm text-ink-soft">Only the owner can connect Google.</p>}
      </div>
      <p className="mt-4 max-w-3xl text-ink-soft">{c.note}</p>
      {connected ? (
        <dl className="mt-4 grid grid-cols-1 gap-3 rounded-[16px] bg-jasmine p-4 text-sm sm:grid-cols-3">
          <div><dt className="text-ink-soft">Google locations found</dt><dd className="font-semibold">{c.locations.length ? c.locations.join(", ") : "None yet"}</dd></div>
          <div><dt className="text-ink-soft">Last checked</dt><dd className="font-semibold">{c.last_synced_at ? timeAgo(c.last_synced_at) : "Not yet"}</dd></div>
          <div><dt className="text-ink-soft">Checks automatically</dt><dd className="font-semibold">Every 10 minutes</dd></div>
        </dl>
      ) : (
        <ol className="mt-4 space-y-1.5 rounded-[16px] bg-jasmine p-4 text-sm">
          <li><b>1.</b> Click <b>Connect Google</b>.</li>
          <li><b>2.</b> Choose the Google account that manages your restaurant's Google listing and click <b>Allow</b>.</li>
          <li><b>3.</b> That's it. Reviews from every verified location arrive here, are read by AI, and urgent ones alert you. You can reply straight back to Google from the inbox.</li>
        </ol>
      )}
      {c.last_error ? (
        <p className="mt-4 flex gap-2 rounded-[12px] bg-chilli-soft p-3 text-sm font-medium text-[#b32f12]"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{c.last_error}</p>
      ) : null}
    </section>
  );
}

function AggregatorCard({ c }: { c: Connection }) {
  const b = BRAND[c.provider];
  return (
    <section className="rounded-[22px] border-2 border-line bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <span className={cn("flex h-14 w-14 items-center justify-center rounded-[16px] font-display text-2xl font-bold text-night", b.color)}>{b.letter}</span>
          <div>
            <h2 className="font-display text-2xl font-bold">{b.name}</h2>
            <div className="mt-1 flex flex-wrap gap-2"><Chip tone="turmeric">Paste or upload</Chip><Chip>No public API</Chip></div>
          </div>
        </div>
        <Link to="/app/import" className={buttonVariants({ variant: "outline" })}><ClipboardPaste className="h-4 w-4" /> Paste a {b.name} review</Link>
      </div>
      <p className="mt-4 max-w-3xl text-ink-soft">{c.note}</p>
    </section>
  );
}

export default function Connections() {
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const { isOwner } = useWorkspace();
  const { data, isLoading } = useQuery({ queryKey: ["connections"], queryFn: appApi.connections, refetchInterval: 10_000 });

  useEffect(() => {
    const g = params.get("google");
    if (!g) return;
    if (g === "connected") toast.success("Google connected. Checking for reviews now.");
    else toast.error(params.get("reason") ?? "Google connection didn't finish. Please try again.");
    if (g === "connected") void appApi.googleSync().catch(() => undefined);
    setParams({}, { replace: true });
    void qc.invalidateQueries({ queryKey: ["connections"] });
  }, [params, setParams, qc]);

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-[2.3rem] font-bold">Connections</h1>
      <p className="mt-1 max-w-2xl text-ink-soft">Where your reviews come from. Google is live today. Zomato and Swiggy only allow approved partners to read reviews, so they'll connect here once approved.</p>
      <div className="mt-6 grid grid-cols-1 gap-5">
        {isLoading ? <Skeleton className="h-[240px]" /> : null}
        {data?.map((c) => c.provider === "google" ? <GoogleCard key={c.provider} c={c} canManage={isOwner} /> : <AggregatorCard key={c.provider} c={c} />)}
      </div>
    </div>
  );
}
