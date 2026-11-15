"""Streamlit front end.  Run:  streamlit run ui/app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from ui import api_client as api  # noqa: E402
from ui import pages_admin, pages_user, theme  # noqa: E402

st.set_page_config(page_title="bdx.insight — Beldex assistant", page_icon=":material/shield:", layout="wide")
theme.apply()


def sign_out() -> None:
    try:
        api.post("/auth/logout")
    except api.ApiError:
        pass
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def track(page_name: str) -> None:
    """Log each page a person opens (once per visit) for the admin activity view."""
    seen = st.session_state.setdefault("_seen", set())
    if page_name not in seen:
        seen.add(page_name)
        try:
            api.post("/activity", {"action": "view_page", "detail": page_name})
        except api.ApiError:
            pass


user = st.session_state.get("user")
if not user:
    st.navigation([st.Page(pages_user.login_page, title="Sign in", icon=":material/login:")],
                  position="hidden").run()
    st.stop()

pages = {"Beldex": [
    st.Page(pages_user.ask_page, title="Ask", icon=":material/forum:", url_path="ask", default=True),
    st.Page(pages_user.news_page, title="News & sources", icon=":material/newspaper:", url_path="news"),
]}
if user["role"] == "admin":
    pages["Admin"] = [
        st.Page(pages_admin.overview_page, title="Overview", icon=":material/monitoring:", url_path="admin"),
        st.Page(pages_admin.users_page, title="Users & sessions", icon=":material/group:", url_path="users"),
        st.Page(pages_admin.usage_page, title="Usage log", icon=":material/receipt_long:", url_path="usage"),
        st.Page(pages_admin.knowledge_page, title="Knowledge base", icon=":material/database:", url_path="knowledge"),
    ]

st.logo(str(Path(__file__).parent / "assets" / "logo.svg"), size="large")

page = st.navigation(pages)
with st.sidebar:
    st.caption(f"Signed in as **{user['name']}** · {user['role']}")
    st.button("Sign out", on_click=sign_out, use_container_width=True)
    st.caption("Answers come only from beldex.io and the indexed sources. Not financial advice.")
track(page.title)
page.run()
