"""Wires the agents together.

Flow for one message:
  1. Router Agent (main agent) splits the message into one request per team
     e.g. "software to install + joining documents + payroll details"  ->  IT, HR, Finance
  2. For EACH request, a RoundRobinGroupChat team runs:
        <Team> Agent  ->  Resolution Agent  ->  Log Agent
     It stops when the Log Agent says LOGGED (or after 12 messages as a safety net).
     Every request gets its own ticket, so each team sees (and is escalated) only its own part.
"""
import asyncio
import re
from typing import Callable

from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import (TextMessage, ToolCallExecutionEvent,
                                        ToolCallRequestEvent, ToolCallSummaryMessage)
from autogen_agentchat.teams import RoundRobinGroupChat

from agents.department_agents import create_department_agent
from agents.log_agent import create_log_agent
from agents.resolution_agent import create_resolution_agent
from agents.router_agent import create_router_agent, parse_route
from config import DEPARTMENT_LABELS, make_model_client
from tools.ticket_store import build_row, next_ticket_id, save_ticket

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


if __name__ == "__main__":  # quick terminal test:  python team.py
    def show(agent, kind, text):
        print(f"\n[{agent} - {kind}]\n{text}")

    rows = asyncio.run(run_request(
        "I'm new here. What software should I install on my laptop? What documents must I give HR? "
        "What details does Finance need for payroll?", "Priya", "SK1045", show))
    for r in rows:
        print(f"\nFINAL {r['ticket_id']} {r['department']}: {r['status']} | {r['escalation_reason']}")
