# Sathish CRM

> A simple CRM that helps sellers track their customers, leads, deals and follow-ups in one place.

**Live:** https://crm.sathishsakthivel.tech

---

## Contents

1. [Features](#features)
2. [Tech stack](#tech-stack)
3. [How it works (process flows)](#how-it-works-process-flows)
4. [Project structure](#project-structure)
5. [Run it on your computer](#run-it-on-your-computer)
6. [Environment variables](#environment-variables)
7. [Testing and code checks](#testing-and-code-checks)
8. [Deploy to a server with HTTPS](#deploy-to-a-server-with-https)
9. [Set up payments (Dodo Payments)](#set-up-payments-dodo-payments)
10. [Set up Google sign-in](#set-up-google-sign-in)
11. [Set up email (SMTP)](#set-up-email-smtp)
12. [Day-to-day operations](#day-to-day-operations)
13. [Troubleshooting](#troubleshooting)
14. [How this project was built](#how-this-project-was-built)

---

## Features

| Area | What it does |
|---|---|
| **Accounts** | Sign up with email + password or Google, password reset by email, sessions renew automatically |
| **Contacts** | Customers with email, phone, company, notes and tags; search and filter by tag |
| **Leads** | Track source (website, referral, social, other) and status; convert a lead into a contact + deal in one click |
| **Deals** | Drag-and-drop pipeline: Prospect → Proposal → Negotiation → Won / Lost; values in INR |
| **Tasks** | Follow-ups linked to a contact, lead or deal; Today / Upcoming / Overdue / Done views; 8 AM reminder email |
| **Files** | Attach PDF, PNG, JPG, DOCX, XLSX (max 10 MB) to contacts and deals |
| **Dashboard** | Key numbers, pipeline by stage, deals won per month, leads by source, conversion rate |
| **Billing** | Free plan (100 contacts, 20 open deals) and Pro plan via Dodo Payments |
| **Admin** | List users, activate/deactivate accounts, platform stats |

Every seller only sees their own data. Asking for another seller's record returns **404 Not Found**.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, TypeScript (strict), Tailwind CSS v4, shadcn/ui, React Query, dnd-kit, Recharts |
| Backend | FastAPI (Python 3.12), SQLAlchemy 2, Alembic, PyJWT + bcrypt, slowapi (rate limits), APScheduler |
| Database | PostgreSQL 16 |
| Payments | Dodo Payments (hosted checkout + signed webhooks) |
| Hosting | Docker Compose on a VPS, Traefik for HTTPS (Let's Encrypt) |
| Tests | pytest (backend), Vitest + React Testing Library (frontend) |

---

## How it works (process flows)

### 1. System overview

```mermaid
flowchart LR
    B[Browser] -- HTTPS --> T[Traefik<br/>TLS + routing]
    T -- "/api/*, /health, /docs" --> API[FastAPI backend]
    T -- "everything else" --> WEB[React app<br/>served by nginx]
    API --> DB[(PostgreSQL)]
    API --> UP[(Uploads volume)]
    API -- checkout / cancel --> DODO[Dodo Payments]
    DODO -- signed webhook --> API
    API -- sign-in --> G[Google OAuth]
    API -- emails --> SMTP[SMTP server]
```

One domain serves everything. The browser loads the React app from `/` and calls the API at `/api/v1/...` on the same domain. Only Traefik is reachable from the internet; the database is private.

### 2. What happens on a request

```mermaid
sequenceDiagram
    participant U as Browser
    participant A as API (FastAPI)
    participant D as PostgreSQL
    U->>A: GET /api/v1/contacts (Authorization: Bearer access_token)
    A->>A: Check token signature + expiry (30 min)
    A->>D: SELECT ... WHERE user_id = current seller
    D-->>A: rows
    A-->>U: 200 { items, total, page, page_size }
    Note over U,A: If the token expired, the app calls /auth/refresh once,<br/>gets a new pair and retries the request automatically.
```

### 3. Sign up and log in

```mermaid
flowchart TD
    R[Register: email + password] --> H[Password hashed with bcrypt]
    H --> S[Free subscription created]
    S --> TK[Access token 30 min + refresh token 7 days]
    TK --> W[Welcome email]
    L[Log in] --> TK
    G[Continue with Google] --> GS[Backend sets a one-time state cookie]
    GS --> GC[Google consent screen]
    GC --> CB[/auth/google/callback checks state + cookie/]
    CB --> TK
    F[Forgot password] --> E[Email with 1-hour reset link]
    E --> NP[New password set, all sessions logged out]
```

### 4. The selling flow (lead → contact → deal → task)

```mermaid
flowchart LR
    LEAD[New lead<br/>status: new] --> C1[contacted] --> Q[qualified]
    Q -- Convert --> CT[Contact created]
    Q -- Convert --> DL[Deal created in Prospect]
    Q -. not interested .-> LOST1[lost]
    DL --> P[Proposal] --> N[Negotiation]
    N --> WON[Won ✓ closed_at set]
    N --> LOST2[Lost ✗ closed_at set]
    CT --> TASK[Tasks / follow-ups]
    DL --> TASK
    TASK -- 8 AM daily --> MAIL[Reminder email]
```

Converting a lead happens in one database transaction: the contact, the deal and the lead's new status are saved together, or not at all.

### 5. Payment flow (upgrade to Pro)

```mermaid
sequenceDiagram
    participant U as Seller
    participant A as API
    participant P as Dodo Payments
    U->>A: Click "Upgrade" → POST /billing/checkout
    A->>P: Create checkout session (Pro product, user_id in metadata)
    P-->>A: checkout_url
    A-->>U: Redirect to Dodo's hosted checkout
    U->>P: Pays
    P->>A: Webhook subscription.active (signed)
    A->>A: Verify signature + timestamp, set plan = pro
    A-->>U: Email "You're on Pro"
    P-->>U: Redirect back to /billing?checkout=success
```

The plan **only** changes when a verified webhook arrives. Clicking "Cancel" asks Dodo to cancel; the plan drops back to Free when Dodo's `subscription.cancelled` webhook arrives.

### 6. Deployment flow

```mermaid
flowchart LR
    DEV[Code on your Mac] -- rsync --> SRV[/opt/sathish-crm on VPS/]
    SRV -- docker compose up --build --> IMG[Images built]
    IMG --> MIG[Backend start: alembic upgrade head]
    MIG --> RUN[uvicorn running]
    RUN --> TR[Traefik picks up labels,<br/>gets HTTPS certificate]
    TR --> LIVE[https://crm.sathishsakthivel.tech]
```

---

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app: routers, CORS, rate limits, body-size limit, scheduler
│   │   ├── config.py          # Settings from environment variables
│   │   ├── database.py        # Engine, session, Base
│   │   ├── models/            # SQLAlchemy tables (user, contact, lead, deal, task, attachment, subscription)
│   │   ├── schemas/           # Pydantic request/response shapes
│   │   ├── routers/           # HTTP endpoints, one file per module
│   │   ├── services/          # Business logic, email, storage, Dodo Payments, reminders
│   │   ├── auth/              # Password hashing, JWT, Google OAuth
│   │   ├── templates/email/   # Email HTML templates
│   │   └── scripts/make_admin.py
│   ├── alembic/               # Database migrations
│   ├── tests/                 # 294 pytest tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/             # One folder per module (auth, contacts, leads, deals, tasks, ...)
│   │   ├── components/        # UI pieces (ui/ = shadcn, layout/, contacts/, deals/, dashboard/ ...)
│   │   ├── hooks/             # React Query hooks
│   │   ├── services/          # API client (api.ts) and one service per module
│   │   ├── context/           # AuthContext
│   │   ├── lib/sections.ts    # Section colours used across the app
│   │   └── types/             # TypeScript types (match the API exactly)
│   ├── nginx.conf
│   └── package.json
├── PRPs/
│   ├── sathish-crm-prp.md     # Implementation blueprint
│   └── api-contract.md        # Exact JSON for every endpoint
├── docker-compose.dev.yml     # Local development (hot reload)
├── docker-compose.yml         # Production-like local run
├── docker-compose.prod.yml    # Server deployment behind Traefik
├── .env.example               # Local settings template
└── .env.production.example    # Server settings template
```

---

## Run it on your computer

### Option A: Docker (easiest)

Needs Docker Desktop running.

```bash
# 1. Create your settings file
cp .env.example .env

# 2. Put a random secret in .env (SECRET_KEY must be 32+ characters)
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
#    paste the output after SECRET_KEY=  and also set POSTGRES_PASSWORD

# 3. Start database + API + frontend (migrations run automatically)
docker compose -f docker-compose.dev.yml up --build
```

| What | URL |
|---|---|
| App | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

Stop with `Ctrl+C`, or `docker compose -f docker-compose.dev.yml down`.

### Option B: Without Docker

Needs Python 3.12, Node 24 and a PostgreSQL database.

```bash
# Backend
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://postgres:PASSWORD@localhost:5432/sathish_crm
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
alembic upgrade head
uvicorn app.main:app --reload            # http://localhost:8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev                              # http://localhost:5173
```

### First steps in the app

1. Open the app and **Sign up**.
2. Make yourself admin (optional):
   ```bash
   # Docker
   docker compose -f docker-compose.dev.yml exec backend python -m app.scripts.make_admin you@example.com
   # Without Docker (in backend/ with the venv active)
   python -m app.scripts.make_admin you@example.com
   ```
3. Add a contact, a lead and a deal; drag the deal across the board.

### Try the whole flow with sample data

With the app running, one script walks through every module through the API and prints
`[OK ]` or `[FAIL]` for each request:

```bash
python3 scripts/demo_walkthrough.py .env
```

| Step | What it checks |
|---|---|
| 1. Sign up + log in | Creates a new demo seller "Priya" |
| 2. Tags + contacts | Duplicate tag → 409, invalid email → 422 |
| 3. Leads | Status change; convert creates a contact + deal; converting twice → 409 |
| 4. Deals | prospect → proposal → negotiation → won sets `closed_at`; moving back clears it; negative value → 422 |
| 5. Tasks | Overdue task, task linked to a deal, mark done; linking to two records → 400 |
| 6. Attachments | PDF accepted, `.exe` rejected |
| 7. Dashboard | Totals for contacts, leads, pipeline value, overdue tasks |
| 8. Data isolation | A second seller "Ravi" gets 404 on Priya's contact and deal |
| 9. Billing | Real Dodo **test** checkout link; unsigned webhook → 401; signed `subscription.active` → Pro, `subscription.cancelled` → Free |

At the end it prints the demo login so you can see the same data in the browser.
Each run creates new users, so it is safe to repeat.

Notes:
- Step 9 needs the Dodo test values in `.env`. The webhooks are signed by the script with your
  `DODO_PAYMENTS_WEBHOOK_SECRET`; no real payment happens.
- A real test-card payment on `localhost` will not upgrade the plan, because Dodo cannot send
  webhooks to your computer. Test real payments on the live site.

---

## Environment variables

| Variable | Required | Example / default | What it's for |
|---|---|---|---|
| `DATABASE_URL` | yes | `postgresql://postgres:pw@localhost:5432/sathish_crm` | Database connection (Docker sets it for you) |
| `SECRET_KEY` | yes | 48+ random characters | Signs login tokens. Must be 32+ chars, not a placeholder |
| `ALGORITHM` | no | `HS256` | Token signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | no | `7` | Refresh token lifetime |
| `FRONTEND_URL` | no | `http://localhost:5173` | Used in email links and redirects |
| `CORS_ORIGINS` | no | `["http://localhost:5173"]` | Sites allowed to call the API |
| `APP_TIMEZONE` | no | `Asia/Kolkata` | Decides "today", "overdue" and the 8 AM reminder time |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | for Google login | from Google Cloud | Empty = Google button disabled |
| `GOOGLE_REDIRECT_URI` | for Google login | `https://DOMAIN/api/v1/auth/google/callback` | Must match Google Cloud exactly |
| `DODO_PAYMENTS_API_KEY` | for payments | `...` | Dodo API key |
| `DODO_PAYMENTS_WEBHOOK_SECRET` | for payments | `whsec_...` | Verifies webhooks |
| `DODO_PAYMENTS_PRO_PRODUCT_ID` | for payments | `pdt_...` | The Pro subscription product |
| `DODO_PAYMENTS_ENVIRONMENT` | for payments | `test_mode` or `live_mode` | Test or real payments |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `EMAIL_FROM` | for email | `smtp.gmail.com` / `587` | Empty host = emails are only logged |
| `UPLOAD_DIR` / `MAX_UPLOAD_MB` | no | `./uploads` / `10` | File storage |
| `FREE_PLAN_MAX_CONTACTS` / `FREE_PLAN_MAX_OPEN_DEALS` | no | `100` / `20` | Free plan limits |
| `VITE_API_URL` | frontend build | `http://localhost:8000` | Where the browser sends API calls |

Never commit `.env`. It is in `.gitignore`.

---

## Testing and code checks

```bash
# Backend: 294 tests, ~98% coverage (uses SQLite in memory, no database needed)
cd backend && source .venv/bin/activate
pytest --cov=app --cov-fail-under=80
ruff check . && ruff format --check .
mypy app --ignore-missing-imports

# Frontend: 58 tests
cd frontend
npm test
npm run lint          # oxlint: no `any`, no console.log
npm run type-check
npm run build
```

---

## Deploy to a server with HTTPS

This is how the live site runs: a Hostinger VPS (Ubuntu 24.04) that already has **Traefik** handling HTTPS for several apps. Sathish CRM joins it by adding Docker labels; it does not change Traefik or other apps.

### One-time setup

1. **DNS** (Hostinger → Domains → DNS records): add an **A** record, name `crm`, pointing at the VPS IP, TTL 300.
2. **SSH key** on your Mac:
   ```bash
   ssh-keygen -t ed25519 -C "my-mac"
   cat ~/.ssh/id_ed25519.pub     # paste into hPanel → VPS → Settings → SSH keys
   ssh root@VPS_IP               # should log in without a password
   ```
3. **Copy the project** (leaves out local secrets and build folders):
   ```bash
   rsync -az --delete \
     --exclude .git/ --exclude node_modules/ --exclude .venv/ --exclude __pycache__/ \
     --exclude dist/ --exclude uploads/ --exclude .env \
     ./ root@VPS_IP:/opt/sathish-crm/
   ```
4. **Create the server's settings** (on the server):
   ```bash
   cd /opt/sathish-crm
   cp .env.production.example .env
   # set DOMAIN, POSTGRES_PASSWORD (openssl rand -hex 24) and SECRET_KEY (openssl rand -base64 48)
   chmod 600 .env
   ```
5. **Start it:**
   ```bash
   docker compose -p sathish-crm -f docker-compose.prod.yml up -d --build
   ```
6. **Check it:**
   ```bash
   curl https://crm.sathishsakthivel.tech/health      # {"status":"ok"}
   ```
   Traefik gets the Let's Encrypt certificate automatically on the first request.

> No Traefik on your server? Install it with Docker first (or add a Caddy service to the compose file). Traefik must have the `websecure` entrypoint and a `letsencrypt` certificate resolver, which `docker-compose.prod.yml` refers to.

### Updating the live site

```bash
# from your Mac, in the project folder
rsync -az --delete --exclude .git/ --exclude node_modules/ --exclude .venv/ \
  --exclude __pycache__/ --exclude dist/ --exclude uploads/ --exclude .env \
  ./ root@VPS_IP:/opt/sathish-crm/

ssh root@VPS_IP 'cd /opt/sathish-crm && docker compose -p sathish-crm -f docker-compose.prod.yml up -d --build'
```

Database migrations run automatically every time the backend starts.

---

## Set up payments (Dodo Payments)

Until this is done, the **Upgrade** button shows "Payments are not configured".

1. Create an account at https://app.dodopayments.com and stay in **Test mode** (toggle at the top).
2. **Products → Create product**
   - Type: **Subscription**
   - Name: `Sathish CRM Pro`
   - Price: your monthly price (for example ₹499 / month), billing every 1 month
   - Save, then copy the **Product ID** (starts with `pdt_`).
3. **Developer → API Keys → Create API key**, copy it.
4. **Developer → Webhooks → Add endpoint**
   - URL: `https://crm.sathishsakthivel.tech/api/v1/billing/webhook`
   - Events: all `subscription.*` events (at least `active`, `renewed`, `on_hold`, `cancelled`, `expired`)
   - Save, then copy the **Signing secret** (starts with `whsec_`).
5. On the server, put the three values in `/opt/sathish-crm/.env`:
   ```env
   DODO_PAYMENTS_API_KEY=...
   DODO_PAYMENTS_WEBHOOK_SECRET=whsec_...
   DODO_PAYMENTS_PRO_PRODUCT_ID=pdt_...
   DODO_PAYMENTS_ENVIRONMENT=test_mode
   ```
   and recreate the backend so it reads the new `.env`:
   ```bash
   docker compose -p sathish-crm -f docker-compose.prod.yml up -d backend
   ```
   Use `up -d`, **not** `restart`: `restart` keeps the old container with the old (empty) values.
   Check the values arrived:
   ```bash
   docker compose -p sathish-crm -f docker-compose.prod.yml exec backend printenv | grep DODO
   ```
   A test-mode key only works with `test_mode`, a live key only with `live_mode`; a mismatch
   shows "Payment provider error".
6. **Test:** log in → Billing → Upgrade → pay with Dodo's test card → you land back on `/billing?checkout=success` and the plan shows **Pro** within a few seconds.
7. When ready for real money: create the same product, API key and webhook in **Live mode**, put the live values in `.env`, set `DODO_PAYMENTS_ENVIRONMENT=live_mode`, restart the backend.

---

## Set up Google sign-in

1. https://console.cloud.google.com → create a project.
2. **APIs & Services → OAuth consent screen**: External, app name "Sathish CRM", your support email, add the domain `sathishsakthivel.tech`.
   While the app is in **Testing** status, add your Gmail under **Test users**, otherwise Google shows "Access blocked".
3. **Credentials → Create credentials → OAuth client ID** → Web application.
   - Authorised redirect URI: `https://crm.sathishsakthivel.tech/api/v1/auth/google/callback`
4. Copy the Client ID and Client secret into the server's `.env`:
   ```env
   GOOGLE_CLIENT_ID=....apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=...
   ```
5. Recreate the backend (`up -d backend`, same command as above).
6. **Check from anywhere:**
   ```bash
   curl -s -o /dev/null -w "%{redirect_url}\n" https://crm.sathishsakthivel.tech/api/v1/auth/google
   ```
   - `https://accounts.google.com/...` → configured ✅
   - `https://crm.sathishsakthivel.tech/login?error=oauth_failed` → keys still missing in the container

---

## Set up email (SMTP)

Without SMTP, emails (welcome, password reset, task reminders, plan changes) are written to the backend log instead of being sent.

Gmail example (needs 2-Step Verification, then Google Account → Security → App passwords):

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-character-app-password
EMAIL_FROM=you@gmail.com
```

Restart the backend after changing `.env`.

---

## Day-to-day operations

All commands run on the server in `/opt/sathish-crm`. A short alias helps:

```bash
alias crm='docker compose -p sathish-crm -f docker-compose.prod.yml'
```

| Task | Command |
|---|---|
| See status | `crm ps` |
| Backend logs | `crm logs -f backend` |
| Apply a `.env` change (recreates the container) | `crm up -d backend` |
| Check which settings the backend sees | `crm exec backend printenv \| grep -E 'DODO\|GOOGLE\|SMTP'` |
| Make a user admin | `crm exec backend python -m app.scripts.make_admin user@example.com` |
| Back up the database | `crm exec -T db pg_dump -U postgres sathish_crm > backup-$(date +%F).sql` |
| Restore a backup | `crm exec -T db psql -U postgres sathish_crm < backup-2026-11-14.sql` |
| Stop everything | `crm down` (data is kept in Docker volumes) |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Backend won't start: "SECRET_KEY must be a random value of at least 32 characters" | Put a real random value in `.env` (see setup steps) |
| Changed `.env` but nothing changed | You used `restart`; run `crm up -d backend` so the container is recreated, then `crm exec backend printenv` to check |
| "Payments are not configured" | Dodo API key or product ID is empty in the container; see [payments](#set-up-payments-dodo-payments) |
| "Payment provider error" | Wrong key / product ID, or test key with `live_mode` (or the reverse); `crm logs backend` shows Dodo's reply |
| Paid but still on Free | Check the webhook URL and signing secret in Dodo; look at `crm logs backend` for "Invalid webhook signature" |
| Google button returns at once to `/login?error=oauth_failed` (never shows Google) | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` are empty in the container |
| Google shows "redirect_uri_mismatch" | The redirect URI in Google Cloud must be exactly `https://crm.sathishsakthivel.tech/api/v1/auth/google/callback` |
| Google shows "Access blocked" | Add your Gmail as a test user on the OAuth consent screen |
| No emails arrive | `SMTP_HOST` is empty or wrong; check `crm logs backend` |
| Site shows 404 right after deploy | Wait ~30 s; Traefik only routes to containers once their health check passes |
| Certificate error | DNS A record must point at the server before the first visit |
| Upload rejected | Only PDF, PNG, JPG, DOCX, XLSX up to 10 MB are allowed |
| "Upgrade" message when adding a contact or deal | The Free plan limit (100 contacts / 20 open deals) was reached |

For a step-by-step story of how the payment and Google sign-in problems were found and fixed,
see [LEARNING_NOTES.md](LEARNING_NOTES.md).

---

## How this project was built

This project started from the **MicroSaaS template** and was built by AI agents in three phases:

```mermaid
flowchart TD
    A["/setup-project<br/>questions → INITIAL.md + CLAUDE.md"] --> B["/generate-prp<br/>→ PRPs/sathish-crm-prp.md + api-contract.md"]
    B --> C["/execute-prp"]
    C --> P1["Phase 1: Foundation (4 agents in parallel)<br/>database · backend core · frontend shell · Docker/CI"]
    P1 --> G1{Gate 1<br/>imports, lint, build, compose config}
    G1 --> P2["Phase 2: Modules (6 agents in parallel)<br/>3 backend + 3 frontend"]
    P2 --> G2{Gate 2<br/>ruff, mypy, oxlint, tsc}
    G2 --> P3["Phase 3: Quality (3 agents in parallel)<br/>tests · security review · docs research"]
    P3 --> FX[Fixes applied + retested]
    FX --> DEP[Deployed with HTTPS]
```

| Phase | Result |
|---|---|
| Foundation | 11 database tables, FastAPI core, React shell with 26 routes, Docker + CI |
| Modules | 50 API endpoints and all pages, built against one shared API contract |
| Quality | 294 backend tests (97.6% coverage), 58 frontend tests, 0 critical security issues; 3 high and 9 medium issues found and fixed |
| Deploy | Live at https://crm.sathishsakthivel.tech behind Traefik with Let's Encrypt |

Key documents: `INITIAL.md` (product definition), `CLAUDE.md` (coding rules), `PRPs/sathish-crm-prp.md` (blueprint), `PRPs/api-contract.md` (API shapes).
