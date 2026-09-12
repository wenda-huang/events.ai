import unittest
from types import SimpleNamespace

from app.services.auto_invite import select_auto_invitees


def user(uid: int, lat: float, lng: float, tags: list[str]) -> SimpleNamespace:
    return SimpleNamespace(id=uid, lat=lat, lng=lng, tags=tags)


class AutoInviteSelectionTests(unittest.TestCase):
    def test_picks_nearby_overlap_and_caps_at_remaining_seats(self):
        event_lat, event_lng = 40.4406, -79.9959
        nearby = user(2, event_lat + 0.01, event_lng, ["food", "tech"])
        better = user(3, event_lat, event_lng, ["food", "music"])
        far = user(4, 34.0522, -118.2437, ["food"])
        no_tags = user(5, event_lat, event_lng, ["sports"])
        host = user(1, event_lat, event_lng, ["food"])
        chosen = select_auto_invitees(
            event_lat=event_lat,
            event_lng=event_lng,
            event_tags={"food", "music"},
            host_id=1,
            people_max=3,
            joined_count=1,
            member_ids={1},
            candidates=[host, nearby, better, far, no_tags],
        )
        self.assertEqual([u.id for u in chosen], [3, 2])

    def test_skips_when_event_has_no_tags_or_is_full(self):
        person = user(2, 40.44, -80.0, ["food"])
        self.assertEqual(
            select_auto_invitees(
                event_lat=40.44,
                event_lng=-80.0,
                event_tags=set(),
                host_id=1,
                people_max=8,
                joined_count=1,
                member_ids={1},
                candidates=[person],
            ),
            [],
        )
        self.assertEqual(
            select_auto_invitees(
                event_lat=40.44,
                event_lng=-80.0,
                event_tags={"food"},
                host_id=1,
                people_max=1,
                joined_count=1,
                member_ids={1},
                candidates=[person],
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
