import atexit
import datetime

import fnmatch
import glob
import json
import os
import re
import signal
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import timedelta
from functools import lru_cache
from pprint import pprint
from typing import Optional

# from httpd_log.parser import standard_line_parser


import requests
from config import Config

# from mail import send_mail
from motto import motto


import time
import logging

logger = logging.getLogger(__name__)


cnf = Config()
SITE = cnf.httpd["sitename"]
SELF_IPS = cnf.ignore_ips["self_ips"]
SERVER_IPS = cnf.ignore_ips["server_ips"]
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
SELF_AGENT_MSGS = cnf.self_agent_msgs

BOTS_LOOKUP_PATH = "bots_lookup.json"
VISITORS_LOOKUP_PATH = "visitors_lookup.json"
TRAFFIC_JSONL = "analysis/traffic.jsonl"
PAGES_LOC_JSON = "analysis/pages_loc.json"
ATTACKERS_THRESHOLD = cnf.attackers_threshold


def read_bots_lookup():
    # read bots_lookup.json from current directory
    if os.path.exists(BOTS_LOOKUP_PATH):
        with open(BOTS_LOOKUP_PATH, "r") as f:
            bots_lookup = json.load(f)
    else:
        bots_lookup = {}
    bots_lookup.update(
        cnf.bots_lookup
    )  # Assuming cnf.bots_lookup is another dictionary you want to merge
    return bots_lookup


def read_visitors_lookup():
    # read visitors_lookup.json from current directory
    if os.path.exists(VISITORS_LOOKUP_PATH):
        with open(VISITORS_LOOKUP_PATH, "r") as f:
            visitors_lookup = json.load(f)
        visitors_lookup = defaultdict(
            lambda: {"loc": "地球", "cnt": 0}, visitors_lookup
        )
    else:
        visitors_lookup = defaultdict(lambda: {"loc": "地球", "cnt": 0})
    return visitors_lookup


def read_pages_loc(result_dict):
    with open(PAGES_LOC_JSON, "r") as f:
        pages_loc = json.load(f)
        result_dict["pages"] = pages_loc["pages"]
        result_dict["locations"] = pages_loc["locations"]


bots_lookup = read_bots_lookup()
visitors_lookup = read_visitors_lookup()


def save_bots_lookup():
    global bots_lookup
    try:
        # Sort the dictionary by its values
        sorted_bots_lookup = {
            k: v
            for k, v in sorted(bots_lookup.items(), key=lambda item: item[1])
        }

        with open(BOTS_LOOKUP_PATH, "w") as f:
            json.dump(
                sorted_bots_lookup, f, indent=4, ensure_ascii=False
            )  # indent=4 for pretty-printing
    except Exception as e:
        print(f"An error occurred: {e}")


def save_visitors_lookup():
    global visitors_lookup
    try:
        with open(VISITORS_LOOKUP_PATH, "w") as f:
            json.dump(
                visitors_lookup, f, indent=4, ensure_ascii=False
            )  # indent=4 for pretty-printing
    except Exception as e:
        print(f"An error occurred: {e}")


@lru_cache(maxsize=1024)
def get_pos_from_ip(ip):
    try:
        url = (
            f"http://ip.taobao.com/outGetIpInfo?ip={ip}&accessKey=alibaba-inc"
        )
        response = requests.get(url, timeout=10)
        ip_info = json.loads(response.text)
        country = ip_info["data"]["country"]
        city = ip_info["data"]["city"]
        if country == "XX":
            country = "猎户座悬臂"
        if city == "XX":
            city = country
        return country, city
    except:
        return "猎户座悬臂", "地球"


def get_first_word_with_key(key, summary):
    words = re.split("[^a-zA-Z]", summary)
    for word in words:
        if key in word and word.find(key) > 0:
            return word
    return None


def extract_spider_brand(summary):
    """
    例如 summary 是 (compatible; Baiduspider... 那么提取出 Baiduspider
    """
    spider = get_first_word_with_key("spider", summary)
    if spider:
        return spider
    else:
        bot = get_first_word_with_key("bot", summary)
        if bot:
            return bot
    return "unk bot"


def access_static(to):
    """
    判断是否真的读取了文章，如果真的读取，一般会加载资源，例如 js, css,
    但由于浏览器缓存，重复访问是不会加载 js,css 的，因此需要加更多判断
    """
    return (
        "themes" in to
        or ".js" in to
        or ".png" in to
        or ".jpg" in to
        or ".gif" in to
        or ".svg" in to
    )


def get_success(info):
    return (info["return"] in ["200"]) and (info["method"] == "GET")


def abnormal_access(info):
    return info["return"] in {
        "404": "not found",
        "302": "temporarily moved",
        "400": "bad request",
    }


def match_ip(ip, patterns):
    for pattern in patterns:
        if fnmatch.fnmatch(ip, pattern):
            return True
    return False


def match_bot_ip(ip, bots_dict):
    for pattern, value in bots_dict.items():
        if fnmatch.fnmatch(ip, pattern):
            return value
    return None


def write_to_f_and_list(content, f, lst):
    f.write(content)
    lst.append(content)


def get_recent_logfiles(logfile, last):
    # 指定的文件夹路径
    dir_path = os.path.dirname(logfile)
    keyword = os.path.basename(logfile)
    files = []
    # 遍历文件夹
    for foldername, subfolders, filenames in os.walk(dir_path):
        for filename in filenames:
            file_path = os.path.join(foldername, filename)
            # 获取文件的修改时间
            file_time = datetime.datetime.fromtimestamp(
                os.path.getmtime(file_path)
            )
            # 如果文件的修改时间大于指定的时间, 并且关键字 access_log 在文件名中
            if file_time > last and keyword in file_path:
                files.append(file_path)

    return files


def extract_full_url(user_agent: str) -> Optional[str]:
    # Use regular expression to match any word that conthttps://github.com/microsoft/pyright/blob/main/docs/configuration.md#reportGeneralTypeIssuesains '.com', '.net', etc., and possibly followed by paths or protocols
    match = re.search(
        r"\b(\w+://)?[\w\.-]+\.(com|net|org|io|cn)[\/\w\.-]*\b", user_agent
    )
    if match:
        return match.group(0)  # Return the full match
    return None


def bot_access(info):
    """
    从 ip， from 和 agent summary 三个方面过滤爬虫
    """
    global bots_lookup
    if "bots_lookup" not in globals():
        bots_lookup = {}

    agent_summary = info["client"].lower()

    if match_bot_ip(info["ip"], bots_lookup):
        return True

    if "bot" in agent_summary or "spider" in agent_summary:
        bots_lookup[info["ip"]] = extract_spider_brand(agent_summary)
        return True

    com = extract_full_url(agent_summary)
    if com is not None:
        bots_lookup[info["ip"]] = com
        return True
    for keyword in BOTS_LINK_KEYWORDS:
        if keyword in info["from"]:
            bots_lookup[info["ip"]] = keyword
            return True
    for keyword in BOTS_AGENT_KEYWORDS:
        if keyword in agent_summary:
            bots_lookup[info["ip"]] = keyword
            return True
    for keyword in BOTS_ACCESS_KEYWORDS:
        if keyword in info["to"]:
            bots_lookup[info["ip"]] = f"to {keyword} bot"
            return True
    for ip in SERVER_IPS:
        if ip in info["to"] or ip in info["from"]:
            bots_lookup[info["ip"]] = f"from {ip}"
            return True
    if info["method"] == "POST":
        bots_lookup[info["ip"]] = "POST bot"
        return True
    return False


def self_access(info):
    """
    根据 ip 网段和 agents 信息来过滤是否是自己访问
    不过通过 ip 访问的也很有可能是云服务方的爬虫
    """
    if match_ip(info["ip"], SELF_IPS):
        return True
    for msg in SELF_AGENT_MSGS:
        # 区分大小写
        if msg in info["client"]:
            return True
    return False


def is_new_access_ip(info, result_dict):
    """
    判断当前访问是否是资源页，这是确定用户是否是初次访问的证据
    """
    if access_static(info["to"]) and (
        info["from"].endswith("html") or info["from"].endswith("/")
    ):
        result_dict["full_visitors"].add(info["ip"])
        return True


def from_equal_to(info):
    """
    判断是否是命令式刷新，普通访问情况下，from 和 to 是不相等的
    """
    return (
        info["from"] == info["to"]
        or info["from"].endswith(info["to"])
        or info["to"].endswith(info["from"])
    )


# 全局变量
global_visit_count = 0
last_update_date = None


# 统计函数
def update_visit_count(valid_access_set, result_dict):
    global global_visit_count, last_update_date

    current_date = datetime.datetime.now().date()
    if current_date != last_update_date:
        global_visit_count = 0
        last_update_date = current_date

    cnt = len(valid_access_set)
    unique_cnt = len(set(valid_access_set))
    global_visit_count += unique_cnt

    if cnt > 0:
        result_dict["content"].insert(
            0, f"<p> {cnt}/{unique_cnt}:{global_visit_count}  </p>\n"
        )
    result_dict["day_cnt"] = cnt
    result_dict["day_unique_cnt"] = unique_cnt


def filter_true_visitors(result_dict, get_loc):
    """
    从访问成功的 ip 中过滤掉根据攻击者和机器人 ip, 以免漏网之鱼
    """
    result_dict["attackers"] = set(
        x[0]
        for x in Counter(result_dict["fails"]).items()
        if x[1] >= ATTACKERS_THRESHOLD
    )
    # sudo iptables -A INPUT -s attacker_ip -j DROP

    valid_access_set = []
    for ip, access_page, from_link, date in reversed(
        result_dict["normal_access"]
    ):
        if ip in result_dict["attackers"] or ip in bots_lookup:
            # 继续过滤掉漏网的攻击者和爬虫
            continue
        if ip not in result_dict["full_visitors"]:
            # 过滤掉非资源页访问，大概率是爬虫，少量人为刷新
            continue
        if get_loc:
            country, city = get_pos_from_ip(ip)
        else:
            country, city = "猎户座悬臂", "地球"

        freq = "初次"
        if ip in visitors_lookup:
            freq = "再次"

        if "html" in access_page:
            valid_access_set.append(ip)
            from_loc = f"从 {from_link} " if from_link else " "
            result_dict["content"].append(
                f"<p> {date} 来自 {country} {city} 的 {ip} {from_loc}{freq}访问了 {access_page} </p>\n"
            )
            if city != "地球":
                visitors_lookup[ip]["loc"] = f"{country}:{city}"
            visitors_lookup[ip]["cnt"] += 1

            if "categories" not in access_page and "pages" in result_dict:
                loc = f"{country} {city}"
                if access_page not in result_dict["pages"]:
                    result_dict["pages"][access_page] = 0
                result_dict["pages"][access_page] += 1
                if loc not in result_dict["locations"]:
                    result_dict["locations"][loc] = 0
                result_dict["locations"][loc] += 1

    for ip in result_dict["attackers"]:
        command = ["sudo", "iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"]
        subprocess.run(command)
        result_dict["content"].insert(0, f"<p> 屏蔽疑似攻击者 {ip} </p>\n")

    update_visit_count(valid_access_set, result_dict)


def collect_httpd_log(logfiles, last, get_loc=False):
    result_dict = {
        "logfile_status": [],
        "robots": set(),
        "normal_access": [],
        "content": [],
        "fails": [],
        "attackers": [],
        "full_visitors": set(),
    }

    try:
        read_pages_loc(result_dict)
    except:
        result_dict["content"].append("读取 pages_loc.json 失败")

    for logfile in logfiles:
        result_dict["logfile_status"].append(f"checking {logfile}")
        with open(logfile, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in reversed(lines):
            try:
                info = standard_line_parser(line)
            except:
                continue
            if info["datetime"] < last:
                break
            if bot_access(info):
                continue
            if abnormal_access(info):
                # a lot of fails from one ip imply potential attackers
                result_dict["fails"].append(info["ip"])
                continue
            if self_access(info):
                continue
            if is_new_access_ip(info, result_dict):
                # collect ips
                continue
            if from_equal_to(info):
                continue

            if info["to"].endswith("html"):
                result_dict["normal_access"].append(
                    (
                        info["ip"],
                        info["to"],
                        info["from"],
                        info["datetime"],
                    )
                )

    filter_true_visitors(result_dict, get_loc)
    return result_dict


def update_traffic_jsonl(result_dict):
    """
    将 result_dict 中 day_cnt, day_unique_cnt append 到 traffic.jsonl 中
    """
    now_date = datetime.datetime.today().strftime("%Y年%m月%d日")
    with open(TRAFFIC_JSONL, "a") as f:
        f.write(
            f'["{now_date}", {result_dict["day_cnt"]}, {result_dict["day_unique_cnt"]}]\n'
        )

    if "pages" in result_dict:
        with open(PAGES_LOC_JSON, "w") as f:
            pages_loc = {
                "pages": result_dict["pages"],
                "locations": result_dict["locations"],
            }
            json.dump(pages_loc, f, indent=4, ensure_ascii=False)

    # copy to /var/www/html/traffic.jsonl
    command = [
        "sudo",
        "cp",
        TRAFFIC_JSONL,
        PAGES_LOC_JSON,
        "/var/www/html/analysis/",
    ]
    subprocess.run(command)
    logger.info(
        "traffic.jsonl and pages_loc.json copied to /var/www/html/analysis/"
    )


def time_in_range(start, end, x=None):
    """Return true if x is in the range [start, end]"""
    if not x:
        x = datetime.datetime.now().time()
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def non_oblivious_time():
    # 一般清醒时间
    return time_in_range(
        datetime.time(0, 0, 0), datetime.time(1, 0, 0)
    ) or time_in_range(datetime.time(8, 0, 0), datetime.time(23, 59, 0))


def eager_fetch(logfiles, watch_url, last, test=False):
    """
    尽管叫做 eager_fetch，但是实际上是一个完整的 logcheck 流程，只是用于执行更频繁场景
    比如对网页的刷新关注
    """
    new_last_time = datetime.datetime.today()
    try:
        mail_content = []
        if type(logfiles) == str:
            logfiles = get_recent_logfiles(logfiles, last)

        httpd_info = collect_httpd_log(logfiles, last, get_loc=not test)
        content = httpd_info["content"]
        mail_content.extend(content)

        update_traffic_jsonl(httpd_info)

        # diff = check_and_save_html_changes(watch_url)
        # if diff:
        #     mail_content.append("<h2>网页变化</h2>\n")
        #     mail_content.extend(diff)
        if mail_content:
            logger.info("start sending mail")
            fmt = "%Y年%m月%d日%H时%M分:\n"
            now = datetime.datetime.today().strftime(fmt)
            original_subject = cnf.mail["subject"]
            cnf.mail["subject"] = f"eager fetch report"
            mail_content = [now] + mail_content
            send_mail(cnf, "".join(mail_content))
            cnf.mail["subject"] = original_subject
        return new_last_time

    except Exception as e:

        # 如果异常，发邮件提醒
        cnf.mail["subject"] = f"eager fetch error: "
        exc_type, exc_value, exc_traceback = sys.exc_info()
        line_number = exc_traceback.tb_lineno  # type: ignore
        logger.error(f"An error occurred on line {line_number}: {str(e)}")
        return False


# c
def cleanup():
    logger.info("saving bots_lookup and visitors_lookup table")
    save_bots_lookup()
    save_visitors_lookup()


def exit_signal_handler(signum, frame):
    cleanup()
    logger.info("Received SIGTERM, shutting down server...")
    sys.exit(0)


def server():
    logger.info("starting logcheck server")
    atexit.register(cleanup)

    # 使用signal注册函数，不需要传递signum和frame，因为atexit不提供它们
    signal.signal(signal.SIGTERM, exit_signal_handler)
    signal.signal(signal.SIGINT, exit_signal_handler)

    start_hour, start_minute = map(int, cnf.time["start"].split(":"))
    end_hour, end_minute = map(int, cnf.time["end"].split(":"))
    start8 = datetime.time(start_hour, start_minute, 0)
    end8 = datetime.time(end_hour, end_minute, 0)
    full_gap = cnf.time["full_gap"]
    eager_gap = cnf.time["eager_gap"]
    logfile = cnf.httpd["logfile"]
    full_last = eager_last = datetime.datetime.today() - timedelta(
        hours=eager_gap
    )

    # 这里 loc 实际是上一次访问的时间
    eager_last_str = visitors_lookup["eager_last"]["loc"]
    if eager_last_str != "地球":
        eager_last = datetime.datetime.fromisoformat(eager_last_str)

    while 1:

        if time_in_range(start8, end8):
            # loc 也用来额外保存一些信息，例如上次 eager_fetch 的时间
            # > 3.7
            if (
                datetime.datetime.today() - timedelta(hours=eager_gap)
                > eager_last
            ):
                logger.info(
                    f"starting eager fetch with eager_last {eager_last}"
                )
                eager_last = eager_fetch(logfile, cnf.watch_url, eager_last)
                if eager_last:  # successful
                    visitors_lookup["eager_last"][
                        "loc"
                    ] = eager_last.isoformat()
                    visitors_lookup["eager_last"]["cnt"] += 1
                    logger.info(
                        f"eager fetch end with new eager_last {eager_last}"
                    )

        time.sleep(60 * 10)  # 10 分钟检查一次


def test_eager_fetch():
    gap = 2000
    last = datetime.datetime.today() - timedelta(hours=gap)
    logfiles = glob.glob(f"/tmp/access_log*")
    return eager_fetch(
        logfiles, "https://zhuanlan.zhihu.com/p/651112449", last, test=True
    )


def full_fetch(logfiles, old_hist, last):
    global bots_lookup
    if type(logfiles) == str:
        logfiles = get_recent_logfiles(logfiles, last)

    httpd_info = collect_httpd_log(logfiles, last, True)

    httpd_content = httpd_info["content"]
    attackers = httpd_info["attackers"]

    # gitnews = safe_gitstar(last)
    fmt = "%Y年%m月%d日%H时%M分"
    now = datetime.datetime.today().strftime(fmt)
    last = last.strftime(fmt)
    mail_content = []
    old = []

    if os.path.exists(old_hist):
        with open(old_hist, "r", encoding="utf-8") as f:
            old = list(f.readlines())

    with open(old_hist, "w", encoding="utf-8") as f:
        write_to_f_and_list(f"<h2>{SITE} 简报</h2> \n", f, mail_content)
        write_to_f_and_list(f"<p>{last} -> {now}</p>\n", f, mail_content)

        if gitnews:
            for line in gitnews:
                write_to_f_and_list(line, f, mail_content)
        if httpd_content:
            for line in httpd_content:
                write_to_f_and_list(line, f, mail_content)
        if attackers:
            for ip in attackers:
                country, city = get_pos_from_ip(ip)
                write_to_f_and_list(
                    f"<p>疑似遭遇到 {country} {city} 的 {ip} 的攻击</p>\n",
                    f,
                    mail_content,
                )
        last_bots_lookup = read_bots_lookup()
        # robots is the diff between bots_lookup and last_bots_lookup
        robots = dict(set(bots_lookup.items()) - set(last_bots_lookup.items()))
        if robots:
            for botname in robots:
                write_to_f_and_list(
                    f"<p>新增来自 {robots[botname]} 的 {botname} 爬取了本站</p>\n",
                    f,
                    mail_content,
                )
        f.write("\n")
        for line in old:
            f.write(line)

    mail_content.extend(motto(cnf))
    if hasattr(cnf, "news"):
        mail_content.append("<h2>Hacknews 简析</h2>\n")
        # 新闻分析获取
        url = cnf.news["url"]
        data = cnf.news["data"]
        response = requests.post(url, data=data, stream=True)

        # 处理每一行响应数据
        for line in response.iter_lines():
            if line:
                mail_content.append(f"<p>{line.decode('utf-8')}</p>\n")

    send_mail(cnf, "".join(mail_content))
    return datetime.datetime.today()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="选择要执行的函数")
    parser.add_argument(
        "--exec",
        required=True,
        help="要执行的函数名称",
    )
    args = parser.parse_args()
    if args.exec == "test":
        test()
    elif args.exec == "read_all":
        read_all()
    elif args.exec == "server":
        server()
    elif args.exec == "test-eager":
        test_eager_fetch()
    elif args.exec == "test-git":
        pprint(test_gitstar())
