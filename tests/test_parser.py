import unittest
import os
from httpd_log.parser import httpd_logfiles, split_session, HttpdLogParser
import datetime


class TestParser(unittest.TestCase):
    def test_httpd_logfiles(self):
        # only for local test
        expected_files = [
            "/home/pipz/codes/ranger/outpost/logs/httpd/access_log",
            "/home/pipz/codes/ranger/outpost/logs/httpd/access_log-20240310",
            "/home/pipz/codes/ranger/outpost/logs/httpd/access_log-20240317",
            "/home/pipz/codes/ranger/outpost/logs/httpd/access_log-20240324",
            "/home/pipz/codes/ranger/outpost/logs/httpd/access_log-20240331",
        ]

        files = httpd_logfiles("/home/pipz/codes/ranger/outpost/logs/httpd/")

        self.assertEqual(sorted(files), sorted(expected_files))

    def test_httpd_logfiles_no_match(self):
        keyword = "nonexistent"
        expected_files = []

        files = httpd_logfiles()

        self.assertEqual(files, expected_files)

    def test_split_session(self):
        start_time = datetime.datetime(2024, 3, 1, 8, 0)
        end_time = datetime.datetime(2024, 3, 3, 12, 0)
        days = 1
        split_sessions = split_session(start_time, end_time, days)
        excepted_sessions = [
            (
                datetime.datetime(2024, 3, 1, 8, 0),
                datetime.datetime(2024, 3, 2, 8, 0),
            ),
            (
                datetime.datetime(2024, 3, 2, 8, 0),
                datetime.datetime(2024, 3, 3, 8, 0),
            ),
            (
                datetime.datetime(2024, 3, 3, 8, 0),
                datetime.datetime(2024, 3, 3, 12, 0),
            ),
        ]
        self.assertEqual(split_sessions, excepted_sessions)

        start_time = datetime.datetime(2024, 3, 30, 8, 0)
        end_time = datetime.datetime(2024, 3, 31, 12, 0)
        split_sessions = split_session(start_time, end_time, days)
        excepted_sessions = [
            (
                datetime.datetime(2024, 3, 30, 8, 0),
                datetime.datetime(2024, 3, 31, 8, 0),
            ),
            (
                datetime.datetime(2024, 3, 31, 8, 0),
                datetime.datetime(2024, 3, 31, 12, 0),
            ),
        ]
        self.assertEqual(split_sessions, excepted_sessions)

    def test_parse_sessions(self):
        start_time = datetime.datetime(2024, 3, 30, 8, 0)
        end_time = datetime.datetime(2024, 3, 31, 12, 0)

        parser = HttpdLogParser(
            start_time, end_time, "/home/pipz/codes/ranger/outpost/logs/httpd/"
        )
        sessions = parser.parse_loglines_to_sessions()
        self.assertEqual(len(sessions), 2)
        self.assertGreater(len(sessions[0]["loglines"]), 500)


if __name__ == "__main__":
    unittest.main()
