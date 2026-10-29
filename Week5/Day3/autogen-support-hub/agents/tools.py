"""
tools.py
--------
The "hands" of each child agent. Every department gets its own small set of
Python functions it can call. Here they read from sample (mock) data so the
project runs without any company systems. In a real deployment you would
replace the body of each function with a call to ServiceNow, Workday, SAP,
Salesforce, Marketo/Eloqua, ON24, Cvent, etc.

Rules for a good AutoGen tool:
  * clear function name + docstring  -> the LLM reads these to decide when to call it
  * type hints on every parameter    -> AutoGen turns them into a JSON schema
  * return a plain string            -> easy for the agent to read
"""

import random
from datetime import datetime, timedelta
from typing import Callable

from autogen_core.tools import FunctionTool

# ---------------------------------------------------------------------------
# Sample data (replace with real systems later)
# ---------------------------------------------------------------------------
SYSTEM_STATUS = {
    "vpn": "🟡 Degraded - Asia-Pacific gateway slow since 09:40 IST, engineers working on it",
    "email": "🟢 Operational",
    "sso": "🟢 Operational",
    "wifi": "🟢 Operational",
    "erp": "🔴 Planned maintenance until 23:00 IST tonight",
    "crm": "🟢 Operational",
}

LEAVE_POLICY = {
    "annual": "18 days per year, accrued monthly (1.5 days). Up to 5 unused days carry forward.",
    "sick": "12 days per year. Medical certificate needed for more than 2 consecutive days.",
    "casual": "6 days per year, maximum 2 days at a time, cannot be carried forward.",
    "maternity": "26 weeks fully paid as per policy.",
    "paternity": "10 working days, to be used within 3 months of the child's birth.",
}

LEAVE_BALANCES = {
    "EMP1001": {"annual": 11.5, "sick": 9, "casual": 4},
    "EMP1002": {"annual": 3.0, "sick": 12, "casual": 1},
    "EMP1003": {"annual": 16.5, "sick": 7, "casual": 6},
}

BENEFITS = {
    "health": "Group health insurance: INR 5,00,000 cover for employee + spouse + 2 children + parents.",
    "wellness": "INR 12,000 yearly wellness allowance (gym, yoga, therapy apps).",
    "learning": "INR 50,000 yearly learning budget for courses and certifications.",
    "pf": "Provident Fund: 12% employer contribution on basic salary.",
    "payroll": "Salary is credited on the last working day of every month.",
}

INVOICES = {
    "INV-2041": {"customer": "Acme Corp", "amount": "INR 2,40,000", "status": "Paid", "date": "2026-10-05"},
    "INV-2042": {"customer": "Globex Ltd", "amount": "INR 85,500", "status": "Overdue (12 days)", "date": "2026-10-10"},
    "INV-2043": {"customer": "Initech", "amount": "INR 1,15,000", "status": "Pending approval", "date": "2026-10-22"},
}

REIMBURSEMENT_POLICY = {
    "travel": "Economy flights / 3AC trains. Submit within 30 days with tickets. Paid in next payroll.",
    "meals": "Up to INR 1,500 per day while travelling. Bills mandatory above INR 500.",
    "internet": "Up to INR 1,000 per month for remote employees. Upload the monthly bill.",
    "client entertainment": "Pre-approval from manager needed. Cap INR 5,000 per event.",
}

PRICING = {
    "starter": {"price": "INR 2,999 / user / month", "best_for": "Small teams up to 10 users", "features": "Chatbot, email support, basic analytics"},
    "growth": {"price": "INR 6,999 / user / month", "best_for": "Growing teams 10-200 users", "features": "Multi-agent workflows, CRM sync, advanced analytics"},
    "enterprise": {"price": "Custom quote", "best_for": "200+ users, compliance needs", "features": "SSO, dedicated CSM, SLA 99.9%, on-prem option"},
}

ORDERS = {
    "ORD-7781": "Shipped - delivered expected 31 Oct 2026",
    "ORD-7782": "Processing - licence keys will be emailed within 24 hours",
    "ORD-7783": "Cancelled on customer request - refund initiated",
}

CAMPAIGNS = {
    "diwali": "Festive Diwali Campaign: 20% off Growth plan till 10 Nov 2026. Channels: email, LinkedIn, webinar.",
    "ai-summit": "AI in Customer Support Summit: lead-gen campaign driving registrations for the 18 Nov event.",
    "newsletter": "Monthly 'Support Pulse' newsletter goes out on the 1st of every month to 42k subscribers.",
}

EVENTS = [
    {"name": "Webinar: Building Multi-Agent Support Bots", "date": "2026-11-06", "platform": "ON24 (virtual)"},
    {"name": "AI in Customer Support Summit", "date": "2026-11-18", "platform": "Cvent (Bengaluru, in-person)"},
    {"name": "Product Office Hours", "date": "2026-11-25", "platform": "Zoom (virtual)"},
]

BRAND_ASSETS = {
    "logo": "Logo pack (SVG/PNG, light & dark) on the Brand Portal > Logos. Keep 24px clear space.",
    "colors": "Primary #6366F1 (Indigo), Secondary #0EA5E9 (Sky), Neutral #0F172A (Slate).",
    "fonts": "Headings: Space Grotesk. Body: Inter.",
    "templates": "Slide and email templates are on the Brand Portal > Templates.",
}


def _match(key: str, table: dict) -> str | None:
    """Loose lookup so 'Annual Leave' still finds 'annual'."""
    k = key.lower().strip()
    for name in table:
        if name in k or k in name:
            return name
    return None


# ---------------------------------------------------------------------------
# Tool builders - one per department
# ---------------------------------------------------------------------------
def build_department_tools(dept_key: str, on_ticket: Callable[[dict], None]) -> list[FunctionTool]:
    """
    Return the tools for one department.
    `on_ticket` is a callback so the dashboard can show every ticket/request created.
    """

    def _new_ticket(prefix: str, department: str, summary: str, priority: str = "Medium") -> dict:
        ticket = {
            "id": f"{prefix}-{random.randint(10000, 99999)}",
            "department": department,
            "summary": summary,
            "priority": priority.title(),
            "created": datetime.now().strftime("%d %b %H:%M"),
            "sla": (datetime.now() + timedelta(hours={"High": 4, "Medium": 24}.get(priority.title(), 48))).strftime("%d %b %H:%M"),
        }
        on_ticket(ticket)
        return ticket

    # ----------------------------- IT --------------------------------------
    def check_system_status(service: str) -> str:
        """Check the live status of an internal service such as vpn, email, sso, wifi, erp or crm."""
        name = _match(service, SYSTEM_STATUS)
        if not name:
            return "Known services: " + ", ".join(SYSTEM_STATUS) + ". " + "All others: no incident reported."
        return f"{name.upper()}: {SYSTEM_STATUS[name]}"

    def create_it_ticket(issue: str, priority: str = "Medium") -> str:
        """Create an IT support ticket. priority must be Low, Medium or High."""
        t = _new_ticket("IT", "IT", issue, priority)
        return f"Ticket {t['id']} created ({t['priority']} priority). SLA target: {t['sla']}."

    def password_reset_steps(system: str) -> str:
        """Return self-service password reset steps for a system (e.g. windows, email, vpn, sso)."""
        return (
            f"Password reset for {system}: 1) Go to https://reset.company.example "
            "2) Enter employee ID 3) Approve the OTP on the authenticator app "
            "4) Choose a new password (12+ chars, 1 symbol) 5) Wait 5 minutes for sync."
        )

    # ----------------------------- HR --------------------------------------
    def get_leave_policy(leave_type: str) -> str:
        """Get the company policy for a leave type: annual, sick, casual, maternity or paternity."""
        name = _match(leave_type, LEAVE_POLICY)
        return f"{name.title()} leave: {LEAVE_POLICY[name]}" if name else "Leave types: " + ", ".join(LEAVE_POLICY)

    def check_leave_balance(employee_id: str) -> str:
        """Look up remaining leave balance for an employee ID like EMP1001."""
        bal = LEAVE_BALANCES.get(employee_id.upper().strip())
        if not bal:
            return f"No employee found with ID {employee_id}. Sample IDs: EMP1001, EMP1002, EMP1003."
        return f"{employee_id.upper()} balance -> " + ", ".join(f"{k}: {v} days" for k, v in bal.items())

    def get_benefits_info(topic: str) -> str:
        """Get benefits information: health, wellness, learning, pf or payroll."""
        name = _match(topic, BENEFITS)
        return BENEFITS[name] if name else "Benefit topics: " + ", ".join(BENEFITS)

    # ----------------------------- Finance ---------------------------------
    def get_invoice_status(invoice_id: str) -> str:
        """Get status, amount and date of an invoice like INV-2042."""
        inv = INVOICES.get(invoice_id.upper().strip())
        if not inv:
            return f"Invoice {invoice_id} not found. Sample IDs: " + ", ".join(INVOICES)
        return f"{invoice_id.upper()} | {inv['customer']} | {inv['amount']} | {inv['status']} | issued {inv['date']}"

    def get_reimbursement_policy(category: str) -> str:
        """Get the expense reimbursement rule for: travel, meals, internet or client entertainment."""
        name = _match(category, REIMBURSEMENT_POLICY)
        return f"{name.title()}: {REIMBURSEMENT_POLICY[name]}" if name else "Categories: " + ", ".join(REIMBURSEMENT_POLICY)

    def raise_refund_request(invoice_id: str, reason: str) -> str:
        """Raise a refund or billing dispute request for an invoice."""
        t = _new_ticket("FIN", "Finance", f"Refund for {invoice_id}: {reason}", "High")
        return f"Refund request {t['id']} raised for {invoice_id}. Finance will respond by {t['sla']}."

    # ----------------------------- Sales -----------------------------------
    def get_pricing(plan: str) -> str:
        """Get pricing and features for a plan: starter, growth or enterprise. Use 'all' to list every plan."""
        if plan.lower().strip() in ("all", "plans", "any", ""):
            return " | ".join(f"{k.title()}: {v['price']} ({v['best_for']})" for k, v in PRICING.items())
        name = _match(plan, PRICING)
        if not name:
            return "Plans: starter, growth, enterprise."
        p = PRICING[name]
        return f"{name.title()} - {p['price']}. Best for: {p['best_for']}. Includes: {p['features']}."

    def check_order_status(order_id: str) -> str:
        """Check the status of a customer order like ORD-7781."""
        return ORDERS.get(order_id.upper().strip(), f"Order {order_id} not found. Sample IDs: " + ", ".join(ORDERS))

    def book_demo(company: str, preferred_date: str) -> str:
        """Book a product demo for a company on a preferred date."""
        t = _new_ticket("DEMO", "Sales", f"Demo for {company} on {preferred_date}", "Medium")
        return f"Demo request {t['id']} logged for {company} ({preferred_date}). An account executive will confirm."

    # ----------------------------- Marketing -------------------------------
    def get_campaign_info(campaign: str) -> str:
        """Get details of a marketing campaign: diwali, ai-summit or newsletter."""
        name = _match(campaign, CAMPAIGNS)
        return CAMPAIGNS[name] if name else "Active campaigns: " + ", ".join(CAMPAIGNS)

    def get_upcoming_events() -> str:
        """List upcoming webinars and events with date and platform."""
        return "\n".join(f"- {e['name']} | {e['date']} | {e['platform']}" for e in EVENTS)

    def get_brand_assets(asset_type: str) -> str:
        """Get brand guidelines for: logo, colors, fonts or templates."""
        name = _match(asset_type, BRAND_ASSETS)
        return BRAND_ASSETS[name] if name else "Asset types: " + ", ".join(BRAND_ASSETS)

    registry = {
        "it": [check_system_status, create_it_ticket, password_reset_steps],
        "hr": [get_leave_policy, check_leave_balance, get_benefits_info],
        "finance": [get_invoice_status, get_reimbursement_policy, raise_refund_request],
        "sales": [get_pricing, check_order_status, book_demo],
        "marketing": [get_campaign_info, get_upcoming_events, get_brand_assets],
    }
    return [FunctionTool(fn, description=fn.__doc__) for fn in registry[dept_key]]
