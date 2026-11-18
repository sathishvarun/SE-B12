# Virundhu QA checklist (17 Nov 2026)

How to read it: ✅ checked and passing · ⚠️ works, with a limit you should know · ⏳ needs you · ❌ not built

How this was checked: 69 automated tests on a real database; a browser robot that opens every page as visitor,
owner and admin on a desktop, an iPhone and an Android phone; package security scanners; manual walk-throughs as a
restaurant owner; and a read of current Indian rules (DPDP Act 2023 and Rules 2025, CCPA dark-pattern rules, IT Rules
2021) and Google/Meta platform rules.

## 1. How far the product is built

| Area | Status |
|---|---|
| Website: home, how it works (with how-to video), about, pricing calculator, contact, legal pages | ✅ |
| Sign up (email/Google), sign in, reset/change password, welcome email, confirm-email link | ✅ (emails ⏳ SMTP) |
| Outlets, QR code per outlet, Google Maps link, directions, review widget for their website | ✅ (map pictures ⏳ Maps key) |
| Reviews in: Google (⏳ Google approval), QR feedback, paste, file, screenshot (Zomato/Swiggy/others) | ✅ |
| AI: tags, urgency, Tamil + English, reply drafts, dishes and staff named | ✅ |
| Inbox, alerts (owner + branch manager), auto-pilot, holding reply, ask guests for reviews | ✅ (WhatsApp ⏳ Meta) |
| Dashboard, Ask Virundhu, Dishes and staff page, weekly summary, competitor benchmark | ✅ (benchmark ⏳ Places key) |
| Plans 1-12 months, Dodo payments, receipts with GSTIN, reminders, auto-pause, instant reopen | ✅ (live mode ⏳ Dodo) |
| Admin: customers, revenue, plan mix, monthly Excel report, deleted accounts, test-account clean-up, backups | ✅ |
| Instagram/Facebook comments by API, Petpooja partner link | ❌ needs Meta / Petpooja approval |

## 2. Website and code quality

| Check | Result |
|---|---|
| Automated tests | ✅ 71 of 71 pass |
| Walk-through test with screenshots (visitor, owner, guest, attacker, admin) | ✅ 23 of 23 steps |
| Sign-in log, wrong passwords, lock-outs; daily summary email; log Excel | ✅ |
| Support tickets with numbers, emails and history | ✅ |
| Code style and type checks (ruff, TypeScript strict, ESLint), production build | ✅ clean |
| Browser console errors/warnings on every page, 3 screen sizes | ✅ 0 |
| Failed network requests, sideways scrolling on phones, text hidden after animations | ✅ 0 |
| A red "401" line in the console after a wrong password | ⚠️ normal: the browser reporting "wrong password" |
| Tests leave no data behind | ✅ |

## 3. Security (including an attacker's view)

| Check | Result |
|---|---|
| Passwords hashed; never visible in the page HTML | ✅ |
| Session token hidden in an HttpOnly cookie; nothing secret in browser storage | ✅ |
| 5 wrong passwords lock the email for 15 min; same answer for unknown email | ✅ |
| Weak / common / name-based passwords refused | ✅ |
| Restaurant A can never see or change Restaurant B's data (tested) | ✅ |
| Owner can't reach admin pages or admin data (tested) | ✅ |
| Payments: server sets the price, underpayment refused, webhook signature checked, no double counting | ✅ |
| Rate limits on sign-in, sign-up, public pages and widget | ✅ |
| Keys only in .env; none sent to the browser; no secrets in logs | ✅ |
| Live server refuses demo admin password / weak secret / plain http | ✅ |
| Browser protection rules (CSP, HSTS, no framing except the widget) | ✅ ready in deploy/Caddyfile, ⏳ on the server |
| Third-party packages (npm audit, pip-audit) | ✅ 0 known vulnerabilities |
| Two-step sign-in for the admin | ❌ recommended before many customers |
| Outside penetration test | ⏳ after launch, when paying customers exist |

## 4. Privacy and data leakage

| Check | Result |
|---|---|
| Privacy Policy: itemised data table, purpose, retention, consent, rights, grievance officer, breach notice | ✅ |
| Consent tick box at sign-up (time saved); guest notice on QR page; WhatsApp only with consent | ✅ |
| Guest phone numbers: not stored, only a scrambled code, deleted after 12 months | ✅ |
| Automatic clean-up of old data, as the policy promises | ✅ |
| Export my data; delete my account (with confirmation email); admin sees deletions | ✅ |
| Admin Excel excludes restaurants' guest reviews (their data, not yours) | ✅ |
| Backups: daily, newest 30, never uploaded to GitHub | ✅ local, ⏳ copy off the server after hosting |
| AI provider doesn't train on the data; disclosed in the policy | ✅ |

## 5. Legal

| Check | Result |
|---|---|
| Terms, Data Processing Terms, Refund Policy match the real plans and prices | ✅ |
| No hidden charges, no auto-renew, no-card trial (CCPA dark-pattern rules) | ✅ |
| No review gating: every guest sees the Google button (Google policy) | ✅ |
| No scraping of Zomato/Swiggy | ✅ |
| Lawyer review of legal pages | ⏳ |
| GST: CA advice, who files (Dodo vs you); Udyam registration | ⏳ |
| Trademark search for "Virundhu" (many restaurants use the name) | ⏳ |
| Your phone, address and grievance officer name on the site | ⏳ .env |

## 6. Things only you can do (in order)

1. Gmail App password into .env (SMTP): until then no email of any kind goes out.
2. Google Cloud: verify the account (phone + card, not charged) so the free map key can be created.
3. Change the admin password (Admin console → Change my password).
4. Phone number, address, grievance officer name in .env.
5. Lawyer review, CA for GST, trademark search.
6. Approve hosting: domain, server, HTTPS, then apply for Google Business Profile API and Meta.
