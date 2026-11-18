import { AnimatePresence, LazyMotion, domAnimation, m } from "motion/react";
import { Check, X } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const BEFORE = [
  "Three apps to check, one outlet at a time",
  "Tamil and Tanglish reviews skimmed or missed",
  "A food-safety complaint found 4 days later",
  "Most reviews never get a reply",
  "No idea which outlet or which problem is hurting sales",
];
const AFTER = [
  "Google, your QR feedback, Zomato and Swiggy in one inbox",
  "Every review read and summarised in English",
  "Serious complaints alert you within a minute",
  "Replies ready in the guest's language; happy Google reviews answered by themselves",
  "Priority 1, 2, 3: what to fix first, per outlet",
];

function BeforeVisual() {
  return (
    <div className="relative">
      <div className="grid grid-cols-3 gap-3">
        {[["Google", 23], ["Zomato", 41], ["Swiggy", 37]].map(([name, n], i) => (
          <div key={name as string} className="relative rounded-[18px] border-2 border-dashed border-ink/20 bg-white p-4 text-center" style={{ transform: `rotate(${[-3, 2, -1.5][i]}deg)` }}>
            <span className="absolute -right-2 -top-2 rounded-full bg-chilli px-2 py-0.5 text-xs font-bold text-white">{n}</span>
            <p className="font-display text-lg font-bold">{name}</p>
            <p className="text-xs text-ink-soft">x 3 outlets</p>
          </div>
        ))}
      </div>
      <div className="mt-5 rotate-[1deg] rounded-[16px] border-2 border-ink/15 bg-white p-4 opacity-80">
        <div className="flex items-center justify-between text-sm"><span className="text-ink-soft">1★ · Zomato · Anna Nagar</span><span className="rounded-full bg-chilli-soft px-2 py-0.5 text-xs font-semibold text-[#b32f12]">Seen 4 days later</span></div>
        <p className="mt-1">"Family vomited after eating the chicken 65."</p>
        <p className="mt-2 text-sm text-ink-soft">No reply.</p>
      </div>
    </div>
  );
}

function AfterVisual() {
  return (
    <div className="rounded-[20px] border-2 border-night bg-white p-4 shadow-[6px_6px_0_#0c3b2e]">
      <div className="flex gap-2 text-sm font-semibold">
        <span className="rounded-full bg-chilli px-3 py-1 text-white">Reply today 2</span>
        <span className="rounded-full bg-turmeric px-3 py-1 text-night">This week 5</span>
        <span className="rounded-full bg-leaf px-3 py-1 text-white">All good 94</span>
      </div>
      {[
        ["Food-safety complaint", "Anna Nagar · Zomato · 2 min ago", "bg-chilli"],
        ["Delivery 70 min late", "RS Puram · Swiggy · 1 hour ago", "bg-turmeric"],
        ["Loved the biryani, replied automatically", "KK Nagar · Google · today", "bg-leaf"],
      ].map(([t, sub, c]) => (
        <div key={t} className="mt-3 flex items-center gap-3 rounded-[12px] bg-jasmine px-3 py-2.5">
          <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", c)} />
          <div className="min-w-0"><p className="truncate font-semibold">{t}</p><p className="text-xs text-ink-soft">{sub}</p></div>
        </div>
      ))}
    </div>
  );
}

/** Toggle between a normal day without Virundhu and with it. */
export function BeforeAfter() {
  const [after, setAfter] = useState(false);
  const list = after ? AFTER : BEFORE;
  return (
    <LazyMotion features={domAnimation}>
      <div className="inline-flex rounded-full bg-jasmine-2 p-1.5" role="radiogroup" aria-label="Compare">
        {[false, true].map((v) => (
          <button key={String(v)} role="radio" aria-checked={after === v} onClick={() => setAfter(v)}
            className={cn("rounded-full px-5 py-2.5 font-semibold transition-colors cursor-pointer",
              after === v ? (v ? "bg-leaf text-white" : "bg-chilli text-white") : "text-ink-soft hover:text-ink")}>
            {v ? "With Virundhu" : "A day without Virundhu"}
          </button>
        ))}
      </div>
      <AnimatePresence mode="wait">
        <m.div key={String(after)} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }}
          className="mt-8 grid items-center gap-8 lg:grid-cols-2">
          <ul className="space-y-3">
            {list.map((t) => (
              <li key={t} className="flex gap-3 text-[1.1rem]">
                <span className={cn("mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full", after ? "bg-leaf text-white" : "bg-chilli-soft text-chilli")}>
                  {after ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
                </span>
                {t}
              </li>
            ))}
          </ul>
          {after ? <AfterVisual /> : <BeforeVisual />}
        </m.div>
      </AnimatePresence>
    </LazyMotion>
  );
}
