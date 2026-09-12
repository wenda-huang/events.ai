from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from app.config import settings

QUERIT_SEARCH = "https://api.querit.ai/v1/search"
QUERIT_CONTENTS = "https://api.querit.ai/v1/contents"


def search_city(city: str, count: int = 100) -> list[dict]:
    queries = [
        f"upcoming events concerts festivals meetups in {city} this week this weekend",
        f"{city} event tickets venue show this week",
        f"site:eventbrite.com/e OR site:allevents.in {city} events",
    ]
    per_query = max(10, count // len(queries) + 8)
    merged: list[dict] = []
    seen: set[str] = set()
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        for hits in pool.map(lambda query: search(query, count=per_query), queries):
            for item in hits:
                url = item.get("url") or ""
                if not url or url in seen:
                    continue
                seen.add(url)
                merged.append(item)
                if len(merged) >= count:
                    return merged[:count]
    return merged[:count]


def search(query: str, count: int = 100) -> list[dict]:
    if not settings.secret("querit_api_key"):
        return []
    headers = {
        "Authorization": f"Bearer {settings.secret('querit_api_key')}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "query": query,
        "count": count,
        "date_range": "w2",
        "languages": ["english"],
    }
    try:
        with httpx.Client(timeout=25) as client:
            res = client.post(QUERIT_SEARCH, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPError:
        return []
    results = data.get("results", {})
    items = results.get("result") if isinstance(results, dict) else results
    if not isinstance(items, list):
        return []
    cleaned = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cleaned.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "snippet": item.get("snippet") or "",
                "site_name": item.get("site_name") or "",
            }
        )
    return cleaned[:count]


def fetch_contents(urls: list[str], char_limit: int = 4000) -> dict[str, str]:
    key = settings.secret("querit_api_key")
    if not key or not urls:
        return {}
    batch_size = settings.contents_batch()
    workers = min(settings.fetch_concurrency(), max(1, (len(urls) + batch_size - 1) // batch_size))
    batches = [urls[start : start + batch_size] for start in range(0, len(urls), batch_size)]
    pages: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_fetch_batch, batch, char_limit) for batch in batches]
        for future in as_completed(futures):
            pages.update(future.result())
    return pages


def _fetch_batch(urls: list[str], char_limit: int) -> dict[str, str]:
    key = settings.secret("querit_api_key")
    if not key or not urls:
        return {}
    crawl_timeout = settings.crawl_timeout()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        with httpx.Client(timeout=crawl_timeout + 10) as client:
            res = client.post(
                QUERIT_CONTENTS,
                headers=headers,
                json={"urls": urls, "format": "text", "crawlTimeout": crawl_timeout},
            )
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPError:
        return {}
    items = data.get("results") or data.get("contents") or data
    if isinstance(items, dict):
        items = items.get("result") or items.get("contents") or []
    if not isinstance(items, list):
        return {}
    pages: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or ""
        text = item.get("text") or item.get("markdown") or item.get("content") or ""
        if url and text:
            pages[url] = str(text)[:char_limit]
    return pages
