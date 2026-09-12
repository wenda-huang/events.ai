import time

import httpx

from app.services import carto

NOMINATIM = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "events.ai/1.0 (hackathon meetup app)"


def geocode_place(address: str, city: str) -> tuple[float, float] | None:
    query = address.strip() or city.strip()
    if not query:
        return None
    if city and city.lower() not in query.lower():
        query = f"{query}, {city}"
    return carto.geocode_address(query) or _nominatim(query)


def reverse_city(lat: float, lng: float) -> str | None:
    return carto.reverse_city(lat, lng) or _nominatim_reverse(lat, lng)


def _nominatim(query: str) -> tuple[float, float] | None:
    try:
        with httpx.Client(timeout=20, headers={"User-Agent": USER_AGENT}) as client:
            res = client.get(NOMINATIM, params={"q": query, "format": "json", "limit": 1})
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


def _nominatim_reverse(lat: float, lng: float) -> str | None:
    try:
        with httpx.Client(timeout=20, headers={"User-Agent": USER_AGENT}) as client:
            res = client.get(
                NOMINATIM_REVERSE,
                params={"lat": lat, "lon": lng, "format": "json"},
            )
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPError:
        return None
    time.sleep(1.1)
    address = data.get("address") if isinstance(data, dict) else None
    if not isinstance(address, dict):
        return None
    for key in ("city", "town", "village", "municipality", "county"):
        value = address.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
