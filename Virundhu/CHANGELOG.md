# Changelog


## 2026-11-19: AI agent team (AI as a service)
- Mani, the lead agent, runs every minute and hands work to Nila (demos) and Tara (support); Autopilot shows a live feed.
- Demos book themselves: open times by email, one-tap booking page, calendar invites, Meet/Zoom/Teams/phone/in person,
  WhatsApp and email to the admin, reminders and follow-up.
- Support answers itself: Tara replies to every ticket and switches a plan on when Dodo shows the money arrived.
- Contact form needs an email and asks how to meet. Site copy: AI staff as a service.

## 2026-11-19: AI staff (AI-as-a-Service)

- **Your AI staff** page (`/app/ai-staff`, `GET /api/v1/ai-staff`): seven named agents with work done in 30 days,
  hours and rupees saved, revenue at risk and won back (assumptions shown).
- **Today's 3 moves**, **Crisis radar** (same complaint 3x at one outlet in 72 h; hygiene 2x) and **Win-back**
  (apology + comeback code in the guest's language, WhatsApp link, tracks returns; table `guest_recoveries`, migration 0017).
- **Owner rules** (`organizations.ai_rules`): banned words and topics that always wait for a person, enforced before
  Google auto-reply.
- Website: Meet your AI staff on Home, `/compare` (what makes Virundhu different), `/whats-next` (live and coming soon).
- Parent company: "Virundhu is a brand of SK Mini Mart" in footer, About, receipts and emails (`PARENT_COMPANY`, `PARENT_GSTIN`).

## 2026-11-18: Suspended accounts are locked until they pay

- When a trial or paid plan ends unpaid, the owner can still sign in, but every menu is greyed out with a lock and
  opens Plan and billing; only Plan and billing, Help and support, Quick help and the bell stay open.
- The server enforces it too: every other API answers 402 until the payment lands, then everything unlocks at once.
- A red "Your account is suspended since <date>" banner with a Pay and unlock button.

## 2026-11-18: Company mailbox and the full customer email journey

- **Admin → Company mailbox**: demo requests, info/support and sent-to-customer counts (total, this week, new or open),
  the latest messages, and an **Open in Gmail** button per company address (MAILBOX_ACCOUNT).
- **Trial reminders** now go 5, 4, 3, 2 and 1 days before the end, each with the owner's first name and a details table.
- **Suspension email** when a trial or plan ends without renewal: data stays safe, features switch off until renewed.
- **Payment confirmation** shows invoice number, months added, outlets covered, plan dates, amount, GST note, payment ID.

## 18 Nov 2026 (Admin console sections, per-restaurant logs, emails log, daily backups)

- Admin console has a grouped left menu: Overview, Customers (Restaurants, Users, Demo requests), Logs (All activity,
  Emails sent, Sign-ins), Help desk (Support tickets, Testimonials), System (Data and backups).
- Every restaurant has its own full log (Restaurants → Logs): sign-ins, every email sent to them, uploads, payments,
  password changes and support requests, with filters.
- Every customer email is recorded (sent or not delivered) in that restaurant's log and in Logs → Emails sent.
- VPS: compressed database backup every day at 03:00 India time, newest 30 days kept, shown in Data and backups.
- Emails: logo, a headline band and Virundhu's own closing line per email type; Reply-To Virundhu.

## 18 Nov 2026 (Customer emails, Google sign-in, launch)

- Customer emails are now a branded Virundhu card (green header, turmeric button for links, help footer) and show
  "Virundhu" as the sender. Emails to the platform admin stay plain.
- Password reset: the link goes to the address the customer signed up with, works once, expires in 30 minutes.
  A "Your Virundhu password was changed" email follows every reset or change (time and device included).
- "Continue with Google" through Google Identity Services: needs only the public client ID.
- Home page no longer moves by itself on phones (live review board has a fixed size).
- Live at https://virundhu.sathishsakthivel.tech (Docker + Traefik HTTPS). 74 tests.

## 17 Nov 2026 (Banana-leaf feast design)

- New look built around a meal served on a banana leaf: deep banana-leaf green, coconut cream, turmeric,
  tomato-rasam red for urgent items. Same colour roles, so every page changed together.
- Backgrounds: hand-drawn food line art (idli, dosa, filter coffee, chilli, curry leaf, review stars and bubbles)
  in `frontend/public/patterns/`. Drawn for Virundhu, so no licence or copyright questions.
- Home hero: a hand-drawn banana-leaf meal with guests' notes floating over each dish; the live review board
  moved to its own section below.
- Checked on 12 screen sizes (320 px phones to 2560 px monitors, phone landscape, iPads): 228 page views,
  no sideways scrolling, no console errors.

## 17 Nov 2026 (Simpler menu, sign out always visible)

- Owner menu grouped by how often it's used: Every day (Dashboard, Reviews to reply, Add reviews, Alerts),
  Understand your guests (Dishes and staff, Ask Virundhu), Set up (Connections, Automation),
  Account (Plan and billing, Settings, Help and support). Hover shows what each page is for.
- Sign out is always visible at the bottom of the menu (the menu scrolls on short screens); on phones there's a
  sign-out icon at the top right and in More.
- Website header: when you're signed in it shows "Open my dashboard" and "Sign out" instead of "Sign in".
- Quick help moved to the bottom right; the WhatsApp button sits above it.

## 17 Nov 2026 (Quick help chat with hand-over to a person)

- **Quick help** button (bottom left) on the website and inside the app: answers from the help guide
  (`backend/app/services/help_guide.md`: Google, Zomato/Swiggy, QR, inbox, automation, payments, trial, sign-in, data).
  Uses the AI when the key is set; otherwise searches the guide. Starter questions for one-tap answers.
- When it can't answer (or "Didn't help? Talk to a person"): inside the app it becomes a support ticket with the chat
  attached; on the website a contact request. The admin is notified (bell + email); questions the guide couldn't answer
  are logged (Activity: "Quick help couldn't answer") so the guide can be improved.
- Admin: **Draft reply with AI** on every ticket writes a reply from the guide and the conversation; you check and send.
  72 tests.

## 17 Nov 2026 (logs, support tickets, your admin email, walk-through report)

- **Sign-in log**: every sign-in (email or Google) with restaurant, time, IP address and device; every wrong password;
  lock-outs (also emailed to the admin). Admin → Data → Log history downloads it as Excel (1 day to 1 year).
  A **daily summary email** at 9 pm lists who signed in, wrong passwords, payments, deletions and open tickets.
  Server log files are kept in backend/logs (10 x 10 MB, oldest deleted, never committed).
- **Support tickets** (VT-00001): owners raise requests from **Help and support** (payment, bug, account, suggestion),
  can link a payment; the admin answers from the **Support** tab and sets the status; every message is emailed and logged.
- **Admin email**: set `SUPERADMIN_EMAIL` in .env to your own address and restart; the admin login moves to it (password
  unchanged) and all admin emails go there.
- `tools/qa/walkthrough_report.py`: a robot uses the app as visitor, owner, guest, attacker and admin, with screenshots,
  and writes an HTML report. 71 tests.

## 17 Nov 2026 (maps, dishes and staff, website widget)

- **Maps and directions**: every outlet linked to its Google Maps listing shows "On Google Maps", a Directions button
  (free, no key) and an embedded map when `GOOGLE_MAPS_EMBED_KEY` is set (Maps Embed API: free, unlimited). Outlets not on
  Google Maps show only the address.
- **Dishes and staff page** (/app/insights): the AI now picks out dishes and staff named in each review (migration 0015);
  the page ranks them with likes vs complaints, a score, the outlet they're mentioned at most, example reviews, and a
  "fix this first" line. 30 days / 90 days / 1 year.
- **Website review widget** (/w/TOKEN, "Website widget" button on each outlet copies the embed code): true average from
  every review, latest 4-5 star reviews with a plain statement of what is shown, and branch directions. The Caddyfile
  allows only this page to be framed. 69 tests.

## 17 Nov 2026 (account deletion done properly)

- Before deleting, the owner sees the balance to pay (always Rs 0: Virundhu is prepaid and never renews by itself; deletion
  is refused if a balance ever exists), paid days left and the last payment.
- After deleting: a confirmation page, and a confirmation email to the owner. The admin gets the bell, an email and a new
  **Deleted accounts** list (Admin → Data) with plan, unused paid days and balance; the monthly report has a Deleted accounts
  sheet. `python -m app.delete_account EMAIL` deletes an account from the command line. 68 tests.

## 17 Nov 2026 (welcome email, receipts, monthly audit report)

- **Welcome email at sign-up**: first name, email, phone, restaurant, city, outlets; trial start and end dates; a
  confirm-your-email link (`/api/v1/auth/verify-email`); and the plans link.
- **Billing details at checkout**: company name, GSTIN (checked) and billing address with pincode, saved on the restaurant and
  sent to Dodo for its invoice.
- **Numbered receipts** (VR-YYYYMM-00001): every payment stores outlets, months, dates covered and a copy of the billing
  details; the owner is emailed; printable receipt page at /app/receipt/:id for the owner and the admin.
- Trial reminders (4/3/2/1 days, with the payment link) stop by themselves once the restaurant pays (tested).
- **Admin**: receipt number and billing details on latest payments; paying restaurants by plan length (1/3/6/9/12 months);
  **monthly audit report** (Excel: summary, payments with GSTIN, plan mix, renewals due next month, idle accounts, new
  sign-ups) downloadable for any month and emailed to the admin automatically on the 1st. Migration 0014. 67 tests.

## 17 Nov 2026 (unpaid accounts pause like a phone bill)

- An ended trial or plan now also stops Google syncing and AI reading (reviews are kept and read automatically, up to 60 days
  back, the moment the restaurant pays). The 21+ outlet "chain" plan now pauses when it runs out too (it was missed).
- LAUNCH_CHECKLIST.md: everything a launch needs, marked built / needs you / not built. 66 tests.

## 17 Nov 2026 (security hardening, revenue dashboard, 14-day trial)

- **Sign-in tokens are hidden from page scripts.** The long-lived session token is now an HttpOnly, SameSite=Strict cookie
  (`vr_session`, path `/api/v1/auth`, Secure on HTTPS) that JavaScript can't read; the short access token lives only in memory.
  Nothing secret is kept in localStorage any more (old tokens are wiped on load). Google sign-in and invitations use the cookie too.
- **Password guessing blocked**: 5 wrong passwords lock that email for 15 minutes (20 per network). Unknown emails and wrong
  passwords get the same answer in the same time.
- **Weak passwords refused** at sign-up, reset, change and invitations: common passwords, repeated characters, and passwords
  containing your name, email or restaurant name.
- **Production safety check**: the server refuses to start in production with a demo admin password, a weak SECRET_KEY or
  without HTTPS.
- **deploy/Caddyfile**: HTTPS plus browser security rules (Content-Security-Policy, HSTS, no framing, no sniffing,
  strict referrer, no camera/mic/location).
- **Package check**: `npm audit` and `pip-audit` report no known vulnerabilities.
- **Every trial is exactly 14 days**: the admin "+7 days" button and the API option are removed; migration 0012 shortens any
  trial that had been extended.
- **Admin revenue dashboard**: total received, this month, last month, this year, what active plans are worth per month,
  renewals due in 30/90 days, a 12-month chart with the next 3 months' renewals, upcoming renewals, trials ending this week
  (with what each would pay), and the latest payments. Payments now record outlets, months and the dates they cover
  (migration 0013). 65 tests.

## 17 Nov 2026 (password safety, trial reminders, admin data tools, backups)

- **Passwords never appear in the page's HTML.** React used to copy what you typed into the input's `value` attribute, so it showed
  in plain text in the browser's Elements panel. Every password box (sign in, sign up, reset, change password, delete account,
  invite, admin password) now uses `SecretInput`, which keeps the text only inside the box.
- **Trial and plan reminders**: 4, 3, 2 and 1 days before a free trial or paid plan ends, and once when it has ended. Each goes once,
  by email to every owner's sign-in email, by WhatsApp to the owner's number (template `WHATSAPP_TEMPLATE_PLAN`, once WhatsApp is
  connected) and to the bell, only between 9 am and 9 pm India time. Migration 0011 (`plan_reminders`).
- **Admin console → Data tab**:
  - **Download Excel**: restaurants, people, payments and demo requests in one .xlsx. Guest reviews are left out on purpose.
  - **Test accounts**: lists restaurants with test emails (test.com, example.com and similar), demo restaurants and test-like
    names; select and delete them with their data and logins. Real-looking restaurants are refused.
  - **Backups**: newest backup, its age and the folder.
- **Backups**: `tools/backup/backup.sh` (keeps the newest 30 in `./backups`, which Git ignores) and `tools/backup/restore.sh`.
  `start.sh` takes one automatically each day before updating the database.
- **Automated tests no longer leave data behind**: every restaurant, login, demo request and activity entry a test run creates is
  deleted when the run ends. 63 tests.

## 17 Nov 2026 (legal pages, browser and mobile check)

- **Privacy Policy rewritten** to the DPDP Rules 2025 notice standard: a table of each kind of personal data, its purpose and how
  long it's kept; consent and how to withdraw it; the right to nominate; complaint to the Data Protection Board; Google user data
  (Limited Use, no AI training); sub-processors; breach notice; visitors outside India; grievance replies within 24 hours / 15 days.
- **Terms of Service rewritten**: 1/3/6/9/12-month plans (old text said 1 or 12), no automatic renewal, all-inclusive price, your
  content stays yours with a limited licence, reviews belong to guests, no fake/incentivised/gated reviews, content complaints,
  indemnity, Coimbatore courts, 15 days' notice of changes.
- **New Data Processing Terms page** (`/data-processing`, in the footer): the restaurant is the data fiduciary for guest data and
  Virundhu its processor (DPDP Act s. 8(2)); breach notice to the restaurant within 48 hours; deletion from backups within 30 days.
- **Refund policy** updated to match the plans.
- **Clearer guest notices** on the QR feedback page and the "ask guests for a review" consent box.
- **Daily data clean-up** (worker, 3:10 am IST): deletes guest-number hashes and contact messages older than a year and expired
  sign-in/reset tokens, so the retention periods in the Privacy Policy are enforced. New test (61 tests now).
- **Browser and mobile check** (`tools/qa/browser_sweep.py`): 25 pages x desktop, iPhone and Android = 75 views; 0 console errors or
  warnings, 0 failed requests, no sideways scrolling, no hidden text after animations. The how-to video now loads only when played;
  sliders, a checkbox and the "Pause the story" button are bigger to tap on phones.

## 17 Nov 2026 (how-to video)

- **New "How to use Virundhu" video**, silent, full HD (1920x1080, 30 fps): 14 steps from creating an account to
  choosing a plan, each with a clear caption card and a marker showing where to click; opening and closing cards with
  the founder's photo. The step list next to the player jumps to each step. Replaces the narrated tour (removed, with
  its audio). Built by `tools/howto_video`.

## 16 Nov 2026 (late: tour video remade, English only)

- **Clearer voice:** Kokoro `am_michael`, chosen by measuring which voice a speech recogniser understood best (94% of
  words exactly right in the final video; the previous voice garbled whole sentences).
- **Smooth video:** recorded from a real browser window at a steady 30 fps in sharp quality, every page opened once
  before recording (no blank loading screens), smooth scrolling, no browser bars, and no jumps to other sites.
- **English only** for now; the Tamil video was removed. A Tamil recording can be added later (see
  `tools/demo_video/README.md`) and the English/Tamil switch appears by itself.
- The founder's photo now appears in the presenter bubble, with a moving voice wave (`tools/demo_video/presenter-photo.jpg`).

## 16 Nov 2026 (night: tour video in English and Tamil)

- **Demo video in two languages:** a switch above the player changes between English (Indian-accent AI voice) and
  Tamil (everyday spoken Tamil, the way people in Tamil Nadu talk, with the usual English words). Captions match the
  voice; chapters jump to the same part in either language. Voices: AI4Bharat Indic-TTS, free and offline.
  Files: `frontend/public/demo/tour-en.mp4`, `tour-ta.mp4`, posters and `tour.json` (chapter times).

## 16 Nov 2026 (night: English only, narrated tour)

- **English only:** the Tamil switch and every piece of Tamil text are gone from the website, samples and demo data.
  (Virundhu still reads reviews guests write in Tamil and Tanglish.)
- **Narrated product tour** (How it works → Watch it work): 2½ minutes covering the whole flow, with an AI voice
  speaking as the founder, captions, a presenter bubble and chapters you can jump to. Replaces the three silent videos.
  Rebuild it with `tools/demo_video` (see its README).

## 16 Nov 2026 (late night: new look, demo videos, the remaining features)

- **New look and motion:** headings now use Anek Tamil wide and heavy (body stays Hind Madurai), with one type scale
  (`type-hero`, `type-section`, `type-lead`). A kolam draws itself in the hero, page headers and the sign-in panel;
  headlines rise in word by word; sections fade up on scroll; numbers count up; cards lift on hover. In the app, the
  sidebar highlight slides between pages and pages fade in. Reduced-motion settings are respected.
- **Sign-in / sign-up:** animated side panel with rotating messages, kolam and the live board.
- **Demo videos** (How it works → Watch it work): three captioned screen recordings of the real app with a fictional
  restaurant: "A morning with Virundhu", "Set up a chain in 2 minutes", "What your guest sees" (`public/demo/*.mp4`).
- **More platforms:** Tripadvisor, Instagram and Facebook reviews can be pasted, uploaded or read from screenshots
  (migration `0010`).
- **Billing-software hook:** `POST /api/v1/hooks/bill` with `X-Virundhu-Key` asks each guest automatically after the
  bill (needs WhatsApp connected). Key made on the Automation page, shown once, stored hashed.
- **How you compare nearby** (Dashboard): your Google rating vs restaurants around each outlet, cached daily. Needs
  `GOOGLE_PLACES_API_KEY`.
- **Testimonials:** admin adds real customers' words (Admin console → testimonials); the home page shows only
  published ones.
- Tests: 60 passing.

## 16 Nov 2026 (night: everything from the market and QA report)

- **Ask guests for reviews on WhatsApp** (Automation): paste numbers or upload a billing export; consent tick required;
  never the same guest twice in 30 days; only a hash of each number is stored (`review_requests` table, migration
  `0009`). Sends automatically with WhatsApp keys, otherwise gives one-tap wa.me links.
- **Monday summary** (Monday 9 am IST): per district and outlet, unhappy count, urgent still open, which outlet to fix
  first. Owners get all outlets, managers their own. Email now, WhatsApp once keys are set. Switch in Automation.
- **Reviews from screenshots** (Add reviews): upload Zomato/Swiggy partner-app screenshots; the AI lists the reviews;
  duplicates skipped.
- **Upload outlets from Excel/CSV** (Settings → Outlets) with a template; same-name outlets are updated.
- **Admin launch checklist** (APP_URL, SMTP, AI key, admin password, phone, payments, Google, WhatsApp) and
  **Send test email**.
- **Installable app** (home-screen icon on phones) and a **WhatsApp chat button** on the website once `CONTACT_PHONE`
  is set.
- **Shorter home page on phones** (about 9,000 → 5,300 px): the review journey stays on How it works, before/after on
  Why Virundhu, the savings calculator on Pricing.
- New WhatsApp templates: `WHATSAPP_TEMPLATE_REVIEW`, `WHATSAPP_TEMPLATE_SUMMARY`. Gmail SMTP steps in GETTING_STARTED 2d.
- Tests: 56 passing.

## 16 Nov 2026 (evening: chains, safer automation, first-day setup)

- **Outlet details:** address, district, pincode, outlet phone, manager name/mobile/email, Google Maps, Zomato and
  Swiggy links. Outlets are grouped by district; edit and hide (old reviews stay). Migration `0008`.
- **One QR code per outlet** (`/f/<token>?o=<outlet id>`): the guest page shows the branch already chosen.
- **Branch manager alerts:** urgent complaints also go to that outlet's manager (email; WhatsApp when keys are set).
- **Brand details:** owner mobile and outlet count at sign-up; cuisine, dine-in/cloud kitchen, GSTIN, head office in
  Settings.
- **Uploads create outlets** named in the file's `outlet` column (within the plan limit) instead of putting
  everything under "Main outlet".
- **Never hide a complaint:** if the AI can't read a review yet, it's sorted by its stars (1-2★ → this week).
- **Auto-pilot for 3★** (optional) and a **polite holding reply** to 1-2★ Google reviews left unanswered for 2, 6 or
  24 hours (optional; no blame, no refund promise; the review stays in the inbox).
- **First-day checklist** on the empty dashboard; page titles for every page; home page now says plainly that
  Zomato and Swiggy need one paste.
- **docs/MARKET_AND_QA_REPORT.md:** competitors in India, Zomato/Swiggy/Google access process, 16 user case studies.
- Tests: 50 passing.

## 16 Nov 2026 (pricing by outlets and months, admin activity log)

- **Outlet-based pricing, worked out automatically:** price per outlet per month falls with the outlet count
  (₹1,499 → ₹1,199 → ₹949 → ₹799 → ₹649 for 51+). Pay for 1, 3, 6, 9 or 12 months: 5%, 10%, 10% + 1 free month,
  15% + 2 free months. One table in `services/pricing.py`; migration `0007` adds `organizations.paid_outlets`.
- **Calculator** on the Pricing page and on Plan and billing: outlets box, slider, month buttons, live total, per-outlet
  cost, savings and free months. Public endpoints `GET /billing/pricing` and `GET /billing/quote`.
- **Dodo checkout** now uses one pay-what-you-want product (`DODO_PRODUCT_FLEX`) and the server sets the amount.
  Underpaid payments are refused. Paid outlet count sets the outlet and review limits.
- **Admin activity log** (`activity_log` table): sign-ups, password changes, password resets, deleted accounts,
  payments and demo requests. Admin console → Activity tab and the admin bell. Kept after an account is deleted.
  Deleted accounts, payments and demo requests are also emailed to the admin.
- Admin monthly revenue now = price tier × paid outlets for paying restaurants.
- Tests: 47 passing (new: pricing rules, underpaid payment refused, public quote, admin sees activity).

## 16 Nov 2026 (launch readiness: privacy, security, trust)

- **No more sample data in the product:** the admin-only fake Zomato/Swiggy test feed, the one-click demo sign-in and the
  nightly demo job are gone. Marketing animations are labelled "Example".
- **Legal and trust pages:** `/privacy` (DPDP-style notice: what, why, AI processing, Google Limited Use statement,
  processors, retention, rights, grievance officer), `/terms`, `/refunds`, `/security`. Footer has a Trust column,
  contact email/phone and a copyright line. Company details come from `.env` (`COMPANY_NAME`, `CONTACT_EMAIL`,
  `CONTACT_PHONE`, `COMPANY_ADDRESS`, `GRIEVANCE_OFFICER`).
- **Consent:** sign-up requires ticking "I agree to the Terms and Privacy Policy"; the time is saved
  (`users.terms_accepted_at`, migration `0006`). Google sign-up shows the same notice. The QR guest page and the
  Contact form say who gets the data and link the Privacy Policy.
- **Account safety:** forgot password + reset page (single-use link, 1 hour, no account enumeration, signs out all
  devices), change password (owners in Settings, admin in the Admin console).
- **Data rights:** Settings → Account and privacy → Download all my data (CSV, Excel-friendly) and Delete my restaurant
  (type the name + password; deletes everything immediately).
- **Security headers** on every API answer (nosniff, no framing, referrer policy, no-store, HSTS on HTTPS).
- **LAUNCH_GUIDE.md:** the owner's journey with what protects them at each step, your go-live checklist, security status
  and trust ideas.

## 16 Nov 2026 (public website)

- The single long landing page is now a proper website with its own header, mobile menu and footer:
  **Home** (`/`), **How it works** (`/how-it-works`), **Why Virundhu** (`/about`), **Pricing** (`/pricing`),
  **Contact** (`/contact`), plus Sign in and Start free trial.
- New interactive pieces (`components/site/`): a before/after toggle ("a day without Virundhu" vs "with Virundhu"),
  an auto-playing six-step story that follows one review from the guest's phone to the fix (tap any step), automation
  cards with mini previews, and a time-saved calculator with its assumptions shown.
- How it works: a sources → Virundhu → outputs diagram and an honest "what's automatic" table per source.
- Why Virundhu: purpose, a before → now timeline, and what we stand for.
- Contact: demo-request form (spam-protected, rate limited) saved as a **lead** and emailed to the admin; the Admin
  console has a new **Demo requests** tab with WhatsApp/email links and a status (new, contacted, won, lost).
  Migration `0005` adds the `leads` table.
- FAQ and pricing text corrected (auto-pilot, QR feedback, GST included, Dodo Payments). Removed the old
  `Landing.tsx` and `OutletReport.tsx`.

## 16 Nov 2026 (automation)

- **Google auto-pilot** (`services/autopilot.py`): after a Google review is read, the reply draft is posted by itself if
  auto-pilot is on, stars >= 4 (or 5 only), the AI says positive, urgency low, not hygiene, no safety flag, the plan is
  active and nobody has replied. Failures leave the review for the owner. Inbox shows "Replied on Google automatically".
- **Own QR feedback link** (`routers/feedback.py`, page `/f/<token>`): guests rate the food without signing in; saved as
  platform `direct` ("QR feedback") with optional name and phone/email, read by the AI and alerted like any review.
  Rate limited, hidden honeypot field against bots. After sending, every guest (not only happy ones, per Google's
  rules) is invited to write a Google review if the owner saved their Google review link.
- **WhatsApp alerts** (`services/whatsapp.py`): urgent reviews send an approved template message through Meta's WhatsApp
  Cloud API to up to 5 numbers, once per number per review. Off until `WHATSAPP_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID`
  are set.
- New **Automation** page for owners with all three. Migration `0004` adds the new columns and the `direct` platform.

## 16 Nov 2026 (later)

- **Ask Virundhu**: a chat page where the owner asks about the last 30 days of reviews. Counts are computed in SQL
  and passed as DATA; the model only explains and ranks (Priority 1, 2, 3: food safety first, then unanswered urgent
  reviews, then the biggest complaint topic, then slipping outlets). Answers in the owner's language. Rate limited to
  20 a minute; cost added to the restaurant's AI usage. `POST /api/v1/assistant/chat`.
- README: real scenario, flow diagram, why restaurants pay, the honest Zomato/Swiggy answer, a 10-minute pitch.

## 16 Nov 2026

**Roles made simple**
- Only two people: the platform admin and the restaurant owner. Removed demo logins, the sample restaurant, the
  outlet-manager role and the Team tab. Seeding now creates only the admin and deletes the old sample restaurant
  (`SEED_DEMO_RESTAURANT=true` brings it back for the automated tests only).

**Reviews**
- Zomato and Swiggy: no public API for reviews or replies (their partner APIs cover orders and menus only), and
  scraping breaks their rules. The owner pastes reviews; in the inbox, **Copy reply and open Zomato/Swiggy** copies the
  reply and opens their partner site.
- Google: reviews sync every 10 minutes and replies post back with one click.
- The fake-review test feed is now visible only to the admin (when opening a restaurant).
- Reviews the AI couldn't read are retried every 5 minutes (`retry_unread_tick`).

**AI**
- The key in `.env` was an OpenAI key placed in the Claude line, so reviews weren't being read. Switched to
  `LLM_PROVIDER=openai` (`gpt-4.1-mini`). `start.sh` now stops with a clear message if a key is in the wrong line.
- OpenAI uses tool calling for structured output (strict JSON mode rejects some schema shapes).

**Payments**
- Added a **Plan and billing** page (owners only, stays open after a trial ends).
- Dodo Payments (default, `PAYMENT_PROVIDER=dodo`): hosted checkout; the plan turns on only after the server reads the
  payment back from Dodo (`/billing/confirm`) or a verified webhook (`/billing/dodo-webhook`).
- Dodo test mode set up: 4 INR products (GST included), API key with minimum permissions, code FIRST10.
- Razorpay kept as an alternative (`PAYMENT_PROVIDER=razorpay`).
- An expired paid plan becomes read-only (HTTP 402) like an expired trial.
- Admin console shows money collected this month.

**Fixes**
- The alerts list opened behind the dashboard cards.
- Ports moved to 8450 (API) and 5450 (website) because 8000/8001 were in use on the Mac.

**Docs**
- New GETTING_STARTED.md (full step-by-step), HOW_IT_WORKS.md, this changelog; README, CLAUDE.md, INITIAL.md, PRP and
  skills updated.
