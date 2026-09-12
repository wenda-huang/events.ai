from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from collections.abc import Iterator
import logging

from sqlalchemy.orm import Session

from app.cities import implemented_cities, match_city
from app.config import settings
from app.models import City, Event, User
from app.serialize import dump_tags
from app.services import geocode, llm, querit

log = logging.getLogger("events.scan")
COMMIT_EVERY = 20


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


def iter_scan(db: Session, user: User | None = None) -> Iterator[dict]:
    del user
    if not settings.secret("querit_api_key"):
        yield _event("error", "QUERIT_API_KEY missing", level="error", ok=False, created=0)
        return
    if not settings.llm_api_key():
        yield _event("error", "OpenRouter API key missing — add it under [openrouter] in config.ini", level="error", ok=False, created=0)
        return

    cities = implemented_cities(db)
    if not cities:
        yield _event("error", "No implemented cities in the cities table", level="error", ok=False, created=0)
        return

    char_limit = settings.page_char_limit()
    result_count = settings.result_count()
    search_workers = min(settings.search_concurrency(), len(cities))
    fetch_workers = settings.fetch_concurrency()
    llm_concurrency = settings.llm_concurrency()
    crawl_timeout = settings.crawl_timeout()
    created = 0
    scanned_docs = 0
    summarized = 0
    skipped = 0
    pending_commits = 0
    city_labels = [city.label for city in cities]

    yield _event(
        "start",
        "Starting event scan pipeline",
        cities=city_labels,
        result_count=result_count,
        page_char_limit=char_limit,
        search_workers=search_workers,
        fetch_workers=fetch_workers,
        llm_concurrency=llm_concurrency,
        crawl_timeout=crawl_timeout,
        model=settings.llm_model(),
        provider=",".join(settings.llm_providers()) or "auto",
        reasoning=settings.llm_reasoning(),
    )

    existing_urls = {e.source_url for e in db.query(Event).filter(Event.source_url.isnot(None)).all()}
    existing_keys = {_dedupe_key(e.title, e.starts_at, e.lat, e.lng) for e in db.query(Event).all()}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    horizon = now + timedelta(days=21)

    queued: list[tuple[City, list[dict]]] = []
    yield _event("querit", f"Searching {len(cities)} cities in parallel", cities=city_labels, workers=search_workers)
    with ThreadPoolExecutor(max_workers=search_workers) as pool:
        futures = {pool.submit(querit.search_city, city.label, result_count): city for city in cities}
        for future in as_completed(futures):
            city = futures[future]
            try:
                hits = future.result() or []
            except Exception as exc:
                skipped += 1
                yield _event("skip", f"Querit search failed for {city.label}", level="warn", city=city.label, reason=str(exc))
                queued.append((city, []))
                continue
            yield _event("querit", f"Querit returned {len(hits)} hits", count=len(hits), city=city.label)
            documents = []
            for item in hits:
                url = item.get("url") or ""
                if not url:
                    continue
                if _spam_url(url):
                    skipped += 1
                    yield _event("skip", "Spam or clone calendar URL", level="warn", url=url, title=item.get("title") or "", city=city.label)
                    continue
                if url in existing_urls:
                    skipped += 1
                    yield _event("skip", "Already in database", level="warn", url=url, title=item.get("title") or "", city=city.label)
                    continue
                existing_urls.add(url)
                documents.append(item)
            queued.append((city, documents))
            scanned_docs += len(documents)

    yield _event(
        "querit",
        f"Finished Querit for {len(cities)} cities — {scanned_docs} pages to summarize",
        cities=city_labels,
        count=scanned_docs,
    )

    work: list[tuple[City, dict]] = [(city, doc) for city, documents in queued for doc in documents]
    urls = [doc["url"] for _, doc in work]
    yield _event(
        "pages",
        f"Fetching page text for {len(urls)} URLs in parallel",
        count=len(urls),
        char_limit=char_limit,
        workers=fetch_workers,
        crawl_timeout=crawl_timeout,
    )
    pages = querit.fetch_contents(urls, char_limit=char_limit)
    yield _event("pages", f"Got text for {len(pages)}/{len(urls)} pages", fetched=len(pages), requested=len(urls))

    for _, doc in work:
        doc["content"] = pages.get(doc["url"], "")[:char_limit]

    for item in _iter_llm_results(work, now, horizon):
        if isinstance(item, dict):
            yield item
            continue
        _kind, index, city, doc, extracted_events, reason = item
        url = doc["url"]
        title = doc.get("title") or url
        yield _event(
            "summarize",
            f"[{index}/{len(work)}] LLM finished: {title}",
            index=index,
            total=len(work),
            url=url,
            title=title,
            chars=len(doc.get("content") or ""),
            city=city.label,
        )
        if not extracted_events:
            skipped += 1
            yield _event("skip", f"Not saved: {reason}", level="warn", url=url, title=title, reason=reason, city=city.label)
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
                city=city.label,
            )
            saved, persist_reason = _persist_extracted(
                db, extracted, city, cities, now, horizon, existing_keys, existing_urls
            )
            if saved:
                created += 1
                pending_commits += 1
                if pending_commits >= COMMIT_EVERY:
                    db.commit()
                    pending_commits = 0
                yield _event(
                    "saved",
                    f"Wrote to events DB: {extracted.title}",
                    title=extracted.title,
                    city=city.label,
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
                    city=city.label,
                )

    if pending_commits:
        db.commit()

    yield _event(
        "done",
        f"Scan finished — created {created}, summarized {summarized}, skipped {skipped}",
        ok=True,
        created=created,
        scanned_docs=scanned_docs,
        summarized=summarized,
        skipped=skipped,
        cities=city_labels,
        result_count=result_count,
        page_char_limit=char_limit,
        search_workers=search_workers,
        fetch_workers=fetch_workers,
        llm_concurrency=llm_concurrency,
        crawl_timeout=crawl_timeout,
    )


def _iter_llm_results(work: list[tuple[City, dict]], now: datetime, horizon: datetime):
    if not work:
        return
    concurrency = min(settings.llm_concurrency(), len(work))
    yield _event(
        "summarize",
        f"Summarizing {len(work)} pages with {settings.llm_model()} ({concurrency} at a time)",
        count=len(work),
        workers=concurrency,
        model=settings.llm_model(),
        provider=",".join(settings.llm_providers()) or "auto",
    )

    def summarize(item: tuple[int, City, dict]):
        index, city, doc = item
        extracted, reason = llm.summarize_page(city.label, doc, now=now, horizon=horizon)
        return index, city, doc, extracted, reason

    jobs = [(index, city, doc) for index, (city, doc) in enumerate(work, start=1)]
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(summarize, job) for job in jobs]
        for future in as_completed(futures):
            index, city, doc, extracted, reason = future.result()
            yield ("result", index, city, doc, extracted, reason)


def run_scan(db: Session, user: User | None = None) -> dict:
    result = {"ok": False, "created": 0}
    for event in iter_scan(db, user):
        if event.get("stage") in {"done", "error"}:
            result = event
    return result


def _persist_extracted(
    db: Session,
    extracted: llm.ExtractedEvent,
    fallback_city: City,
    cities: list[City],
    now: datetime,
    horizon: datetime,
    existing_keys: set,
    existing_urls: set,
) -> tuple[bool, str]:
    title = extracted.title.strip()
    starts = _naive(extracted.starts_at)
    ends = _naive(extracted.ends_at)
    address = extracted.address.strip()
    city_row = match_city(cities, extracted.city) if extracted.city.strip() else None
    city_row = city_row or fallback_city
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
    hit = geocode.lookup_place(address, city_row.label, proximity=(city_row.lat, city_row.lng))
    if hit is None:
        lat, lng = city_row.lat, city_row.lng
    else:
        lat, lng = hit.lat, hit.lng
        address = geocode.prefer_address(address, hit.address)
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
            city=city_row.name,
            city_id=city_row.id,
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
    db.flush()
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
