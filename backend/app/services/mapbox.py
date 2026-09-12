from __future__ import annotations

import logging
import threading
import time

import httpx

from app.config import settings

log = logging.getLogger("events.mapbox")
FORWARD_URL = "https://api.mapbox.com/search/geocode/v6/forward"
# Stay well under the default 600 requests/minute cap.
MIN_INTERVAL_SEC = 0.2

_lock = threading.Lock()
_next_allowed = 0.0
_disabled = False


def _token() -> str:
    return settings.secret("mapbox_api_key")


def _wait_for_slot() -> None:
    global _next_allowed
    with _lock:
        now = time.monotonic()
        delay = _next_allowed - now
        _next_allowed = max(now, _next_allowed) + MIN_INTERVAL_SEC
    if delay > 0:
        time.sleep(delay)


def geocode_address(query: str, *, proximity: tuple[float, float] | None = None) -> tuple[float, float, str] | None:
    global _disabled
    token = _token()
    if _disabled or not token or not query.strip():
        return None
    _wait_for_slot()
    params: dict[str, str | int] = {
        "q": query.strip(),
        "access_token": token,
        "limit": 1,
        "country": "US",
        "autocomplete": "false",
    }
    if proximity is not None:
        params["proximity"] = f"{proximity[1]},{proximity[0]}"
    try:
        with httpx.Client(timeout=12) as client:
            res = client.get(FORWARD_URL, params=params)
            if res.status_code == 429:
                retry_after = float(res.headers.get("Retry-After") or 2)
                log.warning("Mapbox rate limited; sleeping %.1fs", retry_after)
                time.sleep(max(1.0, retry_after))
                return None
            if res.status_code in {401, 403}:
                _disabled = True
                log.warning("Mapbox geocode HTTP %s — check the secret [mapbox] api_key", res.status_code)
                return None
            if res.status_code >= 400:
                log.warning("Mapbox geocode HTTP %s for %s", res.status_code, query)
                return None
            data = res.json()
    except httpx.HTTPError as exc:
        log.warning("Mapbox geocode error for %s: %s", query, exc)
        return None
    return _hit_from_payload(data)


def _hit_from_payload(data: object) -> tuple[float, float, str] | None:
    if not isinstance(data, dict):
        return None
    features = data.get("features")
    if not isinstance(features, list) or not features:
        return None
    feature = features[0]
    if not isinstance(feature, dict):
        return None
    geometry = feature.get("geometry")
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    try:
        lng, lat = float(coords[0]), float(coords[1])
    except (TypeError, ValueError):
        return None
    props = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
    address = (
        str(props.get("full_address") or "").strip()
        or str(props.get("place_formatted") or "").strip()
        or str(props.get("name") or "").strip()
    )
    return lat, lng, address
