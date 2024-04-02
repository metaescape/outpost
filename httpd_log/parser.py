import datetime
import os
import logging


class HttpdLogParser:
    def __init__(
        self, start_time, end_time, log_dir="/var/log/httpd", hours=24
    ):
        self.log_dir = log_dir
        self.start_time = start_time
        self.end_time = end_time
        self.session_list = split_session(start_time, end_time, hours=hours)

    def parse_loglines_to_sessions(self):
        loglines = self.parse_loglines_after_datetime()

        sessions = []
        for k, (start, end, is_full) in enumerate(self.session_list):
            sessions.append(
                {
                    "range": (start, end),
                    "loglines": [],
                    "is_full": is_full,
                }
            )

        for logline in loglines:
            idx = self.get_session_id(logline["datetime"])
            if idx != -1:
                sessions[idx]["loglines"].append(logline)

        return sessions

    def get_session_id(self, log_time):
        for k, (start, end, _) in enumerate(self.session_list):
            if start <= log_time <= end:
                return k
        return -1

    def parse_loglines_after_datetime(self):
        files_from_new_to_old = self.filter_files_by_datetime()

        loglines = []
        for file in files_from_new_to_old:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    log_entry = self.safe_parse_line(line)
                    if log_entry and log_entry["datetime"] > self.start_time:
                        loglines.append(log_entry)
        logging.info(
            f"{len(loglines)} form {self.start_time} to {self.end_time} had been parsed"
        )
        return loglines[::-1]

    def filter_files_by_datetime(self):
        all_files = httpd_logfiles(self.log_dir)
        backup_files, current_files = [], []
        filtered_files = get_files_after_datetime(all_files, self.start_time)
        for file in filtered_files:
            if file.endswith("access_log"):
                current_files.append(file)
            else:
                backup_files.append(file)
        files_from_new_to_old = current_files + sorted(
            backup_files, reverse=True
        )
        return files_from_new_to_old

    def safe_parse_line(self, line):
        try:
            return HttpdLogParser.standard_line_parser(line)
        except:
            return None

    @staticmethod
    def standard_line_parser(logline):
        res = {}
        end = logline.find("-") - 1
        res["ip"] = logline[:end]

        start = logline.find("[") + 1
        end = logline.find("]")
        date_str = logline[start:end].split()[0]
        res["datetime"] = str2datetime(date_str, httpd_default=True)

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


def match_files_in_dir(dir_path, keyword):
    """
    在指定的文件夹中查找文件名包含关键字的文件
    """
    files = []
    # 遍历文件夹
    for foldername, subfolders, filenames in os.walk(dir_path):
        for filename in filenames:
            file_path = os.path.join(foldername, filename)
            # 如果文件名中包含关键字
            if keyword in file_path:
                files.append(file_path)

    return files


def httpd_logfiles(folder="/var/log/httpd"):
    """
    在指定的文件夹中查找文件名包含关键字的文件
    """
    return match_files_in_dir(folder, "access_log")


def get_files_after_datetime(files, last_datetime):
    """
    获取指定时间之后的文件
    """
    new_files = []
    for file in files:
        # 获取文件的修改时间
        file_time = datetime.datetime.fromtimestamp(os.path.getmtime(file))
        # 如果文件的修改时间大于指定的时间
        if file_time > last_datetime:
            new_files.append(file)

    return new_files


def split_session(start_time, end_time, hours=24):
    """
    split time range into sessions, each session is at most 24 hours by default
    """
    session_list = []
    start = start_time
    while start < end_time:
        is_full = True
        end = start + datetime.timedelta(hours=hours)
        if end > end_time:
            end = end_time
            is_full = False
        session_list.append((start, end, is_full))
        start = end
    return session_list


def datetime2str(date_time=None, only_date=False):
    """
    convert datetime to  str format like "2024-01-31T12:49:43"
    """
    if date_time is None:
        date_time = datetime.datetime.today()
    if only_date:
        return date_time.strftime("%Y-%m-%d")
    return date_time.strftime("%Y-%m-%dT%H:%M:%S")


def str2datetime(string, httpd_default=False):
    """
    convert str format like "2024-01-31T12:49:43" to datetime object

    """
    if httpd_default:
        return datetime.datetime.strptime(string, "%d/%b/%Y:%H:%M:%S")
    return datetime.datetime.strptime(string, "%Y-%m-%dT%H:%M:%S")
