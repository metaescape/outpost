import requests
import json
from functools import lru_cache
import os
import datetime


class GeoLocator:
    def __init__(self, access_key="alibaba-inc"):
        self.base_url = "http://ip.taobao.com/outGetIpInfo"
        self.access_key = access_key
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ip2location_path = os.path.join(current_dir, "ip2location.json")
        with open(ip2location_path, "r") as f:
            self.ip2location = json.load(f)

        self.session_dict = {}

    def get_from_cache(self, ip):
        # check if the ip is in the ip2location and is not out of date and
        # the location is not "地球"
        if ip not in self.ip2location:
            return None
        last_datetime_str = self.ip2location[ip][-1]
        # convert last_datetime_str like "2024-01-31T12:49:43" to datetime
        last_datetime = datetime.datetime.strptime(
            last_datetime_str, "%Y-%m-%dT%H:%M:%S"
        )
        now = datetime.datetime.now()
        if now - last_datetime > datetime.timedelta(days=180):  # out of date
            return None
        location = self.ip2location[ip][0]
        if "地球" in location:
            return None
        return tuple(location.split(":"))

    def get_location(self, ip):
        cache_result = self.get_from_cache(ip)
        if cache_result:
            return cache_result

        try:
            return self.get_location_from_server(ip)
        except Exception as e:
            return "地球", "地球"

    def get_location_from_server(self, ip):
        response = requests.get(
            f"{self.base_url}?ip={ip}&accessKey={self.access_key}",
            timeout=10,
        )
        ip_info = response.json()
        country = ip_info["data"]["country"]
        city = ip_info["data"]["city"]
        if country == "XX":
            country = "地球"
        if city == "XX":
            city = country
        return country, city


# add main for manual request
if __name__ == "__main__":
    # convert_old_json() # only need to run once
    geo = GeoLocator()
    print(geo.get_location("153.127.35.18"))