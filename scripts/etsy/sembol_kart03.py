#!/usr/bin/env python3
"""GOREV 0028 - kart 03 (ortak sembol) butunluk kapisi. SALT OKUMA: Etsy'ye yazma yok.

canli <METIN_78.csv> <cikti>            : 78 ilanin canli rank 3 gorseli (1 batch cagrisi, API anahtari; indirme CDN)
kapi  <METIN_78.csv> <canli> <a77> <out>: kapi -> out/SEMBOL_KART03.csv
"""
import csv
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import APIKeyStore, Etsy  # noqa: E402
from pod_galeri_tamset import cift_anahtar  # noqa: E402


def ilanlar(metin):
    L = {}
    for r in csv.DictReader(open(metin, encoding="utf-8")):
        c = cift_anahtar(r.get("cift"))
        if c and r.get("ilan_id"):
            L[str(r["ilan_id"]).strip()] = c
    return L


def canli(metin, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    api = Etsy(APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")))
    L = ilanlar(metin); ids = list(L); ozet = {}
    for i in range(0, len(ids), 100):
        d = api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100]), "includes": "images"}) or {}
        for x in d.get("results") or []:
            lid = str(x["listing_id"]); im = sorted(x.get("images") or [], key=lambda y: y.get("rank") or 0)
            ozet[lid] = {"cift": L[lid], "state": x.get("state"), "foto": len(im),
                         "ranklar": [[y.get("rank"), y.get("listing_image_id")] for y in im]}
            r3 = next((y for y in im if y.get("rank") == 3), None)
            if r3:
                b = requests.get(r3["url_fullxfull"], timeout=60).content
                (out / f"{lid}_{L[lid]}_03_{r3['listing_image_id']}.jpg").write_bytes(b)
                ozet[lid]["r3"] = r3["listing_image_id"]
    (out / "_canli.json").write_text(json.dumps(ozet, indent=1))
    print(f"ilan {len(L)} okunan {len(ozet)} rank3 {sum('r3' in v for v in ozet.values())} kota {api.remaining}")


if __name__ == "__main__":
    m = sys.argv[1]
    if m == "canli":
        canli(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(f"bilinmeyen mod {m}")
