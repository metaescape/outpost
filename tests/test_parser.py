import unittest
from httpd_log.parser import (
    httpd_logfiles,
    split_session,
    HttpdLogParser,
    str2datetime,
    datetime2str,
)
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
        split_sessions = split_session(start_time, end_time)
        excepted_sessions = [
            (
                datetime.datetime(2024, 3, 1, 8, 0),
                datetime.datetime(2024, 3, 2, 8, 0),
                True,
            ),
            (
                datetime.datetime(2024, 3, 2, 8, 0),
                datetime.datetime(2024, 3, 3, 8, 0),
                True,
            ),
            (
                datetime.datetime(2024, 3, 3, 8, 0),
                datetime.datetime(2024, 3, 3, 12, 0),
                False,
            ),
        ]
        self.assertEqual(split_sessions, excepted_sessions)

        start_time = datetime.datetime(2024, 3, 30, 8, 0)
        end_time = datetime.datetime(2024, 3, 31, 8, 0)
        split_sessions = split_session(start_time, end_time)
        excepted_sessions = [
            (
                datetime.datetime(2024, 3, 30, 8, 0),
                datetime.datetime(2024, 3, 31, 8, 0),
                True,
            ),
        ]
        self.assertEqual(split_sessions, excepted_sessions)

        start_time = datetime.datetime(2024, 3, 30, 8, 0)
        end_time = datetime.datetime(2024, 3, 31, 4, 0)
        split_sessions = split_session(start_time, end_time)
        excepted_sessions = [
            (
                datetime.datetime(2024, 3, 30, 8, 0),
                datetime.datetime(2024, 3, 31, 4, 0),
                False,
            ),
        ]
        self.assertEqual(split_sessions, excepted_sessions)

    def test_filter_files_by_datetime(self):
        start_time = datetime.datetime(2024, 3, 30, 8, 0)
        end_time = datetime.datetime(2024, 3, 31, 12, 0)
        parser = HttpdLogParser(
            start_time, end_time, "/home/pipz/codes/ranger/outpost/logs/httpd/"
        )
        # only for local test
        expected_files = [
            "/home/pipz/codes/ranger/outpost/logs/httpd/access_log",
            "/home/pipz/codes/ranger/outpost/logs/httpd/access_log-20240331",
            "/home/pipz/codes/ranger/outpost/logs/httpd/access_log-20240324",
            "/home/pipz/codes/ranger/outpost/logs/httpd/access_log-20240317",
            "/home/pipz/codes/ranger/outpost/logs/httpd/access_log-20240310",
        ]

        files = parser.filter_files_by_datetime()

        self.assertEqual(sorted(files), sorted(expected_files))

    def test_parse_sessions(self):
        start_time = datetime.datetime(2024, 3, 30, 8, 0)
        end_time = datetime.datetime(2024, 3, 31, 12, 0)

        parser = HttpdLogParser(
            start_time, end_time, "/home/pipz/codes/ranger/outpost/logs/httpd/"
        )
        sessions = parser.parse_loglines_to_sessions()
        self.assertEqual(len(sessions), 2)
        self.assertGreater(len(sessions[0]["loglines"]), 500)
        self.assertGreater(len(sessions[1]["loglines"]), 100)

    def test_datetime_conversion(self):
        # 设置测试用的datetime对象
        test_datetime = datetime.datetime(2024, 1, 31, 12, 49, 43)

        datetime_str = datetime2str(test_datetime)
        self.assertEqual(datetime_str, "2024-01-31T12:49:43")

        # 测试默认情况
        converted_datetime = str2datetime(datetime_str)
        self.assertEqual(converted_datetime, test_datetime)

        # 测试httpd默认格式的情况
        test_datetime_str_httpd = "31/Jan/2024:12:49:43"
        converted_datetime_httpd = str2datetime(
            test_datetime_str_httpd, httpd_default=True
        )

        self.assertEqual(converted_datetime_httpd, test_datetime)

        test_datetime = datetime.datetime(2024, 1, 31, 12, 49, 43)
        self.assertEqual(
            datetime2str(test_datetime, only_date=True), "2024-01-31"
        )

        test_string = "2024-01-31T12:49:43"
        expected_datetime = datetime.datetime(2024, 1, 31, 12, 49, 43)
        self.assertEqual(str2datetime(test_string), expected_datetime)


if __name__ == "__main__":
    unittest.main()
