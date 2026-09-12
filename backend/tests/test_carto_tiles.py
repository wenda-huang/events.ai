import unittest
from unittest.mock import patch

from app.config import Settings
from app.main import public_config
from app.services.carto import append_basemap_key, public_tile_url

TILE = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"


class AppendBasemapKeyTests(unittest.TestCase):
    def test_appends_key_query(self):
        self.assertEqual(append_basemap_key(TILE, "abc123"), f"{TILE}?key=abc123")

    def test_appends_with_existing_query(self):
        url = "https://example.com/tile.png?foo=1"
        self.assertEqual(append_basemap_key(url, "abc"), "https://example.com/tile.png?foo=1&key=abc")

    def test_does_not_duplicate_existing_key(self):
        url = f"{TILE}?key=already"
        self.assertEqual(append_basemap_key(url, "other"), url)

    def test_normalizes_api_key_alias(self):
        url = "https://example.com/tile.png?api_key=already"
        self.assertEqual(append_basemap_key(url, "ignored"), "https://example.com/tile.png?key=already")

    def test_encodes_special_characters(self):
        self.assertEqual(
            append_basemap_key("https://example.com/tile.png", "a+b/c"),
            "https://example.com/tile.png?key=a%2Bb%2Fc",
        )

    def test_strips_bearer_prefix(self):
        self.assertEqual(
            append_basemap_key("https://example.com/tile.png", "Bearer secret"),
            "https://example.com/tile.png?key=secret",
        )

    def test_empty_key_leaves_url_unchanged(self):
        self.assertEqual(append_basemap_key(TILE, "  "), TILE)

    def test_preserves_leaflet_placeholders(self):
        out = append_basemap_key(TILE, "k")
        self.assertIn("{s}", out)
        self.assertIn("{z}", out)
        self.assertIn("{x}", out)
        self.assertIn("{y}", out)
        self.assertIn("{r}", out)


class PublicTileUrlTests(unittest.TestCase):
    def test_uses_configured_key(self):
        def secret(_self, name: str) -> str:
            return {
                "carto_tile_url": TILE,
                "carto_api_key": "from-ini",
            }.get(name, "")

        with patch.object(Settings, "secret", secret):
            self.assertEqual(public_tile_url(), f"{TILE}?key=from-ini")

    def test_public_config_includes_key_on_tile_url(self):
        def secret(_self, name: str) -> str:
            return {
                "carto_api_base_url": "https://gcp-us-east1.api.carto.com",
                "carto_tile_url": TILE,
                "carto_api_key": "map-key",
                "querit_api_key": "",
            }.get(name, "")

        with patch.object(Settings, "secret", secret):
            cfg = public_config()
        self.assertTrue(cfg["has_carto_key"])
        self.assertEqual(cfg["tile_url"], f"{TILE}?key=map-key")


if __name__ == "__main__":
    unittest.main()
