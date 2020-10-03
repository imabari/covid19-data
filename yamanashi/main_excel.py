import datetime

import simplejson as json
import pandas as pd

dt_now = datetime.datetime.now()
dt_date = dt_now.replace(hour=0, minute=0, second=0, microsecond=0)
dt_yesterday = dt_date - datetime.timedelta(days=1)

dt_update = dt_now.strftime("%Y/%m/%d %H:%M")

data = {"lastUpdate": dt_update}

# 衛生環境研究所におけるPCR検査数

df_pcr = pd.read_excel(
    "https://www.pref.yamanashi.jp/koucho/coronavirus/documents/pcr.xlsx",
    index_col=0,
    skiprows=1,
)

df_pcr.rename(columns={"検査数": "小計"}, inplace=True)

df_pcr = df_pcr[df_pcr.index < dt_date].fillna(0).astype(int)

df_pcr["日付"] = df_pcr.index.map(lambda d: pd.Timestamp(d, tz="Asia/Tokyo").isoformat())

data["inspections_summary"] = {
    "__comments": "県内の疑似症例の検査状況",
    "date": dt_update,
    "data": df_pcr.to_dict(orient="records"),
}

# 電話相談件数

df_soudan = pd.read_excel(
    "https://www.pref.yamanashi.jp/koucho/coronavirus/documents/soudan.xlsx",
    index_col=0,
    skiprows=1,
)

df_soudan = df_soudan[df_soudan.index < dt_date].fillna(0).astype(int)

df_soudan["日付"] = df_soudan.index.map(
    lambda d: pd.Timestamp(d, tz="Asia/Tokyo").isoformat()
)

df_soudan.head(10)

df_contacts = (
    df_soudan.loc[:, ["日付", "専用相談ダイヤル相談件数"]]
    .rename(columns={"専用相談ダイヤル相談件数": "小計"})
    .copy()
)

data["contacts"] = {
    "__comments": "新型コロナウイルス感染症専用相談ダイヤル相談件数",
    "date": dt_update,
    "data": df_contacts.to_dict(orient="records"),
}

df_querents = (
    df_soudan.loc[:, ["日付", "保健所相談件数"]].rename(columns={"保健所相談件数": "小計"}).copy()
)

data["querents"] = {
    "__comments": "帰国者・接触者相談センター相談件数",
    "date": dt_update,
    "data": df_querents.to_dict(orient="records"),
}

# 陽性者の状況

df_yousei = pd.read_excel(
    "https://www.pref.yamanashi.jp/koucho/coronavirus/documents/yousei.xlsx"
)

df_yousei.columns = df_yousei.columns.map(lambda s: s.replace("\n", ""))
df_yousei.rename(columns={"№": "No", "居住地（生活圏）": "居住地"}, inplace=True)

# 改行除去
df_yousei["居住地"] = df_yousei["居住地"].str.replace("\n", "").str.normalize("NFKC")
df_yousei["年代"] = df_yousei["年代"].str.replace("\n", "")

# 非公表
df_yousei["年代"] = df_yousei["年代"].fillna("非公表")
df_yousei["性別"] = df_yousei["性別"].fillna("非公表")

df_yousei["症状"] = df_yousei["発症日"].where(df_yousei["発症日"].isin(["無症状", "非公表"]))
df_yousei["発症日"] = pd.to_datetime(df_yousei["発症日"], errors="coerce")

df_yousei["No"] = "県内" + df_yousei["No"].astype(str) + "例目"

df_yousei["発生判明日"] = df_yousei["公表日"].apply(
    lambda d: pd.Timestamp(d, tz="Asia/Tokyo").isoformat()
)

df_yousei["退院"] = None

df_patients = df_yousei.reindex(columns=["No", "発生判明日", "居住地", "年代", "性別", "退院"])

data["patients"] = {
    "__comments": "陽性患者の属性",
    "date": dt_update,
    "data": df_patients.to_dict(orient="records"),
}

# 陽性患者数

ser_patients_sum = df_yousei["公表日"].value_counts().sort_index()

if dt_yesterday > ser_patients_sum.index[-1]:
    ser_patients_sum[dt_yesterday] = 0

ser_patients_sum.sort_index(inplace=True)

df_patients_sum = pd.DataFrame({"小計": ser_patients_sum.asfreq("D", fill_value=0)})

df_patients_sum["日付"] = df_patients_sum.index.map(
    lambda d: pd.Timestamp(d, tz="Asia/Tokyo").isoformat()
)

data["patients_summary"] = {
    "__comments": "陽性患者数",
    "date": dt_update,
    "data": df_patients_sum.to_dict(orient="records"),
}

with open("data.json", "w", encoding="utf-8") as fw:
    json.dump(data, fw, ignore_nan=True, ensure_ascii=False, indent=4)
