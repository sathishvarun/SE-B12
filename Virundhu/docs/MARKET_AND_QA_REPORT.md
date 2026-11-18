# Virundhu: competitor check, Zomato/Swiggy partner access, and user case studies

Written 16 Nov 2026. Prices and claims of other companies come from their public listings on that date; check again
before quoting them to a customer.

---

## Part 1. Who else does this in India, and how Virundhu compares

### The companies I found

| Company | What it is | What it does with reviews | Price seen |
|---|---|---|---|
| **Restaverse** | Restaurant growth platform for delivery brands and chains | Pulls reviews and feedback from many platforms (it lists Zomato, Swiggy, Google and more) into one inbox, complaint tracking, real-time WhatsApp alerts, aggregator analytics, menu monitoring | GetApp lists flat plans of 199 / 299 / 399 a month (currency not stated) and a free version |
| **uEngage** | Restaurant marketing and ordering suite | Central review inbox and real-time notifications. Their own case study: a 15-outlet brand cut response time by 60% and went from 4.1 to 4.5 on Google in 3 months | Not public |
| **ReplyMaster** | AI auto-reply tool for Indian businesses | AI replies to Google, Zomato, Swiggy, WhatsApp, Instagram and Facebook messages; replies in Hindi, English, Tamil, Telugu, Kannada | Freemium |
| **Reelo** | Customer data, loyalty and WhatsApp marketing for restaurants | QR feedback, nudges guests to Google, WhatsApp campaigns, connects to billing software (Petpooja, DotPe, Restroworks and others) | From about ₹1,000 a month; listings also show ₹30,000 a year |
| **DineOpen** | POS / billing software | Free AI reply generator (you paste the review); Google reviews and feedback in one dashboard | Not public |
| **Reviwee** | Google-only review tool | AI review requests and replies for Google | From ₹1,999 a month |
| **Swiggy "Guru"** | Swiggy's own free AI assistant for its restaurant partners | Helps partners inside Swiggy's partner app (launched for about 2.7 lakh restaurants) | Free for Swiggy partners |
| **Petpooja, UrbanPiper, LimeTray** | POS and order-integration companies | Connect Swiggy and Zomato **orders and menus** to the billing counter. Reviews are not their main product | Varies |

**What this tells us:**
- The idea "all reviews in one place with AI replies" **already exists** (Restaverse, uEngage, ReplyMaster). We must
  not pitch it as brand new.
- Some tools say they "connect" Zomato and Swiggy reviews. There is no public review API, so they most likely use the
  restaurant's own partner login or read the website. That can break at any time and can risk the listing. Virundhu
  chose not to do that; we should say so openly as a trust point.
- Swiggy now gives partners a free AI assistant, and Zomato builds its own AI tools. A tool that only works inside
  one delivery app will keep losing ground to the apps themselves. **Our space is across apps, plus Google and the
  restaurant's own QR, in Tamil.**

### Where Virundhu is genuinely different (use these in the pitch)

1. **Built for Tamil Nadu:** reads Tamil and Tanglish ("chicken la mudi irundhuchu") and replies in the guest's
   language. Most others are English/Hindi first.
2. **Food-safety safety net:** a hygiene complaint is marked urgent even if the AI fails, and alerts the owner and
   that branch's manager within a minute.
3. **Safe automation, not blind automation:** happy reviews reply themselves; complaints get a polite holding reply
   only if nobody answers in time, and never admit fault or promise refunds.
4. **Honest about Zomato/Swiggy:** no scraping, no sharing the owner's partner password.
5. **Pay per outlet, falling with size:** ₹1,499 for one outlet down to ₹649 per outlet for 51+, with free months on
   9 and 12 months. Clear for a 2-outlet mess and a 100-outlet chain.
6. **Ask Virundhu:** "what should I fix first at Gandhipuram?" with numbers computed from real data, not guessed.
7. **Own QR feedback per outlet:** catches the unhappy guest before they post on Zomato.

### What competitors have that we don't (yet), in order of value

| Missing | Who has it | Why it matters | Effort |
|---|---|---|---|
| **Ask every guest for a review on WhatsApp after the bill** | Reelo, Reviewflowz | More reviews, better rating; the single biggest rating lever | Medium (needs WhatsApp keys + guest phone from billing) |
| **Billing / POS link** (Petpooja, DotPe, etc.) | Reelo | Gets the guest's phone and order automatically | High (partner approval per POS) |
| **Instagram and Facebook comments/DMs** | ReplyMaster | Young guests complain on Instagram | Medium (Meta app review) |
| **Weekly WhatsApp summary to the owner** | Several | Keeps owners using the product | Low |
| **TripAdvisor** (hotels, tourist areas like Ooty, Kodaikanal) | Restaverse, Reviewflowz | Tourist restaurants | Medium |
| **Compare with nearby competitors** on Google | Restaverse (benchmarking) | "You are 4.1, the 3 biryani places near you are 4.4" sells itself | Medium (public Google data only) |
| **Mobile app / home-screen app** | Most | Owners live on the phone | Low: make the site installable (PWA) first |
| **Staff mentions** ("Ravi served us well") | Reviewflowz | Motivates staff | Low (AI already reads the text) |

Recommendation: next build **WhatsApp review requests** and the **weekly WhatsApp summary**. Both need only the Meta
WhatsApp keys you are already planning to get.

---

## Part 2. Getting official Zomato / Swiggy access (the "partner key")

**The honest situation**
- Zomato's old public developer API (developers.zomato.com) is closed; the page no longer works.
- Today Zomato and Swiggy give API access to **approved integration partners**, mainly POS and order-management
  companies (Petpooja, UrbanPiper, Restroworks and others), for **orders and menus**.
- I could not find any public form or programme for **review** access. Do not promise customers it is coming.

**What you can do, step by step**
1. **First get customers.** 20 to 50 paying restaurants, ideally including one or two known brands. Platforms only
   talk to partners who bring restaurants.
2. **Ask through your customers' account managers.** Every Zomato and Swiggy restaurant partner has a point of
   contact. Ask a big customer (for example a 10-outlet chain) to request it on their behalf: "We want our review
   tool Virundhu to read and reply to our reviews through an official integration."
3. **Write to the partnership teams** with a one-page proposal: what Virundhu does, number of restaurants, the
   security measures (encryption, DPDP compliance, no scraping), and that it helps reply rates on their platform.
   For Swiggy, partner support has been reachable at partnersupport@swiggy.in.
4. **Expect a business review, NDA and security check** before any sandbox access, as with other platforms'
   integration programmes.
5. **Until then:** keep paste/upload, push QR feedback hard, and (idea) let owners **forward a review screenshot to a
   Virundhu WhatsApp number**, which the AI reads. Still one action, but from the phone they already use.

**Google (needed for real customers, do this first)**
1. Create a Google Cloud project for Virundhu and note the project number.
2. Submit Google's **Business Profile API access form** ("Application for Basic API Access").
3. Google reviews requests in about 14 days, sometimes longer; rejections happen when the use case is vague. Write
   clearly: "Sync reviews of the restaurant's own verified locations into the owner's dashboard and post the owner's
   replies."
4. In parallel, verify the Google sign-in screen (the `business.manage` permission), with the privacy policy and
   domain.

Until both are approved, Google connect works only for test accounts.

---

## Part 3. Case studies from testing Virundhu as a restaurant owner

I signed up as new restaurants (a single outlet and a "Biryani Chain"), uploaded reviews, added outlets, changed
settings, and opened every page on desktop and a phone-sized screen.

| # | What happened to the owner | Why it matters | Status | How it's automated now |
|---|---|---|---|---|
| 1 | Uploaded a file with branch names (RS Puram, Gandhipuram, Peelamedu). **All went to "Main outlet"** with no warning. | Branch reports were wrong for chains | **Fixed** | Unknown branch names in a file now become outlets automatically (within the plan's outlet limit), and the upload result lists them |
| 2 | With the AI unable to read (no key), a 2★ "late and cold food" review had **no urgency**, so the inbox said "nothing urgent". | A complaint could be missed | **Fixed** | Until the AI reads it, every review is sorted by its stars; 1-2★ go to "this week". Food-safety words still go straight to urgent (this already worked: "hair in biryani" alerted) |
| 3 | A new owner landed on an empty dashboard that only said "Upload your first CSV". | The most automatic steps (Google, QR) were hidden | **Fixed** | A 4-step "Get set up" checklist: outlets, Google, QR codes, Zomato/Swiggy |
| 4 | A 10-branch chain had **one QR code** for all branches; the guest had to pick the branch. | Wrong branch, or guests give up | **Fixed** | Every outlet has its own QR code (Settings → Outlets → QR code) with the branch already chosen |
| 5 | Urgent alerts went to the owner, not to **the manager of that branch**. | The person who can act hears last | **Fixed** | Each outlet stores its manager's name, mobile and email; urgent complaints go to them too (email now, WhatsApp once keys are added) |
| 6 | Outlets had only a name and city: no address, district, pincode, phone, manager, Zomato/Swiggy links. | Chains need district-level views | **Fixed** | Full outlet details, grouped by district; edit and hide outlets |
| 7 | Sign-up asked nothing about phone or outlet count. | Can't call leads, can't size the plan | **Fixed** | Mobile and number of outlets at sign-up; brand details (cuisine, dine-in or cloud kitchen, GSTIN, head office) in Settings |
| 8 | An angry Google review sat **unanswered for hours** in public. | Other guests see silence | **Fixed (opt-in)** | Polite holding reply after 2, 6 or 24 hours, with the outlet phone; review stays in the inbox for a person |
| 9 | 3★ "okay" reviews never got any reply. | Mixed guests feel ignored | **Fixed (opt-in)** | Auto-pilot can now include 3★ |
| 10 | The home page said Google, Zomato and Swiggy reviews are "brought into one place", so owners assumed Zomato is automatic. | Wrong expectations, angry customers later | **Fixed** | Wording now says Google and QR are automatic, Zomato and Swiggy need one paste |
| 11 | Every page had the same browser title. | Weak for Google search; confusing tabs | **Fixed** | Each page has its own title |
| 12 | QR codes and email links point to `localhost`. | Printed QR codes won't work for guests | **Open: at deployment** | Set `APP_URL` to the real domain before printing any QR |
| 13 | No emails are actually sent (no email account set up). | No alerts, no password reset | **Open: needs you** | Steps in GETTING_STARTED 2d; Admin console → Send test email checks it |
| 14 | The home page is very long on a phone (about 11 screens). | Owners stop scrolling | **Fixed** | About 6 screens now; details moved to How it works, Why Virundhu and Pricing |
| 15 | Pasting Zomato reviews one by one is slow for a 10-branch chain. | Owners will stop doing it | **Fixed** | Upload partner-app screenshots; the AI picks out every review. Later an official partner integration (Part 2) |
| 16 | No phone number on the Contact page. | Tamil Nadu owners trust a phone call | **Open: needs your number** | Add `CONTACT_PHONE` in `.env` |

### Built after this report (16 Nov night)
WhatsApp review requests, Monday summary per outlet and district, reviews from screenshots, outlets from Excel,
admin launch checklist with test email, installable phone app, WhatsApp chat button, shorter mobile home page.

Then also built: Tripadvisor/Instagram/Facebook reviews (paste, file or screenshot; automatic reading still needs Meta
approval), a billing-software hook any POS can call after each bill, "How you compare nearby" (switches on with a Google
Places key), an English/Tamil website switch (Tamil to be checked by a native speaker), a testimonials section that shows
only real, published quotes, and three captioned demo videos of the real app.

### Automation ideas (original list)
1. **WhatsApp review request after the bill** (biggest rating lever).
2. **Weekly WhatsApp summary per outlet** to the owner and each manager.
3. **Screenshot to WhatsApp → review** for Zomato/Swiggy until an official integration exists.
4. **Auto "what to fix" list per district** every Monday from Ask Virundhu.
5. **Outlets from Excel**: upload all branches at once (name, district, manager...).
