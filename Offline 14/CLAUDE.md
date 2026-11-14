# CLAUDE.md - Sathish CRM Project Rules

> Project-specific rules for Claude Code. This file is read automatically.

---

## Project Overview

**Project Name:** Sathish CRM
**Description:** A simple CRM that helps sellers track their customers, leads, deals and follow-ups in one place.
**Tech Stack:**
- Backend: FastAPI + Python 3.11+
- Frontend: React + Vite + TypeScript
- Database: PostgreSQL + SQLAlchemy (Alembic migrations)
- Auth: JWT (email/password) + Google OAuth
- UI: Tailwind CSS + shadcn/ui (+ Framer Motion)
- Payments: Dodo Payments

---

## Project Structure

```
sathish-crm/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── user.py          # User, RefreshToken
│   │   │   ├── contact.py       # Contact, Tag, ContactTag
│   │   │   ├── lead.py
│   │   │   ├── deal.py
│   │   │   ├── task.py
│   │   │   ├── attachment.py
│   │   │   └── subscription.py
│   │   ├── schemas/
│   │   ├── routers/             # auth, contacts, leads, deals, tasks,
│   │   │                        # attachments, billing, dashboard, admin
│   │   ├── services/            # business logic, email, storage, dodo
│   │   └── auth/
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # ui/ (shadcn), layout/, contacts/, deals/ ...
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/            # API client
│   │   ├── context/             # AuthContext
│   │   └── types/
│   └── package.json
├── .claude/
│   └── commands/
├── skills/
├── agents/
└── PRPs/
```

---

## Code Standards

### Python (Backend)
```python
# ALWAYS use type hints
def get_contact(db: Session, contact_id: int, user_id: int) -> Contact | None:
    pass

# ALWAYS add docstrings for public functions
def create_deal(db: Session, data: DealCreate, user_id: int) -> Deal:
    """
    Create a new deal for the current seller.

    Args:
        db: Database session
        data: Deal creation data
        user_id: ID of the logged-in seller

    Returns:
        Created Deal object
    """
    pass
```

### TypeScript (Frontend)
```typescript
// ALWAYS define interfaces for props and data
type DealStage = "prospect" | "proposal" | "negotiation" | "won" | "lost";

interface Deal {
  id: number;
  contactId: number;
  title: string;
  value: number;
  currency: string;
  stage: DealStage;
  expectedCloseDate: string | null;
  notes: string | null;
}

// NO any types allowed
const fetchDeal = async (id: number): Promise<Deal> => {
  // ...
};
```

---

## Forbidden Patterns

### Backend
- ❌ Never use `print()` - use `logging` module
- ❌ Never store passwords in plain text - use bcrypt
- ❌ Never hardcode secrets - use environment variables
- ❌ Never use `SELECT *` - specify columns
- ❌ Never skip input validation (Pydantic schemas on every endpoint)

### Frontend
- ❌ Never use `any` type
- ❌ Never leave console.log in production
- ❌ Never skip error handling in async operations
- ❌ Never use inline styles - use Tailwind classes and shadcn/ui components

---

## Module-Specific Rules

### All CRM data (Contacts, Leads, Deals, Tasks, Attachments)
- Every record must belong to a user (`user_id` foreign key)
- Every query must filter by the current user's `user_id`; return 404 (not 403) for another seller's records

### Contacts Module
- Email is optional, but if given it must be a valid email
- Tags are per-seller; tag names are unique per seller

### Leads Module
- `source` must be one of: website, referral, social, other
- `status` must be one of: new, contacted, qualified, lost, converted
- Converting a lead creates a Contact and a Deal in one transaction, sets status to `converted`
  and stores `converted_contact_id`; a converted lead cannot be converted again

### Deals Module
- `stage` must be one of: prospect, proposal, negotiation, won, lost
- Every deal must be linked to a contact owned by the same seller
- `value` is a decimal (never float), must be >= 0
- Moving to `won` or `lost` sets `closed_at`; moving back to an open stage clears it

### Tasks Module
- `priority` must be one of: low, medium, high
- `status` must be one of: pending, done
- A task may link to at most one of contact / lead / deal (or none)
- Overdue = status `pending` and `due_date` before today
- Reminder email is sent once per task (`reminder_sent` flag)

### Attachments Module
- Max file size 10 MB; allowed types: pdf, png, jpg, jpeg, docx, xlsx
- Store files under a generated name, never the user-supplied filename

### Billing Module (Dodo Payments)
- Subscription status only changes via verified Dodo Payments webhooks
- `plan` must be one of: free, pro
- `status` must be one of: active, trialing, past_due, cancelled

### Admin Module
- Admin endpoints require `is_admin = true`; return 403 otherwise

---

## API Conventions

- All endpoints prefixed with `/api/v1/`
- Use plural nouns for resources: `/contacts`, `/leads`, `/deals`, `/tasks`
- List endpoints are paginated (`?page=1&page_size=20`)
- Return appropriate HTTP status codes:
  - 200: Success
  - 201: Created
  - 400: Bad Request
  - 401: Unauthorized
  - 403: Forbidden
  - 404: Not Found
  - 409: Conflict

---

## Authentication

### JWT Configuration
- Access token expires: 30 minutes
- Refresh token expires: 7 days
- Algorithm: HS256
- Passwords hashed with bcrypt

### OAuth Providers
- Google OAuth 2.0 enabled
- Always verify state parameter for CSRF protection

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sathish_crm

# Auth
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Dodo Payments
DODO_PAYMENTS_API_KEY=your-dodo-api-key
DODO_PAYMENTS_WEBHOOK_SECRET=your-dodo-webhook-secret
DODO_PAYMENTS_PRO_PRODUCT_ID=your-pro-product-id

# Email (SMTP)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-smtp-user
SMTP_PASSWORD=your-smtp-password
EMAIL_FROM=no-reply@example.com

# File uploads
UPLOAD_DIR=./uploads
MAX_UPLOAD_MB=10

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Development Commands

```bash
# Backend (use a project-local venv)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Docker
docker-compose up -d

# Tests
pytest backend/tests -v
cd frontend && npm test

# Linting
ruff check backend/
cd frontend && npm run lint && npm run type-check
```

---

## Commit Message Format

```
feat([module]): add [feature]
fix([module]): fix [bug]
refactor([module]): refactor [component]
test([module]): add tests for [feature]
docs: update [documentation]
```

Modules: auth, contacts, leads, deals, tasks, attachments, billing, dashboard, admin

---

## Skills Reference

| Task | Skill to Read |
|------|---------------|
| Database models | skills/DATABASE.md |
| API + Auth | skills/BACKEND.md |
| React + UI | skills/FRONTEND.md |
| Testing | skills/TESTING.md |
| Deployment | skills/DEPLOYMENT.md |

---

## Agent Coordination

For complex tasks, the ORCHESTRATOR coordinates:
- DATABASE-AGENT → Backend models
- BACKEND-AGENT → API development
- FRONTEND-AGENT → UI components
- TEST-AGENT → Testing
- REVIEW-AGENT → Code review
- DEVOPS-AGENT → Deployment

Read agent definitions in `/agents/` folder (currently: ORCHESTRATOR, database, backend, frontend).
