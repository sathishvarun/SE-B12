import { useQuery } from "@tanstack/react-query";
import { Check, CreditCard, Gift, Minus, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button, buttonVariants } from "@/components/ui/button";
import { Spinner } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { billingApi, type PricingTable } from "@/services/api";

// Same numbers as backend/app/services/pricing.py. Used only until the server's table loads;
// the server always recomputes the real amount before taking a payment.
const FALLBACK: PricingTable = {
  tiers: [
    { from_outlets: 1, per_outlet_month: 1499, name: "Single outlet" },
    { from_outlets: 2, per_outlet_month: 1199, name: "Small chain" },
    { from_outlets: 6, per_outlet_month: 949, name: "Growing chain" },
    { from_outlets: 21, per_outlet_month: 799, name: "Large chain" },
    { from_outlets: 51, per_outlet_month: 649, name: "Enterprise chain" },
  ],
  durations: [
    { months: 1, discount_percent: 0, bonus_months: 0 },
    { months: 3, discount_percent: 5, bonus_months: 0 },
    { months: 6, discount_percent: 10, bonus_months: 0 },
    { months: 9, discount_percent: 10, bonus_months: 1 },
    { months: 12, discount_percent: 15, bonus_months: 2 },
  ],
  max_outlets: 500,
  reviews_per_outlet: 500,
};

const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;

export function quoteFrom(t: PricingTable, outlets: number, months: number) {
  const first = t.tiers[0] ?? { from_outlets: 1, per_outlet_month: 1499, name: "Single outlet" };
  let tier = first;
  for (const x of t.tiers) if (outlets >= x.from_outlets) tier = x;
  const d = t.durations.find((x) => x.months === months) ?? { months, discount_percent: 0, bonus_months: 0 };
  const total = Math.round((tier.per_outlet_month * outlets * months * (100 - d.discount_percent)) / 100);
  const listTotal = first.per_outlet_month * outlets * (months + d.bonus_months);
  return {
    tier,
    duration: d,
    total,
    youSave: Math.max(0, listTotal - total),
    effective: Math.round(total / outlets / (months + d.bonus_months)),
  };
}

interface Props {
  tone?: "dark" | "light";
  initialOutlets?: number;
  /** When given, the button pays instead of starting a trial. */
  onPay?: (outlets: number, months: number) => void;
  paying?: boolean;
  payDisabled?: boolean;
}

export function PriceCalculator({ tone = "dark", initialOutlets = 1, onPay, paying, payDisabled }: Props) {
  const { data } = useQuery({ queryKey: ["pricing-table"], queryFn: billingApi.pricing, staleTime: 3_600_000 });
  const table = data ?? FALLBACK;
  const [outlets, setOutlets] = useState(Math.max(1, initialOutlets));
  const [months, setMonths] = useState(12);
  const q = useMemo(() => quoteFrom(table, outlets, months), [table, outlets, months]);
  const dark = tone === "dark";
  const soft = dark ? "text-mist" : "text-ink-soft";
  const clamp = (n: number) => Math.min(table.max_outlets, Math.max(1, Math.round(n) || 1));

  return (
    <div className={cn("grid gap-6 rounded-[24px] p-5 sm:p-7 lg:grid-cols-[1.15fr_1fr]", dark ? "bg-night-2 text-jasmine" : "border-2 border-line bg-white text-ink")}>
      <div>
        <label htmlFor="outlets" className="font-display text-xl font-bold">How many outlets?</label>
        <div className="mt-3 flex items-center gap-3">
          <button type="button" aria-label="One fewer outlet" onClick={() => setOutlets((n) => clamp(n - 1))}
            className={cn("grid h-11 w-11 shrink-0 place-items-center rounded-full cursor-pointer", dark ? "bg-white/10 hover:bg-white/20" : "bg-jasmine-2 hover:bg-line")}>
            <Minus className="h-4 w-4" />
          </button>
          <input id="outlets" type="number" inputMode="numeric" min={1} max={table.max_outlets} value={outlets}
            onChange={(e) => setOutlets(clamp(Number(e.target.value)))}
            className={cn("tabular h-12 w-24 rounded-[12px] border-2 text-center font-display text-2xl font-bold", dark ? "border-white/20 bg-night text-jasmine" : "border-line bg-white")} />
          <button type="button" aria-label="One more outlet" onClick={() => setOutlets((n) => clamp(n + 1))}
            className={cn("grid h-11 w-11 shrink-0 place-items-center rounded-full cursor-pointer", dark ? "bg-white/10 hover:bg-white/20" : "bg-jasmine-2 hover:bg-line")}>
            <Plus className="h-4 w-4" />
          </button>
        </div>
        <input type="range" min={1} max={150} value={Math.min(outlets, 150)} aria-label="Outlets slider"
          onChange={(e) => setOutlets(clamp(Number(e.target.value)))} className="mt-3 h-8 w-full cursor-pointer accent-turmeric" />

        <ul className="mt-4 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
          {table.tiers.map((t, i) => {
            const next = table.tiers[i + 1];
            const active = t === q.tier;
            return (
              <li key={t.name} className={cn("rounded-[12px] px-3 py-2", active ? "bg-turmeric text-night" : dark ? "bg-white/5" : "bg-jasmine-2")}>
                <p className="font-semibold">{next ? (next.from_outlets - 1 === t.from_outlets ? `${t.from_outlets} outlet` : `${t.from_outlets}–${next.from_outlets - 1} outlets`) : `${t.from_outlets}+ outlets`}</p>
                <p className="tabular">{inr(t.per_outlet_month)} each / month</p>
              </li>
            );
          })}
        </ul>

        <p className="mt-6 font-display text-xl font-bold">For how long?</p>
        <div className="mt-3 grid grid-cols-5 gap-2" role="radiogroup" aria-label="Months">
          {table.durations.map((d) => (
            <button key={d.months} type="button" role="radio" aria-checked={months === d.months} onClick={() => setMonths(d.months)}
              className={cn("rounded-[14px] px-1 py-2.5 text-center cursor-pointer transition-colors",
                months === d.months ? "bg-turmeric text-night" : dark ? "bg-white/10 hover:bg-white/20" : "bg-jasmine-2 hover:bg-line")}>
              <span className="block font-display text-lg font-bold">{d.months}</span>
              <span className="block text-xs">{d.months === 1 ? "month" : "months"}</span>
              <span className="block text-xs font-semibold">{d.bonus_months ? `+${d.bonus_months} free` : d.discount_percent ? `${d.discount_percent}% off` : " "}</span>
            </button>
          ))}
        </div>
      </div>

      <div className={cn("flex flex-col rounded-[20px] p-5", dark ? "bg-jasmine text-ink" : "bg-night text-jasmine")}>
        <p className={dark ? "text-ink-soft" : "text-mist"}>{q.tier.name} · {outlets} outlet{outlets === 1 ? "" : "s"} · {months} month{months === 1 ? "" : "s"}</p>
        <p className="tabular mt-1 font-display text-[2.8rem] font-bold leading-none">{inr(q.total)}</p>
        <p className={cn("mt-1", dark ? "text-ink-soft" : "text-mist")}>one payment, GST included</p>
        {q.duration.bonus_months ? (
          <p className="mt-4 flex items-center gap-2 rounded-[12px] bg-leaf/15 px-3 py-2 font-semibold">
            <Gift className="h-4 w-4 shrink-0" /> {q.duration.bonus_months} extra month{q.duration.bonus_months > 1 ? "s" : ""} free: {months + q.duration.bonus_months} months of use
          </p>
        ) : null}
        <ul className="mt-4 space-y-2">
          <li className="flex gap-2"><Check className="mt-1 h-4 w-4 shrink-0 text-leaf" /><span>Works out to <b className="tabular">{inr(q.effective)}</b> per outlet per month</span></li>
          {q.youSave > 0 ? <li className="flex gap-2"><Check className="mt-1 h-4 w-4 shrink-0 text-leaf" /><span>You save <b className="tabular">{inr(q.youSave)}</b> against paying the single-outlet monthly price</span></li> : null}
          <li className="flex gap-2"><Check className="mt-1 h-4 w-4 shrink-0 text-leaf" />{(outlets * table.reviews_per_outlet).toLocaleString("en-IN")} reviews read a month</li>
          <li className="flex gap-2"><Check className="mt-1 h-4 w-4 shrink-0 text-leaf" />Everything included: alerts, reply drafts, QR feedback, Google auto-pilot</li>
        </ul>
        <div className="mt-auto pt-6">
          {onPay ? (
            <Button className="w-full" size="lg" variant={dark ? "dark" : "primary"} onClick={() => onPay(outlets, months)} disabled={payDisabled || paying}>
              {paying ? <><Spinner /> Opening payment page...</> : <><CreditCard className="h-4 w-4" /> Pay {inr(q.total)}</>}
            </Button>
          ) : (
            <Link to="/register" className={cn(buttonVariants({ variant: "dark", size: "lg" }), "w-full")}>Start 14-day free trial</Link>
          )}
          {outlets >= table.max_outlets ? <p className={cn("mt-2 text-sm", soft)}>More than {table.max_outlets} outlets? <Link to="/contact" className="underline">Talk to us</Link>.</p> : null}
        </div>
      </div>
    </div>
  );
}
