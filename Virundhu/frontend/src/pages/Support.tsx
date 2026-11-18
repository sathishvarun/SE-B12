import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/misc";
import { api, billingApi, errorMessage } from "@/services/api";
import { cn } from "@/lib/utils";

export interface TicketMsg { from_admin: boolean; author: string | null; body: string; at: string }
export interface Ticket { id: number; number: string; category: string; category_label: string; subject: string; status: string; status_label: string; restaurant: string | null; user_email: string | null; created_at: string; updated_at: string; messages?: TicketMsg[]; payment?: { invoice_no: string | null; amount: number; status: string; payment_id: string } | null }

const CATS: [string, string][] = [["payment", "Payment or billing"], ["bug", "Something isn't working"], ["account", "Account or sign-in"], ["feature", "Suggestion"], ["other", "Other"]];
const when = (d: string) => new Date(d).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });

export function StatusPill({ s, label }: { s: string; label: string }) {
  return <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-bold", s === "resolved" ? "bg-leaf-soft text-[#16784a]" : s === "in_progress" ? "bg-turmeric/30" : "bg-chilli-soft text-[#b32f12]")}>{label}</span>;
}

export function Thread({ t, onSend, busy, admin, onDraft }: { t: Ticket; onSend: (msg: string, status?: string) => void; busy: boolean; admin?: boolean; onDraft?: () => Promise<string> }) {
  const [msg, setMsg] = useState("");
  const [drafting, setDrafting] = useState(false);
  const [status, setStatus] = useState("");
  return (
    <div className="rounded-[20px] border-2 border-line bg-white p-5">
      <div className="flex flex-wrap items-center gap-2"><span className="font-mono text-sm">{t.number}</span><StatusPill s={t.status} label={t.status_label} /><span className="text-sm text-ink-soft">{t.category_label}{admin && t.restaurant ? ` · ${t.restaurant} (${t.user_email})` : ""}</span></div>
      <h2 className="mt-1 text-xl font-bold">{t.subject}</h2>
      {t.payment ? <p className="mt-1 text-sm">Payment: {t.payment.invoice_no ?? t.payment.payment_id}, ₹{t.payment.amount.toLocaleString("en-IN")}, {t.payment.status}</p> : null}
      <ul className="mt-4 space-y-3">
        {t.messages?.map((m, i) => (
          <li key={i} className={cn("rounded-[14px] p-3", m.from_admin ? "ml-6 bg-night text-jasmine" : "mr-6 bg-jasmine")}>
            <p className="text-xs opacity-75">{m.author} · {when(m.at)}</p><p className="mt-1 whitespace-pre-wrap">{m.body}</p>
          </li>
        ))}
      </ul>
      <form className="mt-4 space-y-2" onSubmit={(e) => { e.preventDefault(); if (msg.trim()) { onSend(msg, status || undefined); setMsg(""); setStatus(""); } }}>
        <label className="block text-sm font-semibold" htmlFor={`reply-${t.id}`}>{admin ? "Reply to the customer" : "Add a message"}</label>
        <textarea id={`reply-${t.id}`} value={msg} onChange={(e) => setMsg(e.target.value)} rows={3} maxLength={5000} className="w-full rounded-[12px] border-2 border-line p-3" />
        <div className="flex flex-wrap gap-2">
          {admin ? (
            <select aria-label="Set status" value={status} onChange={(e) => setStatus(e.target.value)} className="h-11 rounded-[12px] border-2 border-line px-3">
              <option value="">Keep status</option><option value="in_progress">Being worked on</option><option value="resolved">Resolved</option><option value="open">Open</option>
            </select>
          ) : null}
          {onDraft ? <button type="button" disabled={drafting} onClick={async () => { setDrafting(true); try { setMsg(await onDraft()); } finally { setDrafting(false); } }} className="h-11 rounded-[12px] border-2 border-night px-4 font-semibold cursor-pointer disabled:opacity-50">{drafting ? "Writing..." : "Draft reply with AI"}</button> : null}
          <button disabled={busy || !msg.trim()} className="h-11 rounded-[12px] bg-night px-4 font-semibold text-jasmine cursor-pointer disabled:opacity-50">{busy ? "Sending..." : "Send"}</button>
        </div>
      </form>
    </div>
  );
}

/** Owners raise and follow their requests here. Every message is emailed and logged. */
export default function Support() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["tickets"], queryFn: () => api.get<Ticket[]>("/api/v1/support/tickets").then((r) => r.data) });
  const billing = useQuery({ queryKey: ["billing-status"], queryFn: billingApi.status });
  const [open, setOpen] = useState<number | null>(null);
  const thread = useQuery({ queryKey: ["ticket", open], queryFn: () => api.get<Ticket>(`/api/v1/support/tickets/${open}`).then((r) => r.data), enabled: open !== null });
  const [form, setForm] = useState({ category: "bug", subject: "", message: "", payment_id: "" });
  const [busy, setBusy] = useState(false);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const t = await api.post<Ticket>("/api/v1/support/tickets", { ...form, payment_id: form.payment_id ? Number(form.payment_id) : null }).then((r) => r.data);
      toast.success(`Request ${t.number} sent. We reply within 24 hours.`);
      setForm({ category: "bug", subject: "", message: "", payment_id: "" });
      await qc.invalidateQueries({ queryKey: ["tickets"] });
      setOpen(t.id);
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }
  async function send(msg: string) {
    setBusy(true);
    try { await api.post(`/api/v1/support/tickets/${open}/messages`, { message: msg }); await qc.invalidateQueries(); }
    catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-[2.3rem] font-bold">Help and support</h1>
      <p className="mt-1 max-w-2xl text-ink-soft">Payment problem, something not working, or an idea? Send it here. You get a request number by email, we reply within 24 hours, and the whole conversation stays on this page.</p>
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_1.3fr]">
        <div className="space-y-6">
          <form onSubmit={create} className="space-y-3 rounded-[20px] border-2 border-line bg-white p-5">
            <h2 className="text-lg font-bold">New request</h2>
            <label className="block text-sm font-semibold">What is it about?
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="mt-1 block h-11 w-full rounded-[12px] border-2 border-line px-3 font-normal">
                {CATS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select></label>
            {form.category === "payment" && billing.data?.payments.length ? (
              <label className="block text-sm font-semibold">Which payment? (optional)
                <select value={form.payment_id} onChange={(e) => setForm({ ...form, payment_id: e.target.value })} className="mt-1 block h-11 w-full rounded-[12px] border-2 border-line px-3 font-normal">
                  <option value="">Not about a specific payment</option>
                  {billing.data.payments.map((p) => <option key={p.receipt_id} value={p.receipt_id}>{p.invoice_no ?? p.id}, ₹{p.amount.toLocaleString("en-IN")}</option>)}
                </select></label>
            ) : null}
            <label className="block text-sm font-semibold">Subject
              <input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} minLength={4} maxLength={160} required className="mt-1 block h-11 w-full rounded-[12px] border-2 border-line px-3 font-normal" /></label>
            <label className="block text-sm font-semibold">Tell us what happened
              <textarea value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} minLength={5} maxLength={5000} required rows={4} className="mt-1 block w-full rounded-[12px] border-2 border-line p-3 font-normal" /></label>
            <button disabled={busy} className="h-11 rounded-[12px] bg-turmeric px-4 font-semibold text-night cursor-pointer disabled:opacity-60">Send request</button>
          </form>
          <section>
            <h2 className="text-lg font-bold">Your requests</h2>
            {list.isLoading ? <Skeleton className="mt-2 h-24" /> : list.data?.length ? (
              <ul className="mt-2 space-y-2">{list.data.map((t) => (
                <li key={t.id}><button onClick={() => setOpen(t.id)} className={cn("w-full rounded-[14px] border-2 p-3 text-left cursor-pointer", open === t.id ? "border-night" : "border-line bg-white")}>
                  <span className="flex items-center gap-2"><span className="font-mono text-xs">{t.number}</span><StatusPill s={t.status} label={t.status_label} /></span>
                  <span className="mt-1 block font-semibold">{t.subject}</span><span className="text-xs text-ink-soft">Updated {when(t.updated_at)}</span></button></li>
              ))}</ul>
            ) : <p className="mt-2 text-ink-soft">No requests yet.</p>}
          </section>
        </div>
        <div>{thread.data ? <Thread t={thread.data} onSend={(m) => void send(m)} busy={busy} /> : <p className="rounded-[20px] bg-jasmine p-6 text-ink-soft">Choose a request to see the conversation.</p>}</div>
      </div>
    </div>
  );
}
