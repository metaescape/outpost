import unittest
from unittest.mock import MagicMock, patch
from httpd_log.ip_location import GeoLocator

from log_config import setup_logging


class TestGeoLocator(unittest.TestCase):
    def setUp(self):
        self.geo_locator = GeoLocator()
        setup_logging()

    def test_get_from_cache(self):
        ip = "117.136.55.103"
        expected = "中国", "天津"

        self.assertEqual(self.geo_locator.get_from_cache(ip), expected)

        ip = "116.136.55.103"
        expected = None

        self.assertEqual(self.geo_locator.get_from_cache(ip), expected)

    def test_get_location_success(self):
        ip = "127.0.0.1"
        expected_country = "United States"
        expected_city = "New York"

        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"country": expected_country, "city": expected_city}
        }
        with patch("requests.get", return_value=mock_response):
            country, city = self.geo_locator.get_location(ip)

        self.assertEqual(country, expected_country)
        self.assertEqual(city, expected_city)

    def test_get_location_exception(self):
        ip = "127.0.0.2"
        expected_country = "地球"
        expected_city = "地球"

        # Mock an exception being raised by requests.get
        with patch("requests.get", side_effect=Exception):
            country, city = self.geo_locator.get_location(ip)

        self.assertEqual(country, expected_country)
        self.assertEqual(city, expected_city)


if __name__ == "__main__":
    unittest.main()
