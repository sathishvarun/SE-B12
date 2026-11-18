import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Skeleton } from "@/components/ui/misc";
import { api } from "@/services/api";
import { cn } from "@/lib/utils";

interface Example { id: number; rating: number; text: string; date: string; platform: string; outlet: string | null; sentiment: string }
interface Mention { name: string; mentions: number; positive: number; negative: number; neutral: number; score: number; outlets: { name: string; count: number }[]; examples: Example[] }
interface Mentions { days: number; dishes: Mention[]; staff: Mention[] }

const PERIODS = [30, 90, 365] as const;

function Row({ m }: { m: Mention }) {
  const [open, setOpen] = useState(false);
  const good = Math.round((100 * m.positive) / m.mentions);
  const bad = Math.round((100 * m.negative) / m.mentions);
  return (
    <li className="rounded-[16px] border-2 border-line bg-white">
      <button type="button" onClick={() => setOpen((x) => !x)} aria-expanded={open} className="flex w-full items-center gap-3 p-4 text-left cursor-pointer">
        <div className="min-w-0 flex-1">
          <p className="font-semibold capitalize">{m.name}</p>
          <p className="text-sm text-ink-soft">{m.mentions} mention{m.mentions > 1 ? "s" : ""}{m.outlets[0] ? `, most at ${m.outlets[0].name}` : ""}</p>
          <div className="mt-2 flex h-2.5 overflow-hidden rounded-full bg-jasmine-2" aria-label={`${good}% liked, ${bad}% complained`}>
            <span className="bg-leaf" style={{ width: `${good}%` }} /><span className="bg-chilli" style={{ width: `${bad}%` }} />
          </div>
        </div>
        <span className={cn("rounded-full px-3 py-1 text-sm font-bold tabular", m.score >= 30 ? "bg-leaf-soft text-[#16784a]" : m.score <= -20 ? "bg-chilli-soft text-[#b32f12]" : "bg-jasmine-2")}>
          {m.score > 0 ? "+" : ""}{m.score}
        </span>
      </button>
      {open ? (
        <ul className="space-y-2 border-t-2 border-jasmine-2 p-4">
          {m.examples.map((e) => (
            <li key={e.id} className="text-sm"><span className={cn("font-semibold", e.sentiment === "negative" ? "text-[#b32f12]" : e.sentiment === "positive" ? "text-[#16784a]" : "")}>{"★".repeat(e.rating)}</span>{" "}
              “{e.text}” <span className="text-ink-soft">{e.outlet ? `${e.outlet}, ` : ""}{e.platform}, {new Date(e.date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</span></li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}

/** What guests say about each dish and each staff member: the kitchen and floor fix list. */
export default function Insights() {
  const [days, setDays] = useState<(typeof PERIODS)[number]>(90);
  const { data, isLoading } = useQuery({ queryKey: ["mentions", days], queryFn: () => api.get<Mentions>("/api/v1/insights/mentions", { params: { days } }).then((r) => r.data) });
  const worst = data?.dishes.filter((d) => d.negative > 0).sort((a, b) => b.negative - a.negative)[0];
  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[2.3rem] font-bold">Dishes and staff</h1>
          <p className="mt-1 max-w-2xl text-ink-soft">Every dish and every staff member your guests name, and whether they loved it or complained. Score = % positive minus % negative. Tap a row to read the reviews.</p>
        </div>
        <div className="inline-flex gap-1 rounded-full bg-jasmine-2 p-1" role="tablist" aria-label="Period">
          {PERIODS.map((p) => (
            <button key={p} role="tab" aria-selected={days === p} onClick={() => setDays(p)} className={cn("rounded-full px-3.5 py-1.5 text-sm font-semibold cursor-pointer", days === p ? "bg-night text-jasmine" : "")}>{p === 365 ? "1 year" : `${p} days`}</button>
          ))}
        </div>
      </div>
      {worst ? (
        <p className="mt-5 rounded-[16px] bg-chilli-soft p-4"><b className="capitalize">{worst.name}</b> drew {worst.negative} complaint{worst.negative > 1 ? "s" : ""} in this period{worst.outlets[0] ? `, mostly at ${worst.outlets[0].name}` : ""}. Fix this first.</p>
      ) : null}
      {isLoading ? <Skeleton className="mt-6 h-80" /> : (
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          {(["dishes", "staff"] as const).map((k) => (
            <section key={k}>
              <h2 className="text-xl font-bold">{k === "dishes" ? "Dishes" : "Staff"}</h2>
              {data?.[k].length ? <ul className="mt-3 space-y-3">{data[k].map((m) => <Row key={m.name} m={m} />)}</ul>
                : <p className="mt-3 rounded-[16px] bg-jasmine p-4 text-ink-soft">No {k === "dishes" ? "dishes" : "staff"} named yet in this period. New reviews are read for names automatically.</p>}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
