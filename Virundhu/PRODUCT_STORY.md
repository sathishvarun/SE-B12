# Virundhu: the product story

**Live:** https://virundhu.sathishsakthivel.tech
**One line:** every review a restaurant gets, from every app, in every language Tamil Nadu speaks, read the moment it lands, with the serious ones on the owner's phone within a minute.

*Virundhu* (விருந்து) means a feast served to a guest. In Tamil homes the guest is treated like god, and the host keeps asking "is everything all right?". That is the whole product: a host who hears every guest.

---

## 1. The problem we set out to solve

A typical restaurant in Coimbatore, Chennai or Madurai today:

- Gets reviews in **four or five places**: Google Maps, Zomato, Swiggy, WhatsApp messages, and the odd Instagram comment.
- Reads them in **three languages**: English, Tamil script, and Tanglish ("sambar la uppu jaasthi", "parotta semma").
- Has an owner or manager who checks these apps **when they remember**, usually late at night, often days later.
- Misses the reviews that matter most: *"found hair in the biryani"*, *"my child got sick after eating here"*. One unanswered food-safety review can sink a rating and, in the worst case, bring a food-safety officer to the door.
- Replies with the same copy-paste "Thank you for your feedback" to everyone, which guests notice.

### What existed before Virundhu

| Option | Why it falls short for a Tamil Nadu restaurant |
|---|---|
| **Checking each app by hand** | Slow, easy to forget, no alerts, and no record of what was handled |
| **Global review-management tools** | Priced in dollars for large chains, English-first, built for hotels and US retail, and they don't understand Tanglish or cover Zomato and Swiggy the way Indian restaurants need |
| **The partner apps' own dashboards** | Each one shows only its own reviews. Nobody puts Google, Zomato, Swiggy and walk-in guests side by side |
| **Hiring someone to monitor reviews** | Costs far more than a subscription, and still misses the 11 pm complaint |

---

## 2. What Virundhu does now

### For the restaurant owner
- **One inbox for every review**: Google (synced automatically), Zomato and Swiggy (paste, upload a file, or upload a **screenshot**: the AI picks out every review on it), and guests' own feedback from a **QR code** on the bill or the parcel.
- **Reads every review like a person would**: happy or unhappy, what it's about (food, service, delivery, hygiene, price, staff), how urgent, a one-line summary, and a **reply draft in the guest's own language**.
- **Instant alerts**: a food-safety or hygiene complaint reaches the owner and that branch's manager by bell and email (WhatsApp ready) **within a minute**.
- **Reply in one tap**: copy the reply and the right partner site opens; Google replies can be posted straight back. Happy 4-5★ Google reviews can be thanked automatically.
- **Dishes and staff insights**: which dishes guests praise or complain about, and which staff names come up, so the kitchen knows exactly what to fix.
- **Ask Virundhu**: ask in plain words ("what did people complain about this week?") and get the top 3 priorities.
- **Many branches, one view**: per-outlet QR codes, managers, maps and directions, and a review widget for the restaurant's own website.
- **Quick help**: a chat in the corner that answers from the Virundhu guide, and hands over to a real person when it can't.

### For the guest
- Scans a QR code, taps stars, writes a line in any language. No app, no sign-up. Happy guests are then invited to leave the same review on Google.

### For us, the Virundhu team (admin)
- Every restaurant, its plan, trial days, review counts per platform, money collected and AI cost in one console.
- Revenue dashboard (monthly, total, upcoming), plan mix, GST invoices, unpaid accounts paused automatically, monthly audit Excel by email.
- Support tickets with **AI-drafted replies** that we check before sending, a sign-in log with IP and device, a daily 9 pm digest, data export and backups.

---

## 3. Why Virundhu is the best choice for this market

1. **Built for Tamil Nadu, not translated for it.** It understands Tanglish and Tamil script natively and replies the way a local host would.
2. **Covers the apps restaurants actually live on.** Zomato and Swiggy have no public review API, so we made the next best thing fast: paste, file or a screenshot, read in seconds.
3. **Catches what can hurt you, in a minute.** Food-safety complaints are treated as emergencies, not as one more review in a list.
4. **The AI drafts, a person decides.** Complaint replies are never sent blindly, so the restaurant's voice stays its own.
5. **Priced for Indian restaurants.** ₹1,499 per outlet a month, down to ₹649 for big chains, 1 to 12-month plans, GST invoices, and a 14-day free trial with no card.
6. **Private and lawful by design.** Built around India's DPDP Act 2023: consent at sign-up, data download, account deletion, data kept only as long as needed, and a grievance contact.
7. **Secure from day one.** Safe sign-in cookies, lockout after wrong passwords, rate limits, strict browser security rules and HTTPS everywhere.

---

## 4. Concepts used

| Concept | Where it shows up |
|---|---|
| **LLM structured output** | Every review returns fixed fields: sentiment, category, urgency, language, summary, reply |
| **Multilingual NLP** | Tamil, Tanglish and English in, the guest's language out |
| **Grounded answering** | Quick help answers only from the help guide, otherwise hands over to a person |
| **Human-in-the-loop AI** | Complaint replies and support replies are drafts a person approves |
| **Vision OCR with an LLM** | Screenshots of Zomato/Swiggy reviews become separate reviews |
| **Event-driven alerts** | Serious reviews trigger bell, email and WhatsApp alerts |
| **Background jobs and schedules** | Google sync, AI reading, trial reminders, daily digest, monthly audit |
| **Multi-tenant SaaS with roles** | Each restaurant sees only its own data; admin, owner and staff permissions |
| **OAuth 2.0** | Google sign-in and Google Business Profile reviews |
| **Subscription billing with webhooks** | Trials, plans, invoices, automatic pause for unpaid accounts |
| **Privacy by design** | DPDP Act 2023 consent, export, deletion, retention |
| **Containers and a reverse proxy** | Docker services behind Traefik with automatic HTTPS |
| **Automated testing** | Backend tests, a browser walk-through, a 12-screen-size sweep |

Stack: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Redis + ARQ, LangChain (OpenAI or Claude, one at a time), React 19, TypeScript, Vite, Tailwind CSS v4, Playwright, Docker, Traefik.

---

## 5. How it was built

Virundhu started as a brief for a generic "review analysis" demo. We turned it into a product a real restaurant owner would pay for.

| Stage | What happened |
|---|---|
| **Idea** | Picked one market (Tamil Nadu restaurants and cloud kitchens) and one painful moment (the missed food-safety complaint) |
| **Name** | *Virundhu*, the Tamil word for a feast for guests. Checked against existing restaurant names and kept it, with "Every guest, heard" as the promise |
| **Core build** | Review intake from Google, QR, paste, file and screenshot; AI reading in three languages; inbox, dashboard and instant alerts |
| **Business layer** | Per-outlet pricing for chains, 1-12 month plans, 14-day trial with reminders, GST invoices and receipts, automatic pause for unpaid accounts, Dodo Payments |
| **Trust layer** | Privacy Policy, Terms, Refunds and Security pages under DPDP Rules 2025; data export and account deletion with a balance check; sign-in log and lockout |
| **Admin layer** | Admin console with revenue, plan mix, audit Excel, support tickets, deleted-accounts list, backups and data export |
| **Owner insights** | Dishes and staff insights, maps and directions, website review widget, Ask Virundhu |
| **Help** | Quick help chat that answers from the guide and hands over to a person; AI-drafted support replies for the admin |
| **Design** | Started with a dark "kolam" look; redesigned as a **banana-leaf feast**: banana-leaf green, coconut cream, turmeric, and hand-drawn food line art (idli, dosa, filter coffee, chilli, curry leaf). Simpler menu grouped by how often owners use it |
| **Quality** | 72 backend tests, a 23-step browser walk-through, 228 page views across 12 screen sizes with no layout or console problems, dependency security audit, secret scan |
| **Launch** | Docker on a VPS behind Traefik with automatic HTTPS at virundhu.sathishsakthivel.tech |

---

## 6. Honest limits today

- **Zomato and Swiggy** don't offer a public review API, so their reviews come in by paste, file or screenshot, and replies are copied and posted on their partner sites.
- **Posting replies to Google** needs Google's Business Profile API approval for the account.
- **WhatsApp alerts** are built and switch on once a WhatsApp Business (Meta Cloud API) account is added.

---

## 7. Try it and tell us what you think

- Open **https://virundhu.sathishsakthivel.tech** and start the 14-day free trial (no card needed).
- Watch the 2-minute "How to use Virundhu" video on the How it works page.
- Have feedback or found a problem? Use **Quick help** (bottom right) or the **Contact** page. Every message reaches a real person.
