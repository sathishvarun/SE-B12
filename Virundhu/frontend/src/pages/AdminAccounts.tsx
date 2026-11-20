import { useQuery } from "@tanstack/react-query";
import { Download, FileSpreadsheet } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Chip, Skeleton, Spinner } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { accountsApi, errorMessage } from "@/services/api";

type Kind = "month" | "quarter" | "fy";
const inr = (x: number) => `₹${x.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Financial year that contains a date (April to March): 2026 means Apr 2026 - Mar 2027. */
const fyOf = (d: Date) => (d.getMonth() >= 3 ? d.getFullYear() : d.getFullYear() - 1);
const quarterOf = (d: Date) => Math.floor(((d.getMonth() + 9) % 12) / 3) + 1;

function choices(kind: Kind): { value: string; label: string }[] {
  const now = new Date();
  const firstFy = 2026; // the company started in July 2026
  if (kind === "fy") {
    return Array.from({ length: fyOf(now) - firstFy + 1 }, (_, i) => fyOf(now) - i).map((y) => ({ value: `FY${y}`, label: `FY ${y}-${String(y + 1).slice(2)} (Apr ${y} to Mar ${y + 1})` }));
  }
  if (kind === "quarter") {
    const out = [];
    for (let y = fyOf(now); y >= firstFy; y--) {
      for (let q = y === fyOf(now) ? quarterOf(now) : 4; q >= 1; q--) out.push({ value: `${y}-Q${q}`, label: `Q${q} FY ${y}-${String(y + 1).slice(2)} (${["Apr-Jun", "Jul-Sep", "Oct-Dec", "Jan-Mar"][q - 1]})` });
    }
    return out;
  }
  const out = [];
  const d = new Date(now.getFullYear(), now.getMonth(), 1);
  while (d >= new Date(2026, 6, 1)) {
    out.push({ value: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`, label: `${MONTHS[d.getMonth()]} ${d.getFullYear()}` });
    d.setMonth(d.getMonth() - 1);
  }
  return out;
}

export function AccountsPanel() {
  const [kind, setKind] = useState<Kind>("month");
  const options = useMemo(() => choices(kind), [kind]);
  const [picked, setPicked] = useState<Record<Kind, string>>({ month: "", quarter: "", fy: "" });
  const period = picked[kind] || options[0]?.value || "";
  const [busy, setBusy] = useState(false);
  const { data: s } = useQuery({ queryKey: ["accounts", period], queryFn: () => accountsApi.summary(period), enabled: Boolean(period) });

  async function download() {
    setBusy(true);
    try {
      const blob = await accountsApi.report(period);
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `virundhu-accounts-${period}.xlsx`; a.click(); URL.revokeObjectURL(a.href);
      toast.success("Excel downloaded");
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }

  const tile = (label: string, value: string, note?: string) => (
    <div className="rounded-[20px] border-2 border-line bg-white p-5">
      <p className="text-sm text-ink-soft">{label}</p>
      <p className="tabular mt-1 font-display text-2xl font-bold">{value}</p>
      {note ? <p className="text-sm text-ink-soft">{note}</p> : null}
    </div>
  );

  return (
    <div className="space-y-5">
      <p className="max-w-3xl text-ink-soft">
        Books for your auditor and GST filing. Pick a month, a quarter or a financial year (April to March) and download
        one Excel file: summary, every invoice, refunds, GST split, B2B list for GSTR-1, month by month, invoice number
        check and the audit trail. Test payments are always left out.
      </p>
      <section className="flex flex-wrap items-end gap-3 rounded-[20px] border-2 border-line bg-white p-5">
        <div role="radiogroup" aria-label="Period type" className="inline-flex rounded-full bg-jasmine-2 p-1">
          {([["month", "Month"], ["quarter", "Quarter"], ["fy", "Financial year"]] as [Kind, string][]).map(([k, l]) => (
            <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => setKind(k)}
              className={cn("cursor-pointer rounded-full px-4 py-1.5 text-sm font-semibold", kind === k ? "bg-night text-jasmine" : "text-ink-soft")}>{l}</button>
          ))}
        </div>
        <label className="text-sm font-semibold">Period
          <select value={period} onChange={(e) => setPicked({ ...picked, [kind]: e.target.value })}
            className="mt-1 block h-10 min-w-[260px] rounded-[10px] border-2 border-line bg-white px-2 font-normal">
            {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
        <Button onClick={download} disabled={busy || !period}>{busy ? <Spinner /> : <Download className="h-4 w-4" />} Download Excel</Button>
      </section>

      {!s ? <Skeleton className="h-[320px]" /> : (<>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-display text-xl font-bold">{s.label}</h2>
          <Chip tone="plain">Seller: {s.seller}{s.seller_gstin ? `, GSTIN ${s.seller_gstin}` : ""}</Chip>
          {!s.seller_gstin ? <Chip tone="turmeric">Add PARENT_GSTIN on the server so it prints on reports</Chip> : null}
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {tile("Gross received", inr(s.gross), `${s.invoices} invoice${s.invoices === 1 ? "" : "s"}`)}
          {tile("Refunded", inr(s.refunded), `${s.refunds} refund${s.refunds === 1 ? "" : "s"}`)}
          {tile("Net", inr(s.net), `${s.b2b_invoices} B2B · ${s.b2c_invoices} B2C`)}
          {tile("Test payments left out", String(s.test_payments_left_out), "Never counted as income")}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="rounded-[20px] border-2 border-line bg-white p-5">
            <h3 className="font-display text-lg font-bold">By channel</h3>
            {Object.keys(s.by_channel).length === 0 ? <p className="mt-2 text-sm text-ink-soft">No live payments in this period.</p> : (
              <ul className="mt-2 divide-y divide-line">
                {Object.entries(s.by_channel).map(([k, v]) => <li key={k} className="flex justify-between py-2 text-sm"><span>{k}</span><b className="tabular">{inr(v)}</b></li>)}
              </ul>
            )}
            <p className="mt-2 text-xs text-ink-soft">Online payments are sold by Dodo Payments as merchant of record: Dodo issues the tax invoice for those. Match them with Dodo's payout report.</p>
          </section>
          <section className="rounded-[20px] border-2 border-line bg-white p-5">
            <h3 className="font-display text-lg font-bold">GST on direct sales (bank transfer)</h3>
            <dl className="mt-2 grid grid-cols-2 gap-y-1.5 text-sm">
              <dt>Taxable value</dt><dd className="tabular text-right font-semibold">{inr(s.direct_taxable)}</dd>
              <dt>CGST</dt><dd className="tabular text-right">{inr(s.direct_cgst)}</dd>
              <dt>SGST</dt><dd className="tabular text-right">{inr(s.direct_sgst)}</dd>
              <dt>IGST</dt><dd className="tabular text-right">{inr(s.direct_igst)}</dd>
            </dl>
            <p className="mt-2 text-xs text-ink-soft">Prices include {s.gst_rate}% GST. Same-state customers: CGST + SGST; other states: IGST (by the customer's GSTIN).</p>
          </section>
        </div>
        <section className="flex items-start gap-3 rounded-[20px] bg-night p-5 text-jasmine">
          <FileSpreadsheet className="mt-0.5 h-5 w-5 shrink-0 text-turmeric" />
          <p className="text-sm">The Excel has 8 sheets: <b>Summary</b> with notes for the auditor, <b>Sales register</b> (every invoice with customer GSTIN and GST split), <b>Refunds</b>, <b>GST summary</b> by state, <b>B2B invoices</b> for GSTR-1, <b>Month by month</b>, <b>Invoice number check</b> and the <b>Audit trail</b> of payments, refunds and account changes.</p>
        </section>
      </>)}
    </div>
  );
}
