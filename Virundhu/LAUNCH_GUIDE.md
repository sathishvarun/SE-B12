# Virundhu launch guide

Three parts:
- **A.** What a real restaurant owner does, step by step, and what protects them at each step.
- **B.** What *you* must do before the first real customer.
- **C.** What's already secure and what's still open.
- **D.** Ideas that make Virundhu look more trustworthy than other tools.

---

## A. A restaurant owner's journey

| # | The owner does | What they see | What protects them |
|---|---|---|---|
| 1 | Finds Virundhu (your link, WhatsApp, a demo) | Home page: the review story, before/after, pricing | Clear pricing incl. GST, real contact details, Privacy, Terms, Refunds and Security pages in the footer |
| 2 | Clicks **Book a demo** (optional) | Contact form | Spam protection; data used only to reply; you see it under Admin → Demo requests |
| 3 | Clicks **Start free trial** | Name, restaurant, city, email, password | Must tick **"I agree to the Terms and Privacy Policy"**; time of consent is saved; password stored only as a hash; sign-up rate limited |
| 4 | Lands on their own empty dashboard | Only their restaurant | Every request is checked against their restaurant; one restaurant can never see another's data (tested) |
| 5 | **Connections → Connect Google** | Google's consent screen | Google access stored encrypted; used only for reviews and replies; can disconnect any time |
| 6 | **Automation → Download QR**, prints it on bills and packets | Guest page: stars, comment, optional name/phone | Guest is told who gets the feedback and that contact details are optional; Privacy link; bot protection |
| 7 | **Add reviews**: pastes or uploads Zomato/Swiggy reviews | Upload progress | File checks and clear errors; reviews stay inside their restaurant |
| 8 | Gets an **instant alert** for a serious complaint | Bell, email, WhatsApp | Alerts only to the owner's own addresses and numbers |
| 9 | **Inbox**: checks the reply draft, posts it | Reply in the guest's language | AI drafts are never posted without the owner, except happy Google reviews when auto-pilot is on |
| 10 | **Ask Virundhu**: "What should I fix first?" | Priority 1, 2, 3 | Numbers counted from their own data; the AI never sees other restaurants |
| 11 | **Plan and billing** before day 14 | Dodo payment page (UPI/card), FIRST10 code | Card/UPI details never touch Virundhu; plan turns on only after the payment is confirmed with Dodo |
| 12 | Forgets the password | **Forgot password?** → email link | Link works once, for 1 hour; doesn't reveal whether an email has an account; signs out all other devices |
| 13 | Wants to leave | **Settings → Account and privacy** | **Download all my data** (CSV), then **Delete my restaurant** (type the name + password) |

---

## B. Before the first real customer (you)

Do these in order. Tick each one.

### 1. Server and domain
- [ ] Buy/choose the domain, point it to your Hostinger VPS.
- [ ] Deploy with Docker Compose + Caddy (HTTPS is automatic) — see `skills/DEPLOYMENT.md`.
- [ ] In the VPS `.env`: `APP_URL`, `API_URL`, `VITE_API_URL` = `https://YOUR-DOMAIN`.
- [ ] Make a **new** `SECRET_KEY` on the VPS (never reuse the one from your Mac): `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.
- [ ] Use a **strong database password** (`DB_PASSWORD`), different from the Mac one.

### 2. Your admin login
- [ ] Set `SUPERADMIN_EMAIL` to your real email **before the first start** on the VPS.
- [ ] Sign in, then **Admin console → Change my password**. `Virundhu@Admin2026` is written in these docs, so it must not stay.

### 3. Your company details (shown on Contact, Privacy, Terms, Refunds, footer)
In the VPS `.env`:
```
COMPANY_NAME=Virundhu            # or your registered business name
CONTACT_EMAIL=you@yourdomain.com # a domain email looks more trustworthy than Gmail
CONTACT_PHONE=+91 9xxxx xxxxx
COMPANY_ADDRESS=City, Tamil Nadu
GRIEVANCE_OFFICER=Your full name
```

### 4. Legal pages
- [ ] Read `/privacy`, `/terms`, `/refunds`. They're a careful starting point, **not legal advice**. Have a lawyer check them, especially the refund rule (7-day first-month refund) and liability.
- [ ] India's DPDP Rules were notified on 13 Nov 2025 and most duties apply from May 2027; the pages already cover notice, consent, rights, erasure and a grievance contact.

### 5. Email (needed for password reset and alerts)
- [ ] Set `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` (e.g. Gmail app password, Zoho, or Brevo). Without this, reset emails only go to the server log.

### 6. Google
- [ ] Google Cloud → OAuth consent screen: add the **privacy policy URL** (`/privacy`), **terms URL** (`/terms`), logo, your domain; add the VPS redirect URL; **Publish app**.
- [ ] Submit the **Business Profile API access** form.

### 7. Payments (Dodo)
- [ ] Finish **Submit information** (verification) in Dodo.
- [ ] Switch to **Live Mode**: create the same 4 products and FIRST10, make a live API key, set `DODO_PAYMENTS_ENVIRONMENT=live_mode`.
- [ ] Add the webhook `https://YOUR-DOMAIN/api/v1/billing/dodo-webhook` (event `payment.succeeded`) and put its secret in `DODO_PAYMENTS_WEBHOOK_KEY`.
- [ ] Add the Privacy, Terms and Refund URLs in Dodo's business settings if asked.

### 8. WhatsApp (optional at launch)
- [ ] Meta app + approved `virundhu_alert` template + keys (GETTING_STARTED.md Part 7).

### 9. Backups and monitoring
- [ ] Daily database backup on the VPS, kept for 30 days, copied off the server. Add to cron (`crontab -e`):
  `30 21 * * * cd /opt/virundhu && bash tools/backup/backup.sh >> backups/backup.log 2>&1` (3:00 am India time),
  then copy the `backups` folder to a second place (Google Drive, another server). Admin console → Data shows the newest backup.
- [ ] Test restoring one backup once.
- [ ] A free uptime check on `https://YOUR-DOMAIN/health` (e.g. UptimeRobot) that emails you if it goes down.

### 10. Final test on the live site
- [ ] Register a test restaurant → connect Google → print QR → submit a QR review from your phone → see the alert → pay a real 1-outlet, 1-month plan with FIRST10 (refund it from the Dodo dashboard afterwards) → export → delete.

---

## C. Security status

| Area | Status |
|---|---|
| HTTPS | Automatic with Caddy on the VPS |
| Passwords | bcrypt hash; min 8 characters; reset links single-use, 1 hour; change/reset signs out everywhere |
| Sign-in tokens | Short-lived access token; refresh tokens stored only as hashes and rotated |
| Brute force | Rate limits on sign-in, sign-up, reset, contact, QR feedback, Ask Virundhu |
| Restaurant isolation | Every query filtered by restaurant; tested |
| Google tokens | Encrypted at rest |
| Payments | No card data stored; plan turns on only after server-side confirmation; webhook signatures checked; repeats ignored |
| Browser headers | nosniff, no framing, strict referrer, no caching of API answers, HSTS on HTTPS |
| Consent | Terms + Privacy tick box at sign-up, time saved; Google sign-up shows the same notice |
| Data rights | Export CSV, delete restaurant, grievance contact |
| Secrets | Only in `.env`, never in Git |
| Passwords on screen | Never written into the page HTML (`SecretInput`) |
| Sign-in tokens | Session in an HttpOnly, SameSite=Strict, Secure cookie; access token only in memory |
| Password guessing | 5 wrong tries lock the email for 15 minutes; common/name-based passwords refused |
| Production settings | Server won't start with the demo admin password, a weak SECRET_KEY or plain http |
| Browser rules | `deploy/Caddyfile`: CSP, HSTS, no framing, nosniff, strict referrer |
| **To do** | Daily backups on the VPS (cron), uptime check, real SMTP, new admin password and secret key on the VPS, lawyer review of legal pages |

---

## D. Making Virundhu look more trustworthy than other tools (suggestions)

1. **A real face.** On "Why Virundhu", add your photo, name and one line on why you built it. Small Indian SaaS buyers trust a person.
2. **Real proof only.** After your 5 pilot restaurants, add their logos and one quote each, *with written permission*. Never invent reviews or numbers.
3. **Before/after numbers from pilots.** "Reply rate 12% → 95% in 30 days at X Biryani" beats any claim.
4. **Domain email and WhatsApp button.** hello@yourdomain.com and a WhatsApp "Talk to us" button on every page.
5. **GSTIN in the footer** once you have one (Dodo invoices already carry tax).
6. **Status page** (free UptimeRobot public page) linked in the footer.
8. **A 60-second demo video** of the six-step story on the Home page.
