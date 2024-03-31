import unittest
from httpd_log.bots import BotsHunter
from httpd_log.bots import get_first_word_with_key


class TestBotsHunter(unittest.TestCase):
    def setUp(self):
        # only for personal use
        from configs.config import Config

        self.config = Config()

        self.bots_hunter = BotsHunter(self.config)

    def test_match_bot_ip(self):
        # Test the match_bot_ip method
        ip = "127.0.0.1"
        result = self.bots_hunter.match_bot_ip(ip)
        self.assertEqual(result, False)  # Add your expected result here
        ip = "27.43.204.104"
        result = self.bots_hunter.match_bot_ip(ip)
        self.assertEqual(result, True)
        for i in range(256):
            ip = f"42.236.10.{i}"
            result = self.bots_hunter.match_bot_ip(ip)
            self.assertEqual(result, True)

    def test_is_bot_access(self):
        ip = "127.0.0.1"
        client = "Mozilla/5.0"
        from_link = "http://example.com"
        to = "/cgi-bin"
        method = "GET"
        result = self.bots_hunter.is_bot_access(
            ip, client, from_link, to, method
        )
        self.assertEqual(result, True)

    def test_extract_spider_brand(self):
        # Test the extract_spider_brand method
        agent_summary = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        result = self.bots_hunter.extract_spider_brand(agent_summary)
        self.assertEqual(result, "Googlebot")  # Add your expected result here

    def test_extract_full_url(self):
        # Test the extract_full_url method
        agent_summary = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        result = self.bots_hunter.extract_full_url(agent_summary)
        self.assertEqual(
            result, "http://www.google.com/bot.html"
        )  # Add your expected result here

        test_cases = [
            "Mozilla/5.0 (compatible; Dataprovider.com)",
            "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
            "HTTP Banner Detection (https://security.ipip.net)",
            "com.apple.WebKit.Networking/8614.4.6.0.6 CFNetwork/1404.0.5 Darwin/22.3.0",
        ]
        from logcheck import extract_full_url

        assert extract_full_url(test_cases[0]) == "Dataprovider.com"
        assert extract_full_url(test_cases[1]) == "http://ahrefs.com/robot"
        assert extract_full_url(test_cases[2]) == "https://security.ipip.net"
        assert extract_full_url(test_cases[3]) == None

    def test_get_first_word_with_key(self):
        # Test the get_first_word_with_key function
        key = "bot"
        summary = "360bot here"
        result = get_first_word_with_key(key, summary)
        self.assertEqual(result, "360bot")  # Add your expected result here


if __name__ == "__main__":
    unittest.main()
