from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Event, Notification, User

KIND_AI_INVITE = "ai_invite"
KIND_USER_INVITE = "user_invite"
KIND_EVENT_JOIN = "event_join"


def _actor_name(actor: Any) -> str:
    if actor is None:
        return ""
    return (getattr(actor, "name", None) or "").strip() or "Someone"


def invite_message(event_title: str, actor_name: str | None) -> tuple[str, str, str]:
    title = event_title.strip() or "an event"
    if actor_name:
        return f"{actor_name} invited you", f"{actor_name} invited you to {title}.", KIND_USER_INVITE
    return "events.ai invited you", f"You're invited to {title}.", KIND_AI_INVITE


def join_message(event_title: str, actor_name: str) -> tuple[str, str]:
    title = event_title.strip() or "your event"
    name = actor_name.strip() or "Someone"
    return f"{name} joined your event", f"{name} joined {title}."


def should_notify_join(created_by_id: int | None, actor_id: int) -> bool:
    return bool(created_by_id) and created_by_id != actor_id


def recipient_allows_notifications(user: Any | None) -> bool:
    if user is None:
        return False
    # None means the column was added after signup; treat as on.
    return getattr(user, "notifications_enabled", True) is not False


def notification_public(row: Notification) -> dict:
    return {
        "id": row.id,
        "kind": row.kind,
        "title": row.title,
        "body": row.body,
        "event_id": row.event_id,
        "read": row.read_at is not None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _load_user(db: Session, user_id: int | None) -> User | None:
    if not user_id:
        return None
    from app.models import User

    return db.get(User, user_id)


def _existing(
    db: Session,
    *,
    user_id: int,
    kind: str,
    event_id: int | None,
    actor_user_id: int | None,
) -> Notification | None:
    from app.models import Notification

    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.kind == kind,
            Notification.event_id == event_id,
            Notification.actor_user_id == actor_user_id,
        )
        .first()
    )


def _create(
    db: Session,
    *,
    user_id: int,
    kind: str,
    title: str,
    body: str,
    event_id: int | None,
    actor_user_id: int | None,
) -> Notification | None:
    from app.models import Notification

    recipient = _load_user(db, user_id)
    if not recipient_allows_notifications(recipient):
        return None
    found = _existing(
        db,
        user_id=user_id,
        kind=kind,
        event_id=event_id,
        actor_user_id=actor_user_id,
    )
    if found is not None:
        return found
    row = Notification(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        event_id=event_id,
        actor_user_id=actor_user_id,
    )
    db.add(row)
    db.flush()
    return row


def notify_invite(
    db: Session,
    *,
    recipient_id: int,
    event: Event,
    actor: User | None = None,
) -> Notification | None:
    if actor is not None and actor.id == recipient_id:
        return None
    actor_name = _actor_name(actor) if actor is not None else None
    title, body, kind = invite_message(event.title, actor_name)
    return _create(
        db,
        user_id=recipient_id,
        kind=kind,
        title=title,
        body=body,
        event_id=event.id,
        actor_user_id=actor.id if actor is not None else None,
    )


def notify_join(db: Session, *, event: Event, actor: User) -> Notification | None:
    if not should_notify_join(event.created_by_id, actor.id):
        return None
    title, body = join_message(event.title, _actor_name(actor))
    return _create(
        db,
        user_id=event.created_by_id,
        kind=KIND_EVENT_JOIN,
        title=title,
        body=body,
        event_id=event.id,
        actor_user_id=actor.id,
    )


def mark_read(row: Notification) -> Notification:
    if row.read_at is None:
        row.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return row


def backfill_pending_invites(db: Session, user: User) -> None:
    """Create missing invite notifications for memberships that already exist."""
    from app.models import EventMembership
    from sqlalchemy.orm import selectinload

    if not recipient_allows_notifications(user):
        return
    rows = (
        db.query(EventMembership)
        .options(selectinload(EventMembership.event))
        .filter(EventMembership.user_id == user.id, EventMembership.status == "invited")
        .all()
    )
    added = False
    for row in rows:
        if row.event is None:
            continue
        reason = (row.reason or "").lower()
        actor = None
        if reason.startswith("auto-invite") and row.event.created_by_id:
            actor = _load_user(db, row.event.created_by_id)
        before = _existing(
            db,
            user_id=user.id,
            kind=KIND_USER_INVITE if actor is not None else KIND_AI_INVITE,
            event_id=row.event.id,
            actor_user_id=actor.id if actor is not None else None,
        )
        if before is not None:
            continue
        notify_invite(db, recipient_id=user.id, event=row.event, actor=actor)
        added = True
    if added:
        db.commit()
