from httpd_log.bots import BotsHunter
from httpd_log.data import WebTrafficInsights
from collections import defaultdict, Counter
import os


class SessionAnalyzer:
    """
    each session will output a report (dictionary)
    if the session is a full session, it will also save session info to persistent storage
    """

    def __init__(self, session, config):
        """
        session format:
        {
            "range": (start, end),
            "loglines": [],
            "is_full": k != len(self.session_list) - 1,
        }
        """
        self.loglines = session["loglines"]
        self.start_time = session["range"][0]
        self.end_time = session["range"][1]
        self.is_full = session["is_full"]

        self.geolocator = WebTrafficInsights()
        self.bot_hunter = BotsHunter(config)
        self.filter_page_keywords = config.filter_page_keywords

        self.session_data = {
            "fails": Counter(),  # failed access ips, intermidiate data for attackers check
            "full_visitors": set(),  # ips that read html files and static files; intermidiate data for normal access
            "pages": defaultdict(int),  # page: count
            "locations": defaultdict(int),  # location: count
            "normal_access": [],  # normal access
            "ip2location": {},  #  {normal access ip: [location, cnt, last access time]}
            "content": [],  # mail content
            "pv": 0,
            "uv": 0,  # totla page view count and unique count per session
        }

    def add_msg(self, msg, add_tag=True, prepend=False):
        if add_tag:
            final_msg = f"<p> {msg} </p>\n"
        if prepend:
            self.session_data["content"].insert(0, final_msg)
        else:
            self.session_data["content"].append(final_msg)

    def run(self, send_mail=False):
        self.scan_for_bots()
        self.fine_scan_for_normal_access()
        self.generate_report_and_statistics()
        return self.session_data

    def scan_for_bots(self):
        """
        hunt for bots and collection potential attackers
        also collect raw normal visitors
        """
        for info in self.loglines:

            if self.bot_hunter.hunt(
                info,
                fails=self.session_data["fails"],
            ):
                continue

            if is_access_static_files(info["to"]) and (
                info["from"].endswith("html") or info["from"].endswith("/")
            ):
                self.session_data["full_visitors"].add(info["ip"])
                continue

            if info["to"].endswith("html"):
                self.session_data["normal_access"].append(
                    (
                        info["ip"],
                        info["to"],
                        info["from"],
                        info["datetime"],
                    )
                )
        self.bot_hunter.find_and_block_attackers(
            self.session_data["fails"], self
        )

    def fine_scan_for_normal_access(self):
        # 二次过滤 normal_access
        normal_access = self.session_data["normal_access"]
        result = []

        for ip, access_page, from_link, date in normal_access:
            if self.bot_hunter.trapped(ip):
                continue
            if ip not in self.session_data["full_visitors"]:
                # 如果当前 session 中 ip 没有访问任何静态页面，那么比较大概率还是机器
                # 因为一般访问都会加载静态资源，即便重复访问，至少在一天中的某个时间段会加载
                continue
            result.append((ip, access_page, from_link, date))
        self.session_data["normal_access"] = result

    def generate_report_and_statistics(self):
        """
        generate mail access email report and do some statistics on normal access
        """
        valid_access_record = []
        normal_access = self.session_data["normal_access"]
        for ip, access_page, from_link, date in normal_access:
            country, city = self.geolocator.get_location(ip)

            freq = "再次" if ip in self.geolocator else "初次"

            if "html" in access_page:
                valid_access_record.append(ip)
                from_loc = f"从 {from_link} " if from_link else " "
                access_note = f"{date} 来自 {country} {city} 的 {ip} {from_loc}{freq}访问了 {access_page}"
                self.add_msg(access_note)
                self.update_ip2location(ip, country, city, date)
                self.update_pages_loc(country, city, access_page)

        self.update_visit_count(valid_access_record)

    def update_ip2location(self, ip, country, city, date):
        if ip not in self.session_data["ip2location"]:
            self.session_data["ip2location"][ip] = [
                f"{country}:{city}",
                0,
                date,
            ]
        self.session_data["ip2location"][ip][1] += 1
        self.session_data["ip2location"][ip][2] = date
        if country != "地球":
            self.session_data["ip2location"][ip][0] = f"{country}:{city}"

    def update_pages_loc(self, country, city, access_page):
        if any(kw in access_page for kw in self.filter_page_keywords):
            return

        loc = f"{country} {city}"
        self.session_data["pages"][access_page] += 1
        self.session_data["locations"][loc] += 1

    # count page view and unique visitor
    def update_visit_count(self, valid_access_record):

        cnt = len(valid_access_record)
        unique_cnt = len(set(valid_access_record))

        self.add_msg(f"total and unique view {cnt}:{unique_cnt}", prepend=True)
        self.session_data["pv"] = cnt
        self.session_data["uv"] = unique_cnt

    def merge_tables(self):
        """
        ip2location, pages, locations all need to be merged
        """
        self.geolocator.merge_ip2location(self.session_data["ip2location"])
        self.geolocator.merge_pages(self.session_data["pages"])
        self.geolocator.merge_locations(self.session_data["locations"])


def is_access_static_files(to):
    """
    判断是否真的读取了文章，如果真的读取，一般会加载资源，例如 js, css,
    但由于浏览器缓存，重复访问是不会加载 js,css 的，因此需要加更多判断
    """
    return any(
        ext in to for ext in [".js", ".png", ".jpg", ".gif", ".svg", "themes"]
    )


def read_last_line(file_path):
    """高效地读取文件的最后一行"""
    with open(file_path, "rb") as f:
        f.seek(-2, os.SEEK_END)  # 移动到文件的倒数第二个字节
        while f.read(1) != b"\n":  # 向后读取，直到找到换行符
            f.seek(-2, os.SEEK_CUR)
        last_line = f.readline().decode()
    return last_line
