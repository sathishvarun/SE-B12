
import json
from pathlib import Path

from pypdf import PdfReader
from docx import Document

PROJECT_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = PROJECT_DIR / "knowledge_base"
OUTPUT_FILE = PROJECT_DIR / "document_chunks.jsonl"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def extract_text(file_path):
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    elif suffix == ".docx":
        document = Document(str(file_path))
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    elif suffix == ".txt":
        return file_path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

    return ""


def split_into_chunks(text):
    text = " ".join(text.split())

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))

        # Prefer ending at a word boundary.
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - CHUNK_OVERLAP, start + 1)

    return chunks


def main():
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    supported_files = [
        path for path in KNOWLEDGE_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".pdf", ".docx", ".txt"}
    ]

    if not supported_files:
        print("No PDF, DOCX or TXT documents found.")
        print(f"Add documents inside: {KNOWLEDGE_DIR}")
        return

    total_chunks = 0
    processed_files = 0

    with OUTPUT_FILE.open("w", encoding="utf-8") as output:
        for file_path in supported_files:
            try:
                text = extract_text(file_path)
                chunks = split_into_chunks(text)

                if not chunks:
                    print(f"WARNING: No text extracted: {file_path.name}")
                    continue

                category = file_path.parent.name

                for index, chunk in enumerate(chunks):
                    record = {
                        "id": f"{processed_files}_{index}",
                        "text": chunk,
                        "source": str(file_path.relative_to(KNOWLEDGE_DIR)),
                        "category": category,
                        "chunk_index": index
                    }

                    output.write(
                        json.dumps(record, ensure_ascii=False) + "\n"
                    )

                processed_files += 1
                total_chunks += len(chunks)

                print(
                    f"Processed: {file_path.name} "
                    f"({len(chunks)} chunks)"
                )

            except Exception as exc:
                print(f"ERROR processing {file_path.name}: {exc}")

    print("\nDocument ingestion completed.")
    print(f"Files processed: {processed_files}")
    print(f"Total chunks: {total_chunks}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
