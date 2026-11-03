
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

PROJECT_DIR = Path(__file__).resolve().parent
INDEX_FILE = PROJECT_DIR / "vector_store" / "marketing.index"
METADATA_FILE = PROJECT_DIR / "vector_store" / "metadata.json"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class MarketingRAG:
    def __init__(self):
        if not INDEX_FILE.exists() or not METADATA_FILE.exists():
            raise FileNotFoundError(
                "Vector database not found. Run build_vector_db.py first."
            )

        print("Loading marketing knowledge base...")

        self.encoder = SentenceTransformer(EMBEDDING_MODEL)
        self.index = faiss.read_index(str(INDEX_FILE))

        with METADATA_FILE.open("r", encoding="utf-8") as file:
            self.metadata = json.load(file)

        print(f"Loaded {len(self.metadata)} knowledge chunks.")

    def search(self, question, top_k=3):
        if not question or not question.strip():
            return []

        query_embedding = self.encoder.encode(
            [question],
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        query_embedding = np.asarray(
            query_embedding,
            dtype=np.float32
        )

        scores, indices = self.index.search(
            query_embedding,
            min(top_k, len(self.metadata))
        )

        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue

            record = self.metadata[idx]

            results.append({
                "text": record["text"],
                "source": record["source"],
                "category": record["category"],
                "score": float(score)
            })

        return results


if __name__ == "__main__":
    rag = MarketingRAG()

    question = "What is Eloqua Campaign Canvas?"

    results = rag.search(question, top_k=3)

    print("\nQuestion:", question)
    print("\nRetrieved knowledge:")

    for result in results:
        print("\nSource:", result["source"])
        print("Category:", result["category"])
        print("Similarity:", round(result["score"], 4))
        print("Content:", result["text"])
