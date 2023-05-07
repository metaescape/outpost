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

cnf = Config()
SITE = cnf.httpd["sitename"]
self_ips = cnf.ignore_ips["self_ips"]

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


def logcheck(logfiles, old_hist, last):
    normal_acc = []
    fails = []
    robots = set()
    content = []
    if type(logfiles) == str:
        logfiles = [logfiles]
    for logfile in logfiles:
        print(f"checking {logfile}")
        with open(logfile, "r", encoding="utf-8") as f:
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
                    robots.add((info["ip"], extract_spider_brand(ip_summary)))
                elif not success:
                    fails.append(info["ip"])
                elif out_refer and hit_page:  # success out refer
                    normal_acc.append(
                        (info["ip"], info["to"], info["from"], info["return"])
                    )
                if (success and not bot) and full_get:
                    data = (info["ip"], info["from"], "", info["return"])
                    if normal_acc and data[:2] != normal_acc[-1][:2]:
                        normal_acc.append(data)

            attackers = [x[0] for x in Counter(fails).items() if x[1] >= 200]
            no_att = [x for x in set(normal_acc) if x[0] not in attackers]
            robots_d = dict(robots)
            no_bot = [x for x in no_att if x[0] not in robots_d]
            for ip, page, refer, code in no_bot:
                if ip in self_ips or server_ip in refer or server_ip in page:
                    # 过滤能从 ip 访问的用户，这基本是自己，或者也是机器人（云服务商之类）
                    continue
                country, city = get_pos_from_ip(ip)
                flag = "初次" if code == "200" else "再次"
                if refer:
                    content.append(
                        f"来自 {country} {city} 的 {ip} 从 {refer} {flag} 访问了 {page}\n"
                    )
                else:
                    content.append(
                        f"来自 {country} {city} 的 {ip} {flag} 访问了 {page}\n"
                    )

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
    attackers = []

    if os.path.exists(old_hist):
        with open(old_hist, "r", encoding="utf-8") as f:
            old = list(f.readlines())

    with open(old_hist, "w", encoding="utf-8") as f:
        write_to_f_and_list(f"<h2>{SITE} 简报</h2> \n", f, mail_content)
        write_to_f_and_list(f"<p>{last} -> {now}</p>\n", f, mail_content)
        mail_content.extend(motto(cnf))
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


def write_to_f_and_list(content, f, lst):
    f.write(content)
    lst.append(content)


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


def time_in_range(start, end, x):
    """Return true if x is in the range [start, end]"""
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def server():
    start_hour, start_minute = map(int, cnf.time["start"].split(":"))
    end_hour, end_minute = map(int, cnf.time["end"].split(":"))
    start8 = datetime.time(start_hour, start_minute, 0)
    end8 = datetime.time(end_hour, end_minute, 0)
    gap = cnf.time["gap"]
    logfile = cnf.httpd["logfile"]
    checked = False
    while 1:
        if checked or time_in_range(
            start8, end8, datetime.datetime.now().time()
        ):
            last = datetime.datetime.today() - timedelta(hours=gap)
            logcheck(logfile, "loghist.txt", last)
            checked = True
            time.sleep(60 * 60 * gap)
        else:
            time.sleep(60 * 60 * 0.2)


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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="选择要执行的函数")
    parser.add_argument(
        "--exec",
        choices=["test", "read_all", "server"],
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
