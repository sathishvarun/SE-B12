# CLAUDE.md - Virundhu Project Rules

> Project-specific rules for Claude Code. This file is read automatically.

---

## Project Overview

**Project Name:** Virundhu ("feast / welcoming guests" in Tamil). Tagline: *Every guest, heard.*
**Description:** Review-intelligence SaaS for Tamil Nadu restaurant chains and cloud kitchens. It tags every
review (including Tamil and Tanglish), drafts replies and raises an instant alert the moment a serious complaint arrives.
**Users:** only two kinds. The platform admin (`is_superadmin`, never a member of any restaurant, uses the Admin console)
and the restaurant owner (registers, sees only their own restaurant). Features depend on the plan.
**Tech Stack:**
- Backend: FastAPI + Python 3.11+, ARQ worker + Redis for background jobs
- AI: LangChain (LCEL, structured output). ONE provider at a time via `LLM_PROVIDER` (openai | anthropic). Currently openai
- Frontend: React + Vite + TypeScript (strict)
- Database: PostgreSQL 16 + SQLAlchemy 2.0 (Alembic migrations)
- Auth: JWT (email/password) + Google OAuth. Roles in use: owner; platform super admin
- UI: Tailwind CSS v4 + motion + Recharts + sonner (banana-leaf feast palette + food line-art backgrounds in public/patterns, Anek Tamil + Hind Madurai fonts)
- Payments: Dodo Payments (default, `PAYMENT_PROVIDER=dodo`), Razorpay as alternative. One-time payment per 1 or 12 months
- Deploy: Docker Compose behind the VPS's Traefik (auto HTTPS), `deploy/vps/install.sh`; live at https://virundhu.sathishsakthivel.tech

---

## Project Structure

```
Virundhu/
├── backend/app/
│   ├── main.py, config.py, database.py, limiter.py, seed.py (admin only)
│   ├── models/        # user (User, Organization, Membership, ...), review (Outlet, Review, ReviewAnalysis, ...),
│   │                  # ops (AlertRule, Notification, Subscription, Payment, WebhookEvent, SourceConnection)
│   ├── routers/       # auth, google_auth, dashboard, reviews, intake, notifications, team, admin, billing,
│   │                  # assistant (Ask Virundhu), feedback (public QR page), public, health
│   ├── services/      # analysis, alerts, intake, google_reviews, billing (Razorpay), dodo_billing, plans, emailer,
│   │                  # assistant, autopilot (Google auto-reply), whatsapp
│   ├── ai/            # llm.py (single provider), tagging.py, prompts.py, schemas.py, safety.py
│   ├── worker/        # ARQ: analyze_job, retry_unread_tick (5 min), google_sync_tick (10 min), test_feed_tick
│   └── auth/          # security.py, deps.py (OrgContext, require_writable, require_owner, require_superadmin)
├── backend/alembic/versions/   # 0001-0004
├── backend/tests/              # pytest, real Postgres; LLM, Google, Razorpay and Dodo mocked
├── frontend/src/
│   ├── pages/         # Landing, AuthPages, Dashboard, Inbox, Alerts, Ask, AddReviews, Connections, Automation,
│   │                  # SettingsPage, Billing, Admin, Feedback (public /f/:token), JoinPages, NotFound
│   ├── components/    # layout/ (AppLayout, bells, Logo), landing/, ui/, review/
│   ├── services/api.ts, context/AuthContext.tsx, lib/ (workspace, time, tones, copy), types/
├── deploy/github-ci.yml        # move to .github/workflows/ when pushing
├── start.sh / stop.sh          # one-command local run (ports 8450 API, 5450 web)
├── skills/ agents/ PRPs/ claude-commands/ samples/
```

---

## Code Standards

### Python (Backend)
```python
# ALWAYS use type hints and docstrings on public functions
def list_reviews(db: Session, org_id: int, filters: ReviewFilters) -> Page[ReviewOut]:
    """Return reviews of one organization matching the filters, newest first."""
```

### TypeScript (Frontend)
```typescript
type Urgency = "low" | "medium" | "high";
type Sentiment = "positive" | "neutral" | "negative";
type Category =
  | "food_quality" | "delivery" | "price" | "staff"
  | "packaging" | "hygiene" | "app" | "other";
// NO any types allowed
```

---

## Forbidden Patterns

### Backend
- ❌ Never use `print()` - use `logging`
- ❌ Never hardcode secrets or API keys - use environment variables via `config.py`
- ❌ Never call an LLM inside a web request handler - enqueue an ARQ job
- ❌ Never call two LLM providers for the same task (no fallback chains) - only `LLM_PROVIDER` is used
- ❌ Never let the LLM calculate counts, percentages or trends - compute them in SQL/pandas
- ❌ Never put review text into a prompt outside the delimited `<review>` block
- ❌ Never use `SELECT *` or raw SQL strings with user input
- ❌ Never skip Pydantic validation
- ❌ Never call real LLM, Google, Razorpay or Dodo APIs in tests - mock them
- ❌ Never scrape Zomato or Swiggy. They have no public review API; reviews come in by paste/upload
- ❌ Never turn a plan on from the browser's word (return URL, query params). Only from the provider's API or a verified webhook

### Frontend
- ❌ Never use `any`
- ❌ Never leave `console.log` in production
- ❌ Never use inline styles - Tailwind + shadcn/ui only
- ❌ Never use AI clichés in the UI: no sparkle ✨, robot, brain or "magic" icons, no "AI-powered" badges,
  no purple-to-blue gradients
- ❌ Never write robotic copy ("Processing complete"). Write like a helpful colleague ("All 248 reviews read.")

---

## Module-Specific Rules

### Multi-tenancy (all modules)
- Every business record has `organization_id`. Every query filters by the current user's organization.
- A record from another organization returns **404**, never 403.
- Role checks: owner (everything in their restaurant). The super admin views any restaurant with the `X-Org-Id`
  header from the Admin console. (`manager`/`agent` and `outlet_ids` still exist in the database but aren't offered in
  the UI.)
- Writes go through `require_writable`: an expired trial or expired paid plan returns 402. Billing endpoints don't.

### Import
- CSV or Excel. Required columns: review_text, rating. Optional: review_id, date, platform, outlet (aliases accepted).
- Unknown outlet names go to the restaurant's first outlet. Single reviews can be pasted.
- `platform` normalised to google | zomato | swiggy | other. `rating` integer 1-5.
- Unique (organization_id, platform, external_id) - duplicates are skipped and counted, not errors.

### AI Analysis
- Enums are strict (see INITIAL.md Module 4). Retry invalid output max 2 times, then `needs_review`.
- Safety net in `ai/safety.py` can only **raise** urgency, never lower it. Set `safety_override=true`.
- Reply drafts: same language as the review, the org's tone and signature, never promise refunds or blame
  staff, never invent facts (order IDs, amounts).
- Record `model_used`, tokens and `cost_inr` for every call; update `UsageCounter`.
- Check the plan quota before analysing; over-quota reviews stay `pending_quota`.
- If the AI fails, the review becomes `needs_review` (food-safety words still make it urgent) and is retried every
  5 minutes for 7 days.

### Privacy and accounts
- Sign-up requires `accept_terms`; `users.terms_accepted_at` is stored. Don't remove the consent checkbox.
- Forgot/reset password never reveals whether an email exists; reset tokens are hashed, single-use, 30 minutes. Customer emails are branded HTML automatically (services/emailer.branded_html); emails to SUPERADMIN_EMAIL stay plain. A "password was changed" email follows every reset or change.
- Owners can export (`/account/export`) and delete everything (`/account/delete`); keep both working when adding tables
  (new restaurant tables need `organization_id` with ON DELETE CASCADE).
- Legal pages read company details from `/public/config`; never hard-code a name, email or phone.

### Automation
- Google auto-pilot (`services/autopilot.py`) runs right after a review is read. It posts only when ALL hold: owner turned
  it on, plan active, Google review with `source_ref`, no reply yet, stars >= `autopilot_min_rating` (4 or 5), sentiment
  positive, urgency low, not hygiene, no safety override, a draft exists. Any failure leaves the review for the owner.
- QR feedback (`routers/feedback.py`): public, no sign-in, rate limited 5/min, honeypot field `website`. Saves platform
  `direct`. Every guest (never only happy ones) may be invited to Google. Never put the guest's contact in prompts.
- WhatsApp (`services/whatsapp.py`): Meta Cloud API template messages only, deduplicated in `alert_logs`
  (`recipient = "wa:<number>"`). Off unless `WHATSAPP_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID` are set.
- Ask Virundhu (`services/assistant.py`): numbers computed in SQL and passed as DATA; the model only explains and ranks.
  The only LLM call made inside a request (single call, 45 s timeout, 20/min limit).

### Alerts
- Instant, not weekly: every `high` urgency review creates a Notification for the owner (bell, polled every 15 s),
  one email per address and one WhatsApp per saved number (when set up). Sample reviews never email or WhatsApp.

### Billing
- Prices live ONLY in `services/pricing.py`: `OUTLET_TIERS` (price per outlet per month by outlet count) and
  `DURATIONS` (1/3/6/9/12 months → discount %, bonus months). `quote(outlets, months)` is the single calculation.
  The browser sends only outlets + months; the server computes the amount. Public `GET /billing/pricing` and
  `GET /billing/quote` feed the calculator (`components/site/PriceCalculator.tsx` mirrors the formula for instant display).
- Dodo uses ONE pay-what-you-want product (`DODO_PRODUCT_FLEX`); the server sets `amount` in `product_cart`.
- `billing.activate()` recomputes the quote and refuses payments below quote × (100 − `PROMO_MAX_DISCOUNT_PCT`)%.
  It sets `org.plan` (starter 1 / growth ≤5 / chain) and `org.paid_outlets`; `plans.limits_for(org)` then allows
  `paid_outlets` outlets and 500 reviews per outlet a month. Renewals add the new period after the current end.
- Dodo: `POST /billing/checkout` → hosted page → return to `/app/billing?payment_id=` → `POST /billing/confirm` reads the
  payment from Dodo; `POST /billing/dodo-webhook` (Standard Webhooks signature via the SDK) does the same.
- Razorpay: `POST /billing/order` → Checkout.js → `POST /billing/verify` (HMAC of order|payment) and `/billing/webhook`.
- `billing.activate()` is idempotent on the payment ID and extends `Subscription.current_period_end` by the quote's
  `access_days` (months + bonus months × 30.44).

### Admin activity log
- `activity_log` table (migration 0007), written by `services/activity.record()` (never raises): signup,
  password_changed, password_reset, account_deleted (org name captured before delete; no FK so it survives),
  payment, demo_request. Deleted accounts, payments and demo requests also email `SUPERADMIN_EMAIL`.
- Shown in Admin console → Activity tab (`GET /admin/activity`) and the admin bell (`/admin/events`, last 14 days).
- Webhook events are stored in `webhook_events` to ignore repeats. Amounts are integers in the smallest unit.

### Admin
- `/api/v1/admin/*` requires `is_superadmin`; 403 otherwise.

---

## API Conventions

- Prefix `/api/v1/`. `GET /health` unprefixed.
- Plural nouns. Paginated lists: `?page=1&page_size=25` → `{ items, total, page, page_size }`.
- Errors: `{ "detail": "human readable message" }`.
- Status codes: 200, 201, 202 (job queued), 400, 401, 403, 404, 409, 413 (file too large), 422, 429.

---

## Authentication

- Access token 30 minutes, refresh token 7 days, HS256, bcrypt hashing.
- Google OAuth 2.0 with state parameter (CSRF).

---

## Environment Variables

See `.env.example` (full list in PRPs/virundhu-prp.md). Never commit `.env`.

---

## Development Commands

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed               # platform admin
uvicorn app.main:app --reload --port 8450
arq app.worker.settings.WorkerSettings   # second terminal

# Frontend
cd frontend && npm install && npm run dev   # port 5450

# Everything at once (recommended)
bash start.sh

# Everything with Docker
docker compose up -d

# Tests and lint
cd backend && SEED_DEMO_RESTAURANT=true python -m app.seed && pytest -q && python -m app.seed
ruff check backend/
cd frontend && npx eslint src && npx tsc -b --noEmit
```

---

## Commit Message Format

```
feat([module]): add [feature]
fix([module]): fix [bug]
test([module]): add tests for [feature]
docs: update [documentation]
```
Modules: auth, outlets, import, ai, inbox, alerts, dashboard, billing, admin, web, deploy

**Never push to GitHub or deploy without the project owner's approval.**

---

## Skills Reference

| Task | Skill to Read |
|------|---------------|
| Database models | skills/DATABASE.md |
| API + Auth | skills/BACKEND.md |
| LangChain pipeline, prompts, safety net | skills/AI_PIPELINE.md |
| React + UI | skills/FRONTEND.md |
| Testing | skills/TESTING.md |
| Deployment | skills/DEPLOYMENT.md |

---

## Agent Coordination

ORCHESTRATOR coordinates DATABASE, BACKEND, AI, FRONTEND, DEVOPS, TEST and REVIEW agents.
Definitions in `/agents/` (ORCHESTRATOR, database, backend, frontend). AI, DEVOPS, TEST and REVIEW run as
general-purpose agents using the matching skill file.

### Outlets and chain features (migration 0008)
- Outlet: address, district, pincode, phone, manager_name/phone/email, google_maps_url, zomato_url, swiggy_url.
  `PUT /outlets/{id}`, `DELETE /outlets/{id}` (hides; keep at least one). `GET /outlets` returns each outlet's own
  QR link `feedback_url` (`/f/<token>?o=<id>`).
- Urgent alerts add the outlet's manager_email (and manager_phone for WhatsApp, normalised to +91).
- Uploads: unknown names in the `outlet` column become outlets up to `limits_for(org)["outlets"]`.
- AI failure fallback: rating-based urgency (1-2★ medium) unless food-safety words (then high).
- Autopilot: `autopilot_min_rating` may be 3 (needs neutral/positive reading). `holding_reply_hours` (2/6/24, None=off):
  cron `holding_reply_tick` posts `autopilot.holding_text()` to 1-2★ Google reviews older than N hours and newer than
  14 days, sets `holding_reply_at` and workflow `in_progress`.

### Growth features (migration 0009)
- `review_requests` (org, outlet, phone_hash = sha256(SECRET_KEY:org:phone), channel). `services/review_requests.py`:
  `normalise_phone` (+91 mobiles), 30-day cooldown, max 200 per call, consent required (`POST /review-requests`),
  `GET /review-requests/stats`. WhatsApp API template when keys set, else wa.me links (`quote(..., safe="")`).
- `services/weekly_summary.py` + cron Monday 03:30 UTC; `organizations.weekly_summary` switch.
- `app/ai/screenshot.py` (vision, report model, structured output) → `POST /imports/screenshot` (png/jpeg/webp, 5 MB).
- `POST /outlets/import` (CSV/Excel, header aliases, upsert by name, only given columns overwrite).
- `GET /admin/launch-check`, `POST /admin/test-email`.
- `public/sw.js` (no caching) registered in production; `WhatsAppButton` in SiteLayout when company phone is set.

### Design system and motion
- Fonts: headings `Anek Tamil Variable` (wdth axis, `@fontsource-variable/anek-tamil/wdth.css`), body Hind Madurai.
  Utilities in `index.css`: `type-hero`, `type-section`, `type-lead`, `type-label`, `lift`.
- `components/motion/Kolam.tsx` (self-drawing kolam), `Reveal` / `RiseWords` (`components/motion/Reveal.tsx`). Always
  respect `useReducedMotion`.
- The website is English only (the user asked for no Tamil text). Keep it that way.
- Password boxes must use `SecretInput` / `Field type="password"` (components/ui/input.tsx): never a controlled
  `<input type="password" value=...>`, which writes the password into the page HTML.
- Auth: refresh token only in the HttpOnly cookie (`auth/cookies.py`), access token only in memory (`services/api.ts`).
  Never put tokens in localStorage. Lockout: `auth/lockout.py`. Password rules: `auth/passwords.py`.
- Trials are always 14 days; there is no extend option. Admin revenue: `GET /api/v1/admin/revenue`.
- Admin Data tab: `routers/admin_data.py` (Excel export, test-account clean-up, backup status). Backups: `tools/backup/`.
- Trial/plan reminders: `services/plan_reminders.py`, hourly cron, table `plan_reminders` (migration 0011).
- Tests clean up after themselves (`tests/conftest.py` session fixture); keep it that way.
- Demo video: `frontend/public/demo/howto.mp4` (silent, 1080p) + `howto.jpg` + `howto.json` (step starts and titles),
  shown by `components/site/DemoVideos.tsx` on How it works. The user does not want audio in the video.
  Built by `tools/howto_video/rec.py` (Xvfb + headed Chrome at 1.5x + ffmpeg x11grab, wall-clock timestamps).

### Extras (migration 0010, `routers/extras.py`)
- Platforms + `tripadvisor`, `instagram`, `facebook` (check constraint `review_platform`).
- `organizations.billing_key_hash`, `ask_after_bill`; `POST /settings/billing-key`; `POST /hooks/bill`.
- `outlets.competitors` (JSONB) + `competitors_at`; `services/competitors.py` (Places Text Search); `GET /competitors`.
- `testimonials` table; `GET /public/testimonials`; admin CRUD `/admin/testimonials`.

### AI agent team (migration 0018, `services/agent_team.py`)
- Virundhu is AI as a service: its own operations run on agents with no person in the loop. Worker cron `agent_tick`
  (every minute) = Mani, the lead agent, who runs `nila_round` (demos) and `tara_round` (support); each action is a row
  in `agent_runs`, shown at Admin → Autopilot (`GET /admin/agents`).
- Nila: a new Lead (contact form now requires email + `meet_mode`) gets 6 open times (`DEMO_DAYS`, `DEMO_TIMES`, India
  time, never a booked time). The restaurant books at `/demo/:token` (public, token is the key; `/api/v1/public/contact/
  demo/{token}` + `/book`, `/more`, `/cancel`). Booking emails both sides an .ics invite and a link (`DEMO_LINK_*` or a
  per-demo meet.jit.si room), WhatsApps `ADMIN_WHATSAPP`, reminds 24 h and 1 h before, follows up with the trial link.
- Tara: answers every ticket whose last message is the customer's. Payment issues: `recover_payment` finds a succeeded
  Dodo payment for the org that never activated and activates it. Refunds/legal/abuse or a 4th round →
  `call_admin` (WhatsApp + email + bell). Never promise refunds. Agent messages have author `tara@agents.virundhu`.

- Isai (migration 0019, `product_feedback` table, `routers/product_feedback.py`): `POST /public/feedback` (honeypot,
  5/min), `POST /feedback`, `GET /feedback/ease-prompt`, `POST /feedback/ease`, `GET /admin/feedback` (numbers in
  Python, never by the model). `isai_round` runs before Tara: problems/questions or ease <= 2 with a message open a
  ticket; ideas are counted by area; praise with `consent_quote` and rating >= 4 becomes a published testimonial.

### SEO (prerendered public pages)
- `npm run build` = client build + SSR build of `src/entry-server.tsx` + `scripts/prerender.mjs`, which writes real
  HTML for every path in `lib/seo.ts` (`SEO`: title, description, JSON-LD), plus `404.html` (noindex), `app-shell.html`
  (noindex, for /app, /login, /f, /demo, /w...) and `sitemap.xml`. `public/robots.txt` blocks app routes.
- nginx: public pages from files (`try_files $uri $uri/index.html =404`), unknown URLs get a real 404, app routes get the
  shell. `main.tsx` hydrates prebuilt pages (`hydrateRoot`) and seeds `public-config` with `STATIC_CONFIG`.
- Content in the first paint must be visible without JavaScript: `Reveal`/`RiseWords` skip their entrance on first
  paint (`markPainted`), and `useCountUp(..., true)` starts at the real number. New public page → add it to `SEO`.

### Money (migration 0020, `routers/admin_money.py`)
- `payments.is_test` (set by `billing.payments_in_test_mode()` at activation; all payments before live mode were test) and
  `payments.refunded_paise`. `refunds` table filled by the Dodo webhook (`refund.*` → `dodo_billing.record_refund`,
  idempotent on refund_id) and by `POST /admin/money/sync`. Test payments never count as revenue (also in `/admin/revenue`).
- `GET /admin/money?days=&include_test=`: windows (today, yesterday, this/last week, this month, last 30, all time),
  daily and weekly series, every payment and refund. Admin menu groups: Overview, Money, Customers, Help desk, Logs, System.

### Idle sign-out (security)
- `components/layout/IdleSignOut.tsx` + `lib/idle.ts`: admin signed out after 5 minutes without mouse/keyboard/touch/
  scroll, restaurant users after 15; a "Still there?" warning shows for the last minute. Last activity is shared across
  tabs in localStorage (`virundhu.lastActive`, a timestamp only) and checked on start-up in `AuthContext`, so a session
  left idle with the tab closed is ended instead of restored. Login shows the reason (`/login?timeout=5|15`).
- After sign-in people return to the page they opened (`lib/next.ts`), including through Google sign-in.
