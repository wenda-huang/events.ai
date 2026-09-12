import unittest
from types import SimpleNamespace

from app.cities import match_city, nearest_city


class CityHelperTests(unittest.TestCase):
    def setUp(self):
        self.cities = [
            SimpleNamespace(name="Pittsburgh", state="PA", lat=40.4406, lng=-79.9959),
            SimpleNamespace(name="New York", state="NY", lat=40.7128, lng=-74.0060),
            SimpleNamespace(name="Los Angeles", state="CA", lat=34.0522, lng=-118.2437),
        ]

    def test_match_label_and_alias(self):
        self.assertEqual(match_city(self.cities, "Pittsburgh, PA").name, "Pittsburgh")
        self.assertEqual(match_city(self.cities, "nyc").name, "New York")
        self.assertEqual(match_city(self.cities, "LA").name, "Los Angeles")

    def test_nearest_city(self):
        self.assertEqual(nearest_city(self.cities, 40.75, -73.98).name, "New York")
        self.assertEqual(nearest_city(self.cities, 40.44, -80.00).name, "Pittsburgh")


if __name__ == "__main__":
    unittest.main()
