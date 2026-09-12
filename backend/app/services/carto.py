import httpx

from app.config import settings


def _auth_header() -> str:
    token = settings.carto_api_key.strip()
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def geocode_address(address: str) -> tuple[float, float] | None:
    if not settings.carto_api_key:
        return None
    url = settings.carto_api_base_url.rstrip("/") + "/v3/lds/geocoding/geocode"
    try:
        with httpx.Client(timeout=20) as client:
            res = client.get(
                url,
                params={"address": address, "country": "US"},
                headers={"Authorization": _auth_header()},
            )
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPError:
        return None
    return _coords_from_payload(data)


def _coords_from_payload(data: object) -> tuple[float, float] | None:
    if isinstance(data, list) and data:
        return _coords_from_payload(data[0])
    if not isinstance(data, dict):
        return None
    geometry = data.get("geometry")
    if isinstance(geometry, dict):
        coords = geometry.get("coordinates")
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            return float(coords[1]), float(coords[0])
    for lat_key, lng_key in (("lat", "lng"), ("latitude", "longitude"), ("lat", "lon")):
        if lat_key in data and lng_key in data:
            return float(data[lat_key]), float(data[lng_key])
    properties = data.get("properties")
    if isinstance(properties, dict):
        return _coords_from_payload(properties)
    return None
