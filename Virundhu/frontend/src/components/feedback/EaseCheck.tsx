import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, X } from "lucide-react";
import { useState } from "react";
import { useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { errorMessage, productFeedbackApi } from "@/services/api";
import { AREAS, Chips } from "./FeedbackForm";

const FACES: [number, string][] = [[1, "Very hard"], [2, "Hard"], [3, "Okay"], [4, "Easy"], [5, "Very easy"]];
const SNOOZE_KEY = "virundhu.ease.snoozed";

/** "How easy is Virundhu to use?": three quick questions. Used as a page section and as a corner prompt. */
export function EaseCheck({ onDone, compact = false }: { onDone?: () => void; compact?: boolean }) {
  const { pathname } = useLocation();
  const [ease, setEase] = useState<number | null>(null);
  const [nps, setNps] = useState<number | null>(null);
  const [area, setArea] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  async function send() {
    if (!ease) { setError("Pick how easy it feels first."); return; }
    setBusy(true); setError(null);
    try {
      const r = await productFeedbackApi.ease({ ease, nps, area, message: message.trim(), page: pathname });
      setDone(r.message);
      onDone?.();
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }

  if (done) return <p className="flex items-center gap-2 font-semibold text-leaf"><CheckCircle2 className="h-5 w-5" /> {done}</p>;
  return (
    <div className="space-y-5">
      <fieldset>
        <legend className="font-semibold">How easy is Virundhu to use?</legend>
        <div role="radiogroup" aria-label="How easy" className={cn("mt-2 grid gap-2", compact ? "grid-cols-5" : "grid-cols-5 sm:max-w-xl")}>
          {FACES.map(([n, label]) => (
            <button key={n} type="button" role="radio" aria-checked={ease === n} onClick={() => setEase(n)}
              className={cn("rounded-[12px] border-2 px-1 py-2.5 text-center transition-colors", ease === n ? (n <= 2 ? "border-chilli bg-chilli-soft" : n === 3 ? "border-turmeric bg-jasmine" : "border-leaf bg-[#e6f4ea]") : "border-line bg-white hover:border-night")}>
              <span className="block font-display text-xl font-bold">{n}</span>
              <span className="block text-[11px] leading-tight text-ink-soft">{label}</span>
            </button>
          ))}
        </div>
      </fieldset>
      {ease ? (
        <>
          <fieldset>
            <legend className="font-semibold">How likely are you to recommend it to another restaurant owner?</legend>
            <div role="radiogroup" aria-label="Recommend, 0 to 10" className="mt-2 flex flex-wrap gap-1.5">
              {Array.from({ length: 11 }, (_, n) => (
                <button key={n} type="button" role="radio" aria-checked={nps === n} onClick={() => setNps(n)}
                  className={cn("h-9 w-9 rounded-[10px] border-2 text-sm font-bold", nps === n ? "border-night bg-night text-jasmine" : "border-line bg-white hover:border-night")}>{n}</button>
              ))}
            </div>
            <p className="mt-1 flex justify-between text-xs text-ink-soft sm:max-w-[470px]"><span>Not likely</span><span>Very likely</span></p>
          </fieldset>
          <fieldset>
            <legend className="font-semibold">{ease <= 3 ? "Which part felt hard?" : "Which part do you use most?"} <span className="font-normal text-ink-soft">(optional)</span></legend>
            <div className="mt-2"><Chips value={area} onChange={setArea} options={AREAS} label="Part of Virundhu" /></div>
          </fieldset>
          <label className="block">
            <span className="font-semibold">{ease <= 3 ? "What was hard or confusing?" : "Anything that would make it even easier?"} <span className="font-normal text-ink-soft">(optional)</span></span>
            <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={compact ? 2 : 3} maxLength={2000}
              className="mt-1.5 w-full resize-none rounded-[12px] border-2 border-line bg-white p-3 focus:border-night focus:outline-none" />
          </label>
        </>
      ) : null}
      {error ? <p role="alert" className="text-sm font-semibold text-[#b32f12]">{error}</p> : null}
      <Button onClick={send} disabled={busy || !ease}>{busy ? <><Spinner /> Sending...</> : "Send"}</Button>
    </div>
  );
}

function snoozed(): boolean {
  try { return Number(localStorage.getItem(SNOOZE_KEY) ?? 0) > Date.now(); } catch { return false; }
}

/** Corner card that asks the ease questions after a few days of use, at most monthly. */
export function EasePrompt() {
  const q = useQuery({ queryKey: ["ease-prompt"], queryFn: productFeedbackApi.easePrompt, staleTime: 3_600_000 });
  const [hidden, setHidden] = useState(snoozed);
  if (!q.data?.due || hidden) return null;
  const close = () => {
    try { localStorage.setItem(SNOOZE_KEY, String(Date.now() + 7 * 86_400_000)); } catch { /* storage may be off */ }
    setHidden(true);
  };
  return (
    <aside aria-label="Quick question" className="fixed bottom-24 right-4 z-40 max-h-[calc(100vh-8rem)] w-[min(380px,calc(100vw-2rem))] overflow-y-auto rounded-[20px] border-2 border-night bg-white p-5 shadow-[6px_6px_0_#0c3b2e]">
      <button type="button" onClick={close} aria-label="Not now" className="absolute right-3 top-3 rounded-full p-1 text-ink-soft hover:text-night"><X className="h-5 w-5" /></button>
      <p className="pr-6 text-sm text-ink-soft">A quick question, 20 seconds</p>
      <div className="mt-3"><EaseCheck compact onDone={() => setTimeout(close, 4000)} /></div>
    </aside>
  );
}
