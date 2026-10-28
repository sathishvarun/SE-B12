"""
Weather News Agent — web GUI (Streamlit)

Same agent and same tool as weather_news.py, wrapped in a browser interface.
Run:  streamlit run app.py   → opens http://localhost:8501
"""

import asyncio
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import (
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient

from weather_news import SYSTEM_MESSAGE, search_weather_news  # reuse the same tool

load_dotenv()

st.set_page_config(page_title="Weather News Agent", page_icon="🌦️", layout="centered")

# ---------- styling ----------
st.markdown(
    """
    <style>
      .block-container {padding-top: 2.2rem; max-width: 760px;}
      .hero {padding: 1.4rem 1.6rem; border-radius: 18px;
             background: linear-gradient(135deg,#0f4c81 0%,#1e88a8 55%,#43b5a0 100%);
             color: #fff; margin-bottom: 1.4rem;}
      .hero h1 {font-size: 1.75rem; margin: 0 0 .25rem 0; color:#fff;}
      .hero p {margin: 0; opacity: .9; font-size: .95rem;}
      .card {border: 1px solid rgba(128,128,128,.25); border-radius: 16px;
             padding: 1.1rem 1.3rem; margin: .4rem 0 1rem 0;
             background: rgba(30,136,168,.06);}
      .card .city {font-size: 1.25rem; font-weight: 700; margin-bottom: .1rem;}
      .card .meta {font-size: .8rem; opacity: .65; margin-bottom: .7rem;}
      .card .line {padding: .45rem 0; border-top: 1px dashed rgba(128,128,128,.25);
                   font-size: 1.02rem; line-height: 1.45;}
      .card .line:first-of-type {border-top: none;}
      .toolcall {font-family: ui-monospace, Menlo, monospace; font-size: .85rem;
                 background: rgba(128,128,128,.12); padding: .35rem .6rem;
                 border-radius: 8px; display: inline-block;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>🌦️ Weather News Agent</h1>
      <p>AutoGen agent + DuckDuckGo news search → today's weather in 3 short lines.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- sidebar settings ----------
with st.sidebar:
    st.header("⚙️ Settings")
    env_key = os.getenv("OPENAI_API_KEY", "")
    if env_key:
        st.success("OpenAI key loaded from .env")
        api_key = env_key
    else:
        api_key = st.text_input("OpenAI API key", type="password",
                                help="Stored only for this browser session.")
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"], index=0)
    show_trace = st.toggle("Show agent trace (tool call + raw results)", value=True)
    st.divider()
    if st.button("Clear history", use_container_width=True):
        st.session_state.history = []
    st.caption("Search: ddgs (free, no key) · Agent: AutoGen AssistantAgent")

if "history" not in st.session_state:
    st.session_state.history = []


# ---------- agent runner ----------
async def run_agent(city: str, key: str, model_name: str) -> dict:
    client = OpenAIChatCompletionClient(model=model_name, api_key=key)
    agent = AssistantAgent(
        name="weather_news",
        model_client=client,
        tools=[search_weather_news],
        system_message=SYSTEM_MESSAGE,
        reflect_on_tool_use=True,
    )
    out = {"city": city, "tool_calls": [], "raw": "", "answer": ""}
    try:
        async for event in agent.run_stream(task=f"Give me today's weather news for {city}."):
            if isinstance(event, ToolCallRequestEvent):
                for c in event.content:
                    out["tool_calls"].append(f"{c.name}({c.arguments})")
            elif isinstance(event, ToolCallExecutionEvent):
                out["raw"] = "\n\n".join(r.content for r in event.content)
            elif isinstance(event, TextMessage) and event.source == "weather_news":
                out["answer"] = event.content
    finally:
        await client.close()
    return out


def render_card(item: dict, trace: bool) -> None:
    lines = [l.strip() for l in item["answer"].splitlines() if l.strip()]
    body = "".join(f'<div class="line">{l}</div>' for l in lines)
    st.markdown(
        f'<div class="card"><div class="city">📍 {item["city"]}</div>'
        f'<div class="meta">{item["time"]} · {item["model"]}</div>{body}</div>',
        unsafe_allow_html=True,
    )
    if trace:
        with st.expander("🔧 Agent trace"):
            st.markdown("**Tool call**")
            for tc in item["tool_calls"] or ["(no tool call)"]:
                st.markdown(f'<span class="toolcall">{tc}</span>', unsafe_allow_html=True)
            st.markdown("**Raw search results**")
            st.text(item["raw"] or "(empty)")


# ---------- input ----------
quick = ["Chennai", "Coimbatore", "Mumbai", "Delhi", "Bengaluru"]
cols = st.columns(len(quick))
picked = None
for col, name in zip(cols, quick):
    if col.button(name, use_container_width=True):
        picked = name

with st.form("city_form", clear_on_submit=True):
    c1, c2 = st.columns([4, 1])
    typed = c1.text_input("City", placeholder="Type any city…", label_visibility="collapsed")
    submitted = c2.form_submit_button("Get news", use_container_width=True, type="primary")

city = picked or (typed.strip() if submitted else "")

if city:
    if not api_key:
        st.error("Add your OpenAI API key in the sidebar (or in .env) first.")
    else:
        with st.spinner(f"Searching today's weather news for {city}…"):
            try:
                result = asyncio.run(run_agent(city, api_key, model))
                result["time"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
                result["model"] = model
                st.session_state.history.insert(0, result)
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# ---------- results ----------
if st.session_state.history:
    for item in st.session_state.history:
        render_card(item, show_trace)
else:
    st.info("Pick a city above or type one to get today's weather news.")
