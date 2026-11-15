"""Admin console: overview, users & sessions, usage log, knowledge base."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ui import api_client as api
from ui.theme import ACCENT, INK, plotly_layout


def _bar() -> None:
    u = st.session_state.user
    st.markdown(f'<div class="admin-bar"><b>ADMIN</b> · signed in as {u["email"]}</div>', unsafe_allow_html=True)


def _fmt_dt(s) -> str:
    ts = pd.to_datetime(s, errors="coerce")
    return "—" if pd.isna(ts) else ts.strftime("%d %b, %H:%M")


def _compact(n: float) -> str:
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.1f}k" if n >= 1e4 else f"{int(n):,}"


# ------------------------------------------------------------------ overview
def overview_page() -> None:
    _bar()
    top, ctl = st.columns([3, 1])
    top.title("Overview")
    days = ctl.selectbox("Period", [7, 14, 30, 90], index=1, format_func=lambda d: f"Last {d} days")
    try:
        o = api.get("/admin/overview", params={"days": days})
    except api.ApiError as e:
        st.error(e)
        return
    k = o["kpis"]
    r1 = st.columns(5)
    r1[0].metric("Registered users", k["users"], f"+{k['new_users']} new")
    r1[1].metric("Online now", k["online"])
    r1[2].metric("Questions", k["questions"])
    r1[3].metric("Answered from KB", f"{k['answered_pct']}%")
    r1[4].metric("Helpful votes", f"{k['helpful_pct']}%")
    r2 = st.columns(5)
    r2[0].metric("Time in app", f"{k['total_hours']}h")
    r2[1].metric("Avg. session", f"{k['avg_session_min']:.0f}m")
    r2[2].metric("Tokens used", _compact(k["tokens"]))
    r2[3].metric("LLM cost", f"${k['cost_usd']:.2f}", help=f"${k['cost_usd']:.4f} exactly")
    r2[4].metric("Avg. answer", f"{k['avg_latency_ms'] / 1000:.1f}s")

    df = pd.DataFrame(o["series"])
    c1, c2 = st.columns(2)
    if df.empty:
        st.info("No activity in this period yet.")
    else:
        with c1:
            fig = px.bar(df, x="day", y="questions", title="Questions per day", color_discrete_sequence=[INK],
                         labels={"day": "", "questions": ""})
            st.plotly_chart(plotly_layout(fig), use_container_width=True)
        with c2:
            fig = px.line(df.rename(columns={"minutes": "Minutes used", "active_users": "Active users"}), x="day",
                          y=["Minutes used", "Active users"], markers=True, title="Minutes used & active users",
                          color_discrete_sequence=[INK, ACCENT], labels={"value": "", "variable": "", "day": ""})
            st.plotly_chart(plotly_layout(fig), use_container_width=True)
        c3, c4 = st.columns(2)
        with c3:
            fig = px.area(df, x="day", y="tokens", title="Tokens per day", color_discrete_sequence=[ACCENT],
                          labels={"day": "", "tokens": ""})
            st.plotly_chart(plotly_layout(fig), use_container_width=True)
        with c4:
            lang = pd.DataFrame({"language": list(o["languages"]), "questions": list(o["languages"].values())})
            fig = px.bar(lang, x="questions", y="language", orientation="h", title="Questions by language",
                         color="language", color_discrete_sequence=[INK, ACCENT],
                         labels={"language": "", "questions": ""})
            st.plotly_chart(plotly_layout(fig, 240), use_container_width=True)

    s1, s2 = st.columns([1, 1])
    with s1:
        st.subheader("Server")
        s = o["server"]
        st.progress(min(s["cpu_percent"] / 100, 1.0), text=f"CPU {s['cpu_percent']}%")
        st.progress(min(s["ram_percent"] / 100, 1.0), text=f"RAM {s['ram_used_gb']} / {s['ram_total_gb']} GB")
        st.progress(min(s["disk_percent"] / 100, 1.0), text=f"Disk {s['disk_percent']}%")
        st.caption(f"API process: {s['api_process_mb']} MB · Search: {o['knowledge']['backend']} · "
                   f"{o['knowledge']['sources']} sources / {o['knowledge']['chunks']} passages · "
                   f"LLM: {o['llm']['model'] if o['llm']['configured'] else 'not configured'}")
    with s2:
        st.subheader("Questions the knowledge base could not answer")
        if o["unanswered"]:
            st.dataframe(pd.DataFrame(o["unanswered"]), hide_index=True, use_container_width=True)
        else:
            st.caption("None — every question found an answer.")


# ------------------------------------------------------------------ users & sessions
def users_page() -> None:
    _bar()
    st.title("Users & sessions")
    try:
        users = pd.DataFrame(api.get("/admin/users"))
    except api.ApiError as e:
        st.error(e)
        return
    f1, f2 = st.columns([2, 1])
    q = f1.text_input("Search", placeholder="Name, user ID or email", label_visibility="collapsed")
    status = f2.multiselect("Status", ["Online", "Offline", "Suspended"], placeholder="All statuses",
                            label_visibility="collapsed")
    view = users
    if q:
        m = view[["name", "username", "email"]].apply(lambda c: c.str.contains(q, case=False)).any(axis=1)
        view = view[m]
    if status:
        view = view[view.status.isin(status)]
    view = view.reset_index(drop=True)
    table = view.assign(last_login=view.last_login.map(_fmt_dt))[
        ["name", "username", "role", "status", "last_login", "sessions", "minutes", "questions", "tokens",
         "cost_usd", "lang", "last_ip"]]
    ev = st.dataframe(table, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row",
                      column_config={"minutes": st.column_config.NumberColumn("Time used (min)"),
                                     "cost_usd": st.column_config.NumberColumn("Cost $", format="%.4f"),
                                     "last_ip": "Last IP", "lang": "Lang"})
    rows = ev.selection.rows
    if not rows:
        st.caption("Select a row to see that person's sessions, questions and activity.")
        return
    uid = int(view.iloc[rows[0]]["id"])
    d = api.get(f"/admin/users/{uid}")
    u = d["user"]
    st.divider()
    h1, h2, h3 = st.columns([3, 1, 1])
    h1.subheader(f"{u['name']}  ·  {u['username']}")
    h1.caption(f"{u['email']} · role: {u['role']} · reply language: {'Tamil' if u['lang'] == 'ta' else 'English'}")
    if h2.button("Activate" if not u["active"] else "Suspend", use_container_width=True):
        _patch(uid, {"active": not u["active"]})
    if h3.button("Make user" if u["role"] == "admin" else "Make admin", use_container_width=True):
        _patch(uid, {"role": "user" if u["role"] == "admin" else "admin"})

    t1, t2, t3 = st.tabs([f"Questions ({len(d['queries'])})", f"Sessions ({len(d['sessions'])})", "Activity"])
    with t1:
        qs = pd.DataFrame(d["queries"])
        if qs.empty:
            st.caption("No questions yet.")
        else:
            st.dataframe(qs[["at", "question", "lang", "found", "tokens", "cost_usd", "latency_ms", "cpu_ms", "mem_mb", "feedback"]]
                         .assign(at=qs.at.map(_fmt_dt)), hide_index=True, use_container_width=True)
            pick = st.selectbox("Read a full answer", qs.index, format_func=lambda i: qs.question[i][:90])
            row = qs.loc[pick]
            st.markdown(row.answer)
            for s in row.sources:
                st.markdown(f"- [{s['n']}] [{s['title']}]({s['url']})")
    with t2:
        ss = pd.DataFrame(d["sessions"])
        if not ss.empty:
            st.dataframe(ss.assign(started_at=ss.started_at.map(_fmt_dt), last_seen=ss.last_seen.map(_fmt_dt))
                         [["started_at", "last_seen", "minutes", "online", "ended", "ip", "device"]],
                         hide_index=True, use_container_width=True)
    with t3:
        ac = pd.DataFrame(d["activity"])
        if not ac.empty:
            st.dataframe(ac.assign(at=ac.at.map(_fmt_dt)), hide_index=True, use_container_width=True)


def _patch(uid: int, body: dict) -> None:
    try:
        api.patch(f"/admin/users/{uid}", body)
        st.toast("Saved")
        st.rerun()
    except api.ApiError as e:
        st.error(e)


# ------------------------------------------------------------------ usage log
def usage_page() -> None:
    _bar()
    st.title("Usage log")
    tab_q, tab_a = st.tabs(["Every question", "Sign-ins & actions"])
    with tab_q:
        df = pd.DataFrame(api.get("/admin/queries", params={"limit": 1000}))
        if df.empty:
            st.caption("No questions yet.")
        else:
            c1, c2, c3 = st.columns(3)
            who = c1.multiselect("User", sorted(df.user.unique()), placeholder="Everyone")
            lg = c2.multiselect("Language", ["en", "ta"], placeholder="Both")
            only = c3.selectbox("Show", ["All", "Answered", "Not in knowledge base"])
            if who:
                df = df[df.user.isin(who)]
            if lg:
                df = df[df.lang.isin(lg)]
            if only != "All":
                df = df[df.found == (only == "Answered")]
            m = st.columns(4)
            m[0].metric("Questions", len(df))
            m[1].metric("Tokens", f"{int(df.tokens.sum()):,}")
            m[2].metric("CPU time", f"{df.cpu_ms.sum() / 1000:.1f} s")
            m[3].metric("Cost", f"${df.cost_usd.sum():.4f}")
            st.dataframe(df.assign(at=df.at.map(_fmt_dt)), hide_index=True, use_container_width=True,
                         column_config={"cost_usd": st.column_config.NumberColumn("Cost $", format="%.5f")})
            st.download_button("Download CSV", df.to_csv(index=False), "bdx_insight_questions.csv", "text/csv")
    with tab_a:
        ac = pd.DataFrame(api.get("/admin/activity", params={"limit": 1000}))
        if not ac.empty:
            acts = st.multiselect("Action", sorted(ac.action.unique()), placeholder="All actions")
            if acts:
                ac = ac[ac.action.isin(acts)]
            st.dataframe(ac.assign(at=ac.at.map(_fmt_dt)), hide_index=True, use_container_width=True)
            st.download_button("Download CSV", ac.to_csv(index=False), "bdx_insight_activity.csv", "text/csv")


# ------------------------------------------------------------------ knowledge base
def knowledge_page() -> None:
    _bar()
    st.title("Knowledge base")
    st.caption("The agent answers only from these sources. Refreshing re-reads beldex.io with Playwright, "
               "re-indexes everything and asks the news crew (CrewAI) for a new digest.")
    b1, b2, _ = st.columns([1, 1, 3])
    if b1.button("Refresh knowledge", type="primary", use_container_width=True):
        try:
            api.post("/admin/kb/refresh")
            st.toast("Refresh started — it takes a few minutes.")
        except api.ApiError as e:
            st.error(e)
    if b2.button("Rebuild news digest", use_container_width=True):
        with st.spinner("The news crew is writing…"):
            res = api.post("/admin/news/run", timeout=600)
        st.toast(f"Digest ready ({res['engine']})")
    src = api.get("/kb/sources")
    m = st.columns(3)
    m[0].metric("Sources", len(src["sources"]))
    m[1].metric("Passages", src["chunks"])
    m[2].metric("Search engine", src["backend"].upper())
    df = pd.DataFrame(src["sources"])
    st.dataframe(df, hide_index=True, use_container_width=True, column_config={"url": st.column_config.LinkColumn("Link")})
    st.subheader("Refresh history")
    runs = pd.DataFrame(api.get("/admin/kb/runs"))
    if runs.empty:
        st.caption("Not refreshed yet — the app is using the built-in starter knowledge.")
    else:
        st.dataframe(runs.drop(columns=["message"]).assign(started_at=runs.started_at.map(_fmt_dt)),
                     hide_index=True, use_container_width=True)
        with st.expander("Log of the latest refresh"):
            st.code(runs.iloc[0].message or "(running…)")
