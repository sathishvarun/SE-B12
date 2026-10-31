"""Records every ticket (CSV + TXT) and decides whether a human must take over."""
from autogen_agentchat.agents import AssistantAgent

from tools.ticket_store import build_row, save_ticket

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
