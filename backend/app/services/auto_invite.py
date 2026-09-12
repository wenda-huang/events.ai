from sqlalchemy.orm import Session

from app.geo import haversine_mi
from app.models import Event, EventMembership, User
from app.serialize import parse_tags
from app.services.cluster import CLUSTER_RADIUS_MI
from app.services.notifications import notify_invite


def select_auto_invitees(
    *,
    event_lat: float,
    event_lng: float,
    event_tags: set[str],
    host_id: int,
    people_max: int,
    joined_count: int,
    member_ids: set[int],
    candidates: list,
    radius_mi: float = CLUSTER_RADIUS_MI,
) -> list:
    seats = max(0, people_max - joined_count)
    if seats == 0 or not event_tags:
        return []
    ranked: list[tuple[int, float, object]] = []
    for user in candidates:
        if user.id == host_id or user.id in member_ids:
            continue
        if user.lat is None or user.lng is None:
            continue
        user_tags = set(user.tags if isinstance(user.tags, (list, set, tuple)) else parse_tags(user.tags))
        overlap = len(user_tags & event_tags)
        if overlap == 0:
            continue
        dist = haversine_mi(event_lat, event_lng, user.lat, user.lng)
        if dist > radius_mi:
            continue
        ranked.append((overlap, dist, user))
    ranked.sort(key=lambda row: (-row[0], row[1], row[2].id))
    return [user for _, _, user in ranked[:seats]]


def invite_nearby_matches(db: Session, event: Event, host_id: int) -> int:
    event_tags = set(parse_tags(event.tags))
    memberships = (
        db.query(EventMembership).filter(EventMembership.event_id == event.id).all()
    )
    member_ids = {m.user_id for m in memberships}
    joined_count = sum(1 for m in memberships if m.status == "joined")
    users = (
        db.query(User)
        .filter(
            User.onboarded_at.isnot(None),
            User.lat.isnot(None),
            User.lng.isnot(None),
            User.id != host_id,
        )
        .all()
    )
    chosen = select_auto_invitees(
        event_lat=event.lat,
        event_lng=event.lng,
        event_tags=event_tags,
        host_id=host_id,
        people_max=event.people_max,
        joined_count=joined_count,
        member_ids=member_ids,
        candidates=users,
    )
    host = db.get(User, host_id)
    for user in chosen:
        shared = sorted(set(parse_tags(user.tags)) & event_tags)
        db.add(
            EventMembership(
                event_id=event.id,
                user_id=user.id,
                status="invited",
                reason=f"Auto-invite: {', '.join(shared[:3]) or 'shared interests'}",
            )
        )
        notify_invite(db, recipient_id=user.id, event=event, actor=host)
    return len(chosen)
