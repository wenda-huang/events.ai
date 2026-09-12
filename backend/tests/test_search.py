import unittest
from types import SimpleNamespace

from app.services.search import MIN_SCORE, expand_query, score_event
from app.serialize import dump_tags


def _event(**kwargs):
    defaults = {
        "title": "Untitled",
        "description": "",
        "address": "",
        "city": "Pittsburgh",
        "tags": dump_tags([]),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class SearchEngineTests(unittest.TestCase):
    def test_empty_query_is_none(self):
        self.assertIsNone(expand_query(""))
        self.assertIsNone(expand_query("   "))

    def test_food_query_matches_food_event(self):
        query = expand_query("food")
        self.assertIsNotNone(query)
        food = _event(title="Strip District Saturday Market", tags=dump_tags(["markets", "food"]))
        tech = _event(title="Oakland Tech Happy Hour", tags=dump_tags(["tech", "networking"]))
        self.assertGreaterEqual(score_event(food, query), MIN_SCORE)
        self.assertGreater(score_event(food, query), score_event(tech, query))

    def test_synonym_expands_to_tag(self):
        query = expand_query("concert")
        self.assertIn("music", query.tags)
        live = _event(title="South Side Live Music Night", tags=dump_tags(["music", "nightlife"]))
        self.assertGreaterEqual(score_event(live, query), MIN_SCORE)

    def test_unrelated_query_stays_below_threshold(self):
        query = expand_query("underwater basket weaving")
        event = _event(title="Phipps After Hours", description="Conservatory rooms and tea.", tags=dump_tags(["art"]))
        self.assertLess(score_event(event, query), MIN_SCORE)


if __name__ == "__main__":
    unittest.main()
