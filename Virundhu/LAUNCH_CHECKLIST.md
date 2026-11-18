# Virundhu launch checklist (everything a SaaS launch needs)

✅ built and tested   ⏳ needs you (an account, a key, a decision)   ❌ not built yet

## 1. Billing life cycle (like a phone bill)

| Step | What happens | Status |
|---|---|---|
| Sign up | 14-day free trial, all features, no card | ✅ |
| Trial ending | Email + WhatsApp + bell at 5, 4, 2, 1 days, and when it ends (9 am to 9 pm only) | ✅ (email ⏳ SMTP, WhatsApp ⏳ Meta) |
| Trial ends, no payment | Account pauses by itself: can sign in and view, but no new reviews, replies, alerts or automation; Google stops syncing; no AI is spent | ✅ |
| Owner pays | Dodo confirms the payment to the server, the account reopens at once, and waiting reviews (up to 60 days) are read | ✅ |
| Paid plan ending | Same reminders as the trial | ✅ |
| Paid plan runs out | Same pause as a trial (fixed 17 Nov for the chain plan) | ✅ |
| Owner doesn't want to continue | Nothing to cancel (no auto-renew). They can delete everything from Settings, or simply not pay | ✅ |
| Unpaid for a long time | Warning emails, then the data is deleted after a set period (e.g. 90 days), as the Privacy Policy allows | ❌ |
| Refund | Done in the Dodo dashboard; the plan should then end | ⏳ check with one test refund |
| Abuse / not paying / fraud | Admin → Suspend (blocks sign-in completely); Restore to undo | ✅ |

## 2. Restaurant owner (user) side

| Item | Status |
|---|---|
| Sign up (email or Google), sign in, forgot/reset password, change password | ✅ |
| Welcome email with trial dates, plans link and confirm-email link | ✅ |
| Outlets, QR code per outlet, Google connect, Zomato/Swiggy paste/upload/screenshot | ✅ |
| Dashboard, inbox with AI replies, urgent alerts, Ask Virundhu, weekly summary | ✅ |
| Automation (auto-replies, holding reply, ask guests for reviews) | ✅ |
| Plan and billing page, pay, payment history | ✅ |
| Billing details (company, GSTIN, address) at checkout; numbered receipts to view/print; Dodo tax invoice by email | ✅ |
| Team members and roles | ✅ |
| Export all data, delete account | ✅ |
| Help: how-to video, contact page | ✅ |
| Maps and directions per outlet; dishes and staff insights; website review widget | ✅ (map pictures ⏳ free Maps Embed key) |
| Competitor benchmark (Google Places), installable phone app, billing-software hook | ✅ (benchmark ⏳ Places key) |
| Instagram/Facebook comments by API; Petpooja/POS partner connection | ❌ (needs Meta app review / POS partner approval) |
| Help centre / FAQ page for common questions | ❌ |

## 3. Admin side

| Item | Status |
|---|---|
| All restaurants, plans, usage, AI cost; open any restaurant; suspend/restore | ✅ |
| Revenue: total, by month, this month, active plan value, renewals due, trials ending, payments | ✅ |
| Activity log and bell (sign-ups, payments, deletions, password changes, demo requests) | ✅ |
| Excel download of customers, people, payments, demo requests | ✅ |
| Find and delete test accounts | ✅ |
| Backups status | ✅ |
| Launch checklist inside the admin console | ✅ |
| Receipts with billing details; plan mix 1/3/6/9/12; monthly audit report (Excel, emailed on the 1st) | ✅ |
| Two-step sign-in for the admin (code from an authenticator app) | ❌ |
| Send an announcement email to all customers | ❌ |

## 4. Security

| Item | Status |
|---|---|
| Passwords hashed; never in the page HTML; strong-password rules | ✅ |
| Sign-in session in an HttpOnly cookie; nothing secret in browser storage | ✅ |
| Lock after 5 wrong passwords; rate limits everywhere | ✅ |
| Each restaurant sees only its own data (tested) | ✅ |
| Server refuses to start in production with demo secrets | ✅ |
| HTTPS + browser security rules (deploy/Caddyfile) | ✅ file ready, ⏳ on the server |
| Packages checked for known holes (npm audit, pip-audit) | ✅ |
| Error alerts to you when something breaks (e.g. Sentry, free tier) | ❌ |
| Uptime check (UptimeRobot, free) | ⏳ |

## 5. Legal and money

| Item | Status |
|---|---|
| Privacy Policy, Terms, Data Processing Terms, Refund Policy, Security page | ✅ |
| Consent tick box at sign-up, guest notices, data clean-up job | ✅ |
| Lawyer review of the legal pages | ⏳ |
| GST: ask your CA and Dodo who files it; Udyam registration | ⏳ |
| Trademark search for the name | ⏳ |
| Your phone, address and grievance officer name in .env | ⏳ |

## 6. Before going live

| Item | Status |
|---|---|
| VPS, domain, HTTPS, daily backups by cron, copy backups off the server | ⏳ (waiting for your approval) |
| SMTP email, WhatsApp Business, Google Business Profile API approval | ⏳ |
| Dodo verification and live mode | ⏳ |
| New admin password and SECRET_KEY on the server | ⏳ |
| Final test on the live site with real phones | ⏳ |
| GitHub push | ⏳ (waiting for your approval) |
