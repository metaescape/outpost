.PHONY: test install deploy view

# 运行所有测试
test:
	python -m unittest discover -v

# 安装依赖
install:
	pip install -r requirements.txt

httpdlog:
	scp -r root@tc:/var/log/httpd/access* ~/codes/ranger/outpost/logs/httpd/

local-test:
	python main.py --exec=local

push-dir:
	rsync -avz --no-perms --no-owner --no-group --exclude=loghist.txt --exclude=".git/"\
		--exclude="__pycache__/" --exclude="*.json*" --exclude="*.txt" --exclude="*.log"\
		--exclude="*.mypy_cache" --exclude="logs/" \
		~/codes/ranger/outpost/ root@tc:~/outpost/

push-and-restart:
	set -x
	ssh tc 'systemctl stop outpost'
	scp root@tc:~/outpost/analysis/*.json ~/codes/ranger/outpost/
	rsync -avz --no-perms --no-owner --no-group --exclude=loghist.txt --exclude=".git/"\
		--exclude="__pycache__/" --exclude="*.json*" --exclude="*.txt" --exclude="*.log"\
		--exclude="*.mypy_cache" --exclude="logs/" \
		~/codes/ranger/outpost/ root@tc:~/outpost/

	ssh tc 'systemctl start outpost'

view:
	rsync -avz ~/codes/ranger/outpost/analysis/ root@tc:/var/www/html/analysis/ \
	 --exclude="*.json*" --exclude="*.py" --exclude="*.txt"

temp-push-json:
	rsync -avz ~/codes/ranger/outpost/.vscode/*.json root@tc:~/outpost/.vscode/