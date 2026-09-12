import unittest

from app.services.geocode import is_city_level_address, looks_specific_address, lookup_place, prefer_address
from app.services.mapbox import _hit_from_payload


class GeocodeHelperTests(unittest.TestCase):
    def test_city_name_is_generic(self):
        self.assertTrue(is_city_level_address("Pittsburgh", "Pittsburgh", "Pittsburgh, PA"))
        self.assertTrue(is_city_level_address("Pittsburgh, PA", "Pittsburgh", "Pittsburgh, PA"))
        self.assertTrue(is_city_level_address("", "Pittsburgh", "Pittsburgh, PA"))

    def test_venue_is_not_generic(self):
        self.assertFalse(is_city_level_address("Stage AE, Pittsburgh, PA", "Pittsburgh", "Pittsburgh, PA"))
        self.assertTrue(looks_specific_address("401 W Van Buren St, Phoenix, AZ"))

    def test_prefer_keeps_street_address(self):
        self.assertEqual(
            prefer_address("401 W Van Buren St", "Some Venue, Phoenix"),
            "401 W Van Buren St",
        )
        self.assertEqual(
            prefer_address("Stage AE - Pittsburgh, PA", "Stage AE, Chuck Noll Way, Pittsburgh, Pennsylvania"),
            "Stage AE, Chuck Noll Way, Pittsburgh, Pennsylvania",
        )

    def test_city_level_skips_geocode(self):
        self.assertIsNone(lookup_place("Pittsburgh, PA", "Pittsburgh, PA"))

    def test_mapbox_payload_reads_coords_and_address(self):
        hit = _hit_from_payload(
            {
                "features": [
                    {
                        "geometry": {"coordinates": [-80.01229, 40.44611]},
                        "properties": {"full_address": "Stage AE, Chuck Noll Way, Pittsburgh, Pennsylvania"},
                    }
                ]
            }
        )
        self.assertIsNotNone(hit)
        lat, lng, address = hit
        self.assertAlmostEqual(lat, 40.44611)
        self.assertAlmostEqual(lng, -80.01229)
        self.assertIn("Stage AE", address)


if __name__ == "__main__":
    unittest.main()

