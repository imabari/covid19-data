import datetime
import json
import pathlib
import re
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

import camelot
import pycurl
from retry import retry


@retry(tries=5, delay=5, backoff=3)
def get_file(url, dir="."):

    p = pathlib.Path(dir, pathlib.PurePath(url).name)

    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open(mode="wb") as f:

        c = pycurl.Curl()
        c.setopt(c.URL, url)
        c.setopt(c.WRITEDATA, f)
        c.perform()
        c.close()

    return p


def my_parser(s):

    if s:
        y = dt_now.year
        m, d = map(int, re.findall("[0-9]{1,2}", s))

        return pd.Timestamp(year=y, month=m, day=d)

    else:
        return pd.NaT


url = "https://www.pref.miyazaki.lg.jp/kenko/hoken/kansensho/covid19/hassei.html"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
}

r = requests.get(url, headers=headers)
r.raise_for_status()

# PDFのURLをスクレイピング
soup = BeautifulSoup(r.content, "html.parser")
tag = soup.find("a", class_="icon_pdf", text=re.compile("^宮崎県内における感染者発生状況"))

link = urljoin(url, tag.get("href"))

# PDFダウンロード
file = get_file(link)

tables = camelot.read_pdf(
    str(file), pages="2-end", split_text=True, strip_text="\n", line_scale=40
)

# 3ページ目にタイトルがあるか確認、タイトルがない場合は変更
df0 = pd.concat([table.df.T.set_index(0).T.set_index("No.") for table in tables])

# patients

df1 = (
    df0["現在の状況"]
    .str.extract("(\d{1,2}月\d{1,2}日)?(入院中|退院|死亡)")
    .rename(columns={0: "退院日", 1: "退院"})
)

df_kanja = pd.concat([df0, df1], axis=1)

dt_now = datetime.datetime.now()
dt_update = dt_now.strftime("%Y/%m/%d")

data = {"lastUpdate": dt_update}

df_kanja["判明日"] = df_kanja["判明日"].apply(my_parser)

df_kanja["退院日"] = df_kanja["退院日"].fillna("").apply(my_parser)

df_kanja["リリース日"] = df_kanja["判明日"].dt.strftime("%Y-%m-%dT08:00:00.000Z")
df_kanja["date"] = df_kanja["判明日"].dt.strftime("%Y-%m-%d")

df_patients = df_kanja.loc[:, ["リリース日", "居住地", "年代", "性別", "退院", "date"]]

data["patients"] = {
    "data": df_patients.to_dict(orient="records"),
    "date": dt_update,
}

# patients_summary

df_patients_sum = (
    df_kanja["判明日"].value_counts().sort_index().asfreq("D", fill_value=0).reset_index()
)

df_patients_sum["日付"] = df_patients_sum["index"].dt.strftime("%Y-%m-%dT08:00:00.000Z")

df_patients_sum.rename(columns={"判明日": "小計"}, inplace=True)

df_patients_sum.drop(columns=["index"], inplace=True)

data["patients_summary"] = {
    "data": df_patients_sum.to_dict(orient="records"),
    "date": dt_update,
}

# main_summary

r = requests.get(
    "https://www.pref.miyazaki.lg.jp/kansensho-taisaku/kenko/hoken/covid19.html",
    headers=headers,
)
r.raise_for_status()

soup = BeautifulSoup(r.content, "html.parser")

table = soup.find("h3", text="相談・検査件数").find_next_sibling("table")

df_test = pd.read_html(table.prettify(), index_col=0, header=[0, 1])[0]

sr_main_sum = (
    df_kanja["退院"].value_counts().reindex(["入院中", "退院", "死亡"]).fillna(0).astype(int)
)

data["main_summary"] = {
    "attr": "検査実施人数",
    "value": int(df_test.loc["累計", (["検査件数"], ["合計"])]),
    "children": [
        {
            "attr": "陽性患者数",
            "value": int(df_test.loc["累計", (["検査件数"], ["陽性件数"])]),
            "children": [
                {
                    "attr": "入院中",
                    "value": int(sr_main_sum["入院中"]),
                    "children": [
                        {"attr": "軽症・中等症", "value":int(sr_main_sum["入院中"])},
                        {"attr": "重症", "value": 0},
                    ],
                },
                {"attr": "退院", "value": int(sr_main_sum["退院"])},
                {"attr": "死亡", "value": int(sr_main_sum["死亡"])},
            ],
        }
    ],
}

with open("data.json", "w", encoding="utf-8") as fw:
    json.dump(data, fw, ensure_ascii=False, indent=4)
