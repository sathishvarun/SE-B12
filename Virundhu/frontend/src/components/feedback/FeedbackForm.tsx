import { CheckCircle2, Star } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { errorMessage, productFeedbackApi, type FeedbackKind } from "@/services/api";

export const AREAS: [string, string][] = [
  ["setup", "Getting set up"], ["inbox", "Reviews inbox"], ["replies", "Replies"], ["alerts", "Alerts"],
  ["reports", "Reports"], ["ai_staff", "Your AI staff"], ["billing", "Plan and billing"], ["other", "Something else"],
];
const KINDS: [FeedbackKind, string, string][] = [
  ["idea", "An idea", "Something you'd like Virundhu to do"],
  ["problem", "Something's hard", "A bug, or a step that confused you"],
  ["praise", "Something I like", "What's working well for you"],
  ["other", "Something else", "Anything on your mind"],
];

export function Chips<T extends string>({ value, onChange, options, label }: { value: T | null; onChange: (v: T) => void; options: [T, string][]; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-2">
      {options.map(([k, text]) => (
        <button key={k} type="button" role="radio" aria-checked={value === k} onClick={() => onChange(k)}
          className={cn("rounded-full border-2 px-4 py-2 text-sm font-semibold transition-colors", value === k ? "border-night bg-night text-jasmine" : "border-line bg-white hover:border-night")}>
          {text}
        </button>
      ))}
    </div>
  );
}

/** Share-feedback form used on the website (public) and inside the app (signed in). */
export function FeedbackForm({ publicForm = false, page = "" }: { publicForm?: boolean; page?: string }) {
  const [kind, setKind] = useState<FeedbackKind>("idea");
  const [rating, setRating] = useState<number | null>(null);
  const [area, setArea] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [consent, setConsent] = useState(false);
  const [who, setWho] = useState({ name: "", email: "", restaurant: "", website: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (message.trim().length < 3) { setError("Please write a line or two so we know what you mean."); return; }
    if (publicForm && who.email && !/^\S+@\S+\.\S+$/.test(who.email)) { setError("That email doesn't look right."); return; }
    setBusy(true); setError(null);
    const body = { kind, message: message.trim(), rating, area, consent_quote: kind === "praise" && consent, page };
    try {
      const r = publicForm ? await productFeedbackApi.publicSend({ ...body, ...who }) : await productFeedbackApi.send(body);
      setDone(r.message);
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }

  if (done) {
    return (
      <div className="py-8 text-center">
        <CheckCircle2 className="mx-auto h-12 w-12 text-leaf" />
        <h2 className="mt-3 text-2xl font-bold">Got it, thank you</h2>
        <p className="mx-auto mt-2 max-w-md text-ink-soft">{done}</p>
        <Button variant="outline" className="mt-5" onClick={() => { setDone(null); setMessage(""); setRating(null); setConsent(false); }}>Share something else</Button>
      </div>
    );
  }

  const input = "mt-1.5 w-full rounded-[12px] border-2 border-line bg-white px-3.5 py-3 focus:border-night focus:outline-none";
  return (
    <form onSubmit={submit} className="space-y-6" noValidate>
      <fieldset>
        <legend className="font-semibold">What would you like to share?</legend>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {KINDS.map(([k, t, hint]) => (
            <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}
              className={cn("rounded-[14px] border-2 px-4 py-3 text-left transition-colors", kind === k ? "border-night bg-jasmine" : "border-line bg-white hover:border-night")}>
              <span className="block font-semibold">{t}</span><span className="text-sm text-ink-soft">{hint}</span>
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="font-semibold">How do you feel about Virundhu overall? <span className="font-normal text-ink-soft">(optional)</span></legend>
        <div className="mt-2 flex gap-1" role="radiogroup" aria-label="Overall rating">
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} type="button" role="radio" aria-checked={rating === n} aria-label={`${n} of 5`} onClick={() => setRating(n)} className="rounded-md p-1">
              <Star className={cn("h-8 w-8", rating && n <= rating ? "fill-turmeric text-turmeric" : "text-line")} />
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="font-semibold">Which part is it about? <span className="font-normal text-ink-soft">(optional)</span></legend>
        <div className="mt-2"><Chips value={area} onChange={setArea} options={AREAS} label="Part of Virundhu" /></div>
      </fieldset>

      <label className="block">
        <span className="font-semibold">Tell us more</span>
        <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={5} maxLength={3000}
          placeholder={kind === "problem" ? "What were you trying to do, and what happened?" : kind === "idea" ? "What would make Virundhu more useful for you?" : "Write as much or as little as you like."}
          className={cn(input, "resize-none")} />
      </label>

      {publicForm ? (
        <div className="grid gap-4 sm:grid-cols-3">
          <label className="block"><span className="text-sm font-semibold">Your name <span className="font-normal text-ink-soft">(optional)</span></span><input className={input} value={who.name} onChange={(e) => setWho({ ...who, name: e.target.value })} autoComplete="name" /></label>
          <label className="block"><span className="text-sm font-semibold">Email, for a reply <span className="font-normal text-ink-soft">(optional)</span></span><input className={input} type="email" value={who.email} onChange={(e) => setWho({ ...who, email: e.target.value })} autoComplete="email" /></label>
          <label className="block"><span className="text-sm font-semibold">Restaurant <span className="font-normal text-ink-soft">(optional)</span></span><input className={input} value={who.restaurant} onChange={(e) => setWho({ ...who, restaurant: e.target.value })} /></label>
          <input tabIndex={-1} autoComplete="off" aria-hidden="true" value={who.website} onChange={(e) => setWho({ ...who, website: e.target.value })} className="absolute -left-[9999px] h-0 w-0 opacity-0" />
        </div>
      ) : null}

      {kind === "praise" ? (
        <label className="flex items-start gap-3">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1 h-5 w-5 accent-[#0c3b2e]" />
          <span>You may show these words on the Virundhu website with my name and restaurant.</span>
        </label>
      ) : null}

      {error ? <p role="alert" className="rounded-[12px] bg-chilli-soft px-3.5 py-2.5 text-sm font-semibold text-[#b32f12]">{error}</p> : null}
      <div className="flex flex-wrap items-center gap-4">
        <Button type="submit" size="lg" disabled={busy}>{busy ? <><Spinner /> Sending...</> : "Send feedback"}</Button>
        <p className="text-sm text-ink-soft">Isai, our feedback agent, reads every one within a minute.</p>
      </div>
    </form>
  );
}
