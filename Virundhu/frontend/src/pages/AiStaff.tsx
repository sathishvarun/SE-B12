import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, Check, Clock, IndianRupee, MessageCircle, Radar, Settings2, Undo2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Chip, Skeleton, Stars } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { aiStaffApi, errorMessage, type AiAgent, type AiRecovery, type AiRules } from "@/services/api";

const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;
const STATUS: Record<AiAgent["status"], { label: string; tone: "leaf" | "turmeric" | "plain" | "chilli" }> = {
  working: { label: "Working", tone: "leaf" },
  approval: { label: "Waits for your OK", tone: "turmeric" },
  setup: { label: "Needs set-up", tone: "chilli" },
  off: { label: "Off", tone: "plain" },
};
const AVATAR: Record<string, string> = {
  listener: "bg-leaf text-white", responder: "bg-turmeric text-night", guardian: "bg-chilli text-white",
  radar: "bg-night text-turmeric", winback: "bg-lotus text-white", promoter: "bg-sky text-white", analyst: "bg-[#7a4b2a] text-white",
};
const TOPICS = ["hygiene", "food_quality", "delivery", "staff", "packaging", "price"] as const;
const TOPIC_LABEL: Record<string, string> = { hygiene: "Hygiene", food_quality: "Food quality", delivery: "Delivery", staff: "Staff", packaging: "Packaging", price: "Price" };

export default function AiStaff() {
  const { data, isLoading } = useQuery({ queryKey: ["ai-staff"], queryFn: aiStaffApi.get, refetchInterval: 60_000 });
  if (isLoading || !data) return <div className="mx-auto max-w-6xl space-y-4"><Skeleton className="h-[160px]" /><Skeleton className="h-[320px]" /></div>;
  const { roi } = data;
  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="text-[2.3rem] font-bold">Your AI staff</h1>
      <p className="mt-1 max-w-3xl text-ink-soft">Seven team members who read, reply, watch and win guests back for you, day and night. You decide the rules; they do the work.</p>

      <section className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Work done in the last 30 days">
        <Stat icon={<Check className="h-5 w-5" />} label="Reviews read and replied to" value={`${roi.reviews_read} / ${roi.replies_written}`} />
        <Stat icon={<Clock className="h-5 w-5" />} label="Hours of your time saved" value={`${roi.hours_saved} h`} sub={`worth about ${inr(roi.value_saved)}`} />
        <Stat icon={<AlertTriangle className="h-5 w-5" />} label="Revenue at risk from unhappy guests" value={inr(roi.revenue_at_risk)} tone="chilli" />
        <Stat icon={<IndianRupee className="h-5 w-5" />} label="Won back by the win-back team" value={inr(roi.revenue_won_back)} tone="leaf" />
      </section>
      <p className="mt-2 text-xs text-ink-soft">Last 30 days. Estimates: {roi.assumptions}</p>

      <section className="mt-8 rounded-[22px] bg-night p-5 text-jasmine sm:p-6">
        <h2 className="font-display text-2xl font-bold">Today's 3 moves</h2>
        <p className="text-mist">Picked from the last 7 days of reviews. Do these and your rating moves.</p>
        <ol className="mt-4 grid gap-3 md:grid-cols-3">
          {data.moves.map((m, i) => (
            <li key={m.title} className="flex flex-col rounded-[16px] bg-white/[0.07] p-4">
              <span className="font-display text-3xl font-bold text-turmeric">{i + 1}</span>
              <p className="mt-1 font-display text-lg font-bold">{m.title}</p>
              <p className="mt-1 flex-1 text-sm text-mist">{m.why}</p>
              <Link to={m.link} className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-turmeric hover:underline">Do it now <ArrowRight className="h-4 w-4" /></Link>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-8">
        <h2 className="flex items-center gap-2 font-display text-2xl font-bold"><Radar className="h-6 w-6 text-chilli" /> Crisis radar</h2>
        <p className="text-ink-soft">The same complaint three times at one outlet within 72 hours is a pattern, not bad luck.</p>
        {data.crises.length ? (
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {data.crises.map((c) => (
              <article key={c.outlet + c.topic} className={cn("rounded-[18px] border-2 bg-white p-4", c.severity === "critical" ? "border-chilli" : "border-turmeric")}>
                <div className="flex flex-wrap items-center gap-2">
                  <Chip tone={c.severity === "critical" ? "chilli" : "turmeric"}>{c.severity === "critical" ? "Act today" : "Watch closely"}</Chip>
                  <p className="font-display text-lg font-bold">{c.count} complaints about {c.topic} at {c.outlet}</p>
                </div>
                <p className="mt-2 text-sm"><b>Likely cause:</b> {c.likely_cause}.</p>
                <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-ink-soft">{c.examples.map((e) => <li key={e}>{e}</li>)}</ul>
                <p className="mt-3 rounded-[12px] bg-jasmine px-3 py-2 text-sm font-semibold">What to do: {c.action}</p>
              </article>
            ))}
          </div>
        ) : <p className="mt-3 rounded-[16px] border-2 border-dashed border-line bg-white px-4 py-5 text-ink-soft">No repeating complaint right now. Vikram checks every new review.</p>}
      </section>

      <section className="mt-8">
        <h2 className="font-display text-2xl font-bold">Meet the team</h2>
        <p className="text-ink-soft">Tap a card to see a real example of their work.</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.agents.map((a) => <AgentCard key={a.key} a={a} />)}
        </div>
      </section>

      <BeforeNow />

      <WinBack items={data.recovery} />
      <Rules initial={data.rules} />
    </div>
  );
}

function AgentCard({ a }: { a: AiAgent }) {
  const [flipped, setFlipped] = useState(false);
  return (
    <button type="button" onClick={() => setFlipped((f) => !f)} aria-pressed={flipped}
      className={cn("group flex min-h-[230px] cursor-pointer flex-col rounded-[18px] border-2 p-4 text-left transition-colors", flipped ? "border-night bg-night text-jasmine" : "border-line bg-white hover:border-night")}>
      <div className="flex w-full items-center gap-3">
        <span className={cn("flex h-12 w-12 shrink-0 items-center justify-center rounded-full font-display text-xl font-bold transition-transform group-hover:scale-105", AVATAR[a.key] ?? "bg-night text-white")}>{a.name[0]}</span>
        <div className="min-w-0 flex-1">
          <p className="font-display text-lg font-bold leading-tight">{a.name}</p>
          <p className={cn("font-display text-[0.95rem] font-semibold", flipped ? "text-turmeric" : "text-chilli")}>{a.role}</p>
        </div>
        <Chip tone={flipped ? "dark" : STATUS[a.status].tone}>{STATUS[a.status].label}</Chip>
      </div>
      {flipped ? (
        <>
          <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-mist">A day's work, for example</p>
          <p className="mt-1 flex-1 text-[0.95rem]">"{a.sample}"</p>
          <Link to={a.link} onClick={(e) => e.stopPropagation()} className="mt-3 text-sm font-semibold text-turmeric hover:underline">{a.status === "setup" || a.status === "off" ? "Switch me on" : "See my real work"}</Link>
        </>
      ) : (
        <>
          <p className="mt-3 flex-1 text-sm">{a.job}</p>
          <p className="mt-3 font-display text-2xl font-bold">{a.done.toLocaleString("en-IN")} <span className="font-body text-sm font-normal text-ink-soft">{a.unit}{a.extra ? ` · ${a.extra}` : ""}</span></p>
          <p className="mt-1 text-sm font-semibold text-night">Tap to see my work</p>
        </>
      )}
    </button>
  );
}

const CHORES = [
  { chore: "Checking Google, Zomato and Swiggy for new reviews", before: "Every morning, 3 apps, about 30 minutes", now: "Kavya reads each one as it arrives", who: "listener" },
  { chore: "Writing replies to guests", before: "3 minutes a reply, often forgotten", now: "Arjun drafts in the guest's language; happy Google replies go out by themselves", who: "responder" },
  { chore: "Noticing serious complaints", before: "Found days later, after it spread", now: "Meera alerts the branch manager within a minute", who: "guardian" },
  { chore: "Spotting a problem that keeps repeating", before: "Only when the rating drops", now: "Vikram flags 3 alike in 72 hours, with the likely cause", who: "radar" },
  { chore: "Calling back unhappy guests", before: "Rarely done", now: "Anbu writes the apology and comeback code; one tap on WhatsApp", who: "winback" },
  { chore: "Asking happy guests for Google reviews", before: "Staff forget at the counter", now: "Malar invites them after the bill", who: "promoter" },
  { chore: "Preparing the weekly team meeting", before: "Scroll reviews, guess what to fix", now: "Siva's Monday brief: fix, dish, who to thank", who: "analyst" },
];

function BeforeNow() {
  const [now, setNow] = useState(true);
  return (
    <section className="mt-8 rounded-[22px] border-2 border-line bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-2xl font-bold">Your day, {now ? "with your AI staff" : "before Virundhu"}</h2>
        <div role="tablist" className="inline-flex rounded-full bg-jasmine-2 p-1">
          <button role="tab" aria-selected={!now} onClick={() => setNow(false)} className={cn("cursor-pointer rounded-full px-4 py-1.5 text-sm font-semibold", !now ? "bg-chilli text-white" : "text-ink-soft")}>Before</button>
          <button role="tab" aria-selected={now} onClick={() => setNow(true)} className={cn("cursor-pointer rounded-full px-4 py-1.5 text-sm font-semibold", now ? "bg-leaf text-white" : "text-ink-soft")}>Now</button>
        </div>
      </div>
      <ul className="mt-4 divide-y-2 divide-jasmine-2">
        {CHORES.map((c) => (
          <li key={c.chore} className="grid gap-1 py-3 sm:grid-cols-[1fr_1.3fr] sm:items-center sm:gap-4">
            <p className="font-semibold">{c.chore}</p>
            <p className={cn("flex items-center gap-2 text-sm", now ? "text-[#16784a]" : "text-[#c23a1c]")}>
              {now ? <span className={cn("flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[0.7rem] font-bold", AVATAR[c.who])}>{c.now[0]}</span> : <Clock className="h-4 w-4 shrink-0" />}
              {now ? c.now : c.before}
            </p>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-sm text-ink-soft">{now ? "What's left for you: approve the replies that matter, fix what the team points out, and thank your staff." : "About 6 to 8 hours a week for one outlet, and most of it gets skipped on busy days."}</p>
    </section>
  );
}

function Stat({ icon, label, value, sub, tone }: { icon: React.ReactNode; label: string; value: string; sub?: string; tone?: "chilli" | "leaf" }) {
  return (
    <div className="rounded-[18px] border-2 border-line bg-white p-4">
      <span className={cn("flex h-9 w-9 items-center justify-center rounded-[10px]", tone === "chilli" ? "bg-chilli-soft text-chilli" : tone === "leaf" ? "bg-leaf-soft text-leaf" : "bg-jasmine-2 text-night")}>{icon}</span>
      <p className="tabular mt-2 font-display text-[1.9rem] font-bold leading-none">{value}</p>
      <p className="mt-1 text-sm text-ink-soft">{label}{sub ? `, ${sub}` : ""}</p>
    </div>
  );
}

function WinBack({ items }: { items: AiRecovery[] }) {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: ["ai-staff"] });
  const draft = useMutation({ mutationFn: aiStaffApi.draft, onSuccess: () => { void refresh(); toast.success("Message ready. Send it on WhatsApp."); }, onError: (e) => toast.error(errorMessage(e)) });
  const mark = useMutation({ mutationFn: ({ id, s }: { id: number; s: "sent" | "returned" }) => aiStaffApi.mark(id, s), onSuccess: () => void refresh(), onError: (e) => toast.error(errorMessage(e)) });
  return (
    <section className="mt-8">
      <h2 className="flex items-center gap-2 font-display text-2xl font-bold"><Undo2 className="h-6 w-6 text-lotus" /> Win-back: unhappy guests you can still save</h2>
      <p className="text-ink-soft">Guests who left a phone number on your QR feedback. Anbu writes an apology in their language with a comeback code; you send it in one tap.</p>
      {items.length ? (
        <ul className="mt-3 space-y-3">
          {items.map((g) => (
            <li key={g.review_id} className="rounded-[18px] border-2 border-line bg-white p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-semibold">{g.guest}</p><Stars rating={g.rating} />
                <span className="text-sm text-ink-soft">{g.outlet ?? ""} · {g.date}</span>
                <Chip tone={g.status === "returned" ? "leaf" : g.status === "sent" ? "sky" : g.status === "drafted" ? "turmeric" : "plain"} className="ml-auto">
                  {g.status === "returned" ? "Came back" : g.status === "sent" ? "Message sent" : g.status === "drafted" ? "Ready to send" : "Not contacted"}
                </Chip>
              </div>
              <p className="mt-1 text-sm text-ink-soft">{g.summary}</p>
              {g.message ? <p className="mt-2 rounded-[12px] bg-jasmine px-3 py-2 text-sm">{g.message}</p> : null}
              <div className="mt-3 flex flex-wrap gap-2">
                {g.status === "new" ? <Button size="sm" onClick={() => draft.mutate(g.review_id)} disabled={draft.isPending}>Write the apology</Button> : null}
                {g.whatsapp_url && g.status !== "returned" ? (
                  <a href={g.whatsapp_url} target="_blank" rel="noreferrer" onClick={() => mark.mutate({ id: g.review_id, s: "sent" })}
                    className="inline-flex items-center gap-2 rounded-[12px] bg-leaf px-3 py-2 text-sm font-semibold text-white hover:opacity-90"><MessageCircle className="h-4 w-4" /> Send on WhatsApp</a>
                ) : null}
                {g.status === "sent" || g.status === "drafted" ? <Button size="sm" variant="outline" onClick={() => mark.mutate({ id: g.review_id, s: "returned" })}>They came back ({g.code})</Button> : null}
              </div>
            </li>
          ))}
        </ul>
      ) : <p className="mt-3 rounded-[16px] border-2 border-dashed border-line bg-white px-4 py-5 text-ink-soft">No unhappy guest with a phone number yet. Put your QR code on bills and parcels so guests can reach you directly.</p>}
    </section>
  );
}

function Rules({ initial }: { initial: AiRules }) {
  const qc = useQueryClient();
  const [r, setR] = useState(initial);
  const save = useMutation({ mutationFn: aiStaffApi.saveRules, onSuccess: () => { toast.success("Rules saved. Your AI staff follows them from now on."); void qc.invalidateQueries({ queryKey: ["ai-staff"] }); }, onError: (e) => toast.error(errorMessage(e)) });
  const toggle = (t: string) => setR({ ...r, escalate: r.escalate.includes(t) ? r.escalate.filter((x) => x !== t) : [...r.escalate, t] });
  return (
    <section className="mt-8 rounded-[22px] border-2 border-line bg-white p-5 sm:p-6">
      <h2 className="flex items-center gap-2 font-display text-2xl font-bold"><Settings2 className="h-6 w-6" /> Your rules for the AI staff</h2>
      <div className="mt-4 grid gap-5 md:grid-cols-2">
        <label className="text-sm font-semibold">Words a public reply must never contain
          <input value={r.banned_words.join(", ")} onChange={(e) => setR({ ...r, banned_words: e.target.value.split(",").map((w) => w.trim()).filter(Boolean) })}
            className="mt-1 block h-11 w-full rounded-[10px] border-2 border-line px-3 font-normal" placeholder="refund, free, compensation" />
          <span className="font-normal text-ink-soft">Separate with commas. A reply with any of these waits for you.</span>
        </label>
        <div className="text-sm font-semibold">Topics that always wait for a person
          <div className="mt-2 flex flex-wrap gap-2">
            {TOPICS.map((t) => (
              <button key={t} type="button" onClick={() => toggle(t)} aria-pressed={r.escalate.includes(t)}
                className={cn("cursor-pointer rounded-full border-2 px-3 py-1.5 font-semibold", r.escalate.includes(t) ? "border-night bg-night text-jasmine" : "border-line bg-white")}>{TOPIC_LABEL[t]}</button>
            ))}
          </div>
        </div>
        <label className="text-sm font-semibold">Your average order value (₹)
          <input type="number" min={50} max={20000} value={r.avg_order_value} onChange={(e) => setR({ ...r, avg_order_value: Number(e.target.value) || 0 })}
            className="mt-1 block h-11 w-full rounded-[10px] border-2 border-line px-3 font-normal" />
          <span className="font-normal text-ink-soft">Used for revenue at risk and won back.</span>
        </label>
        <label className="text-sm font-semibold">Comeback offer for unhappy guests
          <input value={r.comeback_offer} maxLength={80} onChange={(e) => setR({ ...r, comeback_offer: e.target.value })}
            className="mt-1 block h-11 w-full rounded-[10px] border-2 border-line px-3 font-normal" />
        </label>
      </div>
      <Button className="mt-5" onClick={() => save.mutate(r)} disabled={save.isPending}>Save rules</Button>
    </section>
  );
}
