"""Look and feel: warm paper background, ink text, one orange accent, IBM Plex fonts."""
import streamlit as st

INK, MUTED, LINE, ACCENT, PAPER = "#1B1B18", "#5F5E57", "#E4E2DA", "#C2410C", "#F7F6F2"
GOOD, BAD = "#157F3D", "#B42318"
SERIES = [INK, ACCENT, "#D9A27A", "#8A877D"]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Noto+Sans+Tamil:wght@400;500;600&display=swap');
html, body, [class*="css"], .stMarkdown, .stTextInput input, .stTextArea textarea, button, .stChatInput textarea {{
  font-family: 'IBM Plex Sans', 'Noto Sans Tamil', system-ui, sans-serif !important;
}}
.stApp {{ background: {PAPER}; color: {INK}; }}
#MainMenu, footer, [data-testid="stStatusWidget"] {{ visibility: hidden; }}
.block-container {{ padding-top: 2.2rem; max-width: 1240px; }}
h1, h2, h3 {{ letter-spacing: -0.015em; color: {INK}; }}
h1 {{ font-weight: 600 !important; }}
[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid {LINE}; }}
[data-testid="stMetric"] {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 8px; padding: 14px 16px; }}
[data-testid="stMetricValue"] {{ font-family: 'IBM Plex Mono', monospace !important; font-weight: 500; }}
[data-testid="stMetricLabel"] p {{ color: {MUTED}; }}
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{ border-radius: 6px; font-weight: 500; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{ background: {INK}; border-color: {INK}; }}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{ background: {ACCENT}; border-color: {ACCENT}; }}
[data-testid="stChatMessage"] {{ background: transparent; }}
.wordmark {{ font-size: 1.35rem; color: {INK}; }} .wordmark b {{ letter-spacing: -0.02em; }} .wordmark i {{ color: {ACCENT}; font-style: normal; font-weight: 700; }}
.muted {{ color: {MUTED}; font-size: 0.9rem; }}
.steps {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; color: {MUTED}; line-height: 1.7; }}
.src {{ border-top: 1px solid {LINE}; padding: 8px 0; font-size: 0.9rem; }}
.src .n {{ font-family: 'IBM Plex Mono', monospace; color: #B03A0A; margin-right: 8px; }}
.src .meta {{ color: {MUTED}; font-size: 0.8rem; }}
.card {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 8px; padding: 16px 18px; margin-bottom: 10px; }}
.pill {{ display: inline-block; font-size: 0.75rem; padding: 2px 8px; border-radius: 3px; background: #F0EEE8; color: {MUTED}; }}
.pill.ok {{ background: #E3F1E7; color: #11652F; }} .pill.warn {{ background: #F6EED9; color: #7A5A12; }} .pill.bad {{ background: #F8E1DD; color: #9A1D12; }}
.admin-bar {{ background: {INK}; color: #F7F6F2; padding: 8px 14px; border-radius: 6px; font-size: 0.85rem; margin-bottom: 1rem; }}
.admin-bar b {{ color: #F08A4B; }}
</style>
"""


def apply() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def wordmark(suffix: str = "") -> str:
    return f'<span class="wordmark"><b>bdx</b><i>.</i>insight{suffix}</span>'


def plotly_layout(fig, height: int = 280):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#FFFFFF",
                      plot_bgcolor="#FFFFFF", font=dict(family="IBM Plex Sans, Helvetica, Arial, sans-serif", color=INK, size=12),
                      legend=dict(orientation="h", y=-0.15, title=None), colorway=SERIES)
    fig.update_xaxes(showgrid=False, linecolor=LINE)
    fig.update_yaxes(gridcolor="#EFEDE6", zeroline=False)
    return fig
