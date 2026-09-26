#!/usr/bin/env python3
"""GOREV 0023 - 78 canli POD ilaninin metin taramasi (SALT OKUMA, Etsy'ye yazma YOK).
1 Etsy okuma cagrisi (getListingsByListingIds, includes=images,personalization) YALNIZ API anahtariyla (OAuth yok).
Alanlar: baslik, aciklama, kisisellestirme talimati, foto alt metinleri. Kural (CLAUDE.md "Urun metni", 25 Eyl):
 TIRE      : uzun (U+2014) / orta (U+2013) tire
 HAHNEMUHLE: "Hahnemuhle"/"Hahnemuehle"/"Hahnemühle" disi yazim (dogru: Hahnemühle)
 YASAK     : OBA-free, bright white, omur yili (orn. 100-200 years), 12-colour/12-color
 KARISIK   : ayni ilanda hem colour hem color / hem fulfilment hem fulfillment
Cikti: out/CANLI_METIN_TARAMA.csv (ilan, cift, alan, ihlal, metin_parcasi), out/CANLI_METIN_TARAMA_OZET.json
Kullanim: canli_metin_tarama.py <metin78_csv> | --yerel <listings_json> (test)"""
import csv
import json
import os
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
REF_ID = "4570143815"
OUT = Path("out")
KURAL = [
    ("TIRE", re.compile("[—–]")),
    ("HAHNEMUHLE", re.compile(r"hahnem(?!ühle)\w*", re.I)),
    ("YASAK_OBA", re.compile(r"\bOBA[\s-]*free\b", re.I)),
    ("YASAK_BRIGHT_WHITE", re.compile(r"\bbright\s+white\b", re.I)),
    ("YASAK_OMUR", re.compile(r"\b\d{2,3}\s*(?:-|–|—|to)\s*\d{2,3}\+?\s*years?\b|\b\d{3}\+?\s*years?\b", re.I)),
    ("YASAK_12_RENK", re.compile(r"\b12[\s-]*colou?rs?\b", re.I)),
]
KARISIK = [("colour", re.compile(r"\bcolou?rs?\b", re.I), "colour"), ("fulfil", re.compile(r"\bfulfill?ment\b", re.I), "fulfilment")]


def parca(metin, m, pay=30):
    a, b = max(0, m.start() - pay), min(len(metin), m.end() + pay)
    return " ".join(metin[a:b].split())


def oku(metin78):
    from etsy_common import API, mask
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    cift = {r["ilan_id"]: r.get("cift", "") for r in csv.DictReader(open(metin78, encoding="utf-8")) if r.get("ilan_id")}
    cift.setdefault(REF_ID, "Cancer + Libra")
    ids, sonuc, cagri = list(cift), [], 0
    for i in range(0, len(ids), 100):
        r = requests.get(API + "/listings/batch", headers={"x-api-key": f"{k_}:{s_}"}, timeout=60,
                         params={"listing_ids": ",".join(ids[i:i + 100]), "includes": "images,personalization"})
        cagri += 1
        r.raise_for_status()
        sonuc += r.json().get("results") or []
    print(f"etsy: {len(sonuc)} ilan, cagri {cagri}, kota {r.headers.get('x-remaining-today')}", flush=True)
    return sonuc, cift


def alanlar(x):
    yield "baslik", x.get("title") or ""
    yield "aciklama", x.get("description") or ""
    t = x.get("personalization_instructions") or ""
    for q in x.get("personalization_questions") or x.get("personalization") or []:
        if isinstance(q, dict):
            t += " " + " ".join(str(q.get(k) or "") for k in ("question_text", "instructions"))
    yield "kisisellestirme", t.strip()
    for im in x.get("images") or []:
        yield f"alt_metin#{im.get('rank')}", im.get("alt_text") or ""


def tara(ilanlar, cift):
    satir = []
    for x in ilanlar:
        lid = str(x.get("listing_id"))
        tum = {}
        for alan, metin in alanlar(x):
            for ad, rx in KURAL:
                for m in rx.finditer(metin):
                    satir.append({"ilan": lid, "cift": cift.get(lid, ""), "alan": alan, "ihlal": ad, "metin_parcasi": parca(metin, m)})
            tum[alan] = metin
        hepsi = " ".join(tum.values())
        for ad, rx, uk in KARISIK:
            bul = {m.group(0).lower() for m in rx.finditer(hepsi)}
            uk_var = any(uk in b for b in bul)
            us_var = any(uk not in b for b in bul)
            if uk_var and us_var:
                satir.append({"ilan": lid, "cift": cift.get(lid, ""), "alan": "tum", "ihlal": f"KARISIK_{ad.upper()}",
                              "metin_parcasi": ", ".join(sorted(bul))})
    return satir


def main():
    OUT.mkdir(exist_ok=True)
    if sys.argv[1] == "--yerel":
        ilanlar, cift = json.loads(Path(sys.argv[2]).read_text()), {}
    else:
        ilanlar, cift = oku(sys.argv[1])
    satir = tara(ilanlar, cift)
    with open(OUT / "CANLI_METIN_TARAMA.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ilan", "cift", "alan", "ihlal", "metin_parcasi"])
        w.writeheader(); w.writerows(satir)
    ozet = {"ilan": len(ilanlar), "ihlalli_ilan": len({s["ilan"] for s in satir}),
            "ihlal": {k: {"satir": sum(1 for s in satir if s["ihlal"] == k), "ilan": len({s["ilan"] for s in satir if s["ihlal"] == k})}
                      for k in sorted({s["ihlal"] for s in satir})},
            "alan": {k: sum(1 for s in satir if s["alan"].split("#")[0] == k) for k in sorted({s["alan"].split("#")[0] for s in satir})}}
    (OUT / "CANLI_METIN_TARAMA_OZET.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1))
    print("OZET " + json.dumps(ozet, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
