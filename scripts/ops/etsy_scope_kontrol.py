#!/usr/bin/env python3
"""Etsy token kapsami (salt okuma, Etsy'ye cagri YOK): Drive TEMP/ETSY_TOKEN.json icindeki 'scope' alanindan
istenen kapsamlarin VAR/YOK durumu. Token degerleri okunur ama HICBIR YERE yazilmaz; cikti yalniz kapsam adlari.
Kullanim: etsy_scope_kontrol.py [--dosya yerel.json] [billing_r transactions_r ...]"""
import json
import subprocess
import sys

REMOTE = "gdrive:ASTROLOVE/TEMP/ETSY_TOKEN.json"


def main(argv):
    dosya = None
    if argv[:1] == ["--dosya"]:
        dosya, argv = argv[1], argv[2:]
    istenen = argv or ["billing_r", "transactions_r", "transactions_w", "listings_r", "listings_w", "shops_r"]
    if dosya:
        metin = open(dosya, encoding="utf-8").read()
    else:
        r = subprocess.run(["rclone", "cat", REMOTE], capture_output=True, text=True)
        if r.returncode:
            print("TOKEN OKUNAMADI (rclone)"); return 1
        metin = r.stdout
    try:
        scope = str(json.loads(metin).get("scope") or "")
    except ValueError:
        print("TOKEN JSON DEGIL"); return 1
    if not scope:
        print("scope alani YOK (token dosyasinda kapsam bilgisi tutulmuyor)"); return 1
    var = set(scope.replace(",", " ").split())
    for s in istenen:
        print(f"{s}: {'VAR' if s in var else 'YOK'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
