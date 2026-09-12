import json
import re

import httpx

from app.config import settings
from app.tags import TAG_DICTIONARY

EXTRACT_PROMPT = """You extract real-world meetup/events happening in Pittsburgh, Pennsylvania.

Return ONLY a JSON array. Each item must be:
{{
  "title": string,
  "description": string,
  "address": string,
  "city": "Pittsburgh",
  "starts_at": ISO-8601 datetime,
  "ends_at": ISO-8601 datetime,
  "people_min": number,
  "people_max": number,
  "cost_estimate": string,
  "tags": array of tags from {tags},
  "source_url": string
}}

Rules:
- Only include events that are clearly in or immediately around Pittsburgh.
- Skip items without a usable date/time or place.
- Prefer the next 4 weeks.
- people_min 2-8, people_max 8-40 unless the source says otherwise.
- If cost is unknown use "Free" or a reasonable estimate.
- tags must be from the allowed list only.
"""


def extract_events(documents: list[dict]) -> list[dict]:
    api_key = settings.secret("openai_api_key")
    if not api_key or not documents:
        return []
    blob = json.dumps(documents, ensure_ascii=False)[:20000]
    prompt = EXTRACT_PROMPT.format(tags=", ".join(TAG_DICTIONARY))
    body = {
        "model": settings.secret("openai_model") or settings.openai_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": blob},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = (settings.secret("openai_base_url") or settings.openai_base_url).rstrip("/") + "/chat/completions"
    try:
        with httpx.Client(timeout=60) as client:
            res = client.post(url, headers=headers, json=body)
            res.raise_for_status()
            data = res.json()
            content = data["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError):
        return []
    return _parse_json_array(content)


def _parse_json_array(content: str) -> list[dict]:
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\[.*\])\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    return [item for item in parsed if isinstance(item, dict)]
