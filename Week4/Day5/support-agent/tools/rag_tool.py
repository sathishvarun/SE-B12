"""
STEP 1 — RAG (Retrieval-Augmented Generation)
Loads YOUR content (knowledge/ folder) into a local vector database (ChromaDB)
and gives the agents a tool to search it.
"""
import os
from pathlib import Path
from typing import Type

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
DB_DIR = BASE_DIR / "data" / "vector_db"
COLLECTION = "support_kb"


class MissingKeyError(RuntimeError):
    pass


def kb_count() -> int:
    """Number of chunks currently stored in the knowledge base."""
    return _collection().count()


def _collection():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key.startswith("sk-your"):
        raise MissingKeyError(
            "\n❌ OPENAI_API_KEY not found.\n"
            f"   Create a file named .env in {BASE_DIR}\n"
            "   (copy .env.example) and put your real key in it:\n"
            "   OPENAI_API_KEY=sk-....\n")
    client = chromadb.PersistentClient(path=str(DB_DIR))
    embed = OpenAIEmbeddingFunction(
        api_key_env_var="OPENAI_API_KEY",
        model_name="text-embedding-3-small",
    )
    return client.get_or_create_collection(name=COLLECTION, embedding_function=embed)


def _read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def _chunk(text: str, size: int = 800, overlap: int = 150) -> list[str]:
    text = text.strip()
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return [c for c in chunks if c.strip()]


def ingest_folder(folder: Path = KNOWLEDGE_DIR) -> int:
    """Read every .txt / .md / .pdf in knowledge/ and store it in the vector DB."""
    col = _collection()
    total = 0
    for path in sorted(folder.glob("**/*")):
        if path.suffix.lower() not in {".txt", ".md", ".pdf"}:
            continue
        chunks = _chunk(_read_file(path))
        if not chunks:
            continue
        ids = [f"{path.name}-{i}" for i in range(len(chunks))]
        col.upsert(ids=ids, documents=chunks,
                   metadatas=[{"source": path.name}] * len(chunks))
        total += len(chunks)
        print(f"  ✔ {path.name}: {len(chunks)} chunks")
    return total


def add_text(doc_id: str, text: str, source: str) -> None:
    """Add a single new piece of knowledge (used when an admin answers a ticket)."""
    _collection().upsert(ids=[doc_id], documents=[text], metadatas=[{"source": source}])


def search_kb(query: str, k: int = 4) -> list[dict]:
    col = _collection()
    if col.count() == 0:
        return []
    res = col.query(query_texts=[query], n_results=min(k, col.count()))
    max_dist = float(os.getenv("RAG_MAX_DISTANCE", "0.9"))
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        if dist <= max_dist:  # ignore weak matches so the agent can say NOT FOUND
            hits.append({"text": doc, "source": meta.get("source"), "distance": round(dist, 3)})
    return hits


class KBSearchInput(BaseModel):
    query: str = Field(..., description="The customer's question, or keywords from it")


class KnowledgeBaseSearchTool(BaseTool):
    name: str = "knowledge_base_search"
    description: str = (
        "Searches the company's own support content (FAQs, policies, manuals). "
        "Always use this FIRST. Returns matching passages, or NO_MATCH."
    )
    args_schema: Type[BaseModel] = KBSearchInput

    def _run(self, query: str) -> str:
        hits = search_kb(query)
        if not hits:
            return "NO_MATCH"
        return "\n\n".join(f"[source: {h['source']} | score: {h['distance']}]\n{h['text']}" for h in hits)
