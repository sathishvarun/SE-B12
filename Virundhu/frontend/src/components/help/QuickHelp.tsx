import { HelpCircle, Send, UserRound, X } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, errorMessage } from "@/services/api";
import { cn } from "@/lib/utils";

interface Msg { from: "user" | "bot"; text: string; covered?: boolean; topic?: string }

const STARTERS = ["How do I connect Google?", "Why can't I connect Zomato or Swiggy?", "I paid but my plan isn't active",
  "Emails are not arriving", "How do QR codes work?", "How do I delete my account?"];

/** Quick help: answers from Virundhu's help guide; hands over to a person when it can't. */
export function QuickHelp({ signedIn }: { signedIn: boolean }) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([{ from: "bot", text: "Hi! Ask me anything about Virundhu: connecting Google, Zomato or Swiggy, QR codes, payments, sign-in. If I can't help, I'll pass you to a person." }]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [handover, setHandover] = useState(false);
  const [contact, setContact] = useState({ name: "", email: "", message: "" });
  const [done, setDone] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs, handover, done]);

  const history = () => msgs.slice(1).map((m) => ({ from: m.from, text: m.text }));
  const lastTopic = [...msgs].reverse().find((m) => m.topic)?.topic ?? "other";

  async function ask(text: string) {
    const question = text.trim();
    if (!question || busy) return;
    setQ("");
    setMsgs((m) => [...m, { from: "user", text: question }]);
    setBusy(true);
    try {
      const r = await api.post<{ answer: string; covered: boolean; topic: string }>("/api/v1/help/ask", { question, history: history() }).then((x) => x.data);
      setMsgs((m) => [...m, { from: "bot", text: r.answer, covered: r.covered, topic: r.topic }]);
      if (!r.covered) setHandover(true);
    } catch (e) {
      setMsgs((m) => [...m, { from: "bot", text: `Sorry, I couldn't answer just now (${errorMessage(e)}). You can talk to a person instead.`, covered: false }]);
      setHandover(true);
    } finally { setBusy(false); }
  }

  async function sendToPerson(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    const lastQuestion = [...msgs].reverse().find((m) => m.from === "user")?.text ?? "";
    try {
      if (signedIn) {
        const r = await api.post<{ number: string }>("/api/v1/help/handover", { message: contact.message || lastQuestion || "Please help", topic: lastTopic, history: history() }).then((x) => x.data);
        setDone(`Sent to our team as request ${r.number}. You'll get a reply by email within 24 hours, and you can follow it in Help and support.`);
      } else {
        await api.post("/api/v1/help/contact", { name: contact.name, email: contact.email, message: contact.message || lastQuestion || "Please contact me", history: history() });
        setDone("Thank you. A person will reply to your email within 24 hours.");
      }
      setHandover(false);
    } catch (err) { setMsgs((m) => [...m, { from: "bot", text: errorMessage(err) }]); } finally { setBusy(false); }
  }

  return (
    <>
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls="quick-help"
        className={cn("fixed right-4 z-[60] flex h-12 items-center gap-2 rounded-full bg-night px-4 font-semibold text-jasmine shadow-lg cursor-pointer", signedIn ? "bottom-20 lg:bottom-5" : "bottom-5")}>
        {open ? <X className="h-5 w-5" /> : <HelpCircle className="h-5 w-5" />} {open ? "Close" : "Quick help"}
      </button>
      {open ? (
        <section id="quick-help" role="dialog" aria-label="Quick help"
          className={cn("fixed right-4 z-[60] flex max-h-[min(70dvh,560px)] w-[min(380px,calc(100vw-2rem))] flex-col overflow-hidden rounded-[20px] border-2 border-line bg-white shadow-2xl", signedIn ? "bottom-36 lg:bottom-20" : "bottom-20")}>
          <header className="bg-night px-4 py-3 text-jasmine"><p className="font-display text-lg font-bold">Quick help</p><p className="text-xs text-mist">Answers from the Virundhu guide. A person is one tap away.</p></header>
          <div className="flex-1 space-y-2 overflow-y-auto p-3" aria-live="polite">
            {msgs.map((m, i) => (
              <p key={i} className={cn("max-w-[88%] whitespace-pre-wrap rounded-[14px] px-3 py-2 text-[0.93rem]", m.from === "user" ? "ml-auto bg-turmeric/30" : "bg-jasmine")}>{m.text}</p>
            ))}
            {msgs.length === 1 ? (
              <div className="flex flex-wrap gap-1.5 pt-1">{STARTERS.map((s) => <button key={s} onClick={() => void ask(s)} className="rounded-full border-2 border-line px-2.5 py-1.5 text-xs font-semibold cursor-pointer hover:border-night">{s}</button>)}</div>
            ) : null}
            {busy ? <p className="text-sm text-ink-soft">Thinking...</p> : null}
            {done ? <p className="rounded-[14px] bg-leaf-soft px-3 py-2 text-sm font-medium text-[#16784a]">{done}</p> : null}
            {handover && !done ? (
              <form onSubmit={sendToPerson} className="space-y-2 rounded-[14px] border-2 border-line p-3">
                <p className="text-sm font-semibold">Talk to a person</p>
                {!signedIn ? (
                  <>
                    <input aria-label="Your name" placeholder="Your name" required minLength={2} value={contact.name} onChange={(e) => setContact({ ...contact, name: e.target.value })} className="h-10 w-full rounded-[10px] border-2 border-line px-2 text-sm" />
                    <input aria-label="Your email" type="email" placeholder="Your email" required value={contact.email} onChange={(e) => setContact({ ...contact, email: e.target.value })} className="h-10 w-full rounded-[10px] border-2 border-line px-2 text-sm" />
                  </>
                ) : null}
                <textarea aria-label="Anything to add" placeholder="Anything to add? (optional)" rows={2} value={contact.message} onChange={(e) => setContact({ ...contact, message: e.target.value })} className="w-full rounded-[10px] border-2 border-line p-2 text-sm" />
                <button disabled={busy} className="flex h-10 items-center gap-1.5 rounded-[10px] bg-night px-3 text-sm font-semibold text-jasmine cursor-pointer disabled:opacity-60"><UserRound className="h-4 w-4" /> Send to our team</button>
              </form>
            ) : null}
            <div ref={endRef} />
          </div>
          <form onSubmit={(e) => { e.preventDefault(); void ask(q); }} className="flex gap-2 border-t-2 border-jasmine-2 p-2">
            <input aria-label="Your question" value={q} onChange={(e) => setQ(e.target.value)} maxLength={1000} placeholder="Type your question" className="h-11 flex-1 rounded-[12px] border-2 border-line px-3" />
            <button aria-label="Send question" disabled={busy || !q.trim()} className="grid h-11 w-11 place-items-center rounded-[12px] bg-turmeric cursor-pointer disabled:opacity-50"><Send className="h-4 w-4" /></button>
          </form>
          {!handover && !done && msgs.length > 2 ? <button onClick={() => setHandover(true)} className="border-t-2 border-jasmine-2 py-2 text-sm font-semibold underline cursor-pointer">Didn't help? Talk to a person</button> : null}
        </section>
      ) : null}
    </>
  );
}
