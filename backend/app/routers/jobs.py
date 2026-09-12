import asyncio
import json
import logging
import threading

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import SessionLocal, get_db
from app.models import User
from app.services.cluster import run_cluster
from app.services.scan import iter_scan

log = logging.getLogger("events.jobs")

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/scan")
async def trigger_scan(request: Request, user: User = Depends(get_current_user)):
    user_id = user.id
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    def worker() -> None:
        db = SessionLocal()
        try:
            u = db.get(User, user_id)
            for event in iter_scan(db, u):
                try:
                    asyncio.run_coroutine_threadsafe(queue.put(event), loop).result(timeout=15)
                except Exception:
                    return
        except Exception as exc:
            log.exception("Scan pipeline crashed")
            try:
                asyncio.run_coroutine_threadsafe(
                    queue.put({"stage": "error", "message": str(exc), "level": "error", "ok": False, "created": 0}),
                    loop,
                ).result(timeout=5)
            except Exception:
                pass
        finally:
            db.close()
            try:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result(timeout=5)
            except Exception:
                pass

    thread = threading.Thread(target=worker, daemon=True, name="event-scan")
    thread.start()

    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    if not thread.is_alive() and queue.empty():
                        break
                    continue
                if event is None:
                    break
                yield json.dumps(event, default=str) + "\n"
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/cluster")
def trigger_cluster(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_cluster(db)
