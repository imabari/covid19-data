import datetime
import json
import re
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

import camelot


def pdf_link(url):

    r = requests.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")

    tag = soup.find("a", text=re.compile("^陽性確認者一覧.+?PDF"))

    link = urljoin(url, tag.get("href"))

    return link


def my_parser(s):

    if s != "調査中":
        y = dt_now.year
        m, d = map(int, re.findall("[0-9]{1,2}", s))

        return pd.Timestamp(year=y, month=m, day=d)

    else:
        return pd.NaT


dt_now = datetime.datetime.now()

url = "http://www.pref.saitama.lg.jp/a0701/shingatacoronavirus.html"

r = requests.get(url)
r.raise_for_status()
soup = BeautifulSoup(r.content, "html.parser")

# main_summary

tag = soup.find("div", class_="box_info_ttl")

# 更新日付取得
s_date = tag.find("span", class_="txt_big").get_text(strip=True)
l_date = list(map(int, re.findall("(\d{1,2})", s_date)))

dt_update = datetime.datetime(dt_now.year, *l_date).strftime("%Y/%m/%d %H:%M")

data = {"lastUpdate": dt_update}

# 人数取得
main_sum = [int(i.replace(",", "")) for i in re.findall("([0-9,]+)人", tag.get_text())]

data["main_summary"] = {
    "attr": "検査実施人数",
    "value": main_sum[7],
    "children": [
        {
            "attr": "陽性患者数",
            "value": main_sum[0],
            "children": [
                {
                    "attr": "入院中",
                    "value": main_sum[2],
                    "children": [
                        {"attr": "軽症・中等症", "value": main_sum[3]},
                        {"attr": "重症", "value": main_sum[4]},
                    ],
                },
                {"attr": "退院", "value": main_sum[5]},
                {"attr": "死亡", "value": main_sum[6]},
            ],
        }
    ],
}

# 発生状況リンク取得
href = tag.find("a", text=re.compile("^県内の発生状況")).get("href")
link = pdf_link(urljoin(url, href))

# patients

# PDF読込
tables = camelot.read_pdf(
    link, pages="all", split_text=True, strip_text="\n", line_scale=40
)

df_tmp = pd.concat([table.df for table in tables]).reset_index(drop=True)

df_kanja = df_tmp.T.set_index(0).T

df_kanja.rename(columns={"NO.": "No"}, inplace=True)

df_kanja["No"] = df_kanja["No"].astype(int)
df_kanja.sort_values("No", inplace=True)

df_kanja["公表日"] = df_kanja["判明日"].apply(my_parser)

df_kanja["リリース日"] = df_kanja["公表日"].dt.strftime("%Y-%m-%dT08:00:00.000Z")
df_kanja.loc[df_kanja["公表日"].isnull(), "リリース日"] = "調査中"

df_kanja["date"] = df_kanja["公表日"].dt.strftime("%Y-%m-%d")
df_kanja.loc[df_kanja["公表日"].isnull(), "date"] = "調査中"

df_kanja["公表日"].fillna(method="ffill", inplace=True)

df_patients = df_kanja.reindex(
    columns=["No", "リリース日", "年代", "性別", "居住地", "退院", "date"]
).fillna("")

data["patients"] = {
    "data": df_patients.to_dict(orient="records"),
    "date": dt_update,
}

# CSV保存
df_patients.to_csv("patients.csv", index=None, encoding="utf-8")

# patients_summary

df_patients_sum = (
    df_kanja["公表日"].value_counts().sort_index().asfreq("D", fill_value=0).reset_index()
)

df_patients_sum["日付"] = df_patients_sum["index"].dt.strftime("%Y-%m-%dT08:00:00.000Z")

df_patients_sum.rename(columns={"公表日": "小計"}, inplace=True)

df_patients_sum.drop(columns=["index"], inplace=True)

data["patients_summary"] = {
    "data": df_patients_sum.to_dict(orient="records"),
    "date": dt_update,
}

with open("data.json", "w", encoding="utf-8") as fw:
    json.dump(data, fw, ensure_ascii=False, indent=4)
