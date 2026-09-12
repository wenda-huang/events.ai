from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from app.geo import haversine_mi
from app.models import City, Event
from app.services import carto, mapbox

log = logging.getLogger("events.geocode")

NOMINATIM = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
PHOTON = "https://photon.komoot.io/api"
USER_AGENT = "events.ai/1.0 (hackathon meetup app)"
CITY_CENTER_MI = 0.15

_cache: dict[str, "GeoHit"] = {}
_cache_lock = threading.Lock()
_street_re = re.compile(
    r"\d|(?:\b(?:st|street|ave|avenue|blvd|rd|road|dr|drive|way|ln|lane|pkwy|parkway|plaza|sq|square)\b)",
    re.I,
)


@dataclass(frozen=True)
class GeoHit:
    lat: float
    lng: float
    address: str = ""


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").strip().lower()).strip()


def is_city_level_address(address: str, city_name: str = "", city_label: str = "") -> bool:
    compact = _norm(address)
    if not compact:
        return True
    aliases = {_norm(city_name), _norm(city_label)}
    aliases.discard("")
    if city_label and "," in city_label:
        aliases.add(_norm(city_label.split(",", 1)[0]))
    return compact in aliases


def looks_specific_address(address: str) -> bool:
    return bool(address.strip()) and not is_city_level_address(address) and bool(_street_re.search(address))


def prefer_address(current: str, resolved: str) -> str:
    current = (current or "").strip()
    resolved = (resolved or "").strip()
    if looks_specific_address(current):
        return current
    return resolved or current


def _queries(address: str, city: str) -> list[str]:
    address = address.strip()
    city = city.strip()
    queries: list[str] = []
    if address:
        queries.append(address)
        if city and city.lower() not in address.lower():
            queries.append(f"{address}, {city}")
    return queries


def geocode_place(address: str, city: str, *, allow_nominatim: bool = True) -> tuple[float, float] | None:
    hit = lookup_place(address, city, allow_nominatim=allow_nominatim)
    return (hit.lat, hit.lng) if hit else None


def lookup_place(
    address: str,
    city: str,
    *,
    proximity: tuple[float, float] | None = None,
    allow_nominatim: bool = False,
) -> GeoHit | None:
    if is_city_level_address(address, city_label=city):
        return None
    return geocode_event_address(address, city, proximity=proximity, allow_nominatim=allow_nominatim)


def geocode_event_address(
    address: str,
    city: str = "",
    *,
    proximity: tuple[float, float] | None = None,
    allow_nominatim: bool = False,
) -> GeoHit | None:
    """Resolve a user-entered venue through Mapbox (Photon fallback). City-only queries are allowed."""
    for query in _queries(address, city):
        key = query.casefold()
        with _cache_lock:
            cached = _cache.get(key)
        if cached is not None:
            return cached
        hit = _hit_from_mapbox(query, proximity) or _photon(query)
        if hit is None and allow_nominatim:
            hit = _nominatim(query)
        if hit is not None:
            with _cache_lock:
                _cache[key] = hit
            return hit
    return None


def regeocode_city_center_events(db: Session) -> int:
    cities = {row.id: row for row in db.query(City).all()}
    updated = 0
    pending: dict[tuple[str, str], list[Event]] = {}
    for event in db.query(Event).all():
        city = cities.get(event.city_id)
        if city is None:
            continue
        if haversine_mi(event.lat, event.lng, city.lat, city.lng) >= CITY_CENTER_MI:
            continue
        if is_city_level_address(event.address, city.name, city.label):
            continue
        pending.setdefault((event.address.strip(), city.label), []).append(event)

    for index, ((address, city_label), events) in enumerate(pending.items(), start=1):
        hit = lookup_place(address, city_label)
        if hit is None:
            continue
        if haversine_mi(hit.lat, hit.lng, events[0].lat, events[0].lng) < CITY_CENTER_MI:
            continue
        for event in events:
            event.lat = hit.lat
            event.lng = hit.lng
            event.address = prefer_address(event.address, hit.address)[:300]
            updated += 1
        db.commit()
        if index % 25 == 0:
            log.info("Regeocoded %s/%s venue groups, moved %s events", index, len(pending), updated)
    if updated:
        log.info("Moved %s events off city-center pins", updated)
    return updated


def _hit_from_mapbox(query: str, proximity: tuple[float, float] | None) -> GeoHit | None:
    result = mapbox.geocode_address(query, proximity=proximity)
    if result is None:
        return None
    lat, lng, formatted = result
    return GeoHit(lat=lat, lng=lng, address=formatted or query)


def _photon(query: str) -> GeoHit | None:
    try:
        with httpx.Client(timeout=12, headers={"User-Agent": USER_AGENT}) as client:
            res = client.get(PHOTON, params={"q": query, "limit": 1})
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPError as exc:
        log.warning("Photon geocode failed for %s: %s", query, exc)
        return None
    features = data.get("features") if isinstance(data, dict) else None
    if not isinstance(features, list) or not features:
        return None
    feature = features[0]
    geometry = feature.get("geometry") if isinstance(feature, dict) else None
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    try:
        lng, lat = float(coords[0]), float(coords[1])
    except (TypeError, ValueError):
        return None
    props = feature.get("properties") if isinstance(feature, dict) else {}
    return GeoHit(lat=lat, lng=lng, address=_format_photon_address(props if isinstance(props, dict) else {}))


def _format_photon_address(props: dict) -> str:
    name = str(props.get("name") or "").strip()
    street = " ".join(part for part in (str(props.get("housenumber") or "").strip(), str(props.get("street") or "").strip()) if part)
    city = str(props.get("city") or "").strip()
    state = str(props.get("state") or "").strip()
    parts = [part for part in (name, street, city, state) if part]
    return ", ".join(parts)


def _nominatim(query: str) -> GeoHit | None:
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
        display = str(data[0].get("display_name") or query)
        return GeoHit(lat=float(data[0]["lat"]), lng=float(data[0]["lon"]), address=display)
    except (KeyError, TypeError, ValueError):
        return None


def reverse_city(lat: float, lng: float) -> str | None:
    return carto.reverse_city(lat, lng) or _nominatim_reverse(lat, lng)


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
