
import os

from pathlib import Path

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parent.parent

QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://localhost:6333",
)

COLLECTION_NAME = "music_catalog"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


print("Loading semantic search model...")
model = SentenceTransformer(MODEL_NAME)
print("Semantic search model loaded successfully.")


def semantic_search(query: str, limit: int = 5):
    """Search the Qdrant server using semantic similarity."""

    if not query or not query.strip():
        return []

    query_vector = model.encode(
        query.strip(),
        normalize_embeddings=True,
    ).tolist()

    client = QdrantClient(url=QDRANT_URL)

    try:
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=max(1, min(limit, 20)),
            with_payload=True,
        )

        results = []

        for point in response.points:
            item = dict(point.payload or {})
            item["score"] = round(float(point.score), 4)
            results.append(item)

        return results

    finally:
        client.close()
