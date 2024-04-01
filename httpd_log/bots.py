import fnmatch
import re
import os
import json
import logging
from log_config import setup_logging
from collections import Counter
import subprocess

setup_logging()


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
        self.self_agent_msgs = config.self_agent_msgs
        self.attackers_threshold = config.attackers_threshold
        self.bots_lookup = {}
        # read bots_lookup.json from current directory
        bots_path = os.path.join(os.path.dirname(__file__), "bots_lookup.json")
        if os.path.exists(bots_path):
            logging.info(f"Loading bots lookup from {bots_path}")
            with open(bots_path, "r") as f:
                self.bots_lookup = json.load(f)

        # the key may be regular expression
        self.user_bots_lookup = config.bots_lookup

    def hunt(self, info, fails: list):
        """
        info: an dictionary with keys: ip, from, to, method, agent, return
        fails: a list to collect failed access ips
        """
        ip, from_link, to, method = (
            info["ip"],
            info["from"],
            info["to"],
            info["method"],
        )
        agent_summary, return_code = info["client"], info["return"]
        if self.is_bot_access(ip, agent_summary, from_link, to, method):
            return True
        if self.abnormal_access(return_code):
            # a lot of fails from one ip imply potential attackers
            fails.append(ip)
            return True
        if self.is_self_access(ip, agent_summary):
            return True

        if self.from_equal_to(from_link, to):
            return True

    def find_and_block_attackers(self, fails: list, session):
        """
        find attackers from failed access
        filter out attackers and bots from raw normal visitors
        use iptables command to block attackers
        """

        attackers = set(
            x[0]
            for x in Counter(fails).items()
            if x[1] >= self.attackers_threshold
        )
        # sudo iptables -A INPUT -s attacker_ip -j DROP
        for ip in attackers:
            self.add_bot_ip(ip, "attacker")
            command = [
                "sudo",
                "iptables",
                "-A",
                "INPUT",
                "-s",
                ip,
                "-j",
                "DROP",
            ]

            subprocess.run(command)
            logging.info(f"屏蔽疑似攻击者 {ip}")
            session.add_msg(f"<p> 屏蔽疑似攻击者 {ip} </p>\n")

    def match_bot_ip(self, ip):
        if ip in self.bots_lookup:
            return True

        for pattern, value in self.user_bots_lookup.items():
            if fnmatch.fnmatch(ip, pattern):
                return True
        return False

    def is_recorded_bot(self, ip):
        return self.match_bot_ip(ip)

    def add_bot_ip(self, ip, bot_name):
        self.bots_lookup[ip] = bot_name
        return True

    def is_bot_access(self, ip, agent_summary, from_link, to, method):
        agent_summary = agent_summary.lower()

        if self.is_recorded_bot(ip):
            return True

        # 由于 bots dict 只作为查询表,因此可以随时保存,越保存频繁越能检测到
        if "bot" in agent_summary or "spider" in agent_summary:
            return self.add_bot_ip(
                ip, self.extract_spider_brand(agent_summary)
            )

        com = self.extract_full_url(agent_summary)
        if com is not None:
            return self.add_bot_ip(ip, com)

        for keyword in self.BOTS_LINK_KEYWORDS:
            if keyword in from_link:
                return self.add_bot_ip(ip, keyword)

        for keyword in self.BOTS_AGENT_KEYWORDS:
            if keyword in agent_summary:
                return self.add_bot_ip(ip, keyword)

        for keyword in self.BOTS_ACCESS_KEYWORDS:
            if keyword in to:
                return self.add_bot_ip(ip, "{keyword} bot")

        for ip_address in self.server_ips:
            if ip_address in to or ip_address in from_link:
                return self.add_bot_ip(ip, f"from {ip_address}")

        if method == "POST":
            return self.add_bot_ip(ip, "POST bot")

        return False

    def is_self_access(self, ip, agent_summary):
        """
        根据 ip 网段和 agents 信息来过滤是否是自己访问
        不过通过 ip 访问的也很有可能是云服务方的爬虫
        """
        if match_ip(ip, self.self_ips):
            return True
        for msg in self.self_agent_msgs:
            # don't use str.lower, because it's case sensitive
            if msg in agent_summary:
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

    @staticmethod
    def from_equal_to(from_link, to):
        """
        判断是否是命令式刷新，普通访问情况下，from 和 to 一般是不相等的，这种情况一般忽略
        """
        return (
            from_link == to or from_link.endswith(to) or to.endswith(from_link)
        )

    @staticmethod
    def abnormal_access(return_code):
        return return_code in {
            "404": "not found",
            "302": "temporarily moved",
            "400": "bad request",
        }


def get_first_word_with_key(key, summary):
    words = re.split("[^a-zA-Z0-9]", summary)
    for word in words:
        if key in word and word.find(key) > 0:
            return word
    return None


def match_ip(ip, patterns):
    for pattern in patterns:
        if fnmatch.fnmatch(ip, pattern):
            return True
    return False
