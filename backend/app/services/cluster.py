from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from app.geo import haversine_mi
from app.models import Event, EventMembership, User
from app.serialize import parse_tags
from app.services.notifications import notify_invite

CLUSTER_RADIUS_MI = 3.0


def run_cluster(db: Session) -> dict:
    users = (
        db.query(User)
        .filter(User.onboarded_at.isnot(None), User.lat.isnot(None), User.lng.isnot(None))
        .all()
    )
    users = [u for u in users if parse_tags(u.tags)]
    used: set[int] = set()
    clusters: list[list[User]] = []
    for user in users:
        if user.id in used:
            continue
        group = [user]
        used.add(user.id)
        user_tags = set(parse_tags(user.tags))
        for other in users:
            if other.id in used:
                continue
            if haversine_mi(user.lat, user.lng, other.lat, other.lng) > CLUSTER_RADIUS_MI:
                continue
            if not (user_tags & set(parse_tags(other.tags))):
                continue
            group.append(other)
            used.add(other.id)
        clusters.append(group)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    events = (
        db.query(Event)
        .options(selectinload(Event.memberships))
        .filter(Event.starts_at >= now)
        .all()
    )

    invited = 0
    used_events: set[int] = set()
    for group in clusters:
        tag_union: set[str] = set()
        for member in group:
            tag_union |= set(parse_tags(member.tags))
        centroid_lat = sum(m.lat for m in group) / len(group)
        centroid_lng = sum(m.lng for m in group) / len(group)

        ranked: list[tuple[int, float, Event]] = []
        for event in events:
            if event.id in used_events:
                continue
            overlap = len(tag_union & set(parse_tags(event.tags)))
            if overlap == 0:
                continue
            dist = haversine_mi(centroid_lat, centroid_lng, event.lat, event.lng)
            if dist > CLUSTER_RADIUS_MI:
                continue
            already = {m.user_id for m in event.memberships}
            if all(member.id in already for member in group):
                continue
            ranked.append((overlap, dist, event))
        if not ranked:
            continue
        ranked.sort(key=lambda row: (-row[0], row[1]))
        event = ranked[0][2]
        used_events.add(event.id)
        joined = [m for m in event.memberships if m.status == "joined"]
        seats = max(0, event.people_max - len(joined))
        if seats == 0:
            continue
        for member in group:
            if seats <= 0:
                break
            existing = next((m for m in event.memberships if m.user_id == member.id), None)
            if existing is not None:
                continue
            shared = sorted(tag_union & set(parse_tags(member.tags)) & set(parse_tags(event.tags)))
            reason = f"Nearby cluster match: {', '.join(shared[:3]) or 'shared interests'}"
            db.add(
                EventMembership(
                    event_id=event.id,
                    user_id=member.id,
                    status="invited",
                    reason=reason,
                )
            )
            notify_invite(db, recipient_id=member.id, event=event)
            invited += 1
            seats -= 1
    db.commit()
    return {"ok": True, "clusters": len(clusters), "invites_created": invited}
