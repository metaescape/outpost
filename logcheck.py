from datetime import timedelta
import datetime
import json
import time
import requests
import glob
from collections import Counter
import re
from operator import itemgetter
from collections import defaultdict
from config import Config
from mail import send_mail
from motto import motto
import os
import fnmatch
import requests
from bs4 import BeautifulSoup
import difflib

cnf = Config()
SITE = cnf.httpd["sitename"]
self_ips = cnf.ignore_ips["self_ips"]
BOTS_LOOKUP = {"42.236.10.*": "360 spider"}
server_ip = cnf.ignore_ips["server_ip"]


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


def get_resource(to):
    """
    判断是否真的读取了文章，如果真的读取，一般会加载资源，例如 js, css,
    但由于浏览器缓存，重复访问是不会加载 js,css 的，因此需要加更多判断
    """
    return (
        "themes" in to
        or "posts" in to
        or ".js" in to
        or ".png" in to
        or ".jpg" in to
        or ".gif" in to
    )


def get_success(info):
    """
    304 为使用缓存，因此说明不是第一次访问
    """
    return (info["return"] in ["200", "304"]) and (info["method"] == "GET")


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


def logcheck(logfiles, old_hist, last):
    if type(logfiles) == str:
        logfiles = get_recent_logfiles(logfiles, last)

    httpd_info = collect_httpd_log(logfiles, last, True)

    robots = httpd_info["robots"]
    content = httpd_info["content"]
    attackers = httpd_info["attackers"]

    # 只保留机器人名称和地点（机器人 ip 随时会换）
    bot_reduce = defaultdict(set)
    if robots:
        for ip, botname in sorted(robots, key=itemgetter(1)):
            country, city = get_pos_from_ip(ip)
            bot_reduce[botname].add(city)

    gitnews = None  # gitstar(last)
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
        if content:
            for line in content:
                write_to_f_and_list(line, f, mail_content)
        if attackers:
            for ip in attackers:
                country, city = get_pos_from_ip(ip)
                write_to_f_and_list(
                    f"<p>疑似遭遇到 {country} {city} 的 {ip} 的攻击</p>\n",
                    f,
                    mail_content,
                )
        if robots:
            for botname in bot_reduce:
                cities = ",".join(bot_reduce[botname])
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


def collect_httpd_log(logfiles, last, get_loc=False):
    result_dict = {
        "logfile_status": [],
        "robots": set(),
        "normal_acc": [],
        "content": [],
        "fails": [],
        "attackers": [],
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
                success = get_success(info)
                ip_summary = info["client"].lower()
                bot = "bot" in ip_summary or "spider" in ip_summary
                hit_page = info["to"][-5:] == ".html" or info["to"] == "/"
                out_refer = (
                    5 < len(info["from"]) < 100
                    and "todayad.live" not in info["from"]
                    and SITE not in info["from"]
                )
                full_get = get_resource(info["to"]) and "posts" in info["from"]
                if bot:
                    result_dict["robots"].append(
                        (info["ip"], extract_spider_brand(ip_summary))
                    )
                elif match_bot_ip(info["ip"], BOTS_LOOKUP):
                    result_dict["robots"].add(
                        (info["ip"], match_bot_ip(info["ip"], BOTS_LOOKUP))
                    )

                elif not success:
                    result_dict["fails"].append(info["ip"])
                elif out_refer and hit_page:
                    result_dict["normal_acc"].append(
                        (info["ip"], info["to"], info["from"], info["return"])
                    )
                if (success and not bot) and full_get:
                    data = (info["ip"], info["from"], "", info["return"])
                    if (
                        result_dict["normal_acc"]
                        and data[:2] != result_dict["normal_acc"][-1][:2]
                    ):
                        result_dict["normal_acc"].append(data)

            attackers = [
                x[0]
                for x in Counter(result_dict["fails"]).items()
                if x[1] >= 200
            ]
            result_dict["attackers"] = attackers
            no_att = [
                x
                for x in set(result_dict["normal_acc"])
                if x[0] not in attackers
            ]
            robots_d = dict(result_dict["robots"])
            no_bot = [x for x in no_att if x[0] not in robots_d]
            for ip, page, refer, code in no_bot:
                if (
                    match_ip(ip, self_ips)
                    or server_ip in refer
                    or server_ip in page
                ):
                    continue
                if get_loc:
                    country, city = get_pos_from_ip(ip)
                else:
                    country, city = "地球", "地球"
                flag = "初次" if code == "200" else "再次"
                if "html" in page:
                    from_loc = f"从 {refer} " if refer else " "
                    result_dict["content"].append(
                        f"<p> 来自 {country} {city} 的 {ip}{from_loc}{flag}访问了 {page} </p>"
                    )
    return result_dict


def check_and_save_html_changes(url, filepath=None):
    # Fetching content from the URL
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    if not filepath:
        filepath = "/tmp/" + url.split("/")[-1]
    # Assuming the main content is under <div class="RichText"> tags, this might change based on the actual HTML structure
    content = soup.find("div", class_="RichText").text

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
            gitcontent = (
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


def eager_fetch(logfile: str, watch_url, last):
    mail_content = []
    httpd_info = collect_httpd_log([logfile], last, True)
    content = httpd_info["content"]
    mail_content.extend(content)

    diff = check_and_save_html_changes(watch_url)
    if diff:
        mail_content.append("<h2>网页变化</h2>\n")
        mail_content.extend(diff)
    if mail_content:
        fmt = "%Y年%m月%d日%H时%M分"
        now = datetime.datetime.today().strftime(fmt)
        cnf.mail["subject"] = f"{now} eager fetch report"
        send_mail(cnf, "".join(mail_content))
    print(mail_content)


def server():
    start_hour, start_minute = map(int, cnf.time["start"].split(":"))
    end_hour, end_minute = map(int, cnf.time["end"].split(":"))
    start8 = datetime.time(start_hour, start_minute, 0)
    end8 = datetime.time(end_hour, end_minute, 0)
    gap = cnf.time["gap"]
    interval = cnf.time["interval"]
    logfile = cnf.httpd["logfile"]
    end_day = datetime.time(23, 45, 0)
    while 1:
        if time_in_range(start8, end8):
            last = datetime.datetime.today() - timedelta(hours=gap)
            logcheck(logfile, "loghist.txt", last)

        elif time_in_range(start8, end_day):
            print("check")
            last = datetime.datetime.today() - timedelta(hours=interval)
            eager_fetch("/var/log/httpd/access_log", cnf.watch_url, last)
            print("send")
        time.sleep(60 * 60 * interval)


def read_all():
    gap = 2000
    last = datetime.datetime.today() - timedelta(hours=gap)
    logfiles = glob.glob(f"{cnf.httpd['logfile']}*")
    logcheck(logfiles, "loghist.txt", last)


def test():
    gap = 2000
    last = datetime.datetime.today() - timedelta(hours=gap)
    logfiles = glob.glob(f"{cnf.httpd['logfile']}")
    logcheck(logfiles, "loghist.txt", last)


def test2():
    gap = 2000
    last = datetime.datetime.today() - timedelta(hours=gap)
    logfiles = glob.glob(f"/tmp/access_log*")
    # return collect_httpd_log(logfiles, last)
    check_and_save_html_changes("https://zhuanlan.zhihu.com/p/651112449")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="选择要执行的函数")
    parser.add_argument(
        "--exec",
        choices=["test", "read_all", "server", "test2"],
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
    elif args.exec == "test2":
        print(test2())
