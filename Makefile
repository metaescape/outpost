.PHONY: test install deploy view

# 运行所有测试
test:
	python -m unittest discover -v

# 安装依赖
install:
	pip install -r requirements.txt

push:
	set -x
	ssh tc 'systemctl stop outpost'
	scp root@tc:~/outpost/*.json $HOME/codes/ranger/outpost/
	rsync -avz --no-perms --no-owner --no-group --exclude=loghist.txt --exclude=".git/"\
		--exclude="__pycache__/" --exclude="*.json*" --exclude="*.txt" --exclude="*.log"\
		--exclude="*.mypy_cache" \
		$HOME/codes/ranger/outpost/ root@tc:~/outpost/

	ssh tc 'python ~/outpost/tests.py'
	ssh tc 'systemctl start outpost'

view:
	rsync -avz $HOME/codes/ranger/outpost/analysis/ root@tc:/var/www/html/analysis/ \
	 --exclude="*.json*" --exclude="*.py" --exclude="*.txt"