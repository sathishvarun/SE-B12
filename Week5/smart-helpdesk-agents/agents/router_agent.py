"""MAIN AGENT: reads the message, splits it into one request per team, and sets priority and sentiment.

One message can hold several requests for different teams, for example:
  "What software do I install? What documents does HR need? What does Finance need for payroll?"
  -> 3 requests: IT, HR and Finance. Each one is then handled by that team's own agent.
"""
import json
import re

from autogen_agentchat.agents import AssistantAgent

from config import COMPANY_NAME, DEPARTMENTS

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
- Rewrite each request as a short, complete question in English that makes sense on its own.
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
