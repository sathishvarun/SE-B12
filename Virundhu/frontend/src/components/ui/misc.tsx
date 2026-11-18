import { Star } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type Tone = "chilli" | "turmeric" | "leaf" | "sky" | "lotus" | "plain" | "dark";

const tones: Record<Tone, string> = {
  chilli: "bg-chilli-soft text-[#c23a1c]",
  turmeric: "bg-[#fdefc9] text-[#8a5a00]",
  leaf: "bg-leaf-soft text-[#16784a]",
  sky: "bg-sky-soft text-[#1f5f9e]",
  lotus: "bg-lotus-soft text-[#a42a63]",
  plain: "bg-jasmine-2 text-ink-soft",
  dark: "bg-white/10 text-jasmine",
};

export function Chip({ tone = "plain", children, className, dot }: { tone?: Tone; children: ReactNode; className?: string; dot?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.8rem] font-semibold leading-none", tones[tone], className)}>
      {dot ? <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" /> : null}
      {children}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <span className={cn("inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent", className)} role="status" aria-label="Loading" />;
}

export function Stars({ rating, className }: { rating: number; className?: string }) {
  return (
    <span className={cn("inline-flex", className)} aria-label={`${rating} out of 5 stars`}>
      {Array.from({ length: 5 }, (_, i) => (
        <Star key={i} className={cn("h-3.5 w-3.5", i < rating ? "fill-turmeric text-turmeric" : "text-current opacity-25")} />
      ))}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-[12px] bg-jasmine-2", className)} />;
}
