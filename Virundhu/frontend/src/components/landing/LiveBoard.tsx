import { AnimatePresence, LayoutGroup, LazyMotion, domMax, m, useReducedMotion } from "motion/react";
import { Pause, Play } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Chip, Stars } from "@/components/ui/misc";
import { UrgencyChip } from "@/components/review/Tags";
import { sentimentTone } from "@/lib/tones";
import { categoryLabel, languageLabel, platformLabel, sentimentLabel } from "@/lib/copy";
import { cn } from "@/lib/utils";
import type { Urgency } from "@/types";
import { streamReviews, type SampleReview } from "./samples";

const LANES: { key: Urgency; title: string; color: string; ring: string }[] = [
  { key: "high", title: "Reply today", color: "bg-chilli", ring: "border-chilli/60" },
  { key: "medium", title: "This week", color: "bg-turmeric", ring: "border-turmeric/60" },
  { key: "low", title: "All good", color: "bg-leaf", ring: "border-leaf/60" },
];

type Phase = "reading" | "tagged";
interface Placed extends SampleReview { key: string }

const initialLanes = (): Record<Urgency, Placed[]> => ({ high: [], medium: [], low: [] });

/** The hero: reviews arrive, get read, and drop into the right lane. */
export function LiveBoard({ compact = false }: { compact?: boolean }) {
  const reduce = useReducedMotion() ?? false;
  const [liveLanes, setLanes] = useState(initialLanes);
  const [liveCounts, setCounts] = useState<Record<Urgency, number>>({ high: 0, medium: 0, low: 0 });
  const [step, setStep] = useState(0);
  const [phase, setPhase] = useState<Phase>("reading");
  const [paused, setPaused] = useState(false);
  const current = streamReviews[step % streamReviews.length] as SampleReview;
  const currentKey = `${current.id}-${step}`;

  // Reduced motion: a static, fully sorted board instead of the animation.
  const staticBoard = useMemo(() => {
    const filled = initialLanes();
    streamReviews.forEach((r, i) => filled[r.urgency].unshift({ ...r, key: `${r.id}-${i}` }));
    return { lanes: filled, counts: { high: filled.high.length, medium: filled.medium.length, low: filled.low.length } };
  }, []);
  const lanes = reduce ? staticBoard.lanes : liveLanes;
  const counts = reduce ? staticBoard.counts : liveCounts;

  useEffect(() => {
    if (reduce || paused) return;
    const t = window.setTimeout(() => {
      if (phase === "reading") { setPhase("tagged"); return; }
      setLanes((prev) => ({ ...prev, [current.urgency]: [{ ...current, key: currentKey }, ...prev[current.urgency]].slice(0, compact ? 2 : 3) }));
      setCounts((c) => ({ ...c, [current.urgency]: c[current.urgency] + 1 }));
      setStep((s) => s + 1);
      setPhase("reading");
    }, phase === "reading" ? 1100 : 1700);
    return () => window.clearTimeout(t);
  }, [phase, paused, reduce, current, currentKey, compact]);

  return (
    <LazyMotion features={domMax} strict>
      <LayoutGroup>
        <div className={cn("relative rounded-[22px] border border-white/10 bg-night-2/80 p-4 text-jasmine shadow-[0_30px_80px_-30px_rgba(0,0,0,0.7)] backdrop-blur sm:p-5", compact && "p-3 sm:p-4")}
          onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
          <div className="flex items-center justify-between gap-3">
            <p className="flex items-center gap-2 text-sm font-semibold text-mist">
              <span className="h-2 w-2 rounded-full bg-leaf animate-pulse-dot" aria-hidden="true" />
              {reduce ? "Example week, sorted" : paused ? "Paused" : "Example: reviews coming in"}
            </p>
            {!reduce && !compact ? (
              <button onClick={() => setPaused((p) => !p)} className="rounded-full p-1.5 text-mist hover:bg-white/10 hover:text-white cursor-pointer"
                aria-label={paused ? "Play the demo" : "Pause the demo"}>
                {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
              </button>
            ) : null}
          </div>

          {/* Incoming review */}
          {!reduce ? (
            <div className="mt-3 min-h-[148px]">
              <AnimatePresence mode="popLayout">
                <m.article key={currentKey} layoutId={currentKey} layout
                  initial={{ opacity: 0, y: -24, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: "spring", stiffness: 260, damping: 26 }}
                  className="rounded-[16px] bg-jasmine p-4 text-ink">
                  <div className="flex items-center justify-between text-[0.8rem] text-ink-soft">
                    <span className="font-semibold">{platformLabel[current.platform]}, {current.outlet}</span>
                    <Stars rating={current.rating} className="text-ink" />
                  </div>
                  <p className={cn("mt-1.5 font-display font-medium leading-snug", compact ? "text-[1rem]" : "text-[1.12rem]")}>{current.text}</p>
                  <div className="mt-2.5 flex min-h-[26px] flex-wrap items-center gap-1.5">
                    {phase === "reading" ? (
                      <span className="flex items-center gap-2 text-sm font-medium text-ink-soft">
                        <span className="flex gap-1">{[0, 1, 2].map((d) => <span key={d} className="h-1.5 w-1.5 rounded-full bg-ink-soft animate-pulse-dot" style={{ animationDelay: `${d * 0.2}s` }} />)}</span>
                        Reading in {languageLabel[current.language]}
                      </span>
                    ) : (
                      <>
                        {[<UrgencyChip key="u" urgency={current.urgency} />,
                          <Chip key="s" tone={sentimentTone[current.sentiment]}>{sentimentLabel[current.sentiment]}</Chip>,
                          <Chip key="c">{categoryLabel[current.category]}</Chip>].map((chip, i) => (
                          <m.span key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>{chip}</m.span>
                        ))}
                        {!compact ? <m.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="mt-1 w-full text-sm text-ink-soft">“{current.summary}”</m.p> : null}
                      </>
                    )}
                  </div>
                </m.article>
              </AnimatePresence>
            </div>
          ) : null}

          {/* Lanes */}
          <div className="mt-4 grid grid-cols-3 gap-2 sm:gap-3">
            {LANES.map((lane) => (
              <div key={lane.key} className="min-w-0 rounded-[14px] bg-white/[0.04] p-2 sm:p-2.5">
                <div className="mb-2 flex items-center justify-between gap-1">
                  <span className="flex min-w-0 items-center gap-1.5 text-[0.78rem] font-semibold text-jasmine sm:text-sm">
                    <span className={cn("h-2 w-2 shrink-0 rounded-full", lane.color)} aria-hidden="true" />
                    <span className="truncate">{lane.title}</span>
                  </span>
                  <m.span key={counts[lane.key]} initial={{ scale: 1.5, opacity: 0.4 }} animate={{ scale: 1, opacity: 1 }}
                    className="tabular font-display text-lg font-bold text-white">{counts[lane.key]}</m.span>
                </div>
                <div className={cn("flex flex-col gap-1.5", compact ? "min-h-[84px]" : "min-h-[132px]")}>
                  <AnimatePresence initial={false}>
                    {lanes[lane.key].map((r) => (
                      <m.div key={r.key} layoutId={r.key} layout exit={{ opacity: 0, scale: 0.9 }}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        className={cn("rounded-[10px] border-l-[3px] bg-white/[0.07] px-2 py-1.5 text-[0.74rem] leading-snug text-jasmine/90 sm:text-[0.8rem]", lane.ring)}>
                        <span className="line-clamp-2">{r.summary}</span>
                      </m.div>
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            ))}
          </div>
        </div>
      </LayoutGroup>
    </LazyMotion>
  );
}
