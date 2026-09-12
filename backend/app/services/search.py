from __future__ import annotations

import re
from dataclasses import dataclass

from app.serialize import parse_tags
from app.tags import TAG_SET

MIN_SCORE = 1.0

_TOKEN = re.compile(r"[a-z0-9]+")

SYNONYMS: dict[str, frozenset[str]] = {
    "music": frozenset({"concert", "band", "live", "dj", "gig", "song", "jazz", "choir", "orchestra"}),
    "food": frozenset({"eat", "dinner", "brunch", "lunch", "restaurant", "cafe", "coffee", "cuisine", "tasting", "produce"}),
    "sports": frozenset({"game", "match", "team", "stadium", "ball", "league"}),
    "art": frozenset({"gallery", "exhibit", "museum", "paint", "studio", "design"}),
    "tech": frozenset({"startup", "hack", "software", "coding", "developer", "ai", "computer"}),
    "outdoors": frozenset({"hike", "trail", "park", "river", "walk", "nature", "garden"}),
    "nightlife": frozenset({"bar", "club", "drinks", "evening", "late", "party"}),
    "volunteering": frozenset({"volunteer", "service", "nonprofit", "giveback", "help"}),
    "workshops": frozenset({"class", "lesson", "learn", "workshop", "make", "craft"}),
    "markets": frozenset({"market", "vendor", "farmers", "bazaar", "stall", "shop"}),
    "comedy": frozenset({"standup", "improv", "funny", "laugh", "joke"}),
    "film": frozenset({"movie", "cinema", "screening", "theater", "watch"}),
    "fitness": frozenset({"yoga", "run", "workout", "gym", "exercise"}),
    "gaming": frozenset({"game", "games", "play", "esports", "boardgame"}),
    "networking": frozenset({"meetup", "mixer", "professionals", "career", "connect"}),
    "community": frozenset({"neighborhood", "local", "neighbors", "civic", "town"}),
}

_TOKEN_TO_TAGS: dict[str, set[str]] = {}
for _tag, _words in SYNONYMS.items():
    _TOKEN_TO_TAGS.setdefault(_tag, set()).add(_tag)
    for _word in _words:
        _TOKEN_TO_TAGS.setdefault(_word, set()).add(_tag)


@dataclass(frozen=True)
class SearchQuery:
    raw: str
    tokens: tuple[str, ...]
    tags: frozenset[str]
    expanded: frozenset[str]


def expand_query(q: str) -> SearchQuery | None:
    raw = (q or "").strip().lower()
    if not raw:
        return None
    tokens = tuple(tok for tok in _TOKEN.findall(raw) if len(tok) > 1)
    if not tokens and not raw:
        return None
    tags: set[str] = set()
    expanded: set[str] = set(tokens)
    for token in tokens:
        if token in TAG_SET:
            tags.add(token)
        related = _TOKEN_TO_TAGS.get(token)
        if related:
            tags.update(related)
            expanded.update(related)
            for tag in related:
                expanded.update(SYNONYMS.get(tag, ()))
    return SearchQuery(raw=raw, tokens=tokens, tags=frozenset(tags), expanded=frozenset(expanded))


def score_event(event, query: SearchQuery) -> float:
    title = (event.title or "").lower()
    description = (event.description or "").lower()
    place = f"{event.address or ''} {event.city or ''}".lower()
    tags = {tag.lower() for tag in parse_tags(event.tags)}
    score = 0.0

    if query.raw and query.raw in title:
        score += 5.0
    elif query.raw and query.raw in description:
        score += 2.0
    elif query.raw and query.raw in place:
        score += 2.0

    for token in query.tokens:
        if token in title.split() or f" {token}" in f" {title}":
            score += 2.5
        elif token in description:
            score += 1.0
        elif token in place:
            score += 1.2

    score += 3.0 * len(query.tags & tags)
    score += 1.5 * len((query.expanded & tags) - query.tags)
    return score
