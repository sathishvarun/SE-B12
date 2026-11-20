import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Chip, Skeleton } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { adminTokensApi, type RestaurantTokens, type TokenTotals } from "@/services/api";

const n = (x: number) => x.toLocaleString("en-IN");
const inr = (x: number) => `₹${x.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const short = (x: number) => (x >= 1_000_000 ? `${(x / 1_000_000).toFixed(1)}M` : x >= 1000 ? `${(x / 1000).toFixed(1)}k` : String(x));

function Window({ label, t }: { label: string; t: TokenTotals }) {
  return (
    <div className="rounded-[20px] border-2 border-line bg-white p-5">
      <p className="text-sm text-ink-soft">{label}</p>
      <p className="tabular mt-1 font-display text-3xl font-bold">{n(t.tokens)}</p>
      <p className="text-sm text-ink-soft">tokens · {n(t.calls)} AI call{t.calls === 1 ? "" : "s"}</p>
      <p className="tabular mt-1 font-semibold">{inr(t.cost_inr)} AI cost</p>
    </div>
  );
}

/** Admin → AI tokens: everything across Virundhu. */
export function TokensTotalPanel() {
  const [days, setDays] = useState(30);
  const { data: t } = useQuery({ queryKey: ["admin-tokens", days], queryFn: () => adminTokensApi.total(days), refetchInterval: 60_000 });
  if (!t) return <Skeleton className="h-[520px]" />;
  return (
    <div className="space-y-5">
      <p className="max-w-3xl text-ink-soft">
        Every AI call Virundhu made, for every restaurant and for its own agents, counted from the real token numbers the
        AI provider returned. {t.restaurants_using_ai} restaurant{t.restaurants_using_ai === 1 ? " has" : "s have"} used AI so far.
      </p>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Window label="Today" t={t.windows.today} />
        <Window label="This month" t={t.windows.this_month} />
        <Window label="Last 30 days" t={t.windows.last_30} />
        <Window label="All time" t={t.windows.all_time} />
      </div>
      <p className="text-sm text-ink-soft">{t.price_note} Virundhu's own work with no restaurant attached (support drafts and feedback agents) is {n(t.platform_own.tokens)} tokens, {inr(t.platform_own.cost_inr)} all time.</p>

      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-display text-lg font-bold">Tokens per day</h3>
          <div className="flex gap-2" role="radiogroup" aria-label="How many days">
            {[7, 30, 90].map((d) => (
              <button key={d} type="button" role="radio" aria-checked={days === d} onClick={() => setDays(d)}
                className={cn("cursor-pointer rounded-full border-2 px-3 py-1 text-sm font-semibold", days === d ? "border-night bg-night text-jasmine" : "border-line bg-white hover:border-night")}>{d} days</button>
            ))}
          </div>
        </div>
        <div className="mt-4 h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={t.daily} margin={{ left: 0, right: 8, top: 8 }}>
              <CartesianGrid vertical={false} stroke="#e8e2d0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" minTickGap={16} />
              <YAxis tick={{ fontSize: 11 }} width={48} tickFormatter={(v: number) => short(v)} />
              <Tooltip formatter={(v, _k, p) => [`${n(Number(v))} tokens (${inr((p.payload as { cost_inr: number }).cost_inr)})`, "Used"]} />
              <Bar dataKey="tokens" fill="#0c3b2e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <h3 className="font-display text-lg font-bold">By task, this month</h3>
        {t.by_feature.length === 0 ? <p className="mt-2 text-sm text-ink-soft">No AI calls yet this month.</p> : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead><tr className="text-left text-ink-soft"><th className="py-2 font-semibold">Task</th><th className="text-right font-semibold">Calls</th><th className="text-right font-semibold">Read</th><th className="text-right font-semibold">Written</th><th className="text-right font-semibold">Tokens</th><th className="text-right font-semibold">Cost</th></tr></thead>
              <tbody>
                {t.by_feature.map((f) => (
                  <tr key={f.feature} className="border-t border-line">
                    <td className="py-2">{f.label}</td><td className="tabular text-right">{n(f.calls)}</td><td className="tabular text-right">{n(f.input_tokens)}</td>
                    <td className="tabular text-right">{n(f.output_tokens)}</td><td className="tabular text-right font-semibold">{n(f.tokens)}</td><td className="tabular text-right">{inr(f.cost_inr)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

type SortKey = "tokens_this_month" | "tokens_all_time" | "cost_all_time_inr" | "paid_all_time_inr";

/** Admin → Tokens by restaurant: each restaurant's AI use next to what it paid. */
export function TokensByRestaurantPanel() {
  const { data } = useQuery({ queryKey: ["admin-tokens-restaurants"], queryFn: adminTokensApi.restaurants, refetchInterval: 60_000 });
  const [find, setFind] = useState("");
  const [sort, setSort] = useState<SortKey>("tokens_this_month");
  const rows = useMemo(() => {
    const q = find.trim().toLowerCase();
    return [...(data ?? [])].filter((r) => !q || r.name.toLowerCase().includes(q)).sort((a, b) => b[sort] - a[sort]);
  }, [data, find, sort]);
  if (!data) return <Skeleton className="h-[520px]" />;
  const sum = (k: keyof RestaurantTokens) => data.reduce((s, r) => s + (Number(r[k]) || 0), 0);
  const cols: [SortKey, string][] = [["tokens_this_month", "Tokens this month"], ["tokens_all_time", "Tokens all time"], ["cost_all_time_inr", "AI cost all time"], ["paid_all_time_inr", "Paid all time"]];
  return (
    <div className="space-y-5">
      <p className="max-w-3xl text-ink-soft">
        How much AI each restaurant used, what it cost you, and what that restaurant has paid (live payments, refunds taken
        off). Use it to price plans: the AI share shows how much of a restaurant's payments went on AI.
      </p>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-[20px] border-2 border-line bg-white p-5"><p className="text-sm text-ink-soft">Tokens this month, all restaurants</p><p className="tabular mt-1 font-display text-3xl font-bold">{n(sum("tokens_this_month"))}</p></div>
        <div className="rounded-[20px] border-2 border-line bg-white p-5"><p className="text-sm text-ink-soft">AI cost this month</p><p className="tabular mt-1 font-display text-3xl font-bold">{inr(sum("cost_this_month_inr"))}</p></div>
        <div className="rounded-[20px] border-2 border-line bg-white p-5"><p className="text-sm text-ink-soft">AI cost all time vs paid all time</p><p className="tabular mt-1 font-display text-3xl font-bold">{inr(sum("cost_all_time_inr"))}</p><p className="text-sm text-ink-soft">against {inr(sum("paid_all_time_inr"))} paid</p></div>
      </div>
      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm font-semibold">Find a restaurant
            <input value={find} onChange={(e) => setFind(e.target.value)} className="h-10 w-56 rounded-[10px] border-2 border-line px-3 font-normal" />
          </label>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Sort by">
            {cols.map(([k, label]) => (
              <button key={k} type="button" role="radio" aria-checked={sort === k} onClick={() => setSort(k)}
                className={cn("cursor-pointer rounded-full border-2 px-3 py-1 text-sm font-semibold", sort === k ? "border-night bg-night text-jasmine" : "border-line bg-white hover:border-night")}>{label}</button>
            ))}
          </div>
        </div>
        {rows.length === 0 ? <p className="mt-4 text-sm text-ink-soft">{data.length ? "No restaurant matches that name." : "No restaurants yet."}</p> : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[860px] text-sm">
              <thead><tr className="text-left text-ink-soft"><th className="py-2 font-semibold">Restaurant</th><th className="font-semibold">Plan</th><th className="text-right font-semibold">This month</th><th className="text-right font-semibold">Last month</th><th className="text-right font-semibold">All time</th><th className="text-right font-semibold">AI cost (month / all)</th><th className="text-right font-semibold">Paid</th><th className="text-right font-semibold">AI share</th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-t border-line">
                    <td className="py-2 font-semibold">{r.name}</td>
                    <td><Chip tone={r.plan === "trial" ? "turmeric" : "leaf"}>{r.plan === "trial" ? "Trial" : `${r.paid_outlets ?? 1} outlet${r.paid_outlets === 1 ? "" : "s"}`}</Chip></td>
                    <td className="tabular text-right font-semibold">{n(r.tokens_this_month)}</td>
                    <td className="tabular text-right">{n(r.tokens_last_month)}</td>
                    <td className="tabular text-right">{n(r.tokens_all_time)}</td>
                    <td className="tabular text-right">{inr(r.cost_this_month_inr)} / {inr(r.cost_all_time_inr)}</td>
                    <td className="tabular text-right">{r.paid_all_time_inr ? inr(r.paid_all_time_inr) : "-"}</td>
                    <td className="tabular text-right">{r.ai_share_percent === null ? "-" : `${r.ai_share_percent}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
