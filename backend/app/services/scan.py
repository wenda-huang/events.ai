from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Event, User
from app.serialize import dump_tags
from app.services import geocode, llm, querit


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


def city_for_user(user: User | None) -> str:
    if user is not None and user.lat is not None and user.lng is not None:
        city = geocode.reverse_city(user.lat, user.lng)
        if city:
            return city
    return "Pittsburgh"


def cities_to_scan(db: Session, user: User | None) -> list[str]:
    if user is not None:
        return [city_for_user(user)]
    cities: list[str] = []
    seen: set[str] = set()
    rows = db.query(User).filter(User.onboarded_at.isnot(None), User.lat.isnot(None), User.lng.isnot(None)).all()
    for row in rows:
        city = city_for_user(row)
        key = city.lower()
        if key not in seen:
            seen.add(key)
            cities.append(city)
    return cities or ["Pittsburgh"]


def run_scan(db: Session, user: User | None = None) -> dict:
    if not settings.secret("querit_api_key"):
        return {"ok": False, "reason": "QUERIT_API_KEY missing", "created": 0}
    if not settings.llm_api_key():
        return {"ok": False, "reason": "OpenRouter API key missing — add it under [openrouter] in config.ini", "created": 0}

    cities = cities_to_scan(db, user)
    char_limit = settings.page_char_limit()
    result_count = settings.result_count()
    created = 0
    scanned_docs = 0
    summarized = 0

    existing_urls = {e.source_url for e in db.query(Event).filter(Event.source_url.isnot(None)).all()}
    existing_keys = {_dedupe_key(e.title, e.starts_at, e.lat, e.lng) for e in db.query(Event).all()}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    horizon = now + timedelta(days=35)

    for city in cities:
        hits = querit.search_city(city, count=result_count)
        documents = []
        urls = []
        for item in hits:
            url = item.get("url") or ""
            if not url or url in existing_urls:
                continue
            existing_urls.add(url)
            documents.append(item)
            urls.append(url)
        scanned_docs += len(documents)
        pages = querit.fetch_contents(urls, char_limit=char_limit)
        for doc in documents:
            if doc["url"] in pages:
                doc["content"] = pages[doc["url"]][:char_limit]
            extracted = llm.summarize_page(city, doc)
            if extracted is None:
                continue
            summarized += 1
            if _persist_extracted(db, extracted, city, now, horizon, existing_keys, existing_urls):
                created += 1
    db.commit()
    return {
        "ok": True,
        "created": created,
        "scanned_docs": scanned_docs,
        "summarized": summarized,
        "cities": cities,
        "result_count": result_count,
        "page_char_limit": char_limit,
    }


def _persist_extracted(
    db: Session,
    extracted: llm.ExtractedEvent,
    fallback_city: str,
    now: datetime,
    horizon: datetime,
    existing_keys: set,
    existing_urls: set,
) -> bool:
    title = extracted.title.strip()
    starts = _naive(extracted.starts_at)
    ends = _naive(extracted.ends_at)
    address = extracted.address.strip()
    city = extracted.city.strip() or fallback_city
    source_url = extracted.source_url.strip() or None
    if not title or starts is None:
        return False
    if ends is None:
        ends = starts + timedelta(hours=2)
    if ends <= starts or starts < now - timedelta(days=1) or starts > horizon:
        return False
    if source_url and db.query(Event).filter(Event.source_url == source_url).first():
        return False
    coords = geocode.geocode_place(address or title, city)
    if coords is None:
        coords = geocode.geocode_place(city, city)
    if coords is None:
        return False
    lat, lng = coords
    key = _dedupe_key(title, starts, lat, lng)
    if key in existing_keys:
        return False
    existing_keys.add(key)
    if source_url:
        existing_urls.add(source_url)
    people_min = max(1, extracted.people_min)
    people_max = max(people_min, extracted.people_max)
    db.add(
        Event(
            title=title[:200],
            description=extracted.description.strip()[:4000],
            lat=lat,
            lng=lng,
            address=address[:300],
            city=city[:80],
            starts_at=starts,
            ends_at=ends,
            people_min=people_min,
            people_max=min(200, people_max),
            cost_estimate=(extracted.cost_estimate or "Free")[:80],
            tags=dump_tags(extracted.tags),
            source="ai",
            source_url=source_url,
            estimated_fields=dump_tags(list(extracted.estimated_fields)),
        )
    )
    db.commit()
    return True
