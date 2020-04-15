import datetime
import json
import re
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

import camelot


url = "https://www.pref.aichi.jp/site/covid19-aichi/kansensya-kensa.html"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
}

JST = datetime.timezone(datetime.timedelta(hours=+9), "JST")


class CovidDataManager:
    def __init__(self):

        dt_now = datetime.datetime.now(JST)

        self.data = {"lastUpdate": dt_now.strftime("%Y/%m/%d %H:%M")}
        self.dt_now = dt_now

        r = requests.get(url, headers=headers)

        r.raise_for_status()

        self.soup = BeautifulSoup(r.content, "html.parser")

    def main_summary(self):

        df_main = pd.read_csv(
            "https://docs.google.com/spreadsheets/d/1DdluQBSQSiACG1CaIg4K3K-HVeGGThyecRHSA84lL6I/export?format=csv&gid=0",
            index_col=0,
            header=None,
        )

        main_sum = df_main.T.to_dict(orient="recodes")[0]

        self.data["main_summary"] = {
            "attr": "検査実施人数",
            "value": main_sum["検査実施人数"],
            "children": [
                {
                    "attr": "陽性患者数",
                    "value": main_sum["陽性患者数"],
                    "children": [
                        {
                            "attr": "入院中",
                            "value": main_sum["入院中"],
                            "children": [
                                {"attr": "軽症・中等症", "value": main_sum["軽症・中等症"]},
                                {"attr": "重症", "value": main_sum["重症"]},
                            ],
                        },
                        {"attr": "退院", "value": main_sum["退院"]},
                        {"attr": "転院", "value": main_sum["転院"]},
                        {"attr": "死亡", "value": main_sum["死亡"]},
                    ],
                }
            ],
        }

    # 新型コロナウイルス遺伝子検査件数
    def inspections_summary(self):

        table = self.soup.find(
            "table", summary="愛知県衛生研究所及び名古屋市衛生研究所における新型コロナウイルス遺伝子検査件数"
        )

        caption = table.find("caption").get_text(strip=True)

        # 公表日をdatetimeに変換
        y = self.dt_now.year
        m, d = map(int, re.findall("[0-9]{1,2}", caption))

        # ※時間は変更してください
        last_update = datetime.datetime(y, m, d, 23, 59)

        df_tmp = pd.read_html(table.prettify())[0]

        df = df_tmp[df_tmp["検査日"] != "計"].copy()

        df["備考"] = df["検査日"].where(df["検査日"].str.contains("～"))

        df_date = df["検査日"].str.extract(
            "([0-9]{1,2})月([0-9]{1,2})日（(.)曜日）$", expand=True
        )

        df_date.rename(columns={0: "月", 1: "日", 2: "曜日"}, inplace=True)

        df_date["月"] = df_date["月"].astype(int)
        df_date["日"] = df_date["日"].astype(int)

        df_date["date"] = df_date.apply(
            lambda x: pd.Timestamp(
                year=datetime.datetime.now().year, month=x["月"], day=x["日"]
            ),
            axis=1,
        )

        df["検査日"] = df_date["date"].dt.strftime("%Y-%m-%d")

        df_insp = df.loc[:, ("検査日", "検査件数（件）")].copy()

        df_insp.rename(columns={"検査日": "日付", "検査件数（件）": "小計"}, inplace=True)

        self.data["inspections_summary"] = {
            "data": df_insp.to_dict(orient="recodes"),
            "date": last_update.strftime("%Y/%m/%d %H:%M"),
        }

    # 県内発生事例一覧
    def patients(self):

        tag = self.soup.find("a", text=re.compile("^県内発生事例一覧"))

        y = self.dt_now.year
        m, d, _ = map(int, re.findall("[0-9]+", tag.get_text(strip=True)))

        last_update = datetime.datetime(y, m, d, 23, 59)

        link = urljoin(url, tag.get("href"))

        tables = camelot.read_pdf(
            link, pages="all", split_text=True, strip_text="\n", line_scale=40
        )

        df_csv = pd.concat([table.df for table in tables])

        df_csv.to_csv("data.csv", index=None, header=None)

        def my_parser(s):

            y = self.dt_now.year
            m, d = map(int, re.findall("[0-9]{1,2}", s))

            return pd.Timestamp(year=y, month=m, day=d)

        df_patient = pd.read_csv("data.csv", parse_dates=["発表日"], date_parser=my_parser)

        # patients_summary

        df_pts = (
            df_patient["発表日"]
            .value_counts()
            .sort_index()
            .asfreq("D", fill_value=0)
            .reset_index()
        )

        df_pts["日付"] = df_pts["index"].dt.strftime("%Y-%m-%d")

        df_pts.rename(columns={"発表日": "小計"}, inplace=True)

        df_pts.drop("index", axis=1, inplace=True)

        self.data["patients_summary"] = {
            "data": df_pts.to_dict(orient="records"),
            "last_update": last_update.strftime("%Y-%m-%d %H:%M"),
        }

        # patients

        df_patient.set_index("発表日", inplace=True)

        df_patient["date"] = df_patient.index.strftime("%Y-%m-%d")

        df_patient["short_date"] = df_patient.index.strftime("%m\/%d")

        df_patient["w"] = (df_patient.index.dayofweek + 1) % 7

        df_patient["発表日"] = df_patient.index.strftime("%Y/%m/%d %H:%M")

        df_patient.fillna("", inplace=True)

        self.data["patients"] = {
            "data": df_patient.to_dict(orient="recodes"),
            "date": last_update.strftime("%Y/%m/%d %H:%M"),
        }

    def export_jsons(self):

        with open("data.json", "w") as fw:
            json.dump(self.data, fw, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    dm = CovidDataManager()

    print("---main_summary---")
    dm.main_summary()

    print("---inspections_summary---")
    dm.inspections_summary()

    print("---patients---")
    dm.patients()

    print("---export jsons---")
    dm.export_jsons()

    print("---done---")
