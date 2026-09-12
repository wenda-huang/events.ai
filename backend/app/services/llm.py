import json
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import settings
from app.tags import TAG_DICTIONARY, normalize_tags

EstimatedField = Literal["people_min", "people_max", "cost_estimate", "ends_at"]

SYSTEM_PROMPT = """You are an event summarizer for a meetup map.

You are given one web page (title, URL, snippet, and extracted page text) plus the city the user is in.
Your job is to decide if the page describes a specific upcoming real-world event people can attend, then summarize that event.

Rules:
- Write a clear, concise description of what the event is, when it happens, and why someone would go.
- Only set is_event=true if this is a specific attendable event in or near the given city (a concert, market, meetup, class, game, festival, screening, etc.).
- If the page is a generic city guide, news article, directory, or not about a dated event, set is_event=false and fill remaining fields with empty strings / zeros / empty arrays.
- Title, description, address, city, starts_at, and source_url must come from the page when is_event is true. Do not invent a fake event.
- starts_at and ends_at must be ISO-8601 datetimes. If the page has a date but no time, use a reasonable local time.
- tags must be chosen only from the allowed list.
- people_min, people_max, and cost_estimate are optional details. If the page does not state them, guess a realistic value AND list that field name in estimated_fields.
- If the page does not state an end time, estimate ends_at as a few hours after start and add "ends_at" to estimated_fields.
- Never put title, description, address, city, or starts_at in estimated_fields. If those cannot be taken from the page, is_event must be false.
- source_url must be the page URL you were given.
"""


class ExtractedEvent(BaseModel):
    is_event: bool
    title: str
    description: str
    address: str
    city: str
    starts_at: str = Field(description="ISO-8601 datetime")
    ends_at: str = Field(description="ISO-8601 datetime")
    people_min: int
    people_max: int
    cost_estimate: str
    tags: list[str]
    estimated_fields: list[EstimatedField]
    source_url: str

    @field_validator("tags")
    @classmethod
    def known_tags(cls, value: list[str]) -> list[str]:
        return normalize_tags(value)


def event_json_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "is_event",
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
            "is_event": {
                "type": "boolean",
                "description": "True only if this page is a specific upcoming event people can attend in the given city.",
            },
            "title": {"type": "string"},
            "description": {"type": "string", "description": "Short summary of the event."},
            "address": {"type": "string"},
            "city": {"type": "string"},
            "starts_at": {"type": "string", "description": "ISO-8601 datetime"},
            "ends_at": {"type": "string", "description": "ISO-8601 datetime"},
            "people_min": {"type": "integer"},
            "people_max": {"type": "integer"},
            "cost_estimate": {"type": "string", "description": "Free, a price, or a range such as $10-$25"},
            "tags": {
                "type": "array",
                "items": {"type": "string", "enum": TAG_DICTIONARY},
            },
            "estimated_fields": {
                "type": "array",
                "description": "Fields that were guessed because the page did not state them.",
                "items": {
                    "type": "string",
                    "enum": ["people_min", "people_max", "cost_estimate", "ends_at"],
                },
            },
            "source_url": {"type": "string"},
        },
    }


def summarize_page(city: str, document: dict) -> ExtractedEvent | None:
    api_key = settings.llm_api_key()
    if not api_key:
        return None
    user_payload = {
        "city": city,
        "allowed_tags": TAG_DICTIONARY,
        "page": {
            "title": document.get("title") or "",
            "url": document.get("url") or "",
            "snippet": document.get("snippet") or "",
            "site_name": document.get("site_name") or "",
            "text": document.get("content") or "",
        },
    }
    body = {
        "model": settings.llm_model(),
        "temperature": 0.5,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "event_summary",
                "strict": True,
                "schema": event_json_schema(),
            },
        },
        "provider": {"require_parameters": True},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "events.ai",
    }
    url = settings.llm_base_url() + "/chat/completions"
    data = _post(url, headers, body)
    if data is None:
        body.pop("provider", None)
        data = _post(url, headers, body)
    if data is None:
        body["response_format"] = {"type": "json_object"}
        data = _post(url, headers, body)
    if data is None:
        return None
    raw = _message_json(data)
    if raw is None:
        return None
    return validate_event(raw)


def validate_event(raw: object) -> ExtractedEvent | None:
    if not isinstance(raw, dict):
        return None
    try:
        event = ExtractedEvent.model_validate(raw)
    except ValidationError:
        return None
    if not event.is_event:
        return None
    if event.title.strip() and event.starts_at.strip() and event.source_url.strip():
        return event
    return None


def _post(url: str, headers: dict, body: dict) -> dict | None:
    try:
        with httpx.Client(timeout=90) as client:
            res = client.post(url, headers=headers, json=body)
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPError:
        return None
    return data if isinstance(data, dict) else None


def _message_json(data: dict) -> dict | None:
    try:
        message = data["choices"][0]["message"]
        parsed = message.get("parsed")
        if isinstance(parsed, dict):
            return parsed
        content = message.get("content") or ""
        return json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None
