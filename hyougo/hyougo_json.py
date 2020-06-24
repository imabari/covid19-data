import datetime
import json
import pathlib
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

import jsonschema
from retry import retry

PCR_XLSX = "https://web.pref.hyogo.lg.jp/kk03/documents/pcr.xlsx"
YOUSEI_XLSX = "https://web.pref.hyogo.lg.jp/kk03/documents/yousei.xlsx"
KANJA_HTML = "https://web.pref.hyogo.lg.jp/kk03/corona_kanjyajyokyo.html"

DOWNLOAD_DIR = "download"
DATA_DIR = "data"

# ダウンロード


@retry(tries=5, delay=5, backoff=3)
def get_file(url, dir="."):

    r = requests.get(url)

    p = pathlib.Path(dir, pathlib.PurePath(url).name)
    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open(mode="wb") as fw:
        fw.write(r.content)

    return p

# SCHEMA

AGE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "data": {
            "type": "object",
            "additionalProperties": {"default": 0, "type": "integer"},
        },
        "last_update": {"format": "date-time", "type": "string"},
    },
    "required": ["data", "last_update"],
}

AGE_SUMMARY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "data": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"default": 0, "type": "integer"},
            },
        },
        "labels": {
            "type": "array",
            "items": {"pattern": "^[0-9]{1,2}/[0-9]{1,2}$", "type": "string"},
        },
        "last_update": {"format": "date-time", "type": "string",},
    },
    "required": ["data", "labels", "last_update"],
}

CLUSTERS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "data": {
            "type": "array",
            "items": {
                "type": "object",
                "oneOf": [
                    {"properties": {"日付": {"type": "string", "format": "date-time"}},},
                    {"additionalProperties": {"type": "integer"},},
                ],
            },
        },
        "last_update": {"type": "string", "format": "date-time"},
    },
    "required": ["data", "last_update"],
}

CLUSTERS_SUMMARY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "data": {
            "type": "object",
            "additionalProperties": {"default": 0, "type": "integer"},
        },
        "last_update": {"format": "date-time", "type": "string",},
    },
    "required": ["data", "last_update"],
}

INSPECTIONS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "data": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "判明日": {"type": "string", "format": "date"},
                    "地方衛生研究所等": {"type": "integer"},
                    "民間検査機関等": {
                        "type": "object",
                        "additionalProperties": {"type": "integer"},
                    },
                    "陽性確認": {"type": "integer"},
                },
                "required": ["判明日", "地方衛生研究所等", "民間検査機関等", "陽性確認"],
            },
        },
        "last_update": {"type": "string", "format": "date-time"},
    },
    "required": ["data", "last_update"],
}

INSPECTIONS_SUMMARY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "data": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"default": 0, "type": "integer"},
            },
        },
        "labels": {
            "type": "array",
            "items": {"pattern": r"^[0-9]{1,2}/[0-9]{1,2}$", "type": "string"},
        },
        "last_update": {"format": "date-time", "type": "string",},
    },
    "required": ["data", "labels", "last_update"],
}

MAIN_SUMMARY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-06/schema#",
    "$ref": "#/definitions/Main",
    "definitions": {
        "Main": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "attr": {"type": "string"},
                "value": {"type": "integer", "default": 0},
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Inspections"},
                },
                "last_update": {"format": "date-time", "type": "string",},
            },
            "required": ["attr", "children", "last_update", "value"],
            "title": "Main",
        },
        "Inspections": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "attr": {"type": "string"},
                "value": {"type": "integer", "default": 0},
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Patients"},
                },
            },
            "required": ["attr", "children", "value"],
            "title": "Inspections",
        },
        "Patients": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "attr": {"type": "string"},
                "value": {"type": "integer", "default": 0},
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Symptoms"},
                },
            },
            "required": ["attr", "value"],
            "title": "Patients",
        },
        "Symptoms": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "attr": {"type": "string"},
                "value": {"type": "integer", "default": 0},
            },
            "required": ["attr", "value"],
            "title": "Symptoms",
        },
    },
}

PATIENTS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$ref": "#/definitions/Main",
    "definitions": {
        "Main": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "data": {"type": "array", "items": {"$ref": "#/definitions/Datum"}},
                "last_update": {"type": "string"},
            },
            "required": ["data", "last_update"],
            "title": "Main",
        },
        "Datum": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "No": {"type": "integer"},
                "居住地": {"type": "string"},
                "年代": {"$ref": "#/definitions/Age"},
                "性別": {"$ref": "#/definitions/Sex"},
                "備考": {"type": "string"},
                "退院": {"type": "null"},
                "date": {"type": "string", "format": "date"},
                "リリース日": {"type": "string", "format": "date"},
                "曜日": {"$ref": "#/definitions/Week"},
            },
            "required": ["date", "リリース日", "備考", "居住地", "年代", "性別", "曜日", "No", "退院"],
            "title": "Datum",
        },
        "Age": {
            "type": "string",
            "enum": [
                "10歳未満",
                "10代",
                "20代",
                "30代",
                "40代",
                "50代",
                "60代",
                "70代",
                "80代",
                "90歳以上",
                "非公表",
            ],
            "title": "Age",
        },
        "Sex": {"type": "string", "enum": ["男性", "女性"], "title": "Sex"},
        "Week": {
            "type": "string",
            "enum": ["月", "火", "水", "木", "金", "土", "日"],
            "title": "Week",
        },
    },
}

PATIENTS_SUMMARY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "data": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "日付": {"type": "string", "format": "date"},
                    "小計": {"default": 0, "type": "integer"},
                },
                "required": ["小計", "日付"],
            },
        },
        "last_update": {"format": "date-time", "type": "string",},
    },
    "required": ["data", "last_update"],
}

# データラングリング


def dumps_json(file_name, json_data, dir=DATA_DIR):

    p = pathlib.Path(dir, file_name)

    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open(mode="w") as fw:
        json.dump(json_data, fw, ensure_ascii=False, indent=4)

# 最終更新日

JST = datetime.timezone(datetime.timedelta(hours=+9))
dt_now = datetime.datetime.now(JST)

last_update = dt_now.replace(hour=0, minute=0, second=0, microsecond=0)
last_update


dumps_json("last_update.json", {"last_update": last_update.isoformat()})

# pcr.xlsx

pcr_path = get_file(PCR_XLSX, DOWNLOAD_DIR)

df_pcr = pd.read_excel(pcr_path, index_col="年月日").fillna(0).astype(int)

df_pcr.rename(
    columns={
        "検査件数（合計）": "合計",
        "うち地方衛生研究所等によるPCR検査件数": "地方衛生研究所等",
        "うち民間検査機関等によるPCR検査件数": "民間検査機関等_PCR検査",
        "うち民間検査機関等による抗原検査件数": "民間検査機関等_抗原検査",
        "陽性件数": "陽性確認",
    },
    inplace=True,
)

df_pcr["民間検査機関等"] = df_pcr["民間検査機関等_PCR検査"] + df_pcr["民間検査機関等_抗原検査"]

df_pcr["日付"] = df_pcr.index.map(lambda d: pd.Timestamp(d, tz='Asia/Tokyo').isoformat())

# inspections_summary

df_insp_sum = df_pcr.loc[:, ["地方衛生研究所等", "民間検査機関等"]].copy()

labels = df_insp_sum.index.map(lambda x: f"{x.month}/{x.day}")

inspections_summary = {
    "data": df_insp_sum.to_dict(orient="list"),
    "labels": labels.tolist(),
    "last_update": last_update.isoformat(),
}

jsonschema.validate(inspections_summary, INSPECTIONS_SUMMARY_SCHEMA)
dumps_json("inspections_summary.json", inspections_summary)

# inspections

df_insp = df_pcr.loc[:, ["地方衛生研究所等", "民間検査機関等_PCR検査", "民間検査機関等_抗原検査", "陽性確認"]].copy()
df_insp["判明日"] = df_insp.index.strftime("%Y-%m-%d")

df_insp.sort_index(inplace=True)

insp_dict = [
    {
        "判明日": row["判明日"],
        "地方衛生研究所等": row["地方衛生研究所等"],
        "民間検査機関等": {"PCR検査": row["民間検査機関等_PCR検査"], "抗原検査": row["民間検査機関等_抗原検査"]},
        "陽性確認": row["陽性確認"],
    }
    for _, row in df_insp.iterrows()
]

inspections = {
    "data": insp_dict,
    "last_update": last_update.isoformat(),
}

jsonschema.validate(inspections, INSPECTIONS_SCHEMA)
dumps_json("inspections.json", inspections)

# parent_summary

df_pts = df_pcr.loc[:, ["日付", "陽性確認"]].copy()

df_pts.rename(columns={"陽性確認": "小計"}, inplace=True)

patients_summary = {
    "data": df_pts.to_dict(orient="records"),
    "last_update": last_update.isoformat(),
}

jsonschema.validate(patients_summary, PATIENTS_SUMMARY_SCHEMA)
dumps_json("patients_summary.json", patients_summary)

# kanjya.xlsx

p = get_file(KANJA_HTML, DOWNLOAD_DIR)

soup = BeautifulSoup(p.open(encoding="utf-8"), "html.parser")
tag = soup.find("a", class_="icon_excel")

link = urljoin(KANJA_HTML, tag.get("href"))

kanja_path = get_file(link, DOWNLOAD_DIR)

df_head = pd.read_excel(kanja_path, header=None, skiprows=3).dropna(how="all", axis=1)

df_head.columns = ["".join(i).strip() for i in df_head.head(2).fillna("").T.values]
df_tmp = df_head.iloc[2:, :].copy().reset_index(drop=True)

df_kanja = df_tmp[df_tmp["番号"].notnull()].copy()
df_kanja.dropna(how="all", axis=1, inplace=True)
df_kanja.columns = df_kanja.columns.map(lambda s: s.replace("\n", ""))

df_kanja["番号"] = df_kanja["番号"].astype(int)
df_kanja["年代"] = df_kanja["年代"].astype(str)
df_kanja["年代"] = df_kanja["年代"].replace(
    {"10?[歳代]未満": "10歳未満", "90": "90歳以上", "([1-8]0$)": r"\1代"}, regex=True
)

df_kanja["発表日"] = df_kanja["発表日"].apply(
    lambda date: pd.to_datetime(date, unit="D", origin=pd.Timestamp("1899/12/30"))
)

df_kanja["備考欄"] = df_kanja["備考欄"].str.replace("\n", "")
df_kanja.set_index("番号", inplace=True)
df_kanja.to_csv("kanja.tsv", sep="\t")

# 陽性患者数（累計）

len(df_kanja)

# 陽性患者数（日別）
"""
df_pts = (
    df_kanja["発表日"]
    .value_counts()
    .sort_index()
    .asfreq("D", fill_value=0)
    .reset_index()
)

df_pts["日付"] = df_pts["index"].dt.strftime("%Y-%m-%d")
df_pts.rename(columns={"発表日": "小計"}, inplace=True)
df_pts.drop("index", axis=1, inplace=True)

patients_summary = {
    "data": df_pts.to_dict(orient="records"),
    "last_update": last_update.strftime("%Y-%m-%d %H:%M"),
}

jsonschema.validate(patients_summary, PATIENTS_SUMMARY_SCHEMA)
dumps_json("patients_summary.json", patients_summary)
"""

# 陽性患者情報

df_pt = df_kanja.loc[:, ["発表日", "居住地", "年代", "性別", "備考欄"]].sort_index().reset_index()
df_pt.head(10)

df_pt["退院"] = None

df_pt["date"] = df_pt["発表日"].dt.strftime("%Y-%m-%d")
df_pt["リリース日"] = df_pt["発表日"].apply(
    lambda d: pd.Timestamp(d, tz="Asia/Tokyo").isoformat()
)

week = ["月", "火", "水", "木", "金", "土", "日"]

df_pt["曜日"] = df_pt["発表日"].dt.dayofweek.apply(lambda x: week[x])

df_pt["備考欄"] = df_pt["備考欄"].str.replace("NO.|N0.|NO,|N0,|No,", "No.")
df_pt["備考欄"] = df_pt["備考欄"].str.replace("・", "、")
df_pt["備考欄"] = df_pt["備考欄"].fillna("")
df_pt.rename(columns={"番号": "No", "備考欄": "備考"}, inplace=True)

df_pt.drop("発表日", axis=1, inplace=True)


patients = {
    "data": df_pt.to_dict(orient="records"),
    "last_update": last_update.isoformat(),
}

jsonschema.validate(patients, PATIENTS_SCHEMA)
dumps_json("patients.json", patients)

# 年代集計

age_list = [
    "10歳未満",
    "10代",
    "20代",
    "30代",
    "40代",
    "50代",
    "60代",
    "70代",
    "80代",
    "90歳以上",
    "非公表",
]

df_age = df_kanja["年代"].value_counts().sort_index().reindex(age_list, fill_value=0)

df_age = df_age.astype(int)

age = {
    "data": df_age.to_dict(),
    "last_update": last_update.isoformat(),
}

jsonschema.validate(age, AGE_SCHEMA)
dumps_json("age.json", age)

df_ages = pd.crosstab(df_kanja["発表日"], df_kanja["年代"]).reindex(
    age_list, axis=1, fill_value=0
)

df_ages = df_ages.astype(int)

df_agesum = df_ages.asfreq("D", fill_value=0)

df_agesum

labels = df_agesum.index.map(lambda d: f"{d.month}/{d.day}")

age_summary = {
    "data": df_agesum.to_dict(orient="list"),
    "labels": labels.tolist(),
    "last_update": last_update.isoformat(),
}

jsonschema.validate(age_summary, AGE_SUMMARY_SCHEMA)
dumps_json("age_summary.json", age_summary)

# クラスタ概要

df_cluster_sum = df_kanja.loc[:, "認定こども園":"特定できず"].copy().notnull().sum()

clusters_summary = {
    "data": df_cluster_sum.to_dict(),
    "last_update": last_update.isoformat(),
}

jsonschema.validate(clusters_summary, CLUSTERS_SUMMARY_SCHEMA)
dumps_json("clusters_summary.json", clusters_summary)

# クラスタ

df_clusters = df_kanja.loc[:, "認定こども園":"特定できず"].copy().fillna(0)

df_clusters[df_clusters != 0] = 1

df_clusters["発表日"] = df_kanja["発表日"]

pv_clusters = df_clusters.pivot_table(index="発表日", aggfunc="sum").asfreq(
    "D", fill_value=0
)

pv_clusters = df_clusters.pivot_table(index="発表日", aggfunc="sum").asfreq(
    "D", fill_value=0
)

pv_clusters["日付"] = pv_clusters.index.map(
    lambda d: pd.Timestamp(d, tz="Asia/Tokyo").isoformat()
)

clusters = {
    "data": pv_clusters.to_dict(orient="recodes"),
    "last_update": last_update.isoformat(),
}

jsonschema.validate(clusters, CLUSTERS_SCHEMA)
dumps_json("clusters.json", clusters)

# 重複者

(df_kanja.loc[:, "認定こども園":].copy().notnull().sum(axis=1) > 1).sum()

# yousei.xlsx

yousei_path = get_file(YOUSEI_XLSX, DOWNLOAD_DIR)

df_yousei = pd.read_excel(yousei_path, index_col="発表年月日")

df_yousei.columns = df_yousei.columns.map(lambda s: s.replace("（累計）", "").strip())
# df_yousei.index += pd.to_timedelta("1 days")
df_yousei.rename(columns={"中等症以下": "軽症・中等症", "陽性者数": "陽性患者数"}, inplace=True)
df_yousei.drop("発表時間", axis=1, inplace=True)


d = df_yousei.iloc[-1].to_dict()

main_summary = {
    "attr": "検査実施人数",
    "value": d["検査実施人数"],
    "children": [
        {
            "attr": "陽性患者数",
            "value": d["陽性患者数"],
            "children": [
                {
                    "attr": "入院中",
                    "value": d["入院中"],
                    "children": [
                        {"attr": "軽症・中等症", "value": d["軽症・中等症"]},
                        {"attr": "重症", "value": d["重症"]},
                    ],
                },
                {"attr": "死亡", "value": d["死亡"]},
                {"attr": "退院", "value": d["退院"]},
            ],
        }
    ],
    "last_update": last_update.isoformat(),
}

jsonschema.validate(main_summary, MAIN_SUMMARY_SCHEMA)
dumps_json("main_summary.json", main_summary)

# current_patients

ser_cur = df_yousei["入院中"].reindex(df_pcr.index)

df_current = pd.DataFrame({"小計": ser_cur.combine_first(df_pcr["陽性確認"].cumsum())}).diff().fillna(0).astype(int)
df_current["日付"] = df_current.index.map(lambda d: pd.Timestamp(d, tz='Asia/Tokyo').isoformat())

df_cur_pts = df_current.loc[:, ["日付", "小計"]].copy()

current_patients = {
    "data": df_cur_pts.to_dict(orient="records"),
    "last_update": last_update.isoformat(),
}

jsonschema.validate(current_patients, PATIENTS_SUMMARY_SCHEMA)
dumps_json("current_patients.json", current_patients)
