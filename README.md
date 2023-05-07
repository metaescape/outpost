## Outpost

简要分析 httpd 的日志并且把网站访问信息通过邮件发送, 也可以发送其信息，例如每日提醒，
格言，新闻等，可以把内容写到 motto.org （或其他指定文件，参考 config_example.py 中选项）中，
也可以自己用其他服务（例如爬虫）动态把信息写入文件

环境: python3.6 以上（不依赖第三方 package)

## 使用方法：

先复制一份 config_example.py ，重命名为 config.py ,填写上自己的服务器网站和 ip 信息
阅读 outpost.serice , 请按实际环境修改其中的 `WorkingDirectory=/root/outpost` 指向改目录实际位置

然后执行一下命令启动服务

```bash
cp outpost.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl start outpost
sudo systemctl enable outpost
```

如果没有 systemd， 直接进入到本项目目录后手动执行以下命令也可以

```bash
nohup python3 logcheck.py --exec=server > output.log 2>&1 &

```
