import { cn } from "@/lib/utils";

const DOTS: [number, number][] = [[10, 8.5], [16, 8.5], [22, 8.5], [10, 14.5], [22, 14.5], [10, 20.5], [16, 20.5], [22, 20.5]];

/** Kolam-dot speech bubble. `onDark` swaps the bubble to jasmine for dark backgrounds. */
export function LogoMark({ className, onDark }: { className?: string; onDark?: boolean }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("h-9 w-9", className)} aria-hidden="true">
      <path d="M16 3.5c7.2 0 12.5 4.7 12.5 11s-5.3 11-12.5 11c-1.3 0-2.6-.2-3.8-.5L6.5 28l1.3-5.4C5 20.6 3.5 17.7 3.5 14.5c0-6.3 5.3-11 12.5-11z"
        fill={onDark ? "#FFF8EE" : "#0C3B2E"} />
      {DOTS.map(([x, y]) => <circle key={`${x}-${y}`} cx={x} cy={y} r="1.6" fill={onDark ? "#0C3B2E" : "#FFF8EE"} />)}
      <circle cx="16" cy="14.5" r="2.4" fill="#F8B62D" />
    </svg>
  );
}

export function Logo({ className, onDark }: { className?: string; onDark?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark onDark={onDark} />
      <span className={cn("font-display text-[1.45rem] font-bold tracking-tight", onDark ? "text-jasmine" : "text-night")}>Virundhu</span>
    </span>
  );
}
