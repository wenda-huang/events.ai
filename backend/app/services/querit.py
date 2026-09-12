import httpx

from app.config import settings

QUERIT_SEARCH = "https://api.querit.ai/v1/search"
QUERIT_CONTENTS = "https://api.querit.ai/v1/contents"


def search_city(city: str, count: int = 50) -> list[dict]:
    query = f"upcoming local events concerts festivals meetups in {city} in the next two weeks"
    return search(query, count=count)


def search(query: str, count: int = 50) -> list[dict]:
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
        "date_range": "w4",
        "languages": ["english"],
    }
    try:
        with httpx.Client(timeout=45) as client:
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
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    pages: dict[str, str] = {}
    for chunk_start in range(0, len(urls), 8):
        batch = urls[chunk_start : chunk_start + 8]
        try:
            with httpx.Client(timeout=60) as client:
                res = client.post(
                    QUERIT_CONTENTS,
                    headers=headers,
                    json={"urls": batch, "format": "text", "crawlTimeout": 30},
                )
                res.raise_for_status()
                data = res.json()
        except httpx.HTTPError:
            continue
        items = data.get("results") or data.get("contents") or data
        if isinstance(items, dict):
            items = items.get("result") or items.get("contents") or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or ""
            text = item.get("text") or item.get("markdown") or item.get("content") or ""
            if url and text:
                pages[url] = str(text)[:char_limit]
    return pages
