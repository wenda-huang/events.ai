from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from app.config import settings

_TILE_KEY_ALIASES = {"key", "api_key", "apikey"}


def append_basemap_key(url: str, api_key: str) -> str:
    """Attach a CARTO basemap key so raster tiles are not watermarked."""
    url = (url or "").strip()
    key = (api_key or "").strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    if not url:
        return url
    parts = urlsplit(url)
    query = {name: value for name, value in parse_qsl(parts.query, keep_blank_values=True)}
    existing = ""
    for alias in ("key", "api_key", "apikey"):
        value = (query.get(alias) or "").strip()
        if value:
            existing = value
            break
    token = existing or key
    if not token:
        return url
    query = {name: value for name, value in query.items() if name.lower() not in _TILE_KEY_ALIASES}
    query["key"] = token
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def public_tile_url() -> str:
    url = settings.secret("carto_tile_url") or settings.carto_tile_url
    return append_basemap_key(url, settings.secret("carto_api_key"))


def _auth_header() -> str:
    token = settings.secret("carto_api_key")
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def _base_url() -> str:
    return (settings.secret("carto_api_base_url") or "https://gcp-us-east1.api.carto.com").rstrip("/")


def geocode_address(address: str) -> tuple[float, float] | None:
    if not settings.secret("carto_api_key"):
        return None
    try:
        with httpx.Client(timeout=20) as client:
            res = client.get(
                _base_url() + "/v3/lds/geocoding/geocode",
                params={"address": address},
                headers={"Authorization": _auth_header()},
            )
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPError:
        return None
    return _coords_from_payload(data)


def reverse_city(lat: float, lng: float) -> str | None:
    if not settings.secret("carto_api_key"):
        return None
    try:
        with httpx.Client(timeout=20) as client:
            res = client.get(
                _base_url() + "/v3/lds/geocoding/reverse",
                params={"latitude": lat, "longitude": lng},
                headers={"Authorization": _auth_header()},
            )
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPError:
        return None
    return _city_from_payload(data)


def _city_from_payload(data: object) -> str | None:
    if isinstance(data, list) and data:
        return _city_from_payload(data[0])
    if not isinstance(data, dict):
        return None
    for key in ("city", "town", "locality", "municipality"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    properties = data.get("properties")
    if isinstance(properties, dict):
        return _city_from_payload(properties)
    address = data.get("address")
    if isinstance(address, dict):
        return _city_from_payload(address)
    return None


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
