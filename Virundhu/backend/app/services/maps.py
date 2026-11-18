"""Google Maps for outlets: a directions link (free, no key) and an embedded map (Maps Embed API: free and unlimited,
needs GOOGLE_MAPS_EMBED_KEY). Only outlets linked to their Google Maps listing get a map; others show the address."""

from urllib.parse import quote_plus

from app.config import settings


def _query(outlet) -> str:
    parts = [outlet.name, outlet.address or outlet.area, outlet.city, outlet.pincode]
    return ", ".join(p for p in parts if p)


def on_google_maps(outlet) -> bool:
    url = (outlet.google_maps_url or "").lower()
    return url.startswith("https://") and ("google." in url or "goo.gl" in url or "g.page" in url)


def directions_url(outlet) -> str | None:
    """The owner's own Google Maps link opens the exact place (with its Directions button). Without one, a search."""
    if on_google_maps(outlet):
        return outlet.google_maps_url
    if not (outlet.address or outlet.area):
        return None
    return f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(_query(outlet))}"


def embed_url(outlet) -> str | None:
    if not settings.GOOGLE_MAPS_EMBED_KEY or not on_google_maps(outlet):
        return None
    return f"https://www.google.com/maps/embed/v1/place?key={settings.GOOGLE_MAPS_EMBED_KEY}&q={quote_plus(_query(outlet))}"
