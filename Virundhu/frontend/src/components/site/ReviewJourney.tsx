import { AnimatePresence, LazyMotion, domAnimation, m, useReducedMotion } from "motion/react";
import { Bell, Check, MessageCircle, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const STEPS = [
  { title: "A guest writes a review", body: "9:42 pm. A delivery guest is upset and writes in Tanglish on a delivery app." },
  { title: "It reaches Virundhu", body: "Google and your own QR link arrive by themselves. Zomato and Swiggy reviews are pasted in." },
  { title: "Read in seconds", body: "Mood, topic, language and urgency, plus one line in English, even for Tamil and Tanglish." },
  { title: "You hear at once", body: "A food-safety complaint alerts the owner on the bell, by email and on WhatsApp, a minute later." },
  { title: "The reply is ready", body: "A polite reply in the guest's own language. Happy Google reviews are answered by themselves." },
  { title: "You fix the cause", body: "The dashboard and Ask Virundhu show which outlet and which problem to fix first." },
] as const;

const TAGS = [
  { label: "Unhappy", cls: "bg-chilli-soft text-[#b32f12]" },
  { label: "Hygiene", cls: "bg-chilli text-white" },
  { label: "Tanglish", cls: "bg-lotus-soft text-[#a3245f]" },
  { label: "Reply today", cls: "bg-night text-turmeric" },
];

function ReviewCard({ children, className }: { children?: React.ReactNode; className?: string }) {
  return (
    <div className={cn("rounded-[18px] border-2 border-night bg-white p-4 text-ink shadow-[6px_6px_0_#0c3b2e]", className)}>
      <div className="flex items-center justify-between text-sm text-ink-soft">
        <span>Delivery app review, RS Puram</span>
        <span className="flex text-turmeric">{[1, 2, 3, 4, 5].map((n) => <Star key={n} className={cn("h-4 w-4", n <= 1 ? "fill-turmeric" : "text-line")} />)}</span>
      </div>
      <p className="mt-2 font-display text-[1.25rem] font-medium leading-snug">"Chicken la mudi irundhuchu. Very disgusting, need refund."</p>
      {children}
    </div>
  );
}

function Stage({ step }: { step: number }) {
  switch (step) {
    case 0:
      return (
        <div className="mx-auto w-[260px] rounded-[34px] border-[6px] border-jasmine bg-jasmine-2 p-3 text-ink shadow-[10px_10px_0_#f6b93b]">
          <div className="mx-auto mb-3 h-1.5 w-16 rounded-full bg-night/20" />
          <p className="px-1 text-xs font-semibold text-ink-soft">Rate your order</p>
          <div className="mt-2 flex gap-1 px-1">{[1, 2, 3, 4, 5].map((n) => <Star key={n} className={cn("h-6 w-6", n <= 1 ? "fill-chilli text-chilli" : "text-line")} />)}</div>
          <div className="mt-3 rounded-[14px] bg-white p-3 text-[0.95rem] leading-snug">Chicken la mudi irundhuchu. Very disgusting, need refund.</div>
          <div className="mt-3 rounded-[12px] bg-night py-2 text-center text-sm font-semibold text-jasmine">Submit · 9:42 pm</div>
        </div>
      );
    case 1:
      return (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[["Google", "auto", false], ["Your QR", "auto", false], ["Zomato", "paste", false], ["Swiggy", "paste", true]].map(([name, how, active]) => (
              <div key={name as string} className={cn("rounded-[14px] border-2 px-3 py-2.5 text-center", active ? "border-turmeric bg-turmeric/20" : "border-white/15 bg-white/5")}>
                <p className="font-semibold">{name}</p>
                <p className="text-xs text-mist">{how === "auto" ? "arrives by itself" : "pasted in"}</p>
              </div>
            ))}
          </div>
          <m.div initial={{ y: -16, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.3 }}>
            <ReviewCard><p className="mt-3 text-sm text-ink-soft">Reading...</p></ReviewCard>
          </m.div>
        </div>
      );
    case 2:
      return (
        <ReviewCard>
          <div className="mt-3 flex flex-wrap gap-2">
            {TAGS.map((t, i) => (
              <m.span key={t.label} initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: 0.15 + i * 0.18 }}
                className={cn("rounded-full px-3 py-1 text-sm font-semibold", t.cls)}>{t.label}</m.span>
            ))}
          </div>
          <m.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.95 }} className="mt-3 rounded-[12px] bg-jasmine px-3 py-2 text-sm">
            <span className="text-ink-soft">In one line: </span><b>Hair found in the chicken; wants a refund.</b>
          </m.p>
        </ReviewCard>
      );
    case 3:
      return (
        <div className="space-y-3">
          {[
            { icon: <MessageCircle className="h-5 w-5" />, app: "WhatsApp", tint: "bg-leaf" },
            { icon: <Bell className="h-5 w-5" />, app: "Virundhu", tint: "bg-chilli" },
          ].map((n, i) => (
            <m.div key={n.app} initial={{ x: 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 0.15 + i * 0.3 }}
              className="flex items-start gap-3 rounded-[18px] bg-white p-4 text-ink shadow-lg">
              <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] text-white", n.tint)}>{n.icon}</span>
              <div>
                <p className="text-xs text-ink-soft">{n.app} · 9:43 pm</p>
                <p className="font-semibold">Food-safety complaint at RS Puram</p>
                <p className="text-sm text-ink-soft">Hair found in the chicken; wants a refund. Call the outlet today.</p>
              </div>
            </m.div>
          ))}
          <p className="text-center text-sm text-mist">One minute after the guest pressed submit.</p>
        </div>
      );
    case 4:
      return (
        <ReviewCard>
          <div className="mt-3 rounded-[14px] border-2 border-leaf/40 bg-leaf-soft p-3">
            <p className="text-xs font-semibold text-[#1d7a4d]">Reply draft, in the guest's language</p>
            <m.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="mt-1 text-[0.98rem] leading-snug">
              Romba sorry sir. Idhu namma standard illa. RS Puram kitchen-la ippove check panrom, refund-um arrange panrom. Ungala call panrom. - Team Vaasam
            </m.p>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <span className="rounded-[10px] bg-turmeric px-3 py-1.5 font-semibold text-night">Post on Google</span>
            <span className="rounded-[10px] bg-jasmine-2 px-3 py-1.5 font-semibold">Copy and open Swiggy</span>
          </div>
          <p className="mt-3 flex items-center gap-2 text-sm text-ink-soft"><Check className="h-4 w-4 text-leaf" /> Happy 4-5 star Google reviews are answered by themselves</p>
        </ReviewCard>
      );
    default:
      return (
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-[18px] bg-white p-4 text-ink">
            <p className="text-sm font-semibold text-ink-soft">What guests complained about</p>
            {[["Hygiene", 6, "bg-chilli"], ["Delivery", 4, "bg-turmeric"], ["Packaging", 2, "bg-sky"]].map(([label, n, c], i) => (
              <div key={label as string} className="mt-3">
                <div className="flex justify-between text-sm"><span>{label}</span><b className="tabular">{n}</b></div>
                <div className="mt-1 h-2.5 rounded-full bg-jasmine-2">
                  <m.div initial={{ width: 0 }} animate={{ width: `${(Number(n) / 6) * 100}%` }} transition={{ delay: 0.2 + i * 0.15, duration: 0.6 }} className={cn("h-full rounded-full", c as string)} />
                </div>
              </div>
            ))}
          </div>
          <div className="rounded-[18px] bg-white p-4 text-ink">
            <p className="text-sm font-semibold text-ink-soft">Ask Virundhu</p>
            <p className="mt-2 rounded-[12px] bg-night px-3 py-2 text-sm text-jasmine">What should I fix first?</p>
            <m.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="mt-2 rounded-[12px] bg-jasmine px-3 py-2 text-sm leading-snug">
              <b>Priority 1:</b> hygiene at RS Puram, 6 complaints this week. Check the kitchen today.
            </m.p>
          </div>
        </div>
      );
  }
}

/** The signature moment: follow one real-looking review from the guest's phone to the owner's fix. */
export function ReviewJourney() {
  const reduce = useReducedMotion() ?? false;
  const [step, setStep] = useState(0);
  const [auto, setAuto] = useState(!reduce);

  useEffect(() => {
    if (!auto) return;
    const t = window.setTimeout(() => setStep((s) => (s + 1) % STEPS.length), 4200);
    return () => window.clearTimeout(t);
  }, [step, auto]);

  return (
    <LazyMotion features={domAnimation}>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-12">
        <ol className="space-y-2" role="tablist" aria-label="One review, step by step">
          {STEPS.map((s, i) => (
            <li key={s.title}>
              <button role="tab" aria-selected={step === i} onClick={() => { setStep(i); setAuto(false); }}
                className={cn("relative w-full overflow-hidden rounded-[16px] px-4 py-3 text-left transition-colors cursor-pointer",
                  step === i ? "bg-white/10" : "hover:bg-white/5")}>
                <span className="flex items-start gap-3">
                  <span className={cn("mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-display font-bold",
                    step === i ? "bg-turmeric text-night" : i < step ? "bg-leaf text-white" : "bg-white/10 text-mist")}>
                    {i < step ? <Check className="h-4 w-4" /> : i + 1}
                  </span>
                  <span>
                    <span className={cn("block text-[1.1rem] font-semibold", step === i ? "text-white" : "text-mist")}>{s.title}</span>
                    {step === i ? <span className="mt-1 block text-mist">{s.body}</span> : null}
                  </span>
                </span>
                {step === i && auto ? (
                  <m.span key={`bar-${step}`} initial={{ width: 0 }} animate={{ width: "100%" }} transition={{ duration: 4.2, ease: "linear" }}
                    className="absolute bottom-0 left-0 h-[3px] bg-turmeric" aria-hidden="true" />
                ) : null}
              </button>
            </li>
          ))}
          <li className="px-4 pt-2">
            <button onClick={() => setAuto((a) => !a)} className="-mx-2 min-h-11 rounded-[10px] px-2 text-sm font-semibold text-turmeric hover:underline cursor-pointer">
              {auto ? "Pause the story" : "Play the story"}
            </button>
          </li>
        </ol>
        <div className="flex min-h-[380px] items-center rounded-[26px] border-2 border-white/10 bg-night-2 p-5 sm:p-8" aria-live="polite">
          <AnimatePresence mode="wait">
            <m.div key={step} className="w-full" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3 }}>
              <Stage step={step} />
            </m.div>
          </AnimatePresence>
        </div>
      </div>
    </LazyMotion>
  );
}

