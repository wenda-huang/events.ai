import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import settings
from app.tags import TAG_DICTIONARY, normalize_tags

log = logging.getLogger("events.llm")

EstimatedField = Literal["people_min", "people_max", "cost_estimate", "ends_at"]
ESTIMATED_ALLOWED = {"people_min", "people_max", "cost_estimate", "ends_at"}

SYSTEM_PROMPT = """You extract attendable real-world events for a city meetup map.

You get one web page (title, URL, snippet, page text), the city, today's date, and a date window.

Return every specific event listed on the page that is in or near that city AND starts inside the date window.
Directory, calendar, Ticketmaster, Eventbrite search, and “things to do” pages should still yield the individual events they list.

Rules:
- Prefer events with a clear title and start date/time from the page. Do not invent events.
- If the page is a single event, return that one event.
- If the page lists many events, return up to 8 that fall in the date window. Skip undated or out-of-window items.
- If nothing on the page is a dated event in that city and window, return an empty events array.
- starts_at and ends_at must be ISO-8601 datetimes. If a date has no time, pick a reasonable local time.
- tags must be chosen only from the allowed list.
- people_min, people_max, and cost_estimate: if the page does not state them, guess and list those names in estimated_fields.
- If there is no end time, estimate ends_at a few hours after start and add "ends_at" to estimated_fields.
- estimated_fields may only contain people_min, people_max, cost_estimate, or ends_at.
- source_url should be a per-event URL when the page gives one; otherwise use the page URL.
- address must be the venue and street when the page has them (e.g. "Stage AE, 400 North Shore Dr"). Never use only the city name if a venue exists.
"""


class ExtractedEvent(BaseModel):
    title: str
    description: str = ""
    address: str = ""
    city: str = ""
    starts_at: str = Field(description="ISO-8601 datetime")
    ends_at: str = ""
    people_min: int = 10
    people_max: int = 80
    cost_estimate: str = "Unknown"
    tags: list[str] = []
    estimated_fields: list[EstimatedField] = []
    source_url: str = ""

    @field_validator("tags", mode="before")
    @classmethod
    def known_tags(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return normalize_tags([str(item) for item in value])

    @field_validator("estimated_fields", mode="before")
    @classmethod
    def known_estimated(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if item in ESTIMATED_ALLOWED]

    @field_validator("people_min", "people_max", mode="before")
    @classmethod
    def as_int(cls, value: object) -> int:
        if isinstance(value, bool):
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            match = re.search(r"\d+", value)
            return int(match.group()) if match else 0
        return 0

    @field_validator(
        "title",
        "description",
        "address",
        "city",
        "starts_at",
        "ends_at",
        "cost_estimate",
        "source_url",
        mode="before",
    )
    @classmethod
    def as_str(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()


def event_item_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "title",
            "description",
            "address",
            "city",
            "starts_at",
            "ends_at",
            "people_min",
            "people_max",
            "cost_estimate",
            "tags",
            "estimated_fields",
            "source_url",
        ],
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "address": {"type": "string"},
            "city": {"type": "string"},
            "starts_at": {"type": "string", "description": "ISO-8601 datetime"},
            "ends_at": {"type": "string", "description": "ISO-8601 datetime"},
            "people_min": {"type": "integer"},
            "people_max": {"type": "integer"},
            "cost_estimate": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string", "enum": TAG_DICTIONARY}},
            "estimated_fields": {
                "type": "array",
                "items": {"type": "string", "enum": ["people_min", "people_max", "cost_estimate", "ends_at"]},
            },
            "source_url": {"type": "string"},
        },
    }


def page_json_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["events"],
        "properties": {
            "events": {
                "type": "array",
                "maxItems": 8,
                "items": event_item_schema(),
            }
        },
    }


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.llm_api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "events.ai",
    }


def _page_user_payload(city: str, document: dict, now: datetime, horizon: datetime) -> dict:
    return {
        "city": city,
        "today": now.date().isoformat(),
        "window_start": now.isoformat(),
        "window_end": horizon.isoformat(),
        "allowed_tags": TAG_DICTIONARY,
        "page": {
            "title": document.get("title") or "",
            "url": document.get("url") or "",
            "snippet": document.get("snippet") or "",
            "site_name": document.get("site_name") or "",
            "text": document.get("content") or "",
        },
    }


def page_chat_body(city: str, document: dict, now: datetime, horizon: datetime) -> dict:
    body = {
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(_page_user_payload(city, document, now, horizon), ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "page_events",
                "strict": True,
                "schema": page_json_schema(),
            },
        },
        "provider": settings.llm_provider_prefs(require_parameters=False),
    }
    if settings.llm_reasoning() != "none":
        body["reasoning"] = {"effort": settings.llm_reasoning()}
    return body


def summarize_page(
    city: str,
    document: dict,
    *,
    now: datetime | None = None,
    horizon: datetime | None = None,
) -> tuple[list[ExtractedEvent], str]:
    api_key = settings.llm_api_key()
    if not api_key:
        return [], "no OpenRouter key"
    url = document.get("url") or ""
    title = document.get("title") or url
    now = now or datetime.now(timezone.utc)
    horizon = horizon or (now + timedelta(days=21))
    log.info(
        "Summarizing %s (%s chars) city=%s model=%s provider=%s reasoning=%s",
        url,
        len(document.get("content") or ""),
        city,
        settings.llm_model(),
        ",".join(settings.llm_providers()) or "auto",
        settings.llm_reasoning(),
    )
    body = page_chat_body(city, document, now, horizon)
    body["model"] = settings.llm_model()
    endpoint = settings.llm_base_url() + "/chat/completions"
    data = _post(endpoint, _headers(), body)
    if data is None:
        body["response_format"] = {"type": "json_object"}
        data = _post(endpoint, _headers(), body)
    if data is None:
        return [], "OpenRouter request failed"
    raw = _message_json(data)
    if raw is None:
        return [], "invalid JSON from model"
    return parse_events(raw, page_url=url, title=title)


def parse_events(raw: object, page_url: str = "", title: str = "") -> tuple[list[ExtractedEvent], str]:
    items: list[object] = []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("events"), list):
            items = raw["events"]
        elif raw.get("title") or raw.get("starts_at"):
            if raw.get("is_event") is False:
                items = []
            else:
                items = [raw]
    accepted: list[ExtractedEvent] = []
    last_reason = "no in-window events on page"
    for item in items[:8]:
        event, reason = validate_event(item, page_url=page_url, title=title)
        if event:
            accepted.append(event)
        else:
            last_reason = reason
    if accepted:
        return accepted, "ok"
    return [], last_reason


def validate_event(raw: object, page_url: str = "", title: str = "") -> tuple[ExtractedEvent | None, str]:
    if not isinstance(raw, dict):
        return None, "model output was not an object"
    raw.pop("is_event", None)
    try:
        event = ExtractedEvent.model_validate(raw)
    except ValidationError as exc:
        log.warning("Schema validation failed for %s: %s", title or "page", exc.error_count())
        return None, f"schema validation failed ({exc.error_count()} errors)"
    if not event.source_url.strip():
        event.source_url = page_url
    if event.title.strip() and event.starts_at.strip() and event.source_url.strip():
        return event, "ok"
    return None, "missing title, starts_at, or source_url"


def _post(url: str, headers: dict, body: dict) -> dict | None:
    try:
        with httpx.Client(timeout=45) as client:
            res = client.post(url, headers=headers, json=body)
            if res.status_code >= 400:
                log.warning("OpenRouter HTTP %s: %s", res.status_code, res.text[:400])
                return None
            data = res.json()
    except httpx.HTTPError as exc:
        log.warning("OpenRouter request error: %s", exc)
        return None
    return data if isinstance(data, dict) else None


def _message_json(data: dict) -> dict | list | None:
    try:
        message = data["choices"][0]["message"]
        parsed = message.get("parsed")
        if isinstance(parsed, (dict, list)):
            return parsed
        return _loads_json(_flatten_content(message.get("content")))
    except (KeyError, IndexError, TypeError):
        return None


def _flatten_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    return ""


def _loads_json(content: str) -> dict | list | None:
    text = content.strip()
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, (dict, list)) else None
    except json.JSONDecodeError:
        starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
        if not starts:
            return None
        try:
            data = json.loads(text[min(starts) :])
            return data if isinstance(data, (dict, list)) else None
        except json.JSONDecodeError:
            return None
