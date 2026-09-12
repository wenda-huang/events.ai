import time

import httpx

from app.geo import PITTSBURGH_LAT, PITTSBURGH_LNG
from app.services import carto

NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "events.ai/1.0 (hackathon meetup app)"


def geocode_pittsburgh(address: str) -> tuple[float, float] | None:
    query = address.strip()
    if not query:
        return None
    if "pittsburgh" not in query.lower():
        query = f"{query}, Pittsburgh, PA"
    coords = carto.geocode_address(query) or _nominatim(query)
    if coords is None:
        return None
    lat, lng = coords
    if abs(lat - PITTSBURGH_LAT) > 0.45 or abs(lng - PITTSBURGH_LNG) > 0.45:
        return None
    return lat, lng


def _nominatim(query: str) -> tuple[float, float] | None:
    try:
        with httpx.Client(timeout=20, headers={"User-Agent": USER_AGENT}) as client:
            res = client.get(
                NOMINATIM,
                params={"q": query, "format": "json", "limit": 1, "countrycodes": "us"},
            )
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPError:
        return None
    time.sleep(1.1)
    if not data:
        return None
    try:
        return float(data[0]["lat"]), float(data[0]["lon"])
    except (KeyError, TypeError, ValueError):
        return None
