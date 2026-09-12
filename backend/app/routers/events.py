from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.cities import default_city, implemented_cities, match_city, nearest_city
from app.database import get_db
from app.geo import MAX_RADIUS_MI, within_radius
from app.models import City, Event, EventMembership, User
from app.schemas import EventCreate
from app.serialize import dump_tags, event_public, parse_tags
from app.services import auto_invite, geocode
from app.services.notifications import notify_join
from app.services.search import MIN_SCORE, expand_query, score_event
from app.tags import normalize_tags

router = APIRouter(tags=["events"])


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _default_window() -> tuple[datetime, datetime]:
    start = datetime.now(timezone.utc).replace(tzinfo=None)
    return start, start + timedelta(days=14)


def interest_overlap(user_tags: set[str], event_tags: set[str]) -> int:
    return len(user_tags & event_tags)


def recommend_sort_key(event: dict) -> tuple:
    return (-int(event.get("tag_overlap") or 0), event.get("distance_mi") or 99, event.get("starts_at") or "")


def _load_events(db: Session) -> list[Event]:
    return db.query(Event).options(selectinload(Event.memberships), selectinload(Event.city_row)).all()


def _resolve_city(db: Session, *, city_id: int | None, city_name: str, lat: float, lng: float) -> City | None:
    if city_id is not None:
        row = db.get(City, city_id)
        if row is not None:
            return row
    cities = implemented_cities(db)
    if city_name.strip():
        matched = match_city(cities, city_name)
        if matched is not None:
            return matched
    return nearest_city(cities, lat, lng) or default_city(db)


def search_and_distance_origins(
    lat: float,
    lng: float,
    origin_lat: float | None = None,
    origin_lng: float | None = None,
) -> tuple[tuple[float, float], tuple[float, float]]:
    search = (lat, lng)
    if origin_lat is not None and origin_lng is not None:
        return search, (origin_lat, origin_lng)
    return search, search


@router.get("/events")
def list_events(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_mi: float = Query(3, ge=0.25, le=MAX_RADIUS_MI),
    start: datetime | None = None,
    end: datetime | None = None,
    q: str | None = None,
    origin_lat: float | None = None,
    origin_lng: float | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    window_start, window_end = _default_window()
    if start is not None:
        window_start = _naive(start)
    if end is not None:
        window_end = _naive(end)
    search_at, distance_from = search_and_distance_origins(lat, lng, origin_lat, origin_lng)
    query = expand_query(q or "")
    results = []
    for event in _load_events(db):
        if event.starts_at > window_end or event.ends_at < window_start:
            continue
        if not within_radius(search_at[0], search_at[1], event.lat, event.lng, radius_mi):
            continue
        if query is not None:
            relevance = score_event(event, query)
            if relevance < MIN_SCORE:
                continue
            payload = event_public(event, origin=distance_from, current_user_id=user.id)
            payload["relevance"] = round(relevance, 2)
            results.append(payload)
        else:
            results.append(event_public(event, origin=distance_from, current_user_id=user.id))
    if query is not None:
        results.sort(key=lambda e: (-(e.get("relevance") or 0), e.get("distance_mi") or 99, e["starts_at"]))
    else:
        results.sort(key=lambda e: (e["starts_at"], e["distance_mi"] or 0))
    return {"events": results}


@router.get("/events/recommended")
def recommended_events(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_mi: float = Query(3, ge=0.25, le=MAX_RADIUS_MI),
    start: datetime | None = None,
    end: datetime | None = None,
    origin_lat: float | None = None,
    origin_lng: float | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    window_start, window_end = _default_window()
    if start is not None:
        window_start = _naive(start)
    if end is not None:
        window_end = _naive(end)
    search_at, distance_from = search_and_distance_origins(lat, lng, origin_lat, origin_lng)
    user_tags = set(parse_tags(user.tags))
    scored = []
    for event in _load_events(db):
        if event.starts_at > window_end or event.ends_at < window_start:
            continue
        if not within_radius(search_at[0], search_at[1], event.lat, event.lng, radius_mi):
            continue
        event_tags = set(parse_tags(event.tags))
        payload = event_public(event, origin=distance_from, current_user_id=user.id)
        payload["tag_overlap"] = interest_overlap(user_tags, event_tags)
        scored.append(payload)
    scored.sort(key=recommend_sort_key)
    return {"events": scored}


@router.get("/me/events")
def my_events(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(EventMembership)
        .options(
            selectinload(EventMembership.event).selectinload(Event.memberships),
            selectinload(EventMembership.event).selectinload(Event.city_row),
        )
        .filter(EventMembership.user_id == user.id)
        .all()
    )
    joined = []
    invited = []
    for row in rows:
        payload = event_public(row.event, current_user_id=user.id)
        payload["invite_reason"] = row.reason
        if row.status == "joined":
            joined.append(payload)
        elif row.status == "invited":
            invited.append(payload)
    joined.sort(key=lambda e: e["starts_at"])
    invited.sort(key=lambda e: e["starts_at"])
    return {"joined": joined, "invited": invited}


@router.get("/geocode")
def geocode_lookup(
    q: str = Query(..., min_length=2, max_length=300),
    lat: float | None = None,
    lng: float | None = None,
    user: User = Depends(get_current_user),
):
    proximity = (lat, lng) if lat is not None and lng is not None else None
    hit = geocode.geocode_event_address(q, proximity=proximity)
    if hit is None:
        raise HTTPException(status_code=404, detail="Could not find that address")
    return {"lat": hit.lat, "lng": hit.lng, "address": hit.address or q.strip()}


@router.get("/events/{event_id}")
def get_event(
    event_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = (
        db.query(Event)
        .options(selectinload(Event.memberships), selectinload(Event.city_row))
        .filter(Event.id == event_id)
        .first()
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    origin = (user.lat, user.lng) if user.lat is not None and user.lng is not None else None
    return event_public(event, origin=origin, current_user_id=user.id)


@router.post("/events")
def create_event(
    body: EventCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    starts = _naive(body.starts_at)
    ends = _naive(body.ends_at)
    if ends <= starts:
        raise HTTPException(status_code=400, detail="Event end must be after start")
    if body.people_max < body.people_min:
        raise HTTPException(status_code=400, detail="people_max must be >= people_min")
    proximity = (body.lat, body.lng) if body.lat is not None and body.lng is not None else None
    hit = geocode.geocode_event_address(body.address, body.city, proximity=proximity)
    if hit is None:
        raise HTTPException(status_code=400, detail="Could not find that address on the map")
    lat, lng = hit.lat, hit.lng
    address = geocode.prefer_address(body.address, hit.address)
    city_row = _resolve_city(db, city_id=body.city_id, city_name=body.city, lat=lat, lng=lng)
    event = Event(
        title=body.title.strip(),
        description=body.description.strip(),
        lat=lat,
        lng=lng,
        address=address.strip(),
        city=city_row.name if city_row else body.city.strip(),
        city_id=city_row.id if city_row else None,
        starts_at=starts,
        ends_at=ends,
        people_min=body.people_min,
        people_max=body.people_max,
        cost_estimate=body.cost_estimate.strip() or "Free",
        tags=dump_tags(normalize_tags(body.tags)),
        source="user",
        created_by_id=user.id,
    )
    db.add(event)
    db.flush()
    db.add(EventMembership(event_id=event.id, user_id=user.id, status="joined", reason="Host"))
    db.flush()
    if body.auto_invite:
        auto_invite.invite_nearby_matches(db, event, host_id=user.id)
    db.commit()
    db.refresh(event)
    event = (
        db.query(Event)
        .options(selectinload(Event.memberships), selectinload(Event.city_row))
        .filter(Event.id == event.id)
        .first()
    )
    return event_public(event, current_user_id=user.id)


def _get_event(db: Session, event_id: int) -> Event:
    event = (
        db.query(Event)
        .options(selectinload(Event.memberships), selectinload(Event.city_row))
        .filter(Event.id == event_id)
        .first()
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("/events/{event_id}/signup")
def signup(
    event_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = _get_event(db, event_id)
    joined = [m for m in event.memberships if m.status == "joined"]
    mine = next((m for m in event.memberships if m.user_id == user.id), None)
    was_joined = mine is not None and mine.status == "joined"
    if mine is None or mine.status != "joined":
        if len(joined) >= event.people_max:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Event is full")
    if mine is None:
        mine = EventMembership(event_id=event.id, user_id=user.id, status="joined")
        db.add(mine)
    else:
        mine.status = "joined"
    if not was_joined:
        notify_join(db, event=event, actor=user)
    db.commit()
    event = _get_event(db, event_id)
    return event_public(event, current_user_id=user.id)


@router.delete("/events/{event_id}/signup")
def leave(
    event_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = _get_event(db, event_id)
    mine = next((m for m in event.memberships if m.user_id == user.id), None)
    if mine is None:
        raise HTTPException(status_code=404, detail="You are not signed up")
    db.delete(mine)
    db.commit()
    event = _get_event(db, event_id)
    return event_public(event, current_user_id=user.id)


@router.post("/events/{event_id}/decline")
def decline(
    event_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = _get_event(db, event_id)
    mine = next((m for m in event.memberships if m.user_id == user.id), None)
    if mine is None:
        mine = EventMembership(event_id=event.id, user_id=user.id, status="declined")
        db.add(mine)
    else:
        mine.status = "declined"
    db.commit()
    event = _get_event(db, event_id)
    return event_public(event, current_user_id=user.id)
