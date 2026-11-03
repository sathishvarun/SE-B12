
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

PROJECT_DIR = Path(__file__).resolve().parent

CHUNKS_FILE = PROJECT_DIR / "document_chunks.jsonl"
INDEX_DIR = PROJECT_DIR / "vector_store"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def main():
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            "document_chunks.jsonl not found. Run ingest_documents.py first."
        )

    records = []

    with CHUNKS_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    if not records:
        raise ValueError("No document chunks available for indexing.")

    texts = [record["text"] for record in records]

    print(f"Loading embedding model: {EMBEDDING_MODEL}")

    model = SentenceTransformer(EMBEDDING_MODEL)

    print(f"Creating embeddings for {len(texts)} chunks...")

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    embeddings = np.asarray(embeddings, dtype=np.float32)

    # Inner product on normalized embeddings is cosine similarity.
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    faiss.write_index(
        index,
        str(INDEX_DIR / "marketing.index")
    )

    with (INDEX_DIR / "metadata.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(records, file, indent=2, ensure_ascii=False)

    print("\nVector database created successfully.")
    print(f"Documents indexed: {len(records)}")
    print(f"Embedding dimensions: {embeddings.shape[1]}")
    print(f"Saved to: {INDEX_DIR}")


if __name__ == "__main__":
    main()
