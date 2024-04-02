import datetime


def gitstar(cnf, last):
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
        if repo_response.status_code != 200:
            continue

        new_stars = []
        i = 0
        for i, star in enumerate(repo_response.json()):
            star_time = star["starred_at"]
            star_datetime = datetime.datetime.strptime(
                star_time, "%Y-%m-%dT%H:%M:%SZ"
            )
            user = star["user"]["login"]
            if star_datetime > last:
                new_stars.append(user)
        if new_stars:
            gitcontent.append(
                f"{repo} star 新增 {','.join(new_stars)}, 共 {i + 1} star\n"
            )
    return gitcontent


def safe_gitstar(cnf, last):
    try:
        return gitstar(cnf, last)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        line_number = exc_traceback.tb_lineno  # type: ignore
        return [f"Git 仓库信息获取失败于 line {line_number}: {str(e)}"]


def test_gitstar():
    gap = 2000
    last = datetime.datetime.today() - timedelta(hours=gap)
    return gitstar(last)
