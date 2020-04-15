# -*- coding: utf-8 -*-

import datetime
import json
import os

import pandas as pd


COUNTS_FILE = "./download/toyama_counts.csv"
PATIENTS_FILE = "./download/toyama_patients.csv"
OUT_DIR = "./data"

PREF_CODE = "160008"
PREF_NAME = "富山県"
CITY_NAME = ""


if not os.path.exists(OUT_DIR):
    os.mkdir(OUT_DIR)

JST = datetime.timezone(datetime.timedelta(hours=+9), "JST")

# 現在の時刻
dt_now = datetime.datetime.now(JST).strftime("%Y/%m/%d %H:%M")

data = {"lastUpdate": dt_now}

df_counts = pd.read_csv(
    COUNTS_FILE, index_col="年月日", parse_dates=True, dtype={"備考": "object"},
)

df_counts["日付"] = df_counts.index.strftime("%Y-%m-%d")

data["inspection_status_summary"] = {
    "date": dt_now,
    "data": {
        "attr": "検査実施人数",
        "value": int(df_counts["検査実施人数"].sum()),
        "children": [
            {"attr": "陽性人数", "value": int(df_counts["陽性人数"].sum())},
            {"attr": "陰性人数", "value": int(df_counts["陰性人数"].sum())},
        ],
    },
}

# 検査実施人数
df_insp = df_counts.loc[:, ("日付", "検査実施人数")].copy()
df_insp.rename(columns={"検査実施人数": "小計"}, inplace=True)

data["inspection_persons"] = {"date": dt_now, "data": df_insp.to_dict(orient="recodes")}

# 陽性患者数
df_pats = df_counts.loc[:, ("日付", "陽性人数")].copy()
df_pats.rename(columns={"陽性人数": "小計"}, inplace=True)

data["patients_summary"] = {"date": dt_now, "data": df_pats.to_dict(orient="recodes")}

# 一般相談件数
df_contacts = df_counts.loc[:, ("日付", "一般相談件数")].copy()
df_contacts.rename(columns={"一般相談件数": "小計"}, inplace=True)

data["contacts"] = {"date": dt_now, "data": df_contacts.to_dict(orient="recodes")}

# 帰国者・接触者相談件数
df_querents = df_counts.loc[:, ("日付", "帰国者相談件数")].copy()
df_querents.rename(columns={"帰国者相談件数": "小計"}, inplace=True)

data["querents"] = {"date": dt_now, "data": df_querents.to_dict(orient="recodes")}

# 陽性患者の属性
df_kanja = pd.read_csv(
    PATIENTS_FILE,
    index_col="No",
    dtype={"発症日": "object", "年代": "object", "備考": "object"},
)

df_kanja.rename(columns={"公表年月日": "公表日"}, inplace=True)

df_patients = df_kanja.loc[:, ("公表日", "居住地", "年代", "性別")].copy()

data["patients"] = {"date": dt_now, "data": df_patients.to_dict(orient="recodes")}

with open(os.path.join(OUT_DIR, "data.json"), "w", encoding="utf-8") as fw:
    json.dump(data, fw, ensure_ascii=False, indent=4)

# コンバーター

df_counts["備考"] = df_counts["備考"].fillna("")

# 検査実施人数
df_counts["実施_年月日"] = df_counts.index.strftime("%Y-%m-%d")

# 陰性確認数
df_counts["完了_年月日"] = df_counts.index.strftime("%Y-%m-%d")

# コールセンター相談件数
df_counts["受付_年月日"] = df_counts.index.strftime("%Y-%m-%d")

df_counts["全国地方公共団体コード"] = PREF_CODE
df_counts["都道府県名"] = PREF_NAME
df_counts["市区町村名"] = CITY_NAME

# 人数（検査実施・陰性）

# 検査実施人数
df_counts.rename(columns={"検査実施人数": "検査実施_人数"}, inplace=True)

test_people = df_counts.loc[
    :, ["実施_年月日", "全国地方公共団体コード", "都道府県名", "市区町村名", "検査実施_人数", "備考"]
].copy()

test_people.to_csv(
    os.path.join(OUT_DIR, "160001_toyama_covid19_test_people.csv"),
    index=False,
    encoding="utf-8",
)

# 陰性確認数
df_counts.rename(columns={"陰性人数": "陰性確認_件数"}, inplace=True)

confirm_negative = df_counts.loc[
    :, ["完了_年月日", "全国地方公共団体コード", "都道府県名", "市区町村名", "陰性確認_件数", "備考"]
].copy()

confirm_negative.to_csv(
    os.path.join(OUT_DIR, "160001_toyama_covid19_confirm_negative.csv"),
    index=False,
    encoding="utf-8",
)

# 相談件数（一般・帰国者・接触者相談センター相談件数）

# 一般相談件数
call_center = df_counts.loc[
    :, ["受付_年月日", "全国地方公共団体コード", "都道府県名", "市区町村名", "一般相談件数"]
].copy()

call_center.rename(columns={"一般相談件数": "相談件数"}, inplace=True)
call_center.to_csv(
    os.path.join(OUT_DIR, "160001_toyama_covid19_call_center.csv"),
    index=False,
    encoding="utf-8",
)

# 帰国者・接触者相談センター相談件数
hot_line = df_counts.loc[
    :, ["受付_年月日", "全国地方公共団体コード", "都道府県名", "市区町村名", "帰国者相談件数"]
].copy()

hot_line.rename(columns={"帰国者相談件数": "相談件数"}, inplace=True)
hot_line.to_csv(
    os.path.join(OUT_DIR, "160001_toyama_covid19_hot_line.csv"),
    index=False,
    encoding="utf-8",
)

# 陽性患者情報

df_kanja.rename(
    columns={
        "公表日": "公表_年月日",
        "発症日": "発症_年月日",
        "居住地": "患者_居住地",
        "年代": "患者_年代",
        "性別": "患者_性別",
        "職業": "患者_職業",
        "症状": "患者_状態",
        "渡航歴の有無": "患者_渡航歴の有無フラグ",
        "状態": "患者_退院済フラグ",
    },
    inplace=True,
)

df_kanja["全国地方公共団体コード"] = PREF_CODE
df_kanja["都道府県名"] = PREF_NAME
df_kanja["市区町村名"] = CITY_NAME

df_kanja

df_kanja["患者_退院済フラグ"] = (
    df_kanja["患者_退院済フラグ"].replace({"入院中": 0, "退院": 1}).astype("Int64")
)

df_kanja["患者_渡航歴の有無フラグ"] = (
    df_kanja["患者_渡航歴の有無フラグ"].replace({"x": 0, "o": 1}).astype("Int64")
)

df_kanja["患者_症状"] = ""

patients = df_kanja.loc[
    :,
    [
        "全国地方公共団体コード",
        "都道府県名",
        "市区町村名",
        "公表_年月日",
        "発症_年月日",
        "患者_居住地",
        "患者_年代",
        "患者_性別",
        "患者_職業",
        "患者_状態",
        "患者_症状",
        "患者_渡航歴の有無フラグ",
        "患者_退院済フラグ",
        "備考",
    ],
]

patients.to_csv(
    os.path.join(OUT_DIR, "160001_toyama_covid19_patients.csv"),
    index=False,
    encoding="utf-8",
)
