TAG_DICTIONARY = [
    "music",
    "food",
    "sports",
    "art",
    "tech",
    "outdoors",
    "nightlife",
    "volunteering",
    "workshops",
    "markets",
    "comedy",
    "film",
    "fitness",
    "gaming",
    "networking",
    "community",
]

TAG_SET = set(TAG_DICTIONARY)


def normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in tags:
        tag = raw.strip().lower()
        if tag in TAG_SET and tag not in seen:
            seen.add(tag)
            cleaned.append(tag)
    return cleaned
