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


if __name__ == "__main__":
    logfile = "/var/log/httpd/access_log"
    if os.path.exists(logfile):
        last = datetime.datetime.today() - datetime.timedelta(hours=24)
        print(get_recent_logfiles(logfile, last))
    unittest.main()
