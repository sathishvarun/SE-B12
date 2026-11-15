"""Small HTTP client the Streamlit pages use to talk to the FastAPI backend."""
from __future__ import annotations

import httpx
import streamlit as st

from app.config import settings


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _headers() -> dict:
    h = {}
    try:  # pass the visitor's real IP / browser through to the API for the admin log
        hd = st.context.headers
        h["X-Client-IP"] = (hd.get("X-Forwarded-For") or hd.get("X-Real-Ip") or "").split(",")[0].strip()
        h["X-Client-UA"] = hd.get("User-Agent", "")[:300]
    except Exception:
        pass
    if st.session_state.get("token"):
        h["Authorization"] = f"Bearer {st.session_state.token}"
    return h


def call(method: str, path: str, json: dict | None = None, params: dict | None = None, timeout: float = 120):
    try:
        r = httpx.request(method, settings.api_url + path, json=json, params=params,
                          headers=_headers(), timeout=timeout)
    except httpx.HTTPError:
        raise ApiError(0, "The server is not reachable right now. Please try again in a moment.")
    if r.status_code == 401 and st.session_state.get("token"):
        for k in ("token", "user"):
            st.session_state.pop(k, None)
        raise ApiError(401, "Your session ended. Please sign in again.")
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
            msg = detail if isinstance(detail, str) else "Please check the form and try again."
        except ValueError:
            msg = r.text[:200]
        raise ApiError(r.status_code, msg)
    return r.json()


def get(path, **kw):
    return call("GET", path, **kw)


def post(path, json=None, **kw):
    return call("POST", path, json=json or {}, **kw)


def patch(path, json=None, **kw):
    return call("PATCH", path, json=json or {}, **kw)
