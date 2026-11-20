import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Skeleton } from "@/components/ui/misc";
import { usageApi } from "@/services/api";

const n = (x: number) => x.toLocaleString("en-IN");
const short = (x: number) => (x >= 1_000_000 ? `${(x / 1_000_000).toFixed(1)}M` : x >= 1000 ? `${(x / 1000).toFixed(1)}k` : String(x));

export default function AiUsage() {
  const { data: u } = useQuery({ queryKey: ["usage-tokens"], queryFn: usageApi.mine, refetchInterval: 60_000 });
  if (!u) return <div className="mx-auto max-w-5xl"><Skeleton className="h-[560px]" /></div>;
  const readShare = u.reviews_allowed_per_month ? Math.min(100, Math.round((u.reviews_read_this_month / u.reviews_allowed_per_month) * 100)) : 0;
  const perReview = u.reviews_read_this_month ? Math.round(u.this_month.tokens / u.reviews_read_this_month) : null;

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-[2.3rem] font-bold">AI usage</h1>
      <p className="mt-1 max-w-2xl text-ink-soft">
        How much AI work Virundhu did for {u.restaurant}. A token is a small piece of text, roughly ¾ of a word: the AI
        counts what it reads (your reviews) and what it writes (tags and reply drafts). Everything is included in your plan.
      </p>

      <section className="mt-6 grid gap-4 sm:grid-cols-3">
        {([["This month", u.this_month], ["Last month", u.last_month], ["Since you joined", u.all_time]] as const).map(([label, t]) => (
          <div key={label} className="rounded-[20px] border-2 border-line bg-white p-5">
            <p className="text-sm text-ink-soft">{label}</p>
            <p className="tabular mt-1 font-display text-3xl font-bold">{n(t.tokens)}</p>
            <p className="text-sm text-ink-soft">tokens in {n(t.calls)} AI task{t.calls === 1 ? "" : "s"}</p>
            <p className="text-xs text-ink-soft">{n(t.input_tokens)} read · {n(t.output_tokens)} written</p>
          </div>
        ))}
      </section>

      <section className="mt-5 rounded-[20px] border-2 border-line bg-white p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-display text-lg font-bold">Reviews read this month</h2>
          <p className="tabular text-sm text-ink-soft"><b className="text-ink">{n(u.reviews_read_this_month)}</b> of {n(u.reviews_allowed_per_month)} included</p>
        </div>
        <div className="mt-3 h-3 overflow-hidden rounded-full bg-jasmine-2" role="progressbar" aria-valuenow={readShare} aria-valuemin={0} aria-valuemax={100} aria-label="Reviews read this month">
          <div className="h-full rounded-full bg-leaf" style={{ width: `${readShare}%` }} />
        </div>
        {perReview ? <p className="mt-2 text-sm text-ink-soft">About {n(perReview)} tokens per review this month.</p> : null}
      </section>

      <section className="mt-5 rounded-[20px] border-2 border-line bg-white p-5">
        <h2 className="font-display text-lg font-bold">Per day, last 30 days</h2>
        <div className="mt-4 h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={u.daily} margin={{ left: 0, right: 8, top: 8 }}>
              <CartesianGrid vertical={false} stroke="#e8e2d0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" minTickGap={16} />
              <YAxis tick={{ fontSize: 11 }} width={48} tickFormatter={(v: number) => short(v)} />
              <Tooltip formatter={(v) => [`${n(Number(v))} tokens`, "Used"]} />
              <Bar dataKey="tokens" fill="#0c3b2e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="mt-5 rounded-[20px] border-2 border-line bg-white p-5">
        <h2 className="font-display text-lg font-bold">What the AI did this month</h2>
        {u.by_feature.length === 0 ? <p className="mt-2 text-sm text-ink-soft">No AI work yet this month. Add reviews and it starts reading them straight away.</p> : (
          <table className="mt-3 w-full text-sm">
            <thead><tr className="text-left text-ink-soft"><th className="py-2 font-semibold">Task</th><th className="text-right font-semibold">Times</th><th className="text-right font-semibold">Tokens</th></tr></thead>
            <tbody>
              {u.by_feature.map((f) => (
                <tr key={f.feature} className="border-t border-line"><td className="py-2">{f.label}</td><td className="tabular text-right">{n(f.calls)}</td><td className="tabular text-right font-semibold">{n(f.tokens)}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
