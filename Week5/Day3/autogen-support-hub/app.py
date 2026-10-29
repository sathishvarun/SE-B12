"""
app.py  -  Streamlit front end ("SK Support Hub")
-----------------------------------------------------
Run with:   streamlit run app.py

Tabs:
  💬 Chat            - talk to the Head Agent, watch children work live
  🕸️ Agent Network   - parent -> child -> tool graph, last run highlighted
  📊 Analytics       - department load, tokens per agent, latency
  🎫 Tickets         - every ticket / request the child agents created
  🧾 Run Trace       - step-by-step timeline of any past run
"""

import asyncio

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from agents import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    DEPARTMENTS,
    HEAD_AGENT_NAME,
    SupportOrchestrator,
    TraceEvent,
    get_api_key,
)
from agents.tools import build_department_tools

# ---------------------------------------------------------------------------
# Page setup + custom styling
# ---------------------------------------------------------------------------
st.set_page_config(page_title="SK Support Hub", page_icon="🛰️", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"], .stMarkdown, p, li { font-family: 'Inter', sans-serif; }
h1, h2, h3, .hero-title, .kpi-value { font-family: 'Space Grotesk', sans-serif !important; }

.stApp {
  background:
    radial-gradient(1200px 500px at 10% -10%, rgba(99,102,241,.25), transparent 60%),
    radial-gradient(900px 400px at 100% 0%, rgba(14,165,233,.18), transparent 60%),
    #0B1020;
}
section[data-testid="stSidebar"] { background: #0E1428; border-right: 1px solid rgba(148,163,184,.12); }

.hero { padding: 18px 24px; border-radius: 18px; margin-bottom: 14px;
        background: linear-gradient(135deg, rgba(99,102,241,.22), rgba(14,165,233,.10));
        border: 1px solid rgba(148,163,184,.18); }
.hero-title { font-size: 30px; font-weight: 700; color: #F8FAFC; margin: 0; }
.hero-sub { color: #94A3B8; margin-top: 4px; font-size: 14.5px; }
.pulse { display:inline-block; width:9px; height:9px; border-radius:50%; background:#22C55E;
         margin-right:8px; box-shadow:0 0 0 0 rgba(34,197,94,.7); animation:pulse 1.8s infinite; }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(34,197,94,.6);} 70%{box-shadow:0 0 0 10px rgba(34,197,94,0);} 100%{box-shadow:0 0 0 0 rgba(34,197,94,0);} }

.kpi { background: rgba(15,23,42,.72); border: 1px solid rgba(148,163,184,.14);
       border-radius: 14px; padding: 12px 16px; }
.kpi-label { color:#94A3B8; font-size:12px; text-transform:uppercase; letter-spacing:.06em; }
.kpi-value { color:#F8FAFC; font-size:26px; font-weight:700; }

.dept-card { border-radius: 14px; padding: 12px 14px; margin-bottom: 10px;
             background: rgba(15,23,42,.72); border: 1px solid rgba(148,163,184,.14); }
.dept-card h4 { margin: 0 0 4px 0; color:#F8FAFC; font-size: 16px; }
.dept-card p { margin: 0; color:#94A3B8; font-size: 13px; }

.badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px;
         font-weight:600; margin:2px 4px 2px 0; border:1px solid; }

.trace-row { display:flex; gap:10px; padding:8px 10px; border-radius:10px; margin-bottom:6px;
             background: rgba(15,23,42,.6); border-left: 3px solid #475569; font-size: 13.5px; color:#E2E8F0; }
.trace-time { color:#64748B; min-width:52px; font-variant-numeric: tabular-nums; }
.trace-actor { font-weight:600; min-width:120px; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state (Streamlit reruns the script on every click, so we keep data here)
# ---------------------------------------------------------------------------
defaults = {"messages": [], "runs": [], "tickets": [], "pending": None}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

AGENT_COLORS = {HEAD_AGENT_NAME: "#6366F1", "Customer": "#E2E8F0", "System": "#EF4444"}
AGENT_COLORS.update({d["name"]: d["color"] for d in DEPARTMENTS.values()})
NAME_TO_KEY = {d["name"]: k for k, d in DEPARTMENTS.items()}
KIND_ICON = {
    "route": "📨", "delegate": "➡️", "tool_call": "🛠️", "tool_result": "📦",
    "report_back": "⬅️", "final": "✅", "error": "⛔",
}


def badge(key: str) -> str:
    d = DEPARTMENTS[key]
    return (f"<span class='badge' style='color:{d['color']};border-color:{d['color']}55;"
            f"background:{d['color']}18'>{d['icon']} {d['label']}</span>")


def trace_row(ev: TraceEvent) -> str:
    color = AGENT_COLORS.get(ev.actor, "#94A3B8")
    arrow = f" → <b>{ev.target}</b>" if ev.target else ""
    return (f"<div class='trace-row' style='border-left-color:{color}'>"
            f"<span class='trace-time'>{ev.t:>5.2f}s</span>"
            f"<span class='trace-actor' style='color:{color}'>{KIND_ICON.get(ev.kind, '•')} {ev.actor}</span>"
            f"<span>{ev.detail}{arrow}</span></div>")


def plot_style(fig: go.Figure, height: int = 320) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CBD5E1", family="Inter"),
        xaxis=dict(gridcolor="rgba(148,163,184,.12)"), yaxis=dict(gridcolor="rgba(148,163,184,.12)"),
    )
    return fig


# ---------------------------------------------------------------------------
# Sidebar - settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🛰️ Control Panel")
    if get_api_key():
        st.success("OpenAI key loaded from .env", icon="🔐")
    else:
        st.error("No OPENAI_API_KEY found. Create a .env file (see README).", icon="⚠️")

    model = st.selectbox("Model", AVAILABLE_MODELS,
                         index=AVAILABLE_MODELS.index(DEFAULT_MODEL) if DEFAULT_MODEL in AVAILABLE_MODELS else 0)

    st.markdown("#### Child agents")
    enabled = [k for k, d in DEPARTMENTS.items() if st.toggle(f"{d['icon']} {d['label']}", value=True, key=f"tg_{k}")]
    if not enabled:
        st.warning("Enable at least one department.")

    st.divider()
    if st.button("🧹 Clear conversation", width="stretch"):
        for k, v in defaults.items():
            st.session_state[k] = [] if isinstance(v, list) else v
        st.rerun()
    st.caption("Built with Microsoft AutoGen · OpenAI · Streamlit")

# ---------------------------------------------------------------------------
# Header + KPIs
# ---------------------------------------------------------------------------
st.markdown(
    f"""<div class='hero'>
      <p class='hero-title'><span class='pulse'></span>SK Support Hub</p>
      <div class='hero-sub'>One Head Agent · {len(enabled)} department agents · parent → child delegation with live tracing</div>
    </div>""",
    unsafe_allow_html=True,
)

runs = st.session_state.runs
kpis = [
    ("Queries handled", len(runs)),
    ("Agents online", 1 + len(enabled)),
    ("Avg response", f"{(sum(r.latency for r in runs) / len(runs)):.1f}s" if runs else "—"),
    ("Tickets created", len(st.session_state.tickets)),
    ("Tokens used", f"{sum(sum(r.tokens.values()) for r in runs):,}"),
]
for col, (label, value) in zip(st.columns(len(kpis)), kpis):
    col.markdown(f"<div class='kpi'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div></div>",
                 unsafe_allow_html=True)
st.write("")

tab_chat, tab_net, tab_stats, tab_tix, tab_trace = st.tabs(
    ["💬 Chat", "🕸️ Agent Network", "📊 Analytics", "🎫 Tickets", "🧾 Run Trace"]
)

# ---------------------------------------------------------------------------
# TAB 1 - Chat
# ---------------------------------------------------------------------------
SAMPLES = [
    "My VPN is very slow today, can you check and raise a ticket?",
    "How many annual leaves do I have left? My ID is EMP1002",
    "What's the status of invoice INV-2042 and can I get a refund?",
    "Compare your Starter and Growth plans for a 25-person team",
    "Which webinars and events are coming up next month?",
    "I'm a new joiner: how do I reset my email password and what health insurance do I get?",
]

with tab_chat:
    left, right = st.columns([3, 2], gap="large")

    with right:
        st.markdown("##### ⚡ Try a question")
        for i, q in enumerate(SAMPLES):
            if st.button(q, key=f"sample_{i}", width="stretch"):
                st.session_state.pending = q
                st.rerun()
        st.markdown("##### 🧭 Department agents")
        for k in enabled:
            d = DEPARTMENTS[k]
            st.markdown(f"<div class='dept-card' style='border-left:3px solid {d['color']}'>"
                        f"<h4>{d['icon']} {d['label']}</h4><p>{d['scope']}</p></div>", unsafe_allow_html=True)

    with left:
        if not st.session_state.messages and not st.session_state.pending:
            st.info("👋 Ask anything about IT, HR, Finance, Sales or Marketing. "
                    "The Head Agent will route it to the right specialist(s).")

        for m in st.session_state.messages:
            with st.chat_message(m["role"], avatar="🧑" if m["role"] == "user" else "🛰️"):
                if m.get("departments"):
                    st.markdown(" ".join(badge(k) for k in m["departments"]) +
                                f"<span style='color:#64748B;font-size:12px'> · {m['latency']}s</span>",
                                unsafe_allow_html=True)
                st.markdown(m["content"])

        # ---- process a new question -----------------------------------
        question = st.session_state.pending
        if question:
            st.session_state.pending = None
            with st.chat_message("user", avatar="🧑"):
                st.markdown(question)

            with st.chat_message("assistant", avatar="🛰️"):
                status = st.status("Head Agent is reading your request…", expanded=True)
                live = status.empty()
                lines: list[str] = []

                def on_event(ev: TraceEvent) -> None:
                    """Called by the orchestrator for every step -> live UI update."""
                    lines.append(trace_row(ev))
                    live.markdown("".join(lines), unsafe_allow_html=True)
                    if ev.kind == "delegate":
                        status.update(label=f"Head Agent assigned work to {ev.target}…")
                    elif ev.kind == "report_back":
                        status.update(label=f"{ev.actor} reported back to Head Agent…")

                if not get_api_key():
                    result = None
                    status.update(label="Missing API key", state="error")
                    st.error("Add OPENAI_API_KEY to your .env file and restart the app.")
                else:
                    orchestrator = SupportOrchestrator(model=model, enabled_departments=enabled, on_event=on_event)
                    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                    result = asyncio.run(orchestrator.ask(question, history))
                    status.update(label=f"Done in {result.latency}s · {len(result.departments)} department(s) involved",
                                  state="complete", expanded=False)

            st.session_state.messages.append({"role": "user", "content": question})
            if result:
                st.session_state.messages.append({
                    "role": "assistant", "content": result.answer,
                    "departments": result.departments, "latency": result.latency,
                })
                st.session_state.runs.append(result)
                st.session_state.tickets.extend(result.tickets)
            st.rerun()

# Chat input sits at the bottom of the page
if prompt := st.chat_input("Ask the support hub…", disabled=not enabled):
    st.session_state.pending = prompt
    st.rerun()

# ---------------------------------------------------------------------------
# TAB 2 - Agent Network (parent -> children -> tools)
# ---------------------------------------------------------------------------
with tab_net:
    last = runs[-1] if runs else None
    used = set(last.departments) if last else set()
    called_tools = {e.detail.split("(")[0] for e in last.trace if e.kind == "tool_call"} if last else set()

    dot = [
        "digraph G {", "rankdir=LR; bgcolor=transparent; nodesep=0.25; ranksep=0.9;",
        'node [shape=box, style="rounded,filled", fontname="Helvetica", fontcolor="#F8FAFC", color="#334155", fillcolor="#0F172A"];',
        'edge [color="#475569", arrowsize=0.7];',
        'Customer [label="🧑 Customer", fillcolor="#1E293B"];',
        f'{HEAD_AGENT_NAME} [label="🛰️ Head Agent\\n(parent / router)", fillcolor="#4338CA", color="#818CF8", penwidth=2];',
        f'Customer -> {HEAD_AGENT_NAME} [color="#818CF8", penwidth=2];',
    ]
    for k, d in DEPARTMENTS.items():
        on, hit = k in enabled, k in used
        fill = d["color"] + ("55" if hit else "22") if on else "#1E293B"
        dot.append(f'{d["name"]} [label="{d["icon"]} {d["label"]}", fillcolor="{fill}", '
                   f'color="{d["color"] if on else "#334155"}", penwidth={3 if hit else 1}, '
                   f'fontcolor="{"#F8FAFC" if on else "#64748B"}"];')
        dot.append(f'{HEAD_AGENT_NAME} -> {d["name"]} [dir=both, color="{d["color"] if hit else "#475569"}", '
                   f'penwidth={3 if hit else 1}, style={"solid" if on else "dashed"}];')
        for tool in build_department_tools(k, lambda t: None):
            t_hit = tool.name in called_tools and hit
            dot.append(f'"{tool.name}" [shape=note, fontsize=10, label="{tool.name}", '
                       f'fillcolor="{d["color"] + "44" if t_hit else "#0B1222"}", color="{d["color"] if t_hit else "#1E293B"}", '
                       f'fontcolor="{"#F8FAFC" if t_hit else "#94A3B8"}"];')
            dot.append(f'{d["name"]} -> "{tool.name}" [color="{d["color"] if t_hit else "#1E293B"}"];')
    dot.append("}")

    st.markdown("##### How a request flows")
    st.caption("Highlighted nodes = agents and tools used in the most recent question. Dashed = disabled agent.")
    st.graphviz_chart("\n".join(dot), width="stretch")

    c1, c2, c3 = st.columns(3)
    c1.markdown("**1 · Route** — the Head Agent reads the request and picks one or more departments.")
    c2.markdown("**2 · Delegate** — each child agent gets its own task and calls its own tools.")
    c3.markdown("**3 · Push back & merge** — children return results; the Head Agent writes one reply.")

# ---------------------------------------------------------------------------
# TAB 3 - Analytics
# ---------------------------------------------------------------------------
with tab_stats:
    if not runs:
        st.info("Ask a few questions to see analytics here.")
    else:
        a, b = st.columns(2)

        counts = {k: sum(k in r.departments for r in runs) for k in DEPARTMENTS}
        fig = go.Figure(go.Bar(
            x=[DEPARTMENTS[k]["label"] for k in counts], y=list(counts.values()),
            marker_color=[DEPARTMENTS[k]["color"] for k in counts], text=list(counts.values()), textposition="outside",
        ))
        fig.update_layout(title="Requests handled per department")
        a.plotly_chart(plot_style(fig), width="stretch")

        tok: dict[str, int] = {}
        for r in runs:
            for agent, n in r.tokens.items():
                tok[agent] = tok.get(agent, 0) + n
        tok = dict(sorted(tok.items(), key=lambda x: x[1]))
        fig = go.Figure(go.Bar(
            y=list(tok), x=list(tok.values()), orientation="h",
            marker_color=[AGENT_COLORS.get(n, "#94A3B8") for n in tok], text=[f"{v:,}" for v in tok.values()],
            textposition="outside",
        ))
        fig.update_layout(title="Tokens used per agent")
        b.plotly_chart(plot_style(fig), width="stretch")

        fig = go.Figure(go.Scatter(
            x=list(range(1, len(runs) + 1)), y=[r.latency for r in runs], mode="lines+markers",
            line=dict(color="#6366F1", width=3), marker=dict(size=9, color="#0EA5E9"),
            hovertext=[", ".join(DEPARTMENTS[k]["label"] for k in r.departments) or "Head only" for r in runs],
        ))
        fig.update_layout(title="Response time per question (seconds)", xaxis_title="Question #")
        st.plotly_chart(plot_style(fig, 280), width="stretch")

        multi = sum(len(r.departments) > 1 for r in runs)
        st.caption(f"{multi} of {len(runs)} questions needed more than one department.")

# ---------------------------------------------------------------------------
# TAB 4 - Tickets
# ---------------------------------------------------------------------------
with tab_tix:
    if not st.session_state.tickets:
        st.info("Tickets, refund requests and demo bookings created by the child agents will appear here.")
    else:
        df = pd.DataFrame(st.session_state.tickets)[["id", "department", "summary", "priority", "created", "sla"]]
        df.columns = ["Ticket", "Department", "Summary", "Priority", "Created", "SLA target"]
        st.dataframe(df, width="stretch", hide_index=True)
        st.download_button("⬇️ Download as CSV", df.to_csv(index=False), "tickets.csv", "text/csv")

# ---------------------------------------------------------------------------
# TAB 5 - Run trace
# ---------------------------------------------------------------------------
with tab_trace:
    if not runs:
        st.info("Every question produces a step-by-step trace of the parent and child agents.")
    else:
        user_qs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
        idx = st.selectbox("Choose a question", range(len(runs)), index=len(runs) - 1,
                           format_func=lambda i: f"#{i + 1} · {user_qs[i][:80] if i < len(user_qs) else ''}")
        r = runs[idx]
        st.markdown(" ".join(badge(k) for k in r.departments) or "_Answered by Head Agent only_", unsafe_allow_html=True)
        st.markdown("".join(trace_row(e) for e in r.trace), unsafe_allow_html=True)
