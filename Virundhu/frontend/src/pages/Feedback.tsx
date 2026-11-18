import { useQuery } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { LogoMark } from "@/components/layout/Logo";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { errorMessage, feedbackApi } from "@/services/api";


/** Public page guests reach from the QR code. No sign-in, works on any phone. */
const WORDS = ["", "Very bad", "Not good", "Okay", "Good", "Loved it"];

export default function FeedbackPage() {
  const { token = "" } = useParams();
  const { data, isLoading, isError } = useQuery({ queryKey: ["feedback-form", token], queryFn: () => feedbackApi.form(token), retry: false });
  const [rating, setRating] = useState(0);
  const [text, setText] = useState("");
  const [params] = useSearchParams();
  const fixedOutlet = Number(params.get("o")) || null; // the outlet's own QR code chooses the branch
  const [outlet, setOutlet] = useState<number | "">(fixedOutlet ?? "");
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [website, setWebsite] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ google_review_url: string | null } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!rating) { setError("Tap the stars to rate your food."); return; }
    if (rating <= 3 && text.trim().length < 3) { setError("Please tell us what went wrong, so we can fix it."); return; }
    setBusy(true); setError(null);
    try {
      setDone(await feedbackApi.send(token, { rating, text, outlet_id: outlet || null, name, contact, website }));
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }

  return (
    <main className="kolam-dark flex min-h-dvh items-start justify-center px-4 py-8 text-jasmine sm:items-center">
      <div className="w-full max-w-md">
      <div className="w-full rounded-[24px] bg-jasmine p-6 text-ink shadow-[8px_8px_0_#F6B93B] sm:p-8 animate-rise">
        {isLoading ? <div className="flex justify-center py-10"><Spinner /></div> : null}
        {isError ? <p className="py-8 text-center font-semibold">This feedback link isn't active.</p> : null}
        {data && done ? (
          <div className="py-4 text-center">
            <h1 className="font-display text-3xl font-bold">Thank you!</h1>
            <p className="mt-2 text-ink-soft">{data.restaurant} reads every message. {rating <= 3 ? "We're sorry, and we'll put it right." : "We're glad you enjoyed it."}</p>
            {done.google_review_url ? (
              <div className="mt-6 rounded-[16px] bg-white p-4">
                <p className="font-semibold">Would you also share your experience on Google?</p>
                <p className="mt-1 text-sm text-ink-soft">It helps other guests decide.</p>
                <a href={done.google_review_url} target="_blank" rel="noreferrer"><Button className="mt-3 w-full">Write a Google review</Button></a>
              </div>
            ) : null}
          </div>
        ) : null}
        {data && !done ? (
          <form onSubmit={submit} className="space-y-5" noValidate>
            <div className="flex items-center gap-3">
              <LogoMark className="h-9 w-9" />
              <div>
                <h1 className="font-display text-2xl font-bold leading-tight">{data.restaurant}</h1>
                <p className="text-sm text-ink-soft">How was your food today?</p>
              </div>
            </div>
            <div>
              <div className="flex justify-between" role="radiogroup" aria-label="Your rating">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button key={n} type="button" role="radio" aria-checked={rating === n} aria-label={`${n} star${n > 1 ? "s" : ""}`} onClick={() => setRating(n)}
                    className="rounded-full p-1.5 cursor-pointer">
                    <Star className={cn("h-11 w-11 transition-colors", n <= rating ? "fill-turmeric text-turmeric" : "text-line")} strokeWidth={1.6} />
                  </button>
                ))}
              </div>
              <p className="mt-1 h-5 text-center text-sm font-semibold">{WORDS[rating]}</p>
            </div>
            {fixedOutlet && data.outlets.some((o) => o.id === fixedOutlet) ? (
              <p className="text-sm text-ink-soft">Outlet: <b className="text-ink">{data.outlets.find((o) => o.id === fixedOutlet)?.name}</b></p>
            ) : data.outlets.length > 1 ? (
              <label className="block">
                <span className="text-sm font-semibold">Which outlet?</span>
                <select value={outlet} onChange={(e) => setOutlet(e.target.value ? Number(e.target.value) : "")}
                  className="mt-1.5 w-full rounded-[12px] border-2 border-line bg-white px-3 py-2.5">
                  <option value="">Choose...</option>
                  {data.outlets.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
              </label>
            ) : null}
            <label className="block">
              <span className="text-sm font-semibold">{rating && rating <= 3 ? "What went wrong?" : "Anything to tell us? (optional)"}</span>
              <textarea value={text} onChange={(e) => setText(e.target.value)} rows={4} maxLength={2000}
                placeholder="Write it your way: English, Tamil or Tanglish"
                className="mt-1.5 w-full resize-none rounded-[12px] border-2 border-line bg-white p-3 focus:border-night focus:outline-none" />
            </label>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="block"><span className="text-sm font-semibold">Name (optional)</span>
                <input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} className="mt-1.5 w-full rounded-[12px] border-2 border-line bg-white px-3 py-2.5" /></label>
              <label className="block"><span className="text-sm font-semibold">Phone or email (optional)</span>
                <input value={contact} onChange={(e) => setContact(e.target.value)} maxLength={120} className="mt-1.5 w-full rounded-[12px] border-2 border-line bg-white px-3 py-2.5" /></label>
            </div>
            <input tabIndex={-1} autoComplete="off" aria-hidden="true" value={website} onChange={(e) => setWebsite(e.target.value)} className="absolute -left-[9999px] h-0 w-0 opacity-0" />
            <p className="text-xs text-ink-soft">Your rating and comment go to {data.restaurant}, through Virundhu, so they can read it and put things right. Name, phone and email are optional: add them only if you'd like a reply. You can ask the restaurant to delete your feedback at any time. <a href="/privacy" target="_blank" rel="noreferrer" className="underline">Privacy Policy</a></p>
            {error ? <p role="alert" className="rounded-[12px] bg-chilli-soft px-3 py-2 text-sm font-semibold text-[#b32f12]">{error}</p> : null}
            <Button type="submit" size="lg" className="w-full" disabled={busy}>{busy ? <><Spinner /> Sending...</> : "Send feedback"}</Button>
          </form>
        ) : null}
      </div>
      </div>
    </main>
  );
}
