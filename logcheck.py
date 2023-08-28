import atexit
import datetime
import difflib
import fnmatch
import glob
import json
import os
import re
import signal
import sys
import time
from collections import Counter
from datetime import timedelta
from functools import lru_cache
from pprint import pprint

import requests
from bs4 import BeautifulSoup

from config import Config
from mail import send_mail
from motto import motto

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


def read_bots_look():
    # read bots_lookup.json from current directory
    if os.path.exists("bots_lookup.json"):
        with open("bots_lookup.json", "r") as f:
            bots_lookup = json.load(f)
    else:
        bots_lookup = {}
    bots_lookup.update(
        cnf.bots_lookup
    )  # Assuming cnf.bots_lookup is another dictionary you want to merge
    return bots_lookup


bots_lookup = read_bots_look()


def save_bots_lookup(signum=None, frame=None):
    # update bots_lookup with bots_lookup
    global bots_lookup
    try:
        with open("bots_lookup.json", "w") as f:
            json.dump(bots_lookup, f, indent=4)  # indent=4 for pretty-printing
    except:
        pass


# 使用atexit注册函数
atexit.register(save_bots_lookup)

# 使用signal注册函数
signal.signal(signal.SIGTERM, save_bots_lookup)
signal.signal(signal.SIGINT, save_bots_lookup)


def parse_httpd_log(logline):
    res = {}
    end = logline.find("-") - 1
    res["ip"] = logline[:end]

    start = logline.find("[") + 1
    end = logline.find("]")
    date = logline[start:end].split()[0]
    res["datetime"] = datetime.datetime.strptime(date, "%d/%b/%Y:%H:%M:%S")

    start = logline.find(' "') + 2
    end = logline.find('" ')
    res["method"], res["to"], res["protocol"] = logline[start:end].split()

    logline = logline[end:]
    start = logline.find('" ') + 2
    end = logline.find(' "')
    res["return"], res["size"] = logline[start:end].split()

    logline = logline[end:]
    start = logline.find(' "') + 2
    end = logline.find('" ')
    res["from"] = logline[start:end]
    res["client"] = logline[end:]
    return res


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


def full_fetch(logfiles, old_hist, last):
    global bots_lookup
    if type(logfiles) == str:
        logfiles = get_recent_logfiles(logfiles, last)

    httpd_info = collect_httpd_log(logfiles, last, True)

    httpd_content = httpd_info["content"]
    attackers = httpd_info["attackers"]

    gitnews = safe_gitstar(last)
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
        last_bots_lookup = read_bots_look()
        # robots is the diff between bots_lookup and last_bots_lookup
        robots = dict(set(bots_lookup.items()) - set(last_bots_lookup.items()))
        if robots:
            for botname in robots:
                cities = ",".join(robots[botname])
                write_to_f_and_list(
                    f"<p>来自 {cities} 的 {botname} 爬取了本站</p>\n", f, mail_content
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


def extract_full_url(user_agent: str) -> str:
    # Use regular expression to match any word that contains '.com', '.net', etc., and possibly followed by paths or protocols
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
    判断当前访问是否访问了资源页，这是确定用户是否是初次访问的证据
    """
    if access_static(info["to"]) and (
        info["from"].endswith("html") or info["from"].endswith("/")
    ):
        result_dict["full_visitors"].add(info["ip"])
        return True


def filter_true_visitors(result_dict, get_loc):
    """
    从访问成功的 ip 中过滤掉根据攻击者和机器人 ip, 以免漏网之鱼
    """
    result_dict["attackers"] = set(
        x[0] for x in Counter(result_dict["fails"]).items() if x[1] >= 50
    )

    for ip, access_page, from_link, date in result_dict["normal_access"]:
        if ip in result_dict["attackers"] or ip in bots_lookup:
            # 继续过滤掉漏网的攻击者和爬虫
            continue
        if get_loc:
            country, city = get_pos_from_ip(ip)
        else:
            country, city = "银河系", "漫游中"

        freq = "再次"
        if ip in result_dict["full_visitors"]:
            freq = "初次"

        if "html" in access_page:
            from_loc = f"从 {from_link} " if from_link else " "
            result_dict["content"].append(
                f"<p> {date} 来自 {country} {city} 的 {ip} {from_loc}{freq}访问了 {access_page} </p>\n"
            )


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

    for logfile in logfiles:
        result_dict["logfile_status"].append(f"checking {logfile}")
        with open(logfile, "r", encoding="utf-8", errors="ignore") as f:
            for line in f.readlines():
                try:
                    info = parse_httpd_log(line)
                except:
                    continue
                if info["datetime"] < last:
                    continue
                if bot_access(info):
                    continue
                if not get_success(info):
                    # a lot of fails from one ip imply potential attackers
                    result_dict["fails"].append(info["ip"])
                    continue
                if self_access(info):
                    continue
                if is_new_access_ip(info, result_dict):
                    # collect ips
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


def check_and_save_html_changes(url, filepath=None):
    if not url:
        return []
    # Fetching content from the URL
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    if not filepath:
        filepath = "/tmp/" + url.split("/")[-1]
    # Assuming the main content is under <div class="RichText"> tags, this might change based on the actual HTML structure
    try:
        content = soup.find("div", class_="RichText").text
    except:
        return [f"{url} 抓取失败"]

    # Read the existing file content
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            existing_content = file.read()
    except FileNotFoundError:
        existing_content = ""

    # Compare and save if there's a change
    if content != existing_content:
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(content)
        print("Detected changes and updated the file!")

        # Display the changes
        diff = difflib.ndiff(
            existing_content.splitlines(), content.splitlines()
        )
        changes = [
            line
            for line in diff
            if line.startswith("+ ") or line.startswith("- ")
        ]
        return changes


def safe_gitstar(last):
    try:
        return gitstar(last)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        line_number = exc_traceback.tb_lineno
        return [f"An error occurred on line {line_number}: {str(e)}"]


def gitstar(last):
    repos = cnf.git["repos"]
    user = cnf.git["user"]
    gitcontent = []
    for repo in repos:
        url = (
            f"https://api.github.com/repos/{user}/{repo}/stargazers?per_page=1"
        )
        repo_response = requests.get(
            url, headers={"Accept": "application/vnd.github.v3.star+json"}
        )
        if repo_response.status_code != 200:
            continue

        new_stars = []
        for i, star in enumerate(repo_response.json()):
            star_time = star["starred_at"]
            star_datetime = datetime.datetime.strptime(
                star_time, "%Y-%m-%dT%H:%M:%SZ"
            )
            user = star["user"]["login"]
            if star_datetime > last:
                new_stars.append(user)
        if new_stars:
            gitcontent.append(
                f"{repo} star 新增 {','.join(new_stars)}, 共 {i + 1} star\n"
            )
    return gitcontent


def time_in_range(start, end, x=None):
    """Return true if x is in the range [start, end]"""
    if not x:
        x = datetime.datetime.now().time()
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def non_oblivious_time():
    return time_in_range(
        datetime.time(0, 0, 0), datetime.time(1, 0, 0)
    ) or time_in_range(datetime.time(8, 0, 0), datetime.time(23, 59, 0))


def eager_fetch(logfiles, watch_url, last, test=False):
    """
    尽管叫做 eager_fetch，但是实际上是一个完整的 logcheck 流程，只是用于执行更频繁场景
    比如对网页的刷新关注
    """
    try:
        mail_content = []
        if type(logfiles) == str:
            logfiles = [logfiles]

        httpd_info = collect_httpd_log(logfiles, last, get_loc=not test)
        content = httpd_info["content"]
        mail_content.extend(content)

        diff = check_and_save_html_changes(watch_url)
        if diff:
            mail_content.append("<h2>网页变化</h2>\n")
            mail_content.extend(diff)
        new_star_msg = gitstar(last)
        if new_star_msg:
            mail_content.extend(new_star_msg)
        if mail_content:
            if not test:
                fmt = "%Y年%m月%d日%H时%M分"
                now = datetime.datetime.today().strftime(fmt)
                original_subject = cnf.mail["subject"]
                cnf.mail["subject"] = f"{now} eager fetch report"
                send_mail(cnf, "".join(mail_content))
                cnf.mail["subject"] = original_subject
            else:
                pprint(mail_content)
                pprint(bots_lookup)

    except Exception as e:
        # 如果异常，发邮件提醒
        cnf.mail["subject"] = f"eager fetch error: "
        exc_type, exc_value, exc_traceback = sys.exc_info()
        line_number = exc_traceback.tb_lineno
        if not test:
            if time_in_range(datetime.time(17, 0, 0), datetime.time(21, 0, 0)):
                send_mail(
                    cnf, f"An error occurred on line {line_number}: {str(e)}"
                )
        else:
            print(line_number, e)


def server():
    start_hour, start_minute = map(int, cnf.time["start"].split(":"))
    end_hour, end_minute = map(int, cnf.time["end"].split(":"))
    start8 = datetime.time(start_hour, start_minute, 0)
    end8 = datetime.time(end_hour, end_minute, 0)
    gap = cnf.time["gap"]
    interval = cnf.time["interval"]
    logfile = cnf.httpd["logfile"]
    while 1:
        if time_in_range(start8, end8):
            last = datetime.datetime.today() - timedelta(hours=gap)
            full_fetch(logfile, "loghist.txt", last)

        elif non_oblivious_time():
            last = datetime.datetime.today() - timedelta(hours=interval)
            eager_fetch("/var/log/httpd/access_log", cnf.watch_url, last)
        time.sleep(60 * 60 * interval)


def read_all():
    gap = 2000
    last = datetime.datetime.today() - timedelta(hours=gap)
    logfiles = glob.glob(f"{cnf.httpd['logfile']}*")
    full_fetch(logfiles, "loghist.txt", last)


def test():
    gap = 2000
    last = datetime.datetime.today() - timedelta(hours=gap)
    logfiles = glob.glob(f"{cnf.httpd['logfile']}")
    full_fetch(logfiles, "loghist.txt", last)


def test_eager_fetch():
    gap = 2000
    last = datetime.datetime.today() - timedelta(hours=gap)
    logfiles = glob.glob(f"/tmp/access_log*")
    return eager_fetch(
        logfiles, "https://zhuanlan.zhihu.com/p/651112449", last, test=True
    )


def test_gitstar():
    gap = 2000
    last = datetime.datetime.today() - timedelta(hours=gap)
    return gitstar(last)


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
