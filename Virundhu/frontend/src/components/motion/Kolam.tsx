import { m, LazyMotion, domAnimation, useReducedMotion } from "motion/react";
import { useMemo } from "react";

/**
 * A kolam that draws itself: the pulli (dot grid) appears first, then one unbroken line loops around the dots,
 * the way it's drawn on a doorstep every morning. Purely decorative.
 */
export function Kolam({ size = 520, className, color = "var(--color-turmeric)", delay = 0.2, loop = false }:
  { size?: number; className?: string; color?: string; delay?: number; loop?: boolean }) {
  const reduce = useReducedMotion();
  const { dots, outer, inner } = useMemo(() => {
    const c = 50;
    const dots: [number, number][] = [];
    for (let y = -2; y <= 2; y++) for (let x = -2; x <= 2; x++) if (Math.abs(x) + Math.abs(y) <= 3) dots.push([c + x * 12, c + y * 12]);
    const curve = (petals: number, r: number, depth: number, turns = 1) => {
      const pts: string[] = [];
      const n = 720;
      for (let i = 0; i <= n; i++) {
        const t = (i / n) * Math.PI * 2 * turns;
        const rr = r * (1 - depth + depth * Math.cos(petals * t));
        pts.push(`${(c + rr * Math.cos(t)).toFixed(2)},${(c + rr * Math.sin(t)).toFixed(2)}`);
      }
      return `M${pts.join(" L")}`;
    };
    return { dots, outer: curve(8, 44, 0.32), inner: curve(4, 22, 0.45) };
  }, []);
  const draw = (d: number) => reduce
    ? { initial: { pathLength: 1 }, animate: { pathLength: 1 } }
    : {
        initial: { pathLength: 0, opacity: 0.2 },
        animate: { pathLength: 1, opacity: 1 },
        transition: { duration: 3.2, delay: d, ease: [0.45, 0.05, 0.25, 1] as const, repeat: loop ? Infinity : 0, repeatType: "reverse" as const, repeatDelay: 2.5 },
      };
  return (
    <LazyMotion features={domAnimation}>
      <svg viewBox="0 0 100 100" width={size} height={size} className={className} aria-hidden="true">
        {dots.map(([x, y], i) => (
          <m.circle key={i} cx={x} cy={y} r={0.9} fill={color}
            initial={reduce ? false : { scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 0.9 }}
            transition={{ delay: delay + i * 0.025, type: "spring", stiffness: 300, damping: 18 }} />
        ))}
        <m.path d={outer} fill="none" stroke={color} strokeWidth={0.7} strokeLinecap="round" {...draw(delay + 0.5)} />
        <m.path d={inner} fill="none" stroke={color} strokeWidth={0.6} strokeLinecap="round" {...draw(delay + 1.1)} />
      </svg>
    </LazyMotion>
  );
}
