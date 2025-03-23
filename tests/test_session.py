import unittest
from httpd_log.session import SessionAnalyzer

from httpd_log.parser import HttpdLogParser, datetime2str
from configs.config import Config
import datetime
import os
from collections import defaultdict


class TestSessionIntegration(unittest.TestCase):
    def setUp(self):
        start_time = datetime.datetime(2024, 3, 30, 8, 0)
        self.end_time = datetime.datetime(2024, 3, 31, 12, 0)

        parser = HttpdLogParser(
            start_time,
            self.end_time,
            "/home/pipz/codes/ranger/outpost/logs/httpd/",
        )
        sessions = parser.parse_loglines_to_sessions()
        config = Config()
        self.analyzer = SessionAnalyzer(sessions[1], config)
        self.analyzer.loglines = [
            {
                "client": '" "Mozilla/5.0 (compatible; Dataprovider.com)"\n',
                "datetime": datetime.datetime(2024, 3, 31, 11, 56, 13),
                "from": "-",
                "ip": "149.56.160.142",
                "method": "GET",
                "protocol": "HTTP/1.1",
                "return": "302",
                "size": "235",
                "to": "/.well-known/security.txt",
            },
            {
                "client": '" "Mozilla/5.0 (compatible; Dataprovider.com)"\n',
                "datetime": datetime.datetime(2024, 3, 31, 11, 56, 14),
                "from": "http://www.hugchange.life/.well-known/security.txt",
                "ip": "149.56.160.142",
                "method": "GET",
                "protocol": "HTTP/1.1",
                "return": "404",
                "size": "196",
                "to": "/.well-known/security.txt",
            },
            {
                "client": '" "Mozilla/5.0 (compatible; Dataprovider.com)"\n',
                "datetime": datetime.datetime(2024, 3, 31, 11, 56, 34),
                "from": "https://www.hugchange.life/",
                "ip": "144.217.135.246",
                "method": "GET",
                "protocol": "HTTP/1.1",
                "return": "200",
                "size": "5187",
                "to": "/orgchange/themes/static/dark.css",
            },
        ]

    def test_first_scan(self):
        self.analyzer.scan_for_bots()
        self.assertTrue(self.analyzer.bot_hunter.trapped("149.56.160.142"))

    def test_read_last_line(self):
        from httpd_log.session import read_last_line

        current_file_path = os.path.abspath(__file__)
        self.assertEqual(
            "    unittest.main()\n", read_last_line(current_file_path)
        )

    def test_add_msg(self):
        self.analyzer.add_msg("hello")
        self.assertEqual(
            self.analyzer.session_data["content"],
            ["<p> hello </p>\n"],
        )
        self.analyzer.add_msg("world", prepend=True)
        self.assertEqual(
            self.analyzer.session_data["content"],
            ["<p> world </p>\n", "<p> hello </p>\n"],
        )

    def test_update_ip2location(self):
        self.analyzer.session_data = {
            "ip2location": {},
        }

        self.analyzer.update_ip2location(
            "192.168.1.1", "Country", "City", "2022-01-01"
        )
        self.assertIn("192.168.1.1", self.analyzer.session_data["ip2location"])
        self.assertEqual(
            self.analyzer.session_data["ip2location"]["192.168.1.1"][1], 1
        )
        self.analyzer.update_ip2location(
            "192.168.1.1", "Country", "City", "2022-01-03"
        )
        self.assertEqual(
            self.analyzer.session_data["ip2location"]["192.168.1.1"][1], 2
        )
        self.assertEqual(
            self.analyzer.session_data["ip2location"]["192.168.1.1"][2],
            "2022-01-03",
        )

    def test_update_pages_loc(self):
        self.analyzer.session_data = {
            "pages": defaultdict(int),
            "locations": defaultdict(int),
        }

        self.analyzer.update_pages_loc("Country", "City", "/categories/")
        self.assertEqual(
            self.analyzer.session_data["pages"]["/categories/"], 0
        )
        self.assertEqual(
            self.analyzer.session_data["locations"]["Country City"], 0
        )

        self.analyzer.update_pages_loc("Country", "City", "/posts/1")
        self.assertEqual(self.analyzer.session_data["pages"]["/posts/1"], 1)
        self.assertEqual(
            self.analyzer.session_data["locations"]["Country City"], 1
        )

    def test_update_visit_count(self):
        self.analyzer.session_data = {
            "ip2location": {},
            "pages": defaultdict(int),
            "locations": defaultdict(int),
            "content": [],
        }

        self.analyzer.update_visit_count([1, 1, 2, 2, 3, 3, 4])
        self.assertEqual(self.analyzer.session_data["pv"], 7)
        self.assertEqual(self.analyzer.session_data["uv"], 4)
        self.assertEqual(
            self.analyzer.session_data["content"],
            [f"<p> {datetime2str(self.end_time)} 7:4 / pv:uv </p>\n"],
        )

    def test_get_location(self):
        self.analyzer.session_data = {
            "ip2location": {
                "129.1.1.1": ["Country:City", 1, "2022-01-01"],
            },
        }

        self.assertEqual(
            self.analyzer.get_location("129.1.1.1"), ("Country", "City")
        )

    def test_read_mails(self):
        end = "2024-03-31 12:00:00"
        self.analyzer.end_time = datetime.datetime.strptime(
            end, "%Y-%m-%d %H:%M:%S"
        )
        content = self.analyzer.read_mails(3)
        assert "28" not in content[0]
        assert "5" in content[0]


if __name__ == "__main__":
    unittest.main()
