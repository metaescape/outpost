import unittest
from httpd_log.session import SessionAnalyzer

from httpd_log.parser import HttpdLogParser
from configs.config import Config
import datetime


class TestSessionIntegration(unittest.TestCase):
    def setUp(self):
        start_time = datetime.datetime(2024, 3, 30, 8, 0)
        end_time = datetime.datetime(2024, 3, 31, 12, 0)

        parser = HttpdLogParser(
            start_time, end_time, "/home/pipz/codes/ranger/outpost/logs/httpd/"
        )
        sessions = parser.parse_loglines_to_sessions()
        config = Config()
        self.analyzer = SessionAnalyzer(sessions[0], config)
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
        self.assertTrue(
            self.analyzer.bot_hunter.is_recorded_bot("149.56.160.142")
        )


if __name__ == "__main__":
    unittest.main()
