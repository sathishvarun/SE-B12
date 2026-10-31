"""Wires the agents together.

Flow:  Router (main agent)  ->  Department agent  ->  Resolution agent  ->  Log agent
Step 1 runs the Router alone so we know which department sub-agent to call.
Step 2 runs a RoundRobinGroupChat team: Department -> Resolution -> Log,
       and stops when the Log Agent says LOGGED (or after 12 messages as a safety net).
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


async def run_ticket(complaint: str, employee_name: str = "", employee_id: str = "",
                     on_event: EventFn | None = None, model_client=None) -> dict:
    on_event = on_event or (lambda *a: None)
    client = model_client or make_model_client()
    ctx = {"ticket_id": next_ticket_id(), "employee_name": employee_name,
           "employee_id": employee_id, "complaint": complaint.strip()}
    try:
        # ---- Step 1: main Router agent -------------------------------------
        router = create_router_agent(client)
        routed = await router.run(task=complaint)
        router_text = routed.messages[-1].content
        ctx.update(parse_route(router_text))
        ctx["department"] = DEPARTMENT_LABELS[ctx["department_key"]]
        on_event("Router_Agent", "message",
                 f"Department: {ctx['department']} | Category: {ctx['category']} | "
                 f"Priority: {ctx['priority']} | Sentiment: {ctx['sentiment']}\nSummary: {ctx['summary']}")

        # ---- Step 2: department sub-agent -> resolution -> log ---------------
        dept_agent = create_department_agent(ctx["department_key"], client, ctx)
        team = RoundRobinGroupChat(
            [dept_agent, create_resolution_agent(client), create_log_agent(client, ctx)],
            termination_condition=TextMentionTermination("LOGGED", sources=["Log_Agent"])
            | MaxMessageTermination(12),
        )
        task = (f"Ticket {ctx['ticket_id']} for the {ctx['department']} team\n"
                f"From: {employee_name or 'unknown'} | Employee ID: {employee_id or '-'}\n"
                f"Category: {ctx['category']} | Priority: {ctx['priority']} | Sentiment: {ctx['sentiment']}\n"
                f"Summary: {ctx['summary']}\n"
                f"Original message: {complaint}")
        last_reply = ""
        async for msg in team.run_stream(task=task):
            if isinstance(msg, TaskResult) or getattr(msg, "source", "") == "user":
                continue
            item = _message_text(msg)
            if item:
                on_event(msg.source, *item)
                if msg.source == "Resolution_Agent" and item[0] == "message":
                    last_reply = item[1]
    finally:
        await client.close()

    # Safety net: if the Log Agent never called its tool, log the ticket ourselves.
    if "result" not in ctx:
        conf = re.search(r"CONFIDENCE:\s*(High|Medium|Low)", last_reply, re.I)
        reply = re.sub(r"CONFIDENCE:.*", "", last_reply, flags=re.I).strip()
        ctx.setdefault("department", "Client Support")
        row = build_row(ctx, reply or "No reply generated.", conf.group(1).capitalize() if conf else "Low",
                        "NONE", True, "Agents did not finish the workflow")
        ctx["result"] = save_ticket(row)
        on_event("Log_Agent", "message", f"LOGGED {row['ticket_id']} (fallback) | status={row['status']}")
    return ctx["result"]


if __name__ == "__main__":  # quick terminal test:  python team.py
    def show(agent, kind, text):
        print(f"\n[{agent} - {kind}]\n{text}")

    result = asyncio.run(run_ticket("How do I reset my office password?", "Priya", "SK1045", show))
    print("\nFINAL:", result["status"], "|", result["escalation_reason"])
