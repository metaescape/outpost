import smtplib

from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# 负责将多个对象集合起来
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.mime.application import MIMEApplication
import os


def mail_meta(config):
    """
    邮件元数据
    """
    # SMTP服务器,这里使用163邮箱
    server = config.mail["server"]
    port = config.mail["port"]
    # 发件人邮箱
    sender = config.mail["sender"]
    # 邮箱授权码,注意这里不是邮箱密码,如何获取邮箱授权码,请看本文最后教程
    license = config.mail["license"]
    # 收件人邮箱，可以为多个收件人
    receivers = config.mail["receivers"]
    # relative to current directory
    cur_dir = os.path.dirname(__file__)
    html = os.path.join(cur_dir, config.mail["html"])
    css = os.path.join(cur_dir, config.mail["css"])
    return server, port, sender, license, receivers, html, css


def init_mime(config, mail_sender, mail_receivers):
    mm = MIMEMultipart()
    # 邮件主题
    subject_content = config.mail["subject"]
    # 设置发送者展示信息
    mm["From"] = config.mail["from"] if "from" in config.mail else mail_sender
    # 设置接受者展示信息
    mm["To"] = (
        config.mail["to"] if "to" in config.mail else ",".join(mail_receivers)
    )
    # 设置邮件主题
    mm["Subject"] = Header(subject_content, "utf-8")
    return mm


def send_mm(mm, server, port, sender, license, receivers):
    # 创建SMTP对象
    stp = smtplib.SMTP()
    # 设置发件人邮箱的域名和端口
    stp.connect(server, port)
    # set_debuglevel(1)可以打印出和SMTP服务器交互的所有信息
    stp.set_debuglevel(1)
    # 登录邮箱，传递参数1：邮箱地址，参数2：邮箱授权码
    stp.login(sender, license)
    # 发送邮件，传递参数1：发件人邮箱地址，参数2：收件人邮箱地址，参数3：把邮件内容格式改为str
    stp.sendmail(sender, receivers, mm.as_string())
    print("邮件发送成功")
    # 关闭SMTP对象
    stp.quit()


def add_html(mm: MIMEMultipart, html: str, css: str, content: str):
    """
    将 html 文件添加到邮件中
    """
    if os.path.exists(html):
        with open(html, "r") as html_file:
            html_content = html_file.read()

        html_content = html_content.format(content)
        if os.path.exists(css):
            with open(css, "r") as css_file:
                css_content = css_file.read()

                html_content = html_content.replace(
                    "css_placeholder", css_content
                )
        else:
            html_content = html_content.replace("css_placeholder", "")

        mm.attach(MIMEText(html_content, "html", "utf-8"))
    else:
        mm.attach(MIMEText(content, "plain", "utf-8"))


def add_plain_text(mm, body_content):
    # 邮件正文内容
    message_text = MIMEText(body_content, "plain", "utf-8")
    # 向MIMEMultipart对象中添加文本对象
    if body_content:
        mm.attach(message_text)


def send_mail(config, content="你好，这是一个测试邮件！"):
    """
    发送邮件
    """
    (server, port, sender, license, receivers, html, css) = mail_meta(config)
    mm = init_mime(config, sender, receivers)
    add_plain_text(mm, "")
    add_html(mm, html, css, content)
    send_mm(mm, server, port, sender, license, receivers)


if __name__ == "__main__":
    from config import Config

    config = Config()
    send_mail(config)
