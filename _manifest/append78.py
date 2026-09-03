#!/usr/bin/env python3
"""78 basligi (titles78.txt) + stdin'den 78 URL -> manifest satiri ekler."""
import sys, pathlib

device, edition = sys.argv[1], sys.argv[2]
titles = pathlib.Path("_manifest/titles78.txt").read_text().splitlines()
urls = [l.strip() for l in sys.stdin if l.strip()]
if len(titles) != 78 or len(urls) != 78:
    sys.exit(f"HATA: basliklar={len(titles)} url={len(urls)} (78 bekleniyor)")
with open("_manifest/canva_bulk.tsv", "a") as f:
    for t, u in zip(titles, urls):
        f.write(f"{t}\t{device}\t{edition}\t{u}\n")
print(f"eklendi: {device} {edition} 78 satir")
