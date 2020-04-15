import datetime
import pandas as pd
import json

COUNTS_FILE = "toyama_counts.csv"
PATIENTS_FILE = "toyama_patients.csv"

JST = datetime.timezone(datetime.timedelta(hours=+9), "JST")

# 現在の時刻
dt_now = datetime.datetime.now(JST).strftime("%Y/%m/%d %H:%M")

data = {"lastUpdate": dt_now}

# データ読み込み
df = pd.read_csv(COUNTS_FILE, index_col="年月日", parse_dates=True)

df["日付"] = df.index.strftime("%Y-%m-%d")

# 検査実施人数
df_insp = df.loc[:, ("日付", "検査実施人数")].copy()
df_insp.rename(columns={"検査実施人数": "小計"}, inplace=True)

data["inspection_persons"] = {"date": dt_now, "data": df_insp.to_dict(orient="recodes")}

# 陽性患者数
df_pats = df.loc[:, ("日付", "陽性人数")].copy()
df_pats.rename(columns={"陽性人数": "小計"}, inplace=True)

data["patients_summary"] = {"date": dt_now, "data": df_pats.to_dict(orient="recodes")}

# 一般相談件数
df_contacts = df.loc[:, ("日付", "一般相談件数")].copy()
df_contacts.rename(columns={"一般相談件数": "小計"}, inplace=True)

data["contacts"] = {"date": dt_now, "data": df_contacts.to_dict(orient="recodes")}

# 帰国者・接触者相談件数
df_querents = df.loc[:, ("日付", "帰国者相談件数")].copy()
df_querents.rename(columns={"帰国者相談件数": "小計"}, inplace=True)

data["querents"] = {"date": dt_now, "data": df_querents.to_dict(orient="recodes")}

# 陽性患者の属性
df_kanja = pd.read_csv(PATIENTS_FILE, index_col="No", dtype={"年代": "object"})

df_kanja.rename(columns={"公表年月日": "date"}, inplace=True)
df_patients = df_kanja.loc[:, ("date", "居住地", "年代", "性別")].copy()

data["patients"] = {"date": dt_now, "data": df_patients.to_dict(orient="recodes")}

with open("data.json", "w", encoding="utf-8") as fw:
    json.dump(data, fw, ensure_ascii=False, indent=4)
