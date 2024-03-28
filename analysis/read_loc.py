import json

path = "raw.page"
pages_statistic = {}
locations_statistic = {}
with open(path) as f:
    log_lines = f.readlines()

    # 解析日志，并提取地理位置和被访问的html页面
    for line in log_lines:
        # 分割日志行以提取相关信息
        parts = line.strip().split(" ")
        if parts == [] or parts == [""]:
            continue
        location = parts[3] + " " + parts[4]
        visited_page = parts[-1]
        if "/categories" not in visited_page:
            pages_statistic[visited_page] = (
                pages_statistic.get(visited_page, 0) + 1
            )

        if "猎户座悬臂" not in parts[3]:
            locations_statistic[location] = (
                locations_statistic.get(location, 0) + 1
            )

pages_loc = {
    "pages": pages_statistic,
    "locations": locations_statistic,
}
# save to json file with utf-8 encoding
with open("pages_loc.json", "w", encoding="utf-8") as f:
    json.dump(pages_loc, f, ensure_ascii=False)
