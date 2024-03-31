import fnmatch
import re
import os
import json
import logging

logger = logging.getLogger(__name__)


class BotsHunter:
    # 类变量
    BOTS_ACCESS_KEYWORDS = [
        "/cgi-bin",
        "/manage",
        "/.env",
        "/vendor",
        "/robots.txt",
        "/config",
    ]
    BOTS_LINK_KEYWORDS = [
        "todayad",
        "easyseo",
    ]
    BOTS_AGENT_KEYWORDS = [
        "headless",
        "python",
        "selenium",
    ]

    def __init__(self, config):
        self.config = config
        self.self_ips = config.ignore_ips["self_ips"]
        self.server_ips = config.ignore_ips["server_ips"]
        self.bots_lookup = {}
        # read bots_lookup.json from current directory
        bots_path = os.path.join(os.path.dirname(__file__), "bots_lookup.json")
        if os.path.exists(bots_path):
            logger.info(f"Loading bots lookup from {bots_path}")
            with open(bots_path, "r") as f:
                self.bots_lookup = json.load(f)

        # the key may be regular expression
        self.user_bots_lookup = config.bots_lookup

    def match_bot_ip(self, ip):
        if ip in self.bots_lookup:
            return True

        for pattern, value in self.user_bots_lookup.items():
            if fnmatch.fnmatch(ip, pattern):
                return True
        return False

    def is_bot_access(self, ip, client, from_link, to, method):
        agent_summary = client.lower()

        if self.match_bot_ip(ip):
            return True

        # 由于 bots dict 只作为查询表,因此可以随时保存,越保存频繁越能检测到
        if "bot" in agent_summary or "spider" in agent_summary:
            self.bots_lookup[ip] = self.extract_spider_brand(agent_summary)
            return True

        com = self.extract_full_url(agent_summary)
        if com is not None:
            self.bots_lookup[ip] = com
            return True

        for keyword in self.BOTS_LINK_KEYWORDS:
            if keyword in from_link:
                self.bots_lookup[ip] = keyword
                return True

        for keyword in self.BOTS_AGENT_KEYWORDS:
            if keyword in agent_summary:
                self.bots_lookup[ip] = keyword
                return True

        for keyword in self.BOTS_ACCESS_KEYWORDS:
            if keyword in to:
                self.bots_lookup[ip] = f"to {keyword} bot"
                return True

        for ip_address in self.server_ips:
            if ip_address in to or ip_address in from_link:
                self.bots_lookup[ip] = f"from {ip_address}"
                return True

        if method == "POST":
            self.bots_lookup[ip] = "POST bot"
            return True

        return False

    @staticmethod
    def extract_spider_brand(agent_summary):
        """
        例如 summary 是 (compatible; Baiduspider... 那么提取出 Baiduspider
        """
        spider = get_first_word_with_key("spider", agent_summary)
        if spider:
            return spider
        else:
            bot = get_first_word_with_key("bot", agent_summary)
            if bot:
                return bot
        return "unk bot"

    @staticmethod
    def extract_full_url(agent_summary):
        # Use regular expression to match any word that contains '.com', '.net', etc., and possibly followed by paths or protocols
        match = re.search(
            r"\b(\w+://)?[\w\.-]+\.(com|net|org|io|cn)[\/\w\.-]*\b",
            agent_summary,
        )
        if match:
            return match.group(0)  # Return the full match
        return None


def get_first_word_with_key(key, summary):
    words = re.split("[^a-zA-Z0-9]", summary)
    for word in words:
        if key in word and word.find(key) > 0:
            return word
    return None
