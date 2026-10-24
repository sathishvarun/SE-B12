
from pathlib import Path
import json

from semantic_search import semantic_search

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "music_catalog.json"


def keyword_search(query: str, content_type: str = "all"):
    with DATA_FILE.open("r", encoding="utf-8") as file:
        catalog = json.load(file)

    words = query.casefold().split()
    results = []

    for item in catalog:
        item_type = str(item.get("type", "")).casefold()

        if content_type != "all" and item_type != content_type:
            continue

        searchable_text = " ".join(
            str(item.get(field, ""))
            for field in (
                "title", "artist", "album", "genre", "description"
            )
        ).casefold()

        if all(word in searchable_text for word in words):
            results.append(item)

    return results


def hybrid_search(
    query: str,
    content_type: str = "all",
    limit: int = 5,
):
    keyword_results = keyword_search(query, content_type)
    semantic_results = semantic_search(query, limit=20)

    if content_type != "all":
        semantic_results = [
            item for item in semantic_results
            if item.get("type") == content_type
        ]

    merged = {}

    for item in keyword_results:
        merged[item["id"]] = {
            **item,
            "keyword_match": True,
            "semantic_score": None,
        }

    for item in semantic_results:
        item_id = item.get("id")

        if item_id in merged:
            merged[item_id]["semantic_score"] = item.get("score")
        else:
            merged[item_id] = {
                **item,
                "keyword_match": False,
                "semantic_score": item.get("score"),
            }

    for item in merged.values():
        score = item.get("semantic_score") or 0.0
        item["hybrid_score"] = round(
            score + (0.25 if item["keyword_match"] else 0.0),
            4,
        )

    ranked = sorted(
        merged.values(),
        key=lambda item: item["hybrid_score"],
        reverse=True,
    )

    return {
        "query": query,
        "type": content_type,
        "total": len(ranked[:limit]),
        "results": ranked[:limit],
    }
