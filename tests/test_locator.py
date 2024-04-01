import unittest
from unittest.mock import MagicMock, patch
from httpd_log.data import WebTrafficInsights


class TestGeoLocator(unittest.TestCase):
    def setUp(self):
        self.geo_locator = WebTrafficInsights()

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

    def test_merget_table(self):
        self.geo_locator.ip2location = {
            "103.169.xx.xx": ["地球:地球", 1, "2029-01-31T12:49:43"]
        }
        # 测试合并一个新的IP地址
        new_table = {"103.169.yy.yy": ["地球:火星", 2, "2024-01-31T12:50:00"]}
        self.geo_locator.merge_table(new_table)
        self.assertIn("103.169.yy.yy", self.geo_locator.ip2location)
        self.assertEqual(
            self.geo_locator.ip2location["103.169.yy.yy"],
            ["地球:火星", 2, "2024-01-31T12:50:00"],
        )

        # 测试合并一个已存在的IP地址，验证计数增加

        existing_table = {
            "103.169.xx.xx": ["地球:地球", 2, "2024-01-31T12:55:00"]
        }
        self.geo_locator.merge_table(existing_table)
        self.assertIn("103.169.xx.xx", self.geo_locator.ip2location)
        self.assertEqual(
            self.geo_locator.ip2location["103.169.xx.xx"],
            ["地球:地球", 3, "2024-01-31T12:55:00"],
        )


if __name__ == "__main__":
    unittest.main()
