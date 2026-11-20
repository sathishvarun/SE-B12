import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, CheckCircle2, CircleAlert, Database, Eye, IndianRupee, Inbox, KeyRound, LayoutDashboard, LifeBuoy, LogIn, Mail, MailOpen, Workflow, MessageSquareText, ExternalLink, Quote, ScrollText, ShieldAlert, Users, X, HeartHandshake, CalendarClock, RefreshCw, Gauge, Coins, Landmark } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { SecretInput } from "@/components/ui/input";
import { StatusPill, Thread, type Ticket } from "@/pages/Support";
import { TokensByRestaurantPanel, TokensTotalPanel } from "@/pages/AdminTokens";
import { quoteFrom } from "@/components/site/PriceCalculator";
import { Chip, Skeleton } from "@/components/ui/misc";
import { useAuth } from "@/context/AuthContext";
import { shortDate } from "@/lib/copy";
import { useCountUp } from "@/lib/useCountUp";
import { cn } from "@/lib/utils";
import { accountApi, adminApi, adminBankApi, billingApi, adminAgentsApi, adminAutopilotApi, adminFeedbackApi, adminMoneyApi, api, errorMessage, viewAs, type MoneyWindow } from "@/services/api";

const PLATFORM_COLORS = { google: "#6cb8ff", zomato: "#ff5b3a", swiggy: "#f6b93b", direct: "#2bb673", other: "#a9acd0", tripadvisor: "#34a77b", instagram: "#f06ba8", facebook: "#4a6cf7" } as const;
const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

function Tile({ icon: Icon, label, value, note, money, tone }: { icon: typeof Users; label: string; value: number; note?: string; money?: boolean; tone?: "dark" | "urgent" }) {
  const v = useCountUp(value);
  return (
    <div className={cn("rounded-[18px] p-5", tone === "dark" ? "bg-night text-jasmine" : tone === "urgent" ? "bg-chilli text-white" : "border-2 border-line bg-white")}>
      <p className={cn("flex items-center gap-2 text-sm font-semibold", tone ? "opacity-85" : "text-ink-soft")}><Icon className="h-4 w-4" />{label}</p>
      <p className="tabular mt-1 font-display text-[2.3rem] font-bold leading-none">{money ? inr(v) : Math.round(v).toLocaleString("en-IN")}</p>
      {note ? <p className={cn("mt-1.5 text-sm", tone ? "opacity-80" : "text-ink-soft")}>{note}</p> : null}
    </div>
  );
}

export default function Admin() {
  return <AdminGate />;
}

function AdminGate() {
  const { user } = useAuth();
  if (!user?.is_superadmin) return <p className="rounded-[14px] bg-jasmine-2 p-5 font-medium">This page is only for the Virundhu owner.</p>;
  return <AdminPanel />;
}

/** The admin has no restaurant settings page, so the password change lives here. */
function TestimonialsAdmin() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["admin-testimonials"], queryFn: adminApi.testimonials });
  const empty = { name: "", role: "", quote: "", published: false, sort_order: 0 };
  const [f, setF] = useState(empty);
  const refresh = () => { void qc.invalidateQueries({ queryKey: ["admin-testimonials"] }); void qc.invalidateQueries({ queryKey: ["testimonials"] }); };
  async function add() {
    try { await adminApi.addTestimonial({ ...f, role: f.role || null }); setF(empty); refresh(); toast.success("Saved. Publish it to show it on the home page."); }
    catch (err) { toast.error(errorMessage(err)); }
  }
  return (
    <div className="mt-4 grid gap-5 lg:grid-cols-[1fr_1.2fr]">
      <div className="rounded-[20px] border-2 border-line bg-white p-5">
        <h2 className="text-xl">Add a customer's words</h2>
        <p className="mt-1 text-sm text-ink-soft">Only real customers, in their own words, with their permission. Nothing shows on the website until you publish it.</p>
        <div className="mt-4 space-y-3">
          <input aria-label="Name" placeholder="Name (e.g. Kumar)" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className="h-11 w-full rounded-[12px] border-2 border-line px-3" />
          <input aria-label="Role" placeholder="Owner, Restaurant name, City" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })} className="h-11 w-full rounded-[12px] border-2 border-line px-3" />
          <textarea aria-label="Quote" rows={4} placeholder="What they said" value={f.quote} onChange={(e) => setF({ ...f, quote: e.target.value })} className="w-full rounded-[12px] border-2 border-line p-3" />
          <button type="button" onClick={() => void add()} disabled={f.name.length < 2 || f.quote.length < 10} className="rounded-[12px] bg-turmeric px-4 py-2.5 font-semibold disabled:opacity-50 cursor-pointer">Save</button>
        </div>
      </div>
      <ul className="space-y-3">
        {!data?.length ? <li className="rounded-[20px] border-2 border-dashed border-ink/20 p-6 text-center text-ink-soft">No testimonials yet. Ask your first happy customers.</li> : null}
        {data?.map((t) => (
          <li key={t.id} className="rounded-[18px] border-2 border-line bg-white p-4">
            <p>“{t.quote}”</p>
            <p className="mt-2 text-sm"><b>{t.name}</b>{t.role ? `, ${t.role}` : ""}</p>
            <div className="mt-3 flex gap-2 text-sm">
              <button type="button" className={cn("rounded-[10px] px-3 py-1.5 font-semibold cursor-pointer", t.published ? "bg-leaf-soft text-leaf" : "bg-jasmine-2")}
                onClick={() => void adminApi.saveTestimonial(t.id, { ...t, published: !t.published }).then(refresh)}>{t.published ? "Published: hide" : "Publish"}</button>
              <button type="button" className="rounded-[10px] px-3 py-1.5 font-semibold text-chilli cursor-pointer"
                onClick={() => { if (window.confirm("Delete this testimonial?")) void adminApi.deleteTestimonial(t.id).then(refresh); }}>Delete</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function LaunchChecklist() {
  const { data } = useQuery({ queryKey: ["launch-check"], queryFn: adminApi.launchCheck });
  const [open, setOpen] = useState(false);
  const [sending, setSending] = useState(false);
  if (!data) return null;
  const missing = data.filter((i) => !i.ok && i.required);
  async function test() {
    setSending(true);
    try {
      const r = await adminApi.testEmail();
      if (r.sent) toast.success("Test email sent. Check your inbox (and spam)."); else toast.error("Email sending isn't set up yet. The email was only written to the server log.");
    } catch (err) { toast.error(errorMessage(err)); } finally { setSending(false); }
  }
  return (
    <section className={cn("mt-5 rounded-[20px] border-2 p-5", missing.length ? "border-turmeric bg-turmeric/10" : "border-leaf/40 bg-leaf/5")}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="font-display text-xl font-bold">
          {missing.length ? `Before launch: ${missing.length} thing${missing.length === 1 ? "" : "s"} to set up` : "Ready for real restaurants"}
        </p>
        <div className="flex gap-2">
          <button type="button" onClick={() => void test()} disabled={sending} className="inline-flex items-center gap-1.5 rounded-[10px] bg-white px-3 py-1.5 text-sm font-semibold cursor-pointer"><Mail className="h-4 w-4" /> {sending ? "Sending..." : "Send test email"}</button>
          <button type="button" onClick={() => setOpen((o) => !o)} className="rounded-[10px] bg-night px-3 py-1.5 text-sm font-semibold text-jasmine cursor-pointer">{open ? "Hide" : "Show"} checklist</button>
        </div>
      </div>
      {open ? (
        <ul className="mt-4 space-y-2">
          {data.map((i) => (
            <li key={i.key} className="flex gap-3 rounded-[12px] bg-white px-4 py-3">
              {i.ok ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-leaf" /> : <CircleAlert className={cn("mt-0.5 h-5 w-5 shrink-0", i.required ? "text-chilli" : "text-ink-soft")} />}
              <div>
                <p className="font-semibold">{i.label}{!i.required ? <span className="ml-2 text-sm font-normal text-ink-soft">(optional)</span> : null}</p>
                {!i.ok ? <p className="text-sm text-ink-soft">{i.fix}</p> : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

const dayMonth = (d: string) => new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

function Money({ label, value, note, strong }: { label: string; value: number; note: string; strong?: boolean }) {
  return (
    <div className={cn("rounded-[16px] p-4", strong ? "bg-night text-jasmine" : "bg-jasmine")}>
      <p className={cn("text-sm font-semibold", strong ? "text-mist" : "text-ink-soft")}>{label}</p>
      <p className="mt-1 font-display text-[1.7rem] font-bold tabular">{inr(value)}</p>
      <p className={cn("mt-0.5 text-xs", strong ? "text-mist" : "text-ink-soft")}>{note}</p>
    </div>
  );
}

function PlanMixAndReports() {
  const mix = useQuery({ queryKey: ["admin-plan-mix"], queryFn: adminApi.planMix });
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [busy, setBusy] = useState(false);
  async function download() {
    setBusy(true);
    try {
      const blob = await adminApi.monthlyReport(month);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `virundhu-report-${month}.xlsx`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); }
  }
  return (
    <div className="mt-5 grid gap-5 xl:grid-cols-2">
      <div>
        <h3 className="font-bold">Paying restaurants by plan length</h3>
        <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-6">
          {(["1", "3", "6", "9", "12"] as const).map((k) => (
            <div key={k} className="rounded-[14px] bg-jasmine p-3 text-center"><p className="font-display text-2xl font-bold tabular">{mix.data?.by_months[k] ?? "-"}</p><p className="text-xs text-ink-soft">{k} month{k === "1" ? "" : "s"}</p></div>
          ))}
          <div className="rounded-[14px] bg-turmeric/25 p-3 text-center"><p className="font-display text-2xl font-bold tabular">{mix.data?.on_trial ?? "-"}</p><p className="text-xs text-ink-soft">on trial</p></div>
        </div>
      </div>
      <div>
        <h3 className="font-bold">Monthly audit report (Excel)</h3>
        <p className="text-xs text-ink-soft">Revenue, every receipt with billing details and GSTIN, new vs renewals, the 1/3/6/9/12-month mix, idle accounts, renewals due next month and new sign-ups. Emailed to you automatically on the 1st of every month.</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} aria-label="Report month" className="h-11 rounded-[10px] border-2 border-line px-3" />
          <button onClick={download} disabled={busy || !month} className="h-11 rounded-[12px] bg-night px-4 font-semibold text-jasmine cursor-pointer disabled:opacity-60">{busy ? "Preparing..." : "Download report"}</button>
        </div>
      </div>
    </div>
  );
}

function RevenueBoard() {
  const { data: r, isLoading } = useQuery({ queryKey: ["admin-revenue"], queryFn: adminApi.revenue });
  if (isLoading || !r) return <Skeleton className="mt-5 h-[420px]" />;
  const chart = r.months.map((m) => ({ label: m.label.replace(" 20", " '"), Collected: Math.round(m.collected), "Renewals due": Math.round(m.expected) }));
  return (
    <section className="mt-5 rounded-[20px] border-2 border-line bg-white p-5 sm:p-6" aria-labelledby="rev-title">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 id="rev-title" className="text-xl font-bold">Revenue</h2>
        <p className="text-sm text-ink-soft">Money actually received through Dodo Payments, in rupees, tax included. Test-mode payments count too until you go live.</p>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Money strong label="Total received, all time" value={r.all_time} note={`${r.paying_customers} restaurant${r.paying_customers === 1 ? "" : "s"} paying now`} />
        <Money label="This month" value={r.this_month} note={`Last month ${inr(r.last_month)}. This year ${inr(r.this_year)}`} />
        <Money label="Active plans are worth" value={r.monthly_recurring} note="per month, spread over each plan's length" />
        <Money label="Renewals due, next 30 days" value={r.expected_next_30} note={`${inr(r.expected_next_90)} in the next 90 days, if everyone renews`} />
      </div>
      <div className="mt-5 h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ece4d4" />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} interval={0} angle={-35} textAnchor="end" height={50} />
            <YAxis tick={{ fontSize: 12 }} width={64} tickFormatter={(v: number) => (v >= 1000 ? `₹${Math.round(v / 1000)}k` : `₹${v}`)} />
            <Tooltip formatter={(v) => inr(Number(v))} />
            <Bar dataKey="Collected" fill="#0c3b2e" radius={[6, 6, 0, 0]} />
            <Bar dataKey="Renewals due" fill="#f6b93b" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-xs text-ink-soft">Dark bars: money received each month (last 12 months). Yellow bars: plans that end that month and would bring this in if they renew at today's price.</p>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <div>
          <h3 className="font-bold">Coming up: renewals in the next 90 days</h3>
          {r.upcoming.length ? (
            <div className="mt-2 overflow-x-auto rounded-[14px] border-2 border-line">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="bg-jasmine text-ink-soft"><tr><th className="px-3 py-2">Restaurant</th><th>Plan ends</th><th>Outlets</th><th>Plan</th><th className="px-3 text-right">If renewed</th></tr></thead>
                <tbody>{r.upcoming.map((u) => (
                  <tr key={u.org_id} className="border-t-2 border-jasmine-2"><td className="px-3 py-2"><p className="font-semibold">{u.restaurant}</p><p className="text-xs text-ink-soft">{u.owner_email}</p></td>
                    <td>{dayMonth(u.ends_on)}</td><td className="tabular">{u.outlets}</td><td>{u.months} mo</td><td className="px-3 text-right font-semibold tabular">{inr(u.amount)}</td></tr>
                ))}</tbody>
              </table>
            </div>
          ) : <p className="mt-2 text-ink-soft">No paid plans end in the next 90 days.</p>}
        </div>
        <div>
          <h3 className="font-bold">Trials ending in the next 7 days</h3>
          <p className="text-xs text-ink-soft">What each would pay for 1 month at its outlet count. Total possible: {inr(r.possible_from_trials)}.</p>
          {r.trials_ending.length ? (
            <div className="mt-2 overflow-x-auto rounded-[14px] border-2 border-line">
              <table className="w-full min-w-[480px] text-left text-sm">
                <thead className="bg-jasmine text-ink-soft"><tr><th className="px-3 py-2">Restaurant</th><th>Trial ends</th><th>Outlets</th><th className="px-3 text-right">1 month</th></tr></thead>
                <tbody>{r.trials_ending.map((u) => (
                  <tr key={u.org_id} className="border-t-2 border-jasmine-2"><td className="px-3 py-2"><p className="font-semibold">{u.restaurant}</p><p className="text-xs text-ink-soft">{u.owner_email}</p></td>
                    <td>{dayMonth(u.ends_on)}</td><td className="tabular">{u.outlets}</td><td className="px-3 text-right font-semibold tabular">{inr(u.amount)}</td></tr>
                ))}</tbody>
              </table>
            </div>
          ) : <p className="mt-2 text-ink-soft">No trials end this week.</p>}
        </div>
      </div>

      <PlanMixAndReports />

      <h3 className="mt-5 font-bold">Latest payments</h3>
      {r.recent.length ? (
        <div className="mt-2 overflow-x-auto rounded-[14px] border-2 border-line">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="bg-jasmine text-ink-soft"><tr><th className="px-3 py-2">Date</th><th>Receipt</th><th>Restaurant / billed to</th><th>Outlets</th><th>Months</th><th>Covers until</th><th className="px-3 text-right">Amount</th></tr></thead>
            <tbody>{r.recent.map((p, i) => (
              <tr key={i} className="border-t-2 border-jasmine-2"><td className="px-3 py-2">{dayMonth(p.paid_at)}</td>
                <td><Link to={`/app/receipt/${p.id}`} className="font-mono underline">{p.invoice_no ?? "view"}</Link></td>
                <td><p className="font-semibold">{p.restaurant}</p>{p.bill_name && p.bill_name !== p.restaurant ? <p className="text-xs text-ink-soft">{p.bill_name}</p> : null}{p.bill_gstin ? <p className="font-mono text-xs text-ink-soft">GSTIN {p.bill_gstin}</p> : null}</td>
                <td className="tabular">{p.outlets ?? "-"}</td><td>{p.months ?? "-"}</td><td>{p.covers_until ? dayMonth(p.covers_until) : "-"}</td>
                <td className="px-3 text-right font-semibold tabular">{inr(p.amount)}</td></tr>
            ))}</tbody>
          </table>
        </div>
      ) : <p className="mt-2 text-ink-soft">No payments yet.</p>}
    </section>
  );
}

function SupportAdmin() {
  const qc = useQueryClient();
  const [status, setStatus] = useState("");
  const [open, setOpen] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const list = useQuery({ queryKey: ["admin-tickets", status], queryFn: () => api.get<Ticket[]>("/api/v1/admin/tickets", { params: status ? { status } : {} }).then((r) => r.data) });
  const thread = useQuery({ queryKey: ["admin-ticket", open], queryFn: () => api.get<Ticket>(`/api/v1/admin/tickets/${open}`).then((r) => r.data), enabled: open !== null });
  async function send(message: string, st?: string) {
    setBusy(true);
    try { await api.post(`/api/v1/admin/tickets/${open}/messages`, { message, status: st }); toast.success("Reply sent and emailed"); await qc.invalidateQueries(); }
    catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); }
  }
  return (
    <div className="mt-4 grid gap-5 lg:grid-cols-[1fr_1.4fr]">
      <section>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-display text-xl font-bold">Support tickets</h2>
          <select aria-label="Filter by status" value={status} onChange={(e) => setStatus(e.target.value)} className="h-10 rounded-[10px] border-2 border-line px-2">
            <option value="">All</option><option value="open">Open</option><option value="in_progress">Being worked on</option><option value="resolved">Resolved</option>
          </select>
        </div>
        <p className="mt-1 text-sm text-ink-soft">New tickets reach your bell and email. Every reply is emailed to the customer and kept in the Activity log.</p>
        {list.data?.length ? (
          <ul className="mt-3 space-y-2">{list.data.map((t) => (
            <li key={t.id}><button onClick={() => setOpen(t.id)} className={cn("w-full rounded-[14px] border-2 p-3 text-left cursor-pointer", open === t.id ? "border-night" : "border-line bg-white")}>
              <span className="flex flex-wrap items-center gap-2"><span className="font-mono text-xs">{t.number}</span><StatusPill s={t.status} label={t.status_label} /><span className="text-xs text-ink-soft">{t.category_label}</span></span>
              <span className="mt-1 block font-semibold">{t.subject}</span><span className="text-xs text-ink-soft">{t.restaurant} · {t.user_email}</span></button></li>
          ))}</ul>
        ) : <p className="mt-3 text-ink-soft">No tickets{status ? " with this status" : " yet"}.</p>}
      </section>
      <div>{thread.data ? <Thread t={thread.data} onSend={(m, st) => void send(m, st)} busy={busy} admin onDraft={async () => { try { return (await api.get<{ draft: string }>(`/api/v1/admin/tickets/${open}/draft`)).data.draft; } catch (e) { toast.error(errorMessage(e)); return ""; } }} /> : <p className="rounded-[20px] bg-jasmine p-6 text-ink-soft">Choose a ticket.</p>}</div>
    </div>
  );
}

function LogHistory() {
  const [days, setDays] = useState(30);
  const [busy, setBusy] = useState(false);
  async function download() {
    setBusy(true);
    try {
      const blob = await api.get<Blob>("/api/v1/admin/logs.xlsx", { params: { days }, responseType: "blob" }).then((r) => r.data);
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `virundhu-logs-last-${days}-days.xlsx`; a.click(); URL.revokeObjectURL(a.href);
    } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); }
  }
  return (
    <section className="rounded-[20px] border-2 border-line bg-white p-5">
      <h2 className="font-display text-xl font-bold">Log history</h2>
      <p className="mt-1 text-ink-soft">Every sign-in (who, which restaurant, when, IP address, device), wrong passwords and locks, payments, deletions, password changes, demo requests and support tickets. You also get a summary email every night at 9 pm. Server error logs are kept in backend/logs on the server.</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <select aria-label="Period" value={days} onChange={(e) => setDays(Number(e.target.value))} className="h-11 rounded-[10px] border-2 border-line px-3">
          <option value={1}>Last 24 hours</option><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={365}>Last year</option>
        </select>
        <button onClick={download} disabled={busy} className="h-11 rounded-[12px] bg-night px-4 font-semibold text-jasmine cursor-pointer disabled:opacity-60">{busy ? "Preparing..." : "Download log (Excel)"}</button>
      </div>
    </section>
  );
}

function DeletedAccounts() {
  const { data } = useQuery({ queryKey: ["admin-deleted"], queryFn: () => adminApi.activityOf("account_deleted") });
  return (
    <section className="rounded-[20px] border-2 border-line bg-white p-5 lg:col-span-2">
      <h2 className="font-display text-xl font-bold">Deleted accounts</h2>
      <p className="mt-1 text-ink-soft">Every restaurant deleted by its owner (or by you), newest first, with the plan, unused paid days and balance due at the time.
        Each one also arrives in your bell and by email the moment it happens. Balance due is always ₹0 because Virundhu is paid in advance.</p>
      {data?.length ? (
        <div className="mt-3 overflow-x-auto rounded-[14px] border-2 border-line">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-jasmine text-ink-soft"><tr><th className="px-3 py-2">When</th><th>Restaurant</th><th>Owner</th><th className="px-3">Details</th></tr></thead>
            <tbody>{data.map((a) => (
              <tr key={a.id} className="border-t-2 border-jasmine-2 align-top"><td className="px-3 py-2">{new Date(a.created_at).toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" })}</td>
                <td className="font-semibold">{a.restaurant ?? "-"}</td><td>{a.user_email ?? "-"}</td><td className="px-3">{a.detail ?? ""}</td></tr>
            ))}</tbody>
          </table>
        </div>
      ) : <p className="mt-3 text-ink-soft">No accounts deleted yet.</p>}
    </section>
  );
}

function DataTools() {
  const qc = useQueryClient();
  const tests = useQuery({ queryKey: ["admin-test-accounts"], queryFn: adminApi.testAccounts });
  const backup = useQuery({ queryKey: ["admin-backups"], queryFn: adminApi.backups });
  const [picked, setPicked] = useState<number[]>([]);
  const [busy, setBusy] = useState<"excel" | "delete" | null>(null);

  async function download() {
    setBusy("excel");
    try {
      const blob = await adminApi.exportExcel();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `virundhu-customers-${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(null); }
  }

  async function remove() {
    if (!picked.length) return;
    if (!window.confirm(`Delete ${picked.length} test account${picked.length > 1 ? "s" : ""} and everything in them? This can't be undone.`)) return;
    setBusy("delete");
    try {
      const r = await adminApi.deleteTestAccounts(picked);
      toast.success(`${r.deleted} test account${r.deleted === 1 ? "" : "s"} deleted`);
      setPicked([]);
      await qc.invalidateQueries();
    } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(null); }
  }

  const all = tests.data ?? [];
  return (
    <div className="mt-4 grid gap-5 lg:grid-cols-2">
      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <h2 className="font-display text-xl font-bold">Download customers (Excel)</h2>
        <p className="mt-1 text-ink-soft">One Excel file with four sheets: every restaurant (outlets, plan, trial and paid-until dates, owner name, email
          and phone), every person who can sign in, every payment, and every demo request. Guest reviews aren't included: they belong to
          each restaurant, which can download them from its own Settings.</p>
        <p className="mt-2 text-sm text-ink-soft">The file contains personal data. Keep it on your own computer, don't forward it, and delete old copies.</p>
        <button onClick={download} disabled={busy !== null} className="mt-4 h-11 rounded-[12px] bg-night px-4 font-semibold text-jasmine cursor-pointer disabled:opacity-60">
          {busy === "excel" ? "Preparing..." : "Download Excel"}
        </button>
      </section>

      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <h2 className="font-display text-xl font-bold">Backups</h2>
        {backup.data ? (
          backup.data.latest ? (
            <p className="mt-1 text-ink-soft">Newest backup: <b className="text-ink">{backup.data.latest}</b> ({backup.data.latest_size_kb} KB),{" "}
              {backup.data.hours_ago !== null && backup.data.hours_ago < 1 ? "less than an hour ago" : `${Math.round(backup.data.hours_ago ?? 0)} hours ago`}.
              {" "}{backup.data.count} kept (newest 30).</p>
          ) : <p className="mt-1 font-semibold text-chilli">No backup yet. Run  bash tools/backup/backup.sh  once, or restart with ./start.sh.</p>
        ) : <Skeleton className="mt-2 h-10" />}
        <p className="mt-2 text-sm text-ink-soft">Folder: <code className="break-all">{backup.data?.folder ?? "..."}</code></p>
        <p className="mt-2 text-sm text-ink-soft">A new backup is taken every day you start Virundhu with ./start.sh. On the live server it runs every night.
          To bring one back: <code>bash tools/backup/restore.sh backups/FILE</code></p>
        {backup.data?.hours_ago !== null && backup.data?.hours_ago !== undefined && backup.data.hours_ago > 48 ? (
          <p className="mt-2 font-semibold text-chilli">The newest backup is more than 2 days old.</p>
        ) : null}
      </section>

      <LogHistory />

      <DeletedAccounts />

      <section className="rounded-[20px] border-2 border-line bg-white p-5 lg:col-span-2">
        <h2 className="font-display text-xl font-bold">Test accounts</h2>
        <p className="mt-1 text-ink-soft">Restaurants that look like testing: emails such as test@test.com or @example.com, demo restaurants, and names
          like "test" or "dummy". Deleting removes the restaurant, its reviews and settings, and its owner's login. Real-looking restaurants
          never appear here and can't be deleted from this list.</p>
        {tests.isLoading ? <Skeleton className="mt-3 h-12" /> : all.length === 0 ? (
          <p className="mt-3 font-semibold text-leaf">No test accounts. Your data is clean.</p>
        ) : (
          <>
            <div className="mt-3 overflow-x-auto rounded-[14px] border-2 border-line">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="bg-jasmine text-ink-soft"><tr>
                  <th className="px-3 py-2"><input type="checkbox" aria-label="Select all test accounts" className="h-5 w-5 accent-turmeric"
                    checked={picked.length === all.length} onChange={(e) => setPicked(e.target.checked ? all.map((t) => t.id) : [])} /></th>
                  <th>Restaurant</th><th>Owner email</th><th>Why it looks like a test</th><th>Reviews</th><th>Payments</th>
                </tr></thead>
                <tbody>
                  {all.map((t) => (
                    <tr key={t.id} className="border-t-2 border-jasmine-2">
                      <td className="px-3 py-2"><input type="checkbox" aria-label={`Select ${t.name}`} className="h-5 w-5 accent-turmeric" checked={picked.includes(t.id)}
                        onChange={(e) => setPicked((p) => e.target.checked ? [...p, t.id] : p.filter((x) => x !== t.id))} /></td>
                      <td className="font-semibold">{t.name}</td><td>{t.owner_email ?? "-"}</td><td>{t.reason}</td>
                      <td className="tabular">{t.reviews}</td><td className="tabular">{t.payments}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button onClick={remove} disabled={!picked.length || busy !== null}
              className="mt-3 h-11 rounded-[12px] bg-chilli px-4 font-semibold text-white cursor-pointer disabled:opacity-50">
              {busy === "delete" ? "Deleting..." : `Delete ${picked.length || ""} selected`}
            </button>
          </>
        )}
      </section>
    </div>
  );
}

function AdminPassword() {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (next.length < 10) { toast.error("Use at least 10 characters for the admin password."); return; }
    setBusy(true);
    try { const r = await accountApi.changePassword(current, next); toast.success(r.message); setOpen(false); setCurrent(""); setNext(""); }
    catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }
  if (!open) return <button onClick={() => setOpen(true)} className="flex items-center gap-1.5 rounded-[10px] bg-jasmine-2 px-3 py-2 text-sm font-semibold cursor-pointer"><KeyRound className="h-4 w-4" /> Change my password</button>;
  return (
    <form onSubmit={save} className="flex flex-wrap items-end gap-2 rounded-[14px] border-2 border-line bg-white p-3">
      <label className="text-sm font-semibold">Current<SecretInput type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" className="mt-1 block h-10 w-44 rounded-[10px] border-2 border-line px-2" /></label>
      <label className="text-sm font-semibold">New (10+ characters)<SecretInput type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" className="mt-1 block h-10 w-44 rounded-[10px] border-2 border-line px-2" /></label>
      <button type="submit" disabled={busy} className="h-10 rounded-[10px] bg-night px-3 text-sm font-semibold text-jasmine cursor-pointer">{busy ? "Saving..." : "Save"}</button>
      <button type="button" onClick={() => setOpen(false)} className="h-10 px-2 text-sm text-ink-soft cursor-pointer">Cancel</button>
    </form>
  );
}

type Section = "overview" | "autopilot" | "money" | "renewals" | "tokens" | "tokens-by-restaurant" | "mailbox" | "restaurants" | "users" | "leads" | "activity" | "emails" | "signins" | "support" | "feedback" | "testimonials" | "data";
const SECTIONS: { group: string; items: [Section, string, typeof Users][] }[] = [
  { group: "Overview", items: [["overview", "Today", LayoutDashboard], ["autopilot", "Autopilot", Workflow]] },
  { group: "Money", items: [["money", "Payments", IndianRupee], ["renewals", "Renewals", CalendarClock], ["tokens", "AI tokens", Gauge], ["tokens-by-restaurant", "Tokens by restaurant", Coins]] },
  { group: "Customers", items: [["restaurants", "Restaurants", Building2], ["users", "Users", Users], ["leads", "Demo requests", Inbox]] },
  { group: "Help desk", items: [["support", "Support", LifeBuoy], ["feedback", "Feedback", HeartHandshake], ["testimonials", "Testimonials", Quote], ["mailbox", "Mailbox", MailOpen]] },
  { group: "Logs", items: [["activity", "Activity", ScrollText], ["emails", "Emails sent", Mail], ["signins", "Sign-ins", LogIn]] },
  { group: "System", items: [["data", "Data and backups", Database]] },
];
const when = (d: string) => new Date(d).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
const toneOf = (k: string) => (k === "account_deleted" || k === "account_suspended" || k === "email_failed" || k === "login_failed" || k === "login_locked" ? "chilli" : k === "payment" || k === "account_reactivated" ? "leaf" : k.startsWith("password") ? "turmeric" : k === "signup" || k === "email_sent" ? "sky" : "plain") as "chilli" | "leaf" | "turmeric" | "sky" | "plain";

function ActivityTable({ kind, intro }: { kind?: string; intro: string }) {
  const q = useQuery({ queryKey: ["admin-activity", kind ?? "all"], queryFn: () => (kind ? adminApi.activityOf(kind) : adminApi.activity()), refetchInterval: 60_000 });
  return (
    <div>
      <p className="text-ink-soft">{intro}</p>
      <div className="mt-3 overflow-x-auto rounded-[20px] border-2 border-line bg-white">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead className="bg-jasmine text-ink-soft"><tr><th className="px-4 py-3">When</th><th>What happened</th><th>Restaurant</th><th>Who</th><th className="px-4">Details</th></tr></thead>
          <tbody>
            {q.isLoading ? <tr><td colSpan={5} className="p-4"><Skeleton className="h-10" /></td></tr> : null}
            {q.data && !q.data.length ? <tr><td colSpan={5} className="p-6 text-center text-ink-soft">Nothing yet.</td></tr> : null}
            {q.data?.map((a) => (
              <tr key={a.id} className="border-t-2 border-jasmine-2">
                <td className="whitespace-nowrap px-4 py-3">{when(a.created_at)}</td>
                <td><Chip tone={toneOf(a.kind)}>{a.label}</Chip></td>
                <td className="font-semibold">{a.restaurant ?? "-"}</td>
                <td className="text-ink-soft">{a.user_email ?? "-"}</td>
                <td className="max-w-[340px] px-4 text-ink-soft">{a.detail ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const CHORE_COLOR: Record<string, string> = { leads: "bg-lotus text-white", trials: "bg-chilli text-white", support: "bg-sky text-white", health: "bg-night text-turmeric", money: "bg-leaf text-white" };

function AutopilotPanel() {
  const q = useQuery({ queryKey: ["admin-autopilot"], queryFn: adminAutopilotApi.get, refetchInterval: 60_000 });
  const [view, setView] = useState<"now" | "before">("now");
  const need = (q.data?.chores ?? []).reduce((n, c) => n + c.needs_you, 0);
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-3xl text-ink-soft">Mani, the lead agent, hands every job to the right agent around the clock. You don't need to sign in: if something truly needs you, it comes by WhatsApp and email. {q.data ? <b className="text-ink">{need ? `${need} thing${need === 1 ? "" : "s"} went to you today.` : "Nothing needed you today."}</b> : null}</p>
        <div role="tablist" className="inline-flex rounded-full bg-jasmine-2 p-1">
          <button role="tab" aria-selected={view === "before"} onClick={() => setView("before")} className={cn("cursor-pointer rounded-full px-4 py-1.5 text-sm font-semibold", view === "before" ? "bg-chilli text-white" : "text-ink-soft")}>Before</button>
          <button role="tab" aria-selected={view === "now"} onClick={() => setView("now")} className={cn("cursor-pointer rounded-full px-4 py-1.5 text-sm font-semibold", view === "now" ? "bg-leaf text-white" : "text-ink-soft")}>Now</button>
        </div>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {!q.data ? Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-[240px]" />) : q.data.chores.map((c) => (
          <section key={c.key} className={cn("flex flex-col rounded-[20px] border-2 bg-white p-5", c.needs_you ? "border-chilli" : "border-line")}>
            <div className="flex items-center gap-3">
              <span className={cn("flex h-12 w-12 items-center justify-center rounded-full font-display text-xl font-bold", CHORE_COLOR[c.key])}>{c.name[0]}</span>
              <div><p className="font-display text-lg font-bold leading-tight">{c.name}</p><p className="font-display text-[0.95rem] font-semibold text-chilli">{c.title}</p></div>
            </div>
            <p className="mt-3 font-semibold">{c.chore}</p>
            <p className={cn("mt-1 flex-1 text-sm", view === "now" ? "text-ink" : "text-[#c23a1c]")}>{view === "now" ? c.now : `Before: ${c.before}`}</p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              {c.needs_label ? <Chip tone={c.needs_you ? "chilli" : "leaf"}>{c.needs_you ? `${c.needs_you} ${c.needs_label}` : `No ${c.needs_label}`}</Chip> : null}
              {c.done_label ? <Chip tone="plain">{c.key === "money" ? `₹${c.done.toLocaleString("en-IN")}` : c.done} {c.done_label}</Chip> : null}
            </div>
            <Link to={c.link} className="mt-3 text-sm font-semibold text-night hover:underline">Open</Link>
          </section>
        ))}
      </div>
      <AgentFeedPanel />
    </div>
  );
}

const IST = (iso: string) => new Date(iso).toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" });

function AgentFeedPanel() {
  const q = useQuery({ queryKey: ["admin-agents"], queryFn: adminAgentsApi.get, refetchInterval: 30_000 });
  const f = q.data;
  if (!f) return <Skeleton className="mt-6 h-[300px]" />;
  return (
    <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_1.3fr]">
      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <h3 className="font-display text-xl font-bold">Demos Nila has booked</h3>
        {f.upcoming_demos.length === 0 ? <p className="mt-2 text-sm text-ink-soft">No demos coming up. New requests get times within a minute.</p> : (
          <ul className="mt-3 divide-y divide-line">
            {f.upcoming_demos.map((d) => (
              <li key={d.starts_at + d.restaurant} className="py-3">
                <p className="font-semibold">{d.restaurant} <span className="font-normal text-ink-soft">· {d.name}</span></p>
                <p className="text-sm">{IST(d.starts_at)} · {d.mode}</p>
                <p className="text-sm text-ink-soft">{d.email}{d.phone ? ` · ${d.phone}` : ""}</p>
                {d.link ? <a href={d.link} target="_blank" rel="noreferrer" className="text-sm font-semibold text-night underline">Join link</a> : null}
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <h3 className="font-display text-xl font-bold">What the agents did</h3>
        <p className="text-sm text-ink-soft">Live, newest first. Red lines went to you.</p>
        {f.runs.length === 0 ? <p className="mt-3 text-sm text-ink-soft">Nothing yet. The team checks for work every minute.</p> : (
          <ol className="mt-3 max-h-[420px] space-y-2 overflow-y-auto pr-1">
            {f.runs.map((r) => (
              <li key={r.id} className={cn("rounded-[12px] px-3 py-2 text-sm", r.outcome === "escalated" ? "bg-chilli-soft" : r.outcome === "failed" ? "bg-jasmine-2" : "bg-jasmine")}>
                <span className="font-semibold">{r.name}</span> {r.action}
                <span className="block text-xs text-ink-soft">{IST(r.at)}</span>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

const AREA_LABEL: Record<string, string> = { setup: "Getting set up", inbox: "Reviews inbox", replies: "Replies", alerts: "Alerts", reports: "Reports", ai_staff: "Your AI staff", billing: "Plan and billing", other: "Other" };
const EASE_LABEL = ["Very hard", "Hard", "Okay", "Easy", "Very easy"];

function FeedbackPanel() {
  const q = useQuery({ queryKey: ["admin-feedback"], queryFn: adminFeedbackApi.get, refetchInterval: 60_000 });
  const f = q.data;
  if (!f) return <Skeleton className="h-[420px]" />;
  const most = Math.max(1, ...f.ease_split);
  const tile = (label: string, value: string, note: string, tone: string) => (
    <div className="rounded-[20px] border-2 border-line bg-white p-5">
      <p className="text-sm text-ink-soft">{label}</p>
      <p className={cn("mt-1 font-display text-4xl font-bold", tone)}>{value}</p>
      <p className="text-sm text-ink-soft">{note}</p>
    </div>
  );
  const easeTone = f.ease_avg == null ? "" : f.ease_avg >= 4 ? "text-leaf" : f.ease_avg >= 3 ? "text-[#a86b00]" : "text-chilli";
  const npsTone = f.nps == null ? "" : f.nps >= 30 ? "text-leaf" : f.nps >= 0 ? "text-[#a86b00]" : "text-chilli";
  return (
    <div className="space-y-5">
      <p className="max-w-3xl text-ink-soft">Owners answer "How easy is Virundhu?" in the app, and anyone can share ideas, problems or praise from the website or the app. Isai, the feedback agent, reads each one within a minute: problems become tickets Tara solves, ideas are counted, and praise goes on the website when they allow it. Last {f.days} days.</p>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {tile("Ease of use", f.ease_avg == null ? "-" : `${f.ease_avg}/5`, `${f.ease_count} answer${f.ease_count === 1 ? "" : "s"}`, easeTone)}
        {tile("Would recommend (NPS)", f.nps == null ? "-" : `${f.nps > 0 ? "+" : ""}${f.nps}`, `${f.nps_count} answer${f.nps_count === 1 ? "" : "s"} · above +30 is good`, npsTone)}
        {tile("Ideas", String(f.kinds.idea ?? 0), "counted by part of the app", "text-night")}
        {tile("Problems sent to Tara", String((f.kinds.problem ?? 0) + (f.kinds.question ?? 0)), `${f.kinds.praise ?? 0} praise · ${f.total} in all`, "text-night")}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="rounded-[20px] border-2 border-line bg-white p-5">
          <h3 className="font-display text-lg font-bold">How easy it feels</h3>
          <ul className="mt-3 space-y-2">
            {f.ease_split.map((n, i) => (
              <li key={i} className="grid grid-cols-[80px_1fr_28px] items-center gap-2 text-sm">
                <span>{EASE_LABEL[i]}</span>
                <span className="h-3 overflow-hidden rounded-full bg-jasmine-2"><span className={cn("block h-full rounded-full", i <= 1 ? "bg-chilli" : i === 2 ? "bg-turmeric" : "bg-leaf")} style={{ width: `${(n / most) * 100}%` }} /></span>
                <span className="text-right font-semibold">{n}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-[20px] border-2 border-line bg-white p-5">
          <h3 className="font-display text-lg font-bold">Where people struggle</h3>
          {f.hard_areas.length === 0 ? <p className="mt-2 text-sm text-ink-soft">Nobody has reported a hard part yet.</p> : (
            <ol className="mt-3 space-y-2">{f.hard_areas.slice(0, 6).map(([a, n]) => <li key={a} className="flex justify-between text-sm"><span>{AREA_LABEL[a] ?? a}</span><Chip tone="chilli">{n}</Chip></li>)}</ol>
          )}
        </section>
        <section className="rounded-[20px] border-2 border-line bg-white p-5">
          <h3 className="font-display text-lg font-bold">Most asked-for ideas</h3>
          {f.idea_areas.length === 0 ? <p className="mt-2 text-sm text-ink-soft">No ideas yet.</p> : (
            <ol className="mt-3 space-y-2">{f.idea_areas.slice(0, 6).map(([a, n]) => <li key={a} className="flex justify-between text-sm"><span>{AREA_LABEL[a] ?? a}</span><Chip tone="sky">{n}</Chip></li>)}</ol>
          )}
        </section>
      </div>
      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <h3 className="font-display text-lg font-bold">Every piece of feedback</h3>
        {f.items.length === 0 ? <p className="mt-2 text-sm text-ink-soft">Nothing yet. The form is at /share-feedback and in the app under Share feedback.</p> : (
          <ul className="mt-3 divide-y divide-line">
            {f.items.map((r) => (
              <li key={r.id} className="grid gap-1 py-3 md:grid-cols-[170px_1fr_260px] md:gap-4">
                <div className="text-sm">
                  <Chip tone={r.kind === "problem" || r.kind === "question" ? "chilli" : r.kind === "praise" ? "leaf" : r.kind === "idea" ? "sky" : r.kind === "ease" ? "turmeric" : "plain"}>{r.kind === "ease" ? `Ease ${r.ease}/5` : r.kind}</Chip>
                  <p className="mt-1 font-semibold">{r.who}</p>
                  <p className="text-ink-soft">{r.restaurant ?? (r.source === "website" ? "Website" : "")}</p>
                  <p className="text-xs text-ink-soft">{when(r.at)}</p>
                </div>
                <div className="text-sm">
                  {r.summary ? <p className="font-semibold">{r.summary}</p> : null}
                  {r.message && r.message !== r.summary ? <p className="mt-0.5 text-ink-soft">{r.message}</p> : null}
                  <p className="mt-1 text-xs text-ink-soft">{AREA_LABEL[r.area] ?? r.area}{r.rating ? ` · ${r.rating}★` : ""}{r.nps != null ? ` · recommend ${r.nps}/10` : ""}</p>
                </div>
                <p className={cn("text-sm", r.status === "new" ? "text-ink-soft" : "text-leaf")}>{r.status === "new" ? "Isai is reading it..." : r.action}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function MoneyPanel() {
  const [days, setDays] = useState(30);
  const [includeTest, setIncludeTest] = useState(false);
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["admin-money", days, includeTest], queryFn: () => adminMoneyApi.get(days, includeTest), refetchInterval: 60_000 });
  const sync = useMutation({
    mutationFn: adminMoneyApi.sync,
    onSuccess: (r) => { toast.success(r.message); qc.invalidateQueries({ queryKey: ["admin-money"] }); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const m = q.data;
  if (!m) return <Skeleton className="h-[520px]" />;
  const pick = (keys: string[]) => keys.map((k) => m.windows.find((x) => x.key === k)).filter((x): x is MoneyWindow => Boolean(x));
  const big = pick(["today", "this_week", "this_month", "all_time"]);
  const small = pick(["yesterday", "last_week", "last_30"]);
  const chart = m.daily.map((d) => ({ label: d.label, Collected: Math.round(d.collected), Refunded: Math.round(d.refunded) }));
  const tone = { paid: "leaf", "partly refunded": "turmeric", refunded: "chilli" } as const;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <p className="max-w-2xl text-ink-soft">Every rupee that came in through Dodo and every refund that went out, in India time. Refunds arrive by themselves within seconds of being made in Dodo.</p>
        <Chip tone={m.mode === "live" ? "leaf" : "turmeric"} dot>{m.mode === "live" ? "Live payments" : "Test mode"}</Chip>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {big.map((x) => (
          <div key={x.key} className="rounded-[20px] border-2 border-line bg-white p-5">
            <p className="text-sm text-ink-soft">{x.label}</p>
            <p className="mt-1 font-display text-3xl font-bold">{inr(x.net)}</p>
            <p className="text-sm text-ink-soft">{inr(x.collected)} from {x.payments} payment{x.payments === 1 ? "" : "s"}</p>
            <p className={cn("text-sm", x.refunded ? "font-semibold text-[#b32f12]" : "text-ink-soft")}>{x.refunded ? `− ${inr(x.refunded)} in ${x.refunds} refund${x.refunds === 1 ? "" : "s"}` : "No refunds"}</p>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-ink-soft">
        {small.map((x) => <span key={x.key}>{x.label}: <b className="text-ink">{inr(x.net)}</b> net ({x.payments} paid{x.refunds ? `, ${x.refunds} refunded` : ""})</span>)}
      </div>

      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-display text-lg font-bold">Per day</h3>
          <div className="flex gap-2" role="radiogroup" aria-label="How many days">
            {[7, 30, 90].map((d) => (
              <button key={d} type="button" role="radio" aria-checked={days === d} onClick={() => setDays(d)}
                className={cn("rounded-full border-2 px-3 py-1 text-sm font-semibold", days === d ? "border-night bg-night text-jasmine" : "border-line bg-white hover:border-night")}>{d} days</button>
            ))}
          </div>
        </div>
        <div className="mt-4 h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart} margin={{ left: 0, right: 8, top: 8 }}>
              <CartesianGrid vertical={false} stroke="#e8e2d0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" minTickGap={16} />
              <YAxis tick={{ fontSize: 11 }} width={56} tickFormatter={(v: number) => `₹${v.toLocaleString("en-IN")}`} />
              <Tooltip formatter={(v) => inr(Number(v))} />
              <Bar dataKey="Collected" fill="#1f7a4d" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Refunded" fill="#d2462a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <h3 className="font-display text-lg font-bold">Per week</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <thead><tr className="text-left text-ink-soft"><th className="py-2 font-semibold">Week starting</th><th className="text-right font-semibold">Payments</th><th className="text-right font-semibold">Collected</th><th className="text-right font-semibold">Refunded</th><th className="text-right font-semibold">Net</th></tr></thead>
            <tbody>
              {[...m.weekly].reverse().map((b) => (
                <tr key={b.start} className="border-t border-line">
                  <td className="py-2">{b.label}</td><td className="text-right">{b.payments}</td><td className="text-right">{inr(b.collected)}</td>
                  <td className={cn("text-right", b.refunded ? "text-[#b32f12]" : "")}>{b.refunded ? `− ${inr(b.refunded)}` : "₹0"}</td><td className="text-right font-semibold">{inr(b.net)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-display text-lg font-bold">Every payment</h3>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={includeTest} onChange={(e) => setIncludeTest(e.target.checked)} className="h-4 w-4 accent-[#0c3b2e]" />
            Show test payments{m.hidden_test_payments ? ` (${m.hidden_test_payments} hidden)` : ""}
          </label>
        </div>
        {m.payments.length === 0 ? <p className="mt-3 text-sm text-ink-soft">No payments yet. The first one will show here within seconds of being made.</p> : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead><tr className="text-left text-ink-soft"><th className="py-2 font-semibold">When</th><th className="font-semibold">Restaurant</th><th className="font-semibold">Plan</th><th className="font-semibold">Invoice</th><th className="text-right font-semibold">Amount</th><th className="pl-4 font-semibold">Status</th></tr></thead>
              <tbody>
                {m.payments.map((p) => (
                  <tr key={p.id} className="border-t border-line">
                    <td className="py-2">{when(p.paid_at)}</td>
                    <td>{p.restaurant}{p.is_test ? <span className="ml-1.5 text-xs text-ink-soft">(test)</span> : null}</td>
                    <td className="text-ink-soft">{p.outlets ? `${p.outlets} outlet${p.outlets === 1 ? "" : "s"}` : ""}{p.months ? ` × ${p.months} mo` : ""}</td>
                    <td className="text-ink-soft">{p.invoice_no ?? "-"}</td>
                    <td className="text-right font-semibold">{inr(p.amount)}{p.refunded ? <span className="block text-xs font-normal text-[#b32f12]">− {inr(p.refunded)}</span> : null}</td>
                    <td className="pl-4"><Chip tone={tone[p.status]}>{p.status === "paid" ? "Paid" : p.status === "refunded" ? "Refunded" : "Partly refunded"}</Chip></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-[20px] border-2 border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-display text-lg font-bold">Refunds</h3>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => sync.mutate()} disabled={sync.isPending}><RefreshCw className="h-4 w-4" /> {sync.isPending ? "Checking Dodo..." : "Check Dodo for refunds"}</Button>
            <a href="https://app.dodopayments.com/transactions/payments" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-full border-2 border-line px-3 py-1.5 text-sm font-semibold hover:border-night">Refund in Dodo <ExternalLink className="h-4 w-4" /></a>
          </div>
        </div>
        <p className="mt-1 text-sm text-ink-soft">To give money back, open the payment in Dodo and press Refund. It shows here within seconds, and the restaurant keeps access until its paid period ends.</p>
        {m.refunds.length === 0 ? <p className="mt-3 text-sm text-ink-soft">No refunds so far.</p> : (
          <ul className="mt-3 divide-y divide-line">
            {m.refunds.map((r) => (
              <li key={r.refund_id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                <span><b>{inr(r.amount)}</b> to {r.restaurant ?? "a deleted restaurant"}{r.reason ? <span className="text-ink-soft"> · {r.reason}</span> : null}</span>
                <span className="flex items-center gap-2 text-ink-soft">{when(r.refunded_at)} <Chip tone={r.status === "succeeded" ? "leaf" : r.status === "failed" ? "chilli" : "turmeric"}>{r.status === "succeeded" ? "Refunded" : r.status}</Chip></span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function MailboxPanel() {
  const q = useQuery({ queryKey: ["admin-mailbox"], queryFn: adminApi.mailbox, refetchInterval: 60_000 });
  const m = q.data;
  const look: Record<string, { ring: string; chip: "chilli" | "turmeric" | "leaf" | "sky" | "plain"; badge: string }> = {
    demo: { ring: "border-chilli", chip: "chilli", badge: "new" },
    info: { ring: "border-turmeric", chip: "turmeric", badge: "open" },
    sent: { ring: "border-night", chip: "sky", badge: "failed" },
  };
  return (
    <div>
      <p className="text-ink-soft">Every company email lives on your Google Workspace domain. Counts come from what Virundhu recorded; <b>Open in Gmail</b> opens that inbox{m ? <> (signed in as <b>{m.account}</b>)</> : null} filtered to the address.</p>
      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        {!m ? Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-[190px]" />) : m.boxes.map((b) => (
          <section key={b.key} className={cn("flex flex-col rounded-[20px] border-2 bg-white p-5", look[b.key]?.ring)}>
            <h2 className="font-display text-lg font-bold">{b.label}</h2>
            <p className="break-all text-sm font-semibold text-night">{b.address}</p>
            <p className="mt-1 text-sm text-ink-soft">{b.purpose}</p>
            <div className="mt-3 flex items-end gap-4">
              <p><span className="font-display text-[2.2rem] font-bold leading-none">{b.total}</span><span className="ml-1 text-sm text-ink-soft">total</span></p>
              <p className="text-sm text-ink-soft">{b.week} this week</p>
              {b.new ? <Chip tone={look[b.key]?.chip ?? "plain"}>{b.new} {look[b.key]?.badge}</Chip> : null}
            </div>
            {b.gmail_url.startsWith("/") ? (
              <Link to={b.gmail_url} className="mt-4 flex items-center justify-center gap-2 rounded-[12px] bg-night px-3 py-2.5 text-sm font-semibold text-jasmine hover:opacity-90">
                See every email sent <Mail className="h-4 w-4" />
              </Link>
            ) : (
              <a href={b.gmail_url} target="_blank" rel="noreferrer" className="mt-4 flex items-center justify-center gap-2 rounded-[12px] bg-night px-3 py-2.5 text-sm font-semibold text-jasmine hover:opacity-90">
                Open in Gmail <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </section>
        ))}
      </div>
      <h2 className="mt-7 font-display text-xl font-bold">Latest messages</h2>
      <div className="mt-3 overflow-x-auto rounded-[20px] border-2 border-line bg-white">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-jasmine text-ink-soft"><tr><th className="px-4 py-3">When</th><th>Inbox</th><th>From</th><th>Message</th><th className="px-4">Status</th></tr></thead>
          <tbody>
            {m && !m.recent.length ? <tr><td colSpan={5} className="p-6 text-center text-ink-soft">No demo requests or support messages yet.</td></tr> : null}
            {m?.recent.map((r, i) => (
              <tr key={i} className="border-t-2 border-jasmine-2">
                <td className="whitespace-nowrap px-4 py-3">{when(r.at)}</td>
                <td><Chip tone={r.box === "demo" ? "chilli" : "turmeric"}>{r.box === "demo" ? "Demo" : "Info"}</Chip></td>
                <td className="text-ink-soft">{r.who ?? "-"}</td>
                <td><p className="font-semibold">{r.title}</p>{r.detail ? <p className="max-w-[360px] truncate text-ink-soft">{r.detail}</p> : null}</td>
                <td className="px-4 capitalize text-ink-soft">{r.status.replace("_", " ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RestaurantLog({ org, onClose }: { org: { id: number; name: string }; onClose: () => void }) {
  const [filter, setFilter] = useState("all");
  const q = useQuery({ queryKey: ["org-log", org.id], queryFn: () => adminApi.orgLog(org.id) });
  const kinds = ["all", "email", "login", "upload", "payment", "password", "support"];
  const rows = (q.data ?? []).filter((r) => filter === "all" || r.kind.startsWith(filter) || (filter === "support" && r.kind.includes("ticket")));
  return (
    <section className="mb-5 rounded-[20px] border-2 border-night bg-white p-5" aria-label={`Log for ${org.name}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-xl font-bold">{org.name}: full log</h2>
        <button onClick={onClose} className="flex items-center gap-1 rounded-[10px] px-2 py-1 text-sm font-semibold text-ink-soft hover:bg-jasmine cursor-pointer"><X className="h-4 w-4" /> Close</button>
      </div>
      <p className="text-sm text-ink-soft">Every sign-in, email sent to them, upload, payment, password change and support request for this restaurant, newest first.</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {kinds.map((k) => <button key={k} onClick={() => setFilter(k)} className={cn("rounded-full px-3 py-1 text-sm font-semibold cursor-pointer", filter === k ? "bg-night text-jasmine" : "bg-jasmine-2 text-ink-soft")}>{({ all: "All", email: "Emails", login: "Sign-ins", upload: "Uploads", payment: "Payments", password: "Passwords", support: "Support" } as Record<string, string>)[k]}</button>)}
      </div>
      <div className="mt-3 max-h-[440px] overflow-auto rounded-[14px] border-2 border-jasmine-2">
        <table className="w-full min-w-[640px] text-left text-sm">
          <tbody>
            {q.isLoading ? <tr><td className="p-4"><Skeleton className="h-10" /></td></tr> : null}
            {!q.isLoading && !rows.length ? <tr><td className="p-6 text-center text-ink-soft">Nothing recorded for this filter yet.</td></tr> : null}
            {rows.map((r, i) => (
              <tr key={i} className="border-t-2 border-jasmine-2 first:border-t-0">
                <td className="whitespace-nowrap px-3 py-2.5 text-ink-soft">{when(r.at)}</td>
                <td className="px-2"><Chip tone={toneOf(r.kind)}>{r.label}</Chip></td>
                <td className="px-2 text-ink-soft">{r.who ?? ""}</td>
                <td className="px-3 text-ink-soft">{r.detail ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function BankPaymentForm({ org, onClose }: { org: { id: number; name: string }; onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState({ outlets: "", months: "12", amount: "", reference: "" });
  const [busy, setBusy] = useState(false);
  const { data: table } = useQuery({ queryKey: ["pricing-table"], queryFn: billingApi.pricing, staleTime: 3_600_000 });
  const outlets = Number(f.outlets) || 0;
  const price = table && outlets >= 1 ? quoteFrom(table, outlets, Number(f.months)).total : null;
  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await adminBankApi.record(org.id, { outlets, months: Number(f.months), amount_inr: Number(f.amount), reference: f.reference.trim() });
      toast.success(r.message); void qc.invalidateQueries({ queryKey: ["admin-orgs"] }); void qc.invalidateQueries({ queryKey: ["admin-money"] }); onClose();
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  }
  const box = "mt-1 block h-10 w-full rounded-[10px] border-2 border-line bg-white px-2";
  return (
    <section className="mb-5 rounded-[20px] border-2 border-night bg-white p-5" aria-label={`Record bank payment for ${org.name}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-xl font-bold">Record bank payment: {org.name}</h2>
        <button onClick={onClose} className="flex items-center gap-1 rounded-[10px] px-2 py-1 text-sm font-semibold text-ink-soft hover:bg-jasmine cursor-pointer"><X className="h-4 w-4" /> Close</button>
      </div>
      <p className="text-sm text-ink-soft">Only after the money is in your bank account. This switches the plan on, counts the revenue and emails the GST receipt, just like an online payment.</p>
      <form onSubmit={save} className="mt-3 grid gap-3 sm:grid-cols-5">
        <label className="text-sm font-semibold">Outlets<input inputMode="numeric" value={f.outlets} onChange={(e) => setF({ ...f, outlets: e.target.value.replace(/\D/g, "") })} className={box} required /></label>
        <label className="text-sm font-semibold">Months<select value={f.months} onChange={(e) => setF({ ...f, months: e.target.value })} className={box}>{[1, 3, 6, 9, 12].map((m) => <option key={m} value={m}>{m}</option>)}</select></label>
        <label className="text-sm font-semibold">Amount received (₹)<input inputMode="numeric" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value.replace(/\D/g, "") })} className={box} required /></label>
        <label className="text-sm font-semibold">UTR / bank reference<input value={f.reference} onChange={(e) => setF({ ...f, reference: e.target.value })} className={box} required minLength={4} maxLength={40} /></label>
        <div className="flex items-end"><Button type="submit" disabled={busy} className="w-full">{busy ? "Saving..." : "Record payment"}</Button></div>
      </form>
      {price !== null ? <p className="mt-2 text-sm text-ink-soft">Price for {outlets.toLocaleString("en-IN")} outlets, {f.months} months: <b className="text-ink">₹{price.toLocaleString("en-IN")}</b>. A smaller amount is refused.</p> : null}
    </section>
  );
}

function AdminPanel() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { section } = useParams();
  const tab = (SECTIONS.some((g) => g.items.some(([k]) => k === section)) ? section : "overview") as Section;
  const title = SECTIONS.flatMap((g) => g.items).find(([k]) => k === tab)?.[1] ?? "Admin console";
  const [logOrg, setLogOrg] = useState<{ id: number; name: string } | null>(null);
  const [bankOrg, setBankOrg] = useState<{ id: number; name: string } | null>(null);
  const stats = useQuery({ queryKey: ["admin-stats"], queryFn: adminApi.stats, refetchInterval: 30_000 });
  const orgs = useQuery({ queryKey: ["admin-orgs"], queryFn: adminApi.orgs, refetchInterval: 30_000 });
  const users = useQuery({ queryKey: ["admin-users"], queryFn: adminApi.users, enabled: tab === "users" });
  const leads = useQuery({ queryKey: ["admin-leads"], queryFn: adminApi.leads, refetchInterval: 60_000 });
  const events = useQuery({ queryKey: ["admin-events"], queryFn: adminApi.events, refetchInterval: 60_000 });
  const s = stats.data;


  async function act(fn: () => Promise<unknown>, ok: string) {
    try { await fn(); toast.success(ok); void qc.invalidateQueries({ queryKey: ["admin-orgs"] }); void qc.invalidateQueries({ queryKey: ["admin-users"] }); }
    catch (err) { toast.error(errorMessage(err)); }
  }

  function open(id: number, name: string) {
    viewAs.set({ id, name });
    qc.clear();
    navigate("/app");
  }

  const chart = (s?.daily ?? []).map((d) => ({ ...d, label: shortDate(d.day) }));

  return (
    <div className="mx-auto max-w-[1280px]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h1 className="text-[2.3rem] font-bold">{title}</h1>
        <AdminPassword />
      </div>
      {tab === "overview" ? <p className="mt-1 max-w-3xl text-ink-soft">You run Virundhu. Every customer restaurant, subscription, user and review count is here; pick a section on the left.
        Customers never see these pages. Click <b>Open</b> on a restaurant to see it exactly as its owner does.</p> : null}
      <div className="mt-6">
      <div className="min-w-0">
      {tab === "overview" ? (<>
      <LaunchChecklist />

      {events.data?.length ? (
        <section className="mt-6 rounded-[20px] bg-night p-5 text-jasmine">
          <h2 className="font-display text-xl font-bold">Needs your attention</h2>
          <ul className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
            {events.data.slice(0, 6).map((e) => (
              <li key={e.id} className="rounded-[14px] bg-white/[0.06] p-3">
                <p className={cn("font-semibold", e.kind === "urgent_waiting" ? "text-[#ffb3a3]" : e.kind === "signup" ? "text-[#8ff0bf]" : "text-turmeric")}>{e.title}</p>
                <p className="text-sm text-mist">{e.body}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {!s ? Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[130px]" />) : (
          <>
            <Tile icon={Building2} label="Restaurants" value={s.restaurants} note={`${s.paying} paying, ${s.trialing} on trial`} tone="dark" />
            <Tile icon={MessageSquareText} label="Reviews today" value={s.reviews_today} note={`${s.reviews_7d.toLocaleString("en-IN")} this week, ${s.reviews_30d.toLocaleString("en-IN")} in 30 days`} />
            <Tile icon={ShieldAlert} label="Urgent, not replied" value={s.urgent_open} note="Across all restaurants" tone="urgent" />
            <Tile icon={IndianRupee} label="Monthly revenue (paid outlets)" value={s.mrr_inr} money note={`Collected this month ${inr(s.collected_month_inr)}. AI cost ${inr(s.ai_cost_month_inr)}`} />
          </>
        )}
      </section>


      <section className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-[1.7fr_1fr]">
        <div className="rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
          <h2 className="text-xl font-bold">Reviews coming in, last 14 days</h2>
          <div className="mt-4 h-[260px]">
            {s ? (
              <ResponsiveContainer>
                <BarChart data={chart} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid stroke="#e6dcc8" strokeDasharray="3 4" vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "#5b5d78", fontSize: 11 }} interval={1} />
                  <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "#5b5d78", fontSize: 12 }} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "2px solid #0c3b2e" }} />
                  {(["google", "zomato", "swiggy", "direct", "other"] as const).map((p, i) => (
                    <Bar key={p} dataKey={p} name={p === "direct" ? "QR feedback" : p[0]?.toUpperCase() + p.slice(1)} stackId="a" fill={PLATFORM_COLORS[p]} radius={i === 4 ? [6, 6, 0, 0] : 0} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            ) : <Skeleton className="h-full" />}
          </div>
        </div>
        <div className="rounded-[20px] border-2 border-line bg-white p-5 sm:p-6">
          <h2 className="text-xl font-bold">By platform, last 30 days</h2>
          <ul className="mt-5 space-y-4">
            {s ? (Object.entries(s.by_platform_30d) as [keyof typeof PLATFORM_COLORS, number][]).map(([p, n]) => {
              const max = Math.max(1, ...Object.values(s.by_platform_30d));
              return (
                <li key={p}>
                  <div className="flex justify-between text-sm"><span className="font-semibold capitalize">{p}</span><span className="tabular font-bold">{n.toLocaleString("en-IN")}</span></div>
                  <div className="mt-1 h-3 overflow-hidden rounded-full bg-jasmine-2"><div className="h-full rounded-full" style={{ width: `${(n / max) * 100}%`, background: PLATFORM_COLORS[p] }} /></div>
                </li>
              );
            }) : null}
          </ul>
        </div>
      </section>

      </>) : tab === "restaurants" ? (<>
        {logOrg ? <RestaurantLog org={logOrg} onClose={() => setLogOrg(null)} /> : null}
        {bankOrg ? <BankPaymentForm org={bankOrg} onClose={() => setBankOrg(null)} /> : null}
        <div className="overflow-x-auto rounded-[20px] border-2 border-line bg-white">
          <table className="w-full min-w-[980px] text-left text-sm">
            <thead className="bg-jasmine text-ink-soft"><tr>
              <th className="px-4 py-3">Restaurant</th><th>Plan</th><th>Users</th><th>Outlets</th><th>Reviews 30d</th><th>Urgent</th><th>AI cost</th><th>Last review</th><th className="px-4 text-right">Actions</th>
            </tr></thead>
            <tbody>
              {orgs.isLoading ? <tr><td colSpan={9} className="p-4"><Skeleton className="h-10" /></td></tr> : null}
              {orgs.data?.map((o) => (
                <tr key={o.id} className={cn("border-t-2 border-jasmine-2", o.is_suspended && "opacity-60")}>
                  <td className="px-4 py-3">
                    <p className="font-semibold">{o.name} {o.is_demo ? <Chip tone="lotus" className="ml-1">Demo</Chip> : null} {o.is_suspended ? <Chip tone="chilli" className="ml-1">Suspended</Chip> : null}</p>
                    <p className="text-ink-soft">{o.owner_email ?? "-"}{o.city ? `, ${o.city}` : ""}</p>
                  </td>
                  <td>
                    <select value={o.plan} onChange={(e) => act(() => adminApi.updateOrg(o.id, { plan: e.target.value }), "Plan changed")}
                      className="h-9 rounded-[10px] border-2 border-line bg-white px-2 font-semibold capitalize" aria-label={`Plan for ${o.name}`}>
                      {["trial", "starter", "growth", "chain"].map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                    {o.plan === "trial" && o.trial_ends_at ? <p className="mt-0.5 text-xs text-ink-soft">ends {new Date(o.trial_ends_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</p> : null}
                  </td>
                  <td className="tabular">{o.users}</td>
                  <td className="tabular">{o.outlets}</td>
                  <td className="tabular font-semibold">{o.reviews_30d}</td>
                  <td>{o.urgent_open ? <Chip tone="chilli">{o.urgent_open}</Chip> : <Chip tone="leaf">0</Chip>}</td>
                  <td className="tabular">{inr(o.ai_cost_month_inr)}</td>
                  <td>{o.last_review ? shortDate(o.last_review) : "-"}</td>
                  <td className="px-4">
                    <div className="flex justify-end gap-1.5">
                      <button onClick={() => open(o.id, o.name)} className="flex items-center gap-1 rounded-[10px] bg-night px-2.5 py-1.5 font-semibold text-jasmine cursor-pointer"><Eye className="h-3.5 w-3.5" />Open</button>
                      <button onClick={() => { setLogOrg({ id: o.id, name: o.name }); window.scrollTo({ top: 0, behavior: "smooth" }); }} className="flex items-center gap-1 rounded-[10px] border-2 border-line px-2.5 py-1 font-semibold cursor-pointer hover:border-night"><ScrollText className="h-3.5 w-3.5" />Logs</button>
                      {!o.is_demo ? <button onClick={() => { setBankOrg({ id: o.id, name: o.name }); window.scrollTo({ top: 0, behavior: "smooth" }); }} className="flex items-center gap-1 rounded-[10px] border-2 border-line px-2.5 py-1 font-semibold cursor-pointer hover:border-night"><Landmark className="h-3.5 w-3.5" />Record bank payment</button> : null}
                      {!o.is_demo ? <button onClick={() => act(() => adminApi.updateOrg(o.id, { is_suspended: !o.is_suspended }), o.is_suspended ? "Restaurant restored" : "Restaurant suspended")}
                        className="rounded-[10px] px-2.5 py-1.5 font-semibold text-chilli hover:bg-chilli-soft cursor-pointer">{o.is_suspended ? "Restore" : "Suspend"}</button> : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>) : tab === "testimonials" ? (
        <TestimonialsAdmin />
      ) : tab === "data" ? (
        <DataTools />
      ) : tab === "support" ? (
        <SupportAdmin />
      ) : tab === "activity" ? (
        <ActivityTable intro="Everything recorded across all restaurants, newest first: sign-ups, sign-ins, emails, uploads, payments, passwords and support. Kept even after a restaurant deletes its account." />
      ) : tab === "tokens" ? (
        <TokensTotalPanel />
      ) : tab === "tokens-by-restaurant" ? (
        <TokensByRestaurantPanel />
      ) : tab === "money" ? (
        <MoneyPanel />
      ) : tab === "renewals" ? (
        <RevenueBoard />
      ) : tab === "feedback" ? (
        <FeedbackPanel />
      ) : tab === "autopilot" ? (
        <AutopilotPanel />
      ) : tab === "mailbox" ? (
        <MailboxPanel />
      ) : tab === "emails" ? (
        <ActivityTable kind="email_sent" intro="Every email Virundhu sent to a customer: welcome, password reset, password changed, trial reminders, receipts, alerts and support replies. Open a restaurant's Logs to see only theirs." />
      ) : tab === "signins" ? (
        <ActivityTable kind="login" intro="Every sign-in with the time and device. Wrong passwords and locks are under All activity." />
      ) : tab === "leads" ? (
        <div className="overflow-x-auto rounded-[20px] border-2 border-line bg-white">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead className="bg-jasmine text-ink-soft"><tr><th className="px-4 py-3">Who</th><th>Reach them</th><th>Outlets</th><th>Message</th><th>When</th><th className="px-4 text-right">Status</th></tr></thead>
            <tbody>
              {leads.isLoading ? <tr><td colSpan={6} className="p-4"><Skeleton className="h-10" /></td></tr> : null}
              {leads.data && !leads.data.length ? <tr><td colSpan={6} className="p-6 text-center text-ink-soft">No demo requests yet. They arrive from the Contact page.</td></tr> : null}
              {leads.data?.map((l) => (
                <tr key={l.id} className="border-t-2 border-jasmine-2 align-top">
                  <td className="px-4 py-3"><p className="font-semibold">{l.restaurant}</p><p className="text-ink-soft">{l.name}{l.city ? `, ${l.city}` : ""}</p></td>
                  <td className="py-3">
                    {l.phone ? <a className="block font-semibold underline" href={`https://wa.me/${l.phone.replace(/[^0-9]/g, "")}`} target="_blank" rel="noreferrer">{l.phone}</a> : null}
                    {l.email ? <a className="block text-ink-soft underline" href={`mailto:${l.email}`}>{l.email}</a> : null}
                  </td>
                  <td className="tabular py-3">{l.outlets ?? "-"}</td>
                  <td className="max-w-[280px] py-3 text-ink-soft">{l.message ?? "-"}</td>
                  <td className="py-3">{new Date(l.created_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })}</td>
                  <td className="px-4 py-3 text-right">
                    <select value={l.status} aria-label={`Status for ${l.restaurant}`}
                      onChange={(e) => act(async () => { await adminApi.updateLead(l.id, e.target.value); await qc.invalidateQueries({ queryKey: ["admin-leads"] }); }, "Status saved")}
                      className="h-9 rounded-[10px] border-2 border-line bg-white px-2 font-semibold capitalize">
                      {["new", "contacted", "won", "lost"].map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-[20px] border-2 border-line bg-white">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-jasmine text-ink-soft"><tr><th className="px-4 py-3">User</th><th>Restaurants</th><th>Last sign-in</th><th>Joined</th><th className="px-4 text-right">Status</th></tr></thead>
            <tbody>
              {users.isLoading ? <tr><td colSpan={5} className="p-4"><Skeleton className="h-10" /></td></tr> : null}
              {users.data?.map((u) => (
                <tr key={u.id} className="border-t-2 border-jasmine-2">
                  <td className="px-4 py-3"><p className="font-semibold">{u.full_name} {u.is_superadmin ? <Chip tone="turmeric" className="ml-1">Admin</Chip> : null}</p><p className="text-ink-soft">{u.email}</p></td>
                  <td className="max-w-[280px] text-ink-soft">{u.restaurants.join(", ") || "-"}</td>
                  <td>{u.last_login_at ? new Date(u.last_login_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) : "Never"}</td>
                  <td>{new Date(u.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</td>
                  <td className="px-4 text-right">
                    {u.is_superadmin ? <Chip tone="leaf">Active</Chip> : (
                      <button onClick={() => act(() => adminApi.updateUser(u.id, !u.is_active), u.is_active ? "User switched off" : "User switched on")}
                        className={cn("rounded-full px-3 py-1 font-semibold cursor-pointer", u.is_active ? "bg-leaf-soft text-[#16784a]" : "bg-chilli-soft text-chilli")}>{u.is_active ? "Active" : "Switched off"}</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      </div>
      </div>
    </div>
  );
}
