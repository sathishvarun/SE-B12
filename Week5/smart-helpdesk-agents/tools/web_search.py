"""Optional live web search with SerpAPI. Only used when SERPAPI_API_KEY is set."""
import requests

from config import SERPAPI_API_KEY


def serpapi_search(query: str, num: int = 3) -> str:
    if not SERPAPI_API_KEY:
        return "WEB_SEARCH_DISABLED: no SERPAPI_API_KEY configured."
    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={"q": query, "api_key": SERPAPI_API_KEY, "num": num, "engine": "google"},
            timeout=20,
        )
        resp.raise_for_status()
        items = resp.json().get("organic_results", [])[:num]
    except Exception as exc:  # network / quota problems should never crash the app
        return f"WEB_SEARCH_ERROR: {exc}"
    if not items:
        return "NO_MATCH: web search returned nothing."
    return "\n\n".join(
        f"[source: web - {i.get('link', '')}]\n{i.get('title', '')}: {i.get('snippet', '')}" for i in items
    )
