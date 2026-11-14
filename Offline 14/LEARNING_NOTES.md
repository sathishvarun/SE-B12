# Learning Notes

What we did, step by step, and **why** each step mattered.
This is a learning log. The full project guide is in [README.md](README.md).

| Part | Topic |
|---|---|
| A (sections 1–7) | Fixing "Payments are not configured" |
| B (sections 8–10) | Fixing "Google sign-in failed" |
| C (sections 11–13) | Running the whole app with sample data |
| D (sections 14–15) | Updating the docs, and the big lessons |
| 16 | What's next |

---

# Part A: Fixing "Payments are not configured"

---

## 1. The problem

On the live site `https://crm.sathishsakthivel.tech/billing`, clicking **Upgrade to Pro**
showed a red toast:

> Payments are not configured

The rest of the page (plan, contact/deal counts) worked fine.

---

## 2. Finding the cause: search the code for the error text

The fastest way to debug an error message is to search for its exact text:

```bash
grep -rn "not configured" backend/app frontend/src
```

It pointed to `backend/app/services/dodo_payments.py`:

```python
if not settings.DODO_PAYMENTS_API_KEY or not settings.DODO_PAYMENTS_PRO_PRODUCT_ID:
    raise BadRequestError("Payments are not configured")
```

**Lesson:** the code was not broken. It was protecting itself. The server simply had
no Dodo API key or product ID in its settings, so it refused to start a checkout.

### Where do these settings come from?

```
.env file on the server
   ↓  (docker-compose.prod.yml: env_file: .env)
backend container environment variables
   ↓  (app/config.py reads them with pydantic-settings)
settings.DODO_PAYMENTS_API_KEY in Python
```

In `app/config.py` they default to empty strings (`""`), so if `.env` doesn't set
them, they stay empty and the check above fails.

**Why secrets live in `.env` and not in code:** the project rule is
"never hardcode secrets". `.env` stays on the server and is listed in `.gitignore`,
so keys never end up on GitHub.

---

## 3. The fix: three values from Dodo

From the Dodo Payments dashboard (in **Test Mode**):

| Setting | Where to find it | Looks like |
|---|---|---|
| `DODO_PAYMENTS_API_KEY` | Developer → API Keys | long secret string |
| `DODO_PAYMENTS_PRO_PRODUCT_ID` | Products → create a *subscription* product "Pro" | `pdt_...` |
| `DODO_PAYMENTS_WEBHOOK_SECRET` | Developer → Webhooks → add endpoint | `whsec_...` |

Webhook endpoint URL to register in Dodo:

```
https://crm.sathishsakthivel.tech/api/v1/billing/webhook
```

Then on the server, in the project's `.env`:

```env
DODO_PAYMENTS_API_KEY=...
DODO_PAYMENTS_WEBHOOK_SECRET=whsec_...
DODO_PAYMENTS_PRO_PRODUCT_ID=pdt_...
DODO_PAYMENTS_ENVIRONMENT=test_mode
```

**Watch out:** a test-mode key only works with `test_mode`; a live key only with
`live_mode`. A mismatch gives "Payment provider error" instead.

---

## 4. Reload the container (the tricky part)

```bash
docker compose -p sathish-crm -f docker-compose.prod.yml up -d backend
```

**Why `up -d` and not `restart`?**
A container's environment variables are fixed when the container is *created*.
- `restart` = stop and start the **same** container → still has the old (empty) values.
- `up -d` = notices the config changed and **recreates** the container → reads the new `.env`.

Check the values actually got in:

```bash
docker compose -p sathish-crm -f docker-compose.prod.yml exec backend printenv | grep DODO
```

---

## 5. Checking it from outside

We tested the public endpoints with `curl`:

| Request | Result | Meaning |
|---|---|---|
| `GET /health` | 200 `{"status":"ok"}` | Server + backend are running |
| `POST /api/v1/billing/webhook` (unsigned) | 401 "Invalid webhook signature" | Endpoint reachable, rejects fake requests ✅ |
| `POST /api/v1/billing/checkout` (no login) | 401 "Not authenticated" | Needs a logged-in user |

**Lesson:** from outside, you can't prove the keys are loaded. The webhook returns
the same 401 whether or not the secret is set (on purpose, so attackers learn nothing).
The real test needs a logged-in user, or the `printenv` check on the server.

---

## 6. How the payment flow works (big picture)

```
You click "Upgrade to Pro"
   → frontend calls POST /api/v1/billing/checkout
   → backend asks Dodo to create a checkout (using API key + product ID)
   → Dodo returns a checkout URL → browser goes to Dodo's payment page
   → you pay (test card in test mode)
   → Dodo sends a signed webhook to /api/v1/billing/webhook
   → backend verifies the signature (webhook secret) and sets plan = pro
   → Billing page now shows "Pro"
```

**Why the plan changes only through the webhook:** the browser can be faked, but a
webhook signed with the shared secret can only come from Dodo. That's the project rule
"subscription status only changes via verified Dodo Payments webhooks".

---

## 7. Troubleshooting cheat sheet

| What you see | Likely cause | Fix |
|---|---|---|
| "Payments are not configured" | API key or product ID empty in container | Fill `.env`, run `up -d backend`, check `printenv` |
| "Payment provider error" | Wrong key, wrong product ID, or test/live mismatch | Check backend logs |
| Paid, but plan still "Free" | Webhook not reaching backend or wrong secret | Dodo dashboard → webhook delivery log; backend logs |

Backend logs:

```bash
docker compose -p sathish-crm -f docker-compose.prod.yml logs backend --tail 50
```

---

# Part B: Fixing "Google sign-in failed"

## 8. The problem

Clicking **Continue with Google** came straight back to:

```
https://crm.sathishsakthivel.tech/login?error=oauth_failed
```

with the toast "Google sign-in failed. Please try again." Google's sign-in page never appeared.

---

## 9. Finding the cause: follow the redirect

This time we could test from outside, because the Google login link is public.
`curl` shows where the server sends you (without following it):

```bash
curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}\n" \
  https://crm.sathishsakthivel.tech/api/v1/auth/google
# 307 -> https://crm.sathishsakthivel.tech/login?error=oauth_failed
```

If Google were set up, it would redirect to `https://accounts.google.com/...`.
Searching the code for `oauth_failed` led to `backend/app/routers/auth.py`:

```python
if not oauth.is_google_configured():
    logger.warning("Google OAuth requested but GOOGLE_CLIENT_ID/SECRET are not set")
    return RedirectResponse(f"{settings.FRONTEND_URL}{OAUTH_FAILED_URL}")
```

**Lesson:** this was the same kind of problem as payments. The code was fine, but the
server's `.env` had no `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.

**Lesson 2:** the *word* "failed" in the message didn't tell us *why*. Following the
redirect step by step (where does each URL send me?) found the exact line in seconds.

---

## 10. The fix

1. Google Cloud Console → **APIs & Services → OAuth consent screen** (External).
   While in **Testing**, add your Gmail under **Test users**.
2. **Credentials → Create credentials → OAuth client ID → Web application**.
   Authorized redirect URI, exactly:
   ```
   https://crm.sathishsakthivel.tech/api/v1/auth/google/callback
   ```
3. Put the values in the server's `.env`:
   ```env
   GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxx
   ```
   (The redirect URI is already set by `docker-compose.prod.yml` from `DOMAIN`.)
4. `docker compose -p sathish-crm -f docker-compose.prod.yml up -d backend`
5. Run the `curl` above again → it should now point to `accounts.google.com`.

### How OAuth sign-in works (big picture)

```
You click "Continue with Google"
   → GET /api/v1/auth/google
   → backend makes a random "state" value, saves it in a cookie, redirects to Google
   → you pick your Google account
   → Google redirects to /api/v1/auth/google/callback?code=...&state=...
   → backend checks state == cookie   (CSRF protection: proves the request started here)
   → backend swaps the code for your Google profile (using the client secret)
   → backend logs you in (or creates your account) and sends you to the dashboard
```

| Google error | Meaning |
|---|---|
| `redirect_uri_mismatch` | The callback URL in Google Cloud doesn't match exactly (http vs https, trailing slash) |
| "Access blocked" | App is in Testing and your Gmail isn't a test user |

---

# Part C: Running the whole app with sample data

## 11. Why a walkthrough script?

Clicking through every page by hand is slow and easy to forget steps. A script that
calls the API in order is like a **checklist that checks itself**: every request prints
`[OK ]` or `[FAIL]`, so you see at a glance whether the whole app works.

We ran it against the local Docker copy (`localhost:8000`), never against the live site,
so no real customer data was touched.

```bash
python3 scripts/demo_walkthrough.py .env
```

---

## 12. What it does, and the result

| # | Step | Result |
|---|---|---|
| 1 | Sign up + log in as "Priya" | ✅ |
| 2 | Tag "VIP" + 3 contacts | ✅ duplicate tag → 409, bad email → 422 |
| 3 | 2 leads, mark one qualified, convert it | ✅ created contact + deal together; second convert → 409 |
| 4 | Deal: prospect → proposal → negotiation → won | ✅ `closed_at` set on won, cleared when moved back; negative value → 422 |
| 5 | Tasks: one overdue, one linked to a deal, mark done | ✅ linking to two records → 400 |
| 6 | Upload `quote.pdf`, then `virus.exe` | ✅ PDF saved, `.exe` blocked |
| 7 | Dashboard | ✅ 3 contacts, 1 open lead, 2 open deals, ₹370,000.50 pipeline, 1 overdue task |
| 8 | Second seller "Ravi" opens Priya's contact/deal | ✅ 404, sellers can't see each other's data |
| 9 | Billing | ✅ real Dodo test checkout link; unsigned webhook → 401; signed "active" → **Pro**, "cancelled" → **Free** |

**Notice:** many checks *expect an error*. Testing that bad input is **rejected**
is just as important as testing that good input works.

### Why 404 and not 403 in step 8?

403 would say "this exists, but it's not yours", which leaks that the record exists.
404 says "nothing here", so other sellers learn nothing. That's a project rule in `CLAUDE.md`.

### How step 9 faked a payment safely

The script signs webhooks itself with `DODO_PAYMENTS_WEBHOOK_SECRET` from `.env`,
exactly the way Dodo does (HMAC-SHA256 over `id.timestamp.body`). The backend accepts them
because the signature is valid, and rejects the unsigned one. This proves the
**signature check works** without paying.

A real test-card payment on `localhost` would *not* upgrade the plan: Dodo can't send
webhooks to your computer. Real payments must be tested on the live site.

---

## 13. Mistakes we hit along the way (and fixed)

| Mistake | Lesson |
|---|---|
| Script expected **422** for "task linked to two records", app returned **400** | The app was right (`CLAUDE.md` says 400 for bad requests). When a test fails, first ask: *is the test wrong or the code?* |
| `f"/leads/{l1["id"]}"` crashed on Python 3.11 | Same quotes inside an f-string only work on Python 3.12+. Use `{l1['id']}` |
| First saved the script in `tools/` | `tools/` is in `.gitignore`, so it would never be committed. Moved to `scripts/` |

---

# Part D: Docs and big lessons

## 14. What we added to README.md

- **"Try the whole flow with sample data"** section with the script and the step table
- Payments: use `up -d` (not `restart`), check with `printenv`, test vs live mode warning
- Google: add test users; a `curl` check anyone can run
- Day-to-day: command to see which settings the backend actually has
- Troubleshooting rows for each error we met, plus a link to these notes

---

## 15. The big lessons

1. **Search for the exact error text.** It almost always leads straight to the cause.
2. **"Not configured" errors are usually settings, not code.** Check `.env` first.
3. **Containers read `.env` only when created.** After editing, use `up -d`, then verify with `printenv`.
4. **Test from outside when you can** (`curl` on public URLs), and know what you *can't* see from outside.
5. **Never put secrets in code or git.** They live in `.env`, which is in `.gitignore`.
6. **Test the "no" cases too:** bad input, other users' data, fake webhooks.
7. **Practise locally, verify on live.** Sample data goes to `localhost`, never to production.

---

## 16. What's next

1. On the live site: upgrade with a Dodo test card → plan becomes **Pro**; cancel → back to **Free**.
2. Add Google keys on the server and confirm the `curl` check shows `accounts.google.com`.
3. Fill in SMTP values so reminder and plan-change emails are really sent.
4. Commit the project to git (make sure `.env` is **not** committed).
5. Set up database backups (`pg_dump` on a cron job).
6. When ready for real money: switch to `live_mode` with **live** key, product ID and webhook secret.
