from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.geo import within_radius
from app.models import Event, EventMembership, User
from app.schemas import EventCreate
from app.serialize import dump_tags, event_public, parse_tags
from app.tags import normalize_tags

router = APIRouter(tags=["events"])


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _default_window() -> tuple[datetime, datetime]:
    start = datetime.now(timezone.utc).replace(tzinfo=None)
    return start, start + timedelta(days=14)


def _matches_query(event: Event, q: str) -> bool:
    needle = q.strip().lower()
    if not needle:
        return True
    hay = " ".join(
        [
            event.title,
            event.description,
            event.address,
            event.city,
            " ".join(parse_tags(event.tags)),
        ]
    ).lower()
    return needle in hay


def _load_events(db: Session) -> list[Event]:
    return db.query(Event).options(selectinload(Event.memberships)).all()


@router.get("/events")
def list_events(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_mi: float = Query(3, ge=0.25, le=50),
    start: datetime | None = None,
    end: datetime | None = None,
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    window_start, window_end = _default_window()
    if start is not None:
        window_start = _naive(start)
    if end is not None:
        window_end = _naive(end)
    results = []
    for event in _load_events(db):
        if event.starts_at > window_end or event.ends_at < window_start:
            continue
        if not within_radius(lat, lng, event.lat, event.lng, radius_mi):
            continue
        if q and not _matches_query(event, q):
            continue
        results.append(event_public(event, origin=(lat, lng), current_user_id=user.id))
    results.sort(key=lambda e: (e["starts_at"], e["distance_mi"] or 0))
    return {"events": results}


@router.get("/events/recommended")
def recommended_events(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_mi: float = Query(3, ge=0.25, le=50),
    start: datetime | None = None,
    end: datetime | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    window_start, window_end = _default_window()
    if start is not None:
        window_start = _naive(start)
    if end is not None:
        window_end = _naive(end)
    user_tags = set(parse_tags(user.tags))
    scored = []
    for event in _load_events(db):
        if event.starts_at > window_end or event.ends_at < window_start:
            continue
        if not within_radius(lat, lng, event.lat, event.lng, radius_mi):
            continue
        event_tags = set(parse_tags(event.tags))
        overlap = len(user_tags & event_tags)
        if user_tags and overlap == 0:
            continue
        payload = event_public(event, origin=(lat, lng), current_user_id=user.id)
        payload["tag_overlap"] = overlap
        scored.append(payload)
    scored.sort(key=lambda e: (-e["tag_overlap"], e["distance_mi"] or 99, e["starts_at"]))
    return {"events": scored[:12]}


@router.get("/me/events")
def my_events(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(EventMembership)
        .options(selectinload(EventMembership.event).selectinload(Event.memberships))
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


@router.get("/events/{event_id}")
def get_event(
    event_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = db.query(Event).options(selectinload(Event.memberships)).filter(Event.id == event_id).first()
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
    event = Event(
        title=body.title.strip(),
        description=body.description.strip(),
        lat=body.lat,
        lng=body.lng,
        address=body.address.strip(),
        city=body.city.strip() or "Pittsburgh",
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
    db.commit()
    db.refresh(event)
    event = db.query(Event).options(selectinload(Event.memberships)).filter(Event.id == event.id).first()
    return event_public(event, current_user_id=user.id)


def _get_event(db: Session, event_id: int) -> Event:
    event = db.query(Event).options(selectinload(Event.memberships)).filter(Event.id == event_id).first()
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
    if mine is None or mine.status != "joined":
        if len(joined) >= event.people_max:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Event is full")
    if mine is None:
        mine = EventMembership(event_id=event.id, user_id=user.id, status="joined")
        db.add(mine)
    else:
        mine.status = "joined"
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
