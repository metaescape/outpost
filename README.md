## Outpost

outpost 是前哨的意思，主要是搜集互联网信息并通过邮件发送通知。目前功能包括：

- 解析 httpd 的日志获得网站访问统计信息

- 每日提醒: 随机从指定文件，参考 config_example.py 中选项中选择一条或多条

## 使用方法：

环境: python3.6 以上 (依赖 beautifulsoup4, 用 pip install bs4 安装)

先复制一份 config_example.py ，重命名为 config.py, 填写上自己的服务器网站和 ip 信息
阅读 outpost.serice , 请按实际环境修改其中的 `WorkingDirectory=/root/outpost` 指向改目录实际位置

然后执行以下命令启动服务

```bash
cp outpost.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl start outpost
sudo systemctl enable outpost
```

如果没有 systemd， 直接进入到本项目目录后手动执行以下命令也可以

```bash
nohup python3 main.py --exec=server > output.log 2>&1 &

```
