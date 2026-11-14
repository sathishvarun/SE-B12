# INITIAL.md - Sathish CRM Product Definition

> A simple CRM that helps sellers track their customers, leads, deals and follow-ups in one place.

---

## PRODUCT

### Name
Sathish CRM

### Description
Sathish CRM is a lightweight customer relationship manager built for sellers. A seller can capture new leads,
convert them into contacts and deals, move deals through a visual sales pipeline, and never miss a follow-up
thanks to tasks with due-date reminders. A dashboard with analytics shows pipeline value, deals won and lead
conversion at a glance. Sellers pay for the product through a subscription handled by Dodo Payments.

### Target User
Sellers and small sales teams (freelance sales reps, small business owners, shop owners) who currently track
customers in spreadsheets, notebooks or WhatsApp and want one simple place to manage their sales.

### Type
- [x] SaaS (Software as a Service)

---

## TECH STACK

### Backend
- [x] FastAPI + Python 3.11+

### Frontend
- [x] React + Vite + TypeScript

### Database
- [x] PostgreSQL + SQLAlchemy (Alembic for migrations)

### Authentication
- [x] Email/Password + Google OAuth (JWT access + refresh tokens)

### UI Framework
- [x] Tailwind CSS + shadcn/ui (Framer Motion for animations)

### Payments
- [x] Dodo Payments (seller subscriptions)

---

## MODULES

### Module 1: Authentication (Required)

**Description:** User authentication and authorization. Every seller has their own account; all CRM data is
scoped to the logged-in seller.

**Models:**
- User: id, email, hashed_password, full_name, is_active, is_verified, is_admin, oauth_provider, created_at
- RefreshToken: id, user_id, token, expires_at, revoked

**API Endpoints:**
- POST /api/v1/auth/register - Create new account
- POST /api/v1/auth/login - Login with email/password
- POST /api/v1/auth/refresh - Refresh access token
- POST /api/v1/auth/logout - Revoke refresh token
- GET /api/v1/auth/me - Get current user profile
- PUT /api/v1/auth/me - Update profile
- POST /api/v1/auth/forgot-password - Send password reset email
- POST /api/v1/auth/reset-password - Reset password with token
- GET /api/v1/auth/google - Start Google OAuth flow
- GET /api/v1/auth/google/callback - Google OAuth callback

**Frontend Pages:**
- /login - Login page (email/password + "Continue with Google")
- /register - Registration page
- /forgot-password - Forgot password page
- /reset-password - Reset password page
- /profile - User profile page (protected)

---

### Module 2: Contacts / Customers

**Description:** The seller's address book of customers.

**Models:**
- Contact: id, user_id, name, email, phone, company, address, notes, created_at, updated_at
- Tag: id, user_id, name
- ContactTag: contact_id, tag_id (many-to-many)

**API Endpoints:**
- GET /api/v1/contacts - List contacts (search by name/email/company, filter by tag, paginated)
- POST /api/v1/contacts - Create contact
- GET /api/v1/contacts/{id} - Get contact with linked deals and tasks
- PUT /api/v1/contacts/{id} - Update contact
- DELETE /api/v1/contacts/{id} - Delete contact
- GET /api/v1/tags - List tags
- POST /api/v1/tags - Create tag

**Frontend Pages:**
- /contacts - Contact list with search and tag filter
- /contacts/new - Create contact form
- /contacts/:id - Contact detail (info, linked deals, tasks, attachments)
- /contacts/:id/edit - Edit contact form

---

### Module 3: Leads

**Description:** Potential customers who have not bought yet. Leads can be converted into a Contact plus a Deal.

**Models:**
- Lead: id, user_id, name, email, phone, company, source, status, notes, converted_contact_id (nullable),
  created_at, updated_at
  - source: website | referral | social | other
  - status: new | contacted | qualified | lost | converted

**API Endpoints:**
- GET /api/v1/leads - List leads (filter by status and source, paginated)
- POST /api/v1/leads - Create lead
- GET /api/v1/leads/{id} - Get lead
- PUT /api/v1/leads/{id} - Update lead
- PATCH /api/v1/leads/{id}/status - Change lead status
- DELETE /api/v1/leads/{id} - Delete lead
- POST /api/v1/leads/{id}/convert - Convert lead into a Contact + Deal

**Frontend Pages:**
- /leads - Lead list with status/source filters
- /leads/new - Create lead form
- /leads/:id - Lead detail with "Convert to customer" button
- /leads/:id/edit - Edit lead form

---

### Module 4: Deals / Pipeline

**Description:** Sales opportunities shown on a kanban board. The seller drags deals between stages.

**Models:**
- Deal: id, user_id, contact_id, title, value (decimal), currency, stage, expected_close_date, notes,
  closed_at (nullable), created_at, updated_at
  - stage: prospect | proposal | negotiation | won | lost

**API Endpoints:**
- GET /api/v1/deals - List deals (filter by stage and contact)
- POST /api/v1/deals - Create deal
- GET /api/v1/deals/{id} - Get deal
- PUT /api/v1/deals/{id} - Update deal
- PATCH /api/v1/deals/{id}/stage - Move deal to another stage (sets closed_at on won/lost)
- DELETE /api/v1/deals/{id} - Delete deal

**Frontend Pages:**
- /deals - Kanban pipeline board (drag and drop between stages)
- /deals/new - Create deal form
- /deals/:id - Deal detail (contact, tasks, attachments)
- /deals/:id/edit - Edit deal form

---

### Module 5: Tasks & Follow-ups

**Description:** Reminders to call, email or meet a customer. Each task can be linked to a contact, lead or deal.

**Models:**
- Task: id, user_id, title, description, due_date, priority, status, contact_id (nullable),
  lead_id (nullable), deal_id (nullable), reminder_sent, created_at, updated_at
  - priority: low | medium | high
  - status: pending | done

**API Endpoints:**
- GET /api/v1/tasks - List tasks (filter: today | upcoming | overdue | done; by linked record)
- POST /api/v1/tasks - Create task
- GET /api/v1/tasks/{id} - Get task
- PUT /api/v1/tasks/{id} - Update task
- PATCH /api/v1/tasks/{id}/complete - Mark task done
- DELETE /api/v1/tasks/{id} - Delete task

**Frontend Pages:**
- /tasks - Task list with Today / Upcoming / Overdue tabs
- /tasks/new - Create task form (pick linked contact/lead/deal)
- /tasks/:id/edit - Edit task form

---

### Module 6: File Uploads

**Description:** Attach documents and images (quotes, invoices, photos) to contacts and deals.

**Models:**
- Attachment: id, user_id, contact_id (nullable), deal_id (nullable), filename, content_type, size_bytes,
  storage_path, created_at

**API Endpoints:**
- POST /api/v1/attachments - Upload file (multipart; max 10 MB; pdf, png, jpg, docx, xlsx)
- GET /api/v1/attachments/{id} - Download file
- DELETE /api/v1/attachments/{id} - Delete file

**Frontend Pages:**
- Attachments section on /contacts/:id and /deals/:id (upload, list, download, delete)

---

### Module 7: Billing (Dodo Payments)

**Description:** Seller subscriptions paid through Dodo Payments.

**Models:**
- Subscription: id, user_id, dodo_customer_id, dodo_subscription_id, plan, status, current_period_end,
  created_at, updated_at
  - plan: free | pro
  - status: active | trialing | past_due | cancelled

**API Endpoints:**
- POST /api/v1/billing/checkout - Create Dodo Payments checkout session
- GET /api/v1/billing/subscription - Get current subscription
- POST /api/v1/billing/cancel - Cancel subscription
- POST /api/v1/billing/webhook - Dodo Payments webhook (signature verified)

**Frontend Pages:**
- /billing - Current plan, upgrade button, cancel subscription
- /pricing - Public pricing page

---

### Module 8: Email Notifications

**Description:** Transactional emails sent from the backend.

**Emails:**
- Welcome email after registration
- Password reset link
- Task due-date reminder (daily job: tasks due today or overdue with reminder_sent = false)
- Payment receipt / subscription status change

---

### Module 9: Dashboard & Analytics

**Description:** Overview and statistics for the logged-in seller.

**API Endpoints:**
- GET /api/v1/dashboard/summary - Counts: contacts, open leads, open deals, tasks due today
- GET /api/v1/dashboard/analytics - Pipeline value by stage, deals won per month, lead conversion rate,
  leads by source

**Frontend Pages:**
- /dashboard - Main dashboard: stat cards, pipeline value chart, deals won chart, today's tasks
- /settings - User settings and preferences

---

### Module 10: Admin Panel

**Description:** Admin-only management interface (users with is_admin = true).

**API Endpoints:**
- GET /api/v1/admin/users - List all users
- PUT /api/v1/admin/users/{id} - Update user status (activate/deactivate)
- GET /api/v1/admin/stats - Platform statistics (total users, active subscriptions, records created)

**Frontend Pages:**
- /admin - Admin dashboard (protected, admin only)
- /admin/users - User management

---

## MVP SCOPE

### Must Have (MVP)
- [x] User registration and login (email/password + Google OAuth)
- [x] Contacts: create, edit, delete, search, tags
- [x] Leads: create, edit, status changes, convert to Contact + Deal
- [x] Deals: kanban pipeline with drag-and-drop stages
- [x] Tasks & follow-ups with Today / Upcoming / Overdue views
- [x] File uploads on contacts and deals
- [x] Email notifications (welcome, password reset, task reminders)
- [x] Dashboard with analytics charts
- [x] Dodo Payments subscription billing
- [x] Admin panel

### Nice to Have (Post-MVP)
- Team accounts (multiple sellers sharing one workspace)
- CSV import/export of contacts and leads
- WhatsApp / SMS follow-up reminders
- Email sending to customers from inside the CRM

---

## ACCEPTANCE CRITERIA

### Authentication
- [ ] User can register with email/password
- [ ] User can login with email/password
- [ ] User can sign up / log in with Google OAuth
- [ ] User can reset a forgotten password via email
- [ ] JWT tokens work correctly with refresh
- [ ] Protected routes redirect to login

### Contacts
- [ ] Seller can create, view, edit and delete contacts
- [ ] Seller can search contacts by name, email or company
- [ ] Seller can tag contacts and filter by tag
- [ ] Contact detail shows linked deals, tasks and attachments
- [ ] A seller can never see another seller's contacts

### Leads
- [ ] Seller can create, edit and delete leads
- [ ] Seller can change lead status and filter by status/source
- [ ] Converting a lead creates a Contact and a Deal and marks the lead as converted

### Deals / Pipeline
- [ ] Deals appear on a kanban board grouped by stage
- [ ] Dragging a deal to another stage saves the new stage
- [ ] Moving a deal to won/lost sets closed_at
- [ ] Each deal must be linked to a contact

### Tasks & Follow-ups
- [ ] Seller can create tasks linked to a contact, lead or deal
- [ ] Today / Upcoming / Overdue tabs show the right tasks
- [ ] Seller can mark a task as done
- [ ] A reminder email is sent once for tasks due today or overdue

### File Uploads
- [ ] Seller can upload, download and delete files on contacts and deals
- [ ] Files over 10 MB or of disallowed types are rejected

### Billing
- [ ] Seller can start a Dodo Payments checkout and upgrade to Pro
- [ ] Webhook updates the subscription status (signature verified)
- [ ] Seller can cancel their subscription

### Dashboard & Analytics
- [ ] Dashboard shows contact, lead, deal and task counts
- [ ] Charts show pipeline value by stage, deals won per month and lead conversion rate

### Admin Panel
- [ ] Only admins can open /admin pages and /admin API endpoints
- [ ] Admin can list users and activate/deactivate them
- [ ] Admin can see platform statistics

### Quality
- [ ] All API endpoints documented in OpenAPI
- [ ] Backend test coverage 80%+
- [ ] Frontend TypeScript strict mode passes
- [ ] Docker builds and runs successfully

---

## SPECIAL REQUIREMENTS

### Security
- [x] Rate limiting on auth endpoints
- [x] Input validation on all endpoints
- [x] SQL injection prevention (SQLAlchemy ORM, no raw SQL strings)
- [x] XSS prevention
- [x] CSRF protection on OAuth flow (state parameter)
- [x] Every CRM query filtered by current user_id (no cross-seller data access)
- [x] Dodo Payments webhook signature verification
- [x] File upload type and size validation

### Integrations
- [x] Email service for notifications (SMTP)
- [x] Dodo Payments for subscriptions
- [x] File upload storage (local disk in development, S3-compatible storage in production)

---

## AGENTS

> These 6 agents will build your product in parallel:

| Agent | Role | Works On |
|-------|------|----------|
| DATABASE-AGENT | Creates all models and migrations | All database models |
| BACKEND-AGENT | Builds API endpoints and services | All modules' backends |
| FRONTEND-AGENT | Creates UI pages and components | All modules' frontends |
| DEVOPS-AGENT | Sets up Docker, CI/CD, environments | Infrastructure |
| TEST-AGENT | Writes unit and integration tests | All code |
| REVIEW-AGENT | Security and code quality audit | All code |

> Note: `agents/` currently has definitions for ORCHESTRATOR, DATABASE, BACKEND and FRONTEND only.

---

# READY?

```bash
/generate-prp INITIAL.md
```

Then:

```bash
/execute-prp PRPs/sathish-crm-prp.md
```
