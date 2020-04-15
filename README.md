# What is this

富山県の新型コロナウイルス情報を集め、jsonやcsvとして出力するPythonスクリプトです

# Specification

## main.py
+ main.pyを実行するとオープンデータからデータを取得しdata.jsonを出力します

## toyama_covid19.ipynb
+ toyama_covid19.ipynbはGoogle Colaboratoryで手動で実行し、オープンデータからデータを取得しdata.jsonを出力します

# オープンデータ

## コロナウィルス関連データ（陽性患者属性以外）(CSV)
+ http://opendata.pref.toyama.jp/files/covid19/20200403/toyama_counts.csv

## コロナウィルス関連データ（陽性患者属性のみ）(CSV)
+ http://opendata.pref.toyama.jp/files/covid19/20200403/toyama_patients.csv

# 出力されるデータ
+ toyama_counts.csv
    + inspection_persons（日別検査実施人数）
    + patients_summary（日別陽性患者数）
    + contacts（日別一般相談件数）
    + querents（日別帰国者・接触者相談件数）
+ toyama_patients.csv
    + patients（陽性患者一覧）
