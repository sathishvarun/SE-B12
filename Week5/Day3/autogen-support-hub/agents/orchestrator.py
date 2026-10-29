"""
orchestrator.py
---------------
The PARENT-CHILD multi-agent engine, built with Microsoft AutoGen (AgentChat).

                 ┌──────────────────────────┐
   user  ───────▶│   Head_Agent (PARENT)    │  reads the question, decides
                 │   "the supervisor"       │  which department(s) own it
                 └───┬─────┬─────┬─────┬────┘
       delegate_to_* │     │     │     │      (each delegation = a tool call)
                 ┌───▼┐ ┌──▼─┐ ┌─▼──┐ ┌▼───┐ ┌─────┐
                 │ IT │ │ HR │ │FIN │ │SALES│ │ MKT │   CHILD agents
                 └─┬──┘ └─┬──┘ └─┬──┘ └─┬───┘ └──┬──┘   each with own tools
                   └──────┴──────┴──────┴────────┘
                         results PUSHED BACK to parent
                                   │
                 Head_Agent merges the answers ──▶ final reply to user

How it works:
 1. Each child agent is a normal AutoGen `AssistantAgent` with its own tools.
 2. The Head Agent gets one "delegate_to_<department>" tool per child.
    Calling that tool = assigning the task to the child.
 3. The child runs, uses its tools, and its answer is returned (pushed back)
    to the Head Agent as the tool result.
 4. The Head Agent writes one combined, customer-friendly reply.
 5. Every step is recorded in a trace so the dashboard can show the flow.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
)
from autogen_core.tools import FunctionTool

from .config import DEPARTMENTS, build_model_client
from .tools import build_department_tools

HEAD_AGENT_NAME = "Head_Agent"


# ---------------------------------------------------------------------------
# Data structures the dashboard reads
# ---------------------------------------------------------------------------
@dataclass
class TraceEvent:
    t: float            # seconds since the run started
    actor: str          # who did it  (Head_Agent, IT_Agent, ...)
    kind: str           # route | delegate | tool_call | tool_result | report_back | final | error
    detail: str         # human readable text
    target: str = ""    # who received it (for arrows in the flow chart)


@dataclass
class RunResult:
    answer: str
    departments: list[str] = field(default_factory=list)      # dept keys used
    trace: list[TraceEvent] = field(default_factory=list)
    tickets: list[dict] = field(default_factory=list)
    tokens: dict[str, int] = field(default_factory=dict)      # agent name -> tokens
    latency: float = 0.0


def _usage_tokens(msg) -> int:
    u = getattr(msg, "models_usage", None)
    return (u.prompt_tokens + u.completion_tokens) if u else 0


def _short(text: str, n: int = 220) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


# ---------------------------------------------------------------------------
# The orchestrator
# ---------------------------------------------------------------------------
class SupportOrchestrator:
    def __init__(
        self,
        model: str | None = None,
        enabled_departments: list[str] | None = None,
        on_event: Callable[[TraceEvent], None] | None = None,
    ) -> None:
        self.model = model
        self.enabled = enabled_departments or list(DEPARTMENTS)
        self.on_event = on_event or (lambda e: None)

    # -- small helpers -------------------------------------------------------
    def _emit(self, result: RunResult, start: float, actor: str, kind: str, detail: str, target: str = "") -> None:
        ev = TraceEvent(round(time.perf_counter() - start, 2), actor, kind, detail, target)
        result.trace.append(ev)
        self.on_event(ev)

    def _add_tokens(self, result: RunResult, agent: str, n: int) -> None:
        if n:
            result.tokens[agent] = result.tokens.get(agent, 0) + n

    # -- CHILD agent factory ------------------------------------------------
    def _make_child(self, key: str, model_client, result: RunResult) -> AssistantAgent:
        dept = DEPARTMENTS[key]
        return AssistantAgent(
            name=dept["name"],
            model_client=model_client,
            tools=build_department_tools(key, on_ticket=result.tickets.append),
            description=f"{dept['label']} specialist. Handles: {dept['scope']}.",
            system_message=(
                f"{dept['persona']}\n\n"
                "You receive tasks from the Head Agent, not directly from the customer. "
                "Use your tools to get facts. Reply with a concise, factual answer "
                "(max ~120 words) that the Head Agent can pass to the customer. "
                "If the request is outside your department, say so in one line."
            ),
            reflect_on_tool_use=True,   # after using a tool, write a natural-language answer
            max_tool_iterations=3,      # child may chain up to 3 tool calls
        )

    # -- delegation tool given to the PARENT --------------------------------
    def _make_delegate_tool(self, key: str, model_client, result: RunResult, start: float) -> FunctionTool:
        dept = DEPARTMENTS[key]

        async def delegate(task: str) -> str:
            # 1) Parent assigns the task to the child
            self._emit(result, start, HEAD_AGENT_NAME, "delegate", _short(task), dept["name"])
            if key not in result.departments:
                result.departments.append(key)

            child = self._make_child(key, model_client, result)
            answer = ""
            # 2) Child works (and may call its own tools)
            async for msg in child.run_stream(task=task):
                if isinstance(msg, TaskResult):
                    continue
                self._add_tokens(result, dept["name"], _usage_tokens(msg))
                if isinstance(msg, ToolCallRequestEvent):
                    for call in msg.content:
                        self._emit(result, start, dept["name"], "tool_call", f"{call.name}({_short(call.arguments, 120)})")
                elif isinstance(msg, ToolCallExecutionEvent):
                    for res in msg.content:
                        self._emit(result, start, dept["name"], "tool_result", _short(res.content, 160))
                elif isinstance(msg, (TextMessage, ToolCallSummaryMessage)) and msg.source == dept["name"]:
                    answer = msg.content

            # 3) Child pushes the result back to the parent
            answer = answer or "No answer produced."
            self._emit(result, start, dept["name"], "report_back", _short(answer), HEAD_AGENT_NAME)
            return answer

        return FunctionTool(
            delegate,
            name=f"delegate_to_{key}",
            description=(
                f"Assign a task to the {dept['label']} agent. Use for: {dept['scope']}. "
                "Pass a clear, self-contained task including any IDs the customer gave."
            ),
        )

    # -- PARENT agent ---------------------------------------------------------
    def _make_head(self, tools: list[FunctionTool], model_client) -> AssistantAgent:
        roster = "\n".join(
            f"- delegate_to_{k}: {DEPARTMENTS[k]['label']} -> {DEPARTMENTS[k]['scope']}" for k in self.enabled
        )
        return AssistantAgent(
            name=HEAD_AGENT_NAME,
            model_client=model_client,
            tools=tools,
            description="Head customer-support agent that routes work to department agents.",
            system_message=(
                "You are the Head Agent of a company customer-support desk. You do NOT answer "
                "department questions from your own knowledge. Your job:\n"
                "1. Understand the customer's request.\n"
                "2. Delegate each part to the right department agent with the tools below. "
                "If a request touches several departments, call several tools.\n"
                "3. Combine the department answers into ONE friendly, well-structured reply. "
                "Use short markdown sections per department when more than one was involved.\n"
                "4. For greetings or small talk, reply briefly yourself without delegating.\n"
                "5. If no department fits, say politely what you can help with.\n\n"
                f"Available departments:\n{roster}"
            ),
            reflect_on_tool_use=True,   # write a final answer after children report back
            max_tool_iterations=2,      # allows a follow-up delegation round if needed
        )

    # -- public entry point ---------------------------------------------------
    async def ask(self, question: str, history: list[dict] | None = None) -> RunResult:
        start = time.perf_counter()
        result = RunResult(answer="")
        model_client = build_model_client(self.model)

        try:
            delegates = [self._make_delegate_tool(k, model_client, result, start) for k in self.enabled]
            head = self._make_head(delegates, model_client)

            # Give the parent short conversation memory (last 6 turns)
            context = ""
            if history:
                recent = history[-6:]
                context = "Conversation so far:\n" + "\n".join(
                    f"{m['role'].upper()}: {_short(m['content'], 300)}" for m in recent
                ) + "\n\n"
            task = f"{context}New customer message: {question}"

            self._emit(result, start, "Customer", "route", _short(question), HEAD_AGENT_NAME)

            async for msg in head.run_stream(task=task):
                if isinstance(msg, TaskResult):
                    continue
                self._add_tokens(result, HEAD_AGENT_NAME, _usage_tokens(msg))
                if isinstance(msg, (TextMessage, ToolCallSummaryMessage)) and msg.source == HEAD_AGENT_NAME:
                    result.answer = msg.content

            if not result.answer:
                result.answer = "Sorry, I couldn't produce an answer. Please try rephrasing."
            self._emit(result, start, HEAD_AGENT_NAME, "final", _short(result.answer), "Customer")

        except Exception as exc:  # show the error in the UI instead of crashing
            result.answer = f"⚠️ Something went wrong: `{exc}`"
            self._emit(result, start, "System", "error", str(exc))
        finally:
            await model_client.close()
            result.latency = round(time.perf_counter() - start, 2)

        return result
