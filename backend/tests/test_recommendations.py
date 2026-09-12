import unittest

from app.routers.events import interest_overlap, recommend_sort_key, search_and_distance_origins


class InterestRankingTests(unittest.TestCase):
    def test_overlap_is_intersection_size(self):
        self.assertEqual(interest_overlap({"food", "tech"}, {"tech", "art"}), 1)
        self.assertEqual(interest_overlap({"food"}, {"tech"}), 0)
        self.assertEqual(interest_overlap(set(), {"food"}), 0)

    def test_zero_overlap_events_are_kept_and_sorted_last(self):
        events = [
            {"title": "Far tech", "tag_overlap": interest_overlap({"food"}, {"tech"}), "distance_mi": 0.5, "starts_at": "2026-09-13"},
            {"title": "Nearby food", "tag_overlap": interest_overlap({"food"}, {"food"}), "distance_mi": 1.2, "starts_at": "2026-09-14"},
            {"title": "Closer food", "tag_overlap": interest_overlap({"food"}, {"food", "community"}), "distance_mi": 0.2, "starts_at": "2026-09-15"},
        ]
        ranked = sorted(events, key=recommend_sort_key)
        self.assertEqual([e["title"] for e in ranked], ["Closer food", "Nearby food", "Far tech"])

    def test_radius_center_can_differ_from_distance_origin(self):
        search, distance = search_and_distance_origins(40.44, -80.0, 40.5, -79.9)
        self.assertEqual(search, (40.44, -80.0))
        self.assertEqual(distance, (40.5, -79.9))

    def test_distance_origin_defaults_to_search_center(self):
        search, distance = search_and_distance_origins(40.44, -80.0)
        self.assertEqual(search, distance)


if __name__ == "__main__":
    unittest.main()
