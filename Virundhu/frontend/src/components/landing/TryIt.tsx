import { LazyMotion, domAnimation, m } from "motion/react";
import { Check, Copy, ShieldAlert } from "lucide-react";
import { useState, type FormEvent } from "react";
import { CategoryChip, LanguageChip, SentimentChip, UrgencyChip } from "@/components/review/Tags";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/misc";
import { errorMessage, publicApi } from "@/services/api";
import type { TryResult } from "@/types";
import { trySamples } from "./samples";

/** Paste any review and watch the real AI read it. */
export function TryIt() {
  const [text, setText] = useState(trySamples[0]?.text ?? "");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<TryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (text.trim().length < 3) { setError("Type or paste a review first."); return; }
    setBusy(true); setError(null); setResult(null); setCopied(false);
    try {
      setResult(await publicApi.tryReview(text.trim()));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function copyReply() {
    if (!result) return;
    try { await navigator.clipboard.writeText(result.suggested_reply); setCopied(true); setTimeout(() => setCopied(false), 1800); } catch { /* clipboard blocked */ }
  }

  return (
    <LazyMotion features={domAnimation} strict>
      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={onSubmit} className="rounded-[20px] border-2 border-night bg-white p-5 shadow-[8px_8px_0_#0c3b2e] sm:p-6">
          <label htmlFor="try-text" className="font-display text-xl font-bold">Paste a review your restaurant got</label>
          <p className="mt-1 text-sm text-ink-soft">English, Tamil or Tanglish. Up to 500 characters.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {trySamples.map((s) => (
              <button key={s.label} type="button" onClick={() => { setText(s.text); setResult(null); setError(null); }}
                className="rounded-full border-2 border-line px-3 py-1 text-sm font-semibold text-ink-soft hover:border-night hover:text-ink cursor-pointer">
                Try {s.label}
              </button>
            ))}
          </div>
          <textarea id="try-text" value={text} maxLength={500} rows={4} onChange={(e) => setText(e.target.value)}
            className="mt-3 w-full resize-none rounded-[14px] border-2 border-line bg-jasmine/60 p-3.5 font-display text-[1.05rem] leading-snug focus:border-night focus:outline-none" />
          <div className="mt-3 flex items-center justify-between gap-3">
            <span className="tabular text-sm text-ink-soft">{text.length}/500</span>
            <Button type="submit" disabled={busy}>{busy ? <><Spinner /> Reading...</> : "Read this review"}</Button>
          </div>
        </form>

        <div className="min-h-[300px] rounded-[20px] bg-night p-5 text-jasmine sm:p-6" aria-live="polite">
          {!result && !error && !busy ? (
            <div className="flex h-full flex-col justify-center">
              <p className="font-display text-2xl font-bold">What Virundhu sends back</p>
              <ul className="mt-4 space-y-2 text-mist">
                <li>How urgent it is, so your team knows what to answer first</li>
                <li>The guest's mood and what the complaint is about</li>
                <li>One line in English, even for Tamil and Tanglish</li>
                <li>A reply draft in the guest's own language</li>
              </ul>
            </div>
          ) : null}
          {busy ? (
            <div className="flex h-full items-center justify-center gap-3 text-mist"><Spinner className="h-5 w-5" /> Reading the review...</div>
          ) : null}
          {error ? (
            <div className="flex h-full flex-col justify-center">
              <p className="font-display text-xl font-bold text-turmeric">The live reader is unavailable right now</p>
              <p className="mt-2 text-mist">{error}</p>
            </div>
          ) : null}
          {result ? (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {[<UrgencyChip key="u" urgency={result.urgency} />, <SentimentChip key="s" sentiment={result.sentiment} />,
                  <CategoryChip key="c" category={result.category} />, <LanguageChip key="l" language={result.language} />].map((c, i) => (
                  <m.span key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>{c}</m.span>
                ))}
              </div>
              {result.food_safety ? (
                <m.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-start gap-2 rounded-[12px] bg-chilli/15 p-3 text-sm font-medium text-[#ffb3a3]">
                  <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" /> Food-safety words found, so this always goes to Reply today and the owner gets an email.
                </m.p>
              ) : null}
              <m.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.35 }}>
                <p className="text-sm text-mist">In one line</p>
                <p className="font-display text-xl font-semibold">{result.summary}</p>
              </m.div>
              <m.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="rounded-[14px] bg-white/[0.06] p-4">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <p className="text-sm text-mist">Reply draft</p>
                  <button onClick={copyReply} className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-semibold text-turmeric hover:bg-white/10 cursor-pointer">
                    {copied ? <><Check className="h-4 w-4" /> Copied</> : <><Copy className="h-4 w-4" /> Copy reply</>}
                  </button>
                </div>
                <p className="leading-relaxed">{result.suggested_reply}</p>
              </m.div>
            </div>
          ) : null}
        </div>
      </div>
    </LazyMotion>
  );
}
