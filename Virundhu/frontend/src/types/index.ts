export type Sentiment = "positive" | "neutral" | "negative";
export type Urgency = "low" | "medium" | "high";
export type Language = "english" | "tamil" | "tanglish" | "other";
export type Category =
  | "food_quality" | "delivery" | "price" | "staff"
  | "packaging" | "hygiene" | "app" | "other";
export type Platform = "google" | "zomato" | "swiggy" | "direct" | "other" | "tripadvisor" | "instagram" | "facebook";
export type Role = "owner" | "manager" | "agent";
export type WorkflowStatus = "new" | "in_progress" | "replied" | "ignored";
export type InboxView = "all" | "clock" | "today" | "week" | "replied";

export interface PublicConfig {
  company?: { name: string; email: string | null; phone: string | null; address: string | null; grievance_officer: string; parent?: string | null; demo_email?: string | null; founded?: string | null; parent_gstin?: string | null };
  app_name: string;
  google_enabled: boolean;
  google_client_id?: string | null;
  payments_enabled: boolean;
  razorpay_key_id: string | null;
  ai_ready: boolean;
  llm_provider: "anthropic" | "openai";
}

export interface Organization { id: number; name: string; slug: string; plan: string; is_demo: boolean; city: string | null; trial_ends_at?: string | null; is_suspended?: boolean; locked_since?: string | null }

export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  is_superadmin: boolean;
  role: Role | null;
  organization: Organization | null;
  outlet_names?: string[] | null;
  organizations?: { id: number; name: string; city: string | null; role: Role; plan: string }[];
  two_step?: boolean;
  two_step_required?: boolean;
}

export interface TokenResponse { access_token: string; user: CurrentUser }

export interface Analysis {
  sentiment: Sentiment | null;
  category: Category | null;
  urgency: Urgency | null;
  language: Language | null;
  summary: string | null;
  suggested_reply: string | null;
  safety_override: boolean;
  food_safety: boolean;
}

export interface Review {
  id: number;
  external_id: string;
  platform: Platform;
  rating: number;
  review_date: string;
  review_text: string;
  outlet_id: number | null;
  outlet_name: string | null;
  workflow_status: WorkflowStatus;
  final_reply: string | null;
  is_sample: boolean;
  reply_posted_at: string | null;
  can_post_to_google: boolean;
  analysis: Analysis | null;
  auto_replied?: boolean;
  guest_name?: string | null;
  guest_contact?: string | null;
  reply_due_at?: string | null; // reply promise: bad reviews on the clock
  replied_at?: string | null;
}

export interface ReplyPromise {
  target_minutes: number;
  reminders_on: boolean;
  bad: number;
  within: number;
  late: number;
  missed: number;
  pct_within: number | null;
  median_minutes: number | null;
  waiting: number;
  overdue: number;
  days: number;
}

export interface ReviewPage {
  items: Review[];
  total: number;
  page: number;
  page_size: number;
  counts: Record<InboxView, number>;
}

export interface TryResult {
  sentiment: Sentiment;
  category: Category;
  urgency: Urgency;
  language: Language;
  summary: string;
  suggested_reply: string;
  safety_override: boolean;
  food_safety: boolean;
}

export interface Overview {
  promise?: ReplyPromise | null;
  kpis: {
    reviews_week: number;
    reviews_prev_week: number;
    positive_pct: number;
    positive_pct_prev: number;
    avg_rating: number | null;
    avg_rating_prev: number | null;
    urgent_pending: number;
    reply_rate_30d: number;
  };
  trend: { week_start: string; positive: number; neutral: number; negative: number }[];
  categories: { category: Category; count: number }[];
  outlets: { outlet_id: number; name: string; city: string | null; reviews: number; avg_rating: number | null; negative_pct: number; urgent_pending: number }[];
  platforms: { platform: Platform; count: number }[];
  urgent: { id: number; platform: Platform; rating: number; review_date: string; review_text: string; summary: string | null; category: Category | null; outlet_name: string | null }[];
  as_of: string;
}

export interface ImportBatch {
  id: number; filename: string; status: "queued" | "processing" | "completed" | "failed";
  total_rows: number; valid_rows: number; duplicate_rows: number; invalid_rows: number; analyzed_rows: number;
  errors: { row: number; reason: string }[] | null;
  created_at?: string | null; source?: "file" | "paste" | "screenshot";
}

export interface Connection {
  provider: "google" | "zomato" | "swiggy"; status: string; official_api: boolean;
  account_email: string | null; locations: string[]; last_synced_at: string | null; last_error: string | null;
  note: string; available?: boolean;
}

export interface NotificationItem { id: number; review_id: number | null; severity: string; title: string; body: string; created_at: string; read: boolean }
export interface NotificationList { unread: number; items: NotificationItem[] }

export interface TeamMember { membership_id: number; user_id: number; full_name: string; email: string; role: Role; is_you: boolean; outlet_ids: number[] | null }
export interface TeamInvite { id: number; email: string; role: Role; expires_at: string; outlet_ids?: number[] | null; invite_url?: string | null }
export interface Team { members: TeamMember[]; invitations: TeamInvite[]; seats: number }
export interface Outlet {
  id: number; name: string; area: string | null; city: string | null; district?: string | null; address?: string | null; pincode?: string | null;
  phone?: string | null; manager_name?: string | null; manager_phone?: string | null; manager_email?: string | null;
  google_maps_url?: string | null; zomato_url?: string | null; swiggy_url?: string | null; feedback_url?: string | null;
  on_google_maps?: boolean; directions_url?: string | null; map_embed_url?: string | null;
  google_rating?: number | null; google_rating_count?: number | null;
}
export type OutletInput = Omit<Outlet, "id" | "feedback_url">;
export interface OrgSettings { name: string; city: string | null; reply_tone: "warm" | "professional" | "short"; reply_signature: string | null; alert_emails: string[]; plan: string; trial_ends_at: string | null;
  autopilot_enabled: boolean; autopilot_min_rating: number; google_connected: boolean; google_review_url: string | null;
  feedback_url: string; whatsapp_numbers: string[]; whatsapp_available: boolean;
  owner_phone?: string | null; business_type?: string | null; cuisine?: string | null; gstin?: string | null; head_office?: string | null;
  outlets_declared?: number | null; holding_reply_hours?: number | null; reply_target_minutes?: number | null; weekly_summary?: boolean;
  ask_after_bill?: boolean; has_billing_key?: boolean }
export interface InviteInfo { email: string; role: Role; organization_name: string; has_account: boolean }

export interface AdminStats {
  restaurants: number; paying: number; trialing: number; users: number;
  reviews_today: number; reviews_7d: number; reviews_30d: number; urgent_open: number;
  ai_cost_month_inr: number; mrr_inr: number; collected_month_inr: number; by_platform_30d: Record<Platform, number>;
  daily: { day: string; google: number; zomato: number; swiggy: number; direct: number; other: number }[];
}
export interface AdminOrg {
  id: number; name: string; city: string | null; plan: string; is_demo: boolean; is_suspended: boolean;
  trial_ends_at: string | null; created_at: string; users: number; outlets: number; reviews_30d: number;
  urgent_open: number; ai_cost_month_inr: number; last_review: string | null; owner_email: string | null;
}
export interface AdminUser { id: number; full_name: string; email: string; is_active: boolean; is_superadmin: boolean; restaurants: string[]; last_login_at: string | null; created_at: string }

export interface AdminEvent { id: string; kind: string; title: string; body: string; at: string; organization_id: number | null }
export interface ActivityItem { id: number; kind: string; label: string; restaurant: string | null; user_email: string | null; detail: string | null; created_at: string }
