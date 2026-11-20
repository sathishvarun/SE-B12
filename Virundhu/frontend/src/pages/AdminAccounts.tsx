import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Download, FileSpreadsheet, Landmark, Mail, RefreshCw, Undo2, X } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Chip, Skeleton, Spinner } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import { accountsApi, adminBankApi, adminBooksApi, errorMessage, saveBlob, type AdminRequestRow, type BankPaymentRow } from "@/services/api";

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
        <BooksTools period={period} />
        <section className="flex items-start gap-3 rounded-[20px] bg-night p-5 text-jasmine">
          <FileSpreadsheet className="mt-0.5 h-5 w-5 shrink-0 text-turmeric" />
          <p className="text-sm">The Excel has 9 sheets: <b>Summary</b> with notes for the auditor, <b>Sales register</b> (every invoice with customer GSTIN and GST split), <b>Refunds</b> with credit note numbers, <b>GST summary</b> by state, <b>B2B invoices</b> for GSTR-1, <b>Month by month</b>, <b>Dodo payouts</b> with fees, <b>Invoice number check</b> and the <b>Audit trail</b> of payments, refunds and account changes.</p>
        </section>
      </>)}
    </div>
  );
}

async function grab(get: () => Promise<Blob>, name: string) {
  try { saveBlob(await get(), name); } catch (err) { toast.error(errorMessage(err)); }
}

function BooksTools({ period }: { period: string }) {
  const qc = useQueryClient();
  const st = useQuery({ queryKey: ["books-settings"], queryFn: adminBooksApi.settings });
  const reqs = useQuery({ queryKey: ["books-requests"], queryFn: adminBooksApi.requests });
  const bank = useQuery({ queryKey: ["books-bank"], queryFn: adminBooksApi.bankPayments });
  const [busy, setBusy] = useState<string | null>(null);
  const [paying, setPaying] = useState<AdminRequestRow | null>(null);
  const [refunding, setRefunding] = useState<BankPaymentRow | null>(null);
  const refresh = () => { for (const k of ["books-settings", "books-requests", "books-bank", "accounts"]) void qc.invalidateQueries({ queryKey: [k] }); };
  async function run(key: string, fn: () => Promise<{ message: string }>) {
    setBusy(key);
    try { toast.success((await fn()).message); refresh(); } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(null); }
  }
  const s = st.data;
  const open = (reqs.data ?? []).filter((r) => r.status === "open");
  const ok = (good: boolean, yes: string, no: string) => (
    <li className="flex items-start gap-2">{good ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-leaf" /> : <X className="mt-0.5 h-4 w-4 shrink-0 text-chilli" />}<span>{good ? yes : no}</span></li>
  );
  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-[20px] border-2 border-line bg-white p-5">
          <h3 className="font-display text-lg font-bold">Books set-up</h3>
          {!s ? <Skeleton className="mt-3 h-24" /> : (
            <ul className="mt-2 space-y-1.5 text-sm">
              {ok(Boolean(s.seller_gstin), `Seller GSTIN ${s.seller_gstin}`, "Seller GSTIN missing: add PARENT_GSTIN on the server")}
              {ok(Boolean(s.sac), `SAC code ${s.sac}`, "SAC code missing: add GST_SAC (ask your accountant)")}
              {ok(s.bank_ready, `Bank details on proforma invoices (account ending ${s.bank_last4})`, "Bank details missing: add BANK_ACCOUNT_NAME, BANK_ACCOUNT_NUMBER, BANK_IFSC")}
              {ok(s.payouts > 0, `${s.payouts} Dodo payout${s.payouts === 1 ? "" : "s"} imported`, "No Dodo payouts imported yet")}
              <li className="flex items-start gap-2"><Mail className="mt-0.5 h-4 w-4 shrink-0" /><span>On the 1st of every month, last month's Excel goes to <b>{s.report_recipients.join(", ")}</b></span></li>
            </ul>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => run("sync", adminBooksApi.dodoSync)} disabled={busy !== null}>{busy === "sync" ? <Spinner /> : <RefreshCw className="h-4 w-4" />} Sync Dodo fees and payouts</Button>
            <Button size="sm" variant="outline" onClick={() => run("mail", () => adminBooksApi.emailNow(/^\d{4}-\d{2}$/.test(period) ? period : undefined))} disabled={busy !== null}>{busy === "mail" ? <Spinner /> : <Mail className="h-4 w-4" />} Email {/^\d{4}-\d{2}$/.test(period) ? "this month's" : "last month's"} Excel now</Button>
          </div>
        </section>
        <section className="rounded-[20px] border-2 border-line bg-white p-5">
          <h3 className="font-display text-lg font-bold">Waiting for bank transfer {open.length ? <Chip tone="turmeric" className="ml-1">{open.length}</Chip> : null}</h3>
          {!reqs.data ? <Skeleton className="mt-3 h-24" /> : open.length === 0 ? <p className="mt-2 text-sm text-ink-soft">No proforma invoices waiting. Big chains get one when they choose bank transfer.</p> : (
            <ul className="mt-2 divide-y divide-line text-sm">
              {open.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span><b className="font-mono">{r.number}</b> · {r.restaurant} · {r.outlets} × {r.months} mo · <b>{inr(r.amount)}</b></span>
                  <span className="flex gap-2">
                    <button type="button" onClick={() => grab(() => adminBooksApi.requestPdf(r.id), `${r.number}.pdf`)} className="cursor-pointer font-semibold underline">PDF</button>
                    <button type="button" onClick={() => setPaying(r)} className="cursor-pointer font-semibold text-leaf underline">Money arrived</button>
                    <button type="button" onClick={() => run(`c${r.id}`, async () => { await adminBooksApi.cancelRequest(r.id); return { message: `${r.number} cancelled` }; })} className="cursor-pointer text-ink-soft underline">Cancel</button>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
      {paying ? <RecordArrival r={paying} onDone={() => { setPaying(null); refresh(); }} /> : null}

      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <h3 className="font-display text-lg font-bold">Bank transfer payments</h3>
        <p className="text-sm text-ink-soft">Tax invoice PDF for each, and refunds: a partial or full refund issues a numbered credit note, emails it to the owner and goes into the Excel.</p>
        {!bank.data ? <Skeleton className="mt-3 h-20" /> : bank.data.length === 0 ? <p className="mt-2 text-sm text-ink-soft">No bank transfer payments yet.</p> : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead><tr className="text-left text-ink-soft"><th className="py-2 font-semibold">Invoice</th><th className="font-semibold">Restaurant</th><th className="font-semibold">UTR</th><th className="text-right font-semibold">Amount</th><th className="text-right font-semibold">Refunded</th><th /></tr></thead>
              <tbody>
                {bank.data.map((b) => (
                  <tr key={b.id} className="border-t border-line">
                    <td className="py-2 font-mono">{b.invoice_no}</td><td>{b.restaurant}</td><td className="font-mono text-ink-soft">{b.reference}</td>
                    <td className="tabular text-right font-semibold">{inr(b.amount)}</td><td className="tabular text-right">{b.refunded ? inr(b.refunded) : "-"}</td>
                    <td className="pl-3 text-right"><span className="flex justify-end gap-3">
                      <button type="button" onClick={() => grab(() => adminBooksApi.paymentPdf(b.id), `${b.invoice_no}.pdf`)} className="cursor-pointer font-semibold underline">Invoice PDF</button>
                      {b.refunded < b.amount ? <button type="button" onClick={() => setRefunding(b)} className="cursor-pointer font-semibold text-chilli underline">Refund</button> : null}
                    </span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {refunding ? <RefundForm p={refunding} onDone={() => { setRefunding(null); refresh(); }} /> : null}
      </section>
    </div>
  );
}

function RecordArrival({ r, onDone }: { r: AdminRequestRow; onDone: () => void }) {
  const [amount, setAmount] = useState(String(Math.round(r.amount)));
  const [utr, setUtr] = useState("");
  const [busy, setBusy] = useState(false);
  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true);
    try { toast.success((await adminBankApi.record(r.organization_id, { outlets: r.outlets, months: r.months, amount_inr: Number(amount), reference: utr.trim() })).message); onDone(); }
    catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }
  return (
    <form onSubmit={save} className="flex flex-wrap items-end gap-3 rounded-[20px] border-2 border-night bg-white p-5">
      <p className="w-full font-semibold"><Landmark className="mr-1 inline h-4 w-4" />Money arrived for {r.number} ({r.restaurant}, {r.outlets} outlets × {r.months} months)</p>
      <label className="text-sm font-semibold">Amount received (₹)<input inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value.replace(/\D/g, ""))} className="mt-1 block h-10 w-40 rounded-[10px] border-2 border-line px-2" required /></label>
      <label className="text-sm font-semibold">UTR / bank reference<input value={utr} onChange={(e) => setUtr(e.target.value)} minLength={4} maxLength={40} className="mt-1 block h-10 w-56 rounded-[10px] border-2 border-line px-2" required /></label>
      <Button type="submit" disabled={busy}>{busy ? <Spinner /> : null} Switch plan on and send tax invoice</Button>
      <button type="button" onClick={onDone} className="h-10 cursor-pointer px-2 text-sm text-ink-soft">Cancel</button>
    </form>
  );
}

function RefundForm({ p, onDone }: { p: BankPaymentRow; onDone: () => void }) {
  const left = p.amount - p.refunded;
  const [amount, setAmount] = useState("");
  const [utr, setUtr] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true);
    try {
      const r = await adminBooksApi.refund(p.id, { amount_inr: Number(amount), reference: utr.trim(), reason: reason.trim() || undefined });
      toast.success(r.message); await grab(() => adminBooksApi.creditNotePdf(r.refund_id), `${r.credit_note}.pdf`); onDone();
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }
  return (
    <form onSubmit={save} className="mt-4 flex flex-wrap items-end gap-3 rounded-[16px] border-2 border-chilli p-4">
      <p className="w-full font-semibold"><Undo2 className="mr-1 inline h-4 w-4" />Refund on {p.invoice_no} ({p.restaurant}). Up to {inr(left)} left. Only after the money has left your bank.</p>
      <label className="text-sm font-semibold">Amount refunded (₹)<input inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value.replace(/\D/g, ""))} className="mt-1 block h-10 w-40 rounded-[10px] border-2 border-line px-2" required /></label>
      <label className="text-sm font-semibold">Refund UTR<input value={utr} onChange={(e) => setUtr(e.target.value)} minLength={4} maxLength={40} className="mt-1 block h-10 w-48 rounded-[10px] border-2 border-line px-2" required /></label>
      <label className="text-sm font-semibold">Reason<input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={300} placeholder="e.g. 2 outlets closed" className="mt-1 block h-10 w-60 rounded-[10px] border-2 border-line px-2" /></label>
      <Button type="submit" disabled={busy}>{busy ? <Spinner /> : null} Record refund and issue credit note</Button>
      <button type="button" onClick={onDone} className="h-10 cursor-pointer px-2 text-sm text-ink-soft">Cancel</button>
    </form>
  );
}
