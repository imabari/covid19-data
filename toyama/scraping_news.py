import json
import datetime
import re

import requests
from bs4 import BeautifulSoup

url = "http://www.pref.toyama.jp/sections/1118/virus/index.html"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
}

r = requests.get(url, headers=headers)
r.raise_for_status()
soup = BeautifulSoup(r.content, "html.parser")

td = soup.find("table", width="730").find("td")

m = re.search("【更新情報.+】", td.text)

if m:
    year, month, day = map(int, re.findall("(\d+)", m.group()))

    dt_update = datetime.date(year, month, day).isoformat()

    news = [
        {"date": dt_update, "url": i.get("href"), "text": i.get_text(strip=True)}
        for i in td.find_all("a")
    ]

    data = {"newsItems": news}

    with open("../data/news.json", "w", encoding="utf-8") as fw:
        json.dump(data, fw, ensure_ascii=False, indent=4)
