"""
config.py
---------
Central configuration: loads the .env file, creates the OpenAI model client,
and describes every department (child agent) in one place.

To add a new department later, add one entry to DEPARTMENTS here and
one tool list in tools.py - nothing else needs to change.
"""

import os

from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Reads OPENAI_API_KEY / OPENAI_MODEL from the .env file in the project root
load_dotenv()

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

AVAILABLE_MODELS = ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4o", "gpt-4.1"]


def get_api_key() -> str | None:
    """Return the OpenAI key from the environment (.env), or None if missing."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return key or None


def build_model_client(model: str | None = None, temperature: float = 0.2) -> OpenAIChatCompletionClient:
    """Create the OpenAI client that every agent uses to 'think'."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and paste your key."
        )
    return OpenAIChatCompletionClient(
        model=model or DEFAULT_MODEL,
        api_key=api_key,
        temperature=temperature,
    )


# ---------------------------------------------------------------------------
# Department (child agent) definitions
# ---------------------------------------------------------------------------
# key        -> internal id, used for tool names like "delegate_to_it"
# name       -> AutoGen agent name (must be a valid Python identifier)
# label/icon -> what the dashboard shows
# color      -> accent color in the dashboard
# scope      -> what the Head Agent reads to decide who should handle a query
# persona    -> the child agent's system message
DEPARTMENTS: dict[str, dict] = {
    "it": {
        "name": "IT_Agent",
        "label": "IT Support",
        "icon": "💻",
        "color": "#38BDF8",
        "scope": "laptops, VPN, passwords, email, software access, outages, system status, IT tickets",
        "persona": (
            "You are the IT Support specialist. Diagnose technical issues step by step, "
            "check system status before blaming the user, and create an IT ticket when the "
            "problem can't be solved by self-service. Keep instructions numbered and short."
        ),
    },
    "hr": {
        "name": "HR_Agent",
        "label": "Human Resources",
        "icon": "🧑‍🤝‍🧑",
        "color": "#F472B6",
        "scope": "leave policy, leave balance, benefits, insurance, onboarding, payroll dates, workplace policies",
        "persona": (
            "You are the HR specialist. Be warm and precise. Quote the relevant policy, "
            "use the tools to look up leave balances or benefits, and never guess numbers."
        ),
    },
    "finance": {
        "name": "Finance_Agent",
        "label": "Finance",
        "icon": "💰",
        "color": "#34D399",
        "scope": "invoices, payments, refunds, expense reimbursement, billing, payment schedules",
        "persona": (
            "You are the Finance specialist. Always check invoice or payment data with your "
            "tools before answering, show amounts with currency, and state the next action clearly."
        ),
    },
    "sales": {
        "name": "Sales_Agent",
        "label": "Sales",
        "icon": "📈",
        "color": "#FBBF24",
        "scope": "pricing, plans, quotes, orders, order status, demos, upgrades, discounts",
        "persona": (
            "You are the Sales specialist. Recommend the right plan for the customer's need, "
            "use the pricing and order tools, and offer a demo when the customer is evaluating."
        ),
    },
    "marketing": {
        "name": "Marketing_Agent",
        "label": "Marketing",
        "icon": "📣",
        "color": "#A78BFA",
        "scope": "campaigns, webinars, events, newsletters, brand assets, logo usage, partnerships",
        "persona": (
            "You are the Marketing specialist. Share campaign and event details from your tools, "
            "point people to the correct brand assets, and keep a friendly, on-brand tone."
        ),
    },
}
