import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import type {
  ActivityItem, AdminEvent, AdminOrg, AdminStats, AdminUser, Connection, CurrentUser, ImportBatch, InboxView, InviteInfo, NotificationList, OrgSettings,
  Outlet, OutletInput, Overview, Platform, PublicConfig, Review, ReviewPage, Team, TeamInvite, TokenResponse, TryResult, WorkflowStatus,
} from "@/types";

const SIGNED_IN = "vr_signed_in"; // only a "1": tells the page to try restoring the session. Not a secret.
const VIEW_ORG = "vr_view_org";
const OLD_KEYS = ["vr_access", "vr_refresh"]; // older versions kept tokens here; wiped on load
function resolveApiUrl(): string {
  const configured: string = import.meta.env.VITE_API_URL ?? "http://localhost:8450";
  // Opened from a phone on the same Wi-Fi? Point "localhost" at the computer that served this page.
  if (configured.includes("localhost") && typeof window !== "undefined" && !["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    return configured.replace("localhost", window.location.hostname);
  }
  return configured;
}
export const API_URL: string = resolveApiUrl();

function store(): Storage | null {
  try { return window.localStorage; } catch { return null; }
}

// The short-lived access token lives only in memory (gone when the tab closes). The long-lived session token is an
// HttpOnly cookie set by the server: no script on this page, ours or anyone else's, can read either from storage.
let accessToken: string | null = null;
try { OLD_KEYS.forEach((k) => store()?.removeItem(k)); } catch { /* storage off */ }

export const tokens = {
  access: (): string | null => accessToken,
  signedIn: (): boolean => { try { return store()?.getItem(SIGNED_IN) === "1"; } catch { return false; } },
  save: (t: { access_token: string }): void => {
    accessToken = t.access_token;
    try { store()?.setItem(SIGNED_IN, "1"); } catch { /* storage off */ }
  },
  clear: (): void => {
    accessToken = null;
    try { store()?.removeItem(SIGNED_IN); store()?.removeItem(VIEW_ORG); } catch { /* storage off */ }
  },
};

/** Super admin "open this restaurant": every request carries X-Org-Id while it's set. */
export const viewAs = {
  get: (): { id: number; name: string } | null => {
    try { const raw = store()?.getItem(VIEW_ORG); return raw ? (JSON.parse(raw) as { id: number; name: string }) : null; } catch { return null; }
  },
  set: (org: { id: number; name: string } | null): void => {
    try { if (org) store()?.setItem(VIEW_ORG, JSON.stringify(org)); else store()?.removeItem(VIEW_ORG); } catch { /* storage off */ }
  },
};

export const api = axios.create({ baseURL: API_URL, timeout: 30000, withCredentials: true });

api.interceptors.request.use((config) => {
  const token = tokens.access();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  const view = viewAs.get();
  if (view && !config.url?.includes("/admin/") && !config.url?.includes("/auth/")) config.headers["X-Org-Id"] = String(view.id);
  return config;
});

let refreshing: Promise<string | null> | null = null;

/** One refresh at a time: page load and a failed request asking together share the same answer. */
function refreshAccess(): Promise<string | null> {
  refreshing ??= doRefresh().finally(() => { refreshing = null; });
  return refreshing;
}

async function doRefresh(): Promise<string | null> {
  if (!tokens.signedIn()) return null;
  try {
    const { data } = await axios.post<TokenResponse>(`${API_URL}/api/v1/auth/refresh`, {}, { withCredentials: true });
    tokens.save(data);
    return data.access_token;
  } catch {
    tokens.clear();
    return null;
  }
}

// On 401, try one silent refresh, then repeat the original request.
api.interceptors.response.use(undefined, async (error: AxiosError) => {
  if (error.response?.status === 402) window.dispatchEvent(new Event("virundhu:locked"));
  const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
  const isAuthCall = original?.url?.includes("/auth/");
  if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
    original._retried = true;
    const token = await refreshAccess();
    if (token) {
      original.headers.Authorization = `Bearer ${token}`;
      return api(original);
    }
  }
  return Promise.reject(error);
});

/** One clear sentence for any API error. */
export function errorMessage(err: unknown): string {
  if (err instanceof AxiosError) {
    if (!err.response) return "Can't reach Virundhu right now. Check your internet and try again.";
    const detail = (err.response.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return "Please check the highlighted fields.";
    if (err.response.status === 429) return "Too many tries. Please wait a minute and try again.";
  }
  return "Something went wrong. Please try again.";
}

export const authApi = {
  login: (email: string, password: string) => api.post<TokenResponse>("/api/v1/auth/login", { email, password }).then((r) => r.data),
  register: (body: { full_name: string; organization_name: string; city?: string; email: string; password: string; accept_terms: boolean; phone?: string; outlets?: number }) =>
    api.post<TokenResponse>("/api/v1/auth/register", body).then((r) => r.data),
  forgot: (email: string) => api.post<{ message: string }>("/api/v1/auth/forgot-password", { email }).then((r) => r.data),
  reset: (token: string, password: string) => api.post("/api/v1/auth/reset-password", { token, password }).then((r) => r.data),
  me: () => api.get<CurrentUser>("/api/v1/auth/me").then((r) => r.data),
  logout: () => api.post("/api/v1/auth/logout", {}),
  refresh: refreshAccess,
};

export const accountApi = {
  changePassword: (current_password: string, new_password: string) =>
    api.post<{ message: string }>("/api/v1/account/password", { current_password, new_password }).then((r) => r.data),
  exportCsv: () => api.get<Blob>("/api/v1/account/export", { responseType: "blob" }).then((r) => r.data),
  deleteCheck: () => api.get<{ balance_due: number; plan: string; paid_until: string | null; paid_days_left: number; last_payment: { amount: number; invoice_no: string | null; date: string } | null }>("/api/v1/account/delete-check").then((r) => r.data),
  deleteAll: (confirm_name: string, password: string) => api.post("/api/v1/account/delete", { confirm_name, password }).then((r) => r.data),
};

export interface Testimonial { id: number; name: string; role: string | null; quote: string; published: boolean; sort_order: number }
export type TestimonialInput = Omit<Testimonial, "id">;

export const publicApi = {
  testimonials: () => api.get<Testimonial[]>("/api/v1/public/testimonials").then((r) => r.data),
  config: () => api.get<PublicConfig>("/api/v1/public/config").then((r) => r.data),
  tryReview: (text: string) => api.post<TryResult>("/api/v1/public/try", { text }).then((r) => r.data),
};

export interface BillingDetails { company_name: string; gstin: string; address: string }
export interface Receipt {
  id: number; invoice_no: string | null; paid_at: string; restaurant: string; bill_name: string; bill_gstin: string | null;
  bill_address: string | null; bill_email: string | null; outlets: number | null; months: number | null; period_start: string | null;
  period_end: string | null; amount: number; currency: string; payment_id: string; status: string;
  seller: { name: string; email: string; address: string; parent?: string | null; gstin?: string | null };
}
export interface BillingStatus {
  billing?: { company_name: string; gstin: string | null; address: string | null };
  plan: string; limits: { reviews_per_month: number; outlets: number; seats: number };
  ends_at: string | null; expired: boolean; payments_enabled: boolean; provider: "dodo" | "razorpay"; promo: { code: string; text: string } | null;
  paid_outlets: number | null; outlets_now: number;
  pricing: PricingTable;
  payments: { id: string; receipt_id: number; invoice_no: string | null; months: number | null; outlets: number | null; amount: number; status: string; paid_at: string }[];
}
export interface PricingTable {
  tiers: { from_outlets: number; per_outlet_month: number; name: string }[];
  durations: { months: number; discount_percent: number; bonus_months: number }[];
  max_outlets: number; reviews_per_outlet: number;
}
export interface RazorpayOrder { order_id: string; amount: number; currency: string; key_id: string; restaurant: string; email: string; name: string }

export interface Lead { id: number; name: string; restaurant: string; phone: string | null; email: string | null; city: string | null; outlets: number | null; message: string | null; status: string; created_at: string }

export const siteApi = {
  contact: (body: { name: string; restaurant: string; phone: string; email: string; city: string; outlets: number | null; message: string; website: string }) =>
    api.post("/api/v1/public/contact", body).then((r) => r.data),
};

export const feedbackApi = {
  form: (token: string) =>
    api.get<{ restaurant: string; city: string | null; outlets: { id: number; name: string }[] }>(`/api/v1/public/feedback/${token}`).then((r) => r.data),
  send: (token: string, body: { rating: number; text: string; outlet_id: number | null; name: string; contact: string; website: string }) =>
    api.post<{ thanks: boolean; google_review_url: string | null }>(`/api/v1/public/feedback/${token}`, body).then((r) => r.data),
};

export const assistantApi = {
  chat: (message: string, history: { role: "user" | "assistant"; text: string }[]) =>
    api.post<{ answer: string }>("/api/v1/assistant/chat", { message, history }, { timeout: 90_000 }).then((r) => r.data),
};

export const billingApi = {
  status: () => api.get<BillingStatus>("/api/v1/billing").then((r) => r.data),
  pricing: () => api.get<PricingTable>("/api/v1/billing/pricing").then((r) => r.data),
  order: (outlets: number, months: number) => api.post<RazorpayOrder>("/api/v1/billing/order", { outlets, months }).then((r) => r.data),
  checkout: (outlets: number, months: number, details?: BillingDetails) =>
    api.post<{ checkout_url: string }>("/api/v1/billing/checkout", { outlets, months, ...details }).then((r) => r.data),
  receipt: (id: number) => api.get<Receipt>(`/api/v1/billing/receipts/${id}`).then((r) => r.data),
  confirm: (payment_id: string) => api.post<{ status: string; plan: string }>("/api/v1/billing/confirm", { payment_id }).then((r) => r.data),
  verify: (body: { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }) =>
    api.post("/api/v1/billing/verify", body).then((r) => r.data),
};

export const appApi = {
  overview: (outletId?: number) =>
    api.get<Overview>("/api/v1/dashboard/overview", { params: outletId ? { outlet_id: outletId } : {} }).then((r) => r.data),
  reviews: (params: { view: InboxView; q?: string; outlet_id?: number; page?: number }) =>
    api.get<ReviewPage>("/api/v1/reviews", { params: { page_size: 50, ...params } }).then((r) => r.data),
  updateReview: (id: number, body: { workflow_status?: WorkflowStatus; final_reply?: string }) =>
    api.patch<Review>(`/api/v1/reviews/${id}`, body).then((r) => r.data),
  addReview: (body: { text: string; rating: number; platform: Platform; outlet_id?: number }) =>
    api.post<{ id: number }>("/api/v1/reviews", body).then((r) => r.data),
  upload: (file: File, outletId?: number) => {
    const form = new FormData();
    form.append("file", file);
    if (outletId) form.append("outlet_id", String(outletId));
    return api.post<ImportBatch>("/api/v1/imports", form).then((r) => r.data);
  },
  screenshot: (file: File, platform: Platform, outletId?: number) => {
    const form = new FormData();
    form.append("file", file);
    form.append("platform", platform);
    if (outletId) form.append("outlet_id", String(outletId));
    return api.post<{ added: number; duplicates: number; reviews: { rating: number; text: string }[] }>("/api/v1/imports/screenshot", form).then((r) => r.data);
  },
  importOutlets: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post<{ added: string[]; updated: string[]; skipped: string[] }>("/api/v1/outlets/import", form).then((r) => r.data);
  },
  billingKey: () => api.post<{ key: string; endpoint: string }>("/api/v1/settings/billing-key").then((r) => r.data),
  competitors: (outletId: number, refresh = false) =>
    api.get<{ enabled: boolean; outlet?: string; where?: string; area_average?: number | null; fetched_at?: string;
      you?: { name: string; rating: number | null; reviews: number } | null;
      nearby?: { id: string; name: string; rating: number | null; reviews: number; address: string }[] }>(
      "/api/v1/competitors", { params: { outlet_id: outletId, refresh } }).then((r) => r.data),
  askGuests: (body: { numbers: string[]; outlet_id?: number; consent: boolean }) =>
    api.post<{ results: { phone: string; status: "sent" | "link" | "skipped_recent" | "invalid"; link: string | null }[]; sending_automatically: boolean }>("/api/v1/review-requests", body).then((r) => r.data),
  askStats: () => api.get<{ asked_30d: number; feedback_30d: number; sending_automatically: boolean }>("/api/v1/review-requests/stats").then((r) => r.data),
  batch: (id: number) => api.get<ImportBatch>(`/api/v1/imports/${id}`).then((r) => r.data),
  batches: () => api.get<ImportBatch[]>("/api/v1/imports").then((r) => r.data),
  templateUrl: `${API_URL}/api/v1/imports/template.csv`,
  connections: () => api.get<Connection[]>("/api/v1/connections").then((r) => r.data),
  notifications: () => api.get<NotificationList>("/api/v1/notifications").then((r) => r.data),
  readAll: () => api.post("/api/v1/notifications/read-all"),
  team: () => api.get<Team>("/api/v1/team").then((r) => r.data),
  invite: (email: string, role: "manager" | "agent", outlet_ids: number[] | null) =>
    api.post<TeamInvite>("/api/v1/team/invitations", { email, role, outlet_ids }).then((r) => r.data),
  cancelInvite: (id: number) => api.delete(`/api/v1/team/invitations/${id}`),
  changeRole: (membershipId: number, role: string) => api.patch(`/api/v1/team/members/${membershipId}`, { role }),
  setOutlets: (membershipId: number, outlet_ids: number[] | null) =>
    api.patch(`/api/v1/team/members/${membershipId}`, outlet_ids ? { outlet_ids } : { all_outlets: true }),
  googleStart: () => api.post<{ url: string }>("/api/v1/connections/google/start").then((r) => r.data),
  googleSync: () => api.post("/api/v1/connections/google/sync"),
  googleDisconnect: () => api.post("/api/v1/connections/google/disconnect"),
  postReply: (id: number, text: string) => api.post<Review>(`/api/v1/reviews/${id}/post-reply`, { text }).then((r) => r.data),
  removeMember: (membershipId: number) => api.delete(`/api/v1/team/members/${membershipId}`),
  outlets: () => api.get<Outlet[]>("/api/v1/outlets").then((r) => r.data),
  addOutlet: (body: Partial<OutletInput> & { name: string }) => api.post<Outlet>("/api/v1/outlets", body).then((r) => r.data),
  updateOutlet: (id: number, body: Partial<OutletInput> & { name: string }) => api.put<Outlet>(`/api/v1/outlets/${id}`, body).then((r) => r.data),
  removeOutlet: (id: number) => api.delete(`/api/v1/outlets/${id}`),
  settings: () => api.get<OrgSettings>("/api/v1/settings").then((r) => r.data),
  saveSettings: (body: Partial<OrgSettings>) => api.patch<OrgSettings>("/api/v1/settings", body).then((r) => r.data),
};

export const inviteApi = {
  info: (token: string) => api.get<InviteInfo>(`/api/v1/invitations/${token}`).then((r) => r.data),
  accept: (token: string, body: { full_name: string; password: string }) =>
    api.post<TokenResponse>(`/api/v1/invitations/${token}/accept`, body).then((r) => r.data),
};

export interface TestAccount { id: number; name: string; owner_email: string | null; reason: string; reviews: number; payments: number; created_at: string }
export interface BackupInfo { folder: string; count: number; latest: string | null; latest_at: string | null; latest_size_kb: number | null; hours_ago: number | null }

export interface RevenueMonth { month: string; label: string; collected: number; payments: number; expected: number }
export interface RevenueRow { org_id: number; restaurant: string; owner_email: string | null; ends_on: string; outlets: number; months: number; amount: number; kind: "renewal" | "trial" }
export interface RevenuePayment { id: number; invoice_no: string | null; bill_name: string | null; bill_gstin: string | null; paid_at: string; restaurant: string; amount: number; outlets: number | null; months: number | null; covers_until: string | null }
export interface Revenue {
  all_time: number; this_month: number; last_month: number; this_year: number; paying_customers: number; monthly_recurring: number;
  expected_next_30: number; expected_next_90: number; possible_from_trials: number;
  months: RevenueMonth[]; upcoming: RevenueRow[]; trials_ending: RevenueRow[]; recent: RevenuePayment[];
}

export const adminApi = {
  revenue: () => api.get<Revenue>("/api/v1/admin/revenue").then((r) => r.data),
  planMix: () => api.get<{ by_months: Record<string, number>; on_trial: number }>("/api/v1/admin/plan-mix").then((r) => r.data),
  monthlyReport: (month: string) => api.get<Blob>("/api/v1/admin/reports/monthly.xlsx", { params: { month }, responseType: "blob" }).then((r) => r.data),
  testimonials: () => api.get<Testimonial[]>("/api/v1/admin/testimonials").then((r) => r.data),
  addTestimonial: (b: TestimonialInput) => api.post<Testimonial>("/api/v1/admin/testimonials", b).then((r) => r.data),
  saveTestimonial: (id: number, b: TestimonialInput) => api.put<Testimonial>(`/api/v1/admin/testimonials/${id}`, b).then((r) => r.data),
  deleteTestimonial: (id: number) => api.delete(`/api/v1/admin/testimonials/${id}`),
  leads: () => api.get<Lead[]>("/api/v1/admin/leads").then((r) => r.data),
  mailbox: () => api.get<Mailbox>("/api/v1/admin/mailbox").then((r) => r.data),
  updateLead: (id: number, status: string) => api.patch<Lead>(`/api/v1/admin/leads/${id}`, { status }).then((r) => r.data),
  stats: () => api.get<AdminStats>("/api/v1/admin/stats").then((r) => r.data),
  orgs: () => api.get<AdminOrg[]>("/api/v1/admin/organizations").then((r) => r.data),
  updateOrg: (id: number, body: { plan?: string; is_suspended?: boolean }) =>
    api.patch<AdminOrg>(`/api/v1/admin/organizations/${id}`, body).then((r) => r.data),
  users: () => api.get<AdminUser[]>("/api/v1/admin/users").then((r) => r.data),
  events: () => api.get<AdminEvent[]>("/api/v1/admin/events").then((r) => r.data),
  launchCheck: () => api.get<{ key: string; label: string; ok: boolean; fix: string; required: boolean }[]>("/api/v1/admin/launch-check").then((r) => r.data),
  testEmail: () => api.post<{ sent: boolean }>("/api/v1/admin/test-email").then((r) => r.data),
  exportExcel: () => api.get<Blob>("/api/v1/admin/export.xlsx", { responseType: "blob" }).then((r) => r.data),
  testAccounts: () => api.get<TestAccount[]>("/api/v1/admin/test-accounts").then((r) => r.data),
  deleteTestAccounts: (ids: number[]) => api.post<{ deleted: number }>("/api/v1/admin/test-accounts/delete", { ids, confirm: "DELETE" }).then((r) => r.data),
  backups: () => api.get<BackupInfo>("/api/v1/admin/backups").then((r) => r.data),
  activity: () => api.get<ActivityItem[]>("/api/v1/admin/activity").then((r) => r.data),
  orgLog: (id: number) => api.get<{ at: string; kind: string; label: string; who: string | null; detail: string | null }[]>(`/api/v1/admin/organizations/${id}/log`).then((r) => r.data),
  activityOf: (kind: string) => api.get<ActivityItem[]>("/api/v1/admin/activity", { params: { kind } }).then((r) => r.data),
  updateUser: (id: number, is_active: boolean) => api.patch(`/api/v1/admin/users/${id}`, { is_active }),
};

export interface Mailbox {
  account: string;
  sender: string;
  boxes: { key: string; label: string; address: string; purpose: string; total: number; new: number; week: number; gmail_url: string }[];
  recent: { at: string; box: string; who: string | null; title: string; detail: string | null; status: string }[];
}

export interface AiAgent { key: string; name: string; role: string; sample: string; job: string; status: "working" | "approval" | "setup" | "off"; done: number; unit: string; extra?: string; link: string }
export interface AiMove { kind: string; title: string; why: string; link: string }
export interface AiCrisis { outlet: string; topic: string; count: number; severity: "critical" | "high"; likely_cause: string; examples: string[]; action: string }
export interface AiRecovery { review_id: number; guest: string; contact: string; rating: number; summary: string; outlet: string | null; date: string; status: "new" | "drafted" | "sent" | "returned"; code: string | null; message: string | null; whatsapp_url: string | null }
export interface AiRules { banned_words: string[]; escalate: string[]; avg_order_value: number; comeback_offer: string }
export interface AiStaff {
  as_of: string;
  agents: AiAgent[];
  roi: { reviews_read: number; replies_written: number; hours_saved: number; value_saved: number; revenue_at_risk: number; revenue_won_back: number; assumptions: string };
  moves: AiMove[];
  crises: AiCrisis[];
  recovery: AiRecovery[];
  rules: AiRules;
}

export const aiStaffApi = {
  get: () => api.get<AiStaff>("/api/v1/ai-staff").then((r) => r.data),
  saveRules: (rules: AiRules) => api.put<AiRules>("/api/v1/ai-staff/rules", rules).then((r) => r.data),
  draft: (reviewId: number) => api.post<{ code: string; message: string }>(`/api/v1/ai-staff/recovery/${reviewId}`).then((r) => r.data),
  mark: (reviewId: number, status: "sent" | "returned") => api.post(`/api/v1/ai-staff/recovery/${reviewId}/status`, { status }).then((r) => r.data),
};

export interface AdminChore { key: string; name: string; title: string; chore: string; before: string; now: string; needs_you: number; needs_label: string; done: number; done_label: string; link: string }
export const adminAutopilotApi = { get: () => api.get<{ as_of: string; chores: AdminChore[]; restaurants: number }>("/api/v1/admin/autopilot").then((r) => r.data) };
