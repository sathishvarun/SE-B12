"""Google Maps for outlets: a directions link (free, no key) and an embedded map (Maps Embed API: free and unlimited,
needs GOOGLE_MAPS_EMBED_KEY). Only outlets linked to their Google Maps listing get a map; others show the address."""

from urllib.parse import quote_plus

from app.config import settings


def _query(outlet) -> str:
    parts = [outlet.name, outlet.address or outlet.area, outlet.city, outlet.pincode]
    return ", ".join(p for p in parts if p)


def on_google_maps(outlet) -> bool:
    return bool(getattr(outlet, "google_place_id", None)) or _owner_link(outlet)


def place_url(outlet) -> str | None:
    """The exact Google Maps listing when the outlet is linked to it (Places API search on Connections)."""
    if not getattr(outlet, "google_place_id", None):
        return None
    name = quote_plus(outlet.google_place_name or outlet.name)
    return f"https://www.google.com/maps/search/?api=1&query={name}&query_place_id={quote_plus(outlet.google_place_id)}"


def _owner_link(outlet) -> bool:
    url = (outlet.google_maps_url or "").lower()
    return url.startswith("https://") and ("google." in url or "goo.gl" in url or "g.page" in url)


def directions_url(outlet) -> str | None:
    """Best free link to the branch on Google Maps: the owner's own link, else the linked listing, else a search by
    address (or by name and city). No key, no cost."""
    if _owner_link(outlet):
        return outlet.google_maps_url
    if place := place_url(outlet):
        return place
    if outlet.address or outlet.area:
        return f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(_query(outlet))}"
    if outlet.city:
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(_query(outlet))}"
    return None


def embed_url(outlet) -> str | None:
    if not settings.GOOGLE_MAPS_EMBED_KEY:
        return None
    if getattr(outlet, "google_place_id", None):
        q = quote_plus(f"place_id:{outlet.google_place_id}")
        return f"https://www.google.com/maps/embed/v1/place?key={settings.GOOGLE_MAPS_EMBED_KEY}&q={q}"
    if not on_google_maps(outlet):
        return None
    return f"https://www.google.com/maps/embed/v1/place?key={settings.GOOGLE_MAPS_EMBED_KEY}&q={quote_plus(_query(outlet))}"
