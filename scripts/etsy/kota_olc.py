#!/usr/bin/env python3
"""Etsy kota olcumu (salt okuma, OAuth/token YOK): GET /openapi-ping iki kez (arada --ara sn), yanit basliklari
x-limit-per-day / x-remaining-today / x-limit-per-second / x-remaining-this-second + sunucu Date -> CSV satiri.
Iki olcum farki: ping'in kotadan dusup dusmedigi. Saatlik log gun sifirlamasi mi kayan 24 saat mi oldugunu gosterir
(00:00 UTC'de toplu sicrama = gunluk sifirlama; gun icinde, 24 saat onceki yuke karsilik gelen sicramalar = kayan pencere).
Kullanim: kota_olc.py --csv ETSY_KOTA.csv [--ara 20]
"""
import argparse
import csv
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import API, APIKeyStore  # noqa: E402

BASLIK = ["x-limit-per-day", "x-remaining-today", "x-limit-per-second", "x-remaining-this-second"]


def ping(st):
    r = requests.get(API + "/openapi-ping", headers={"x-api-key": st.api_key_header}, timeout=30)
    return r.status_code, {h: r.headers.get(h, "") for h in BASLIK}, r.headers.get("date", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True); ap.add_argument("--ara", type=int, default=20)
    a = ap.parse_args()
    st = APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""))
    s1, h1, d1 = ping(st)
    time.sleep(a.ara)
    s2, h2, d2 = ping(st)
    yeni = not Path(a.csv).exists()
    with open(a.csv, "a", newline="") as fh:
        w = csv.writer(fh)
        if yeni:
            w.writerow(["utc", "http", *BASLIK, "utc2", "remaining2", "fark"])
        try:
            fark = int(h1["x-remaining-today"]) - int(h2["x-remaining-today"])
        except ValueError:
            fark = ""
        w.writerow([d1, s1, *[h1[h] for h in BASLIK], d2, h2["x-remaining-today"], fark])
    print(f"{d1} HTTP {s1} | " + " | ".join(f"{h} {h1[h]}" for h in BASLIK)
          + f" || {a.ara}s sonra remaining {h2['x-remaining-today']} (fark {fark})", flush=True)
    return 0 if s1 == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
