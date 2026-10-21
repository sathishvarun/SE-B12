# Day 2 Assignment – n8n AI Agent Workflows

Three AI-agent workflows built in n8n (self-hosted on Hostinger), all using OpenAI **gpt-5-mini**.

| # | Workflow | Trigger | Status |
|---|----------|---------|--------|
| 1 | LinkedIn Post Approval | n8n Form | Draft (not published) |
| 2 | Gmail Chat Agent (Emergent) | Webhook (POST) | Published |
| 3 | Tamil Nadu Weather – Telegram Bot | Telegram message | Published |

---

## 1. LinkedIn Post Approval

**Link:** https://n8n-2fqi.srv2061895.hstgr.cloud/workflow/jMofMENLH6DrOYfP

**Short description:** Enter a topic in a form → a Writer Agent drafts a LinkedIn post → a Reviewer Agent scores and improves it → the final post is emailed for human approval → approved posts are saved to Google Sheets.

**Flow**
```
LinkedIn Topic Form → Writer Agent → Reviewer Agent → Send for Approval (Gmail) → Approved?
                                                                                 ├─ true  → Save Approved Post (Google Sheets)
                                                                                 └─ false → Rejected – Nothing Saved
```

**Key points**
- **Writer Agent** – B2B LinkedIn ghostwriter: strong hook in line one, 120–150 words, one CTA, max 3 hashtags, max 2 emojis.
- **Reviewer Agent** – strict editor: checks hook, clarity, CTA, length and hashtags, rewrites the weakest part, returns only the final post.
- **Human-in-the-loop** – Gmail *Send and Wait* with Approve / Reject buttons (waits up to 1 day).
- **Output** – approved posts appended to Google Sheet (Sheet2: Date, Topic, Final Post, Status).

---

## 2. Gmail Chat Agent (Emergent)

**Link:** https://n8n-2fqi.srv2061895.hstgr.cloud/workflow/28Rt3frpeCaJVq2y

**Short description:** A chat-based Gmail assistant for an Emergent front-end app. The user chats in plain language; the agent searches/summarises emails and drafts and sends emails only after confirmation.

**Flow**
```
Emergent Chat Webhook (POST) → Prepare Input → Gmail Agent → Send Reply to Emergent
                                                 ├─ Model:  OpenAI (gpt-5-mini)
                                                 ├─ Memory: Chat Memory (last 10 messages per sessionId)
                                                 └─ Tools:  Search Emails, Send Email
```

**Key points**
- **API contract** – request `{ "message": "...", "sessionId": "..." }` → response `{ "reply": "...", "sessionId": "..." }`.
- **Endpoint** – `POST /webhook/gmail-chat`
- **Search Emails** – uses Gmail search syntax (e.g. `is:unread newer_than:1d`), returns up to 10 emails.
- **Safety rule** – shows a preview (To, Subject, Body) and asks "Shall I send?" before sending.
- Replies in the user's style – English, Tamil or Tanglish; IST-aware date/time.

---

## 3. Tamil Nadu Weather – Telegram Bot

**Link:** https://n8n-2fqi.srv2061895.hstgr.cloud/workflow/c9nIUWHb1AFBitu0

**Short description:** A conversational Telegram bot that chats naturally and gives live weather for any Tamil Nadu / Indian city, using Open-Meteo with an automatic wttr.in fallback and a human-in-the-loop step before sending emails.

**Flow**
```
Telegram Message In → Weather Assistant → Send Reply (Telegram)
                        ├─ Model:  OpenAI Chat Model (gpt-5-mini)
                        ├─ Memory: Chat Memory (last 50 messages per Telegram chat)
                        └─ Tools:  Weather_Primary (Open-Meteo)
                                   Weather_Backup  (wttr.in)
                                   HITL (Telegram send-and-wait) → Send a message in Gmail
```

**Key points**
- **Fallback logic** – always calls Open-Meteo first (lat/long); if it fails or returns no data, calls wttr.in by city name. Never invents numbers.
- **Reply format** – City, condition, temp (feels-like), humidity, rain, wind, one advice line, and the data source.
- **Human-in-the-loop** – any Gmail send goes through Telegram approval first.
- Replies in Tamil, English or Tanglish; phone-friendly plain text with emojis.

---

## Tech Stack
- **n8n** (self-hosted, Hostinger VPS)
- **OpenAI** gpt-5-mini – LLM for all agents
- **Gmail** (OAuth2) – approvals, search, send
- **Google Sheets** – storage for approved posts
- **Telegram Bot API** – chat interface and HITL
- **Open-Meteo / wttr.in** – free weather APIs
- **Emergent** – chat front-end calling the webhook

## Concepts Covered
- AI Agent node with Chat Model, Memory and Tools
- Multi-agent chain (Writer → Reviewer)
- Human-in-the-loop approvals (Gmail and Telegram send-and-wait)
- Tool fallback / error handling
- Webhook-based API for an external app
- Session-based conversation memory
