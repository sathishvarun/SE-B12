import { useQuery } from "@tanstack/react-query";
import { ArrowDownRight, ArrowUpRight, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { buttonVariants } from "@/components/ui/button";
import { Chip, Skeleton, Stars } from "@/components/ui/misc";
import { useAuth } from "@/context/AuthContext";
import { useOverview } from "@/hooks/useOverview";
import { categoryLabel, greeting, platformLabel, shortDate } from "@/lib/copy";
import { useCountUp } from "@/lib/useCountUp";
import { cn } from "@/lib/utils";
import { useWorkspace } from "@/lib/workspace";
import { appApi, errorMessage } from "@/services/api";
import type { Overview } from "@/types";

const PLATFORM_COLORS: Record<string, string> = { google: "#6cb8ff", zomato: "#ff5b3a", swiggy: "#f6b93b", direct: "#2bb673", other: "#a9acd0", tripadvisor: "#34a77b", instagram: "#f06ba8", facebook: "#4a6cf7" };

function Delta({ now, before, unit = "", invert = false }: { now: number | null; before: number | null; unit?: string; invert?: boolean }) {
  if (now === null || before === null || before === 0) return <span className="text-sm text-ink-soft">No data last week</span>;
  const diff = Math.round((now - before) * 10) / 10;
  if (diff === 0) return <span className="text-sm text-ink-soft">Same as last week</span>;
  const good = invert ? diff < 0 : diff > 0;
  const Icon = diff > 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={cn("inline-flex items-center gap-0.5 text-sm font-semibold", good ? "text-[#16784a]" : "text-[#c23a1c]")}>
      <Icon className="h-4 w-4" />{Math.abs(diff)}{unit} vs last week
    </span>
  );
}

function Kpi({ label, value, decimals = 0, suffix = "", children, tone = "light" }:
  { label: string; value: number; decimals?: number; suffix?: string; children?: React.ReactNode; tone?: "light" | "urgent" }) {
  const shown = useCountUp(value);
  return (
    <div className={cn("rounded-[18px] p-5", tone === "urgent" ? "bg-chilli text-white" : "border-2 border-line bg-white")}>
      <p className={cn("text-sm font-semibold", tone === "urgent" ? "text-white/85" : "text-ink-soft")}>{label}</p>
      <p className="tabular mt-1 font-display text-[2.6rem] font-bold leading-none">{shown.toFixed(decimals)}{suffix}</p>
      <div className="mt-2">{children}</div>
    </div>
  );
}

function TrendChart({ data }: { data: Overview["trend"] }) {
  const rows = data.map((d) => ({ ...d, label: shortDate(d.week_start) }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={rows} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <CartesianGrid stroke="#e6dcc8" strokeDasharray="3 4" vertical={false} />
        <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "#5b5d78", fontSize: 12 }} />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "#5b5d78", fontSize: 12 }} />
        <Tooltip contentStyle={{ borderRadius: 12, border: "2px solid #0c3b2e", fontFamily: "Hind Madurai" }}
          labelFormatter={(l) => `Week of ${l}`} />
        <Area type="monotone" dataKey="positive" name="Happy" stackId="1" stroke="#2bb673" fill="#2bb673" fillOpacity={0.85} />
        <Area type="monotone" dataKey="neutral" name="Mixed" stackId="1" stroke="#6cb8ff" fill="#6cb8ff" fillOpacity={0.85} />
        <Area type="monotone" dataKey="negative" name="Unhappy" stackId="1" stroke="#ff5b3a" fill="#ff5b3a" fillOpacity={0.85} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function NearbyCard() {
  const { data: outlets } = useQuery({ queryKey: ["outlets"], queryFn: appApi.outlets });
  const [picked, setPicked] = useState<number | null>(null);
  const outletId = picked ?? outlets?.[0]?.id ?? null;
  const { data, isFetching, error, refetch } = useQuery({
    queryKey: ["competitors", outletId], queryFn: () => appApi.competitors(outletId as number), enabled: outletId !== null, retry: false,
  });
  if (data && !data.enabled) {
    return (
      <section className="mt-5 rounded-[20px] border-2 border-dashed border-ink/20 bg-white p-5">
        <h2 className="text-xl">How you compare nearby</h2>
        <p className="mt-1 text-ink-soft">See your Google rating next to the restaurants around each outlet. Switched off: needs a Google Places key (GOOGLE_PLACES_API_KEY in .env).</p>
      </section>
    );
  }
  const you = data?.you?.rating ?? null;
  const rows = [...(data?.nearby ?? []).slice(0, 8)];
  const max = 5;
  return (
    <section className="mt-5 rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl">How you compare nearby</h2>
          <p className="text-sm text-ink-soft">Google ratings of restaurants around {data?.where ?? "your outlet"}. Updated once a day.</p>
        </div>
        {(outlets?.length ?? 0) > 1 ? (
          <select value={outletId ?? ""} onChange={(e) => setPicked(Number(e.target.value))} aria-label="Outlet"
            className="h-10 rounded-[12px] border-2 border-line bg-white px-3 text-sm">
            {outlets?.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
          </select>
        ) : null}
      </div>
      {error ? <p className="mt-4 text-chilli">{errorMessage(error)} <button type="button" className="underline cursor-pointer" onClick={() => void refetch()}>Try again</button></p> : null}
      {isFetching && !data ? <Skeleton className="mt-4 h-40" /> : null}
      {data?.enabled ? (
        <>
          <div className="mt-4 flex flex-wrap gap-6">
            <div><p className="text-sm text-ink-soft">You</p><p className="font-display text-3xl font-extrabold tabular">{you ? `${you.toFixed(1)}★` : "Not found"}</p></div>
            <div><p className="text-sm text-ink-soft">Area average</p><p className="font-display text-3xl font-extrabold tabular">{data.area_average ? `${data.area_average.toFixed(1)}★` : "-"}</p></div>
            {you && data.area_average ? (
              <p className={cn("self-end rounded-full px-3 py-1 text-sm font-semibold", you >= data.area_average ? "bg-leaf-soft text-leaf" : "bg-chilli-soft text-chilli")}>
                {you >= data.area_average ? "Above" : "Below"} the area by {Math.abs(you - data.area_average).toFixed(1)}★
              </p>
            ) : null}
          </div>
          <ul className="mt-4 space-y-2">
            {rows.map((r) => (
              <li key={r.id} className="grid grid-cols-[minmax(0,1fr)_120px_48px] items-center gap-3 text-sm">
                <span className="truncate">{r.name} <span className="text-ink-soft">({r.reviews.toLocaleString("en-IN")})</span></span>
                <span className="h-2.5 overflow-hidden rounded-full bg-jasmine-2"><span className="block h-full rounded-full bg-sky" style={{ width: `${((r.rating ?? 0) / max) * 100}%` }} /></span>
                <span className="tabular text-right font-semibold">{r.rating?.toFixed(1)}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

export default function Dashboard() {
  const { adminHome } = useWorkspace();
  if (adminHome) return <Navigate to="/app/admin" replace />;
  return <RestaurantDashboard />;
}

function RestaurantDashboard() {
  const { user } = useAuth();
  const { org } = useWorkspace();
  const [outletId, setOutletId] = useState<number | undefined>();
  const all = useOverview();
  const { data, isLoading, isError, error } = useOverview(outletId);
  const outlets = all.data?.outlets ?? [];
  const firstName = (user?.full_name ?? "").split(" ")[0];

  if (isError) {
    return <p className="rounded-[14px] bg-chilli-soft p-4 font-medium text-[#b32f12]">{errorMessage(error)}</p>;
  }

  const k = data?.kpis;
  const maxCat = Math.max(1, ...(data?.categories ?? []).map((c) => c.count));
  const platformTotal = (data?.platforms ?? []).reduce((s, p) => s + p.count, 0);
  const empty = data && k && k.reviews_week === 0 && data.trend.length === 0;

  return (
    <div className="mx-auto max-w-[1280px]">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[2.3rem] font-bold sm:text-[2.7rem]">{greeting()}{firstName ? `, ${firstName}` : ""}</h1>
          <p className="mt-1 text-lg text-ink-soft">Here's how guests felt about {org?.name ?? "your restaurant"} this week.</p>
        </div>
        {outlets.length > 1 ? (
          <div className="flex flex-wrap gap-1.5 rounded-full bg-jasmine-2 p-1" role="radiogroup" aria-label="Outlet">
            {[{ id: undefined, name: "All outlets" }, ...outlets.map((o) => ({ id: o.outlet_id, name: o.name }))].map((o) => (
              <button key={o.name} role="radio" aria-checked={outletId === o.id} onClick={() => setOutletId(o.id)}
                className={cn("rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors cursor-pointer",
                  outletId === o.id ? "bg-night text-jasmine" : "text-ink-soft hover:text-ink")}>
                {o.name}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {empty ? (
        <section className="mt-8 rounded-[22px] border-2 border-line bg-white p-6 sm:p-8" aria-label="Get started">
          <h2 className="text-2xl font-bold">Get set up in 10 minutes</h2>
          <p className="mt-1 max-w-xl text-ink-soft">Do these once. After that, reviews come in and get read by themselves, and this page fills up with charts, outlet scores and urgent replies.</p>
          <ol className="mt-6 grid gap-4 md:grid-cols-2">
            {[
              ["Add your outlets", "Name, district and manager for each branch. Each gets its own QR code.", "/app/settings", "Add outlets"],
              ["Connect Google", "Your Google reviews arrive every 10 minutes, for every branch.", "/app/connections", "Connect Google"],
              ["Print your QR codes", "On the bill and the food packet. Guests rate you in seconds.", "/app/automation", "Get QR codes"],
              ["Add Zomato and Swiggy reviews", "Paste them, or upload a file with an outlet column.", "/app/import", "Add reviews"],
            ].map(([title = "", body, to = "/app", cta], i) => (
              <li key={title} className="flex gap-4 rounded-[16px] bg-jasmine p-4">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-night font-display font-bold text-jasmine">{i + 1}</span>
                <div>
                  <p className="font-display text-lg font-bold">{title}</p>
                  <p className="text-ink-soft">{body}</p>
                  <Link to={to} className={cn(buttonVariants({ size: "sm", variant: i === 0 ? "primary" : "outline" }), "mt-3")}>{cta}</Link>
                </div>
              </li>
            ))}
          </ol>
        </section>
      ) : (
        <>
          <section className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="This week">
            {isLoading || !k ? Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[138px]" />) : (
              <>
                <Kpi label="Need a reply today" value={k.urgent_pending} tone="urgent">
                  <Link to="/app/inbox?view=today" className="inline-flex rounded-full bg-white/20 px-3 py-1 text-sm font-semibold hover:bg-white/30">Open these in the inbox</Link>
                </Kpi>
                <Kpi label="Reviews this week" value={k.reviews_week}><Delta now={k.reviews_week} before={k.reviews_prev_week} /></Kpi>
                <Kpi label="Happy guests" value={k.positive_pct} suffix="%"><Delta now={k.positive_pct} before={k.positive_pct_prev} unit=" pts" /></Kpi>
                <Kpi label="Average rating" value={k.avg_rating ?? 0} decimals={1} suffix="★"><Delta now={k.avg_rating} before={k.avg_rating_prev} /></Kpi>
              </>
            )}
          </section>

          <section className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-[1.6fr_1fr]">
            <div className="rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-xl font-bold">How guests felt, week by week</h2>
                <div className="flex gap-3 text-sm text-ink-soft">
                  {[["Happy", "bg-leaf"], ["Mixed", "bg-sky"], ["Unhappy", "bg-chilli"]].map(([l, c]) => (
                    <span key={l} className="flex items-center gap-1.5"><span className={cn("h-2.5 w-2.5 rounded-full", c)} />{l}</span>
                  ))}
                </div>
              </div>
              <div className="mt-4">{data ? <TrendChart data={data.trend} /> : <Skeleton className="h-[260px]" />}</div>
            </div>

            <div className="rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
              <h2 className="text-xl font-bold">What guests complained about</h2>
              <p className="text-sm text-ink-soft">Last 30 days, mixed and unhappy reviews</p>
              <ul className="mt-5 space-y-3">
                {(data?.categories ?? []).map((c) => (
                  <li key={c.category}>
                    <div className="flex justify-between text-sm"><span className="font-semibold">{categoryLabel[c.category]}</span><span className="tabular font-bold">{c.count}</span></div>
                    <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-jasmine-2">
                      <div className={cn("h-full rounded-full transition-[width] duration-700", c.category === "hygiene" ? "bg-chilli" : "bg-turmeric")} style={{ width: `${(c.count / maxCat) * 100}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-[1.6fr_1fr]">
            <div className="rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
              <h2 className="text-xl font-bold">Outlets compared</h2>
              <p className="text-sm text-ink-soft">Last 30 days. Click an outlet to see only its numbers.</p>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[520px] text-left">
                  <thead className="text-sm text-ink-soft">
                    <tr><th className="py-2 font-semibold">Outlet</th><th className="font-semibold">Rating</th><th className="font-semibold">Reviews</th><th className="w-[30%] font-semibold">Unhappy</th><th className="text-right font-semibold">Reply today</th></tr>
                  </thead>
                  <tbody>
                    {(all.data?.outlets ?? []).map((o) => (
                      <tr key={o.outlet_id} onClick={() => setOutletId(o.outlet_id === outletId ? undefined : o.outlet_id)}
                        className={cn("cursor-pointer border-t-2 border-jasmine-2 transition-colors hover:bg-jasmine", outletId === o.outlet_id && "bg-jasmine")}>
                        <td className="py-3"><p className="font-semibold">{o.name}</p><p className="text-sm text-ink-soft">{o.city}</p></td>
                        <td className="tabular font-display text-lg font-bold">{o.avg_rating?.toFixed(1) ?? "-"}★</td>
                        <td className="tabular">{o.reviews}</td>
                        <td>
                          <div className="flex items-center gap-2">
                            <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-jasmine-2"><div className="h-full rounded-full bg-chilli" style={{ width: `${o.negative_pct}%` }} /></div>
                            <span className="tabular w-12 text-sm font-semibold">{o.negative_pct}%</span>
                          </div>
                        </td>
                        <td className="text-right">{o.urgent_pending ? <Chip tone="chilli">{o.urgent_pending}</Chip> : <Chip tone="leaf">0</Chip>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
              <h2 className="text-xl font-bold">Where reviews came from</h2>
              <div className="mt-2 flex items-center gap-4">
                <div className="h-[170px] w-[170px] shrink-0">
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie data={data?.platforms ?? []} dataKey="count" nameKey="platform" innerRadius={50} outerRadius={78} paddingAngle={3} stroke="none">
                        {(data?.platforms ?? []).map((p) => <Cell key={p.platform} fill={PLATFORM_COLORS[p.platform] ?? "#a9acd0"} />)}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <ul className="space-y-2">
                  {(data?.platforms ?? []).map((p) => (
                    <li key={p.platform} className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full" style={{ background: PLATFORM_COLORS[p.platform] }} />
                      <span className="font-semibold">{platformLabel[p.platform]}</span>
                      <span className="tabular text-ink-soft">{platformTotal ? Math.round((p.count / platformTotal) * 100) : 0}%</span>
                    </li>
                  ))}
                </ul>
              </div>
              {k ? <p className="mt-3 rounded-[12px] bg-jasmine px-4 py-3 text-sm"><span className="font-bold">{k.reply_rate_30d}%</span> of reviews got a reply in the last 30 days.</p> : null}
            </div>
          </section>
          <NearbyCard />

          <section className="mt-5 rounded-[20px] bg-night p-5 text-jasmine sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xl font-bold">Guests waiting for a reply</h2>
              <Link to="/app/inbox?view=today" className={buttonVariants({ size: "sm" })}>Reply in the inbox</Link>
            </div>
            {data && data.urgent.length === 0 ? <p className="mt-4 text-mist">Nothing urgent. Every guest who needed a reply has one.</p> : null}
            <ul className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {(data?.urgent ?? []).map((u) => (
                <li key={u.id}>
                  <Link to={`/app/inbox?view=today&id=${u.id}`} className="block h-full rounded-[16px] bg-white/[0.06] p-4 transition-colors hover:bg-white/[0.11]">
                    <div className="flex items-center justify-between text-sm text-mist">
                      <span>{platformLabel[u.platform]}, {u.outlet_name}, {shortDate(u.review_date)}</span>
                      <Stars rating={u.rating} />
                    </div>
                    <p className="mt-2 font-display text-[1.05rem] font-semibold leading-snug">{u.summary}</p>
                    <p className="mt-1 line-clamp-2 text-sm text-mist">{u.review_text}</p>
                    {u.category === "hygiene" ? <p className="mt-2 flex items-center gap-1.5 text-sm font-semibold text-[#ffb3a3]"><ShieldAlert className="h-4 w-4" />Food safety</p> : null}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
