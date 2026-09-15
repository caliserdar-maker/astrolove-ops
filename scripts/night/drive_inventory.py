#!/usr/bin/env python3
"""GECE DENETIMI - GOREV 6: Drive urun/medya envanteri (Mo 15 Eyl 2026).

SALT OKUR: hicbir dosya degistirilmez, tasinmaz, silinmez. Girdi, workflow'un
rclone lsjson ile urettigi dosya listesi (JSON). 78 burc cifti icin poster, wallpaper,
mockup, video, ZIP ve PDF dosyalari eslenir; eksik / yinelenen / yanlis adlandirilmis
/ yanlis cifte ait dosyalar raporlanir.

Kullanim: drive_inventory.py --listing L.json --pod-state P.csv --out OUT
"""
import argparse
import csv
import json
import pathlib
import re
from collections import defaultdict

BURCLAR = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
EDISYON = ["Champagne_Ivory", "Pure_White", "Warm_Parchment", "Midnight_Blue", "Deep_Black"]
# Alt cizgi kelime karakteri oldugu icin \b "Aries_Leo" icinde caliSmaz; harf sinirina bakilir.
BURC_RX = re.compile(r"(?<![A-Za-z])(" + "|".join(BURCLAR) + r")(?![A-Za-z])", re.I)

TUR = [
    ("zip", re.compile(r"\.zip$", re.I)),
    ("pdf", re.compile(r"\.pdf$", re.I)),
    ("video", re.compile(r"\.(mp4|mov|webm)$", re.I)),
    ("mockup", re.compile(r"mockup|scene|hero|room", re.I)),
    ("wallpaper", re.compile(r"wallpaper|phone|tablet|desktop|watch", re.I)),
    ("poster/print", re.compile(r"print|poster|\.(png|jpg|jpeg|tif|tiff)$", re.I)),
]


def tur_bul(yol):
    for ad, rx in TUR:
        if rx.search(yol):
            return ad
    return "diger"


def cift_bul(yol):
    """Yoldaki ilk iki burc adi -> alfabetik cift anahtari."""
    b = [m.group(1).capitalize() for m in BURC_RX.finditer(yol)]
    if len(b) < 2:
        return None, b
    return "_".join(sorted(x.upper() for x in b[:2])), b[:2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing", required=True)
    ap.add_argument("--pod-state", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    beklenen = set()
    with open(a.pod_state, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("pair") or "") and (r.get("listing_id") or "").isdigit():
                beklenen.add("_".join(sorted(r["pair"].split("_"))))

    dosyalar = json.loads(pathlib.Path(a.listing).read_text(encoding="utf-8"))
    cift_tur = defaultdict(lambda: defaultdict(list))
    ciftsiz, adlar = [], defaultdict(list)
    for d in dosyalar:
        yol = d.get("Path") or d.get("Name") or ""
        if not yol or d.get("IsDir"):
            continue
        ad = pathlib.PurePath(yol).name
        adlar[ad].append(yol)
        cift, burc = cift_bul(yol)
        tur = tur_bul(yol)
        if cift is None:
            ciftsiz.append((yol, tur, len(burc)))
        else:
            cift_tur[cift][tur].append((yol, int(d.get("Size") or 0)))

    satir = []
    for cift in sorted(beklenen):
        t = cift_tur.get(cift, {})
        eksik = [x for x in ("zip", "poster/print", "mockup", "video") if not t.get(x)]
        satir.append({
            "cift": cift, "beklenen": "EVET",
            "zip": len(t.get("zip", [])), "pdf": len(t.get("pdf", [])),
            "poster_print": len(t.get("poster/print", [])), "mockup": len(t.get("mockup", [])),
            "wallpaper": len(t.get("wallpaper", [])), "video": len(t.get("video", [])),
            "diger": len(t.get("diger", [])),
            "toplam": sum(len(v) for v in t.values()),
            "sonuc": "EKSIK" if eksik else "TAM",
            "not": ("eksik tur: " + ",".join(eksik)) if eksik else "",
        })
    for cift in sorted(set(cift_tur) - beklenen):
        t = cift_tur[cift]
        satir.append({"cift": cift, "beklenen": "HAYIR",
                      "zip": len(t.get("zip", [])), "pdf": len(t.get("pdf", [])),
                      "poster_print": len(t.get("poster/print", [])),
                      "mockup": len(t.get("mockup", [])), "wallpaper": len(t.get("wallpaper", [])),
                      "video": len(t.get("video", [])), "diger": len(t.get("diger", [])),
                      "toplam": sum(len(v) for v in t.values()), "sonuc": "BEKLENMEYEN_CIFT",
                      "not": "POD_LISTINGS_STATE'te olmayan cift"})
    kopya = {ad: yollar for ad, yollar in adlar.items() if len(yollar) > 1}
    for ad, yollar in sorted(kopya.items(), key=lambda kv: -len(kv[1]))[:200]:
        satir.append({"cift": "(yinelenen ad)", "beklenen": "", "zip": "", "pdf": "",
                      "poster_print": "", "mockup": "", "wallpaper": "", "video": "",
                      "diger": "", "toplam": len(yollar), "sonuc": "YINELENEN",
                      "not": f"{ad} -> {len(yollar)} kopya: {'; '.join(yollar[:3])}"})

    sutun = ["cift", "beklenen", "zip", "pdf", "poster_print", "mockup", "wallpaper", "video",
             "diger", "toplam", "sonuc", "not"]
    with open(out / "task_06_drive_inventory.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sutun)
        w.writeheader()
        for x in satir:
            w.writerow(x)

    ozet = {
        "taranan_dosya": len(dosyalar),
        "beklenen_cift": len(beklenen),
        "cifti_cozulen_dosya": sum(sum(len(v) for v in t.values()) for t in cift_tur.values()),
        "cifte_baglanamayan_dosya": len(ciftsiz),
        "tam_cift": sum(1 for x in satir if x["sonuc"] == "TAM"),
        "eksik_cift": sum(1 for x in satir if x["sonuc"] == "EKSIK"),
        "beklenmeyen_cift": sum(1 for x in satir if x["sonuc"] == "BEKLENMEYEN_CIFT"),
        "yinelenen_ad": len(kopya),
    }
    (out / "_task_06_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    print("GOREV 6 ozet:", json.dumps(ozet, ensure_ascii=False))


if __name__ == "__main__":
    main()
