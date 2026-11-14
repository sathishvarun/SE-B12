# Sathish CRM — API Contract (Phase 2)

> Single source of truth for request/response JSON shapes. Backend and frontend agents both follow this.
> Base URL: `/api/v1`. All JSON keys are **snake_case** on both sides (frontend TS types use the same snake_case names; no mapping layer).
> Dates: `date` fields are `"YYYY-MM-DD"`; datetimes are ISO 8601 strings with timezone. Money (`value`) is serialized as a **string** decimal, e.g. `"1500.00"` (frontend parses with `Number()` for display/sums).
> Errors: `{ "detail": string }` (validation errors use FastAPI's default 422 `{ "detail": [ {loc, msg, type} ] }`).
> Pagination: list endpoints take `?page=1&page_size=20` and return `Page<T>` = `{ items: T[], total: number, page: number, page_size: number }`.
> Auth: `Authorization: Bearer <access_token>` on every endpoint except the public ones marked (public).

---

## Auth — `/auth`

| Method | Path | Body | Response |
|---|---|---|---|
| POST | /auth/register (public, 5/min) | `{ email, password (min 8), full_name }` | 201 `TokenResponse` (409 if email exists) |
| POST | /auth/login (public, 5/min) | JSON `{ email, password }` | `TokenResponse` (401 bad credentials, 403 inactive) |
| POST | /auth/refresh (public) | `{ refresh_token }` | `TokenResponse` (old refresh token revoked — rotation) |
| POST | /auth/logout | `{ refresh_token }` | 204 |
| GET | /auth/me | – | `UserResponse` |
| PUT | /auth/me | `{ full_name?, current_password?, new_password? }` (new_password requires current_password unless user has no password, i.e. Google-only) | `UserResponse` |
| POST | /auth/forgot-password (public, 3/min) | `{ email }` | 200 `{ "message": "If that email exists, a reset link has been sent." }` |
| POST | /auth/reset-password (public) | `{ token, new_password }` | 200 `{ "message": "Password updated." }` (400 invalid/expired) |
| GET | /auth/google (public) | – | 307 redirect to Google (signed `state`) |
| GET | /auth/google/callback (public) | `?code&state` | 307 redirect to `${FRONTEND_URL}/oauth/callback#access_token=...&refresh_token=...` ; on error `${FRONTEND_URL}/login?error=oauth_failed` |

```ts
TokenResponse = { access_token: string; refresh_token: string; token_type: "bearer" }
UserResponse  = { id: number; email: string; full_name: string | null; is_active: boolean; is_verified: boolean;
                  is_admin: boolean; oauth_provider: "google" | null; has_password: boolean;
                  plan: "free" | "pro"; created_at: string }
```
Reset link emailed: `${FRONTEND_URL}/reset-password?token=<raw token>`.

---

## Contacts — `/contacts`, `/tags`

```ts
Tag = { id: number; name: string }
Contact = { id: number; name: string; email: string | null; phone: string | null; company: string | null;
            address: string | null; notes: string | null; tags: Tag[]; created_at: string; updated_at: string }
ContactDetail = Contact & { deals: DealSummary[]; tasks: Task[]; attachments: Attachment[] }
ContactInput = { name: string; email?: string | null; phone?: string | null; company?: string | null;
                 address?: string | null; notes?: string | null; tag_ids?: number[] }
```
| Method | Path | Body / Query | Response |
|---|---|---|---|
| GET | /contacts | `?search&tag_id&page&page_size` | `Page<Contact>` (ordered by name) |
| GET | /contacts/options | – | `{ id, name, company }[]` (all contacts, for select dropdowns) |
| POST | /contacts | `ContactInput` | 201 `Contact` (402 if free plan limit reached) |
| GET | /contacts/{id} | – | `ContactDetail` |
| PUT | /contacts/{id} | `ContactInput` | `Contact` |
| DELETE | /contacts/{id} | – | 204 |
| GET | /tags | – | `Tag[]` |
| POST | /tags | `{ name }` | 201 `Tag` (409 duplicate) |

---

## Leads — `/leads`

```ts
LeadSource = "website" | "referral" | "social" | "other"
LeadStatus = "new" | "contacted" | "qualified" | "lost" | "converted"
Lead = { id: number; name: string; email: string | null; phone: string | null; company: string | null;
         source: LeadSource; status: LeadStatus; notes: string | null; converted_contact_id: number | null;
         created_at: string; updated_at: string }
LeadInput = { name: string; email?; phone?; company?; source?: LeadSource; notes? }
```
| Method | Path | Body / Query | Response |
|---|---|---|---|
| GET | /leads | `?status&source&search&page&page_size` | `Page<Lead>` (newest first) |
| POST | /leads | `LeadInput` | 201 `Lead` |
| GET | /leads/{id} | – | `Lead` |
| PUT | /leads/{id} | `LeadInput` | `Lead` |
| PATCH | /leads/{id}/status | `{ status }` (not "converted" → 400) | `Lead` |
| DELETE | /leads/{id} | – | 204 |
| POST | /leads/{id}/convert | `{ deal_title: string; deal_value: string|number; expected_close_date?: string|null }` | 201 `{ lead: Lead; contact: Contact; deal: Deal }` (409 if already converted) |

---

## Deals — `/deals`

```ts
DealStage = "prospect" | "proposal" | "negotiation" | "won" | "lost"
DealSummary = { id: number; title: string; value: string; currency: string; stage: DealStage;
                expected_close_date: string | null }
Deal = DealSummary & { contact_id: number; contact: { id: number; name: string; company: string | null };
                       position: number; notes: string | null; closed_at: string | null;
                       created_at: string; updated_at: string }
DealDetail = Deal & { tasks: Task[]; attachments: Attachment[] }
DealInput = { title: string; contact_id: number; value: string|number; currency?: string; stage?: DealStage;
              expected_close_date?: string|null; notes?: string|null }
DealBoard = { prospect: Deal[]; proposal: Deal[]; negotiation: Deal[]; won: Deal[]; lost: Deal[] }  // each ordered by position
```
| Method | Path | Body / Query | Response |
|---|---|---|---|
| GET | /deals | `?stage&contact_id&page&page_size` | `Page<Deal>` |
| GET | /deals/board | – | `DealBoard` |
| POST | /deals | `DealInput` | 201 `Deal` (404 if contact not owned; 402 free-plan open-deal limit) |
| GET | /deals/{id} | – | `DealDetail` |
| PUT | /deals/{id} | `DealInput` | `Deal` |
| PATCH | /deals/{id}/stage | `{ stage: DealStage; position: number }` | `Deal` (sets/clears closed_at) |
| DELETE | /deals/{id} | – | 204 |

(Note: board is `/deals/board`, not `?view=board`.)

---

## Tasks — `/tasks`

```ts
TaskPriority = "low" | "medium" | "high"
TaskStatus = "pending" | "done"
Task = { id: number; title: string; description: string | null; due_date: string | null; priority: TaskPriority;
         status: TaskStatus; contact_id: number | null; lead_id: number | null; deal_id: number | null;
         linked_type: "contact" | "lead" | "deal" | null; linked_name: string | null;
         is_overdue: boolean; completed_at: string | null; created_at: string; updated_at: string }
TaskInput = { title: string; description?; due_date?: string|null; priority?: TaskPriority;
              contact_id?: number|null; lead_id?: number|null; deal_id?: number|null }  // at most one link → else 400
```
| Method | Path | Body / Query | Response |
|---|---|---|---|
| GET | /tasks | `?view=today|upcoming|overdue|done&contact_id&lead_id&deal_id&page&page_size` (no view = all pending) | `Page<Task>` (by due_date asc, nulls last; done: completed_at desc) |
| POST | /tasks | `TaskInput` | 201 `Task` |
| GET | /tasks/{id} | – | `Task` |
| PUT | /tasks/{id} | `TaskInput` | `Task` |
| PATCH | /tasks/{id}/complete | – | `Task` |
| DELETE | /tasks/{id} | – | 204 |

Views: today = pending & due_date == today; upcoming = pending & due_date > today (or null); overdue = pending & due_date < today; done = status done.

---

## Attachments — `/attachments`

```ts
Attachment = { id: number; filename: string; content_type: string; size_bytes: number;
               contact_id: number | null; deal_id: number | null; created_at: string }
```
| Method | Path | Body | Response |
|---|---|---|---|
| POST | /attachments | multipart: `file`, and `contact_id` OR `deal_id` (form fields) | 201 `Attachment` (400 bad type, 413 too large) |
| GET | /attachments/{id} | – | file download (frontend fetches as blob via axios with auth header) |
| DELETE | /attachments/{id} | – | 204 |

Allowed: pdf, png, jpg, jpeg, docx, xlsx; max 10 MB.

---

## Billing — `/billing`

```ts
Subscription = { plan: "free" | "pro"; status: "active" | "trialing" | "past_due" | "cancelled";
                 current_period_end: string | null; limits: { max_contacts: number | null; max_open_deals: number | null };
                 usage: { contacts: number; open_deals: number } }
```
| Method | Path | Body | Response |
|---|---|---|---|
| GET | /billing/subscription | – | `Subscription` (limits null on pro) |
| POST | /billing/checkout | – | `{ checkout_url: string }` (409 if already pro) |
| POST | /billing/cancel | – | `Subscription` |
| POST | /billing/webhook (public, signature verified) | Dodo payload | 200 `{ "received": true }` |

Checkout return URL: `${FRONTEND_URL}/billing?checkout=success`.

---

## Dashboard — `/dashboard`

```ts
DashboardSummary = { contacts: number; open_leads: number; open_deals: number; open_pipeline_value: string;
                     tasks_due_today: number; tasks_overdue: number }
DashboardAnalytics = {
  pipeline_by_stage: { stage: DealStage; count: number; value: string }[];      // all 5 stages, zeros included
  deals_won_by_month: { month: string /* "YYYY-MM" */; count: number; value: string }[];  // last 6 months incl. current, zeros included
  lead_conversion_rate: number;   // 0..1 = converted / total leads (0 when no leads)
  leads_by_source: { source: LeadSource; count: number }[] }
```
| GET | /dashboard/summary | `DashboardSummary` |
| GET | /dashboard/analytics | `DashboardAnalytics` |

---

## Admin — `/admin` (403 unless is_admin)

```ts
AdminUser = { id: number; email: string; full_name: string | null; is_active: boolean; is_admin: boolean;
              plan: "free" | "pro"; created_at: string }
AdminStats = { total_users: number; active_users: number; pro_subscriptions: number; signups_last_30_days: number;
               total_contacts: number; total_deals: number }
```
| GET | /admin/users | `?search&page&page_size` | `Page<AdminUser>` |
| PUT | /admin/users/{id} | `{ is_active?: boolean; is_admin?: boolean }` | `AdminUser` (400 if admin edits own is_active/is_admin) |
| GET | /admin/stats | – | `AdminStats` |
