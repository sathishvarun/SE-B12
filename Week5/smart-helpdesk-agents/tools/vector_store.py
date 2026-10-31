"""Vector search over the knowledge base with ChromaDB + OpenAI embeddings (search by MEANING).

How it works:
  1. Every section of every document in knowledge_base/ becomes one "chunk".
  2. Each chunk is turned into an embedding (a list of numbers that captures its meaning)
     with OpenAI's text-embedding-3-small model and stored in a local ChromaDB folder (vector_store/).
  3. A question is embedded the same way; ChromaDB returns the chunks whose meaning is closest
     (cosine distance), filtered to the asking team's own documents.
  The index rebuilds itself automatically whenever a document is added or changed.
"""
import hashlib
import threading

from config import (EMBEDDING_MODEL, KB_DIR, OPENAI_API_KEY, OPENAI_BASE_URL,
                    VECTOR_DIR, VECTOR_MAX_DISTANCE)

COLLECTION = "sk_soft_knowledge_base"
_lock = threading.Lock()
_state = {"collection": None, "fingerprint": None, "disabled": ""}
embedding_function_override = None   # tests can plug in a fake embedding function here


def _fingerprint() -> str:
    """Changes whenever any knowledge base file is added, removed or edited."""
    h = hashlib.sha256()
    for f in sorted(KB_DIR.rglob("*.md")):
        h.update(str(f.relative_to(KB_DIR)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def _embedding_function():
    if embedding_function_override is not None:
        return embedding_function_override
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
    return OpenAIEmbeddingFunction(api_key=OPENAI_API_KEY, model_name=EMBEDDING_MODEL)


def _chunks():
    from tools.kb_search import _passages   # same section splitting as the keyword search
    ids, docs, metas = [], [], []
    for f in sorted(KB_DIR.rglob("*.md")):
        source = str(f.relative_to(KB_DIR))
        department = source.split("/")[0]
        for i, (title, block) in enumerate(_passages(f)):
            if len(block.splitlines()) < 2:      # a heading on its own carries no answer
                continue
            ids.append(f"{source}#{i}")
            docs.append(block)
            metas.append({"source": source, "department": department})
    return ids, docs, metas


def _collection():
    """Open the ChromaDB collection, (re)building it when the documents changed."""
    import chromadb
    from chromadb.config import Settings

    fp = _fingerprint()
    if _state["collection"] is not None and _state["fingerprint"] == fp:
        return _state["collection"]
    client = chromadb.PersistentClient(path=str(VECTOR_DIR), settings=Settings(anonymized_telemetry=False))
    ef = _embedding_function()
    col = None
    try:
        col = client.get_collection(COLLECTION, embedding_function=ef)
    except Exception:
        pass
    if col is None or (col.metadata or {}).get("fingerprint") != fp:
        if col is not None:
            client.delete_collection(COLLECTION)
        col = client.create_collection(COLLECTION, embedding_function=ef,
                                       metadata={"fingerprint": fp, "hnsw:space": "cosine"})
        ids, docs, metas = _chunks()
        if ids:
            col.add(ids=ids, documents=docs, metadatas=metas)
    _state.update(collection=col, fingerprint=fp)
    return col


def vector_available() -> bool:
    if _state["disabled"]:
        return False
    if embedding_function_override is None and (not OPENAI_API_KEY or OPENAI_BASE_URL):
        return False        # no key, or a non-OpenAI provider without an embeddings endpoint
    try:
        import chromadb  # noqa: F401
        return True
    except Exception as exc:           # not installed, or a broken install: use keyword search
        _state["disabled"] = f"chromadb unavailable: {exc}"
        return False


def vector_search(query: str, department: str | None = None, top_k: int = 3) -> list[dict]:
    """Closest chunks by meaning: [{source, text, score}] with score = 1 - cosine distance."""
    with _lock:
        col = _collection()
        n = col.count()
        if n == 0:
            return []
        res = col.query(query_texts=[query], n_results=min(top_k, n),
                        where={"department": department} if department else None)
    out = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        if dist <= VECTOR_MAX_DISTANCE:
            out.append({"source": meta["source"], "text": doc, "score": round(1 - dist, 3)})
    return out


def vector_disable(reason: str):
    _state["disabled"] = reason
