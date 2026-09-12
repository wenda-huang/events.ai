import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import config


class ConfigIniTests(unittest.TestCase):
    def test_percent_encoded_tile_url_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            ini = Path(tmp) / "config.ini"
            ini.write_text(
                "[carto]\n"
                "tile_url = https://example.com/%7Bz%7D/%7Bx%7D/%7By%7D.png\n",
                encoding="utf-8",
            )
            with patch.object(config, "_ini_paths", return_value=[ini]):
                values = config.ini_values()
        self.assertEqual(
            values["carto_tile_url"],
            "https://example.com/%7Bz%7D/%7Bx%7D/%7By%7D.png",
        )
