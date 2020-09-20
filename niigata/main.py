# -*- coding: utf-8 -*-

import datetime
import pathlib
import re
from urllib.parse import urljoin

import jaconv
import pandas as pd
import requests
from bs4 import BeautifulSoup

JST = datetime.timezone(datetime.timedelta(hours=+9))
dt_now = datetime.datetime.now(JST)

BASE_URL = "https://www.pref.niigata.lg.jp/site/shingata-corona/index.html"

niigata_names = {
    151009: "新潟市",
    151017: "新潟市北区",
    151025: "新潟市東区",
    151033: "新潟市中央区",
    151041: "新潟市江南区",
    151050: "新潟市秋葉区",
    151068: "新潟市南区",
    151076: "新潟市西区",
    151084: "新潟市西蒲区",
    152021: "長岡市",
    152048: "三条市",
    152056: "柏崎市",
    152064: "新発田市",
    152081: "小千谷市",
    152099: "加茂市",
    152102: "十日町市",
    152111: "見附市",
    152129: "村上市",
    152137: "燕市",
    152161: "糸魚川市",
    152170: "妙高市",
    152188: "五泉市",
    152226: "上越市",
    152234: "阿賀野市",
    152242: "佐渡市",
    152251: "魚沼市",
    152269: "南魚沼市",
    152277: "胎内市",
    153079: "聖籠町",
    153427: "弥彦村",
    153613: "田上町",
    153851: "阿賀町",
    154059: "出雲崎町",
    154610: "湯沢町",
    154822: "津南町",
    155047: "刈羽村",
    155811: "関川村",
    155861: "粟島浦村",
}

niigata_codes = {v: k for k, v in niigata_names.items()}


def niigata_get_code(s):
    return niigata_codes.get(s.strip(), 0)


def str2date(s):

    n = re.findall("[0-9]{1,2}", s)

    y = dt_now.year

    if len(n) == 2:
        m, d = map(int, n)
        return pd.Timestamp(y, m, d)

    else:
        return pd.NaT


def df_update(df1, df2):

    df = df1.reindex(df1.index.union(df2.index))
    df.update(df2)

    return df


def fetch_yousei(url):

    df = pd.read_html(url, index_col=0)[0].T
    df.rename(
        index={"入院中 (予定含む)": "hospitalization", "退院": "discharge"},
        columns={"累計": "count"},
        inplace=True,
    )

    df1 = df.loc[["hospitalization", "discharge"], "count"].copy()
    df1.index.name = "type"

    p_hospitalization_csv = pathlib.Path("dist", "csv", "hospitalization.csv")
    p_hospitalization_csv.parent.mkdir(parents=True, exist_ok=True)

    df1.to_csv(p_hospitalization_csv, encoding="utf_8_sig")


def fetch_excel(url, text):

    r = requests.get(url)
    r.raise_for_status()

    soup = BeautifulSoup(r.content, "html.parser")

    tag = soup.find("a", text=re.compile(f"^{text}"), href=re.compile("xls[mx]?$"))

    if tag:
        link = urljoin(url, tag.get("href"))
        p = fetch_file(link, r"dist/excel")

        return p
    else:
        raise FileNotFoundError("Excelファイルが見つかりません")


def fetch_file(url, dir="."):

    r = requests.get(url)
    r.raise_for_status()

    p = pathlib.Path(dir, pathlib.PurePath(url).name)
    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open(mode="wb") as fw:
        fw.write(r.content)
    return p


def fetch_kanja(url):

    df = pd.read_html(url, na_values=["-", "－", "―"])[0]

    df.rename(
        columns={"患者 No. ※報道発表資料へリンク": "No", "患者 No. ※報道発表資料へリンク.1": "報道発表資料"},
        inplace=True,
    )

    df.dropna(thresh=4, inplace=True)

    df["備考"] = df["備考"].fillna("").astype(str)

    df["年代"] = df["年代"].fillna("").astype(str)
    df["年代"] = df["年代"].mask(df["年代"].str.startswith("10歳未満"), "10歳未満")

    df["判明日"] = df["判明日"].apply(
        lambda s: jaconv.z2h(s, kana=False, digit=True, ascii=True).replace(" ", "")
    )
    df["判明日"] = df["判明日"].apply(str2date)

    df["居住地"] = df["居住地"].apply(
        lambda s: jaconv.z2h(s, kana=False, digit=True, ascii=True).replace(" ", "")
    )
    df["居住地"] = df["居住地"].apply(lambda s: s.rstrip(")").split("(")[-1])

    df = df.sort_values("No").reset_index(drop=True)

    df.to_csv("kanja.tsv", sep="\t")

    df1 = df.copy()

    df1.rename(
        columns={
            "判明日": "公表_年月日",
            "居住地": "患者_居住地",
            "年代": "患者_年代",
            "性別": "患者_性別",
            "職業": "患者_職業",
        },
        inplace=True,
    )

    df1["都道府県名"] = "新潟県"
    df1["市区町村名"] = df1["患者_居住地"]
    df1["全国地方公共団体コード"] = df1["市区町村名"].apply(niigata_get_code)

    df2 = df1.reindex(
        columns=[
            "No",
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
        ]
    )
    
    df2.set_index("No", inplace=True)

    p_patients_csv = pathlib.Path("dist", "csv", "150002_niigata_covid19_patients.csv")
    p_patients_csv.parent.mkdir(parents=True, exist_ok=True)

    df2.to_csv(p_patients_csv, encoding="utf_8_sig")


def fetch_soudan(url):

    p_soudan = fetch_excel(url, "センター相談件数")

    df = pd.read_excel(p_soudan, skiprows=3, skipfooter=4)

    df.set_axis(["年", "受付_年月日", "曜日", "相談件数", "紹介人数", "備考"], axis=1, inplace=True)

    flg_is_serial = df["受付_年月日"].astype("str").str.isdigit()

    fromSerial = pd.to_datetime(
        df.loc[flg_is_serial, "受付_年月日"].astype(float),
        unit="D",
        origin=pd.Timestamp("1899/12/30"),
    )

    fromString = df.loc[~flg_is_serial, "受付_年月日"]

    df["受付_年月日"] = pd.concat([fromString, fromSerial])

    df1 = df.loc[flg_is_serial].copy()
    df1.drop(["年", "曜日"], axis=1, inplace=True)
    df1.reset_index(drop=True, inplace=True)

    df1.to_csv("soudan.tsv", sep="\t")

    df2 = df1.copy()

    df2["全国地方公共団体コード"] = 150002
    df2["都道府県名"] = "新潟県"
    df2["市区町村名"] = ""
    df2["備考"] = ""

    df3 = df2.reindex(
        columns=["受付_年月日", "全国地方公共団体コード", "都道府県名", "市区町村名", "相談件数", "備考",]
    )

    df3.set_index("受付_年月日", inplace=True)

    df_temp = pd.read_csv(
        "https://raw.githubusercontent.com/CodeForNiigata/covid19-data-niigata/master/dist/csv/150002_niigata_covid19_test_count.csv",
        index_col=0,
        parse_dates=True,
        dtype={"全国地方公共団体コード": "Int64", "相談件数": "Int64"},
    )

    df4 = df_update(df_temp, df3)
    df4.index = df4.index.strftime("%Y-%m-%d")

    p_callcenter_csv = pathlib.Path(
        "dist", "csv", "150002_niigata_covid19_call_center.csv"
    )
    p_callcenter_csv.parent.mkdir(parents=True, exist_ok=True)

    df4.to_csv(p_callcenter_csv, encoding="utf_8_sig")


def fetch_kensa(url):

    p_kensa = fetch_excel(url, "検査件数一覧表")

    df = pd.read_excel(p_kensa, skiprows=2, skipfooter=2)

    df.set_axis(
        ["年", "実施_年月日", "曜日", "検査実施_件数", "PCRセンター実施件数", "陽性件数"], axis=1, inplace=True
    )

    flg_is_serial = df["実施_年月日"].astype("str").str.isdigit()

    fromSerial = pd.to_datetime(
        df.loc[flg_is_serial, "実施_年月日"].astype(float),
        unit="D",
        origin=pd.Timestamp("1899/12/30"),
    )

    fromString = df.loc[~flg_is_serial, "実施_年月日"]

    df["実施_年月日"] = pd.concat([fromString, fromSerial])

    df1 = df.loc[flg_is_serial].copy()
    df1.drop(["年", "曜日"], axis=1, inplace=True)

    df1["検査実施_件数"] = df1["検査実施_件数"].fillna(0).astype("Int64")
    df1["PCRセンター実施件数"] = df1["PCRセンター実施件数"].fillna(0).astype("Int64")
    df1["陽性件数"] = df1["陽性件数"].fillna(0).astype("Int64")

    df1.reset_index(drop=True, inplace=True)

    df1.to_csv("kensa.tsv", sep="\t")

    df2 = df1.copy()

    df2["全国地方公共団体コード"] = 150002
    df2["都道府県名"] = "新潟県"
    df2["市区町村名"] = ""
    df2["備考"] = ""

    df3 = df2.reindex(
        columns=["実施_年月日", "全国地方公共団体コード", "都道府県名", "市区町村名", "検査実施_件数", "備考",]
    )

    df3.set_index("実施_年月日", inplace=True)

    df_temp = pd.read_csv(
        "https://raw.githubusercontent.com/CodeForNiigata/covid19-data-niigata/master/dist/csv/150002_niigata_covid19_test_count.csv",
        index_col=0,
        parse_dates=True,
        dtype={"全国地方公共団体コード": "Int64", "検査実施_件数": "Int64"},
    )

    df4 = df_update(df_temp, df3)
    df4.index = df4.index.strftime("%Y-%m-%d")

    p_testcount_csv = pathlib.Path(
        "dist", "csv", "150002_niigata_covid19_test_count.csv",
    )

    p_testcount_csv.parent.mkdir(parents=True, exist_ok=True)

    df4.to_csv(p_testcount_csv, encoding="utf_8_sig")


if __name__ == "__main__":

    r = requests.get(BASE_URL)
    r.raise_for_status()

    soup = BeautifulSoup(r.content, "html.parser")

    tag = soup.find("a", text="県内における発生状況の詳細はこちら")

    if tag:
        link = urljoin(BASE_URL, tag.get("href"))

        fetch_yousei(BASE_URL)
        fetch_kanja(link)
        fetch_soudan(link)
        fetch_kensa(link)
