import unittest
from datetime import datetime, timezone

from app.config import settings
from app.services.llm import page_chat_body, parse_events


class LlmChatTests(unittest.TestCase):
    def test_default_model_and_provider(self):
        self.assertEqual(settings.llm_model(), "inception/mercury-2.5")
        self.assertEqual(settings.llm_providers(), ["inception"])

    def test_chat_body_is_regular_completion(self):
        now = datetime(2026, 9, 13, tzinfo=timezone.utc)
        body = page_chat_body(
            "Pittsburgh, PA",
            {"title": "Jazz", "url": "https://example.com/jazz", "content": "Jazz tonight"},
            now,
            now,
        )
        self.assertIn("messages", body)
        self.assertNotIn("endpoint", body)
        self.assertNotIn("requests", body)
        self.assertEqual(body["provider"]["only"], ["inception"])
        self.assertNotIn("reasoning", body)

    def test_parse_events_from_page(self):
        events, reason = parse_events(
            {
                "events": [
                    {
                        "title": "Jazz Night",
                        "description": "",
                        "address": "Main St",
                        "city": "Pittsburgh",
                        "starts_at": "2026-09-13T20:00:00",
                        "ends_at": "2026-09-13T22:00:00",
                        "people_min": 10,
                        "people_max": 40,
                        "cost_estimate": "$15",
                        "tags": ["music"],
                        "estimated_fields": [],
                        "source_url": "https://example.com/jazz",
                    }
                ]
            },
            page_url="https://example.com/jazz",
            title="Jazz Night",
        )
        self.assertEqual(reason, "ok")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Jazz Night")

    def test_parse_events_empty_page(self):
        events, reason = parse_events({"events": []}, page_url="https://example.com", title="none")
        self.assertEqual(events, [])
        self.assertEqual(reason, "no in-window events on page")


if __name__ == "__main__":
    unittest.main()
