#!/usr/bin/env python3
"""POD SEO v3 degisiklik dosyasi (Serdar onayi 27 Eyl 2026). Etsy cagrisi YOK.

Girdi (repo):
  data/pod/pod78_ids.csv          listing_id, cift, a, b  (a/b = canli basliktaki sira)
  data/pod/aciklama_v3_sablon.txt {A} {B} {A_TARIH} {B_TARIH}
  data/pod/burc_tarih.csv         burc, tarih
  data/pod/etiket_v3.txt          {CIFT} + 12 ortak etiket (# satirlari yorum)
Kurallar:
  Baslik  : "{A} and {B} Personalized Zodiac Couple Wall Art" (<= 140)
  Etiket 1: "{a} and {b}" <= 20 ise; degilse "{a} {b}" <= 20 ise; degilse "astrology lover gift"
  Mevsim  : 1 Oca - 14 Sub arasi "newlywed gift" -> "valentines day gift" (--tarih ile)
Denetim (hepsi DUR): 78 kayit, benzersiz id, 13 benzersiz etiket <= 20, baslik <= 140,
  uzun/orta tire yok, yasak ifade yok (metin_kurali ile ayni liste + instant download),
  cerceveli bolumde Hahnemuhle/cotton yok, sablon yer tutucusu kalmadi.
Cikti: pod_changes_v3.json [{id, pair, title, description, tags}] + ozet satiri.
Kullanim: pod_seo_v3_build.py --out OUT.json [--tarih 2026-09-27]
"""
import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
VERI = KOK / "data/pod"
YASAK = {
    "OBA-free": r"\bOBA[\s-]*free\b", "bright white": r"\bbright[\s-]+white\b",
    "omur yili": r"\b\d{2,4}\s*(?:[-–—]|to)?\s*(?:\d{2,4}\s*)?\+?\s*years?\b",
    "12-colour": r"\b12[\s-]*colou?rs?\b", "uzun/orta tire": r"[—–‒―−]",
    "instant download": r"\binstant\s+download", "prodigi": r"\bprodigi\b",
}
YEDEK_CIFT = "astrology lover gift"


def cift_etiketi(a, b):
    for t in (f"{a} and {b}".lower(), f"{a} {b}".lower()):
        if len(t) <= 20:
            return t
    return YEDEK_CIFT


def ortak_etiketler(tarih):
    satir = [s.strip() for s in (VERI / "etiket_v3.txt").read_text(encoding="utf-8").splitlines()
             if s.strip() and not s.startswith("#")]
    if satir[0] != "{CIFT}" or len(satir) != 13:
        raise SystemExit("HATA: etiket_v3.txt ilk satir {CIFT} ve toplam 13 satir olmali. DUR.")
    ortak = satir[1:]
    sevgililer = (tarih.month == 1) or (tarih.month == 2 and tarih.day <= 14)
    if sevgililer:
        ortak = ["valentines day gift" if t == "newlywed gift" else t for t in ortak]
    return ortak


def denetle(r):
    t = r["tags"]
    if len(t) != 13 or len(set(t)) != 13 or any(len(x) > 20 for x in t):
        raise SystemExit(f"HATA: {r['id']} etiket kurali: {t}. DUR.")
    if len(r["title"]) > 140:
        raise SystemExit(f"HATA: {r['id']} baslik {len(r['title'])} karakter. DUR.")
    metin = r["title"] + "\n" + r["description"] + "\n" + " ".join(t)
    for ad, rx in YASAK.items():
        if re.search(rx, metin, re.I):
            raise SystemExit(f"HATA: {r['id']} yasak ifade ({ad}). DUR.")
    if re.search(r"\{[A-Z_]+\}", metin):
        raise SystemExit(f"HATA: {r['id']} sablon yer tutucusu kaldi. DUR.")
    m = re.search(r"^FRAMED\n(.*?)(?:\n\n|\Z)", r["description"], re.M | re.S)
    if not m or re.search(r"hahnem|cotton|photo rag", m.group(1), re.I):
        raise SystemExit(f"HATA: {r['id']} FRAMED bolumu yok ya da kagit iddiasi var. DUR.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tarih", default=date.today().isoformat())
    a = ap.parse_args()
    tarih = date.fromisoformat(a.tarih)
    sablon = (VERI / "aciklama_v3_sablon.txt").read_text(encoding="utf-8").strip()
    tarihler = {r["burc"]: r["tarih"] for r in csv.DictReader(open(VERI / "burc_tarih.csv", encoding="utf-8"))}
    ortak = ortak_etiketler(tarih)
    kayit = []
    for r in csv.DictReader(open(VERI / "pod78_ids.csv", encoding="utf-8")):
        A, B = r["a"], r["b"]
        aciklama = (sablon.replace("{A_TARIH}", tarihler[A]).replace("{B_TARIH}", tarihler[B])
                    .replace("{A}", A).replace("{B}", B))
        if A == B:  # ayni burc cifti: tarih satiri tekrar etmesin
            aciklama = aciklama.replace(f"{A}: {tarihler[A]}. {B}: {tarihler[B]}.", f"{A}: {tarihler[A]}.")
        rec = {"id": r["listing_id"], "pair": r["cift"],
               "title": f"{A} and {B} Personalized Zodiac Couple Wall Art",
               "description": aciklama, "tags": [cift_etiketi(A, B)] + ortak}
        denetle(rec)
        kayit.append(rec)
    if len(kayit) != 78 or len({k["id"] for k in kayit}) != 78:
        raise SystemExit(f"HATA: {len(kayit)} kayit. DUR.")
    Path(a.out).write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    yedek = sum(1 for k in kayit if k["tags"][0] == YEDEK_CIFT)
    print(f"OK {len(kayit)} ilan | tarih {tarih} | yedek cift etiketi {yedek} | "
          f"en uzun baslik {max(len(k['title']) for k in kayit)} | "
          f"aciklama {min(len(k['description']) for k in kayit)}-{max(len(k['description']) for k in kayit)} karakter")


if __name__ == "__main__":
    sys.exit(main())
