# PRP: Sathish CRM

> Implementation blueprint for parallel agent execution

---

## METADATA

| Field | Value |
|-------|-------|
| **Product** | Sathish CRM |
| **Type** | SaaS |
| **Version** | 1.0 |
| **Created** | 2026-11-14 |
| **Complexity** | High (10 modules, 10 models, 48 endpoints, 26 pages, 3 external integrations) |
| **Source** | INITIAL.md |

---

## PRODUCT OVERVIEW

**Description:** A simple CRM that helps sellers track their customers, leads, deals and follow-ups in one place.
Sellers capture leads, convert them into contacts and deals, move deals through a kanban pipeline, and get
email reminders for follow-ups.

**Target User:** Sellers and small sales teams who currently track customers in spreadsheets, notebooks or WhatsApp.

**Value Proposition:** Sellers lose sales when they forget to follow up or lose track of who is where in the
buying process. Sathish CRM gives them one simple place to see every customer, every open deal and every
follow-up due today, without the complexity and price of enterprise CRMs.

**MVP Scope:**
- [ ] Registration and login (email/password + Google OAuth)
- [ ] Contacts: CRUD, search, tags
- [ ] Leads: CRUD, status changes, convert to Contact + Deal
- [ ] Deals: kanban pipeline with drag-and-drop stages
- [ ] Tasks & follow-ups with Today / Upcoming / Overdue views
- [ ] File uploads on contacts and deals
- [ ] Email notifications (welcome, password reset, task reminders)
- [ ] Dashboard with analytics charts
- [ ] Dodo Payments subscription billing (Free / Pro)
- [ ] Admin panel

---

## TECH STACK

| Layer | Technology | Skill Reference |
|-------|------------|-----------------|
| Backend | FastAPI + Python 3.11+ | skills/BACKEND.md |
| Frontend | React + TypeScript + Vite | skills/FRONTEND.md |
| Database | PostgreSQL + SQLAlchemy 2.0 + Alembic | skills/DATABASE.md |
| Auth | JWT (python-jose) + bcrypt (passlib) + Google OAuth 2.0 | skills/BACKEND.md |
| UI | Tailwind CSS + shadcn/ui + Framer Motion | skills/FRONTEND.md (Tailwind path) |
| Drag & drop | @dnd-kit/core | - |
| Charts | Recharts | - |
| Data fetching | @tanstack/react-query + axios | skills/FRONTEND.md |
| Forms | react-hook-form + zod | - |
| Payments | Dodo Payments (REST API + webhooks) | - |
| Email | SMTP via `fastapi-mail` (or `smtplib` in a service) | - |
| Scheduled jobs | APScheduler (daily task-reminder job) | - |
| Rate limiting | slowapi | - |
| Testing | pytest + pytest-cov + httpx TestClient; Vitest + React Testing Library | skills/TESTING.md |
| Deployment | Docker + docker-compose + GitHub Actions | skills/DEPLOYMENT.md |

**UI note:** `skills/FRONTEND.md` shows both Chakra and Tailwind setups. This project uses **Tailwind + shadcn/ui only**.
Do not install `@chakra-ui/*` or `@emotion/*`.

---

## DATABASE MODELS

All tables have `id` (int PK), `created_at`, `updated_at` (except join tables). All CRM tables have
`user_id` FK → `users.id` (ON DELETE CASCADE) and an index on `user_id`.

### User (`users`)
- id, email (unique, indexed), hashed_password (nullable for OAuth-only users), full_name, is_active (default true),
  is_verified (default false), is_admin (default false), oauth_provider (nullable: "google"), created_at, updated_at
- Relationships: contacts, leads, deals, tasks, attachments, tags, refresh_tokens, subscription (one-to-one)

### RefreshToken (`refresh_tokens`)
- id, user_id FK, token (unique, indexed — store a SHA-256 hash, not the raw token), expires_at, revoked (default false), created_at

### PasswordResetToken (`password_reset_tokens`)
- id, user_id FK, token_hash (unique), expires_at (1 hour), used (default false), created_at

### Contact (`contacts`)
- id, user_id FK, name (required), email (nullable), phone, company, address, notes (text), created_at, updated_at
- Relationships: tags (many-to-many via contact_tags), deals, tasks, attachments
- Index: (user_id, name)

### Tag (`tags`)
- id, user_id FK, name
- Unique constraint: (user_id, name)

### ContactTag (`contact_tags`)
- contact_id FK (CASCADE), tag_id FK (CASCADE); composite PK

### Lead (`leads`)
- id, user_id FK, name, email, phone, company, source (enum: website | referral | social | other),
  status (enum: new | contacted | qualified | lost | converted, default new), notes,
  converted_contact_id FK → contacts.id (nullable, SET NULL), created_at, updated_at
- Index: (user_id, status)

### Deal (`deals`)
- id, user_id FK, contact_id FK → contacts.id (required, CASCADE), title, value (Numeric(12,2), >= 0),
  currency (char 3, default "INR"), stage (enum: prospect | proposal | negotiation | won | lost, default prospect),
  position (int, order within a kanban column), expected_close_date (date, nullable), notes,
  closed_at (nullable), created_at, updated_at
- Index: (user_id, stage)

### Task (`tasks`)
- id, user_id FK, title, description, due_date (date), priority (enum: low | medium | high, default medium),
  status (enum: pending | done, default pending), contact_id / lead_id / deal_id (all nullable FK, SET NULL),
  reminder_sent (default false), completed_at (nullable), created_at, updated_at
- Check constraint: at most one of contact_id / lead_id / deal_id is non-null
- Index: (user_id, status, due_date)

### Attachment (`attachments`)
- id, user_id FK, contact_id FK (nullable, CASCADE), deal_id FK (nullable, CASCADE), filename (original, display only),
  content_type, size_bytes, storage_path (generated UUID name), created_at
- Check constraint: exactly one of contact_id / deal_id is non-null

### Subscription (`subscriptions`)
- id, user_id FK (unique), dodo_customer_id, dodo_subscription_id (unique, nullable), plan (enum: free | pro, default free),
  status (enum: active | trialing | past_due | cancelled, default active), current_period_end (nullable), created_at, updated_at
- A free Subscription row is created for every new user at registration

**Model count:** 11 (User, RefreshToken, PasswordResetToken, Contact, Tag, ContactTag, Lead, Deal, Task, Attachment, Subscription)

---

## SHARED BACKEND CONVENTIONS

- Prefix all routers with `/api/v1`. `GET /health` stays unprefixed.
- `get_current_user` dependency on every CRM endpoint; `get_current_admin` for `/admin/*`.
- **Ownership rule:** every service function takes `user_id` and filters by it. A record belonging to another
  seller returns **404**, never 403, so IDs can't be probed.
- List endpoints accept `page` (default 1) and `page_size` (default 20, max 100) and return
  `{ items: [...], total: int, page: int, page_size: int }`.
- Errors return `{ "detail": "message" }` (FastAPI default).
- Follow the skills' pattern (sync SQLAlchemy `Session` via `Depends(get_db)`). Keep slow I/O (SMTP, Dodo API,
  file writes) in services; email sending goes through FastAPI `BackgroundTasks`.
- `logging` only, no `print()`. Secrets only from `config.py` (pydantic-settings reading env vars).

---

## MODULES

### Module 1: Authentication
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Create account (+ free subscription, welcome email). Rate limited 5/min |
| POST | /api/v1/auth/login | Email/password → access + refresh token. Rate limited 5/min |
| POST | /api/v1/auth/refresh | Rotate refresh token, return new access token |
| POST | /api/v1/auth/logout | Revoke refresh token |
| GET | /api/v1/auth/me | Current user profile |
| PUT | /api/v1/auth/me | Update full_name / password |
| POST | /api/v1/auth/forgot-password | Send reset link (always returns 200, even for unknown email). Rate limited 3/min |
| POST | /api/v1/auth/reset-password | Reset password using token |
| GET | /api/v1/auth/google | Redirect to Google with signed `state` |
| GET | /api/v1/auth/google/callback | Verify `state`, exchange code, create/link user, redirect to frontend with tokens |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /login | LoginPage | LoginForm, GoogleButton |
| /register | RegisterPage | RegisterForm, GoogleButton |
| /forgot-password | ForgotPasswordPage | ForgotPasswordForm |
| /reset-password | ResetPasswordPage | ResetPasswordForm |
| /profile | ProfilePage | ProfileForm, ChangePasswordForm |

Plus: `AuthContext`, `ProtectedRoute`, `AdminRoute`, axios interceptor that refreshes the access token on 401 once.

---

### Module 2: Contacts / Customers
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/contacts | List (query: `search`, `tag_id`, pagination) |
| POST | /api/v1/contacts | Create (with `tag_ids`) |
| GET | /api/v1/contacts/{id} | Detail incl. tags, deals, tasks, attachments |
| PUT | /api/v1/contacts/{id} | Update |
| DELETE | /api/v1/contacts/{id} | Delete (cascades deals and attachments) |
| GET | /api/v1/tags | List seller's tags |
| POST | /api/v1/tags | Create tag (409 if name exists) |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /contacts | ContactsListPage | ContactsTable, SearchInput, TagFilter, Pagination, EmptyState |
| /contacts/new | ContactCreatePage | ContactForm, TagMultiSelect |
| /contacts/:id | ContactDetailPage | ContactInfoCard, LinkedDealsList, LinkedTasksList, AttachmentsPanel |
| /contacts/:id/edit | ContactEditPage | ContactForm |

---

### Module 3: Leads
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/leads | List (query: `status`, `source`, `search`, pagination) |
| POST | /api/v1/leads | Create |
| GET | /api/v1/leads/{id} | Detail |
| PUT | /api/v1/leads/{id} | Update |
| PATCH | /api/v1/leads/{id}/status | Change status (cannot set `converted` directly) |
| DELETE | /api/v1/leads/{id} | Delete |
| POST | /api/v1/leads/{id}/convert | Body: `{ deal_title, deal_value, expected_close_date? }`. Creates Contact + Deal in **one transaction**, sets lead status `converted`. 409 if already converted |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /leads | LeadsListPage | LeadsTable, StatusBadge, StatusFilter, SourceFilter |
| /leads/new | LeadCreatePage | LeadForm |
| /leads/:id | LeadDetailPage | LeadInfoCard, StatusSelect, ConvertLeadDialog |
| /leads/:id/edit | LeadEditPage | LeadForm |

---

### Module 4: Deals / Pipeline
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/deals | List (query: `stage`, `contact_id`); unpaginated board mode with `?view=board` returns deals grouped by stage |
| POST | /api/v1/deals | Create (contact must belong to seller, else 404) |
| GET | /api/v1/deals/{id} | Detail incl. contact, tasks, attachments |
| PUT | /api/v1/deals/{id} | Update |
| PATCH | /api/v1/deals/{id}/stage | Body: `{ stage, position }`. Sets `closed_at` on won/lost, clears it otherwise |
| DELETE | /api/v1/deals/{id} | Delete |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /deals | DealsBoardPage | KanbanBoard, KanbanColumn (with stage total value), DealCard (dnd-kit) |
| /deals/new | DealCreatePage | DealForm, ContactSelect |
| /deals/:id | DealDetailPage | DealInfoCard, StageBadge, LinkedTasksList, AttachmentsPanel |
| /deals/:id/edit | DealEditPage | DealForm |

Drag-and-drop uses optimistic update via react-query; roll back and show a toast on API error.

---

### Module 5: Tasks & Follow-ups
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/tasks | List (query: `view=today|upcoming|overdue|done`, `contact_id`, `lead_id`, `deal_id`, pagination) |
| POST | /api/v1/tasks | Create (linked record must belong to seller; at most one link) |
| GET | /api/v1/tasks/{id} | Detail |
| PUT | /api/v1/tasks/{id} | Update (changing `due_date` resets `reminder_sent`) |
| PATCH | /api/v1/tasks/{id}/complete | Mark done, set `completed_at` |
| DELETE | /api/v1/tasks/{id} | Delete |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /tasks | TasksPage | Tabs (Today / Upcoming / Overdue / Done), TaskItem, PriorityBadge, CompleteCheckbox |
| /tasks/new | TaskCreatePage | TaskForm, LinkedRecordSelect |
| /tasks/:id/edit | TaskEditPage | TaskForm |

---

### Module 6: File Uploads
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/attachments | Multipart: `file` + `contact_id` or `deal_id`. Max 10 MB; types: pdf, png, jpg/jpeg, docx, xlsx (check extension **and** content type) |
| GET | /api/v1/attachments/{id} | Download (`FileResponse`, `Content-Disposition: attachment`) |
| DELETE | /api/v1/attachments/{id} | Delete DB row and file |

Storage: `services/storage.py` with a local-disk implementation writing to `UPLOAD_DIR/<user_id>/<uuid>.<ext>`.
Keep the interface small (`save`, `open`, `delete`) so an S3 version can be added post-MVP.

**Frontend:** `AttachmentsPanel` component (upload dropzone, file list, download, delete) used on contact and deal detail pages.

---

### Module 7: Billing (Dodo Payments)
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/billing/checkout | Create Dodo Payments checkout for the Pro product; return `checkout_url` |
| GET | /api/v1/billing/subscription | Current plan + status |
| POST | /api/v1/billing/cancel | Cancel Pro subscription via Dodo API |
| POST | /api/v1/billing/webhook | **No auth.** Verify webhook signature with `DODO_PAYMENTS_WEBHOOK_SECRET`; reject invalid with 401. Idempotent: handle subscription active / renewed / cancelled / failed events by updating Subscription |

**Rules:**
- Subscription plan/status changes **only** through verified webhooks (checkout redirect alone never upgrades).
- Free plan limit (enforced in services): max 100 contacts and 20 open deals; return 402 with a clear message when exceeded.
- Wrap the Dodo API in `services/dodo_payments.py` so tests can mock it. Confirm exact request/webhook formats against
  the current Dodo Payments docs during implementation.

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /pricing | PricingPage (public) | PlanCard (Free / Pro) |
| /billing | BillingPage | CurrentPlanCard, UpgradeButton, CancelSubscriptionDialog |

---

### Module 8: Email Notifications
**Agents:** BACKEND-AGENT

**Service:** `services/email.py` with `send_email(to, subject, html)`; templates in `app/templates/email/`.
| Email | Trigger |
|-------|---------|
| Welcome | After register (BackgroundTasks) |
| Password reset | `/auth/forgot-password` |
| Task reminder | Daily APScheduler job at 08:00: tasks with `status=pending`, `due_date <= today`, `reminder_sent=false` → one digest email per seller, then set `reminder_sent=true` |
| Subscription change | Dodo webhook: upgraded / cancelled / payment failed |

When `SMTP_HOST` is empty (local dev), log the email instead of sending.

---

### Module 9: Dashboard & Analytics
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/dashboard/summary | `{ contacts, open_leads, open_deals, open_pipeline_value, tasks_due_today, tasks_overdue }` |
| GET | /api/v1/dashboard/analytics | `{ pipeline_by_stage[], deals_won_by_month[] (last 6 months), lead_conversion_rate, leads_by_source[] }` — computed with SQL aggregates (GROUP BY), not Python loops |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /dashboard | DashboardPage | StatCard ×4, PipelineByStageChart, DealsWonChart, LeadsBySourceChart, TodayTasksList |
| /settings | SettingsPage | Settings tabs: Profile link, Billing link, Account (delete account) |

---

### Module 10: Admin Panel
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/admin/users | List all users (search, pagination) with plan |
| PUT | /api/v1/admin/users/{id} | Update `is_active` / `is_admin` (admin cannot deactivate themselves) |
| GET | /api/v1/admin/stats | Total users, active Pro subscriptions, signups last 30 days, total contacts/deals |

All return 403 for non-admins. First admin is created with a CLI script: `python -m app.scripts.make_admin <email>`.

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /admin | AdminDashboardPage | StatCard grid |
| /admin/users | AdminUsersPage | UsersTable, ActiveToggle |

---

### Shared Frontend Layout
- `AppLayout`: sidebar (Dashboard, Contacts, Leads, Deals, Tasks, Settings; Admin if `is_admin`), top bar with user menu
- shadcn/ui components to add: button, input, textarea, label, form, select, dialog, dropdown-menu, table, tabs,
  badge, card, toast (sonner), skeleton, checkbox, avatar
- `types/` holds one interface file per module mirroring backend schemas (no `any`)
- `services/api.ts` axios instance using `import.meta.env.VITE_API_URL`; one service file per module

---

## PHASE EXECUTION PLAN

**Phase 1: Foundation (4 agents in parallel)**
- DATABASE-AGENT: `database.py`, all 11 models, `models/__init__.py`, Alembic config + initial migration
- BACKEND-AGENT: `main.py` (CORS, routers, `/health`, slowapi), `config.py`, `requirements.txt`, folder structure, `auth/` security helpers (hash, JWT)
- FRONTEND-AGENT: Vite + React + TS (strict), Tailwind + shadcn/ui init, router, `AppLayout`, `api.ts`, `AuthContext` skeleton, ESLint + type-check scripts
- DEVOPS-AGENT: `docker-compose.yml` (postgres, backend, frontend), Dockerfiles, `.env.example`, GitHub Actions CI (lint, type-check, test)

**Validation Gate 1:** `pip install -r requirements.txt`, `alembic upgrade head`, `npm install`, `docker-compose config`

**Phase 2: Modules (backend + frontend parallel per module)**
Order matters where modules depend on each other:
- 2a: Auth module (everything depends on it)
- 2b (parallel): Contacts, Leads, Tasks, Email service, Billing
- 2c (parallel, need Contacts): Deals, File Uploads, Lead → convert
- 2d (parallel, need all CRM data): Dashboard & Analytics, Admin Panel, task-reminder job

Frontend agents can build against the endpoint tables in this PRP (the API contract) while backend is in progress.

**Validation Gate 2:** `ruff check backend/`, `mypy backend/app`, `npm run lint`, `npm run type-check`

**Phase 3: Quality (3 agents in parallel)**
- TEST-AGENT: pytest (each module: happy path, validation errors, **cross-seller access returns 404**, admin 403, webhook signature), Vitest + RTL for forms, kanban and auth flow; 80%+ backend coverage
- REVIEW-AGENT: Security audit (ownership filters, upload validation, webhook verification, rate limits, secrets), N+1 query check
- RESEARCH-AGENT: Validate Dodo Payments API/webhook usage and Google OAuth flow against current docs

> Note: `agents/` currently only defines ORCHESTRATOR, DATABASE, BACKEND and FRONTEND. DEVOPS, TEST, REVIEW and
> RESEARCH work runs as general-purpose agents using `skills/DEPLOYMENT.md` and `skills/TESTING.md`.

**Final Validation:** Full test suite, docker build, health checks

---

## VALIDATION GATES

| Gate | Commands |
|------|----------|
| 1 | `alembic upgrade head`, `npm install`, `docker-compose config` |
| 2 | `ruff check backend/`, `npm run lint`, `npm run type-check` |
| 3 | `pytest --cov=app --cov-fail-under=80`, `npm test` |
| Final | `docker-compose up -d`, `curl localhost:8000/health`, open `localhost:5173` and log in |

---

## ACCEPTANCE CRITERIA CHECKLIST

Copied from INITIAL.md — every item must pass before the build is done.

- **Auth:** register, login, Google sign-in, password reset, token refresh, protected routes redirect to /login
- **Contacts:** CRUD, search, tag filter, detail shows linked deals/tasks/attachments, no cross-seller access
- **Leads:** CRUD, status filter, convert creates Contact + Deal and marks lead converted
- **Deals:** kanban grouped by stage, drag saves stage, won/lost sets closed_at, deal requires contact
- **Tasks:** linked to contact/lead/deal, correct Today/Upcoming/Overdue tabs, mark done, one reminder email
- **Uploads:** upload/download/delete on contacts and deals; >10 MB or bad type rejected
- **Billing:** Dodo checkout upgrades to Pro via webhook, signature verified, cancel works
- **Dashboard:** counts + pipeline, deals-won and conversion charts
- **Admin:** admin-only access, activate/deactivate users, platform stats
- **Quality:** OpenAPI docs, 80%+ backend coverage, TS strict passes, Docker builds and runs

---

## ENVIRONMENT VARIABLES

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sathish_crm

# Auth
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_URL=http://localhost:5173

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Dodo Payments
DODO_PAYMENTS_API_KEY=your-dodo-api-key
DODO_PAYMENTS_WEBHOOK_SECRET=your-dodo-webhook-secret
DODO_PAYMENTS_PRO_PRODUCT_ID=your-pro-product-id
DODO_PAYMENTS_ENVIRONMENT=test_mode

# Email (empty SMTP_HOST = log emails instead of sending)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=no-reply@example.com

# File uploads
UPLOAD_DIR=./uploads
MAX_UPLOAD_MB=10

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## NEXT STEP

Execute with parallel agents:
/execute-prp PRPs/sathish-crm-prp.md
