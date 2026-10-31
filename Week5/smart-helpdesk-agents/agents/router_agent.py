"""MAIN AGENT: reads the query and decides department, priority and sentiment."""
import json
import re

from autogen_agentchat.agents import AssistantAgent

from config import COMPANY_NAME, DEPARTMENTS

_dept_lines = "\n".join(f"- {key}: {desc}" for key, desc in DEPARTMENTS.items())

SYSTEM_MESSAGE = f"""You are the Router Agent (the main agent) of the {COMPANY_NAME} help desk (an IT services company).
Read the query from an employee (or a client) and decide which team should handle it.

Departments:
{_dept_lines}

Priority rules:
- High: production outage / P1, client system down, security breach or leaked secrets, money charged wrongly,
  legal threats, fraud, harassment, very angry person, or anything blocking client delivery today.
- Medium: needs action in 1-2 days (P2/P3 bugs, invoice queries, access or VPN problem for one person).
- Low: general questions, how-to, information requests.

Reply with ONLY a JSON object, no extra text:
{{"department": "<one key from the list>", "category": "<short label, e.g. Production Incident, Access, Leave, Expenses, RFP>",
  "priority": "High|Medium|Low", "sentiment": "Positive|Neutral|Negative|Angry",
  "summary": "<one line summary>"}}"""


def create_router_agent(model_client) -> AssistantAgent:
    return AssistantAgent(
        name="Router_Agent",
        description="Main agent: classifies the query and routes it to the right department.",
        model_client=model_client,
        system_message=SYSTEM_MESSAGE,
    )


def parse_route(text: str) -> dict:
    """Read the JSON the Router Agent produced, with safe defaults if it is messy."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    data = {}
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = {}
    dept = str(data.get("department", "customer_support")).lower().strip().replace(" ", "_")
    if dept not in DEPARTMENTS:
        dept = "customer_support"
    priority = str(data.get("priority", "Medium")).capitalize()
    sentiment = str(data.get("sentiment", "Neutral")).capitalize()
    return {
        "department_key": dept,
        "category": data.get("category", "General"),
        "priority": priority if priority in ("High", "Medium", "Low") else "Medium",
        "sentiment": sentiment if sentiment in ("Positive", "Neutral", "Negative", "Angry") else "Neutral",
        "summary": data.get("summary", ""),
    }
