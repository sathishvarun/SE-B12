"""Tamil titles for sources and news items, so Tamil mode shows Tamil everywhere.

Titles are translated once with the LLM and kept in data/title_ta.json, so each title costs
tokens only the first time. Without an LLM (or if the call fails) the English title is kept.
"""
from __future__ import annotations

import json
import logging
import re
import threading

from app.config import settings

log = logging.getLogger("beldex.translate")
CACHE = settings.data_dir / "title_ta.json"
TAMIL = re.compile(r"[஀-௿]")
_lock = threading.Lock()
_cache: dict[str, str] | None = None


def _load() -> dict[str, str]:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
        except Exception:
            _cache = {}
    return _cache


def ta_titles(titles: list[str]) -> dict[str, str]:
    """Map each English title to Tamil. Titles already in Tamil map to themselves."""
    cache = _load()
    todo = sorted({t for t in titles if t and not TAMIL.search(t) and t not in cache})
    if todo:
        from app.rag.llm import get_llm
        llm = get_llm()
        if llm is not None:
            prompt = ("Translate each title to simple, natural Tamil for everyday readers. Keep product and coin "
                      "names (Beldex, BDX, BChat, BelNet, BNS, Bitcoin, Ethereum, USDT, Nexus) and version numbers in "
                      "English. Reply with a JSON array of strings only, same order and same count.\n\n"
                      + json.dumps(todo, ensure_ascii=False))
            try:
                out = llm.invoke(prompt).content
                arr = json.loads(out[out.find("["): out.rfind("]") + 1])
                if len(arr) == len(todo):
                    with _lock:
                        cache.update({en: str(ta).strip() for en, ta in zip(todo, arr) if str(ta).strip()})
                        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
            except Exception as e:  # keep English titles if anything goes wrong
                log.warning("title translation failed: %s", e)
    return {t: (t if TAMIL.search(t or "") else cache.get(t, t)) for t in titles}
