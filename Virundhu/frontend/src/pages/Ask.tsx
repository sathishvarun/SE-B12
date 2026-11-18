import { ArrowUp, MessageCircleQuestion, RotateCcw } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Spinner } from "@/components/ui/misc";
import { useWorkspace } from "@/lib/workspace";
import { cn } from "@/lib/utils";
import { assistantApi, errorMessage } from "@/services/api";

interface Turn { role: "user" | "assistant"; text: string; failed?: boolean }

const STARTERS = [
  "What should I fix first this week? Give me priority 1, 2 and 3.",
  "Which outlet is doing worst and why?",
  "Any food-safety complaints I haven't replied to?",
  "What are guests happiest about?",
];

/** Ask Virundhu: plain questions about the last 30 days of reviews. Numbers come from the server, not the model. */
export default function Ask() {
  const { org } = useWorkspace();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns, busy]);

  async function send(message: string) {
    const q = message.trim();
    if (!q || busy) return;
    const history = turns.filter((t) => !t.failed).map(({ role, text: t }) => ({ role, text: t }));
    setTurns((prev) => [...prev, { role: "user", text: q }]);
    setText("");
    setBusy(true);
    try {
      const { answer } = await assistantApi.chat(q, history);
      setTurns((prev) => [...prev, { role: "assistant", text: answer }]);
    } catch (err) {
      setTurns((prev) => [...prev, { role: "assistant", text: errorMessage(err), failed: true }]);
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) { e.preventDefault(); void send(text); }

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-9rem)] max-w-3xl flex-col">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[2.3rem] font-bold">Ask Virundhu</h1>
          <p className="mt-1 max-w-xl text-ink-soft">Ask anything about {org?.name ?? "your restaurant"}'s reviews from the last 30 days, in English, Tamil or Tanglish.</p>
        </div>
        {turns.length ? (
          <button onClick={() => setTurns([])} className="flex items-center gap-1.5 text-sm font-semibold text-ink-soft hover:text-ink cursor-pointer">
            <RotateCcw className="h-4 w-4" /> New conversation
          </button>
        ) : null}
      </div>

      <div className="mt-6 flex-1 space-y-4">
        {!turns.length ? (
          <div className="rounded-[20px] border-2 border-dashed border-line bg-white p-5 sm:p-6">
            <p className="flex items-center gap-2 font-semibold"><MessageCircleQuestion className="h-5 w-5 text-turmeric" /> Try one of these</p>
            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
              {STARTERS.map((s) => (
                <button key={s} onClick={() => void send(s)}
                  className="rounded-[14px] bg-jasmine px-4 py-3 text-left font-medium hover:bg-turmeric/30 cursor-pointer">{s}</button>
              ))}
            </div>
            <p className="mt-4 text-sm text-ink-soft">Answers use only your own reviews. Every number is counted by Virundhu, not guessed.</p>
          </div>
        ) : null}
        {turns.map((t, i) => (
          <div key={i} className={cn("flex", t.role === "user" ? "justify-end" : "justify-start")}>
            <div className={cn("max-w-[88%] whitespace-pre-wrap rounded-[18px] px-4 py-3 leading-relaxed",
              t.role === "user" ? "bg-night text-jasmine" : t.failed ? "bg-chilli-soft text-[#b32f12]" : "border-2 border-line bg-white")}>
              {t.text}
            </div>
          </div>
        ))}
        {busy ? <div className="flex items-center gap-2 text-ink-soft"><Spinner /> Reading your reviews...</div> : null}
        <div ref={end} />
      </div>

      <form onSubmit={onSubmit} className="sticky bottom-24 mt-6 flex items-end gap-2 rounded-[20px] border-2 border-night bg-white p-2 lg:bottom-4">
        <label htmlFor="ask" className="sr-only">Your question</label>
        <textarea id="ask" rows={1} value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask about your reviews..."
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(text); } }}
          className="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent px-3 py-2.5 focus:outline-none" />
        <button type="submit" disabled={busy || !text.trim()} aria-label="Send"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[14px] bg-turmeric text-night disabled:opacity-40 cursor-pointer">
          <ArrowUp className="h-5 w-5" />
        </button>
      </form>
    </div>
  );
}
