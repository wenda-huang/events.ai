from __future__ import annotations

import re
from typing import Sequence, TypeVar

from sqlalchemy.orm import Session

from app.geo import haversine_mi
from app.models import City, Event

# Top 9 US cities by population (Census) plus Pittsburgh, PA.
IMPLEMENTED_CITIES = [
    {"name": "New York", "state": "NY", "lat": 40.7128, "lng": -74.0060},
    {"name": "Los Angeles", "state": "CA", "lat": 34.0522, "lng": -118.2437},
    {"name": "Chicago", "state": "IL", "lat": 41.8781, "lng": -87.6298},
    {"name": "Houston", "state": "TX", "lat": 29.7604, "lng": -95.3698},
    {"name": "Phoenix", "state": "AZ", "lat": 33.4484, "lng": -112.0740},
    {"name": "Philadelphia", "state": "PA", "lat": 39.9526, "lng": -75.1652},
    {"name": "San Antonio", "state": "TX", "lat": 29.4241, "lng": -98.4936},
    {"name": "San Diego", "state": "CA", "lat": 32.7157, "lng": -117.1611},
    {"name": "Dallas", "state": "TX", "lat": 32.7767, "lng": -96.7970},
    {"name": "Pittsburgh", "state": "PA", "lat": 40.4406, "lng": -79.9959},
]

DEFAULT_CITY_NAME = "Pittsburgh"
DEFAULT_CITY_STATE = "PA"
DEFAULT_LAT = 40.4406
DEFAULT_LNG = -79.9959

_ALIASES = {
    "nyc": ("New York", "NY"),
    "new york city": ("New York", "NY"),
    "la": ("Los Angeles", "CA"),
    "los angeles": ("Los Angeles", "CA"),
    "philly": ("Philadelphia", "PA"),
    "dallas texas": ("Dallas", "TX"),
}

T = TypeVar("T")


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").strip().lower()).strip()


def implemented_cities(db: Session) -> list[City]:
    return db.query(City).order_by(City.name, City.state).all()


def default_city(db: Session) -> City | None:
    return (
        db.query(City)
        .filter(City.name == DEFAULT_CITY_NAME, City.state == DEFAULT_CITY_STATE)
        .first()
        or db.query(City).order_by(City.id).first()
    )


def nearest_city(cities: Sequence[T], lat: float, lng: float) -> T | None:
    if not cities:
        return None
    return min(cities, key=lambda city: haversine_mi(lat, lng, city.lat, city.lng))


def match_city(cities: Sequence[T], raw: str) -> T | None:
    compact = _norm(raw)
    if not compact:
        return None
    alias = _ALIASES.get(compact)
    if alias:
        name, state = alias
        for city in cities:
            if city.name == name and city.state == state:
                return city
    for city in cities:
        if compact == _norm(city.name) or compact == _norm(f"{city.name} {city.state}"):
            return city
    for city in cities:
        name_n = _norm(city.name)
        if len(name_n) >= 4 and re.search(rf"\b{re.escape(name_n)}\b", compact):
            return city
    return None


def seed_cities(db: Session) -> None:
    existing = {(row.name.lower(), row.state.lower()): row for row in db.query(City).all()}
    for item in IMPLEMENTED_CITIES:
        key = (item["name"].lower(), item["state"].lower())
        row = existing.get(key)
        if row is None:
            db.add(City(name=item["name"], state=item["state"], lat=item["lat"], lng=item["lng"]))
        else:
            row.lat = item["lat"]
            row.lng = item["lng"]
    db.commit()


def associate_events_to_default_city(db: Session) -> None:
    city = default_city(db)
    if city is None:
        return
    for event in db.query(Event).filter(Event.city_id.is_(None)).all():
        event.city_id = city.id
        if not (event.city or "").strip():
            event.city = city.name
    db.commit()
