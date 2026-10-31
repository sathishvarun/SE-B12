"""
SMART HELP DESK  -  single-file version (AutoGen multi-agent + Streamlit)
=========================================================================
Router (main) agent -> department agent (Support/Finance/Marketing/Sales/HR/IT)
-> Resolution agent -> Log agent (TXT + CSV, escalation) + ticket history + weekly summary.

SETUP ON MAC (Terminal):
  mkdir ~/helpdesk && cd ~/helpdesk          # put this file here
  python3 -m venv .venv && source .venv/bin/activate
  pip install 'autogen-agentchat==0.7.5' 'autogen-ext[openai]==0.7.5' 'streamlit>=1.45' 'python-dotenv>=1.0' 'pandas>=2.0' 'openpyxl>=3.1' 'requests>=2.31'
  streamlit run helpdesk_app.py              # first run creates .env, knowledge_base/, logs/, .streamlit/
  -> open the new .env file, paste OPENAI_API_KEY (SERPAPI_API_KEY optional), save,
     then stop (Ctrl+C) and run the same command again.  App: http://localhost:8501

VPS (Ubuntu): same steps, then run:
  streamlit run helpdesk_app.py --server.address 0.0.0.0 --server.port 8501
  (set APP_PASSWORD in .env so the page is protected)
"""
from datetime import date, datetime, timedelta
from datetime import datetime
from pathlib import Path
from typing import Callable
import asyncio
import csv
import io
import json
import os
import re
import threading

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import (TextMessage, ToolCallExecutionEvent,
                                        ToolCallRequestEvent, ToolCallSummaryMessage)
from autogen_agentchat.teams import RoundRobinGroupChat
from dotenv import load_dotenv
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

# ============================================================================
# First-run bootstrap: create .env, theme settings and knowledge base files if missing
# ============================================================================
_HERE = Path(__file__).resolve().parent
_ENV_TEMPLATE = "# Copy this file to .env and fill in your own keys.  NEVER commit .env to GitHub.\n\n# Required: OpenAI key from https://platform.openai.com/api-keys\nOPENAI_API_KEY=sk-your-key-here\nOPENAI_MODEL=gpt-4o-mini\n\n# Optional: live web search for Marketing/Sales agents (https://serpapi.com/manage-api-key)\nSERPAPI_API_KEY=\n\n# Optional: use another OpenAI-compatible provider instead (Groq, Gemini, Ollama...)\n# OPENAI_BASE_URL=https://api.groq.com/openai/v1\n\n# Optional but recommended on a VPS: password to open the app\nAPP_PASSWORD=\n\n# Optional: show source file names and every agent's step in the chat (demo / assignment screenshots).\n# Keep false for real employees - they only see the answer.\nSHOW_AGENT_STEPS=false\n"
_STREAMLIT_CONFIG = '[server]\nheadless = true\nport = 8501\n\n[browser]\ngatherUsageStats = false\n\n[theme]\nprimaryColor = "#FF6B1A"\n\n[client]\ntoolbarMode = "minimal"\n'
_KB_FILES = {
    "customer_support/client_portal_and_releases.md": "# SK Soft Technology Client Portal, Access and Releases\n\n## Client portal login problems\n1. On the portal login page click Forgot Password and enter your registered work email.\n2. Use the reset link within 30 minutes.\n3. The new password needs at least 12 characters with upper case, lower case, a number and a symbol.\n4. After 5 wrong attempts the account is locked for 30 minutes.\n5. Single sign-on (SSO) users must reset their password with their own company IT team.\n\n## Adding or removing client users\n- Only the client's named admin can request new portal users or removal of users, by raising a P4 ticket.\n- Requests are completed within 1 business day.\n\n## Reporting a bug\n- Raise a ticket with the steps to reproduce, the expected result, the actual result, the browser or app version and screenshots.\n- Confirmed bugs are given a bug ID and planned into a release based on severity.\n\n## Releases and maintenance windows\n- Planned releases happen every second Saturday between 10 PM and 2 AM IST.\n- Clients are informed by email 5 business days before each release, with release notes.\n- Emergency hotfixes for P1 issues can be deployed at any time after client approval.\n",
    "customer_support/client_support_sla.md": "# SK Soft Technology Client Support and SLA Policy\n\n## Severity levels and response times\n- P1 Critical: production is down or no users can log in. First response within 15 minutes, 24x7. Target fix or workaround within 4 hours.\n- P2 High: a major feature is broken for many users, no workaround. First response within 1 hour. Target fix within 1 business day.\n- P3 Medium: a feature is broken but a workaround exists. First response within 4 business hours. Target fix within 5 business days.\n- P4 Low: questions, how-to requests and small UI issues. First response within 1 business day. Fixed in a planned release.\n\n## How to raise a support ticket\n1. Log in to the SK Soft Client Support Portal and click New Ticket.\n2. Choose the product, the environment (Production, UAT or Dev) and the severity.\n3. Describe the problem, the steps to reproduce it, the time it started and attach screenshots or error logs.\n4. You receive a ticket number by email immediately. All updates are posted on the ticket.\n5. For a P1 outage, also call the 24x7 support hotline so the on-call engineer is paged at once.\n\n## Production outage (P1) process\n- The on-call engineer joins a bridge call within 15 minutes and shares updates every 30 minutes.\n- The client's account manager and the delivery head are informed automatically.\n- After the fix, a Root Cause Analysis (RCA) report is shared within 3 business days.\n\n## Escalation matrix\n- Level 1: Support engineer on the ticket.\n- Level 2: Support team lead, if there is no response within the SLA time.\n- Level 3: Delivery manager and account manager for repeated SLA misses.\n\n## SLA service credits\n- If the monthly uptime falls below the 99.5% committed in the contract, the client receives a service credit of 5% of that month's support fee for every 0.5% below target, up to 25%.\n",
    "finance/invoices_and_expenses.md": "# SK Soft Technology Finance: Client Invoices, Payments and Employee Expenses\n\n## Client invoicing\n- Time-and-material (T&M) projects are invoiced monthly on the 3rd working day, based on approved timesheets.\n- Fixed-price projects are invoiced on each milestone the client signs off.\n- Payment terms are Net 30 days from the invoice date unless the contract says otherwise.\n- Every invoice carries the PO number, the GSTIN of both parties and the SOW reference.\n\n## Duplicate or wrong charge on an invoice\n1. The client shares the invoice number and the payment reference (UTR or transaction ID).\n2. Finance checks the bank statement and the payment gateway within 2 business days.\n3. If a duplicate payment is confirmed, the extra amount is refunded within 5 business days, or adjusted against the next invoice if the client prefers.\n4. A credit note is issued for every refund or adjustment.\n\n## Payroll details new joiners must provide\nSubmit these in the Payroll section of SK People before the 20th of your joining month, so your first salary is not delayed:\n1. Salary bank account: bank name, account number, IFSC code and a cancelled cheque or bank passbook front page. The account must be in your own name.\n2. PAN card number (mandatory for income tax / TDS).\n3. UAN (Universal Account Number) from your previous employer, for Provident Fund (PF) transfer. Freshers get a new UAN created by Finance.\n4. Investment / tax declaration (old or new tax regime choice, rent, 80C investments) for the financial year.\n5. Form 12B with salary details from your previous employer if you joined in the middle of the financial year.\n- Salary is credited on the last working day of each month. Payslips are in SK People > Payroll > Payslips.\n- Form 16 is issued every year by 15 June.\n\n## Employee expense claims and reimbursements\n1. Submit claims in the Expense Portal within 30 days of the expense.\n2. Attach a clear photo or PDF of each bill. Claims above Rs 5,000 need project manager approval.\n3. Approved claims are paid with the next monthly salary.\n- Travel limits for client visits: hotel up to Rs 4,000 per night in metro cities and Rs 2,500 elsewhere; daily food allowance Rs 1,000; local cab travel is reimbursed at actuals with receipts.\n- Onsite (abroad) assignments get a daily allowance as per the country table in the Travel Policy.\n\n## Vendor payments\n- Vendor invoices are paid within 45 days of receiving a valid invoice with a PO number.\n",
    "hr/leave_wfh_and_policies.md": "# SK Soft Technology HR: Leave, Hybrid Work, Onboarding, Appraisals and Workplace Policies\n\n## Leave types per year\n- Casual leave: 12 days. Sick leave: 10 days. Earned (privilege) leave: 18 days.\n- Maternity leave: 26 weeks. Paternity leave: 10 working days.\n- Up to 10 unused earned leaves can be carried forward to the next year.\n\n## How to apply for leave\n1. Log in to the HR Portal (SK People) and open Leave > Apply.\n2. Choose the leave type and dates and add a short reason.\n3. Casual and earned leave must be applied at least 3 working days in advance; inform your project manager so client deliverables are planned.\n4. Sick leave of more than 2 days needs a medical certificate.\n5. Your reporting manager approves or rejects within 2 working days.\n\n## Joining documents to submit to HR\nUpload these in SK People within 3 working days of joining (scanned copies; bring originals for verification on day 1):\n1. Signed offer letter and appointment letter.\n2. Identity and address proof: Aadhaar card and PAN card (passport if available).\n3. Education certificates: 10th, 12th and degree/diploma mark sheets and certificates.\n4. Experience documents from previous employers: relieving letter, experience letter and last 3 months' payslips.\n5. Two recent passport-size photos.\n6. Filled forms in SK People: personal details, emergency contact, nominee details and the code of conduct acceptance.\n- For payroll details (bank account, PF/UAN, tax declaration) see the Finance team's payroll checklist.\n\n## Hybrid work (work from home)\n- Employees work from the office at least 3 days a week and may work from home up to 2 days a week.\n- Client-facing projects may require more office days as per the client contract.\n- Full remote work for longer periods needs approval from the delivery head and HR.\n\n## Onboarding for new joiners\n- Day 1: laptop handover, ID card, HR induction and policy acceptance in SK People.\n- Week 1: mandatory security and POSH trainings, and project allocation by the resource management team.\n- A buddy from the project team is assigned to every new joiner for the first 30 days.\n\n## Appraisals and bench\n- The appraisal cycle runs every April, with a mid-year review in October.\n- Employees not allocated to a project (bench) must complete assigned upskilling courses and stay available for client interviews.\n\n## Notice period\n- 60 days for all employees, and 90 days for managers and above.\n\n## Workplace complaints\n- Complaints about harassment, discrimination or unsafe behaviour are handled confidentially by the Internal Committee (IC) under the POSH policy.\n- Email ic@sksoft.example or speak to any HR business partner. The committee responds within 2 working days.\n",
    "it/it_support_guide.md": "# SK Soft Technology IT Support Guide\n\n## New joiner laptop setup (software to install)\nYour laptop comes with Windows/macOS, the antivirus and the Software Center already installed. On day 1:\n1. Sign in with your SK Soft email and set up multi-factor authentication (MFA) with the Microsoft Authenticator app on your phone.\n2. Install the SK Soft VPN client from the Software Center and connect once to check it works.\n3. From the Software Center install the standard tools: Microsoft Outlook and Teams, Slack, Google Chrome, 7-Zip and Zoom.\n4. Developers also install, from the Software Center: Git, Visual Studio Code (or IntelliJ IDEA), Docker Desktop, Postman, and Python or Node.js as your project needs.\n5. Raise an Access Request in the IT Service Portal for GitHub, Jira, Confluence and the AWS dev account (see below).\n6. Do not install personal or pirated software; anything not in the Software Center needs an IT request.\n- IT runs a 30-minute \"Laptop Ready\" session for new joiners every Monday at 11 AM on Teams.\n\n## Access to GitHub, Jira, Confluence and AWS\n1. Raise an Access Request in the IT Service Portal and select the tools you need (GitHub organisation, Jira project, Confluence space, AWS dev account).\n2. Mention the project code and your project manager's name.\n3. Your project manager approves the request in the portal.\n4. Standard access is provided within 1 working day after approval.\n- Production (AWS prod, production databases) access needs extra approval from the delivery head and is given only for a limited time.\n- Access is removed automatically when you are released from a project.\n\n## VPN not connecting or disconnecting\n1. Make sure you have the latest SK Soft VPN client (updates are pushed every month).\n2. Restart the VPN client and sign in again with multi-factor authentication (MFA).\n3. Switch to another network (for example a mobile hotspot) to check whether your home Wi-Fi is the problem.\n4. If it still drops, raise an IT ticket with a screenshot of the error and the time it happened.\n\n## Reset your office password\n1. Go to the Self-Service Password Portal and enter your employee ID.\n2. Verify with the code sent to your registered mobile or the authenticator app.\n3. Choose a password with at least 12 characters, including upper case, lower case, a number and a symbol.\n4. Passwords expire every 90 days and the last 5 cannot be reused.\n\n## Laptops and software\n- Developer laptops have 32 GB RAM and are replaced every 4 years.\n- Hardware faults are fixed within 3 working days; a spare laptop is given if it takes longer.\n- Install licensed software (IDEs, Docker Desktop, database tools) only from the Software Center or by raising a request. Pirated or personal-licence software is not allowed.\n\n## Security incidents\n- Report a lost or stolen laptop to IT and your manager within 2 hours so it can be locked and wiped remotely.\n- Never share passwords or MFA codes, even with IT staff.\n- Report phishing emails with the Report Phishing button in Outlook.\n- Never commit secrets, passwords or API keys to GitHub; if it happens, inform the security team immediately so the key is rotated.\n",
    "marketing/brand_case_studies_webinars.md": "# SK Soft Technology Marketing: Brand, Case Studies, Webinars and Social Media\n\n## Brand guidelines\n- Primary colour: SK Soft Blue #1D4ED8. Accent: Signal Orange #FF6B1A. Text: Graphite #1F2937.\n- Fonts: Poppins for headings, Inter for body text.\n- Do not stretch, recolour or add effects to the logo. Keep clear space around it equal to the height of the letters SK.\n- Use the official slide template from the Marketing Hub for all client presentations.\n\n## Publishing a client case study\n1. Fill in the Case Study Request form in the Marketing Hub with the project summary, technology used and measurable results (for example cost saved, time reduced).\n2. Get written approval from the client to use their name and logo. Without approval, the case study is published as anonymous (\"a leading bank\").\n3. The content team drafts the case study within 7 working days.\n4. The delivery manager checks technical accuracy and the account manager gives final sign-off.\n5. Approved case studies go on the website, LinkedIn and sales decks.\n\n## Hosting a webinar or tech talk\n- Submit the webinar request at least 21 days before the event with the topic, speakers, target audience and date.\n- Marketing creates the registration page and sends reminders 7 days, 1 day and 1 hour before the event.\n- A dry run with all speakers is mandatory 2 days before the event.\n- Registrant and attendee leads are shared with Sales within 2 working days after the event.\n\n## Social media and blogs\n- Only the marketing team posts on official SK Soft Technology accounts.\n- Employees can write technical blogs; submit drafts to the content team for a 3 working day review.\n- Never share client names, code, architecture diagrams or project details publicly without approval.\n",
    "sales/rate_card_rfp_and_contracts.md": "# SK Soft Technology Sales: Rate Card, Discounts, RFPs and Contracts\n\n## Standard monthly rate card (India offshore, per resource)\n- Junior developer (0-2 years): Rs 1,80,000 per month.\n- Developer (3-5 years, Java, .NET, Python, React): Rs 2,60,000 per month.\n- Senior developer / tech lead (6+ years): Rs 3,60,000 per month.\n- QA engineer: Rs 2,00,000 per month. DevOps / cloud engineer: Rs 3,00,000 per month.\n- Onsite resources are priced separately by the pricing team.\n\n## Discount approval limits\n- Account managers can approve up to 5% discount.\n- Sales heads can approve up to 10%.\n- Discounts above 10%, or any deal with 10 or more resources for 12 months or longer, need approval from the pricing committee (decision within 3 working days).\n- Volume guide: 5 to 9 resources for 12 months or more can receive up to 7%.\n\n## Responding to an RFP\n1. Log the RFP in the CRM within 1 working day and share it with the pre-sales team.\n2. Hold a bid / no-bid meeting within 2 working days.\n3. Send clarification questions to the client before their question deadline.\n4. Pre-sales prepares the solution and effort estimate; pricing team prepares the commercials.\n5. The delivery head and sales head review the final proposal at least 2 days before submission.\n\n## Contracts\n- An NDA must be signed before receiving any confidential client documents.\n- Every engagement needs a signed MSA (master agreement) and a SOW (statement of work) before work starts.\n- Proof of Concept (POC) work of up to 2 weeks can be offered free with sales head approval.\n"
}

if not (_HERE / ".env").exists():
    (_HERE / ".env").write_text(_ENV_TEMPLATE, encoding="utf-8")
if not (_HERE / ".streamlit" / "config.toml").exists():
    (_HERE / ".streamlit").mkdir(exist_ok=True)
    (_HERE / ".streamlit" / "config.toml").write_text(_STREAMLIT_CONFIG, encoding="utf-8")
for _rel, _text in _KB_FILES.items():
    _p = _HERE / "knowledge_base" / _rel
    if not _p.exists():
        _p.parent.mkdir(parents=True, exist_ok=True)
        _p.write_text(_text, encoding="utf-8")

# ============================================================================
# config.py
# ============================================================================
BASE_DIR = _HERE
load_dotenv(BASE_DIR / ".env")

COMPANY_NAME = "SK Soft Technology"

# ---- Keys & model -----------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")  # optional: Groq / Gemini / Ollama
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")   # optional: live web search
APP_PASSWORD = os.getenv("APP_PASSWORD", "")         # optional: protects the app on a VPS
# Show file names and each agent's steps in the chat (for demos / assignment screenshots only)
SHOW_AGENT_STEPS = os.getenv("SHOW_AGENT_STEPS", "false").strip().lower() in ("1", "true", "yes", "on")

# ---- Paths ------------------------------------------------------------------
KB_DIR = BASE_DIR / "knowledge_base"
LOG_DIR = BASE_DIR / "logs"
LOG_CSV = LOG_DIR / "tickets.csv"
LOG_TXT = LOG_DIR / "tickets.txt"
LOG_DIR.mkdir(exist_ok=True)

# ---- Departments the Router Agent can send work to ---------------------------
# key = folder name inside knowledge_base/, value = what that team handles
DEPARTMENTS = {
    "customer_support": "Client support: production incidents/outages, SLA and severity (P1-P4), support tickets, "
                        "bug reports, client portal login, releases and maintenance windows",
    "finance": "Client invoices, payment disputes, duplicate charges, credit notes, employee expense claims, "
               "travel reimbursement, vendor payments",
    "marketing": "Brand guidelines, client case studies, webinars and tech talks, blogs, social media",
    "sales": "Rate card, resource pricing, discounts, RFPs and proposals, NDA/MSA/SOW contracts, POCs",
    "hr": "Leave, work from home / hybrid rules, onboarding, appraisals, bench, notice period, POSH complaints",
    "it": "GitHub/Jira/AWS access, VPN, office password, laptops, software installs, security incidents",
}

DEPARTMENT_LABELS = {
    "customer_support": "Client Support",
    "finance": "Finance",
    "marketing": "Marketing",
    "sales": "Sales",
    "hr": "HR",
    "it": "IT",
}


def make_model_client():
    """Create the LLM client. Works with OpenAI, or any OpenAI-compatible API."""
    from autogen_ext.models.openai import OpenAIChatCompletionClient

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file.")

    kwargs = {"model": OPENAI_MODEL, "api_key": OPENAI_API_KEY, "temperature": 0.2}
    if OPENAI_BASE_URL:
        # Non-OpenAI providers need a short description of what the model can do.
        kwargs["base_url"] = OPENAI_BASE_URL
        kwargs["model_info"] = {
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
            "structured_output": False,
        }
    return OpenAIChatCompletionClient(**kwargs)

# ============================================================================
# tools/kb_search.py
# ============================================================================
STOPWORDS = set("""
a an the and or but if to of in on at for with from by is are was were be been am i me my
we our you your it its this that these those can could would should will shall do does did
have has had not no yes please hi hello how what when where why who which there their them
they he she his her get got want need about any some just so very also into than then too
""".split())


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words if w not in STOPWORDS and len(w) > 2}


def _passages(file: Path):
    """Split a markdown file into sections (one per heading)."""
    text = file.read_text(encoding="utf-8")
    title = file.stem.replace("_", " ")
    for block in re.split(r"\n(?=#{1,3} )", text):
        block = block.strip()
        if block:
            yield title, block


def search(query: str, department: str | None = None, top_k: int = 3) -> list[dict]:
    """Return the best matching passages: [{source, text, score}]."""
    q_terms = _terms(query)
    if not q_terms:
        return []
    folder = KB_DIR / department if department else KB_DIR
    min_hits = 1 if len(q_terms) <= 2 else 2  # avoid weak, one-word matches

    results = []
    for file in sorted(folder.rglob("*.md")):
        for title, block in _passages(file):
            p_terms = _terms(block) | _terms(title)
            hits = q_terms & p_terms
            if len(hits) >= min_hits:
                results.append({
                    "source": str(file.relative_to(KB_DIR)),
                    "text": block,
                    "score": len(hits),
                })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def format_results(results: list[dict]) -> str:
    if not results:
        return "NO_MATCH: nothing relevant was found in the knowledge base."
    parts = [f"[source: {r['source']}]\n{r['text']}" for r in results]
    return "\n\n---\n\n".join(parts)

# ============================================================================
# tools/web_search.py
# ============================================================================
def serpapi_search(query: str, num: int = 3) -> str:
    if not SERPAPI_API_KEY:
        return "WEB_SEARCH_DISABLED: no SERPAPI_API_KEY configured."
    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={"q": query, "api_key": SERPAPI_API_KEY, "num": num, "engine": "google"},
            timeout=20,
        )
        resp.raise_for_status()
        items = resp.json().get("organic_results", [])[:num]
    except Exception as exc:  # network / quota problems should never crash the app
        return f"WEB_SEARCH_ERROR: {exc}"
    if not items:
        return "NO_MATCH: web search returned nothing."
    return "\n\n".join(
        f"[source: web - {i.get('link', '')}]\n{i.get('title', '')}: {i.get('snippet', '')}" for i in items
    )

# ============================================================================
# tools/ticket_store.py
# ============================================================================
COLUMNS = [
    "ticket_id", "timestamp", "employee_name", "employee_id", "department", "category",
    "priority", "sentiment", "summary", "complaint", "kb_sources", "response",
    "confidence", "status", "escalation_reason", "assigned_to",
]

RISK_WORDS = {
    "legal threat": ["lawyer", "legal", "sue", "court", "police", "consumer forum"],
    "fraud": ["fraud", "scam", "stolen", "hacked", "unauthori"],
    "payment dispute": ["chargeback", "charged twice", "charged three", "charged my card", "double charge",
                        "my bank", "dispute"],
    "workplace complaint": ["harass", "discriminat", "abuse", "threaten", "unsafe"],
}

_lock = threading.Lock()


def next_ticket_id() -> str:
    count = len(load_tickets())
    return f"TKT-{count + 1:04d}"


def escalation_check(ticket: dict, agent_says_escalate: bool = False, agent_reason: str = "") -> list[str]:
    """Return the list of reasons to escalate. Empty list = can be resolved by AI."""
    reasons = []
    if ticket.get("priority") == "High":
        reasons.append("High priority")
    if ticket.get("sentiment") == "Angry":
        reasons.append("Very angry employee/client")
    if not ticket.get("kb_sources") or ticket.get("kb_sources") == "NONE":
        reasons.append("No matching document in knowledge base")
    if ticket.get("confidence") == "Low":
        reasons.append("Low confidence answer")
    text = ticket.get("complaint", "").lower()
    for label, words in RISK_WORDS.items():
        if any(w in text for w in words):
            reasons.append(f"Involves {label}")
    if agent_says_escalate and agent_reason:
        reasons.append(f"Log Agent: {agent_reason}")
    # keep order, remove duplicates
    return list(dict.fromkeys(reasons))


def save_ticket(ticket: dict) -> dict:
    """Append one ticket to logs/tickets.csv and logs/tickets.txt."""
    row = {c: ticket.get(c, "") for c in COLUMNS}
    with _lock:
        _upgrade_old_log()
        new_file = not LOG_CSV.exists()
        with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            if new_file:
                writer.writeheader()
            writer.writerow(row)
        with open(LOG_TXT, "a", encoding="utf-8") as f:
            f.write(
                f"{'=' * 70}\n"
                f"{row['ticket_id']} | {row['timestamp']} | {row['status'].upper()}\n"
                f"From       : {row['employee_name'] or '-'} | Employee ID: {row['employee_id'] or '-'}\n"
                f"Department : {row['department']} | Category: {row['category']}\n"
                f"Priority   : {row['priority']} | Sentiment: {row['sentiment']} | Confidence: {row['confidence']}\n"
                f"Query      : {row['complaint']}\n"
                f"Sources    : {row['kb_sources']}\n"
                f"Reply      : {row['response']}\n"
                f"Escalation : {row['escalation_reason'] or '-'} -> {row['assigned_to']}\n\n"
            )
    return row


def build_row(ctx: dict, response: str, confidence: str, kb_sources: str,
              agent_escalate: bool = False, agent_reason: str = "") -> dict:
    ticket = dict(ctx)
    ticket.update({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "response": response.strip(),
        "confidence": confidence if confidence in ("High", "Medium", "Low") else "Low",
        "kb_sources": kb_sources or "NONE",
    })
    reasons = escalation_check(ticket, agent_escalate, agent_reason)
    dept_label = DEPARTMENT_LABELS.get(ticket.get("department_key", ""), ticket.get("department", ""))
    ticket["status"] = "Escalated" if reasons else "Resolved"
    ticket["escalation_reason"] = " + ".join(reasons)
    ticket["assigned_to"] = f"{dept_label} human team" if reasons else "AI Agent"
    return ticket


def _upgrade_old_log():
    """Older versions used customer_name/order_id columns: rename them once."""
    if not LOG_CSV.exists():
        return
    with open(LOG_CSV, encoding="utf-8") as f:
        header = f.readline().strip().split(",")
    if header != COLUMNS:
        df = pd.read_csv(LOG_CSV, dtype=str).fillna("")
        df = df.rename(columns={"customer_name": "employee_name", "order_id": "employee_id"})
        df.reindex(columns=COLUMNS, fill_value="").to_csv(LOG_CSV, index=False)


def load_tickets() -> pd.DataFrame:
    if not LOG_CSV.exists():
        return pd.DataFrame(columns=COLUMNS)
    _upgrade_old_log()
    return pd.read_csv(LOG_CSV, dtype=str).fillna("")

# ============================================================================
# agents/router_agent.py
# ============================================================================
MAX_REQUESTS = 4
_dept_lines = "\n".join(f"- {key}: {desc}" for key, desc in DEPARTMENTS.items())

SYSTEM_MESSAGE = f"""You are the Router Agent (the main agent) of the {COMPANY_NAME} help desk (an IT services company).
Read the message from an employee (or a client) and decide which team or teams must handle it.

Departments:
{_dept_lines}

Splitting rules:
- If the message asks things that belong to DIFFERENT teams, split it into one request per team
  (for example software setup -> it, joining documents -> hr, payroll details -> finance).
- Put everything for the same team into ONE request. Maximum {MAX_REQUESTS} requests.
- Rewrite each request as a short, complete question that makes sense on its own.
- A simple message for one team is just one request.

Priority rules (per request):
- High: production outage / P1, client system down, security breach or leaked secrets, money charged wrongly,
  legal threats, fraud, harassment, very angry person, or anything blocking client delivery today.
- Medium: needs action in 1-2 days (P2/P3 bugs, invoice queries, access or VPN problem for one person).
- Low: general questions, how-to, information requests, new joiner questions.

Reply with ONLY a JSON object, no extra text:
{{"sentiment": "Positive|Neutral|Negative|Angry",
  "summary": "<one line summary of the whole message>",
  "requests": [
    {{"department": "<one key from the list>", "category": "<short label, e.g. Laptop Setup, Joining Documents, Payroll>",
      "priority": "High|Medium|Low", "question": "<the part of the message for this team>"}}
  ]}}"""


def create_router_agent(model_client) -> AssistantAgent:
    return AssistantAgent(
        name="Router_Agent",
        description="Main agent: splits the message into one request per team and routes each to that team.",
        model_client=model_client,
        system_message=SYSTEM_MESSAGE,
    )


def _clean(value, allowed, default):
    value = str(value or default).strip().capitalize()
    return value if value in allowed else default


def parse_route(text: str, original: str = "") -> dict:
    """Read the Router's JSON safely. Returns {sentiment, summary, requests: [...]} with at least one request."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    data = {}
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = {}

    raw = data.get("requests")
    if not isinstance(raw, list) or not raw:          # older single-team format, or messy output
        raw = [data] if data.get("department") else [{}]

    merged: dict[str, dict] = {}                      # one request per team
    for item in raw[:MAX_REQUESTS]:
        if not isinstance(item, dict):
            continue
        dept = str(item.get("department", "customer_support")).lower().strip().replace(" ", "_")
        if dept not in DEPARTMENTS:
            dept = "customer_support"
        question = str(item.get("question") or original).strip()
        priority = _clean(item.get("priority"), ("High", "Medium", "Low"), "Medium")
        if dept in merged:                            # same team twice -> join the questions
            merged[dept]["question"] += " " + question
            if priority == "High":
                merged[dept]["priority"] = "High"
        else:
            merged[dept] = {"department_key": dept, "category": item.get("category") or "General",
                            "priority": priority, "question": question}
    if not merged:
        merged["customer_support"] = {"department_key": "customer_support", "category": "General",
                                      "priority": "Medium", "question": original}
    return {
        "sentiment": _clean(data.get("sentiment"), ("Positive", "Neutral", "Negative", "Angry"), "Neutral"),
        "summary": str(data.get("summary", "")).strip(),
        "requests": list(merged.values()),
    }

# ============================================================================
# agents/department_agents.py
# ============================================================================
def create_department_agent(department: str, model_client, ctx: dict) -> AssistantAgent:
    label = DEPARTMENT_LABELS[department]

    def search_kb(query: str) -> str:
        """Search this department's company documents. Returns passages with their source file."""
        results = search(query, department)
        if not results:  # maybe the router picked a neighbouring team: try all documents
            results = search(query)
        ctx.setdefault("searched_sources", set()).update(r["source"] for r in results)
        return format_results(results)

    tools = [search_kb]
    web_line = ""
    if SERPAPI_API_KEY:
        def web_search(query: str) -> str:
            """Search the public web (SerpAPI). Use ONLY for public/market facts, never for company policy."""
            result = serpapi_search(query)
            ctx.setdefault("searched_sources", set()).add("web")
            return result

        tools.append(web_search)
        web_line = ("\n- You may call web_search for public, non-policy facts (market trends, public holidays, "
                    "software versions). Never use it for company policy.")

    system_message = f"""You are the {label} Knowledge Agent. You handle: {DEPARTMENTS[department]}.
Steps:
1. Call search_kb with the key words from the ticket summary.{web_line}
2. Read the passages. Keep ONLY the ones that really answer the question.
3. Reply in this exact format:
FACTS:
- <fact copied from the documents>
- <fact>
SOURCES: <comma separated file names, e.g. {department}/policy.md> or NONE
If nothing relevant was found write "FACTS: none" and "SOURCES: NONE". Never invent facts."""

    return AssistantAgent(
        name=f"{label.replace(' ', '_')}_Agent",
        description=f"{label} department agent that finds answers in the {label} documents.",
        model_client=model_client,
        tools=tools,
        system_message=system_message,
        reflect_on_tool_use=True,
        max_tool_iterations=2,
    )

# ============================================================================
# agents/resolution_agent.py
# ============================================================================
SYSTEM_MESSAGE = """You are the Resolution Agent.
Write a short, polite, helpful reply to the person who raised the ticket.
Rules:
- Use ONLY the FACTS given by the department agent. Do not invent policies, numbers or dates.
- If FACTS is none, say honestly that you don't have that information yet and that a
  team member will follow up. Do not guess.
- If the person is upset, start with one line of empathy.
- Use numbered steps when there is a process. Keep it under 150 words.
- Reply in the same language the person used.
- If the task says it is ONE part of a bigger message, answer only that team's part: no greeting, no sign-off.
- Speak as the help desk. NEVER mention file names, documents, sources, the knowledge base, agents,
  tools, FACTS or anything about how the answer was found. Just give the answer.
Finish with exactly one last line:
CONFIDENCE: High | Medium | Low   (High = facts fully answer it, Low = facts missing or partial)"""


def create_resolution_agent(model_client) -> AssistantAgent:
    return AssistantAgent(
        name="Resolution_Agent",
        description="Writes the employee/client-ready reply grounded in the retrieved facts.",
        model_client=model_client,
        system_message=SYSTEM_MESSAGE,
    )

# ============================================================================
# agents/log_agent.py
# ============================================================================
SYSTEM_MESSAGE = """You are the Log Agent. You ALWAYS call the log_ticket tool exactly once.
Fill the arguments from the conversation:
- response: the Resolution Agent's full reply WITHOUT the CONFIDENCE line
- confidence: the value from the CONFIDENCE line (High, Medium or Low)
- kb_sources: the SOURCES line from the department agent (or NONE)
- escalate: true if a human should take over (very angry person, legal threat, fraud,
  payment dispute, harassment, missing information, low confidence), otherwise false
- escalation_reason: a short reason when escalate is true, otherwise empty
Do not write anything else."""


def create_log_agent(model_client, ctx: dict) -> AssistantAgent:
    def log_ticket(response: str, confidence: str, kb_sources: str,
                   escalate: bool = False, escalation_reason: str = "") -> str:
        """Save the ticket to the log file and decide Resolved / Escalated."""
        # Keep only sources that were really returned by search_kb (stops made-up file names).
        found = ctx.get("searched_sources", set())
        claimed = [s.strip() for s in kb_sources.replace(";", ",").split(",") if s.strip()]
        verified = [s for s in claimed if s in found or (s == "web" and "web" in found)]
        sources = ", ".join(verified) if verified else "NONE"

        row = build_row(ctx, response, confidence.strip().capitalize(), sources,
                        bool(escalate), escalation_reason)
        ctx["result"] = save_ticket(row)
        return f"LOGGED {row['ticket_id']} | status={row['status']} | {row['escalation_reason'] or 'no escalation'}"

    return AssistantAgent(
        name="Log_Agent",
        description="Saves the ticket to the log and escalates complex cases to a human.",
        model_client=model_client,
        tools=[log_ticket],
        system_message=SYSTEM_MESSAGE,
        reflect_on_tool_use=False,
    )

# ============================================================================
# team.py
# ============================================================================
EventFn = Callable[[str, str, str], None]  # (agent_name, kind, text)


def _message_text(msg) -> tuple[str, str] | None:
    if isinstance(msg, ToolCallRequestEvent):
        calls = ", ".join(f"{c.name}({c.arguments[:200]})" for c in msg.content)
        return "tool_call", f"Calling tool: {calls}"
    if isinstance(msg, ToolCallExecutionEvent):
        return "tool_result", "\n\n".join(r.content for r in msg.content)
    if isinstance(msg, ToolCallSummaryMessage):
        return None  # same text as the tool result shown just before
    if isinstance(msg, TextMessage):
        return "message", msg.content
    return None


async def _run_team(client, request: dict, base: dict, original: str, multi: bool, on_event: EventFn) -> dict:
    """Team agent -> Resolution -> Log for ONE request. Returns the saved ticket row."""
    ctx = dict(base)
    ctx.update({
        "ticket_id": next_ticket_id(),
        "department_key": request["department_key"],
        "department": DEPARTMENT_LABELS[request["department_key"]],
        "category": request["category"],
        "priority": request["priority"],
        "complaint": request["question"],
    })
    on_event("Router_Agent", "part", ctx["department"])

    team = RoundRobinGroupChat(
        [create_department_agent(ctx["department_key"], client, ctx),
         create_resolution_agent(client), create_log_agent(client, ctx)],
        termination_condition=TextMentionTermination("LOGGED", sources=["Log_Agent"]) | MaxMessageTermination(12),
    )
    part_note = ("\nNOTE: this is ONE part of a bigger message that other teams are answering. "
                 "Answer ONLY the question for your team. No greeting and no sign-off.") if multi else ""
    task = (f"Ticket {ctx['ticket_id']} for the {ctx['department']} team\n"
            f"From: {ctx['employee_name'] or 'unknown'} | Employee ID: {ctx['employee_id'] or '-'}\n"
            f"Category: {ctx['category']} | Priority: {ctx['priority']} | Sentiment: {ctx['sentiment']}\n"
            f"Question for this team: {request['question']}\n"
            f"Full original message (for context only): {original}{part_note}")

    last_reply = ""
    async for msg in team.run_stream(task=task):
        if isinstance(msg, TaskResult) or getattr(msg, "source", "") == "user":
            continue
        item = _message_text(msg)
        if item:
            on_event(msg.source, *item)
            if msg.source == "Resolution_Agent" and item[0] == "message":
                last_reply = item[1]

    # Safety net: if the Log Agent never called its tool, log the ticket ourselves.
    if "result" not in ctx:
        conf = re.search(r"CONFIDENCE:\s*(High|Medium|Low)", last_reply, re.I)
        reply = re.sub(r"CONFIDENCE:.*", "", last_reply, flags=re.I).strip()
        row = build_row(ctx, reply or "No reply generated.", conf.group(1).capitalize() if conf else "Low",
                        "NONE", True, "Agents did not finish the workflow")
        ctx["result"] = save_ticket(row)
        on_event("Log_Agent", "message", f"LOGGED {row['ticket_id']} (fallback) | status={row['status']}")
    return ctx["result"]


async def run_request(message: str, employee_name: str = "", employee_id: str = "",
                      on_event: EventFn | None = None, model_client=None) -> list[dict]:
    """Handle one message from a user. Returns one ticket row per team that was involved."""
    on_event = on_event or (lambda *a: None)
    client = model_client or make_model_client()
    try:
        # ---- Step 1: main Router agent splits the message by team ------------
        routed = await create_router_agent(client).run(task=message)
        route = parse_route(routed.messages[-1].content, message)
        teams = [DEPARTMENT_LABELS[r["department_key"]] for r in route["requests"]]
        on_event("Router_Agent", "message",
                 f"Teams: {', '.join(teams)} | Sentiment: {route['sentiment']}\nSummary: {route['summary']}\n"
                 + "\n".join(f"- {DEPARTMENT_LABELS[r['department_key']]} ({r['priority']}): {r['question']}"
                             for r in route["requests"]))

        # ---- Step 2: each team handles its own part ---------------------------
        base = {"employee_name": employee_name, "employee_id": employee_id,
                "sentiment": route["sentiment"], "summary": route["summary"]}
        multi = len(route["requests"]) > 1
        results = []
        for request in route["requests"]:
            part_base = dict(base, summary=request["question"] if multi else (route["summary"] or request["question"]))
            results.append(await _run_team(client, request, part_base, message, multi, on_event))
        return results
    finally:
        await client.close()


async def run_ticket(complaint: str, employee_name: str = "", employee_id: str = "",
                     on_event: EventFn | None = None, model_client=None) -> dict:
    """Older single-answer helper (first team's ticket). New code should use run_request."""
    return (await run_request(complaint, employee_name, employee_id, on_event, model_client))[0]

# ============================================================================
# app.py
# ============================================================================
st.set_page_config(page_title=f"{COMPANY_NAME} Help Desk", page_icon="🎧", layout="wide")

# ----------------------------------------------------------------------------
# Content shown to the user
# ----------------------------------------------------------------------------
# (icon, team, what they handle, [(short button label, full question sent), ...])
DEPT_CARDS = [
    ("🚀", "New Joiner", "One question for several teams at once (IT + HR + Finance)",
     [("Day-1: software + documents + payroll",
       "I am new to this company. What software do I need to install on my computer? What documents do I need "
       "to submit to HR? What basic details must I give Finance for my payroll?"),
      ("Project start: access + leave",
       "I'm joining a client project next week. How do I get GitHub, Jira and AWS access, and how do I apply "
       "for 2 days of casual leave the week after?")]),
    ("🛟", "Client Support", "Production incidents, SLAs, support tickets and releases",
     [("Production is down!", "Our client's production application is down and no users can log in. This is a P1 – please help now!"),
      ("Raise a support ticket", "How do I raise a support ticket for a bug and how fast will the support team respond?")]),
    ("💳", "Finance", "Client invoices, payments and expense claims",
     [("Claim travel expenses", "How do I claim my cab and hotel expenses from the client visit in Bengaluru?"),
      ("Invoice charged twice", "The client says invoice INV-2291 was charged twice. Fix this now or their legal team will get involved.")]),
    ("📣", "Marketing", "Brand, case studies, webinars and blogs",
     [("Publish a case study", "We finished a cloud migration project for a client. How do I publish it as a case study?"),
      ("Host a tech webinar", "How early do I need to request a GenAI webinar for our clients?")]),
    ("💼", "Sales", "Rate card, discounts, RFPs and contracts",
     [("Rate & discount for 5 devs", "A client wants 5 Java developers for 12 months. What is our rate and what discount can I offer?"),
      ("Respond to an RFP", "We received an RFP from a bank. What is the process to respond?")]),
    ("👥", "HR", "Leave, hybrid work, onboarding and appraisals",
     [("Apply for leave", "How do I apply for 3 days of casual leave next week?"),
      ("Work from home rules", "How many days can I work from home in a week?")]),
    ("🖥️", "IT", "GitHub/Jira/AWS access, VPN, laptop and security",
     [("GitHub, Jira & AWS access", "I just joined a project. How do I get access to GitHub, Jira and the AWS dev account?"),
      ("VPN keeps dropping", "My VPN keeps disconnecting every 10 minutes and I can't reach the dev server.")]),
]

TEAM_ICONS = {name: icon for icon, name, _, _ in DEPT_CARDS}

FRIENDLY_STEP = {
    "Router_Agent": "🧭 Understood your request",
    "Resolution_Agent": "✍️ Writing your answer",
    "Log_Agent": "🗂️ Saving your ticket",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p { font-family: 'Inter', sans-serif; }
[data-testid="stToolbar"] { display: none; }
.block-container { padding-top: 3.6rem; max-width: 1150px; }
h1, h2, h3, .hero-title { font-family: 'Poppins', sans-serif !important; }

.hero { background: linear-gradient(135deg, #14213D 0%, #23407a 60%, #FF6B1A 135%);
        border-radius: 22px; padding: 28px 32px 24px; color: #fff; margin-bottom: 14px;
        box-shadow: 0 10px 30px rgba(20,33,61,.18); }
.hero .hero-title { font-size: 2rem !important; font-weight: 700; margin: 0; color: #fff; line-height: 1.25; }
.hero .hero-sub { color: #dbe4ff; margin: 6px 0 18px; font-size: 1.02rem; }
.steps { display: flex; gap: 12px; flex-wrap: wrap; }
.step { flex: 1; min-width: 190px; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.22);
        border-radius: 14px; padding: 12px 14px; font-size: .9rem; color: #f1f5ff; }
.step .num { display:inline-block; width:24px; height:24px; line-height:24px; text-align:center; border-radius:50%;
             background:#FF6B1A; color:#fff; font-weight:700; margin-right:8px; font-size:.8rem; }

.section-title { font-family:'Poppins',sans-serif; font-weight:600; font-size:1.15rem; margin: 18px 0 2px; }
.section-sub { color:#6b7280; font-size:.9rem; margin-bottom:10px; }
.dept-head { font-weight:600; font-size:1.02rem; }
.dept-sub { color:#6b7280; font-size:.84rem; margin-bottom:6px; }

[class*="st-key-sample"] button { border-radius: 12px; justify-content: flex-start; text-align: left;
        font-size: .85rem; padding: 8px 12px; min-height: 0; }
[class*="st-key-sample"] button p { text-align:left; }

.chip { display:inline-block; padding:4px 11px; border-radius:999px; font-size:.78rem; font-weight:600;
        margin: 0 6px 6px 0; border:1px solid transparent; }
.chip-ok   { background:#dcfce7; color:#166534; }
.chip-esc  { background:#fee2e2; color:#991b1b; }
.chip-high { background:#fee2e2; color:#b91c1c; }
.chip-med  { background:#fef3c7; color:#92400e; }
.chip-low  { background:#dbeafe; color:#1e40af; }
.chip-dept { background:#eef2ff; color:#3730a3; }
.chip-id   { background:#f3f4f6; color:#374151; }
.handoff { background:#fff7ed; border-left:4px solid #FF6B1A; padding:10px 14px; border-radius:8px;
           color:#7c2d12; font-size:.9rem; margin-top:8px; }
.part-head { font-family:'Poppins',sans-serif; font-weight:600; font-size:1.05rem; margin-bottom:6px; }
.source { color:#6b7280; font-size:.82rem; margin-top:6px; }
.mini-hero { background: linear-gradient(135deg, #14213D 0%, #23407a 70%, #FF6B1A 160%); border-radius: 16px;
             padding: 14px 20px; color: #fff; margin-bottom: 12px; font-size: .95rem; }
.mini-hero b { font-family:'Poppins',sans-serif; font-size: 1.1rem; }
.ex-label { font-weight:600; font-size:.95rem; margin: 2px 0 2px; }
.ex-sub { color:#6b7280; font-size:.85rem; margin: 2px 0 4px; }
[class*="st-key-team_pick"] button, [class*="st-key-q_pick"] button { font-size: .9rem; padding: 6px 14px; }
[class*="st-key-q_pick"] button { border-color: #FF6B1A55; }
</style>
"""


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def password_gate():
    if not APP_PASSWORD or st.session_state.get("authed"):
        return
    st.markdown(f"<div class='hero'><p class='hero-title'>🔒 {COMPANY_NAME} Help Desk</p>"
                "<p class='hero-sub'>Please enter the team password to continue.</p></div>",
                unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password")
    if st.button("Enter", type="primary"):
        if pwd == APP_PASSWORD:
            st.session_state.authed = True
            st.rerun()
        st.error("That password is not correct.")
    st.stop()


def chips(r: dict) -> str:
    status = (f"<span class='chip chip-ok'>✅ Solved</span>" if r["status"] == "Resolved"
              else f"<span class='chip chip-esc'>🙋 Passed to a person</span>")
    pr = {"High": "chip-high", "Medium": "chip-med", "Low": "chip-low"}.get(r["priority"], "chip-low")
    return (status
            + f"<span class='chip chip-dept'>{r['department']} team</span>"
            + f"<span class='chip {pr}'>{r['priority']} priority</span>"
            + f"<span class='chip chip-id'>🎫 {r['ticket_id']}</span>")


def render_part(r: dict, multi: bool):
    if multi:
        st.markdown(f"<div class='part-head'>{TEAM_ICONS.get(r['department'], '🎧')} {r['department']} team</div>",
                    unsafe_allow_html=True)
    st.markdown(chips(r), unsafe_allow_html=True)
    st.markdown(r["response"])
    if r["status"] == "Escalated":
        why = f"<br><small>Why: {r['escalation_reason']}</small>" if SHOW_AGENT_STEPS else ""
        st.markdown(f"<div class='handoff'>🙋 A person from the <b>{r['assigned_to'].replace(' human team', ' team')}</b> will follow up on this "
                    f"shortly. Please keep your ticket number <b>{r['ticket_id']}</b> handy.{why}</div>",
                    unsafe_allow_html=True)
    if SHOW_AGENT_STEPS:
        src = r["kb_sources"] if r["kb_sources"] != "NONE" else "no matching company document"
        st.markdown(f"<div class='source'>📄 Based on: {src}</div>", unsafe_allow_html=True)


def render_answer(msg: dict):
    results = msg.get("results") or [msg["result"]]
    multi = len(results) > 1
    if multi:
        names = ", ".join(r["department"] for r in results[:-1]) + f" and {results[-1]['department']}"
        st.markdown(f"Your message had questions for **{len(results)} teams** ({names}). "
                    "Each team has answered its part below:")
    for r in results:
        if multi:
            with st.container(border=True):
                render_part(r, multi)
        else:
            render_part(r, multi)
    if SHOW_AGENT_STEPS and msg.get("steps"):  # employees only see the answer, nothing about files or agents
        with st.expander("🔍 Behind the scenes — how the AI team handled this"):
            for agent, kind, text in msg["steps"]:
                label = agent.replace("_", " ")
                if kind == "part":
                    st.markdown(f"**➡️ {text} team starts its part**")
                elif kind == "tool_call":
                    st.caption(f"**{label}** · using a tool")
                    st.code(text, language=None)
                elif kind == "tool_result":
                    st.caption(f"**{label}** · tool result")
                    st.code(text[:1500], language=None)
                else:
                    st.caption(f"**{label}**")
                    st.markdown(text)


def to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False, sheet_name="Tickets")
    return buf.getvalue()


# ----------------------------------------------------------------------------
# Page 1: Ask
# ----------------------------------------------------------------------------
def page_ask():
    history = st.session_state.setdefault("chat", [])
    if not (st.session_state.get("user_name") and st.session_state.get("user_ref")):
        details_gate()
        return

    # ---- 1. Welcome banner (slim once a conversation has started) -------------
    if history:
        st.markdown(f"<div class='mini-hero'><b>🎧 {COMPANY_NAME} Help Desk</b> &nbsp;·&nbsp; "
                    f"Hi {st.session_state.user_name}, ask anything — we send it to the right team automatically.</div>",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='hero'>
          <p class='hero-title'>Hi {st.session_state.user_name} 👋 How can we help today?</p>
          <p class='hero-sub'>Ask anything about client support, finance, marketing, sales, HR or IT at
             {COMPANY_NAME} — in your own words. No need to know which team to contact.</p>
          <div class='steps'>
            <div class='step'><span class='num'>1</span>Pick an example or type your question</div>
            <div class='step'><span class='num'>2</span>We send it to the right team automatically</div>
            <div class='step'><span class='num'>3</span>Get an answer from company policy — or a person follows up</div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ---- 2. Example questions: one line of teams, then that team's questions ---
    example_bar()

    # ---- 3. Conversation (newest at the bottom, just above the question box) --
    if not history:
        with st.chat_message("assistant", avatar="🎧"):
            st.markdown(f"I'm the **{COMPANY_NAME} Help Desk Assistant**. Pick a team above and tap an example, "
                        "or type your own question in the box at the bottom.")
    for msg in history:
        with st.chat_message(msg["role"], avatar="🙂" if msg["role"] == "user" else "🎧"):
            if msg["role"] == "user":
                st.markdown(msg["text"])
            elif "result" in msg or "results" in msg:
                render_answer(msg)
            else:
                st.markdown(msg["text"])

    # ---- 4. Question box, always last -----------------------------------------
    question = st.chat_input("Type your question here… e.g. “How do I apply for leave?”")
    question = question or st.session_state.pop("pending", None)
    if question:
        handle_question(question)
    if st.session_state.chat:
        scroll_to_bottom()


def details_gate():
    st.markdown(f"""
    <div class='hero'>
      <p class='hero-title'>Welcome to the {COMPANY_NAME} Help Desk 👋</p>
      <p class='hero-sub'>One place for every question — client support, finance, marketing, sales, HR and IT.
         Tell us who you are to get started.</p>
      <div class='steps'>
        <div class='step'><span class='num'>1</span>Enter your name and Employee ID</div>
        <div class='step'><span class='num'>2</span>Pick an example or type your question</div>
        <div class='step'><span class='num'>3</span>Get an answer — or the right team follows up</div>
      </div>
    </div>""", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])
    with mid.form("details"):
        st.markdown("#### 👤 Your details")
        name = st.text_input("Full name *", placeholder="e.g. Priya Raman")
        emp_id = st.text_input("Employee ID *", placeholder="e.g. SK1045")
        st.caption("Both fields are required. They are saved on every ticket so the team can reach you.")
        if st.form_submit_button("Start chatting →", type="primary", width="stretch"):
            if not name.strip() or not emp_id.strip():
                st.error("Please enter both your name and your Employee ID.")
            else:
                st.session_state.user_name = name.strip().title()
                st.session_state.user_ref = emp_id.strip().upper()
                st.rerun()


def send_example(key: str, options: dict):
    picked = st.session_state.get(key)
    if picked:
        st.session_state.pending = options[picked]
        st.session_state[key] = None  # clear the chip so it can be tapped again


def example_bar():
    with st.container(border=True):
        st.markdown("<div class='ex-label'>💡 Try an example — pick a team</div>", unsafe_allow_html=True)
        teams = [f"{icon} {name}" for icon, name, _, _ in DEPT_CARDS]
        team = st.pills("Team", teams, default=teams[0], key="team_pick",
                        label_visibility="collapsed") or teams[0]
        icon, name, sub, qs = DEPT_CARDS[teams.index(team)]
        st.markdown(f"<div class='ex-sub'>{icon} <b>{name}</b> · {sub}. Tap a question to ask it:</div>",
                    unsafe_allow_html=True)
        options = {f"💬 {short}": full for short, full in qs}
        key = f"q_pick_{name}"
        st.pills("Questions", list(options), key=key, label_visibility="collapsed",
                 on_change=send_example, args=(key, options))


def scroll_to_bottom():
    components.html("""<script>
      setTimeout(() => {
        const d = window.parent.document;
        const main = d.querySelector('[data-testid="stMain"]') || d.querySelector('section.main');
        if (main) main.scrollTo({top: main.scrollHeight, behavior: 'smooth'});
        window.parent.scrollTo({top: d.body.scrollHeight, behavior: 'smooth'});
      }, 400);
    </script>""", height=0)


def handle_question(question: str):
    history = st.session_state.chat
    history.append({"role": "user", "text": question})
    with st.chat_message("user", avatar="🙂"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🎧"):
        if not OPENAI_API_KEY:
            text = ("⚠️ I'm not connected to the AI service yet. Ask the admin to add **OPENAI_API_KEY** "
                    "to the `.env` file and restart the app.")
            st.markdown(text)
            history.append({"role": "assistant", "text": text})
            return

        steps = []
        progress = st.empty()  # the progress box disappears once the answer is ready
        status = progress.status("Reading your question…", expanded=False)

        def on_event(agent: str, kind: str, text: str):
            steps.append((agent, kind, text))
            if agent == "Router_Agent" and kind == "message":
                teams = text.split("|")[0].replace("Teams:", "").strip()
                status.update(label=f"Sending it to: {teams}…")
                status.write(f"🧭 Sent to **{teams}**")
            elif agent == "Router_Agent" and kind == "part":
                status.update(label=f"{TEAM_ICONS.get(text, '🎧')} {text} team is working on its part…")
                status.write(f"{TEAM_ICONS.get(text, '🎧')} **{text} team** is checking company policy")
            elif agent.endswith("_Agent") and agent not in FRIENDLY_STEP:
                if kind == "message":
                    status.write("📄 Found what we need")
            elif agent == "Resolution_Agent":
                status.write("✍️ Answer written")
            elif agent == "Log_Agent" and kind == "tool_result":
                status.write("🗂️ Ticket saved")

        try:
            results = asyncio.run(run_request(question, st.session_state.get("user_name", ""),
                                              st.session_state.get("user_ref", ""), on_event))
        except Exception as exc:
            status.update(label="Something went wrong", state="error")
            text = f"😕 Sorry, I couldn't process that right now. ({exc})"
            st.markdown(text)
            history.append({"role": "assistant", "text": text})
            return

        progress.empty()
        msg = {"role": "assistant", "results": results, "steps": steps}
        render_answer(msg)
        history.append(msg)


# ----------------------------------------------------------------------------
# Page 2: Ticket history
# ----------------------------------------------------------------------------
def page_history():
    st.markdown("### 🗂️ Ticket history")
    st.caption("Every question is saved as a ticket. Click a row to see the full details.")
    df = load_tickets()
    if df.empty:
        st.info("No tickets yet — ask a question on the **Ask** page first.")
        return

    m = st.columns(4)
    m[0].metric("Total tickets", len(df), border=True)
    m[1].metric("✅ Solved by AI", int((df["status"] == "Resolved").sum()), border=True)
    m[2].metric("🙋 Passed to a person", int((df["status"] == "Escalated").sum()), border=True)
    m[3].metric("🔴 High priority", int((df["priority"] == "High").sum()), border=True)

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    search = c1.text_input("Search", placeholder="Search tickets…", label_visibility="collapsed")
    dept = c2.selectbox("Team", ["All teams"] + sorted(df["department"].unique()), label_visibility="collapsed")
    prio = c3.selectbox("Priority", ["Any priority", "High", "Medium", "Low"], label_visibility="collapsed")
    stat = c4.selectbox("Status", ["Any status", "Resolved", "Escalated"], label_visibility="collapsed")

    view = df.iloc[::-1]
    if search:
        view = view[view.apply(lambda r: search.lower() in " ".join(r.values).lower(), axis=1)]
    if dept != "All teams":
        view = view[view["department"] == dept]
    if prio != "Any priority":
        view = view[view["priority"] == prio]
    if stat != "Any status":
        view = view[view["status"] == stat]

    table = pd.DataFrame({
        "Ticket": view["ticket_id"],
        "When": view["timestamp"],
        "Team": view["department"],
        "Priority": view["priority"].map({"High": "🔴 High", "Medium": "🟠 Medium", "Low": "🔵 Low"}),
        "Status": view["status"].map({"Resolved": "✅ Solved", "Escalated": "🙋 With a person"}),
        "Question": view["summary"].where(view["summary"] != "", view["complaint"]),
    })
    event = st.dataframe(table, hide_index=True, width="stretch", on_select="rerun",
                         selection_mode="single-row", height=min(420, 40 + 35 * len(table)))
    rows = event.selection.rows if event and event.selection else []
    if rows:
        r = view.iloc[rows[0]].to_dict()
        with st.container(border=True):
            st.markdown(f"**{r['ticket_id']}** · {r['timestamp']} · {r['employee_name'] or 'Anonymous'}"
                        f" {('· ' + r['employee_id']) if r['employee_id'] else ''}")
            st.markdown(chips(r), unsafe_allow_html=True)
            st.markdown(f"**Question:** {r['complaint']}")
            st.markdown(f"**Answer:**\n\n{r['response']}")
            if r["status"] == "Escalated":
                st.markdown(f"<div class='handoff'>Assigned to <b>{r['assigned_to']}</b> — {r['escalation_reason']}</div>",
                            unsafe_allow_html=True)
            if SHOW_AGENT_STEPS:
                st.caption(f"📄 Sources: {r['kb_sources']} · Confidence: {r['confidence']} · Sentiment: {r['sentiment']}")

    st.markdown("**Download**")
    d1, d2, d3, _ = st.columns([1, 1, 1, 3])
    d1.download_button("📊 Excel", to_excel(df), "tickets.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    d2.download_button("📄 CSV", LOG_CSV.read_bytes(), "tickets.csv", "text/csv", width="stretch")
    if LOG_TXT.exists():
        d3.download_button("📝 TXT", LOG_TXT.read_bytes(), "tickets.txt", "text/plain", width="stretch")


# ----------------------------------------------------------------------------
# Page 3: Weekly summary
# ----------------------------------------------------------------------------
def page_weekly():
    st.markdown("### 📊 Weekly summary")
    df = load_tickets()
    if df.empty:
        st.info("No tickets yet — the weekly summary appears once questions come in.")
        return
    df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce")

    c1, c2 = st.columns([1, 3])
    picked = c1.date_input("Week containing", value=date.today())
    start = datetime.combine(picked - timedelta(days=picked.weekday()), datetime.min.time())
    end = start + timedelta(days=7)
    c2.markdown(f"<div style='padding-top:32px;color:#6b7280'>Showing <b>{start:%a %d %b}</b> → "
                f"<b>{(end - timedelta(days=1)):%a %d %b %Y}</b></div>", unsafe_allow_html=True)
    week = df[(df["ts"] >= start) & (df["ts"] < end)]
    if week.empty:
        st.info("No tickets in this week. Pick another date above.")
        return

    total = len(week)
    solved = int((week["status"] == "Resolved").sum())
    m = st.columns(4)
    m[0].metric("Tickets this week", total, border=True)
    m[1].metric("✅ Solved by AI", f"{solved}  ({solved * 100 // total}%)", border=True)
    m[2].metric("🙋 Passed to a person", total - solved, border=True)
    m[3].metric("🔴 High priority", int((week["priority"] == "High").sum()), border=True)

    g1, g2 = st.columns(2)
    with g1.container(border=True):
        st.markdown("**Questions per team**")
        st.bar_chart(week["department"].value_counts(), color="#FF6B1A", height=260, horizontal=True)
    with g2.container(border=True):
        st.markdown("**Solved vs passed to a person**")
        st.bar_chart(pd.crosstab(week["department"], week["status"]), color=["#dc2626", "#16a34a"]
                     if set(week["status"]) == {"Escalated", "Resolved"} else None, height=260, horizontal=True)
    with st.container(border=True):
        st.markdown("**Tickets per day**")
        st.bar_chart(week.groupby(week["ts"].dt.strftime("%a %d"))["ticket_id"].count(), color="#14213D", height=220)

    esc = week[week["status"] == "Escalated"]
    st.markdown(f"**🙋 Waiting for a person ({len(esc)})**")
    if esc.empty:
        st.success("Nothing waiting — every ticket this week was solved by the AI team.")
    for _, r in esc.iterrows():
        st.markdown(f"<div class='handoff'><b>{r['ticket_id']}</b> · {r['department']} · {r['priority']} priority — "
                    f"{r['summary'] or r['complaint']}<br><small>{r['escalation_reason']}</small></div>",
                    unsafe_allow_html=True)

    lines = [f"WEEKLY HELP DESK REPORT  {start:%d %b %Y} - {(end - timedelta(days=1)):%d %b %Y}", "=" * 60,
             f"Total: {total} | Solved by AI: {solved} | Passed to a person: {total - solved} | "
             f"High priority: {(week['priority'] == 'High').sum()}", ""]
    for dep, grp in week.groupby("department"):
        lines.append(f"[{dep}] {len(grp)} tickets (High {(grp['priority'] == 'High').sum()}, "
                     f"Medium {(grp['priority'] == 'Medium').sum()}, Low {(grp['priority'] == 'Low').sum()})")
        lines += [f"  - {r['ticket_id']} {r['priority']:<6} {r['status']:<9} {r['summary']}" for _, r in grp.iterrows()]
        lines.append("")
    st.download_button("📝 Download weekly report (TXT)", "\n".join(lines),
                       f"weekly_report_{start:%Y_%m_%d}.txt", "text/plain")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
st.markdown(CSS, unsafe_allow_html=True)
password_gate()

with st.sidebar:
    st.markdown(f"## 🎧 {COMPANY_NAME}")
    st.caption("AI Help Desk for every team")
    if st.session_state.get("user_name") and st.session_state.get("user_ref"):
        with st.container(border=True):
            st.markdown(f"👤 **{st.session_state.user_name}**  \n🪪 Employee ID: `{st.session_state.user_ref}`")
            if st.button("✏️ Change details", width="stretch"):
                st.session_state.user_name = st.session_state.user_ref = ""
                st.session_state.chat = []
                st.rerun()
    if st.button("🧹 Start a new chat", width="stretch"):
        st.session_state.chat = []
        st.rerun()
    with st.expander("❓ How does this work?"):
        st.markdown("1. **You ask** in plain words.\n"
                    "2. A **main AI agent** picks the right team — Client Support, Finance, Marketing, "
                    "Sales, HR or IT — and sets the priority.\n"
                    "3. That **team's agent** reads only that team's company documents.\n"
                    "4. You get an answer. If it's urgent, sensitive or not covered, "
                    "a **person from that team** follows up.\n"
                    "5. Every question is **saved as a ticket**.")
    if SHOW_AGENT_STEPS:  # technical status only in demo mode
        st.divider()
        st.caption("🛠️ Demo mode: showing sources and agent steps")
        st.caption(f"{'🟢' if OPENAI_API_KEY else '🔴'} AI connected · `{OPENAI_MODEL}`")
        st.caption(f"{'🟢' if SERPAPI_API_KEY else '⚪'} Web search {'on' if SERPAPI_API_KEY else 'off'}")

page = st.segmented_control("Menu", ["💬 Ask", "🗂️ Ticket history", "📊 Weekly summary"],
                            default="💬 Ask", key="page", label_visibility="collapsed") or "💬 Ask"
{"💬 Ask": page_ask, "🗂️ Ticket history": page_history, "📊 Weekly summary": page_weekly}[page]()
