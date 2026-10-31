"""Knowledge base search (the "R" in RAG).

search() uses vector search (ChromaDB + embeddings, by meaning) when it is available,
and falls back to simple keyword matching otherwise, so the app always works.
"""
import logging
import re
from pathlib import Path

from config import KB_DIR, SEARCH_MODE
from tools.vector_store import vector_available, vector_disable, vector_search

STOPWORDS = set("""
a an the and or but if to of in on at for with from by is are was were be been am i me my
we our you your it its this that these those can could would should will shall do does did
have has had not no yes please hi hello how what when where why who which there their them
they he she his her get got want need about any some just so very also into than then too
""".split())


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words if w not in STOPWORDS and len(w) > 2}


def _passages(file: Path):
    """Split a markdown file into sections (one per heading)."""
    text = file.read_text(encoding="utf-8")
    title = file.stem.replace("_", " ")
    for block in re.split(r"\n(?=#{1,3} )", text):
        block = block.strip()
        if block:
            yield title, block


def keyword_search(query: str, department: str | None = None, top_k: int = 3) -> list[dict]:
    """Keyword matching: passages sharing the most words with the query: [{source, text, score}]."""
    q_terms = _terms(query)
    if not q_terms:
        return []
    folder = KB_DIR / department if department else KB_DIR
    min_hits = 1 if len(q_terms) <= 2 else 2  # avoid weak, one-word matches

    results = []
    for file in sorted(folder.rglob("*.md")):
        for title, block in _passages(file):
            p_terms = _terms(block) | _terms(title)
            hits = q_terms & p_terms
            if len(hits) >= min_hits:
                results.append({
                    "source": str(file.relative_to(KB_DIR)),
                    "text": block,
                    "score": len(hits),
                })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def format_results(results: list[dict]) -> str:
    if not results:
        return "NO_MATCH: nothing relevant was found in the knowledge base."
    parts = [f"[source: {r['source']}]\n{r['text']}" for r in results]
    return "\n\n---\n\n".join(parts)


def search_mode() -> str:
    """What the search is using right now: 'vector' or 'keyword'."""
    return "vector" if SEARCH_MODE == "vector" and vector_available() else "keyword"


def search(query: str, department: str | None = None, top_k: int = 3) -> list[dict]:
    """Best matching passages for the query: vector search first, keyword search as the fallback."""
    if search_mode() == "vector":
        try:
            results = vector_search(query, department, top_k)
            if results:
                return results
        except Exception as exc:                 # e.g. no internet / embeddings API error
            logging.warning("Vector search unavailable, using keyword search: %s", exc)
            vector_disable(str(exc))
    return keyword_search(query, department, top_k)

