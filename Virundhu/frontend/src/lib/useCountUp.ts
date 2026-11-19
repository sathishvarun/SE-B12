import { useEffect, useRef, useState } from "react";

/** Animates a number from its previous value to `target` (instant when reduced motion is on). */
export function useCountUp(target: number, duration = 900, startAtTarget = false): number {
  // startAtTarget: show the real number straight away (prebuilt pages that search engines read).
  const [value, setValue] = useState(startAtTarget ? target : 0);
  const from = useRef(startAtTarget ? target : 0);
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const start = performance.now();
    const begin = from.current;
    let frame = 0;
    const tick = (now: number) => {
      const t = reduce ? 1 : Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const next = begin + (target - begin) * eased;
      setValue(next);
      if (t < 1) frame = requestAnimationFrame(tick);
      else from.current = target;
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);
  return value;
}
