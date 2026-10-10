#!/usr/bin/env python3
"""ADIM 3 analiz (etsy-arama, 10 Eki 2026): etiket ve baslik onerisi MI hacmine gore + PASS/FAIL denetim.

Girdi: 5_CAPRAZ_KONTROL_DOLU.csv (Drive 1aIes28V..., S001-S229), canli_78.json (API salt okur, 10 Eki 08:33 UTC).
Cikti: ETIKET_ONERI.csv, BASLIK_ONERI.csv, adim3_sayilar.json. Etsy'ye yazmaz.
Kullanim: python3 arama_adim3.py <dolu.csv> <canli_78.json> <cikti_klasoru>
"""
import csv
import json
import re
import sys
from pathlib import Path

SATIS = {"AQUARIUS_LIBRA", "AQUARIUS_SCORPIO", "CANCER_LEO"}
# Degisim kurali (MI esas): dusuk hacimli 2 etiket -> yuksek hacimli, urunle ilgili 2 terim
DEGIS = {
    "astrology couple art": "1st anniversary gift",  # S002 6/5.4k -> S055 22.5k/66.9k (kagit baski = 1. yil "paper")
    "giclee print": "astrology decor",               # S012 736/950.9k (kategori Giclee kapsar) -> S219 6.5k/14.5k
}


def sayi(v):
    s = (v or "").strip().lower().replace(",", "")
    if not s or s == "yok":
        return None
    k = 1
    if s.endswith("k"):
        s, k = s[:-1], 1e3
    elif s.endswith("m"):
        s, k = s[:-1], 1e6
    try:
        return int(round(float(s) * k))
    except ValueError:
        return None


def mi_tablo(path):
    t = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        s = r["not"][:4]
        if r["terim"] not in t:  # ayni terim iki kez varsa ilki (tek sayim)
            t[r["terim"]] = (s, r["MI arama/30g"].strip(), r["MI rekabet"].strip())
    return t


def hucre(tag, t):
    s, a, k = t.get(tag, ("-", "olculmedi", "olculmedi"))
    return f"{tag} [{s}: {a} / {k}]"


def baslik(a, b):
    return f"{a} and {b} Couple Wall Art, Personalized Zodiac Print with Names"


def main(dolu, canli, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    t = mi_tablo(dolu)
    rows = json.load(open(canli, encoding="utf-8"))
    et, ba, hata = [], [], []
    top_m = top_o = 0
    degisen = 0
    for r in rows:
        a, b = [x.title() for x in r["zodiac_pair"].split("_")]
        cur = r["tags"].split(" | ")
        yeni = [DEGIS.get(x, x) for x in cur]
        sm = sum(sayi(t.get(x, ("", "", ""))[1]) or 0 for x in cur)
        so = sum(sayi(t.get(x, ("", "", ""))[1]) or 0 for x in yeni)
        kontrol = r["zodiac_pair"] in SATIS
        n = sum(x != y for x, y in zip(cur, yeni))
        if not kontrol:
            degisen += n
            top_m += sm
            top_o += so
        row = {"listing_id": r["listing_id"], "cift": r["zodiac_pair"],
               "satis_alan": "EVET: kontrol, degismez" if kontrol else "",
               "mevcut_13": " | ".join(cur), "onerilen_13": " | ".join(yeni),
               "degisen": "; ".join(f"{x} -> {y}" for x, y in zip(cur, yeni) if x != y) or "yok",
               "mevcut_MI_toplam": sm, "onerilen_MI_toplam": so}
        for i, x in enumerate(cur, 1):
            row[f"m{i:02d}"] = hucre(x, t)
        for i, x in enumerate(yeni, 1):
            row[f"o{i:02d}"] = hucre(x, t)
        et.append(row)
        # denetim
        if len(yeni) != 13 or len(set(yeni)) != 13 or any(len(x) > 20 for x in yeni):
            hata.append((r["zodiac_pair"], "13 benzersiz / <=20"))
        if any(x in ("cancer", "cancer gift", "cancer art") for x in yeni):
            hata.append((r["zodiac_pair"], "tek basina cancer"))
        if "newlywed gift" in cur and "newlywed gift" not in yeni:
            hata.append((r["zodiac_pair"], "mevsim kurali bozuldu"))
        nb = baslik(a, b)
        low = nb.lower()
        if low.count(a.lower()) < (2 if a == b else 1) or b.lower() not in low or len(nb) > 140 or len(nb.split()) > 15:
            hata.append((r["zodiac_pair"], "baslik"))
        pair = f"{a.lower()} and {b.lower()}"
        pm = t.get(pair, t.get(cur[0], ("-", "yok", "yok")))
        ba.append({"listing_id": r["listing_id"], "cift": r["zodiac_pair"],
                   "satis_alan": "EVET: kontrol, degismez" if kontrol else "",
                   "mevcut_baslik": r["title"], "onerilen_baslik": nb,
                   "mevcut_ilk40": r["title"][:40], "onerilen_ilk40": nb[:40],
                   "kelime_gruplari_MI": (f"{pair} [{pm[0]}: {pm[1]}] | couple wall art [S060: 1.1k / 226.8k] | "
                                          "zodiac print [S016: 108 / 70.5k] | names: couple names print [S023: 1 / 40.7k]")})
    blob = json.dumps(et + ba, ensure_ascii=False)
    if re.search("[–—]", blob):
        hata.append(("*", "uzun/orta tire"))
    for fn, data in (("ETIKET_ONERI.csv", et), ("BASLIK_ONERI.csv", ba)):
        with open(out / fn, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    n = len([r for r in rows if r["zodiac_pair"] not in SATIS])
    say = {"ilan": len(rows), "uygulanan_ilan": n, "degisen_etiket": degisen,
           "mevcut_MI_toplam": top_m, "onerilen_MI_toplam": top_o,
           "ilan_basi_mevcut": round(top_m / n), "ilan_basi_onerilen": round(top_o / n),
           "denetim": "PASS" if not hata else hata}
    (out / "adim3_sayilar.json").write_text(json.dumps(say, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(say, ensure_ascii=False))
    return 0 if not hata else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
