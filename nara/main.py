import pathlib
import datetime
import json

import pandas as pd
import requests

KANJA_URL = "http://www.pref.nara.jp/secure/227193/%E5%A5%88%E8%89%AF%E7%9C%8C_01%E6%96%B0%E5%9E%8B%E3%82%B3%E3%83%AD%E3%83%8A%E3%82%A6%E3%82%A4%E3%83%AB%E3%82%B9%E6%84%9F%E6%9F%93%E8%80%85_%E6%82%A3%E8%80%85%E3%83%AA%E3%82%B9%E3%83%88.xlsx"

SYUKEI_URL = "http://www.pref.nara.jp/secure/227221/%E5%A5%88%E8%89%AF%E7%9C%8C_02%E6%96%B0%E5%9E%8B%E3%82%B3%E3%83%AD%E3%83%8A%E3%82%A6%E3%82%A4%E3%83%AB%E3%82%B9%E6%84%9F%E6%9F%93%E8%80%85_%E6%82%A3%E8%80%85%E9%9B%86%E8%A8%88%E8%A1%A8.xlsx"

DOWNLOAD_DIR = "download"
DATA_DIR = "data"


def get_file(url, file_name, dir="."):

    r = requests.get(url)

    p = pathlib.Path(dir, file_name)
    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open(mode="wb") as fw:
        fw.write(r.content)

    return p


JST = datetime.timezone(datetime.timedelta(hours=+9), "JST")

dt_now = datetime.datetime.now(JST)

data = {"lastUpdate": dt_now.strftime("%Y/%m/%d %H:%M")}

# 新型コロナウイルス陽性感染者及び患者リスト

kanja_path = get_file(KANJA_URL, "kanja.xlsx", DOWNLOAD_DIR)

dt_update = pd.read_excel(kanja_path, nrows=1, header=None).iat[0, 1]

df_kanja = pd.read_excel(kanja_path, skiprows=1)

df_kanja.rename(columns={"患者_年代": "年代", "患者_性別": "性別"}, inplace=True)

df_kanja["発表日"] = df_kanja["公表_年月日"].dt.strftime("%Y-%m-%dT08:00:00.000Z").fillna("")

df_kanja["発症日"] = df_kanja["発症_年月日"].dt.strftime("%Y-%m-%d 00:00:00").fillna("")

df_kanja["住居地"] = ""
df_kanja["職業"] = ""
df_kanja["状態"] = ""
df_kanja["症状"] = ""
df_kanja["備考"] = df_kanja["患者_居住地"].fillna("")

patients = df_kanja.loc[
    :, ["No", "発表日", "住居地", "年代", "性別", "職業", "状態", "症状", "発症日", "備考"]
]

data["patients"] = {
    "data": patients.to_dict(orient="records"),
    "date": dt_update.strftime("%Y/%m/%d"),
}

# 新型コロナウイルス感染者及び患者集計表

syukei_path = get_file(SYUKEI_URL, "syukei.xlsx", DOWNLOAD_DIR)

dt_update = pd.read_excel(syukei_path, nrows=1, header=None).iat[0, 1]

df_syukei = (
    pd.read_excel(syukei_path, skiprows=1, index_col="公表_年月日")
    .drop(columns=["全国地方公共団体コード", "都道府県名", "備考"])
    .asfreq("D")
)

df_syukei["日付"] = df_syukei.index.strftime("%Y-%m-%dT08:00:00.000Z")

patients_summary = df_syukei.loc[:, ["日付", "陽性確認_件数"]].copy()
patients_summary.rename(columns={"陽性確認_件数": "小計"}, inplace=True)
patients_summary["小計"] = patients_summary["小計"].fillna(0).astype(int)

data["patients_summary"] = {
    "date": dt_update.strftime("%Y/%m/%d"),
    "data": patients_summary.to_dict(orient="recodes"),
}

## main_summary

main_sum = df_syukei.iloc[-1].fillna(0).astype(int)

data["main_summary"] = {
    "date": dt_update.strftime("%Y/%m/%d"),
    "attr": "検査実施人数",
    "value": 0,
    "children": [
        {
            "attr": "感染者数累計",
            "value": int(main_sum["入院者数_累計"]),
            "children": [
                {
                    "attr": "現在感染者数",
                    "value": int(main_sum["現在感染者数"]),
                    "children": [
                        {
                            "attr": "入院中",
                            "value": int(main_sum["入院者数"]),
                            "children": [{"attr": "重症", "value": int(main_sum["重症"])}],
                        },
                        {"attr": "宿泊療養", "value": int(main_sum["宿泊療養者数"])},
                        {"attr": "自宅療養", "value": int(main_sum["自宅療養数"])},
                    ],
                },
                {"attr": "退院等累計", "value": int(main_sum["退院者_累計"])},
                {"attr": "死亡", "value": int(main_sum["死亡者_累計"])},
            ],
        }
    ],
}

## sickbeds_summary

data["sickbeds_summary"] = {
    "data": {
        "残り病床数": int(main_sum["感染症対応病床数"] - main_sum["入院者数"]),
        "入院患者数": int(main_sum["入院者数"]),
    },
    "date": dt_update.strftime("%Y/%m/%d"),
    "total": {"宿泊療養室数": int(main_sum["宿泊療養室数"]), "総病床数": int(main_sum["感染症対応病床数"]),},
}

# json保存

p = pathlib.Path(DATA_DIR, "data.json")
p.parent.mkdir(parents=True, exist_ok=True)

with p.open(mode="w", encoding="utf-8") as fw:
    json.dump(data, fw, ensure_ascii=False, indent=4)
