import smtplib

# 负责构造文本
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# 负责将多个对象集合起来
from email.mime.multipart import MIMEMultipart
from email.header import Header


def send_mail(config, body_content="你好，这是一个测试邮件！"):
    """
    发送邮件
    """
    # SMTP服务器,这里使用163邮箱
    mail_server = config.mail["server"]
    mail_port = config.mail["port"]
    # 发件人邮箱
    mail_sender = config.mail["sender"]
    # 邮箱授权码,注意这里不是邮箱密码,如何获取邮箱授权码,请看本文最后教程
    mail_license = config.mail["license"]
    # 收件人邮箱，可以为多个收件人
    mail_receivers = config.mail["receivers"]

    mm = MIMEMultipart("related")
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

    # 邮件正文内容
    # 构造文本,参数1：正文内容，参数2：文本格式，参数3：编码方式
    message_text = MIMEText(body_content, "plain", "utf-8")
    # 向MIMEMultipart对象中添加文本对象
    mm.attach(message_text)

    # 创建SMTP对象
    stp = smtplib.SMTP()
    # 设置发件人邮箱的域名和端口
    stp.connect(mail_server, mail_port)
    # set_debuglevel(1)可以打印出和SMTP服务器交互的所有信息
    stp.set_debuglevel(1)
    # 登录邮箱，传递参数1：邮箱地址，参数2：邮箱授权码
    stp.login(mail_sender, mail_license)
    # 发送邮件，传递参数1：发件人邮箱地址，参数2：收件人邮箱地址，参数3：把邮件内容格式改为str
    stp.sendmail(mail_sender, mail_receivers, mm.as_string())
    print("邮件发送成功")
    # 关闭SMTP对象
    stp.quit()


if __name__ == "__main__":
    from config import Config

    config = Config()
    send_mail(config)
