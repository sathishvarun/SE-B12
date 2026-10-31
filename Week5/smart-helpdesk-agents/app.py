"""Streamlit UI for the Smart Help Desk.  Run:  streamlit run app.py"""
import asyncio
import io
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config import COMPANY_NAME, SHOW_AGENT_STEPS, APP_PASSWORD, LOG_CSV, LOG_TXT, OPENAI_API_KEY, OPENAI_MODEL, SERPAPI_API_KEY
from team import run_ticket
from tools.ticket_store import load_tickets

st.set_page_config(page_title=f"{COMPANY_NAME} Help Desk", page_icon="🎧", layout="wide")

# ----------------------------------------------------------------------------
# Content shown to the user
# ----------------------------------------------------------------------------
# (icon, team, what they handle, [(short button label, full question sent), ...])
DEPT_CARDS = [
    ("🛟", "Client Support", "Production incidents, SLAs, support tickets and releases",
     [("Production is down!", "Our client's production application is down and no users can log in. This is a P1 – please help now!"),
      ("Raise a support ticket", "How do I raise a support ticket for a bug and how fast will the support team respond?")]),
    ("💳", "Finance", "Client invoices, payments and expense claims",
     [("Claim travel expenses", "How do I claim my cab and hotel expenses from the client visit in Bengaluru?"),
      ("Invoice charged twice", "The client says invoice INV-2291 was charged twice. Fix this now or their legal team will get involved.")]),
    ("📣", "Marketing", "Brand, case studies, webinars and blogs",
     [("Publish a case study", "We finished a cloud migration project for a client. How do I publish it as a case study?"),
      ("Host a tech webinar", "How early do I need to request a GenAI webinar for our clients?")]),
    ("💼", "Sales", "Rate card, discounts, RFPs and contracts",
     [("Rate & discount for 5 devs", "A client wants 5 Java developers for 12 months. What is our rate and what discount can I offer?"),
      ("Respond to an RFP", "We received an RFP from a bank. What is the process to respond?")]),
    ("👥", "HR", "Leave, hybrid work, onboarding and appraisals",
     [("Apply for leave", "How do I apply for 3 days of casual leave next week?"),
      ("Work from home rules", "How many days can I work from home in a week?")]),
    ("🖥️", "IT", "GitHub/Jira/AWS access, VPN, laptop and security",
     [("GitHub, Jira & AWS access", "I just joined a project. How do I get access to GitHub, Jira and the AWS dev account?"),
      ("VPN keeps dropping", "My VPN keeps disconnecting every 10 minutes and I can't reach the dev server.")]),
]

FRIENDLY_STEP = {
    "Router_Agent": "🧭 Understood your request",
    "Resolution_Agent": "✍️ Writing your answer",
    "Log_Agent": "🗂️ Saving your ticket",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p { font-family: 'Inter', sans-serif; }
[data-testid="stToolbar"] { display: none; }
.block-container { padding-top: 3.6rem; max-width: 1150px; }
h1, h2, h3, .hero-title { font-family: 'Poppins', sans-serif !important; }

.hero { background: linear-gradient(135deg, #14213D 0%, #23407a 60%, #FF6B1A 135%);
        border-radius: 22px; padding: 28px 32px 24px; color: #fff; margin-bottom: 14px;
        box-shadow: 0 10px 30px rgba(20,33,61,.18); }
.hero .hero-title { font-size: 2rem !important; font-weight: 700; margin: 0; color: #fff; line-height: 1.25; }
.hero .hero-sub { color: #dbe4ff; margin: 6px 0 18px; font-size: 1.02rem; }
.steps { display: flex; gap: 12px; flex-wrap: wrap; }
.step { flex: 1; min-width: 190px; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.22);
        border-radius: 14px; padding: 12px 14px; font-size: .9rem; color: #f1f5ff; }
.step .num { display:inline-block; width:24px; height:24px; line-height:24px; text-align:center; border-radius:50%;
             background:#FF6B1A; color:#fff; font-weight:700; margin-right:8px; font-size:.8rem; }

.section-title { font-family:'Poppins',sans-serif; font-weight:600; font-size:1.15rem; margin: 18px 0 2px; }
.section-sub { color:#6b7280; font-size:.9rem; margin-bottom:10px; }
.dept-head { font-weight:600; font-size:1.02rem; }
.dept-sub { color:#6b7280; font-size:.84rem; margin-bottom:6px; }

[class*="st-key-sample"] button { border-radius: 12px; justify-content: flex-start; text-align: left;
        font-size: .85rem; padding: 8px 12px; min-height: 0; }
[class*="st-key-sample"] button p { text-align:left; }

.chip { display:inline-block; padding:4px 11px; border-radius:999px; font-size:.78rem; font-weight:600;
        margin: 0 6px 6px 0; border:1px solid transparent; }
.chip-ok   { background:#dcfce7; color:#166534; }
.chip-esc  { background:#fee2e2; color:#991b1b; }
.chip-high { background:#fee2e2; color:#b91c1c; }
.chip-med  { background:#fef3c7; color:#92400e; }
.chip-low  { background:#dbeafe; color:#1e40af; }
.chip-dept { background:#eef2ff; color:#3730a3; }
.chip-id   { background:#f3f4f6; color:#374151; }
.handoff { background:#fff7ed; border-left:4px solid #FF6B1A; padding:10px 14px; border-radius:8px;
           color:#7c2d12; font-size:.9rem; margin-top:8px; }
.source { color:#6b7280; font-size:.82rem; margin-top:6px; }
.mini-hero { background: linear-gradient(135deg, #14213D 0%, #23407a 70%, #FF6B1A 160%); border-radius: 16px;
             padding: 14px 20px; color: #fff; margin-bottom: 12px; font-size: .95rem; }
.mini-hero b { font-family:'Poppins',sans-serif; font-size: 1.1rem; }
.ex-label { font-weight:600; font-size:.95rem; margin: 2px 0 2px; }
.ex-sub { color:#6b7280; font-size:.85rem; margin: 2px 0 4px; }
[class*="st-key-team_pick"] button, [class*="st-key-q_pick"] button { font-size: .9rem; padding: 6px 14px; }
[class*="st-key-q_pick"] button { border-color: #FF6B1A55; }
</style>
"""


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def password_gate():
    if not APP_PASSWORD or st.session_state.get("authed"):
        return
    st.markdown(f"<div class='hero'><p class='hero-title'>🔒 {COMPANY_NAME} Help Desk</p>"
                "<p class='hero-sub'>Please enter the team password to continue.</p></div>",
                unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password")
    if st.button("Enter", type="primary"):
        if pwd == APP_PASSWORD:
            st.session_state.authed = True
            st.rerun()
        st.error("That password is not correct.")
    st.stop()


def chips(r: dict) -> str:
    status = (f"<span class='chip chip-ok'>✅ Solved</span>" if r["status"] == "Resolved"
              else f"<span class='chip chip-esc'>🙋 Passed to a person</span>")
    pr = {"High": "chip-high", "Medium": "chip-med", "Low": "chip-low"}.get(r["priority"], "chip-low")
    return (status
            + f"<span class='chip chip-dept'>{r['department']} team</span>"
            + f"<span class='chip {pr}'>{r['priority']} priority</span>"
            + f"<span class='chip chip-id'>🎫 {r['ticket_id']}</span>")


def render_answer(msg: dict):
    r = msg["result"]
    st.markdown(chips(r), unsafe_allow_html=True)
    st.markdown(r["response"])
    if r["status"] == "Escalated":
        why = f"<br><small>Why: {r['escalation_reason']}</small>" if SHOW_AGENT_STEPS else ""
        st.markdown(f"<div class='handoff'>🙋 A person from the <b>{r['assigned_to'].replace(' human team', ' team')}</b> will follow up on this "
                    f"shortly. Please keep your ticket number <b>{r['ticket_id']}</b> handy.{why}</div>",
                    unsafe_allow_html=True)
    if not SHOW_AGENT_STEPS:  # employees only see the answer, nothing about files or agents
        return
    src = r["kb_sources"] if r["kb_sources"] != "NONE" else "no matching company document"
    st.markdown(f"<div class='source'>📄 Based on: {src}</div>", unsafe_allow_html=True)
    if msg.get("steps"):
        with st.expander("🔍 Behind the scenes — how the AI team handled this"):
            for agent, kind, text in msg["steps"]:
                label = agent.replace("_", " ")
                if kind == "tool_call":
                    st.caption(f"**{label}** · using a tool")
                    st.code(text, language=None)
                elif kind == "tool_result":
                    st.caption(f"**{label}** · tool result")
                    st.code(text[:1500], language=None)
                else:
                    st.caption(f"**{label}**")
                    st.markdown(text)


def to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False, sheet_name="Tickets")
    return buf.getvalue()


# ----------------------------------------------------------------------------
# Page 1: Ask
# ----------------------------------------------------------------------------
def page_ask():
    history = st.session_state.setdefault("chat", [])
    if not (st.session_state.get("user_name") and st.session_state.get("user_ref")):
        details_gate()
        return

    # ---- 1. Welcome banner (slim once a conversation has started) -------------
    if history:
        st.markdown(f"<div class='mini-hero'><b>🎧 {COMPANY_NAME} Help Desk</b> &nbsp;·&nbsp; "
                    f"Hi {st.session_state.user_name}, ask anything — we send it to the right team automatically.</div>",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='hero'>
          <p class='hero-title'>Hi {st.session_state.user_name} 👋 How can we help today?</p>
          <p class='hero-sub'>Ask anything about client support, finance, marketing, sales, HR or IT at
             {COMPANY_NAME} — in your own words. No need to know which team to contact.</p>
          <div class='steps'>
            <div class='step'><span class='num'>1</span>Pick an example or type your question</div>
            <div class='step'><span class='num'>2</span>We send it to the right team automatically</div>
            <div class='step'><span class='num'>3</span>Get an answer from company policy — or a person follows up</div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ---- 2. Example questions: one line of teams, then that team's questions ---
    example_bar()

    # ---- 3. Conversation (newest at the bottom, just above the question box) --
    if not history:
        with st.chat_message("assistant", avatar="🎧"):
            st.markdown(f"I'm the **{COMPANY_NAME} Help Desk Assistant**. Pick a team above and tap an example, "
                        "or type your own question in the box at the bottom.")
    for msg in history:
        with st.chat_message(msg["role"], avatar="🙂" if msg["role"] == "user" else "🎧"):
            if msg["role"] == "user":
                st.markdown(msg["text"])
            elif "result" in msg:
                render_answer(msg)
            else:
                st.markdown(msg["text"])

    # ---- 4. Question box, always last -----------------------------------------
    question = st.chat_input("Type your question here… e.g. “How do I apply for leave?”")
    question = question or st.session_state.pop("pending", None)
    if question:
        handle_question(question)
    if st.session_state.chat:
        scroll_to_bottom()


def details_gate():
    st.markdown(f"""
    <div class='hero'>
      <p class='hero-title'>Welcome to the {COMPANY_NAME} Help Desk 👋</p>
      <p class='hero-sub'>One place for every question — client support, finance, marketing, sales, HR and IT.
         Tell us who you are to get started.</p>
      <div class='steps'>
        <div class='step'><span class='num'>1</span>Enter your name and Employee ID</div>
        <div class='step'><span class='num'>2</span>Pick an example or type your question</div>
        <div class='step'><span class='num'>3</span>Get an answer — or the right team follows up</div>
      </div>
    </div>""", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])
    with mid.form("details"):
        st.markdown("#### 👤 Your details")
        name = st.text_input("Full name *", placeholder="e.g. Priya Raman")
        emp_id = st.text_input("Employee ID *", placeholder="e.g. SK1045")
        st.caption("Both fields are required. They are saved on every ticket so the team can reach you.")
        if st.form_submit_button("Start chatting →", type="primary", width="stretch"):
            if not name.strip() or not emp_id.strip():
                st.error("Please enter both your name and your Employee ID.")
            else:
                st.session_state.user_name = name.strip().title()
                st.session_state.user_ref = emp_id.strip().upper()
                st.rerun()


def send_example(key: str, options: dict):
    picked = st.session_state.get(key)
    if picked:
        st.session_state.pending = options[picked]
        st.session_state[key] = None  # clear the chip so it can be tapped again


def example_bar():
    with st.container(border=True):
        st.markdown("<div class='ex-label'>💡 Try an example — pick a team</div>", unsafe_allow_html=True)
        teams = [f"{icon} {name}" for icon, name, _, _ in DEPT_CARDS]
        team = st.pills("Team", teams, default=teams[0], key="team_pick",
                        label_visibility="collapsed") or teams[0]
        icon, name, sub, qs = DEPT_CARDS[teams.index(team)]
        st.markdown(f"<div class='ex-sub'>{icon} <b>{name}</b> · {sub}. Tap a question to ask it:</div>",
                    unsafe_allow_html=True)
        options = {f"💬 {short}": full for short, full in qs}
        key = f"q_pick_{name}"
        st.pills("Questions", list(options), key=key, label_visibility="collapsed",
                 on_change=send_example, args=(key, options))


def scroll_to_bottom():
    components.html("""<script>
      setTimeout(() => {
        const d = window.parent.document;
        const main = d.querySelector('[data-testid="stMain"]') || d.querySelector('section.main');
        if (main) main.scrollTo({top: main.scrollHeight, behavior: 'smooth'});
        window.parent.scrollTo({top: d.body.scrollHeight, behavior: 'smooth'});
      }, 400);
    </script>""", height=0)


def handle_question(question: str):
    history = st.session_state.chat
    history.append({"role": "user", "text": question})
    with st.chat_message("user", avatar="🙂"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🎧"):
        if not OPENAI_API_KEY:
            text = ("⚠️ I'm not connected to the AI service yet. Ask the admin to add **OPENAI_API_KEY** "
                    "to the `.env` file and restart the app.")
            st.markdown(text)
            history.append({"role": "assistant", "text": text})
            return

        steps = []
        progress = st.empty()  # the progress box disappears once the answer is ready
        status = progress.status("Reading your question…", expanded=False)

        def on_event(agent: str, kind: str, text: str):
            steps.append((agent, kind, text))
            if agent == "Router_Agent":
                dept = text.split("|")[0].replace("Department:", "").strip()
                status.update(label=f"Sending it to the {dept} team…")
                status.write(f"🧭 Routed to **{dept}**")
            elif agent.endswith("_Agent") and agent not in FRIENDLY_STEP:
                if kind == "tool_call":
                    status.update(label="Checking company policy…")
                    status.write("🔎 Checking company policy")
                elif kind == "message":
                    status.write("📄 Found what we need")
            elif agent == "Resolution_Agent":
                status.update(label="Writing your answer…")
                status.write("✍️ Answer written")
            elif agent == "Log_Agent" and kind == "tool_result":
                status.write("🗂️ Ticket saved")

        try:
            result = asyncio.run(run_ticket(question, st.session_state.get("user_name", ""),
                                            st.session_state.get("user_ref", ""), on_event))
        except Exception as exc:
            status.update(label="Something went wrong", state="error")
            text = f"😕 Sorry, I couldn't process that right now. ({exc})"
            st.markdown(text)
            history.append({"role": "assistant", "text": text})
            return

        progress.empty()
        msg = {"role": "assistant", "result": result, "steps": steps}
        render_answer(msg)
        history.append(msg)


# ----------------------------------------------------------------------------
# Page 2: Ticket history
# ----------------------------------------------------------------------------
def page_history():
    st.markdown("### 🗂️ Ticket history")
    st.caption("Every question is saved as a ticket. Click a row to see the full details.")
    df = load_tickets()
    if df.empty:
        st.info("No tickets yet — ask a question on the **Ask** page first.")
        return

    m = st.columns(4)
    m[0].metric("Total tickets", len(df), border=True)
    m[1].metric("✅ Solved by AI", int((df["status"] == "Resolved").sum()), border=True)
    m[2].metric("🙋 Passed to a person", int((df["status"] == "Escalated").sum()), border=True)
    m[3].metric("🔴 High priority", int((df["priority"] == "High").sum()), border=True)

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    search = c1.text_input("Search", placeholder="Search tickets…", label_visibility="collapsed")
    dept = c2.selectbox("Team", ["All teams"] + sorted(df["department"].unique()), label_visibility="collapsed")
    prio = c3.selectbox("Priority", ["Any priority", "High", "Medium", "Low"], label_visibility="collapsed")
    stat = c4.selectbox("Status", ["Any status", "Resolved", "Escalated"], label_visibility="collapsed")

    view = df.iloc[::-1]
    if search:
        view = view[view.apply(lambda r: search.lower() in " ".join(r.values).lower(), axis=1)]
    if dept != "All teams":
        view = view[view["department"] == dept]
    if prio != "Any priority":
        view = view[view["priority"] == prio]
    if stat != "Any status":
        view = view[view["status"] == stat]

    table = pd.DataFrame({
        "Ticket": view["ticket_id"],
        "When": view["timestamp"],
        "Team": view["department"],
        "Priority": view["priority"].map({"High": "🔴 High", "Medium": "🟠 Medium", "Low": "🔵 Low"}),
        "Status": view["status"].map({"Resolved": "✅ Solved", "Escalated": "🙋 With a person"}),
        "Question": view["summary"].where(view["summary"] != "", view["complaint"]),
    })
    event = st.dataframe(table, hide_index=True, width="stretch", on_select="rerun",
                         selection_mode="single-row", height=min(420, 40 + 35 * len(table)))
    rows = event.selection.rows if event and event.selection else []
    if rows:
        r = view.iloc[rows[0]].to_dict()
        with st.container(border=True):
            st.markdown(f"**{r['ticket_id']}** · {r['timestamp']} · {r['employee_name'] or 'Anonymous'}"
                        f" {('· ' + r['employee_id']) if r['employee_id'] else ''}")
            st.markdown(chips(r), unsafe_allow_html=True)
            st.markdown(f"**Question:** {r['complaint']}")
            st.markdown(f"**Answer:**\n\n{r['response']}")
            if r["status"] == "Escalated":
                st.markdown(f"<div class='handoff'>Assigned to <b>{r['assigned_to']}</b> — {r['escalation_reason']}</div>",
                            unsafe_allow_html=True)
            if SHOW_AGENT_STEPS:
                st.caption(f"📄 Sources: {r['kb_sources']} · Confidence: {r['confidence']} · Sentiment: {r['sentiment']}")

    st.markdown("**Download**")
    d1, d2, d3, _ = st.columns([1, 1, 1, 3])
    d1.download_button("📊 Excel", to_excel(df), "tickets.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    d2.download_button("📄 CSV", LOG_CSV.read_bytes(), "tickets.csv", "text/csv", width="stretch")
    if LOG_TXT.exists():
        d3.download_button("📝 TXT", LOG_TXT.read_bytes(), "tickets.txt", "text/plain", width="stretch")


# ----------------------------------------------------------------------------
# Page 3: Weekly summary
# ----------------------------------------------------------------------------
def page_weekly():
    st.markdown("### 📊 Weekly summary")
    df = load_tickets()
    if df.empty:
        st.info("No tickets yet — the weekly summary appears once questions come in.")
        return
    df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce")

    c1, c2 = st.columns([1, 3])
    picked = c1.date_input("Week containing", value=date.today())
    start = datetime.combine(picked - timedelta(days=picked.weekday()), datetime.min.time())
    end = start + timedelta(days=7)
    c2.markdown(f"<div style='padding-top:32px;color:#6b7280'>Showing <b>{start:%a %d %b}</b> → "
                f"<b>{(end - timedelta(days=1)):%a %d %b %Y}</b></div>", unsafe_allow_html=True)
    week = df[(df["ts"] >= start) & (df["ts"] < end)]
    if week.empty:
        st.info("No tickets in this week. Pick another date above.")
        return

    total = len(week)
    solved = int((week["status"] == "Resolved").sum())
    m = st.columns(4)
    m[0].metric("Tickets this week", total, border=True)
    m[1].metric("✅ Solved by AI", f"{solved}  ({solved * 100 // total}%)", border=True)
    m[2].metric("🙋 Passed to a person", total - solved, border=True)
    m[3].metric("🔴 High priority", int((week["priority"] == "High").sum()), border=True)

    g1, g2 = st.columns(2)
    with g1.container(border=True):
        st.markdown("**Questions per team**")
        st.bar_chart(week["department"].value_counts(), color="#FF6B1A", height=260, horizontal=True)
    with g2.container(border=True):
        st.markdown("**Solved vs passed to a person**")
        st.bar_chart(pd.crosstab(week["department"], week["status"]), color=["#dc2626", "#16a34a"]
                     if set(week["status"]) == {"Escalated", "Resolved"} else None, height=260, horizontal=True)
    with st.container(border=True):
        st.markdown("**Tickets per day**")
        st.bar_chart(week.groupby(week["ts"].dt.strftime("%a %d"))["ticket_id"].count(), color="#14213D", height=220)

    esc = week[week["status"] == "Escalated"]
    st.markdown(f"**🙋 Waiting for a person ({len(esc)})**")
    if esc.empty:
        st.success("Nothing waiting — every ticket this week was solved by the AI team.")
    for _, r in esc.iterrows():
        st.markdown(f"<div class='handoff'><b>{r['ticket_id']}</b> · {r['department']} · {r['priority']} priority — "
                    f"{r['summary'] or r['complaint']}<br><small>{r['escalation_reason']}</small></div>",
                    unsafe_allow_html=True)

    lines = [f"WEEKLY HELP DESK REPORT  {start:%d %b %Y} - {(end - timedelta(days=1)):%d %b %Y}", "=" * 60,
             f"Total: {total} | Solved by AI: {solved} | Passed to a person: {total - solved} | "
             f"High priority: {(week['priority'] == 'High').sum()}", ""]
    for dep, grp in week.groupby("department"):
        lines.append(f"[{dep}] {len(grp)} tickets (High {(grp['priority'] == 'High').sum()}, "
                     f"Medium {(grp['priority'] == 'Medium').sum()}, Low {(grp['priority'] == 'Low').sum()})")
        lines += [f"  - {r['ticket_id']} {r['priority']:<6} {r['status']:<9} {r['summary']}" for _, r in grp.iterrows()]
        lines.append("")
    st.download_button("📝 Download weekly report (TXT)", "\n".join(lines),
                       f"weekly_report_{start:%Y_%m_%d}.txt", "text/plain")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
st.markdown(CSS, unsafe_allow_html=True)
password_gate()

with st.sidebar:
    st.markdown(f"## 🎧 {COMPANY_NAME}")
    st.caption("AI Help Desk for every team")
    if st.session_state.get("user_name") and st.session_state.get("user_ref"):
        with st.container(border=True):
            st.markdown(f"👤 **{st.session_state.user_name}**  \n🪪 Employee ID: `{st.session_state.user_ref}`")
            if st.button("✏️ Change details", width="stretch"):
                st.session_state.user_name = st.session_state.user_ref = ""
                st.session_state.chat = []
                st.rerun()
    if st.button("🧹 Start a new chat", width="stretch"):
        st.session_state.chat = []
        st.rerun()
    with st.expander("❓ How does this work?"):
        st.markdown("1. **You ask** in plain words.\n"
                    "2. A **main AI agent** picks the right team — Client Support, Finance, Marketing, "
                    "Sales, HR or IT — and sets the priority.\n"
                    "3. That **team's agent** reads only that team's company documents.\n"
                    "4. You get an answer. If it's urgent, sensitive or not covered, "
                    "a **person from that team** follows up.\n"
                    "5. Every question is **saved as a ticket**.")
    if SHOW_AGENT_STEPS:  # technical status only in demo mode
        st.divider()
        st.caption("🛠️ Demo mode: showing sources and agent steps")
        st.caption(f"{'🟢' if OPENAI_API_KEY else '🔴'} AI connected · `{OPENAI_MODEL}`")
        st.caption(f"{'🟢' if SERPAPI_API_KEY else '⚪'} Web search {'on' if SERPAPI_API_KEY else 'off'}")

page = st.segmented_control("Menu", ["💬 Ask", "🗂️ Ticket history", "📊 Weekly summary"],
                            default="💬 Ask", key="page", label_visibility="collapsed") or "💬 Ask"
{"💬 Ask": page_ask, "🗂️ Ticket history": page_history, "📊 Weekly summary": page_weekly}[page]()
