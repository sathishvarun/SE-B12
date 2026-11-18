# Virundhu: step-by-step guide

Follow the parts in order the first time. After that you only need Part 3.

There are only two kinds of people:
- **You, the admin**: `admin@virundhu.local` / `Virundhu@Admin2026`. You see every restaurant.
- **A restaurant owner**: registers from your link and sees only their own restaurant.

---

## Part 1. Install the tools (once per Mac)

Open **Terminal** and run each line:

```bash
brew install python@3.12 node
brew install --cask docker
```

Then open **Docker Desktop** once from Applications and wait until it says "running".

---

## Part 2. Put your keys in `.env` (once)

The file is `Virundhu/.env`. Open it in VS Code. Keys live only in this file, and it is never uploaded to GitHub.

### 2a. AI key (already done)
You pasted an **OpenAI** key (it starts with `sk-proj`). It was sitting in the Claude line, so no review could be read. It has been moved, and the file now says:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...        (your key)
OPENAI_TAGGING_MODEL=gpt-4.1-mini
OPENAI_REPORT_MODEL=gpt-4.1
ANTHROPIC_API_KEY=                (leave empty)
```

Only one AI provider is used. If you ever switch to Claude, put the Claude key (starts with `sk-ant-`) in `ANTHROPIC_API_KEY` and set `LLM_PROVIDER=anthropic`. `start.sh` now stops with a clear message if a key is in the wrong line.

### 2b. Payments with Dodo Payments (already done, test mode)
These are set up in your Dodo dashboard (Test Mode), and their values are already in `.env`:

| What | In Dodo | In `.env` |
|---|---|---|
| API key "Virundhu app (test)" | Developer → API Keys | `DODO_PAYMENTS_API_KEY` |
| 1 product "Virundhu subscription (outlets x months)": INR, one time, tax inclusive, **Pay What You Want** ticked (minimum ₹1,000) | Products | `DODO_PRODUCT_FLEX=pdt_0Ns4GiQfCbUinuuwqa9GL` (test mode). Virundhu sets the exact amount for each checkout from the outlet count and months. The 4 older fixed-price products are no longer used; you can archive them. |
| Discount code FIRST10: 20% off, 10 uses in total, once per customer | Sales → Discounts | `PROMO_CODE=FIRST10` (shown on the billing page) |

`PAYMENT_PROVIDER=dodo` picks Dodo. Razorpay code is still there; set `PAYMENT_PROVIDER=razorpay` and add its keys to switch.

**Webhook (later, on the VPS):** in Dodo go to Developer → Webhooks → Add endpoint, use `https://YOUR-DOMAIN/api/v1/billing/dodo-webhook`, and pick the event `payment.succeeded`. Copy the signing secret into `DODO_PAYMENTS_WEBHOOK_KEY`. Locally you don't need it: the app checks the payment with Dodo when the owner comes back from the payment page.

**Going live:** finish "Submit information" (verification) in Dodo, switch to Live Mode, create the same pay-what-you-want product and the discount there (put its new ID in `DODO_PRODUCT_FLEX`), make a live API key, and set `DODO_PAYMENTS_ENVIRONMENT=live_mode`.

---

### 2c. Your company details (shown on Contact, Privacy, Terms, Refunds and the footer)
```
COMPANY_NAME=Virundhu
CONTACT_EMAIL=your email
CONTACT_PHONE=+91 your number
COMPANY_ADDRESS=City, Tamil Nadu
GRIEVANCE_OFFICER=Your full name
```
Before going live, read LAUNCH_GUIDE.md.

### 2d. Email sending (so alerts and password-reset emails really go out)

Easiest for now: your Gmail with an **App password** (about 500 emails a day).
1. Open myaccount.google.com → **Security** → turn on **2-Step Verification** (if it isn't on).
2. Search for **App passwords** in the same page → create one named `Virundhu` → copy the 16-letter password.
3. Put these in `.env` (no spaces in the password) and restart `./start.sh`:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=sathish.varun@gmail.com
   SMTP_PASSWORD=the16letterpassword
   EMAIL_FROM="Virundhu <sathish.varun@gmail.com>"
   ```
4. Sign in as admin → Admin console → **Send test email**. It should arrive in a minute (check spam the first time).

Later, with your own domain (info@virunthu.com), use Zoho Mail or Brevo: they give you an SMTP host, user and password
for the same four lines.

**Admin console → Show checklist** always shows what is still missing before launch.

---

## Part 3. Start the app (every time)

```bash
cd "/Users/sathishvarun/Downloads/SE-B12/Offline Session Task/Virundhu"
bash start.sh
```

The first run takes a few minutes. It:
1. starts Docker, the database and Redis
2. checks your AI key
3. creates the Python virtual environment in `backend/.venv` and installs packages
4. creates the tables and your admin login
5. installs the website packages
6. starts the API (port 8450), the background worker, and the website (port 5450), then opens the browser

**To stop:** press `Ctrl + C` in that Terminal window.

**If you want to run the backend by hand** (not needed normally):
```bash
cd "/Users/sathishvarun/Downloads/SE-B12/Offline Session Task/Virundhu/backend"
source .venv/bin/activate
uvicorn app.main:app --port 8450 --reload
```

---

## Part 3b. Your data: where it is, backups, Excel, test accounts

- **Where the data lives:** everything (restaurants, owners, reviews, payments) is in the PostgreSQL database that runs inside
  Docker on your Mac (Docker volume `pgdata`). On the VPS later, the same database runs inside Docker there.
- **Backups:** `./start.sh` saves a copy once a day into the `backups` folder of the project (newest 30 kept). Make one any time:
  `bash tools/backup/backup.sh`. Bring one back: `bash tools/backup/restore.sh backups/virundhu-YYYY-MM-DD-HHMM.sql.gz`.
  The `backups` folder holds personal data: it's never uploaded to GitHub.
- **Excel of all customers:** sign in as admin → Admin console → **Data** → **Download Excel**.
- **Delete test accounts** (test@test.com and similar): Admin console → **Data** → Test accounts → tick → **Delete selected**.

## Part 4. Test as a restaurant owner

1. Open a **private window** in Chrome (Cmd + Shift + N) and go to **http://localhost:5450**.
2. Click **Start free trial**. Type a name, the restaurant name (for example SMS hotel), the city, an email and a password.
3. You land on that restaurant's **Dashboard**. It is empty.
4. Click **Add reviews** and drop in `samples/virundhu_sample_reviews.xlsx` (15 test reviews).
5. Wait about a minute. Each review gets read: happy or unhappy, the topic, how urgent, and a reply in the guest's language.
6. The bell shows **alerts** for serious complaints (the two food-safety reviews).
7. Open **Inbox**. Click a review, edit the reply, then:
   - Google review → **Post reply on Google** (after Google is connected)
   - Zomato or Swiggy review → **Copy reply and open Zomato/Swiggy**, then paste it there
   - Then click **Mark as replied**
8. Open **Plan and billing** and pay (Part 5).

Reviews that couldn't be read earlier, for example because of the wrong key, are tried again automatically every 5 minutes.

---

## Part 5. Test a payment

1. As the owner, open **Plan and billing**. You'll see the **FIRST10** offer.
2. Type the number of outlets, pick 1, 3, 6, 9 or 12 months, check the total, and click **Pay**. Dodo's payment page opens with that exact amount.
3. Optional: enter `FIRST10` in the discount box to see 20% off.
4. Pay with test details (Test Mode never takes real money):
   - **Card:** `4242 4242 4242 4242`, any future expiry date, any CVV
   - **UPI:** `success@upi` for a successful payment, `failure@upi` for a failed one
5. Dodo sends you back to Plan and billing. You'll see "Payment received", the new plan, and the payment in the list.

When a trial or paid plan ends, the owner can still look, but adding and replying is paused until they pay. The Plan and billing page always stays open.

---

## Part 6. What you see as admin

Sign in with `admin@virundhu.local` / `Virundhu@Admin2026` in your normal window.

- **Admin console**: number of restaurants, paying vs trial, reviews today, urgent reviews nobody replied to, money collected through Razorpay this month, and AI cost.
- **Restaurants table**: each restaurant's plan and trial days. Here you can:
  - **Open** a restaurant to see it exactly as the owner does
  - give **+7 days** of trial
  - change its plan
  - **Suspend** it
- **Bell**: new sign-ups, trials ending, and urgent reviews left unanswered for over 24 hours.

---

## Where reviews come from

| Source | Comes in | Reply goes back |
|---|---|---|
| Google | Automatically every 10 minutes after **Connections → Connect Google** | One click |
| Zomato / Swiggy | The owner pastes or uploads them | Copy, then paste on their partner site |

Zomato and Swiggy don't offer review access to outside software. HOW_IT_WORKS.md explains why.

---

## Part 7. Automation (Automation page)

**Google auto-pilot.** Automation → choose "4 and 5 stars" or "5 stars only" → **Turn on auto-pilot**. Happy Google reviews
then get the reply posted by itself. Unhappy, urgent or hygiene reviews always wait for the owner. Needs Google
connected (and Google's API approval).

**Polite first reply to complaints (optional).** Automation → choose 2, 6 or 24 hours. A 1-2★ Google review with no
reply after that time gets a short, safe reply ("sorry, please call us on ..."). It never admits fault or promises a
refund, and the review stays in the inbox for a person.

**Ask guests for a review.** Automation → paste mobile numbers from today's bills (or upload the billing export CSV) →
tick that the guests agreed → **Ask**. Until WhatsApp is connected you get one-tap WhatsApp links. Nobody is asked twice
in 30 days, and only a scrambled form of each number is stored.

**Monday summary.** On by default. Every Monday 9 am, owners get last week per district and outlet and which outlet to
fix first; each outlet manager gets their own outlet. Email now, WhatsApp once connected.

**From your billing software (optional).** Automation → **Get the key for your billing software** → give the address,
key and example to your POS provider → **Turn on**. After each bill, the guest gets the feedback message on WhatsApp by
itself. Needs WhatsApp connected.

**How you compare nearby (optional).** In Google Cloud, turn on **Places API (New)**, create an API key restricted to
it, and put `GOOGLE_PLACES_API_KEY=...` in `.env`. Google charges per request; Virundhu asks at most once a day per outlet.

**QR feedback link.** Automation → **Download QR to print** → put it on bills, food packets and table cards, or paste the
link in WhatsApp order messages. Add your Google review link (Google Business Profile → Ask for reviews) so every guest
is invited to Google after giving feedback. Note: on your Mac the link starts with `localhost`, so it only works on your
Mac. After deploying, it uses your domain and works on any phone.

**WhatsApp alerts (needs a Meta account, once):**
1. Go to developers.facebook.com → **Create app** → type **Business** → add **WhatsApp**.
2. In WhatsApp → **API Setup**: note the **Phone number ID**. Add your business phone number (or use the test number).
3. Create a permanent token: Business Settings → **System users** → add one → **Generate token** with `whatsapp_business_messaging`.
4. In WhatsApp Manager → **Message templates** → create `virundhu_alert`, category **Utility**, language **English**, body:
   `Urgent review at {{1}}: {{2}}. Open it in Virundhu: {{3}}`. Wait for approval.
5. Put these in `.env` and restart:
   ```
   WHATSAPP_TOKEN=your-permanent-token
   WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
   WHATSAPP_TEMPLATE=virundhu_alert
   WHATSAPP_TEMPLATE_LANG=en
   ```
6. Create two more templates the same way and wait for approval:
   - `virundhu_review_request`, category **Marketing**: `Thank you for eating at {{1}}! How was your food? Tell us in 10 seconds: {{2}}`
   - `virundhu_weekly_summary`, category **Utility**: `Your week at {{1}}: {{2}} See details: {{3}}`
7. Each owner adds their WhatsApp numbers on the Automation page (with the country code, e.g. +919876543210), and each
   outlet's manager mobile in Settings → Outlets.

---

## If something goes wrong

| You see | Do this |
|---|---|
| "Docker didn't start" | Open Docker Desktop, wait, run `bash start.sh` again |
| "Port 8450 is still busy" | `kill $(lsof -ti :8450)` then `bash start.sh` |
| "ANTHROPIC_API_KEY ... isn't a Claude key" | Read Part 2a |
| Reviews stay "not read yet" | Check the Terminal for errors from the worker; check the AI key |
| "Online payment isn't switched on yet" | Check the Dodo values in `.env` (Part 2b) and restart |
