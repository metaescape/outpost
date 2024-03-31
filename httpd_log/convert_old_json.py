import os
import json


def convert_old_json():
    """
    original format of ip2location.json(visitors_lookup.json) is
    {
    "140.237.123.195": {
        "loc": "中国:中国",
        "cnt": 3
    },
    ...
    }

    convert to :
        {
    "140.237.123.195": {["中国:中国", 3, "2024-03-31T12:49:43"]},
    },
    the last element is the time of the last visit
    """
    # use relative path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "visitors_lookup.json")

    with open(file_path, "r") as f:
        ip2location = json.load(f)

    new_ip2location = {}
    for ip, info in ip2location.items():
        loc, cnt = info["loc"], info["cnt"]
        new_ip2location[ip] = [loc, cnt, "2024-01-31T12:49:43"]

    new_file_path = os.path.join(current_dir, "ip2location.json")
    with open(new_file_path, "w") as f:
        json.dump(new_ip2location, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    convert_old_json()  # only need to run once
