import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarCheck, Copy, Receipt, Download, MessageCircle, QrCode, Send, ShieldCheck, Star } from "lucide-react";
import QRCode from "qrcode";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/input";
import { Chip, Skeleton, Spinner } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { appApi, errorMessage } from "@/services/api";
import type { OrgSettings } from "@/types";

function Card({ icon, title, status, children }: { icon: React.ReactNode; title: string; status: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-[22px] border-2 border-line bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-[14px] bg-night text-turmeric">{icon}</span>
          <h2 className="font-display text-2xl font-bold">{title}</h2>
        </div>
        {status}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function useSave() {
  const qc = useQueryClient();
  return async (body: Partial<OrgSettings>, done: string) => {
    try {
      await appApi.saveSettings(body);
      toast.success(done);
      void qc.invalidateQueries({ queryKey: ["settings"] });
    } catch (err) { toast.error(errorMessage(err)); }
  };
}

function Autopilot({ s }: { s: OrgSettings }) {
  const save = useSave();
  const [busy, setBusy] = useState(false);
  async function toggle(on: boolean, min = s.autopilot_min_rating) {
    setBusy(true);
    await save({ autopilot_enabled: on, autopilot_min_rating: min }, on ? "Auto-pilot is on" : "Auto-pilot is off");
    setBusy(false);
  }
  return (
    <Card icon={<Star className="h-6 w-6" />} title="Auto-reply to happy Google reviews"
      status={s.autopilot_enabled ? <Chip tone="leaf">On</Chip> : <Chip>Off</Chip>}>
      <p className="max-w-2xl text-ink-soft">
        When a guest leaves a happy review on Google, Virundhu posts the thank-you reply by itself. With 3 stars included,
        mixed reviews get a polite "thank you, we'll do better". Anything unhappy, urgent or about hygiene always waits for you.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <span className="text-sm font-semibold">Reply by itself to</span>
        {[3, 4, 5].map((n) => (
          <button key={n} type="button" disabled={busy} onClick={() => toggle(s.autopilot_enabled, n)}
            className={cn("rounded-full px-4 py-2 text-sm font-semibold cursor-pointer", s.autopilot_min_rating === n ? "bg-night text-jasmine" : "bg-jasmine-2 text-ink-soft")}>
            {n === 3 ? "3, 4 and 5 stars" : n === 4 ? "4 and 5 stars" : "5 stars only"}
          </button>
        ))}
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Button onClick={() => toggle(!s.autopilot_enabled)} variant={s.autopilot_enabled ? "outline" : "primary"} disabled={busy}>
          {busy ? <Spinner /> : null} {s.autopilot_enabled ? "Turn off" : "Turn on auto-pilot"}
        </Button>
        {!s.google_connected ? <p className="text-sm text-ink-soft">Works once Google is connected on the <Link to="/app/connections" className="font-semibold underline">Connections</Link> page.</p> : null}
      </div>
    </Card>
  );
}

function FeedbackLink({ s }: { s: OrgSettings }) {
  const save = useSave();
  const [qr, setQr] = useState<string>("");
  const [googleUrl, setGoogleUrl] = useState(s.google_review_url ?? "");
  useEffect(() => {
    QRCode.toDataURL(s.feedback_url, { width: 640, margin: 2, color: { dark: "#11132A", light: "#FFFFFF" } }).then(setQr).catch(() => setQr(""));
  }, [s.feedback_url]);

  async function copy() {
    await navigator.clipboard.writeText(s.feedback_url);
    toast.success("Link copied");
  }
  return (
    <Card icon={<QrCode className="h-6 w-6" />} title="Your own feedback link" status={<Chip tone="leaf">Ready</Chip>}>
      <p className="max-w-2xl text-ink-soft">
        Print this QR code on the bill and the food packet, or send the link with WhatsApp orders. Guests rate the food in
        a few seconds, no app or sign-in. Their feedback lands here straight away and is read like any other review. No
        Zomato or Swiggy needed. Running several outlets? Each outlet has its own QR code in Settings → Outlets.
      </p>
      <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-[180px_1fr]">
        <div className="flex h-[180px] w-[180px] items-center justify-center rounded-[16px] border-2 border-line bg-white">
          {qr ? <img src={qr} alt="QR code for your feedback link" className="h-[168px] w-[168px]" /> : <Spinner />}
        </div>
        <div className="space-y-3">
          <p className="break-all rounded-[12px] bg-jasmine px-3 py-2 font-mono text-sm">{s.feedback_url}</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={copy}><Copy className="h-4 w-4" /> Copy link</Button>
            {qr ? <a href={qr} download="virundhu-feedback-qr.png"><Button><Download className="h-4 w-4" /> Download QR to print</Button></a> : null}
            <a href={s.feedback_url} target="_blank" rel="noreferrer"><Button variant="ghost">Open the guest page</Button></a>
          </div>
        </div>
      </div>
      <form className="mt-6 flex flex-wrap items-end gap-3 border-t-2 border-jasmine-2 pt-5"
        onSubmit={(e) => { e.preventDefault(); void save({ google_review_url: googleUrl.trim() }, "Google review link saved"); }}>
        <div className="min-w-[260px] flex-1">
          <Field id="g-url" label="Your Google review link (optional)" placeholder="https://g.page/r/.../review"
            hint="After giving feedback, every guest is invited to also post on Google. Find the link in Google Business Profile → Ask for reviews."
            value={googleUrl} onChange={(e) => setGoogleUrl(e.target.value)} />
        </div>
        <Button type="submit" variant="dark">Save</Button>
      </form>
    </Card>
  );
}

function WhatsApp({ s }: { s: OrgSettings }) {
  const save = useSave();
  const [numbers, setNumbers] = useState(s.whatsapp_numbers.join(", "));
  const list = numbers.split(/[,\n]+/).map((n) => n.trim()).filter(Boolean);
  return (
    <Card icon={<MessageCircle className="h-6 w-6" />} title="Urgent alerts on WhatsApp"
      status={s.whatsapp_available ? (s.whatsapp_numbers.length ? <Chip tone="leaf">On</Chip> : <Chip>No numbers yet</Chip>) : <Chip tone="turmeric">Coming soon</Chip>}>
      <p className="max-w-2xl text-ink-soft">
        The moment a serious review arrives (food safety, a very angry guest), these numbers get a WhatsApp message with
        a link to the review. Bell and email alerts keep working as before.
      </p>
      <form className="mt-4 flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); void save({ whatsapp_numbers: list }, "WhatsApp numbers saved"); }}>
        <div className="min-w-[260px] flex-1">
          <Field id="wa" label="WhatsApp numbers (up to 5)" placeholder="+919876543210, +919812345678"
            hint="With the country code. For example the owner and each outlet manager." value={numbers} onChange={(e) => setNumbers(e.target.value)} />
        </div>
        <Button type="submit" variant="dark">Save numbers</Button>
      </form>
      {!s.whatsapp_available ? <p className="mt-3 text-sm text-ink-soft">WhatsApp sending is being switched on by Virundhu. Your numbers are saved and will start getting alerts as soon as it's live.</p> : null}
    </Card>
  );
}

/** Everything that runs by itself, in one place. */
function HoldingReply({ s }: { s: OrgSettings }) {
  const save = useSave();
  const [busy, setBusy] = useState(false);
  const hours = s.holding_reply_hours ?? 0;
  async function set(h: number) {
    setBusy(true);
    await save({ holding_reply_hours: h }, h ? `Unanswered complaints get a polite reply after ${h} hours` : "Turned off");
    setBusy(false);
  }
  const phone = s.owner_phone;
  return (
    <Card icon={<ShieldCheck className="h-6 w-6" />} title="A polite first reply to unhappy Google reviews"
      status={hours ? <Chip tone="leaf">After {hours} h</Chip> : <Chip>Off</Chip>}>
      <p className="max-w-2xl text-ink-soft">
        If a 1 or 2 star Google review has no reply after the time you choose, Virundhu posts a short, safe reply so the guest
        isn't ignored. It never admits fault and never promises a refund. The review stays in your inbox so someone still calls the guest.
      </p>
      <blockquote className="mt-3 max-w-2xl rounded-[14px] bg-jasmine px-4 py-3 text-sm">
        We're sorry your experience wasn't what it should have been, and thank you for telling us. {phone ? `Please call us on ${phone} so we can put it right.` : "Please reply here so we can fix it."} - Team {s.name}
      </blockquote>
      {!phone ? <p className="mt-2 text-sm text-ink-soft">Add the outlet phone in Settings → Outlets (or your mobile in Settings → Restaurant) so guests can call you.</p> : null}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold">Reply after</span>
        {[0, 2, 6, 24].map((h) => (
          <button key={h} type="button" disabled={busy} onClick={() => set(h)}
            className={cn("rounded-full px-4 py-2 text-sm font-semibold cursor-pointer", hours === h ? "bg-night text-jasmine" : "bg-jasmine-2 text-ink-soft")}>
            {h === 0 ? "Off" : `${h} hours`}
          </button>
        ))}
      </div>
    </Card>
  );
}

/** Pull phone numbers out of pasted text or a billing export (CSV). */
function findNumbers(text: string): string[] {
  const found = text.match(/(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}/g) ?? [];
  return [...new Set(found.map((n) => n.replace(/[\s-]/g, "")))];
}

function AskGuests() {
  const { data: outlets } = useQuery({ queryKey: ["outlets"], queryFn: appApi.outlets });
  const { data: stats, refetch } = useQuery({ queryKey: ["ask-stats"], queryFn: appApi.askStats });
  const [text, setText] = useState("");
  const [outlet, setOutlet] = useState<number | "">("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<Awaited<ReturnType<typeof appApi.askGuests>> | null>(null);
  const numbers = findNumbers(text);

  async function onFile(f: File | undefined) {
    if (!f) return;
    const content = await f.text();
    const n = findNumbers(content);
    setText((t) => [t.trim(), ...n].filter(Boolean).join("\n"));
    toast.success(`${n.length} mobile number${n.length === 1 ? "" : "s"} found in the file`);
  }

  async function ask() {
    setBusy(true);
    try {
      const res = await appApi.askGuests({ numbers, outlet_id: outlet || undefined, consent });
      setResults(res);
      void refetch();
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }

  const links = results?.results.filter((r) => r.status === "link") ?? [];
  return (
    <Card icon={<Send className="h-6 w-6" />} title="Ask guests for a review on WhatsApp"
      status={stats ? <Chip tone="leaf">{stats.asked_30d} asked · {stats.feedback_30d} replied (30 days)</Chip> : null}>
      <p className="max-w-2xl text-ink-soft">
        The biggest way to raise your rating: ask every guest. Paste mobile numbers from today's bills or upload your billing
        export. Each guest gets a short "How was your food?" message with your feedback link. Nobody is asked twice in 30 days.
      </p>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <label htmlFor="ask-numbers" className="text-sm font-semibold">Mobile numbers</label>
          <textarea id="ask-numbers" rows={5} value={text} onChange={(e) => setText(e.target.value)} placeholder={"98765 43210\n91234 56789"}
            className="mt-1.5 w-full rounded-[14px] border-2 border-line bg-white p-3 font-mono text-sm" />
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
            <label className="cursor-pointer font-semibold underline decoration-turmeric decoration-2 underline-offset-4">
              Upload billing export (CSV)
              <input type="file" accept=".csv,.txt" className="sr-only" onChange={(e) => void onFile(e.target.files?.[0])} />
            </label>
            <span className="text-ink-soft">{numbers.length} number{numbers.length === 1 ? "" : "s"} found</span>
          </div>
        </div>
        <div className="space-y-3">
          {(outlets?.length ?? 0) > 1 ? (
            <label className="block text-sm font-semibold">Outlet
              <select value={outlet} onChange={(e) => setOutlet(e.target.value ? Number(e.target.value) : "")}
                className="mt-1.5 h-11 w-full rounded-[12px] border-2 border-line bg-white px-3 font-normal">
                <option value="">All outlets (guest chooses)</option>
                {outlets?.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select>
            </label>
          ) : null}
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 h-5 w-5 shrink-0 accent-turmeric" />
            <span>These guests agreed to get a message from us about their visit (for example on the bill or while ordering). We'll stop if anyone asks.</span>
          </label>
          <Button onClick={ask} disabled={busy || !numbers.length || !consent}>{busy ? <Spinner /> : <Send className="h-4 w-4" />} Ask {numbers.length || ""} guest{numbers.length === 1 ? "" : "s"}</Button>
          <p className="text-xs text-ink-soft">{stats?.sending_automatically ? "Messages go out automatically from your WhatsApp Business number." : "Until WhatsApp is connected, you get one-tap links: tap each, then press Send in WhatsApp."}</p>
        </div>
      </div>
      {results ? (
        <div className="mt-4 rounded-[14px] bg-jasmine p-4 text-sm">
          <p className="font-semibold">
            {results.results.filter((r) => r.status === "sent").length} sent · {links.length} ready to send · {results.results.filter((r) => r.status === "skipped_recent").length} asked recently · {results.results.filter((r) => r.status === "invalid").length} not a mobile number
          </p>
          {links.length ? (
            <ul className="mt-3 flex flex-wrap gap-2">
              {links.map((l) => (
                <li key={l.phone}><a href={l.link ?? "#"} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-[10px] bg-white px-3 py-1.5 font-semibold hover:bg-leaf/10"><MessageCircle className="h-3.5 w-3.5 text-leaf" /> {l.phone}</a></li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}

function BillingSoftware({ s }: { s: OrgSettings }) {
  const save = useSave();
  const [key, setKey] = useState<{ key: string; endpoint: string } | null>(null);
  const on = !!s.ask_after_bill;
  async function makeKey() {
    if (s.has_billing_key && !window.confirm("Make a new key? The old one stops working.")) return;
    try { setKey(await appApi.billingKey()); } catch (err) { toast.error(errorMessage(err)); }
  }
  return (
    <Card icon={<Receipt className="h-6 w-6" />} title="Ask every guest automatically, from your billing software"
      status={on ? <Chip tone="leaf">On</Chip> : <Chip>Off</Chip>}>
      <p className="max-w-2xl text-ink-soft">
        If your billing software (Petpooja, DotPe, a custom POS...) can call a web link after each bill, Virundhu sends the
        guest the "How was your food?" message on WhatsApp by itself. Nobody has to paste numbers. Needs WhatsApp connected.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Button variant={on ? "outline" : "primary"} onClick={() => void save({ ask_after_bill: !on }, on ? "Turned off" : "Turned on")}>{on ? "Turn off" : "Turn on"}</Button>
        <Button variant="outline" onClick={() => void makeKey()}>{s.has_billing_key ? "Make a new key" : "Get the key for your billing software"}</Button>
      </div>
      {key ? (
        <div className="mt-4 rounded-[14px] bg-night p-4 text-sm text-jasmine">
          <p className="font-semibold text-turmeric">Give these to your billing software provider. The key is shown only once.</p>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-all font-mono text-[0.8rem] leading-relaxed">{`POST ${key.endpoint}
Header  X-Virundhu-Key: ${key.key}
Body    {"phone": "9876543210", "outlet": "RS Puram"}`}</pre>
          <Button size="sm" variant="primary" className="mt-3" onClick={() => { void navigator.clipboard.writeText(key.key); toast.success("Key copied"); }}><Copy className="h-4 w-4" /> Copy key</Button>
        </div>
      ) : null}
    </Card>
  );
}

function WeeklySummary({ s }: { s: OrgSettings }) {
  const save = useSave();
  const on = s.weekly_summary !== false;
  return (
    <Card icon={<CalendarCheck className="h-6 w-6" />} title="Monday summary" status={on ? <Chip tone="leaf">On</Chip> : <Chip>Off</Chip>}>
      <p className="max-w-2xl text-ink-soft">
        Every Monday at 9 am you get last week in one message: reviews and stars per district and outlet, how many were unhappy,
        and which outlet to fix first. Each outlet manager gets their own outlet only. By email, and on WhatsApp once it's connected.
      </p>
      <Button className="mt-4" variant={on ? "outline" : "primary"} onClick={() => void save({ weekly_summary: !on }, on ? "Monday summary turned off" : "Monday summary turned on")}>
        {on ? "Turn off" : "Turn on"}
      </Button>
    </Card>
  );
}

export default function Automation() {
  const { data, isLoading } = useQuery({ queryKey: ["settings"], queryFn: appApi.settings });
  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-[2.3rem] font-bold">Automation</h1>
      <p className="mt-1 max-w-2xl text-ink-soft">Let Virundhu do the routine work. You only step in when something needs you.</p>
      <div className="mt-6 grid grid-cols-1 gap-5">
        {isLoading || !data ? <Skeleton className="h-[300px]" /> : <>
          <Autopilot s={data} />
          <HoldingReply s={data} />
          <AskGuests />
          <BillingSoftware s={data} />
          <WeeklySummary s={data} />
          <FeedbackLink s={data} />
          <WhatsApp s={data} />
        </>}
      </div>
    </div>
  );
}
