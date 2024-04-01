import unittest
from httpd_log.bots import BotsHunter
from httpd_log.bots import get_first_word_with_key
from unittest.mock import patch, MagicMock


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
            '" "Mozilla/5.0 (compatible; Dataprovider.com)"\n',
        ]
        from logcheck import extract_full_url

        self.assertEqual(extract_full_url(test_cases[0]), "Dataprovider.com")
        self.assertEqual(
            extract_full_url(test_cases[1]), "http://ahrefs.com/robot"
        )
        self.assertEqual(
            extract_full_url(test_cases[2]), "https://security.ipip.net"
        )
        self.assertEqual(extract_full_url(test_cases[3]), None)

        self.assertEqual(extract_full_url(test_cases[4]), "Dataprovider.com")

    def test_get_first_word_with_key(self):
        # Test the get_first_word_with_key function
        key = "bot"
        summary = "360bot here"
        result = get_first_word_with_key(key, summary)
        self.assertEqual(result, "360bot")  # Add your expected result here

    @patch("subprocess.run")
    def test_find_and_block_attackers(self, mock_subprocess_run):
        # 模拟失败的访问尝试
        import collections

        fails = collections.Counter(
            ["192.168.1.1", "192.168.1.1", "192.168.1.1", "192.168.1.2"]
        )
        self.bots_hunter.attackers_threshold = 3

        # 使用MagicMock来模拟session对象
        mock_session = MagicMock()

        # 调用方法
        self.bots_hunter.find_and_block_attackers(
            fails=fails, session=mock_session
        )

        # 验证是否正确地识别出攻击者，并尝试通过iptables命令屏蔽它们
        mock_subprocess_run.assert_called_once_with(
            [
                "sudo",
                "iptables",
                "-A",
                "INPUT",
                "-s",
                "192.168.1.1",
                "-j",
                "DROP",
            ]
        )

        mock_session.add_msg.assert_called_once_with(
            "<p> 屏蔽疑似攻击者 192.168.1.1 </p>\n"
        )


if __name__ == "__main__":
    unittest.main()
