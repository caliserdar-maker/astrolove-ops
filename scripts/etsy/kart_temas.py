#!/usr/bin/env python3
"""Temas sayfasi (Serdar 23 Eki madde 3; Etsy yok): kagit taramasinda eski "Fine Art Paper" kartina benzeyen (64x64 gri MAE)
ama OCR'da terim cikmayan poster gorselleri tek sayfada, ilan no + cift etiketli; ust satirda eski kartin kendisi (Drive referansi)
ve OCR bulgulu bir ornek (12. gorsel) yan yana.
Kullanim: kart_temas.py --kaynak KLASOR (GORSEL.json + GORSEL/) --ocr GORSEL_OCR.csv --ref KART.jpg --ciftler pod78_ids.csv
          --rank 11 --beklenen 55 --out KLASOR"""
import argparse
import csv
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

KOL, GEN = 8, 400
FONT = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def font(n):
    for f in FONT:
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            pass
    return ImageFont.load_default()


def karo(im, etiket, F, yuk):
    im = im.convert("RGB"); h = int(im.height * GEN / im.width)
    k = Image.new("RGB", (GEN, yuk + 44), "white"); k.paste(im.resize((GEN, h)), (0, 0))
    ImageDraw.Draw(k).text((6, yuk + 8), etiket, fill="black", font=F)
    return k


def main():
    ap = argparse.ArgumentParser()
    for x in ("--kaynak", "--ocr", "--ref", "--ciftler", "--out"):
        ap.add_argument(x, required=True)
    ap.add_argument("--rank", type=int, default=11)
    ap.add_argument("--beklenen", type=int, default=55)
    ap.add_argument("--mae", type=float, default=40.0)
    a = ap.parse_args()
    kay, out = pathlib.Path(a.kaynak), pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cift = {r["listing_id"]: r["cift"] for r in csv.DictReader(open(a.ciftler, encoding="utf-8"))}
    ocr = list(csv.DictReader(open(a.ocr, encoding="utf-8")))
    mae_k = [k for k in ocr[0] if k.startswith("mae_") and "06" in k][0]
    bulgulu = {r["listing_id"] for r in ocr if r["ocr_bulgu"]}
    sec = sorted((r for r in ocr if r["listing_id"] in cift and r["listing_id"] not in bulgulu and int(r["rank"]) == a.rank
                  and float(r[mae_k]) < a.mae), key=lambda r: cift[r["listing_id"]])
    gor = {str(g["image_id"]): g for g in json.load(open(kay / "GORSEL.json", encoding="utf-8"))}
    ornek = next((r for r in ocr if r["listing_id"] in bulgulu and r["ocr_bulgu"] and r["rank"] == "12"), None)
    F = font(20)
    ref = Image.open(a.ref); yuk = int(ref.height * GEN / ref.width)
    karolar = [karo(ref, "ESKI KART (Drive referansi)", F, yuk)]
    if ornek:
        karolar.append(karo(Image.open(kay / "GORSEL" / gor[str(ornek["image_id"])]["dosya"]), f"OCR bulgulu {ornek['listing_id']} #12", F, yuk))
    while len(karolar) % KOL:
        karolar.append(Image.new("RGB", (GEN, yuk + 44), "white"))
    eksik = []
    for r in sec:
        g = gor.get(str(r["image_id"]))
        p = kay / "GORSEL" / g["dosya"] if g else None
        if not p or not p.exists():
            eksik.append(r["listing_id"]); continue
        karolar.append(karo(Image.open(p), f"{r['listing_id']} #{r['rank']} {cift[r['listing_id']]}", font(16), yuk))
    sat = (len(karolar) + KOL - 1) // KOL
    S = Image.new("RGB", (KOL * GEN + (KOL + 1) * 8, sat * (yuk + 44) + (sat + 1) * 8), (200, 200, 200))
    for i, k in enumerate(karolar):
        S.paste(k, (8 + (i % KOL) * (GEN + 8), 8 + (i // KOL) * (yuk + 52)))
    S.save(out / "KART_TEMAS_55.jpg", quality=88)
    oz = dict(secilen=len(sec), beklenen=a.beklenen, eksik=eksik, rank=a.rank, mae_esik=a.mae, mae_alan=mae_k,
              ilanlar=[(r["listing_id"], cift[r["listing_id"]], r["image_id"], r[mae_k]) for r in sec], boyut=S.size)
    (out / "KART_TEMAS_55.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1), encoding="utf-8")
    print("TEMAS", json.dumps({k: v for k, v in oz.items() if k != "ilanlar"}, ensure_ascii=False), flush=True)
    sys.exit(0 if len(sec) == a.beklenen and not eksik else 2)


if __name__ == "__main__":
    main()
