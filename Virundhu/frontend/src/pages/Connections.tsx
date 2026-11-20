import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ClipboardPaste, LogOut, MapPin, RefreshCw, Search, Star, Unlink } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Button, buttonVariants } from "@/components/ui/button";
import { Chip, Skeleton, Spinner } from "@/components/ui/misc";
import { timeAgo } from "@/lib/time";
import { cn } from "@/lib/utils";
import { useWorkspace } from "@/lib/workspace";
import { appApi, errorMessage, placesApi, type OutletPlace, type PlaceHit } from "@/services/api";
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
            c.available === false
              ? <span className="rounded-full bg-turmeric/20 px-3 py-1.5 text-sm font-semibold">Switching on soon</span>
              : <Button size="lg" onClick={connect} disabled={busy !== null}>{busy === "connect" ? <Spinner /> : null} Connect Google</Button>
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
      ) : c.available === false ? (
        <p className="mt-4 rounded-[16px] bg-jasmine p-4 text-sm">
          The Virundhu team is switching on the Google connection for your account. You don't need to do anything; this page
          will show <b>Connect Google</b> once it's ready. Until then, add Google reviews with <b>Paste one review</b> or a
          screenshot in <a href="/app/import" className="font-semibold underline">Add reviews</a>.
        </p>
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

function OutletListing({ o, canManage }: { o: OutletPlace; canManage: boolean }) {
  const qc = useQueryClient();
  const [q, setQ] = useState(o.outlet);
  const [hits, setHits] = useState<PlaceHit[] | null>(null);
  const [busy, setBusy] = useState<"search" | "link" | "sync" | "off" | null>(null);
  const refresh = () => void qc.invalidateQueries({ queryKey: ["places"] });

  async function find(e: FormEvent) {
    e.preventDefault();
    setBusy("search");
    try { setHits(await placesApi.search(q)); } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(null); }
  }
  async function pick(h: PlaceHit) {
    setBusy("link");
    try { const r = await placesApi.link(o.outlet_id, h.place_id); toast.success(r.message); setHits(null); refresh(); }
    catch (err) { toast.error(errorMessage(err)); } finally { setBusy(null); }
  }
  async function check() {
    setBusy("sync");
    try { const r = await placesApi.sync(o.outlet_id); (r.outlet.error ? toast.error : toast.success)(r.message); refresh(); }
    catch (err) { toast.error(errorMessage(err)); } finally { setBusy(null); }
  }
  async function unlink() {
    setBusy("off");
    try { await placesApi.unlink(o.outlet_id); toast.success(`${o.outlet} is no longer checked on Google. Its reviews stay in the inbox.`); refresh(); }
    catch (err) { toast.error(errorMessage(err)); } finally { setBusy(null); }
  }

  return (
    <li className="rounded-[16px] border-2 border-line p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold">{o.outlet}</p>
          {o.place_id ? (
            <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-soft">
              <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{o.place_name ?? "Linked listing"}</span>
              {o.rating !== null ? <span className="flex items-center gap-1 font-semibold text-ink"><Star className="h-3.5 w-3.5 fill-turmeric text-turmeric" />{o.rating.toFixed(1)} from {(o.rating_count ?? 0).toLocaleString("en-IN")} reviews</span> : null}
              <span>Checked {o.synced_at ? timeAgo(o.synced_at) : "not yet"}</span>
            </p>
          ) : <p className="text-sm text-ink-soft">Not linked to Google yet.</p>}
        </div>
        {canManage && o.place_id ? (
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={check} disabled={busy !== null}>{busy === "sync" ? <Spinner /> : <RefreshCw className="h-4 w-4" />} Check now</Button>
            <Button size="sm" variant="ghost" onClick={unlink} disabled={busy !== null}><Unlink className="h-4 w-4" /> Unlink</Button>
          </div>
        ) : null}
      </div>
      {o.error ? <p className="mt-3 flex gap-2 rounded-[12px] bg-chilli-soft p-2.5 text-sm font-medium text-[#b32f12]"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{o.error}</p> : null}
      {canManage && !o.place_id ? (
        <form onSubmit={find} className="mt-3 flex flex-wrap gap-2">
          <label className="sr-only" htmlFor={`find-${o.outlet_id}`}>Restaurant name and area</label>
          <input id={`find-${o.outlet_id}`} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name and area, e.g. Annapoorna RS Puram Coimbatore"
            className="h-11 min-w-0 flex-1 rounded-[12px] border-2 border-line bg-white px-3" />
          <Button type="submit" disabled={busy !== null || q.trim().length < 3}>{busy === "search" ? <Spinner /> : <Search className="h-4 w-4" />} Find on Google</Button>
        </form>
      ) : null}
      {hits ? (
        hits.length === 0 ? <p className="mt-3 text-sm text-ink-soft">Nothing found. Add the area or city to the name and try again.</p> : (
          <ul className="mt-3 divide-y divide-line rounded-[12px] border-2 border-line">
            {hits.map((h) => (
              <li key={h.place_id} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <div className="min-w-0">
                  <p className="font-semibold">{h.name}</p>
                  <p className="text-sm text-ink-soft">{h.address}{h.rating !== null ? ` · ${h.rating.toFixed(1)}★ (${h.reviews.toLocaleString("en-IN")})` : ""}</p>
                </div>
                <Button size="sm" variant="outline" onClick={() => pick(h)} disabled={busy !== null}>{busy === "link" ? <Spinner /> : null} This is {o.outlet}</Button>
              </li>
            ))}
          </ul>
        )
      ) : null}
    </li>
  );
}

function MapsListingCard({ canManage }: { canManage: boolean }) {
  const { data } = useQuery({ queryKey: ["places"], queryFn: placesApi.status, refetchInterval: 30_000 });
  if (!data || !data.enabled || data.full_sync_connected) return null;
  const linked = data.outlets.filter((o) => o.place_id).length;
  return (
    <section className="rounded-[22px] border-2 border-line bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <span className="flex h-14 w-14 items-center justify-center rounded-[16px] bg-leaf font-display text-2xl font-bold text-white"><MapPin className="h-7 w-7" /></span>
          <div>
            <h2 className="font-display text-2xl font-bold">Google reviews from your Maps listing</h2>
            <div className="mt-1 flex flex-wrap gap-2"><Chip tone="leaf">Works today</Chip><Chip>{linked} of {data.outlets.length} outlet{data.outlets.length === 1 ? "" : "s"} linked</Chip></div>
          </div>
        </div>
      </div>
      <p className="mt-4 max-w-3xl text-ink-soft">
        Find each outlet on Google Maps once. Virundhu then checks it every day and brings in its newest Google reviews,
        which the AI reads and drafts replies for. Post the reply on Google yourself: copy it from the inbox. Once you
        connect Google above, every review comes in and replies post automatically, and this stops by itself.
      </p>
      {data.outlets.length === 0 ? <p className="mt-4 text-sm text-ink-soft">Add your outlets in <Link to="/app/settings" className="font-semibold underline">Settings</Link> first.</p> : (
        <ul className="mt-4 grid gap-3">
          {data.outlets.map((o) => <OutletListing key={o.outlet_id} o={o} canManage={canManage} />)}
        </ul>
      )}
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
        {data?.map((c) => c.provider === "google" ? <GoogleCard key={c.provider} c={c} canManage={isOwner} /> : null)}
        <MapsListingCard canManage={isOwner} />
        {data?.filter((c) => c.provider !== "google").map((c) => <AggregatorCard key={c.provider} c={c} />)}
      </div>
    </div>
  );
}
