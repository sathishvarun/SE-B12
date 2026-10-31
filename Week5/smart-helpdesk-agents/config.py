"""Central settings: API keys, paths, departments and the model client."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
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
