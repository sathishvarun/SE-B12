"""The knowledge base: the ONLY place answers come from.

Sources = shipped seed facts (app/rag/seed_knowledge.json) + pages the Playwright crawler saved
from beldex.io (data/knowledge/*.jsonl). Documents are split with LangChain and indexed either in
FAISS (vector search, needs an embeddings key) or BM25 (keyword search, works offline).
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.rag.llm import get_embeddings

SEED = Path(__file__).with_name("seed_knowledge.json")
KDIR = settings.data_dir / "knowledge"
IDX = settings.data_dir / "index"


@dataclass
class Hit:
    doc: Document
    score: float


def load_documents() -> list[Document]:
    docs: list[Document] = []
    for item in json.loads(SEED.read_text(encoding="utf-8")):
        docs.append(Document(page_content=item["text"], metadata={
            "title": item["title"], "url": item["url"], "published": item.get("published", ""),
            "kind": item.get("kind", "reference"), "origin": "seed"}))
    for f in sorted(KDIR.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if len(row.get("text", "")) < 80:
                continue
            docs.append(Document(page_content=row["text"], metadata={
                "title": row.get("title") or row["url"], "url": row["url"],
                "published": row.get("published", ""), "kind": row.get("kind", "official"),
                "origin": "crawl", "fetched_at": row.get("fetched_at", "")}))
    return docs


def _fingerprint() -> str:
    h = hashlib.sha1(SEED.read_bytes())
    for f in sorted(KDIR.glob("*.jsonl")):
        h.update(f.read_bytes())
    h.update(settings.search_mode.encode())
    return h.hexdigest()[:16]


STOP = set("""a an the is are was were be been of in on at to for from by with and or not no do does did
how what when where who why which can could should would will i me my we our you your it its this that these
those there their about tell explain please much many any some get give know""".split())


def _stem(t: str) -> str:
    for suf in ("ing", "ers", "er", "ed", "es", "s"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            return t[: -len(suf)]
    return t


def _tokens(text: str) -> list[str]:
    return [_stem(t) for t in re.findall(r"[\w஀-௿]+", text.lower()) if t not in STOP]


class KnowledgeBase:
    def __init__(self):
        self._lock = threading.Lock()
        self._fp = ""
        self.chunks: list[Document] = []
        self.backend = "none"
        self._faiss = None
        self._bm25 = None

    def ensure(self) -> None:
        fp = _fingerprint()
        if fp == self._fp:
            return
        with self._lock:
            if fp == self._fp:
                return
            self._build(fp)

    def _build(self, fp: str) -> None:
        splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
        self.chunks = splitter.split_documents(load_documents())
        emb = get_embeddings()
        self._faiss = self._bm25 = None
        if emb is not None:
            from langchain_community.vectorstores import FAISS
            path = IDX / fp
            try:
                if path.exists():
                    self._faiss = FAISS.load_local(str(path), emb, allow_dangerous_deserialization=True)
                else:
                    self._faiss = FAISS.from_documents(self.chunks, emb)
                    path.mkdir(parents=True, exist_ok=True)
                    self._faiss.save_local(str(path))
                self.backend = "faiss"
            except Exception as exc:  # embeddings API down -> keep working with keywords
                print(f"[knowledge] FAISS unavailable ({exc}); using BM25")
        if self._faiss is None:
            from rank_bm25 import BM25Okapi
            self._bm25 = BM25Okapi([_tokens(c.page_content + " " + c.metadata["title"]) for c in self.chunks])
            self.backend = "bm25"
        self._fp = fp

    def search(self, query: str, k: int = 5) -> list[Hit]:
        self.ensure()
        if self.backend == "faiss":
            pairs = self._faiss.similarity_search_with_relevance_scores(query, k=k)
            return [Hit(d, float(s)) for d, s in pairs if s >= 0.25]
        words = _tokens(query)
        if not words:
            return []
        scores = self._bm25.get_scores(words)
        best = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [Hit(self.chunks[i], float(scores[i])) for i in best if scores[i] > 0.8]

    def latest(self, n: int = 8) -> list[Document]:
        """Newest dated items, for the News page and the news crew."""
        docs = [d for d in load_documents() if d.metadata.get("published")]
        docs.sort(key=lambda d: d.metadata["published"], reverse=True)
        return docs[:n]

    def sources(self) -> list[dict]:
        self.ensure()
        seen: dict[str, dict] = {}
        for c in self.chunks:
            m = c.metadata
            s = seen.setdefault(m["url"], {"title": m["title"], "url": m["url"], "kind": m["kind"],
                                           "origin": m["origin"], "published": m.get("published", ""),
                                           "fetched_at": m.get("fetched_at", ""), "chunks": 0})
            s["chunks"] += 1
        return list(seen.values())


kb = KnowledgeBase()
