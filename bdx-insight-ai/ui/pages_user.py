"""Screens for everyone: sign in, ask the agent, news & sources."""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from ui import api_client as api
from ui.i18n import SUGGESTIONS, lang, t
from ui.theme import wordmark


# ------------------------------------------------------------------ sign in
def login_page() -> None:
    left, gap, right = st.columns([1.15, 0.1, 0.9])
    with left:
        st.markdown(wordmark(), unsafe_allow_html=True)
        st.markdown('<h1 style="font-size:2.6rem;line-height:1.1;margin:1.2rem 0 0.6rem">Ask Beldex anything.<br>'
                    'Get answers you can check.</h1>', unsafe_allow_html=True)
        st.markdown("Researched answers on Beldex — built only on **beldex.io**, its whitepaper and official "
                    "updates — with the source under every reply. Ask in English or Tamil.")
        st.markdown('<p class="muted" lang="ta">பெல்டெக்ஸ் பற்றி தமிழிலும் கேட்கலாம் — ஒவ்வொரு பதிலுக்கும் ஆதாரம் உண்டு.</p>',
                    unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="muted">Example</div>'
                    '<p><b>Q:</b> What changed in the Obscura hardfork?</p>'
                    '<p class="steps">✓ searched knowledge base · 4 passages · 3 sources</p>'
                    '<p>It went live on 7 Dec 2025 at block 4,939,540 and added Bulletproofs++, '
                    'which makes proofs smaller and faster to verify. <span class="n" style="color:#B03A0A">[1]</span></p></div>',
                    unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            role = st.segmented_control("Account type", ["User", "Admin"], default="User",
                                        key="login_role", label_visibility="collapsed") or "User"
            if role == "Admin":
                st.markdown("#### Admin console")
                st.caption("Admin accounts are created by the owner. Every sign-in is logged.")
                with st.form("admin_login"):
                    login = st.text_input("Admin email or user ID")
                    pw = st.text_input("Password", type="password")
                    if st.form_submit_button("Open admin console", type="primary", use_container_width=True):
                        _do_login(login, pw, "admin")
            else:
                tab_in, tab_up = st.tabs(["Sign in", "Create account"])
                with tab_in:
                    with st.form("user_login"):
                        login = st.text_input("User ID or email")
                        pw = st.text_input("Password", type="password")
                        if st.form_submit_button("Sign in", type="primary", use_container_width=True):
                            _do_login(login, pw, "user")
                with tab_up:
                    with st.form("signup"):
                        c1, c2 = st.columns(2)
                        name = c1.text_input("Full name")
                        username = c2.text_input("User ID", help="Letters, numbers, dot, dash or underscore")
                        email = st.text_input("Email")
                        pw = st.text_input("Password", type="password", help="At least 8 characters")
                        lg = st.radio("Reply language", ["English", "தமிழ்"], horizontal=True)
                        if st.form_submit_button("Create account", type="primary", use_container_width=True):
                            try:
                                res = api.post("/auth/register", {"name": name, "username": username, "email": email,
                                                                  "password": pw, "lang": "ta" if lg == "தமிழ்" else "en"})
                                _signed_in(res)
                            except api.ApiError as e:
                                st.error(e)
            st.caption("Independent tool, not affiliated with Beldex. Information only — not financial advice.")


def _do_login(login: str, pw: str, as_role: str) -> None:
    if not login or not pw:
        st.error("Enter your user ID and password.")
        return
    try:
        _signed_in(api.post("/auth/login", {"login": login, "password": pw, "as_role": as_role}))
    except api.ApiError as e:
        st.error(e)


def _signed_in(res: dict) -> None:
    st.session_state.token = res["token"]
    st.session_state.user = res["user"]
    st.session_state.lang = res["user"]["lang"]
    st.session_state.chat = None
    st.rerun()


# ------------------------------------------------------------------ ask
def _render_answer(item: dict, idx: int) -> None:
    st.markdown(item["answer"])
    if item.get("steps"):
        with st.expander(t("how")):
            st.markdown('<div class="steps">' + "<br>".join("✓ " + html.escape(s) for s in item["steps"]) + "</div>",
                        unsafe_allow_html=True)
            u = item.get("usage")
            if u:
                st.caption(f"{u['latency_ms']} ms · {u['prompt_tokens'] + u['completion_tokens']} tokens")
    if item.get("sources"):
        rows = []
        for s in item["sources"]:
            meta = " · ".join(x for x in [s.get("published"), s.get("kind")] if x)
            rows.append(f'<div class="src"><span class="n">[{s["n"]}]</span>'
                        f'<a href="{html.escape(s["url"])}" target="_blank">{html.escape(s["title"])}</a> '
                        f'<span class="meta">{html.escape(meta)}</span></div>')
        st.markdown(f"**{t('sources')}**" + "".join(rows), unsafe_allow_html=True)
    if item.get("id"):
        c1, c2, _ = st.columns([1, 1, 6])
        if c1.button(t("helpful"), key=f"up{idx}"):
            api.post(f"/chat/{item['id']}/feedback", {"value": 1})
            st.toast("Thanks!")
        if c2.button(t("not_helpful"), key=f"down{idx}"):
            api.post(f"/chat/{item['id']}/feedback", {"value": -1})
            st.toast("Thanks — the admin will see this.")


def _set_lang() -> None:
    choice = st.session_state.lang_picker
    if choice:
        st.session_state.lang = "ta" if choice == "தமிழ்" else "en"
        try:
            api.post("/me/lang", {"lang": st.session_state.lang})
        except api.ApiError:
            pass


def ask_page() -> None:
    head, picker = st.columns([3, 1])
    head.title(t("ask_title"))
    head.caption(t("ask_sub"))
    picker.segmented_control("Reply language", ["English", "தமிழ்"],
                             default="தமிழ்" if lang() == "ta" else "English",
                             key="lang_picker", on_change=_set_lang)

    if st.session_state.get("chat") is None:
        try:
            hist = api.get("/history")[:10][::-1]
        except api.ApiError:
            hist = []
        st.session_state.chat = [m for h in hist for m in (
            {"role": "user", "content": h["question"]},
            {"role": "assistant", "answer": h["answer"], "sources": h["sources"], "id": h["id"]})]

    chat = st.session_state.chat
    if not chat:
        st.markdown(f'<p class="muted">{t("try")}</p>', unsafe_allow_html=True)
        pick = st.pills("Suggestions", SUGGESTIONS[lang()], label_visibility="collapsed", key="sugg")
        if pick:
            st.session_state.pending = pick
            st.session_state.sugg = None

    for i, m in enumerate(chat):
        with st.chat_message(m["role"], avatar=":material/person:" if m["role"] == "user" else ":material/shield:"):
            if m["role"] == "user":
                st.markdown(m["content"])
            else:
                _render_answer(m, i)

    question = st.chat_input(t("placeholder")) or st.session_state.pop("pending", None)
    if question:
        chat.append({"role": "user", "content": question})
        with st.spinner(t("thinking")):
            try:
                res = api.post("/chat", {"question": question, "lang": lang()})
                chat.append({"role": "assistant", **res})
            except api.ApiError as e:
                chat.append({"role": "assistant", "answer": f"⚠ {e}", "sources": []})
        st.rerun()


# ------------------------------------------------------------------ news & sources
def news_page() -> None:
    st.title(t("news_title"))
    try:
        digest = api.get("/news")
        src = api.get("/kb/sources")
    except api.ApiError as e:
        st.error(e)
        return
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader(t("digest"))
        st.caption(f"Made by the news crew ({digest.get('engine')}) · {digest.get('generated_at', '')}")
        st.markdown(digest["tamil" if lang() == "ta" else "english"])
    with right:
        st.subheader("Latest items")
        for it in digest.get("items", []):
            st.markdown(f'<div class="card"><div class="muted">{html.escape(it["published"])}</div>'
                        f'<b>{html.escape(it["title"])}</b><br><span class="muted">{html.escape(it["summary"][:160])}…</span><br>'
                        f'<a href="{html.escape(it["url"])}" target="_blank">Open source</a></div>', unsafe_allow_html=True)
    st.subheader(t("all_sources"))
    df = pd.DataFrame(src["sources"])
    if not df.empty:
        st.dataframe(df[["title", "url", "kind", "published", "chunks"]], hide_index=True, use_container_width=True,
                     column_config={"url": st.column_config.LinkColumn("Link"),
                                    "chunks": st.column_config.NumberColumn("Passages")})
    st.caption(f"Search engine: {src['backend']} · {src['chunks']} passages indexed")
