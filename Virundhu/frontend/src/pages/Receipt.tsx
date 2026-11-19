import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { LogoMark } from "@/components/layout/Logo";
import { Skeleton } from "@/components/ui/misc";
import { billingApi, errorMessage } from "@/services/api";

const inr = (n: number) => `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const day = (d: string | null) => (d ? new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }) : "-");

/** A printable receipt (Print → Save as PDF). Owners see their own; the admin sees any, for audit. */
export default function ReceiptPage() {
  const { id } = useParams();
  const { data: r, isLoading, error } = useQuery({ queryKey: ["receipt", id], queryFn: () => billingApi.receipt(Number(id)), enabled: !!id });
  if (isLoading) return <Skeleton className="h-[480px]" />;
  if (error || !r) return <p className="font-semibold text-chilli">{error ? errorMessage(error) : "Receipt not found."}</p>;
  const rows: [string, string][] = [
    ["Plan", `${r.outlets ?? "-"} outlet${r.outlets === 1 ? "" : "s"}, ${r.months ?? "-"} month${r.months === 1 ? "" : "s"}`],
    ["Period covered", `${day(r.period_start)} to ${day(r.period_end)}`],
    ["Payment ID", r.payment_id],
    ["Status", r.status === "paid" ? "Paid" : r.status],
  ];
  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 print:hidden">
        <Link to="/app/billing" className="font-semibold underline">Back to Plan and billing</Link>
        <button onClick={() => window.print()} className="flex h-11 items-center gap-2 rounded-[12px] bg-night px-4 font-semibold text-jasmine cursor-pointer">
          <Printer className="h-4 w-4" /> Print or save as PDF
        </button>
      </div>
      <article className="receipt-print rounded-[20px] border-2 border-line bg-white p-6 sm:p-10 print:border-0 print:p-0">
        <header className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-jasmine-2 pb-5">
          <div className="flex items-center gap-3"><LogoMark className="h-10 w-10" /><div>
            <p className="font-display text-xl font-bold">{r.seller.name || "Virundhu"}</p>
            {r.seller.parent ? <p className="text-sm text-ink-soft">A product of {r.seller.parent}{r.seller.gstin ? `, GSTIN ${r.seller.gstin}` : ""}</p> : null}
            {r.seller.address ? <p className="text-sm text-ink-soft">{r.seller.address}</p> : null}
            {r.seller.email ? <p className="text-sm text-ink-soft">{r.seller.email}</p> : null}
          </div></div>
          <div className="text-right">
            <p className="font-display text-2xl font-bold">Payment receipt</p>
            <p className="font-mono text-sm">{r.invoice_no ?? "-"}</p>
            <p className="text-sm text-ink-soft">{day(r.paid_at)}</p>
          </div>
        </header>
        <section className="mt-5">
          <p className="text-sm font-semibold text-ink-soft">Billed to</p>
          <p className="text-lg font-bold">{r.bill_name}</p>
          {r.bill_gstin ? <p>GSTIN: <span className="font-mono">{r.bill_gstin}</span></p> : null}
          {r.bill_address ? <p>{r.bill_address}</p> : null}
          {r.bill_email ? <p className="text-ink-soft">{r.bill_email}</p> : null}
          {r.bill_name !== r.restaurant ? <p className="text-ink-soft">Restaurant: {r.restaurant}</p> : null}
        </section>
        <table className="mt-6 w-full text-left">
          <tbody>
            {rows.map(([k, v]) => <tr key={k} className="border-t-2 border-jasmine-2"><th className="w-44 py-2.5 font-semibold text-ink-soft">{k}</th><td className="py-2.5">{v}</td></tr>)}
            <tr className="border-t-2 border-night"><th className="py-3 text-lg font-bold">Amount paid</th><td className="py-3 text-lg font-bold tabular">{inr(r.amount)} <span className="text-sm font-normal text-ink-soft">(taxes included)</span></td></tr>
          </tbody>
        </table>
        <p className="mt-6 text-sm text-ink-soft">Paid through Dodo Payments, our payment partner and merchant of record, which emails the tax invoice separately. Keep this receipt for your records.</p>
      </article>
    </div>
  );
}
