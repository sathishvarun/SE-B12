import { cn } from "@/lib/utils";

/** A full meal on a banana leaf, drawn by hand (no stock art): the "virundhu" the product is named after. */
export function FeastLeafArt({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 560 320" className={className} role="img" aria-label="A South Indian meal served on a banana leaf">
      <defs>
        <linearGradient id="leaf" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#3fae5a" /><stop offset="0.55" stopColor="#23874a" /><stop offset="1" stopColor="#14623a" />
        </linearGradient>
        <radialGradient id="sambar" cx="0.4" cy="0.35" r="0.7"><stop offset="0" stopColor="#f7a43a" /><stop offset="1" stopColor="#c8601c" /></radialGradient>
        <radialGradient id="rasam" cx="0.4" cy="0.35" r="0.7"><stop offset="0" stopColor="#f0603e" /><stop offset="1" stopColor="#a8321c" /></radialGradient>
        <radialGradient id="vada" cx="0.4" cy="0.35" r="0.7"><stop offset="0" stopColor="#e7a24b" /><stop offset="1" stopColor="#9b5a1c" /></radialGradient>
      </defs>
      {/* leaf */}
      <path d="M18 168 C70 40 300 6 548 70 C540 210 360 318 120 300 C70 296 30 250 18 168 Z" fill="url(#leaf)" />
      <path d="M30 196 C180 150 360 110 540 80" stroke="#bfe6a8" strokeWidth="3" fill="none" opacity="0.7" />
      <g stroke="#bfe6a8" strokeWidth="1.2" opacity="0.35" fill="none">
        {Array.from({ length: 14 }, (_, i) => {
          const x = 60 + i * 34;
          const y = 186 - i * 7.6;
          return <path key={i} d={`M${x} ${y} C${x + 10} ${y - 50} ${x + 30} ${y - 80} ${x + 40} ${y - 110} M${x} ${y} C${x - 6} ${y + 40} ${x - 10} ${y + 70} ${x - 12} ${y + 100}`} />;
        })}
      </g>
      {/* rice */}
      <ellipse cx="270" cy="200" rx="78" ry="44" fill="#fffdf6" /><ellipse cx="262" cy="190" rx="54" ry="28" fill="#ffffff" />
      <g fill="#efe7d6">{[0, 1, 2, 3, 4, 5].map((i) => <circle key={i} cx={232 + i * 14} cy={200 + (i % 2) * 8} r="2" />)}</g>
      {/* sambar + rasam bowls */}
      <circle cx="160" cy="214" r="34" fill="#dcd2c0" /><circle cx="160" cy="212" r="28" fill="url(#sambar)" />
      <circle cx="152" cy="206" r="4" fill="#ffd27a" /><circle cx="168" cy="216" r="3" fill="#7bb84a" />
      <circle cx="378" cy="200" r="30" fill="#dcd2c0" /><circle cx="378" cy="198" r="24" fill="url(#rasam)" />
      {/* vada and idli */}
      <circle cx="420" cy="124" r="28" fill="url(#vada)" /><circle cx="420" cy="124" r="8" fill="#23874a" />
      <ellipse cx="320" cy="112" rx="34" ry="20" fill="#fffaf0" /><ellipse cx="320" cy="106" rx="30" ry="14" fill="#ffffff" />
      {/* appalam */}
      <circle cx="200" cy="118" r="38" fill="#f7e3a6" />
      <g fill="#e3c071">{[[188, 104], [210, 112], [196, 130], [214, 128], [182, 120]].map(([x, y]) => <circle key={`${x}${y}`} cx={x} cy={y} r="2.4" />)}</g>
      {/* chutneys, pickle, banana, payasam */}
      <circle cx="108" cy="150" r="14" fill="#9fd36b" /><circle cx="92" cy="182" r="11" fill="#fff4dc" />
      <circle cx="122" cy="122" r="9" fill="#c43d1d" />
      <path d="M460 176 C490 160 510 130 512 108" stroke="#ffd84a" strokeWidth="14" strokeLinecap="round" fill="none" />
      <circle cx="470" cy="214" r="22" fill="#dcd2c0" /><circle cx="470" cy="212" r="17" fill="#f5deb0" /><circle cx="466" cy="208" r="3" fill="#b06a2a" />
    </svg>
  );
}

const NOTES = [
  { dish: "Idli", text: "Soft as cotton", stars: 5, mood: "good", cls: "left-[34%] -top-2", r: "-3deg" },
  { dish: "Sambar", text: "Too salty today", stars: 2, mood: "bad", cls: "-left-2 top-[46%]", r: "2deg" },
  { dish: "Vada", text: "Crispy, hot", stars: 5, mood: "good", cls: "right-0 top-[12%]", r: "3deg" },
  { dish: "Rasam", text: "Waited 25 min", stars: 3, mood: "mixed", cls: "right-[6%] bottom-0", r: "-2deg" },
] as const;

/** Banana-leaf meal with guests' notes floating over each dish: reviews about food, sorted by Virundhu. */
export function FeastLeaf({ className, compact = false }: { className?: string; compact?: boolean }) {
  return (
    <div className={cn("relative", className)}>
      <FeastLeafArt className="relative w-full drop-shadow-[0_30px_40px_rgba(0,0,0,0.35)]" />
      {NOTES.slice(0, compact ? 3 : 4).map((n, i) => (
        <div key={n.dish} style={{ ["--r" as string]: n.r, animationDelay: `${i * 0.9}s` }}
          className={cn("float-soft absolute rounded-[14px] bg-white px-3 py-2 text-ink shadow-[0_12px_28px_-10px_rgba(0,0,0,0.45)]", compact ? "text-[0.7rem]" : "text-sm", n.cls)}>
          <p className="flex items-center gap-1.5 font-semibold">
            <span className={cn("h-2 w-2 rounded-full", n.mood === "good" ? "bg-leaf" : n.mood === "bad" ? "bg-chilli" : "bg-sky")} />
            {n.dish}
            <span className="text-turmeric-deep" aria-label={`${n.stars} out of 5 stars`}>{"★".repeat(n.stars)}<span className="text-line">{"★".repeat(5 - n.stars)}</span></span>
          </p>
          <p className="text-ink-soft">{n.text}</p>
        </div>
      ))}
    </div>
  );
}
