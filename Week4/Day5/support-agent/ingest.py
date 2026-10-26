"""Load everything in knowledge/ (.txt, .md, .pdf) into the vector database.
Run this once, and again whenever you add or change your content.
(You can also do this from the "Knowledge Base" page of the web app.)

    python ingest.py
"""
from dotenv import load_dotenv

load_dotenv()

from tools.rag_tool import KNOWLEDGE_DIR, MissingKeyError, ingest_folder  # noqa: E402

if __name__ == "__main__":
    print(f"Loading content from {KNOWLEDGE_DIR} ...")
    try:
        n = ingest_folder()
    except MissingKeyError as e:
        raise SystemExit(str(e))
    print(f"Done. {n} chunks stored in data/vector_db")
