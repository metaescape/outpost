import json
import os
import datetime
import logging
from mail.mail import send_mail
from httpd_log.parser import (
    HttpdLogParser,
    datetime2str,
    str2datetime,
    tolerant_time,
)
import importlib
import configs.config
from configs.config import Config
from httpd_log.session import SessionAnalyzer
import time
from datetime import timedelta
import sys

CHECK_GAP = 10  # 10 分钟检查一次


class Workflow:
    def __init__(self, start_time, end_time, log_folder, config):
        self.is_server = False
        if log_folder == "/var/log/httpd/" and os.path.exists(log_folder):
            logging.info("Workflow: start on server")
            self.is_server = True

        gap_hours = 24
        true_gap = end_time - start_time
        if tolerant_time(true_gap, timedelta(hours=config.time["eager_gap"])):
            # convert to hours
            gap_hours = true_gap.total_seconds() / 3600

        logging.info(f"gap hours is set to {gap_hours} hours")

        self.parser = HttpdLogParser(
            start_time, end_time, log_folder, gap_hours
        )

        self.config = config
        self.end_time = end_time

    def run(self):
        self.sessions = self.parser.parse_loglines_to_sessions()
        for session in self.sessions:
            analyzer = SessionAnalyzer(session, self.config, self.is_server)
            session_result = analyzer.run()
            if analyzer.is_full:
                write_last(session["range"][1])
                if self.is_server:
                    analyzer.copy_to_server_dir()
            if self.is_server:
                # if not time_is_ok(self.config, session["range"][1]): # 取消注释用于测试
                #     self.mailing_eager_test(session_result["content"])
                mail_last = read_last(type="mail")
                next_send_time = (
                    mail_last
                    + timedelta(days=self.config.mail["days"])
                    - timedelta(minutes=CHECK_GAP + 1)
                )
                logging.info("next mail time is %s", next_send_time)
                if session["range"][1] > next_send_time:
                    write_last(session["range"][1], type="mail")
                    mail_content = analyzer.read_mails(
                        days=self.config.mail["days"]
                    )
                    self.mailing(mail_content)

    def mailing(self, mail_content):
        logging.info("sending mail ...")
        send_mail(self.config, "".join(mail_content))
        self.mail_content = []

    def mailing_eager_test(self, content):
        """
        只在测试时使用，用于发送测试邮件
        """
        logging.info("sending test mail ...")
        original_subject = self.config.mail["subject"]
        self.config.mail["subject"] = f"eager fetch report"
        send_mail(self.config, "".join(content))
        self.config.mail["subject"] = original_subject


def eager_fetch(log_dir, config):
    """
    尽管叫做 eager_fetch，但是实际上是一个完整的 logcheck 流程，只是用于执行更频繁场景
    比如对网页的刷新关注
    """
    start = read_last(type="eager")
    end = datetime.datetime.today()
    workflow = Workflow(start, end, log_dir, config)
    workflow.run()
    return end

    # diff = check_and_save_html_changes(config.watch_url)
    # diff = None
    # if diff:
    #     mail_content.append("<h2>网页变化</h2>\n")
    #     mail_content.extend(diff)


def read_last(type="eager"):
    with open("timestamp.json", "r") as f:
        res = json.load(f)
    current_time = datetime.datetime.today()
    if type == "eager":
        if "last_fetch" not in res:
            return current_time
        last_str = res["last_fetch"]
    elif type == "mail":
        if "last_mail" not in res:
            return current_time
        last_str = res["last_mail"]
    return str2datetime(last_str)


def write_last(last, type="eager"):
    time_str = datetime2str(last)
    with open("timestamp.json", "r") as f:
        res = json.load(f)
    if type == "eager":
        res["last_fetch"] = time_str
    elif type == "mail":
        res["last_mail"] = time_str
    with open("timestamp.json", "w") as f:
        logging.info(f"writing {time_str} to last {type} ...")
        json.dump(res, f)


def time_in_range(start, end, x=None):
    """Return true if x is in the range [start, end]"""
    if not x:
        x = datetime.datetime.now().time()
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def time_is_ok(config, last_datetime):
    eager_gap = config.time["eager_gap"]
    start_hour, start_minute = map(int, config.time["start"].split(":"))
    end_hour, end_minute = map(int, config.time["end"].split(":"))
    window_start = datetime.time(start_hour, start_minute, 0)
    window_end = datetime.time(end_hour, end_minute, 0)

    return time_in_range(window_start, window_end) and (
        datetime.datetime.today() - timedelta(hours=eager_gap) > last_datetime
    )


def dynamic_import_config():
    """
    重新加载配置文件，可以在运行时修改配置文件
    """
    importlib.reload(configs.config)
    return Config()


def server():
    logging.info("starting outpost server")
    config = dynamic_import_config()
    log_dir = "/var/log/httpd/"
    first = True
    while 1:
        eager_last = read_last(type="eager")
        if first or time_is_ok(config, eager_last):
            # loc 也用来额外保存一些信息，例如上次 eager_fetch 的时间
            logging.info(f"starting eager fetch with eager_last {eager_last}")
            try:
                fetch_end = eager_fetch(log_dir, config)
                logging.info(f"eager fetch end at {fetch_end}")
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()

                line_number = exc_traceback.tb_lineno  # type: ignore
                logging.error(
                    f"An error occurred on line {line_number}: {str(e)}"
                )
            first = False
        time.sleep(60 * CHECK_GAP)


def local_test():
    print("local test")
    config = Config()
    start_time = read_last()
    end_time = datetime.datetime(2024, 3, 31, 12, 0)
    log_folder = "/home/pipz/codes/ranger/outpost/logs/httpd/"
    instance = Workflow(
        start_time, end_time, log_folder, config
    )  # 适当调整以匹配实际的初始化方法
    print("start wrokflow")

    instance.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="选择要执行的函数")
    parser.add_argument(
        "--exec",
        required=True,
        help="要执行的函数名称",
    )
    args = parser.parse_args()
    if args.exec == "server":
        server()
    if args.exec == "local":
        local_test()
