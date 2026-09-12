import json

from app.auth import is_admin
from app.geo import haversine_mi
from app.models import City, Event, User


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def dump_tags(tags: list[str]) -> str:
    return json.dumps(tags)


def user_public(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "phone": user.phone,
        "lat": user.lat,
        "lng": user.lng,
        "tags": parse_tags(user.tags),
        "onboarded": user.onboarded_at is not None,
        "default_radius_mi": user.default_radius_mi,
        "is_admin": is_admin(user),
    }


def city_public(city: City) -> dict:
    return {
        "id": city.id,
        "name": city.name,
        "state": city.state,
        "lat": city.lat,
        "lng": city.lng,
        "label": city.label,
    }


def event_public(
    event: Event,
    *,
    origin: tuple[float, float] | None = None,
    current_user_id: int | None = None,
) -> dict:
    memberships = event.memberships or []
    joined = [m for m in memberships if m.status == "joined"]
    invited = [m for m in memberships if m.status == "invited"]
    my_status = None
    if current_user_id is not None:
        mine = next((m for m in memberships if m.user_id == current_user_id), None)
        my_status = mine.status if mine else None
    distance = None
    if origin is not None:
        distance = round(haversine_mi(origin[0], origin[1], event.lat, event.lng), 2)
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "location": {
            "lat": event.lat,
            "lng": event.lng,
            "address": event.address,
            "city": event.city_row.label if event.city_row is not None else event.city,
        },
        "starts_at": event.starts_at.isoformat(),
        "ends_at": event.ends_at.isoformat(),
        "people_min": event.people_min,
        "people_max": event.people_max,
        "cost_estimate": event.cost_estimate,
        "estimated_fields": parse_tags(getattr(event, "estimated_fields", None) or "[]"),
        "tags": parse_tags(event.tags),
        "source": event.source,
        "source_url": event.source_url,
        "created_by": event.created_by_id,
        "attendee_count": len(joined),
        "invite_count": len(invited),
        "my_status": my_status,
        "distance_mi": distance,
    }
