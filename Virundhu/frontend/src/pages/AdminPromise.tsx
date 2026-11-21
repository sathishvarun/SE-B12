import { useQuery } from "@tanstack/react-query";
import { Search, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { NoMapYet, OpenInMaps } from "@/components/review/MapLinks";
import { Chip, Skeleton } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { adminPromiseApi } from "@/services/api";

const target = (m: number) => (m < 120 ? `${m} min` : `${m / 60} h`);

/** Admin → Reply promise: every restaurant's score, slowest first, so you know whom to call. */
export function ReplyPromisePanel() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({ queryKey: ["admin-promise", days], queryFn: () => adminPromiseApi.league(days), refetchInterval: 60_000 });
  const rows = data ?? [];
  const bad = rows.reduce((s, r) => s + r.bad, 0);
  const within = rows.reduce((s, r) => s + r.within, 0);
  return (
    <div className="space-y-5">
      <p className="max-w-3xl text-ink-soft">
        The promise on the website: no bad review sits unanswered for more than an hour. This is how each restaurant keeps
        it. Slowest first, so you know whom to call. Bad = 1 to 3 stars or urgent; the clock starts when the review reaches Virundhu.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1.5 rounded-full bg-jasmine-2 p-1">
          {[7, 30, 90].map((d) => (
            <button key={d} type="button" onClick={() => setDays(d)} className={cn("rounded-full px-3.5 py-1.5 text-sm font-semibold cursor-pointer", days === d ? "bg-night text-jasmine" : "text-ink-soft")}>
              Last {d} days
            </button>
          ))}
        </div>
        {bad ? <Chip tone={within / bad >= 0.9 ? "leaf" : "turmeric"}>All restaurants: {Math.round((100 * within) / bad)}% in time ({within} of {bad})</Chip> : null}
      </div>
      {isLoading ? <Skeleton className="h-[300px]" /> : rows.length === 0 ? (
        <p className="rounded-[18px] border-2 border-dashed border-ink/15 bg-white p-8 text-center text-ink-soft">No bad reviews in this period.</p>
      ) : (
        <div className="overflow-x-auto rounded-[20px] border-2 border-line bg-white">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-jasmine text-ink-soft">
              <tr>{["Restaurant", "Target", "In time", "Bad reviews", "Usual reply", "Waiting now", "Past target"].map((h) => <th key={h} className="px-4 py-3 font-semibold">{h}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.org_id} className="border-t border-line">
                  <td className="px-4 py-3"><p className="font-semibold">{r.name}</p><p className="text-xs text-ink-soft">{r.plan}{r.reminders_on ? "" : ", reminders off"}</p></td>
                  <td className="px-4 py-3">{target(r.target_minutes)}</td>
                  <td className="px-4 py-3 tabular">
                    {r.pct_within === null ? "-" : <span className={cn("rounded-full px-2 py-0.5 font-semibold", r.pct_within >= 90 ? "bg-[#dff3e8] text-[#16784a]" : r.pct_within >= 60 ? "bg-[#fdefc9] text-[#8a5a00]" : "bg-chilli-soft text-[#b32f12]")}>{Math.round(r.pct_within)}%</span>}
                  </td>
                  <td className="px-4 py-3 tabular">{r.within} of {r.bad}</td>
                  <td className="px-4 py-3 tabular">{r.median_minutes === null ? "-" : `${r.median_minutes} min`}</td>
                  <td className="px-4 py-3 tabular">{r.waiting}</td>
                  <td className={cn("px-4 py-3 tabular", r.overdue ? "font-semibold text-[#b32f12]" : "")}>{r.overdue}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/** Admin → All branches: every restaurant's branches with free Google Maps links. */
export function BranchesPanel() {
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [city, setCity] = useState("");
  useEffect(() => { const t = setTimeout(() => setSearch(q.trim()), 300); return () => clearTimeout(t); }, [q]);
  const { data, isLoading } = useQuery({ queryKey: ["admin-branches", search, city], queryFn: () => adminPromiseApi.branches(search, city) });
  return (
    <div className="space-y-5">
      <p className="max-w-3xl text-ink-soft">
        Every branch of every customer. {data ? `${data.with_map} of ${data.total} can be opened on Google Maps.` : ""} Branches
        linked to their Google listing open the exact place; the rest open a search for their address.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <label className="relative min-w-[240px] flex-1">
          <span className="sr-only">Search branches</span>
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-soft" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Restaurant, branch, area or city"
            className="h-10 w-full rounded-full border-2 border-line bg-white pl-10 pr-4 focus:border-night focus:outline-none" />
        </label>
        <div className="flex flex-wrap gap-1.5">
          {[["", data?.total ?? 0] as [string, number], ...(data?.cities ?? [])].map(([c, n]) => (
            <button key={c || "all"} type="button" onClick={() => setCity(c)}
              className={cn("rounded-full px-3 py-1.5 text-sm font-semibold cursor-pointer", city === c ? "bg-night text-jasmine" : "bg-jasmine-2 text-ink-soft")}>
              {c || "All cities"} <span className="tabular opacity-70">{n}</span>
            </button>
          ))}
        </div>
      </div>
      {isLoading ? <Skeleton className="h-[300px]" /> : (
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(data?.items ?? []).map((b) => (
            <li key={b.id} className="flex flex-col gap-1.5 rounded-[18px] border-2 border-line bg-white p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-xs font-semibold text-[#b32f12]">{b.restaurant}</p>
                  <p className="font-display text-lg font-bold leading-tight">{b.name}</p>
                  <p className="text-sm text-ink-soft">{[b.address || b.area, b.city].filter(Boolean).join(", ") || "No address yet"}</p>
                </div>
                {b.google_rating ? <span className="inline-flex items-center gap-1 text-sm font-semibold"><Star className="h-4 w-4 fill-turmeric text-turmeric" aria-hidden="true" />{b.google_rating.toFixed(1)}</span> : null}
              </div>
              <div className="mt-auto pt-1">{b.directions_url ? <OpenInMaps url={b.directions_url} /> : <NoMapYet />}</div>
            </li>
          ))}
          {data && data.items.length === 0 ? <li className="text-ink-soft">No branches match.</li> : null}
        </ul>
      )}
      {data && data.total > data.items.length ? <p className="text-sm text-ink-soft">Showing {data.items.length} of {data.total}. Search or pick a city to narrow it down.</p> : null}
    </div>
  );
}
