
from pathlib import Path
import json
import uuid

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "music_catalog.json"
VECTOR_DIR = PROJECT_ROOT / "vector_db" / "qdrant"

COLLECTION_NAME = "music_catalog"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def record_text(item):
    fields = [
        item.get("title", ""),
        item.get("artist", ""),
        item.get("album", ""),
        item.get("genre", ""),
        item.get("description", ""),
    ]
    return " ".join(
        str(value) for value in fields if value
    ).strip()


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Catalogue not found: {DATA_FILE}"
        )

    with DATA_FILE.open("r", encoding="utf-8") as file:
        catalog = json.load(file)

    if not isinstance(catalog, list) or not catalog:
        raise ValueError(
            "The catalogue must be a non-empty JSON list."
        )

    for item in catalog:
        if not item.get("id"):
            raise ValueError(
                "Every catalogue record needs an id."
            )

    texts = [record_text(item) for item in catalog]

    if any(not text for text in texts):
        raise ValueError(
            "Every record needs searchable text."
        )

    print("Loading embedding model...", flush=True)
    model = SentenceTransformer(MODEL_NAME)

    print("Generating embeddings...", flush=True)
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    client = QdrantClient(path=str(VECTOR_DIR))

    try:
        if client.collection_exists(COLLECTION_NAME):
            client.delete_collection(COLLECTION_NAME)

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=model.get_sentence_embedding_dimension(),
                distance=models.Distance.COSINE,
            ),
        )

        points = []

        for item, vector in zip(catalog, vectors):
            point_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL, item["id"]
                )
            )

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload=item,
                )
            )

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )

        print(
            f"Indexed {len(points)} records successfully.",
            flush=True,
        )
        print(f"Collection: {COLLECTION_NAME}")
        print(
            f"Vector dimensions: "
            f"{model.get_sentence_embedding_dimension()}"
        )
        print(f"Storage location: {VECTOR_DIR}")

    finally:
        client.close()


if __name__ == "__main__":
    main()
