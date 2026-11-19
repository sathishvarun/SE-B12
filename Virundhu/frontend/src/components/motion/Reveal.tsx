import { m, LazyMotion, domAnimation, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

// Content in the first paint (the prebuilt HTML Google reads) is shown straight away, never hidden waiting for
// JavaScript. Only content that appears after the page has started animates in.
let firstPaint = true;
export function markPainted() {
  firstPaint = false;
}

/** Fades a block up the first time it scrolls into view. Children with `stagger` come in one after another. */
export function Reveal({ children, className, delay = 0, y = 24 }: { children: ReactNode; className?: string; delay?: number; y?: number }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <LazyMotion features={domAnimation}>
      <m.div className={className} initial={firstPaint ? false : { opacity: 0, y }} whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }} transition={{ duration: 0.6, delay, ease: [0.2, 0.8, 0.2, 1] }}>
        {children}
      </m.div>
    </LazyMotion>
  );
}

/** Splits a headline into words that rise in one after another. */
export function RiseWords({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  const reduce = useReducedMotion();
  if (reduce) return <span className={className}>{text}</span>;
  return (
    <LazyMotion features={domAnimation}>
      <span className={className}>
        <span className="sr-only">{text}</span>
        {text.split(" ").map((w, i) => (
          <span key={i} aria-hidden="true" className="inline-block overflow-hidden pb-[0.08em] align-bottom">
            <m.span className="inline-block" initial={firstPaint ? false : { y: "105%" }} animate={{ y: 0 }}
              transition={{ delay: delay + i * 0.07, duration: 0.7, ease: [0.2, 0.8, 0.2, 1] }}>
              {w}{" "}
            </m.span>
          </span>
        ))}
      </span>
    </LazyMotion>
  );
}
