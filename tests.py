import unittest
import os
from logcheck import get_recent_logfiles
import shutil
import datetime


class BasicsTestCase(unittest.TestCase):
    def setUp(self):
        # Create a test directory and a test file
        self.test_dir = "/tmp/test_dir"
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_file = os.path.join(self.test_dir, "test_file.txt")
        with open(self.test_file, "w") as file:
            file.write("This is a test file.")

    def test_get_recent_logfiles(self):
        # Call the function to test
        last = datetime.datetime.today() - datetime.timedelta(hours=24)
        result = get_recent_logfiles(self.test_file, last)
        # Check if the test file is in the result
        self.assertIn(self.test_file, result)

    def tearDown(self):
        # Remove the test directory after the test
        shutil.rmtree(self.test_dir)

    def test_mail(self):
        pass

    def test_motto(self):
        pass

    def test_bots(self):
        test_cases = [
            "Mozilla/5.0 (compatible; Dataprovider.com)",
            "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
            "HTTP Banner Detection (https://security.ipip.net)",
        ]
        from logcheck import extract_full_url

        assert extract_full_url(test_cases[0]) == "Dataprovider.com"
        assert extract_full_url(test_cases[1]) == "http://ahrefs.com/robot"
        assert extract_full_url(test_cases[2]) == "https://security.ipip.net"


if __name__ == "__main__":
    logfile = "/var/log/httpd/access_log"
    if os.path.exists(logfile):
        last = datetime.datetime.today() - datetime.timedelta(hours=24)
        print(get_recent_logfiles(logfile, last))
    unittest.main()
