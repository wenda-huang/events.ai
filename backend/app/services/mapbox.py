from __future__ import annotations

import logging
import re
import threading
import time

import httpx

from app.config import settings

log = logging.getLogger("events.mapbox")
SEARCHBOX_URL = "https://api.mapbox.com/search/searchbox/v1/forward"
FORWARD_URL = "https://api.mapbox.com/search/geocode/v6/forward"
# Stay well under the default 600 requests/minute cap.
MIN_INTERVAL_SEC = 0.2
_STOP = {"the", "a", "an", "of", "and", "at", "in", "on", "to", "for"}

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
    token = _token()
    if _disabled or not token or not query.strip():
        return None
    return _searchbox(query, proximity=proximity) or _geocode_v6(query, proximity=proximity)


def _searchbox(query: str, *, proximity: tuple[float, float] | None) -> tuple[float, float, str] | None:
    params: dict[str, str | int] = {
        "q": query.strip(),
        "access_token": _token(),
        "limit": 5,
        "country": "US",
        "language": "en",
        "types": "poi,address,street,place",
    }
    if proximity is not None:
        params["proximity"] = f"{proximity[1]},{proximity[0]}"
    data = _get_json(SEARCHBOX_URL, params, query)
    return _best_hit_from_payload(query, data)


def _geocode_v6(query: str, *, proximity: tuple[float, float] | None) -> tuple[float, float, str] | None:
    params: dict[str, str | int] = {
        "q": query.strip(),
        "access_token": _token(),
        "limit": 5,
        "country": "US",
        "autocomplete": "false",
    }
    if proximity is not None:
        params["proximity"] = f"{proximity[1]},{proximity[0]}"
    data = _get_json(FORWARD_URL, params, query)
    return _best_hit_from_payload(query, data) or _hit_from_payload(data)


def _get_json(url: str, params: dict[str, str | int], query: str) -> object | None:
    global _disabled
    _wait_for_slot()
    try:
        with httpx.Client(timeout=12) as client:
            res = client.get(url, params=params)
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
            return res.json()
    except httpx.HTTPError as exc:
        log.warning("Mapbox geocode error for %s: %s", query, exc)
        return None


def _tokens(value: str) -> list[str]:
    return [part for part in re.split(r"[^a-z0-9]+", value.casefold()) if part and part not in _STOP]


def _feature_score(query: str, feature: dict) -> int:
    props = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
    name = str(props.get("name") or "")
    address = str(props.get("full_address") or props.get("place_formatted") or "")
    ftype = str(props.get("feature_type") or props.get("type") or "").casefold()
    q_tokens = _tokens(query)
    hay = f"{name} {address}".casefold()
    score = 0
    for token in q_tokens:
        if token in hay:
            score += 4 if token in name.casefold() else 1
    if name and name.casefold() in query.casefold():
        score += 6
    if ftype in {"address", "poi"}:
        score += 3
    elif ftype in {"street", "neighborhood"}:
        score += 1
    elif ftype in {"place", "region", "country", "district", "locality"}:
        score -= 3
    return score


def _coords_and_address(feature: dict) -> tuple[float, float, str] | None:
    geometry = feature.get("geometry")
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        props = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
        nested = props.get("coordinates") if isinstance(props.get("coordinates"), dict) else None
        if nested:
            coords = [nested.get("longitude"), nested.get("latitude")]
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    try:
        lng, lat = float(coords[0]), float(coords[1])
    except (TypeError, ValueError):
        return None
    props = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
    name = str(props.get("name") or "").strip()
    formatted = (
        str(props.get("full_address") or "").strip()
        or str(props.get("place_formatted") or "").strip()
        or name
    )
    if name and formatted and name.casefold() not in formatted.casefold():
        formatted = f"{name}, {formatted}"
    return lat, lng, formatted


def _best_hit_from_payload(query: str, data: object) -> tuple[float, float, str] | None:
    if not isinstance(data, dict):
        return None
    features = data.get("features")
    if not isinstance(features, list) or not features:
        return None
    ranked: list[tuple[int, tuple[float, float, str]]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        hit = _coords_and_address(feature)
        if hit is None:
            continue
        ranked.append((_feature_score(query, feature), hit))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    best_score, best_hit = ranked[0]
    if best_score <= 0:
        return ranked[0][1] if len(query.strip()) > 0 else None
    return best_hit


def _hit_from_payload(data: object) -> tuple[float, float, str] | None:
    if not isinstance(data, dict):
        return None
    features = data.get("features")
    if not isinstance(features, list) or not features:
        return None
    feature = features[0]
    if not isinstance(feature, dict):
        return None
    return _coords_and_address(feature)
