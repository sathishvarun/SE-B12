"""Quick help: answers questions about Virundhu from help_guide.md. Uses the AI when a key is set; otherwise (or if the
AI fails) picks the best-matching guide section by keywords. It says when it isn't sure, so a person can step in."""

import logging
import re
from functools import lru_cache
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)
GUIDE_PATH = Path(__file__).with_name("help_guide.md")


@lru_cache
def guide() -> str:
    return GUIDE_PATH.read_text(encoding="utf-8")


def sections() -> list[tuple[str, str]]:
    parts = re.split(r"^## ", guide(), flags=re.M)[1:]
    return [(p.split("\n", 1)[0].strip(), p.split("\n", 1)[1].strip()) for p in parts]


class HelpAnswer(BaseModel):
    answer: str = Field(
        max_length=1500,
        description="Short, friendly, step by step. Plain English (or Tamil/Tanglish "
        "if the question is in it). Only facts from the guide.",
    )
    covered: bool = Field(description="True only if the guide fully answers the question.")
    topic: str = Field(max_length=20, description="One of: payment, bug, account, feature, other.")


SYSTEM = """You are Virundhu's Quick help assistant. Answer ONLY from the guide below. Be brief and practical: numbered
steps when there are steps, and name the exact menu (e.g. Settings → Outlets). Never invent features, prices, dates or
promises. Never ask for passwords or card numbers. If the guide doesn't cover the question, or it needs someone to look
at their account or a payment, say so in one line and set covered=false so they can talk to a person.

GUIDE:
{guide}"""

_WORDS = re.compile(r"[a-z0-9]+")


def keyword_answer(question: str) -> HelpAnswer:
    q = set(_WORDS.findall(question.lower())) - {"the", "a", "is", "to", "my", "i", "not", "how", "do", "what", "and"}
    best, score = None, 0
    for title, body in sections():
        words = _WORDS.findall((title + " " + body).lower())
        s = sum(3 if w in title.lower() else 1 for w in q if w in words)
        if s > score:
            best, score = (title, body), s
    if not best or score < 2:
        return HelpAnswer(
            answer='I couldn\'t find this in the help guide. Tap "Talk to a person" and support will '
            "reply within 24 hours.",
            covered=False,
            topic="other",
        )
    title, body = best
    lines: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if lines and line and not re.match(r"^(- |\d+\. )", line):
            lines[-1] += " " + line  # join a wrapped line to its sentence
        elif line:
            lines.append(line)
    body = "\n".join(lines)
    topic = (
        "payment"
        if "payment" in title.lower() or "plan" in title.lower()
        else ("account" if "account" in title.lower() else "other")
    )
    return HelpAnswer(answer=f"{title}\n\n{body[:1200]}", covered=True, topic=topic)


def ask(question: str, history: list[dict] | None = None, org_id: int | None = None) -> HelpAnswer:
    question = question.strip()[:1000]
    if not settings.llm_configured:
        return keyword_answer(question)
    try:
        from app.ai.llm import chat_model

        extra = {} if settings.LLM_PROVIDER == "anthropic" else {"method": "function_calling"}
        model = chat_model("tagging", "help", org_id).with_structured_output(HelpAnswer, **extra)
        msgs = [SystemMessage(content=SYSTEM.format(guide=guide()))]
        for h in (history or [])[-6:]:
            text = str(h.get("text", ""))[:800]
            msgs.append(
                HumanMessage(content=text) if h.get("from") == "user" else SystemMessage(content=f"(You said) {text}")
            )
        msgs.append(HumanMessage(content=question))
        return model.invoke(msgs)
    except Exception:  # AI down: still help from the guide
        logger.exception("Quick help AI failed; using the guide search")
        return keyword_answer(question)


def draft_reply(
    subject: str, thread: list[tuple[bool, str]], restaurant: str | None, org_id: int | None = None
) -> str:
    """A suggested support reply for the admin, from the guide and the conversation. The admin edits and sends it."""
    convo = "\n".join(("SUPPORT: " if admin else "CUSTOMER: ") + body[:1500] for admin, body in thread[-8:])
    if not settings.llm_configured:
        return keyword_answer(subject + " " + (thread[-1][1] if thread else "")).answer
    from app.ai.llm import chat_model

    prompt = (
        f"Write a reply from Virundhu support to {restaurant or 'the customer'} about '{subject}'. Use only the "
        "guide's facts; if something needs checking (a payment, their account), say what you'll check and by when "
        "('within 24 hours'). Warm, short, plain English, sign off '- Virundhu support'. No placeholders.\n\n"
        f"CONVERSATION:\n{convo}"
    )
    res = chat_model("report", "support_draft", org_id).invoke(
        [SystemMessage(content=SYSTEM.format(guide=guide())), HumanMessage(content=prompt)]
    )
    return str(res.content).strip()
