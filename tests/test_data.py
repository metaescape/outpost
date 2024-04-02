import unittest
from unittest.mock import MagicMock, patch
from httpd_log.data import WebTrafficInsights


class TestWebTrafficInsights(unittest.TestCase):
    def setUp(self):
        self.insights = WebTrafficInsights()

    def test_get_from_cache(self):

        ip = "116.136.55.103"
        expected = None

        self.assertEqual(self.insights.get_from_cache(ip), expected)

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
            country, city = self.insights.get_location(ip)

        self.assertEqual(country, expected_country)
        self.assertEqual(city, expected_city)

    def test_get_location_exception(self):
        ip = "127.0.0.2"
        expected_country = "地球"
        expected_city = "地球"

        # Mock an exception being raised by requests.get
        with patch("requests.get", side_effect=Exception):
            country, city = self.insights.get_location(ip)

        self.assertEqual(country, expected_country)
        self.assertEqual(city, expected_city)

    def test_merge_ip2location(self):
        self.insights.ip2location = {
            "103.169.xx.xx": ["地球:地球", 1, "2029-01-31T12:49:43"]
        }
        # 测试合并一个新的IP地址
        new_table = {"103.169.yy.yy": ["地球:火星", 2, "2024-01-31T12:50:00"]}
        self.insights.merge_ip2location(new_table)
        self.assertIn("103.169.yy.yy", self.insights.ip2location)
        self.assertEqual(
            self.insights.ip2location["103.169.yy.yy"],
            ["地球:火星", 2, "2024-01-31T12:50:00"],
        )

        # 测试合并一个已存在的IP地址，验证计数增加

        existing_table = {
            "103.169.xx.xx": ["地球:地球", 2, "2024-01-31T12:55:00"]
        }
        self.insights.merge_ip2location(existing_table)
        self.assertIn("103.169.xx.xx", self.insights.ip2location)
        self.assertEqual(
            self.insights.ip2location["103.169.xx.xx"],
            ["地球:地球", 3, "2024-01-31T12:55:00"],
        )

    def test_merge_locations(self):
        new_locations = {"地球:地球": 1}
        pages = {"page1": 1}
        self.insights.merge_page_locations(pages, new_locations)
        self.assertEqual(
            self.insights.pages_locations["locations"]["地球:地球"], 1
        )
        self.assertEqual(self.insights.pages_locations["pages"]["page1"], 1)

        self.insights.pages_locations["locations"]["地球:地球"] = 1
        additional_locations = {"地球:地球": 2}
        self.insights.merge_page_locations(pages, additional_locations)
        self.assertEqual(
            self.insights.pages_locations["locations"]["地球:地球"], 3
        )


if __name__ == "__main__":
    unittest.main()
