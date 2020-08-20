import datetime
import pathlib
import re
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

import camelot


def fetch_pdf(soup, text):

    tag = soup.find("a", text=re.compile(f"^{text}"), href=re.compile(".pdf$"))

    if tag:

        link = urljoin(BASE_URL, tag.get("href"))

        p = fetch_file(link, "data")

        tables = camelot.read_pdf(
            str(p), pages="all", split_text=True, strip_text="\n", line_scale=40
        )

        df = pd.concat([table.df for table in tables])

        df.columns = df.iloc[0]

        return df.iloc[1:].set_index("No")

    else:

        raise FileNotFoundError("PDFファイルが見つかりません")


def fetch_file(url, dir="."):

    r = requests.get(url)
    r.raise_for_status()

    p = pathlib.Path(dir, pathlib.PurePath(url).name)
    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open(mode="wb") as fw:
        fw.write(r.content)

    return p


def my_parser(s):

    y = dt_now.year
    m, d = map(int, re.findall("[0-9]{1,2}", s))

    return pd.Timestamp(year=y, month=m, day=d)


BASE_URL = "https://www.pref.aichi.jp/site/covid19-aichi/kansensya-kensa.html"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
}

JST = datetime.timezone(datetime.timedelta(hours=+9), "JST")
dt_now = datetime.datetime.now(JST)


if __name__ == "__main__":

    r = requests.get(BASE_URL)
    r.raise_for_status()

    soup = BeautifulSoup(r.content, "html.parser")

    df1 = fetch_pdf(soup, "7月まで")
    df2 = fetch_pdf(soup, "8月以降")

    df1.to_csv("./data/source1.csv")
    df2.to_csv("./data/source2.csv")

    df = pd.concat([df1, df2])

    df["発表日"] = df["発表日"].apply(my_parser)
    df["date"] = df["発表日"].dt.date
    df["w"] = (df["発表日"].dt.dayofweek + 1) % 7
    df["short_date"] = df["発表日"].dt.strftime("%m\\/%d")
    df["発表日"] = df["発表日"].dt.strftime("%Y/%m/%d %H:%M")

    df.to_csv("./data/patients.csv")
    df
