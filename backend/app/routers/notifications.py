from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Notification, User
from app.services.notifications import backfill_pending_invites, mark_read, notification_public

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    backfill_pending_invites(db, user)
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.id.desc())
        .limit(50)
        .all()
    )
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.read_at.is_(None))
        .count()
    )
    return {
        "notifications": [notification_public(row) for row in rows],
        "unread_count": unread_count,
        "enabled": getattr(user, "notifications_enabled", True) is not False,
    }


@router.post("/notifications/{notification_id}/read")
def read_notification(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    mark_read(row)
    db.commit()
    db.refresh(row)
    return notification_public(row)


@router.post("/notifications/read-all")
def read_all_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.read_at.is_(None))
        .all()
    )
    for row in rows:
        mark_read(row)
    db.commit()
    return {"ok": True, "updated": len(rows)}
