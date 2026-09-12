from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from collections.abc import Iterator
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Event, User
from app.serialize import dump_tags
from app.services import geocode, llm, querit

log = logging.getLogger("events.scan")


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


def _event(stage: str, message: str, level: str = "info", **data: object) -> dict:
    payload = {"stage": stage, "message": message, "level": level, **data}
    log_fn = log.error if level == "error" else log.warning if level == "warn" else log.info
    extras = {k: v for k, v in data.items() if k not in {"page_text"}}
    log_fn("%s — %s %s", stage, message, extras if extras else "")
    return payload


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


def iter_scan(db: Session, user: User | None = None) -> Iterator[dict]:
    if not settings.secret("querit_api_key"):
        yield _event("error", "QUERIT_API_KEY missing", level="error", ok=False, created=0)
        return
    if not settings.llm_api_key():
        yield _event("error", "OpenRouter API key missing — add it under [openrouter] in config.ini", level="error", ok=False, created=0)
        return

    cities = cities_to_scan(db, user)
    char_limit = settings.page_char_limit()
    result_count = settings.result_count()
    created = 0
    scanned_docs = 0
    summarized = 0
    skipped = 0

    yield _event(
        "start",
        "Starting event scan pipeline",
        cities=cities,
        result_count=result_count,
        page_char_limit=char_limit,
        model=settings.llm_model(),
        provider=",".join(settings.llm_providers()) or "auto",
        reasoning=settings.llm_reasoning(),
    )

    existing_urls = {e.source_url for e in db.query(Event).filter(Event.source_url.isnot(None)).all()}
    existing_keys = {_dedupe_key(e.title, e.starts_at, e.lat, e.lng) for e in db.query(Event).all()}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    horizon = now + timedelta(days=21)

    for city in cities:
        yield _event("city", f"Scanning city: {city}", city=city)
        hits = querit.search_city(city, count=result_count)
        yield _event("querit", f"Querit returned {len(hits)} hits", count=len(hits), city=city)

        documents = []
        urls = []
        for item in hits:
            url = item.get("url") or ""
            if not url:
                continue
            if _spam_url(url):
                skipped += 1
                yield _event("skip", "Spam or clone calendar URL", level="warn", url=url, title=item.get("title") or "")
                continue
            if url in existing_urls:
                skipped += 1
                yield _event("skip", "Already in database", level="warn", url=url, title=item.get("title") or "")
                continue
            existing_urls.add(url)
            documents.append(item)
            urls.append(url)
        scanned_docs += len(documents)
        yield _event("pages", f"Fetching page text for {len(urls)} URLs", count=len(urls), char_limit=char_limit)
        pages = querit.fetch_contents(urls, char_limit=char_limit)
        yield _event("pages", f"Got text for {len(pages)}/{len(urls)} pages", fetched=len(pages), requested=len(urls))

        for index, doc in enumerate(documents, start=1):
            url = doc["url"]
            title = doc.get("title") or url
            text = pages.get(url, "")
            doc["content"] = text[:char_limit]
            yield _event(
                "summarize",
                f"[{index}/{len(documents)}] OpenRouter summarizing: {title}",
                index=index,
                total=len(documents),
                url=url,
                title=title,
                chars=len(doc["content"]),
            )
            extracted_events, reason = llm.summarize_page(city, doc, now=now, horizon=horizon)
            if not extracted_events:
                skipped += 1
                yield _event("skip", f"Not saved: {reason}", level="warn", url=url, title=title, reason=reason)
                continue
            for extracted in extracted_events:
                summarized += 1
                yield _event(
                    "summarize",
                    f"LLM accepted event: {extracted.title}",
                    title=extracted.title,
                    starts_at=extracted.starts_at,
                    tags=extracted.tags,
                    estimated_fields=list(extracted.estimated_fields),
                    url=extracted.source_url or url,
                )
                saved, persist_reason = _persist_extracted(db, extracted, city, now, horizon, existing_keys, existing_urls)
                if saved:
                    created += 1
                    yield _event(
                        "saved",
                        f"Wrote to events DB: {extracted.title}",
                        title=extracted.title,
                        city=extracted.city or city,
                        url=extracted.source_url or url,
                    )
                else:
                    skipped += 1
                    yield _event(
                        "skip",
                        f"Not saved: {persist_reason}",
                        level="warn",
                        url=extracted.source_url or url,
                        title=extracted.title,
                        reason=persist_reason,
                    )

    yield _event(
        "done",
        f"Scan finished — created {created}, summarized {summarized}, skipped {skipped}",
        ok=True,
        created=created,
        scanned_docs=scanned_docs,
        summarized=summarized,
        skipped=skipped,
        cities=cities,
        result_count=result_count,
        page_char_limit=char_limit,
    )


def run_scan(db: Session, user: User | None = None) -> dict:
    result = {"ok": False, "created": 0}
    for event in iter_scan(db, user):
        if event.get("stage") in {"done", "error"}:
            result = event
    return result


def _persist_extracted(
    db: Session,
    extracted: llm.ExtractedEvent,
    fallback_city: str,
    now: datetime,
    horizon: datetime,
    existing_keys: set,
    existing_urls: set,
) -> tuple[bool, str]:
    title = extracted.title.strip()
    starts = _naive(extracted.starts_at)
    ends = _naive(extracted.ends_at)
    address = extracted.address.strip()
    city = extracted.city.strip() or fallback_city
    source_url = extracted.source_url.strip() or None
    if not title or starts is None:
        return False, "missing title or unparseable starts_at"
    if ends is None:
        ends = starts + timedelta(hours=2)
    if ends <= starts:
        return False, "end is not after start"
    if starts < now - timedelta(days=1) or starts > horizon:
        return False, "start is outside the next 3 weeks"
    if source_url:
        same = db.query(Event).filter(Event.source_url == source_url, Event.title == title[:200]).first()
        if same:
            return False, "duplicate source_url"
    coords = geocode.geocode_place(address or title, city)
    if coords is None:
        coords = geocode.geocode_place(city, city)
    if coords is None:
        return False, "could not geocode address"
    lat, lng = coords
    key = _dedupe_key(title, starts, lat, lng)
    if key in existing_keys:
        return False, "duplicate title/date/location"
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
    return True, "ok"


def _spam_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if host.endswith(".gov.br") or host.endswith(".gov.np"):
        return True
    if "printable" in path and "calendar" in path:
        return True
    return False
