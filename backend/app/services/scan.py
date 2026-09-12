from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.geo import PITTSBURGH_LAT, PITTSBURGH_LNG
from app.models import Event
from app.serialize import dump_tags
from app.services import geocode, llm, querit
from app.tags import normalize_tags


def _naive(value: str | datetime) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _dedupe_key(title: str, starts: datetime, lat: float, lng: float) -> tuple:
    return (title.strip().lower(), starts.date().isoformat(), round(lat, 3), round(lng, 3))


def run_scan(db: Session) -> dict:
    if not settings.secret("querit_api_key"):
        return {"ok": False, "reason": "QUERIT_API_KEY missing", "created": 0}
    if not settings.secret("openai_api_key"):
        return {"ok": False, "reason": "OPENAI_API_KEY missing — add it under [openai] in config.ini", "created": 0}

    seen_urls = {e.source_url for e in db.query(Event).filter(Event.source_url.isnot(None)).all()}
    existing_keys = {
        _dedupe_key(e.title, e.starts_at, e.lat, e.lng) for e in db.query(Event).all()
    }

    documents: list[dict] = []
    urls: list[str] = []
    for query in querit.scan_queries():
        for item in querit.search(query, count=6):
            if not item["url"] or item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])
            documents.append(item)
            urls.append(item["url"])
        if len(documents) >= 40:
            break

    pages = querit.fetch_contents(urls[:16])
    for doc in documents:
        if doc["url"] in pages:
            doc["content"] = pages[doc["url"]][:4000]

    extracted = llm.extract_events(documents)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    horizon = now + timedelta(days=35)
    created = 0

    for item in extracted:
        title = (item.get("title") or "").strip()
        starts = _naive(item.get("starts_at"))
        ends = _naive(item.get("ends_at"))
        address = (item.get("address") or "").strip()
        source_url = (item.get("source_url") or "").strip() or None
        if not title or starts is None:
            continue
        if ends is None:
            ends = starts + timedelta(hours=2)
        if ends <= starts or starts < now - timedelta(days=1) or starts > horizon:
            continue
        if source_url and db.query(Event).filter(Event.source_url == source_url).first():
            continue
        coords = geocode.geocode_pittsburgh(address or title)
        if coords is None:
            coords = (PITTSBURGH_LAT, PITTSBURGH_LNG)
        lat, lng = coords
        key = _dedupe_key(title, starts, lat, lng)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        people_min = int(item.get("people_min") or 2)
        people_max = int(item.get("people_max") or 16)
        if people_max < people_min:
            people_max = people_min
        db.add(
            Event(
                title=title[:200],
                description=(item.get("description") or "")[:4000],
                lat=lat,
                lng=lng,
                address=address[:300],
                city="Pittsburgh",
                starts_at=starts,
                ends_at=ends,
                people_min=max(1, people_min),
                people_max=min(80, people_max),
                cost_estimate=(item.get("cost_estimate") or "Free")[:80],
                tags=dump_tags(normalize_tags(item.get("tags") or [])),
                source="ai",
                source_url=source_url,
            )
        )
        created += 1
    db.commit()
    return {"ok": True, "created": created, "scanned_docs": len(documents)}
