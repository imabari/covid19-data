
import copy
import datetime
import json
import re

import jaconv
import requests
import pandas as pd
import simplejson as json
from bs4 import BeautifulSoup

def get_title(tag):
    if tag.name == "h2":
        if tag.get_text(strip=True) == "新型コロナウイルス感染症の県内における発生状況":
            return True

    return False

# 和暦から西暦のdateに変換
def wareki2date(s):

    m = re.match(r"令和(\d{1,2})年(\d{1,2})月(\d{1,2})日", s)

    year, month, day = map(int, m.groups())

    year += 2018

    result = datetime.datetime(year, month, day, tzinfo=JST)

    return result

def my_parser(s):

    dt_str = jaconv.z2h(s.strip(), kana=False, digit=True, ascii=True)

    y = dt_now.year
    m, d = map(int, re.findall(r"(\d{1,2})", dt_str))

    return pd.Timestamp(year=y, month=m, day=d)

def df_conv(df):

    df0 = df.iloc[1:, :].copy()

    df0.columns = ["期間", "件数", "内訳"]

    df1 = pd.concat(
        [
            df0["期間"].str.split("～", expand=True).rename(columns={0: "開始", 1: "終了"}),
            df0["内訳"].str.split("、", expand=True),
        ],
        axis=1,
    )

    # 日付に変換
    df1["開始"] = df1["開始"].apply(my_parser)
    df1["終了"] = df1["終了"].apply(my_parser)

    df2 = df1.melt(id_vars=["開始", "終了"]).dropna()

    df3 = (
        df2["value"]
        .str.extract("([0-9,]+)[日件]([0-9,]+)件", expand=True)
        .rename(columns={0: "日", 1: "小計"})
        .astype(int)
    )

    df4 = pd.concat([df2, df3], axis=1)

    df4["日付"] = df4.apply(
        lambda x: x["開始"].replace(day=x["日"])
        if x["終了"].day < x["日"]
        else x["終了"].replace(day=x["日"]),
        axis=1,
    )

    df = pd.DataFrame({"小計": df4.set_index("日付")["小計"].sort_index().asfreq("D", fill_value=0)})
    df["日付"] = df.index.strftime("%Y-%m-%dT00:00:00+09:00")

    return df.to_dict(orient="records")

# スクレイピング

def kanja_scraping():

    r = requests.get(
        "https://www.pref.yamanashi.jp/koucho/coronavirus/info_coronavirus_prevention.html"
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")

    h2 = soup.find(get_title)

    data = []
    s = ""

    # 下向きに同レベルのタグを抽出

    for tag in h2.find_next_siblings():
        if tag.name == "h4":
            data.append(jaconv.z2h(s.rstrip(), kana=False, digit=True, ascii=True))
            s = ""
        elif tag.name == "h2":
            data.append(jaconv.z2h(s.rstrip(), kana=False, digit=True, ascii=True))
            break

        s += tag.get_text(strip=True) + "\n"

    result = []

    for d in data[1:]:

        # m = re.match("^.+$", d, re.MULTILINE)
        m = re.match(r"県内\d{1,3}例目", d)

        if m:

            temp = {"No": m.group(0)}

            for i in re.finditer(r"(発生判明日|年代|性別|居住地):(.+)$", d, re.MULTILINE):
                temp[i.group(1)] = i.group(2)

                if i.group(1) == "居住地":

                    t = copy.deepcopy(temp)

                    t["リリース日"] = wareki2date(t["発生判明日"]).isoformat()
                    del t["発生判明日"]
                    t["退院"] = None

                    result.append(t)
    return result[::-1]

JST = datetime.timezone(datetime.timedelta(hours=+9))
dt_now = datetime.datetime.now(JST)
dt_update = dt_now.strftime("%Y/%m/%d %H:%M")

data = {"lastUpdate": dt_update}

df1 = pd.read_csv("patients.csv", encoding="utf-8")
df2 = pd.DataFrame(kanja_scraping())

df_kanja = pd.concat([df1, df2])

data["patients"] = {
    "__comments": "陽性患者の属性",
    "data": df_kanja.to_dict(orient="records"),
    "date": dt_update,
}

ser_patients_sum = pd.to_datetime(df_kanja["リリース日"]).value_counts().sort_index()

df_patients_sum = pd.DataFrame({"小計": ser_patients_sum.asfreq("D", fill_value=0)})
df_patients_sum["日付"] =df_patients_sum.index.strftime("%Y-%m-%dT00:00:00+09:00")

data["patients_summary"] = {
    "__comments": "陽性患者数",
    "data": df_patients_sum.to_dict(orient="recodes"),
    "date": dt_update,
}

dfs = pd.read_html("https://www.pref.yamanashi.jp/koucho/coronavirus/info_coronavirus_data.html")

dfs[0]

ser_main = dfs[0].iloc[1].str.extractall(r"(\d+)人")[0]

ser_main.index = ["入院中", "重症", "宿泊療養", "退院", "死亡", "累計"]

ser_main = ser_main.astype(int)

data["main_summary"] = {
    "attr": "陽性患者数",
    "value": int(ser_main["累計"]),
    "children": [
        {
            "attr": "入院中",
            "value": int(ser_main["入院中"]),
            "children": [
                {"attr": "軽症・中等症", "value": int(ser_main["入院中"] - ser_main["重症"]),},
                {"attr": "重症", "value": int(ser_main["重症"])},
            ],
        },
        {"attr": "宿泊療養", "value": int(ser_main["宿泊療養"])},
        {"attr": "退院", "value": int(ser_main["退院"])},
        {"attr": "死亡", "value": int(ser_main["死亡"])},
    ],
}

len(dfs)

# 県衛生環境研究所における疑似症例の検査状況

data["inspections_summary"] = {
    "__comments": "県内の疑似症例の検査状況",
    "data": df_conv(dfs[1]),
    "date": dt_update,
}

# 帰国者・接触者相談センター

data["querents"] = {
    "__comments": "帰国者・接触者相談センター相談件数",
    "data": df_conv(dfs[2]),
    "date": dt_update,
}

# 新型コロナウイルス感染症専用相談ダイヤル

data["contacts"] = {
    "__comments": "新型コロナウイルス感染症専用相談ダイヤル相談件数",
    "data": df_conv(dfs[3]),
    "date": dt_update,
}

with open("data.json", "w", encoding="utf-8") as fw:
    json.dump(data, fw, ignore_nan=True, ensure_ascii=False, indent=4)
