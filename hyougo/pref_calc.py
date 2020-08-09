# -*- coding: utf-8 -*-

import pathlib
import re
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


def fetch_excel(url):

    r = requests.get(url)
    r.raise_for_status()

    soup = BeautifulSoup(r.content, "html.parser")
    tag = soup.find("a", href=re.compile("xls[mx]?$"))

    if tag:
        link = urljoin(url, tag.get("href"))
        p = fetch_file(link, "data")

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


if __name__ == "__main__":

    # スクレイピング

    p = fetch_excel("https://web.pref.hyogo.lg.jp/kk03/corona_kanjyajyokyo.html")

    df_kanja = pd.read_excel(
        p,
        skiprows=3,
        skipfooter=2,
        usecols=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        dtype={"番号": "Int64"},
    )

    # 前処理

    # 全列欠損を削除
    df_kanja.dropna(how="all", inplace=True)

    # 発表日
    flg_is_serial = df_kanja["発表日"].astype("str").str.isdigit()

    fromSerial = pd.to_datetime(
        df_kanja.loc[flg_is_serial, "発表日"].astype(float),
        unit="D",
        origin=pd.Timestamp("1899/12/30"),
    )
    fromString = pd.to_datetime(df_kanja.loc[~flg_is_serial, "発表日"])

    df_kanja["発表日"] = pd.concat([fromString, fromSerial])

    df_kanja.set_index("番号", inplace=True)

    # 除外
    df_kanja.drop(738, inplace=True)

    # 年代
    df_kanja["年代"] = df_kanja["年代"].astype(str)
    df_kanja["年代"] = df_kanja["年代"].replace({"10?[歳代]未満": "10歳未満"}, regex=True)

    # 備考欄
    df_kanja["備考欄"] = df_kanja["備考欄"].str.replace("\n", "")
    df_kanja["備考欄"] = df_kanja["備考欄"].str.replace("NO.|N0.|NO,|N0,|No,", "No.")
    df_kanja["備考欄"] = df_kanja["備考欄"].str.replace("・", "、")
    df_kanja["備考欄"] = df_kanja["備考欄"].fillna("")

    # ステータス
    df_kanja["ステータス"] = df_kanja["発症日"].mask(
        df_kanja["発症日"].astype("str").str.isdigit(), "症状あり"
    )

    # 発症日

    df_kanja["発症日"] = df_kanja["発症日"].where(df_kanja["発症日"].astype("str").str.isdigit())
    df_kanja["発症日"] = pd.to_datetime(
        df_kanja["発症日"].astype(float), unit="D", origin=pd.Timestamp("1899/12/30")
    )

    # ファイル保存
    df_kanja.to_csv(pathlib.Path("data", "kanja.csv"), encoding="utf_8_sig")

    # 年代集計

    ages = ("非公表", "10歳未満", "10", "20", "30", "40", "50", "60", "70", "80", "90")

    cr_ages = (
        pd.crosstab(
            df_kanja["発表日"], df_kanja["年代"], values=df_kanja["年代"], aggfunc="count"
        )
        .reindex(columns=ages)
        .asfreq("D", fill_value=0)
        .fillna(0)
        .astype(int)
    )

    # 計追加
    cr_ages["計"] = cr_ages.sum(axis=1)

    # 最終行を表示
    cr_ages.tail(1)

    # ファイル保存
    cr_ages.to_csv(pathlib.Path("data", "ages.csv"), encoding="utf_8_sig")

    # 管轄集計

    area = (
        "芦屋",
        "宝塚",
        "伊丹",
        "加古川",
        "加東",
        "中播磨",
        "龍野",
        "赤穂",
        "豊岡",
        "朝来",
        "丹波",
        "洲本",
        "神戸",
        "姫路",
        "尼崎",
        "西宮",
        "明石",
    )

    cr_area = (
        pd.crosstab(
            df_kanja["発表日"], df_kanja["管轄"], values=df_kanja["管轄"], aggfunc="count"
        )
        .reindex(columns=area)
        .asfreq("D", fill_value=0)
        .fillna(0)
        .astype(int)
    )

    # 計追加
    cr_area["計"] = cr_area.sum(axis=1)

    # 最終行を表示
    cr_area.tail(1)

    # ファイル保存
    cr_area.to_csv(pathlib.Path("data", "area.csv"), encoding="utf_8_sig")

    # 発表日別陽性者一覧

    df_kanja["発表日"] = df_kanja["発表日"].dt.strftime("%Y-%m-%d")
    df_kanja["発症日"] = df_kanja["発症日"].dt.strftime("%Y-%m-%d")

    grouped_df = df_kanja.groupby("発表日")

    with pd.ExcelWriter(
        pathlib.Path("data", "daily_kanja.xlsx"), engine="openpyxl"
    ) as writer:

        for id in grouped_df.groups:

            d = grouped_df.get_group(id)

            # ExcelWriterを用いて新規シートにDataFrameを保存
            d.to_excel(writer, sheet_name=str(id), index=False)
