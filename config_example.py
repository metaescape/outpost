class Config:
    # 在每天 8 点到 8:30 分析并发送邮件
    time = {"start": "8:00", "end": "8:30", "gap": 24}  # hour
    # 指定网站域名和日志文件地址，其中日志文件地址是必须的
    httpd = {"sitename": "mywebsite", "logfile": "/var/log/httpd/access_log"}
    # 指定每日一言的地址，以及每日一言的数量和前缀，前缀可以是空字符串，只从该文件中选择满足前缀的句子
    motto = {"path": "motto.org", "num": 1, "prefix": ":"}

    # 不需要分析的IP， 包括个人电脑的IP和服务器的IP
    # self_ips: 个人电脑的 IP 地址，可以有多个，因为自己可能从不同的地方访问网页
    ignore_ips = {
        "self_ips": ["120.40.232.54", "59.61.27.167"],
        "server_ip": "2.14.147.196",
    }
    # 用来检查某个或某些 git 仓库 star 变化，当前不启用，可以忽略
    git = {
        "repos": ["myrepo"],
        "user": "haha",
    }

    mail = {
        "server": "smtp.163.com",
        "port": "25",
        "sender": "yourname@163.com",
        "license": "YPKYMHLOHDQQRAKN",
        "receivers": ["yourname@163.com"],
        "subject": "最新报告",
        "from": "tc server <yourname@163.com>",
        "to": "you <yourname@163.com>",
        "html": "template.html",
        "css": "style.css",
    }
