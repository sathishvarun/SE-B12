import { useQuery } from "@tanstack/react-query";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Skeleton } from "@/components/ui/misc";
import { platformLabel } from "@/lib/copy";
import { cn } from "@/lib/utils";
import { appApi, type GlancePeriod, type GlanceSplit } from "@/services/api";

type View = "today" | "month";

/** Change against last month (same days of the month), worded so an owner reads it in a second. */
function Change({ now, before, goodWhenUp = true }: { now: number; before: number; goodWhenUp?: boolean }) {
  if (!before && !now) return <span className="text-sm text-ink-soft">no change</span>;
  if (!before) return <span className="text-sm text-ink-soft">new this month</span>;
  const pct = Math.round(((now - before) / before) * 100);
  if (pct === 0) return <span className="inline-flex items-center gap-1 text-sm text-ink-soft"><Minus className="h-3.5 w-3.5" />same as last month</span>;
  const up = pct > 0;
  const good = up === goodWhenUp;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={cn("inline-flex items-center gap-1 text-sm font-semibold", good ? "text-[#16784a]" : "text-[#b32f12]")}>
      <Icon className="h-4 w-4" aria-hidden="true" />{Math.abs(pct)}% {up ? "more" : "fewer"} than last month
    </span>
  );
}

function Tile({ label, value, sub, tone }: { label: string; value: number | string; sub?: ReactNode; tone?: "good" | "bad" | "warn" }) {
  return (
    <div className="rounded-[18px] border-2 border-line bg-white p-4">
      <p className="text-sm font-semibold text-ink-soft">{label}</p>
      <p className={cn("mt-1 font-display text-[2.2rem] font-bold leading-none tabular", tone === "good" && "text-[#16784a]", tone === "bad" && "text-[#b32f12]", tone === "warn" && "text-[#8a5a00]")}>{value}</p>
      {sub ? <div className="mt-2">{sub}</div> : null}
    </div>
  );
}

function SplitTable({ title, rows, monthLabel, lastLabel, label }: { title: string; rows: GlanceSplit[]; monthLabel: string; lastLabel: string; label: (k: string) => string }) {
  return (
    <div className="overflow-x-auto rounded-[18px] border-2 border-line bg-white">
      <table className="w-full min-w-[460px] text-left text-sm">
        <caption className="px-4 pt-3 text-left font-display text-lg font-bold">{title}</caption>
        <thead className="text-ink-soft">
          <tr>
            <th className="px-4 py-2 font-semibold">&nbsp;</th>
            <th className="px-3 py-2 text-right font-semibold">{monthLabel.split(" ")[0]}</th>
            <th className="px-3 py-2 text-right font-semibold">{lastLabel.split(" ")[0]}</th>
            <th className="px-3 py-2 text-right font-semibold">Positive</th>
            <th className="px-3 py-2 text-right font-semibold">Negative</th>
            <th className="px-4 py-2 text-right font-semibold">Rating</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? <tr><td colSpan={6} className="px-4 py-4 text-ink-soft">No reviews in these two months yet.</td></tr> : rows.map((r) => (
            <tr key={r.key} className="border-t border-line">
              <td className="px-4 py-2 font-semibold">{label(r.key)}</td>
              <td className="px-3 py-2 text-right tabular font-semibold">{r.this_month}</td>
              <td className="px-3 py-2 text-right tabular text-ink-soft">{r.last_month}</td>
              <td className="px-3 py-2 text-right tabular text-[#16784a]">{r.positive}</td>
              <td className={cn("px-3 py-2 text-right tabular", r.negative ? "font-semibold text-[#b32f12]" : "text-ink-soft")}>{r.negative}</td>
              <td className="px-4 py-2 text-right tabular">{r.avg_rating === null ? "-" : `${r.avg_rating.toFixed(1)}★`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * The owner's (or CEO's) one screen: how many reviews came, how many were happy or unhappy, how many we answered,
 * where they came from, and how this month compares with last month. Every number is counted by the database.
 */
export function AtAGlance({ outletId }: { outletId?: number }) {
  const [view, setView] = useState<View>("month");
  const { data, isLoading } = useQuery({ queryKey: ["summary", outletId ?? 0], queryFn: () => appApi.summary(outletId), refetchInterval: 60_000 });
  if (isLoading || !data) return <Skeleton className="mt-8 h-[260px]" />;
  const p: GlancePeriod = view === "today" ? data.today : data.this_month;
  const prev = data.last_month_to_date;
  const replyRate = p.reviews ? Math.round((Math.min(p.replied, p.reviews) / p.reviews) * 100) : null;
  return (
    <section className="mt-8" aria-labelledby="glance">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="glance" className="font-display text-2xl font-bold">At a glance</h2>
          <p className="text-sm text-ink-soft">
            {view === "today" ? "Reviews written today, and replies sent today." : `${data.month_label} so far, compared with the same days of ${data.last_month_label}.`}
          </p>
        </div>
        <div className="flex gap-1 rounded-full bg-jasmine-2 p-1" role="tablist" aria-label="Period">
          {([["today", "Today"], ["month", "This month"]] as const).map(([k, l]) => (
            <button key={k} type="button" role="tab" aria-selected={view === k} onClick={() => setView(k)}
              className={cn("cursor-pointer rounded-full px-4 py-1.5 text-sm font-semibold", view === k ? "bg-night text-jasmine" : "text-ink-soft")}>{l}</button>
          ))}
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Tile label="Reviews" value={p.reviews} sub={view === "month" ? <Change now={p.reviews} before={prev.reviews} /> : undefined} />
        <Tile label="Positive" value={p.positive} tone="good" sub={view === "month" ? <Change now={p.positive} before={prev.positive} /> : undefined} />
        <Tile label="Negative" value={p.negative} tone={p.negative ? "bad" : undefined} sub={view === "month" ? <Change now={p.negative} before={prev.negative} goodWhenUp={false} /> : undefined} />
        <Tile label="Replied" value={p.replied} sub={replyRate !== null ? <span className="text-sm text-ink-soft">{replyRate}% of {view === "today" ? "today's" : "this month's"} reviews</span> : undefined} />
        <Tile label="Waiting for a reply" value={data.waiting} tone={data.waiting ? "warn" : "good"} sub={<span className="text-sm text-ink-soft">{data.waiting ? "open the inbox to answer" : "all answered"}</span>} />
      </div>
      {view === "month" ? (
        <>
          <p className="mt-3 text-sm text-ink-soft">
            Average rating {p.avg_rating === null ? "-" : `${p.avg_rating.toFixed(1)}★`}
            {prev.avg_rating !== null ? ` (same days last month ${prev.avg_rating.toFixed(1)}★)` : ""}. All of {data.last_month_label}: {data.last_month.reviews} reviews, {data.last_month.positive} positive, {data.last_month.negative} negative.
          </p>
          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            <SplitTable title="Where reviews came from" rows={data.by_platform} monthLabel={data.month_label} lastLabel={data.last_month_label} label={(k) => platformLabel[k as keyof typeof platformLabel] ?? k} />
            <SplitTable title="By branch" rows={data.by_outlet} monthLabel={data.month_label} lastLabel={data.last_month_label} label={(k) => k} />
          </div>
        </>
      ) : null}
    </section>
  );
}
