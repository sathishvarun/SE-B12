
from pathlib import Path
import json
from hybrid_search import hybrid_search
from fastapi import FastAPI, Query, HTTPException
from semantic_search import semantic_search
from hybrid_search import hybrid_search
app = FastAPI(
    title="Spotify Hybrid Search API",
    description="Search tracks, artists, albums, playlists and podcasts.",
    version="1.0.0",
)

# Locate data/music_catalog.json from the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "music_catalog.json"


def load_catalog():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Music catalogue not found: {DATA_FILE}"
        )

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("The music catalogue must be a JSON list.")

    return data


@app.get("/")
def home():
    return {
        "message": "Spotify Hybrid Search API is running",
        "docs": "/docs",
        "search_endpoint": "/search",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/search")
def search_music(
    query: str = Query(
        min_length=1,
        max_length=200,
        description="Words to search for",
    ),
    content_type: str = Query(
        default="all",
        alias="type",
        description="all, track, artist, album, playlist or podcast",
    ),
):
    allowed_types = {
        "all", "track", "artist", "album", "playlist", "podcast"
    }

    if content_type.lower() not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Type must be one of: {', '.join(sorted(allowed_types))}",
        )

    try:
        catalog = load_catalog()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load music catalogue: {exc}",
        ) from exc

    words = query.casefold().split()
    results = []

    for item in catalog:
        item_type = str(item.get("type", "")).casefold()

        if content_type.lower() != "all" and item_type != content_type.lower():
            continue

        searchable_text = " ".join(
            str(item.get(field, ""))
            for field in (
                "title", "artist", "album", "genre", "description"
            )
        ).casefold()

        # Match every query word, regardless of word order.
        if all(word in searchable_text for word in words):
            results.append(item)

    return {
        "query": query,
        "type": content_type.lower(),
        "total": len(results),
        "results": results,
    }
@app.get("/semantic-search")
def search_semantically(
    query: str = Query(min_length=1, max_length=200),
):
    try:
        results = semantic_search(query, limit=5)
        return {
            "query": query,
            "total": len(results),
            "results": results,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Semantic search failed: {exc}",
        ) from exc

   

@app.get("/hybrid-search")
def search_hybrid(
    query: str = Query(min_length=1, max_length=200),
    content_type: str = Query(default="all", alias="type"),
):
    try:
        return hybrid_search(query, content_type)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Hybrid search failed: {exc}",
        ) from exc
