import unittest

from app.services.notifications import (
    KIND_AI_INVITE,
    KIND_USER_INVITE,
    invite_message,
    join_message,
    recipient_allows_notifications,
    should_notify_join,
)


class NotificationCopyTests(unittest.TestCase):
    def test_ai_cluster_invite_copy(self):
        title, body, kind = invite_message("Jazz Night", None)
        self.assertEqual(kind, KIND_AI_INVITE)
        self.assertEqual(title, "events.ai invited you")
        self.assertIn("Jazz Night", body)

    def test_user_invite_names_the_inviter(self):
        title, body, kind = invite_message("Jazz Night", "Maya")
        self.assertEqual(kind, KIND_USER_INVITE)
        self.assertEqual(title, "Maya invited you")
        self.assertIn("Maya", body)
        self.assertIn("Jazz Night", body)

    def test_join_copy(self):
        title, body = join_message("Jazz Night", "Sam")
        self.assertEqual(title, "Sam joined your event")
        self.assertIn("Jazz Night", body)

    def test_host_is_not_notified_when_they_join_their_own_event(self):
        self.assertFalse(should_notify_join(3, 3))
        self.assertFalse(should_notify_join(None, 9))
        self.assertTrue(should_notify_join(3, 9))

    def test_toggle_skips_disabled_recipients(self):
        self.assertTrue(recipient_allows_notifications(type("U", (), {"notifications_enabled": True})()))
        self.assertFalse(recipient_allows_notifications(type("U", (), {"notifications_enabled": False})()))
        self.assertFalse(recipient_allows_notifications(None))
