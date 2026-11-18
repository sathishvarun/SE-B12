import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CreditCard, Lock } from "lucide-react";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { PriceCalculator, quoteFrom } from "@/components/site/PriceCalculator";
import { Skeleton } from "@/components/ui/misc";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { billingApi, errorMessage, type BillingDetails, type BillingStatus } from "@/services/api";

interface RazorpayResponse { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }
interface RazorpayInstance { open: () => void; on: (event: string, cb: (r: { error?: { description?: string } }) => void) => void }
declare global { interface Window { Razorpay?: new (options: Record<string, unknown>) => RazorpayInstance } }

const PLAN_NAME: Record<string, string> = { trial: "Free trial", starter: "Single outlet", growth: "Small chain", chain: "Chain" };
const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;
const longDate = (iso: string) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });

function loadCheckout(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Couldn't load Razorpay. Check your internet connection and try again."));
    document.body.appendChild(s);
  });
}

function BillingForm({ initial, value, onChange }: { initial?: BillingStatus["billing"]; value: BillingDetails | null; onChange: (v: BillingDetails) => void }) {
  const v = value ?? { company_name: initial?.company_name ?? "", gstin: initial?.gstin ?? "", address: initial?.address ?? "" };
  const set = (k: keyof BillingDetails) => (e: ChangeEvent<HTMLInputElement>) => onChange({ ...v, [k]: e.target.value });
  return (
    <fieldset className="mt-4 grid gap-3 rounded-[16px] border-2 border-line bg-white p-4 sm:grid-cols-2">
      <legend className="px-1 text-sm font-semibold">Printed on your receipt and invoice</legend>
      <label className="text-sm font-semibold">Company or restaurant name
        <input value={v.company_name} onChange={set("company_name")} maxLength={160} className="mt-1 block h-11 w-full rounded-[10px] border-2 border-line px-3 font-normal" /></label>
      <label className="text-sm font-semibold">GSTIN (optional)
        <input value={v.gstin} onChange={set("gstin")} maxLength={15} placeholder="33ABCDE1234F1Z5" className="mt-1 block h-11 w-full rounded-[10px] border-2 border-line px-3 font-normal uppercase" /></label>
      <label className="text-sm font-semibold sm:col-span-2">Billing address, with pincode
        <input value={v.address} onChange={set("address")} maxLength={300} placeholder="Door no, street, area, city, pincode" className="mt-1 block h-11 w-full rounded-[10px] border-2 border-line px-3 font-normal" /></label>
    </fieldset>
  );
}

export default function Billing() {
  const qc = useQueryClient();
  const { refreshUser } = useAuth();
  const [paying, setPaying] = useState(false);
  const [details, setDetails] = useState<BillingDetails | null>(null);
  const { data, isLoading } = useQuery({ queryKey: ["billing"], queryFn: billingApi.status });
  const [params, setParams] = useSearchParams();
  const confirming = useRef(false);

  // Back from Dodo's checkout page: ask the server to check the payment with Dodo.
  useEffect(() => {
    const paymentId = params.get("payment_id");
    if (!paymentId || confirming.current) return;
    confirming.current = true;
    billingApi.confirm(paymentId)
      .then(async (r) => {
        if (r.status === "succeeded") { toast.success(`Payment received. You're on the ${PLAN_NAME[r.plan] ?? r.plan} plan.`); await refreshUser(); }
        else if (r.status === "failed" || r.status === "cancelled") toast.error("The payment didn't go through. No money was taken.");
        else toast("Your payment is still being confirmed. This page will update in a minute.");
      })
      .catch((err) => toast.error(errorMessage(err)))
      .finally(() => { setParams({}, { replace: true }); void qc.invalidateQueries({ queryKey: ["billing"] }); });
  }, [params, setParams, qc, refreshUser]);

  async function pay(outlets: number, months: number) {
    setPaying(true);
    if (data?.provider === "dodo") {
      try {
        const bill = details ?? { company_name: data.billing?.company_name ?? "", gstin: data.billing?.gstin ?? "", address: data.billing?.address ?? "" };
        const { checkout_url } = await billingApi.checkout(outlets, months, bill);
        window.location.assign(checkout_url);
      } catch (err) { toast.error(errorMessage(err)); setPaying(false); }
      return;
    }
    try {
      await loadCheckout();
      const order = await billingApi.order(outlets, months);
      if (!window.Razorpay) throw new Error("Razorpay didn't load. Please refresh and try again.");
      const rzp = new window.Razorpay({
        key: order.key_id,
        order_id: order.order_id,
        amount: order.amount,
        currency: order.currency,
        name: "Virundhu",
        description: `${outlets} outlet${outlets === 1 ? "" : "s"}, ${months} month${months === 1 ? "" : "s"}`,
        prefill: { name: order.name, email: order.email },
        notes: { restaurant: order.restaurant },
        theme: { color: "#11132A" },
        handler: async (res: RazorpayResponse) => {
          try {
            await billingApi.verify(res);
            toast.success("Payment received. Thank you!");
            await refreshUser();
            void qc.invalidateQueries({ queryKey: ["billing"] });
          } catch (err) { toast.error(errorMessage(err)); }
        },
        modal: { ondismiss: () => setPaying(false) },
      });
      rzp.on("payment.failed", (r) => toast.error(r.error?.description ?? "The payment didn't go through. No money was taken."));
      rzp.open();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setPaying(false);
    }
  }

  if (isLoading || !data) return <div className="mx-auto max-w-5xl"><Skeleton className="h-[420px]" /></div>;

  const onTrial = data.plan === "trial";
  const step = params.get("step");
  if (step === "checkout") {
    const outlets = Math.max(1, Number(params.get("outlets")) || 1);
    const months = Number(params.get("months")) || 1;
    const bill = details ?? { company_name: data.billing?.company_name ?? "", gstin: data.billing?.gstin ?? "", address: data.billing?.address ?? "" };
    return <Checkout data={data} outlets={outlets} months={months} bill={bill} paying={paying}
      onBack={() => setParams({}, { replace: false })} onPay={() => pay(outlets, months)} />;
  }
  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-[2.3rem] font-bold">Plan and billing</h1>

      <section className={cn("mt-5 rounded-[20px] border-2 p-5 sm:p-6", data.expired ? "border-chilli bg-chilli-soft" : "border-line bg-white")}>
        <p className="text-sm text-ink-soft">Your plan</p>
        <p className="font-display text-3xl font-bold">{PLAN_NAME[data.plan] ?? data.plan}</p>
        <p className="mt-1 text-ink-soft">
          {data.ends_at
            ? data.expired
              ? `${onTrial ? "Your trial" : "Your plan"} ended on ${longDate(data.ends_at)}. Every menu is locked until you pay; your reviews and settings are kept safe.`
              : `${onTrial ? "Trial ends" : "Paid until"} ${longDate(data.ends_at)}.`
            : null}
          {" "}{data.paid_outlets ? `Paid for ${data.paid_outlets} outlet${data.paid_outlets === 1 ? "" : "s"}: ` : ""}{data.limits.outlets} outlet{data.limits.outlets === 1 ? "" : "s"}, {data.limits.reviews_per_month.toLocaleString("en-IN")} reviews a month.
        </p>
      </section>

      {data.promo && data.payments_enabled ? (
        <div className="mt-5 flex flex-wrap items-center gap-3 rounded-[16px] border-2 border-dashed border-night bg-turmeric/30 px-4 py-3">
          <span className="rounded-[10px] bg-night px-3 py-1.5 font-mono text-lg font-bold tracking-wider text-turmeric">{data.promo.code}</span>
          <p className="font-medium">{data.promo.text || "Launch offer."} Enter the code on the payment page.</p>
        </div>
      ) : null}

      <h2 className="mt-7 font-display text-2xl font-bold">{onTrial || data.expired ? "Choose outlets and months" : "Renew or add outlets"}</h2>
      <p className="mt-1 text-ink-soft">
        You have {data.outlets_now} outlet{data.outlets_now === 1 ? "" : "s"} set up. The price per outlet drops as you add outlets, and longer periods get a discount.
        {!onTrial && !data.expired ? " Paying now adds the new period after your current one ends." : ""}
      </p>
      <BillingForm initial={data.billing} value={details} onChange={setDetails} />
      <div className="mt-4">
        <div id="choose-plan" className="scroll-mt-6"><PriceCalculator tone="light" initialOutlets={data.paid_outlets ?? data.outlets_now} initialMonths={null} onPay={(o, m) => { setParams({ step: "checkout", outlets: String(o), months: String(m) }); window.scrollTo({ top: 0 }); }} /></div>
      </div>
      <p className="mt-3 flex items-center gap-2 text-sm text-ink-soft"><Lock className="h-4 w-4" /> {data.provider === "dodo" ? "Paid securely through Dodo Payments: UPI and cards, with a GST invoice. Virundhu never sees your card details." : "Paid securely through Razorpay: UPI, cards, net banking and wallets. Virundhu never sees your card details."}</p>

      <h2 className="mt-9 font-display text-2xl font-bold">Payments</h2>
      {data.payments.length ? (
        <div className="mt-3 overflow-x-auto rounded-[16px] border-2 border-line bg-white">
          <table className="w-full text-left">
            <thead className="text-sm text-ink-soft"><tr><th className="px-4 py-3">Date</th><th className="px-4 py-3">Receipt</th><th className="px-4 py-3">Plan</th><th className="px-4 py-3">Amount</th><th className="px-4 py-3"><span className="sr-only">Open</span></th></tr></thead>
            <tbody>
              {data.payments.map((p) => (
                <tr key={p.id} className="border-t-2 border-jasmine-2">
                  <td className="px-4 py-3">{longDate(p.paid_at)}</td>
                  <td className="px-4 py-3 font-mono text-sm">{p.invoice_no ?? p.id}</td>
                  <td className="px-4 py-3 text-sm">{p.outlets ? `${p.outlets} outlet${p.outlets > 1 ? "s" : ""}, ${p.months} mo` : "-"}</td>
                  <td className="tabular px-4 py-3 font-semibold">{inr(p.amount)}</td>
                  <td className="px-4 py-3"><Link to={`/app/receipt/${p.receipt_id}`} className="font-semibold underline">View / print</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="mt-2 text-ink-soft">No payments yet.</p>}
    </div>
  );
}

/** Step 2 of paying: what they are buying, for whom, and the total. "Pay" opens the secure payment page. */
function Checkout({ data, outlets, months, bill, paying, onBack, onPay }: {
  data: BillingStatus; outlets: number; months: number; bill: BillingDetails; paying: boolean; onBack: () => void; onPay: () => void;
}) {
  const { data: table } = useQuery({ queryKey: ["pricing-table"], queryFn: billingApi.pricing, staleTime: 3_600_000 });
  if (!table) return <div className="mx-auto max-w-3xl"><Skeleton className="h-[420px]" /></div>;
  const q = quoteFrom(table, outlets, months);
  const totalMonths = months + q.duration.bonus_months;
  const start = data.expired || !data.ends_at ? new Date() : new Date(data.ends_at);
  const end = new Date(start); end.setMonth(end.getMonth() + totalMonths);
  const day = (d: Date) => d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;
  const rows: [string, string][] = [
    ["Restaurant", bill.company_name || "-"],
    ...(bill.gstin ? [["GSTIN", bill.gstin] as [string, string]] : []),
    ...(bill.address ? [["Billing address", bill.address] as [string, string]] : []),
    ["Plan", `${q.tier.name}, ${inr(q.tier.per_outlet_month)} per outlet a month`],
    ["Outlets", String(outlets)],
    ["Months", `${months}${q.duration.bonus_months ? ` + ${q.duration.bonus_months} free = ${totalMonths} months` : ""}`],
    ...(q.duration.discount_percent ? [["Discount", `${q.duration.discount_percent}% off`] as [string, string]] : []),
    ["Plan valid", `${day(start)} to ${day(end)}`],
  ];
  return (
    <div className="mx-auto max-w-3xl">
      <button type="button" onClick={onBack} className="flex cursor-pointer items-center gap-2 font-semibold text-ink-soft hover:text-ink"><ArrowLeft className="h-4 w-4" /> Change outlets or months</button>
      <h1 className="mt-3 text-[2.3rem] font-bold">Review and pay</h1>
      <section className="mt-5 overflow-hidden rounded-[20px] border-2 border-line bg-white">
        <dl className="divide-y-2 divide-jasmine-2">
          {rows.map(([k, v]) => (
            <div key={k} className="grid grid-cols-[40%_60%] gap-3 px-5 py-3"><dt className="text-ink-soft">{k}</dt><dd className="font-semibold">{v}</dd></div>
          ))}
        </dl>
        <div className="flex flex-wrap items-end justify-between gap-3 bg-night px-5 py-5 text-jasmine">
          <div><p className="text-mist">Total to pay, GST included</p><p className="tabular font-display text-[2.6rem] font-bold leading-none">{inr(q.total)}</p></div>
          {q.youSave > 0 ? <p className="rounded-[12px] bg-leaf/20 px-3 py-1.5 font-semibold">You save {inr(q.youSave)}</p> : null}
        </div>
      </section>
      <button type="button" onClick={onPay} disabled={paying}
        className="mt-5 flex w-full cursor-pointer items-center justify-center gap-2 rounded-[14px] bg-chilli px-5 py-4 font-display text-lg font-bold text-white hover:opacity-90 disabled:opacity-60">
        <CreditCard className="h-5 w-5" /> {paying ? "Opening the payment page..." : `Pay ${inr(q.total)} securely`}
      </button>
      <p className="mt-3 flex items-center gap-2 text-sm text-ink-soft"><Lock className="h-4 w-4" /> You'll go to {data.provider === "dodo" ? "Dodo Payments" : "Razorpay"} to pay by UPI or card. Your plan starts, and every menu unlocks, as soon as the payment succeeds.</p>
    </div>
  );
}
