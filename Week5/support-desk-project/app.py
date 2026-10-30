"""
Multi-Agent Customer Support Desk
AutoGen (AgentChat) + Streamlit  |  Social Eagle Gen AI Architect Buildathon

Three agents run one after another in a RoundRobinGroupChat:
  1. Assistant             -> answers from its own knowledge (no tools)
  2. Web_Search_Assistant  -> calls the web_search tool and answers from live results
  3. Entry_Agent           -> calls the save_to_file tool, then returns both answers

Run:  streamlit run app.py
"""

import asyncio
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

# Optional: load keys from a local .env file (never committed to GitHub)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import (
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
)
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
ANSWERS_FILE = BASE_DIR / "answers.txt"          # required by the spec
TICKETS_FILE = BASE_DIR / "tickets.jsonl"        # structured history for the UI

ASSISTANT = "Assistant"
WEB_AGENT = "Web_Search_Assistant"
ENTRY_AGENT = "Entry_Agent"
STOP_WORD = "TERMINATE"

AGENT_META = {
    ASSISTANT: {"icon": "🧠", "label": "Assistant (own knowledge)"},
    WEB_AGENT: {"icon": "🌐", "label": "Web Search Assistant"},
    ENTRY_AGENT: {"icon": "🗂️", "label": "Entry Agent"},
}

CATEGORIES = ["General", "Account & Login", "Billing & Payments", "Technical Issue",
              "Orders & Shipping", "Product Question", "Feedback / Complaint"]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]
TONES = ["Friendly", "Professional", "Concise", "Step-by-step"]

SAMPLE_QUERIES = [
    "How do I reset my password?",
    "How do I enable two-factor authentication on Gmail?",
    "My order hasn't arrived, what should I do?",
    "How do I get a refund on the Apple App Store?",
]

# Collected during a run so the UI can show the web sources as clickable links
SEARCH_SOURCES: list[dict] = []


# --------------------------------------------------------------------------
# Tools (plain Python functions -> AutoGen tools)
# --------------------------------------------------------------------------
def web_search(query: str) -> str:
    """Search the web for the customer's query and return the top results
    (title, link, snippet) as text."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "ERROR: SERPER_API_KEY is not set, so web search is unavailable."

    num = int(os.getenv("SEARCH_RESULTS", "5"))
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": num},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # network / auth / quota errors
        return f"ERROR: web search failed - {exc}"

    lines = []
    answer_box = data.get("answerBox", {})
    if answer_box.get("answer") or answer_box.get("snippet"):
        lines.append(f"Featured answer: {answer_box.get('answer') or answer_box.get('snippet')}")

    for i, item in enumerate(data.get("organic", [])[:num], start=1):
        title, link, snippet = item.get("title", ""), item.get("link", ""), item.get("snippet", "")
        SEARCH_SOURCES.append({"title": title, "link": link, "snippet": snippet})
        lines.append(f"[{i}] {title}\n    {link}\n    {snippet}")

    return "\n".join(lines) if lines else "No results found."


def save_to_file(ticket_id: str, query: str, assistant_answer: str, web_search_answer: str) -> str:
    """Save the ticket id, the customer query, the Assistant answer and the
    Web Search answer into answers.txt."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = (
        f"{'=' * 70}\n"
        f"Ticket   : {ticket_id}\n"
        f"Time     : {stamp}\n"
        f"Query    : {query}\n"
        f"{'-' * 70}\n"
        f"[Answer 1 - Assistant]\n{assistant_answer.strip()}\n"
        f"{'-' * 70}\n"
        f"[Answer 2 - Web Search Assistant]\n{web_search_answer.strip()}\n"
        f"{'=' * 70}\n\n"
    )
    with open(ANSWERS_FILE, "a", encoding="utf-8") as f:
        f.write(block)
    return f"Saved ticket {ticket_id} to {ANSWERS_FILE.name}"


# --------------------------------------------------------------------------
# Team
# --------------------------------------------------------------------------
def build_team(model_client, tone: str) -> RoundRobinGroupChat:
    assistant = AssistantAgent(
        name=ASSISTANT,
        model_client=model_client,
        description="Answers the customer's query from its own knowledge.",
        system_message=(
            "You are a senior customer support agent. Answer the customer's query "
            "directly from your own knowledge. You have no tools. "
            f"Tone: {tone}. Use short paragraphs or numbered steps where helpful. "
            "Take the customer name, category and priority into account. "
            "Do not mention other agents and never write the word TERMINATE."
        ),
    )

    web_agent = AssistantAgent(
        name=WEB_AGENT,
        model_client=model_client,
        tools=[web_search],
        reflect_on_tool_use=True,  # read the search results, then write a real answer
        description="Searches the web and answers from live results.",
        system_message=(
            "You are a customer support researcher. ALWAYS call the web_search tool "
            "once with a clear search query built from the customer's question. Then "
            "write an answer based ONLY on the search results, and end with a short "
            "'Sources:' list of the links you used. If the search failed, say so "
            f"briefly. Tone: {tone}. Never write the word TERMINATE."
        ),
    )

    entry_agent = AssistantAgent(
        name=ENTRY_AGENT,
        model_client=model_client,
        tools=[save_to_file],
        reflect_on_tool_use=True,
        description="Saves the query and both answers, then hands them back.",
        system_message=(
            f"You are the ticket entry agent. Read the conversation. Call save_to_file "
            f"exactly once with: the ticket id, the customer's query, the full answer "
            f"written by {ASSISTANT}, and the full answer written by {WEB_AGENT} "
            "(copy them word for word). After the tool succeeds, reply with one short "
            "line confirming the ticket was saved, then on a new line write TERMINATE."
        ),
    )

    termination = TextMentionTermination(STOP_WORD, sources=[ENTRY_AGENT]) | MaxMessageTermination(12)
    return RoundRobinGroupChat([assistant, web_agent, entry_agent], termination_condition=termination)


def build_task(ticket: dict) -> str:
    return (
        f"Ticket ID: {ticket['id']}\n"
        f"Customer: {ticket['customer'] or 'Guest'}\n"
        f"Category: {ticket['category']}\n"
        f"Priority: {ticket['priority']}\n\n"
        f"Customer query: {ticket['query']}"
    )


def clean(text: str) -> str:
    return re.sub(rf"\s*{STOP_WORD}\s*$", "", text or "").strip()


async def run_team(ticket: dict, settings: dict, on_event) -> dict:
    """Run the 3-agent team and stream every event back to the UI."""
    SEARCH_SOURCES.clear()
    os.environ["SEARCH_RESULTS"] = str(settings["results"])

    model_client = OpenAIChatCompletionClient(
        model=settings["model"], temperature=settings["temperature"]
    )
    team = build_team(model_client, settings["tone"])

    answers = {ASSISTANT: "", WEB_AGENT: "", ENTRY_AGENT: ""}
    tool_calls = []
    stop_reason, usage = "", {"prompt": 0, "completion": 0}

    try:
        async for msg in team.run_stream(task=build_task(ticket)):
            if isinstance(msg, TaskResult):
                stop_reason = msg.stop_reason or ""
                continue
            source = getattr(msg, "source", "")
            mu = getattr(msg, "models_usage", None)
            if mu:
                usage["prompt"] += mu.prompt_tokens
                usage["completion"] += mu.completion_tokens

            if isinstance(msg, ToolCallRequestEvent):
                for call in msg.content:
                    tool_calls.append({"agent": source, "tool": call.name, "args": call.arguments})
                    on_event("tool", source, f"Calling `{call.name}`")
            elif isinstance(msg, ToolCallExecutionEvent):
                for res in msg.content:
                    on_event("tool_done", source, "Tool error" if res.is_error else "Tool finished")
            elif isinstance(msg, (TextMessage, ToolCallSummaryMessage)) and source in answers:
                answers[source] = clean(msg.content)
                on_event("answer", source, answers[source])
    finally:
        await model_client.close()

    return {
        "answers": answers,
        "tool_calls": tool_calls,
        "sources": list(SEARCH_SOURCES),
        "stop_reason": stop_reason,
        "usage": usage,
    }


# --------------------------------------------------------------------------
# History helpers
# --------------------------------------------------------------------------
def save_ticket(record: dict) -> None:
    with open(TICKETS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_tickets() -> list[dict]:
    if not TICKETS_FILE.exists():
        return []
    out = []
    for line in TICKETS_FILE.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return list(reversed(out))


def update_feedback(ticket_id: str, value: str) -> None:
    tickets = list(reversed(load_tickets()))
    for t in tickets:
        if t["id"] == ticket_id:
            t["feedback"] = value
    TICKETS_FILE.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tickets), encoding="utf-8")


def transcript(t: dict) -> str:
    a = t["answers"]
    return (
        f"Ticket {t['id']} | {t['time']}\nCustomer: {t['customer'] or 'Guest'} | "
        f"Category: {t['category']} | Priority: {t['priority']}\n\nQuery: {t['query']}\n\n"
        f"--- Assistant answer ---\n{a.get(ASSISTANT, '')}\n\n"
        f"--- Web Search answer ---\n{a.get(WEB_AGENT, '')}\n"
    )


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
st.set_page_config(page_title="AI Support Desk", page_icon="🎧", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem;}
      .hero {padding: 1.2rem 1.4rem; border-radius: 14px;
             background: linear-gradient(120deg, #4f46e5 0%, #0ea5e9 100%); color: white;}
      .hero h1 {margin: 0; font-size: 1.8rem; color: white;}
      .hero p {margin: .3rem 0 0; opacity: .9;}
      .pill {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.78rem;
             margin-right:6px; background:rgba(99,102,241,.12); border:1px solid rgba(99,102,241,.35);}
    </style>
    """,
    unsafe_allow_html=True,
)

ss = st.session_state
ss.setdefault("query", "")
ss.setdefault("last", None)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("⚙️ Settings")
    openai_ok = bool(os.getenv("OPENAI_API_KEY"))
    serper_ok = bool(os.getenv("SERPER_API_KEY"))
    st.write(("✅" if openai_ok else "❌") + " OPENAI_API_KEY")
    st.write(("✅" if serper_ok else "⚠️") + " SERPER_API_KEY")

    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"], index=0)
    temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.3, 0.1)
    results = st.slider("Web results to read", 3, 10, 5)
    tone = st.selectbox("Answer tone", TONES)

    st.divider()
    st.subheader("👤 Customer")
    customer = st.text_input("Name / email (optional)")
    category = st.selectbox("Category", CATEGORIES)
    priority = st.select_slider("Priority", PRIORITIES, value="Medium")

    st.divider()
    tickets_all = load_tickets()
    st.metric("Tickets handled", len(tickets_all))
    if ANSWERS_FILE.exists():
        st.download_button("⬇️ Download answers.txt", ANSWERS_FILE.read_text(encoding="utf-8"),
                           file_name="answers.txt")

# ---------------- Header ----------------
st.markdown(
    """<div class="hero"><h1>🎧 AI Customer Support Desk</h1>
    <p>Three AutoGen agents in sequence: 🧠 Assistant → 🌐 Web Search Assistant → 🗂️ Entry Agent</p></div>""",
    unsafe_allow_html=True,
)
st.write("")

tab_ask, tab_history, tab_how = st.tabs(["💬 Ask Support", "📜 Ticket History", "🧩 How it works"])

# ---------------- Ask tab ----------------
with tab_ask:
    st.caption("Try a sample question:")
    cols = st.columns(len(SAMPLE_QUERIES))
    for col, q in zip(cols, SAMPLE_QUERIES):
        if col.button(q, use_container_width=True):
            ss.query = q

    with st.form("ask_form"):
        query = st.text_area("Your question or task", key="query", height=100,
                             placeholder="e.g. How do I reset my password?")
        submitted = st.form_submit_button("🚀 Send to support team", type="primary",
                                          use_container_width=True)

    if submitted:
        if not query.strip():
            st.warning("Please type a question first.")
        elif not openai_ok:
            st.error("OPENAI_API_KEY is missing. Add it to your .env file and restart the app.")
        else:
            ticket = {
                "id": "TKT-" + uuid.uuid4().hex[:6].upper(),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "query": query.strip(), "customer": customer.strip(),
                "category": category, "priority": priority,
            }
            settings = {"model": model, "temperature": temperature, "results": results, "tone": tone}

            progress = st.progress(0, text="Starting the team…")
            status = st.status(f"Working on ticket {ticket['id']}…", expanded=True)
            steps = {ASSISTANT: 33, WEB_AGENT: 66, ENTRY_AGENT: 100}

            def on_event(kind, source, text):
                icon = AGENT_META.get(source, {}).get("icon", "•")
                if kind == "answer":
                    status.write(f"{icon} **{source}** finished.")
                    progress.progress(steps.get(source, 0), text=f"{source} done")
                elif kind == "tool":
                    status.write(f"{icon} **{source}** → {text}")
                else:
                    status.write(f"   ↳ {text}")

            start = datetime.now()
            try:
                result = asyncio.run(run_team(ticket, settings, on_event))
                secs = (datetime.now() - start).total_seconds()
                status.update(label=f"Ticket {ticket['id']} resolved in {secs:.1f}s", state="complete",
                              expanded=False)
                record = {**ticket, **result, "settings": settings, "seconds": round(secs, 1),
                          "feedback": None}
                save_ticket(record)
                ss.last = record
            except Exception as exc:
                status.update(label="Something went wrong", state="error")
                st.exception(exc)

    last = ss.last
    if last:
        a = last["answers"]
        st.markdown(
            f"<span class='pill'>🎫 {last['id']}</span><span class='pill'>📂 {last['category']}</span>"
            f"<span class='pill'>⚡ {last['priority']}</span><span class='pill'>⏱️ {last['seconds']}s</span>"
            f"<span class='pill'>🔢 {last['usage']['prompt'] + last['usage']['completion']} tokens</span>",
            unsafe_allow_html=True,
        )
        st.markdown(f"**Question:** {last['query']}")

        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.subheader("🧠 Answer 1 · Assistant")
                st.markdown(a.get(ASSISTANT) or "_No answer_")
        with c2:
            with st.container(border=True):
                st.subheader("🌐 Answer 2 · Web Search")
                st.markdown(a.get(WEB_AGENT) or "_No answer_")
                if last["sources"]:
                    with st.expander(f"🔗 {len(last['sources'])} web sources"):
                        for s in last["sources"]:
                            st.markdown(f"- [{s['title']}]({s['link']})  \n  <small>{s['snippet']}</small>",
                                        unsafe_allow_html=True)

        st.success(f"🗂️ Entry Agent: {a.get(ENTRY_AGENT) or 'Saved to answers.txt'}")

        f1, f2, f3, f4 = st.columns([1, 1, 2, 3])
        if f1.button("👍 Helpful", key="up"):
            update_feedback(last["id"], "helpful"); last["feedback"] = "helpful"
        if f2.button("👎 Not helpful", key="down"):
            update_feedback(last["id"], "not helpful"); last["feedback"] = "not helpful"
        f3.download_button("⬇️ Download transcript", transcript(last), file_name=f"{last['id']}.txt")
        if last.get("feedback"):
            f4.caption(f"Thanks! Feedback recorded: **{last['feedback']}**")

        with st.expander("🔍 Agent activity (tool calls & stop reason)"):
            st.write(f"**Stop reason:** {last['stop_reason']}")
            st.json(last["tool_calls"])

# ---------------- History tab ----------------
with tab_history:
    tickets = load_tickets()
    if not tickets:
        st.info("No tickets yet. Ask your first question in the **Ask Support** tab.")
    else:
        search = st.text_input("🔎 Filter tickets", placeholder="Search by keyword or ticket id")
        cat_filter = st.multiselect("Category", CATEGORIES)
        shown = [t for t in tickets
                 if (not search or search.lower() in (t["query"] + t["id"]).lower())
                 and (not cat_filter or t["category"] in cat_filter)]
        helpful = sum(1 for t in tickets if t.get("feedback") == "helpful")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total tickets", len(tickets))
        m2.metric("Marked helpful", helpful)
        m3.metric("Avg. time", f"{sum(t.get('seconds', 0) for t in tickets) / len(tickets):.1f}s")
        for t in shown:
            with st.expander(f"{t['id']} · {t['time']} · {t['query'][:70]}"):
                st.caption(f"{t['customer'] or 'Guest'} · {t['category']} · {t['priority']} · "
                           f"feedback: {t.get('feedback') or '—'}")
                h1, h2 = st.columns(2)
                h1.markdown("**🧠 Assistant**\n\n" + (t["answers"].get(ASSISTANT) or ""))
                h2.markdown("**🌐 Web Search**\n\n" + (t["answers"].get(WEB_AGENT) or ""))

# ---------------- How it works tab ----------------
with tab_how:
    st.markdown(
        """
| Order | Agent | Tool | Job |
|---|---|---|---|
| 1 | 🧠 **Assistant** | none | Answers from its own knowledge |
| 2 | 🌐 **Web_Search_Assistant** | `web_search` (Serper) | Searches Google, answers from results, lists sources |
| 3 | 🗂️ **Entry_Agent** | `save_to_file` | Writes ticket + query + both answers to `answers.txt`, then says **TERMINATE** |

- **Team:** `RoundRobinGroupChat` → fixed order, every agent sees the shared history.
- **Stop:** `TextMentionTermination("TERMINATE", sources=["Entry_Agent"]) | MaxMessageTermination(12)`.
- **Streaming:** `team.run_stream()` feeds the live status panel; `asyncio.run()` bridges async AutoGen and Streamlit.
- **Keys:** read from environment variables / `.env` — never hard-coded.
        """
    )
