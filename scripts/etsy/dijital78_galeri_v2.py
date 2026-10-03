#!/usr/bin/env python3
"""
DIJITAL 78 - GALERI V2 (Etsy API cagrisi YOK).

Girdi:
  - GALERI_V1/GALERI_KAYNAK.csv  (canli POD gorsel URL'leri; yeni Etsy cagrisi yok)
  - ZIP_FINAL/<CIFT>/*.zip       (arka plansiz gercek poster JPG'leri + olcum)

Yaptigi:
  1. Canli kapaktan muze etiketi plakasi (dijital_kapak_plaka.py) -> KAPAK_V2.jpg
  2. 5 ZIP'ten her edisyonun posterini cikarir (arka plan YOK) ve tum oranlarin
     piksel olcusunu alir -> Print Sizes karti olculen pikselden uretilir
  3. 3 dijital kart + BES_RENK.jpg
  4. GALERI_DIZILIM_V2.jpg (15 kutu: kapak, video, 5 RENK, oda 1-2, Symbol Story,
     Crafted, What's Included, Print Sizes, How to Download, 5 edisyon)
"""
import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pod"))
import dijital_kartlar as K  # noqa: E402
from pod_gallery_sample import Fonts, palette  # noqa: E402

EDISYON_SIRA = ["Midnight_Blue", "Deep_Black", "Warm_Parchment", "Champagne_Ivory", "Pure_White"]
ORANLAR = {"2:3": 2 / 3, "3:4": 3 / 4, "4:5": 4 / 5, "11:14": 11 / 14, "A": 1 / 2 ** 0.5}
KUTU = ["1 KAPAK (etiketsiz)", "2 VIDEO (V11)", "3 5 COLORS", "4 ODA 1", "5 ODA 2",
        "6 SYMBOL STORY", "7 CRAFTED", "8 WHAT'S INCLUDED", "9 PRINT SIZES",
        "10 HOW TO DOWNLOAD", "11 MIDNIGHT BLUE", "12 DEEP BLACK", "13 WARM PARCHMENT",
        "14 CHAMPAGNE IVORY", "15 PURE WHITE"]


def indir(url, hedef):
    req = urllib.request.Request(url, headers={"User-Agent": "astrolove-ops/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(hedef, "wb") as fh:
        shutil.copyfileobj(r, fh)


def oran_adi(w, h):
    r = w / h
    return min(ORANLAR, key=lambda k: abs(ORANLAR[k] - r))


def zipten_poster(zip_yolu, hedef_yukseklik=1500):
    """ZIP icindeki JPG'lerin oran/olcusu + 2:3 posteri (arka plansiz gercek artwork)."""
    olcum, poster = {}, None
    with zipfile.ZipFile(zip_yolu) as z:
        for zi in z.infolist():
            if zi.is_dir() or not zi.filename.lower().endswith((".jpg", ".jpeg")):
                continue
            with z.open(zi) as fh:
                im = Image.open(fh)
                im.load()
            ad = oran_adi(im.width, im.height)
            olcum[ad] = (im.width, im.height)
            if ad == "2:3":
                k = hedef_yukseklik / im.height
                poster = im.convert("RGB").resize((max(1, int(im.width * k)), hedef_yukseklik),
                                                  Image.LANCZOS)
    return olcum, poster


def oynat_isareti(im):
    d = ImageDraw.Draw(im, "RGBA")
    r = int(min(im.size) * 0.13)
    cx, cy = im.width // 2, im.height // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, 120), outline=(255, 255, 255, 230),
              width=max(2, r // 12))
    ok = int(r * 0.5)
    d.polygon([(cx - ok // 2, cy - ok), (cx - ok // 2, cy + ok), (cx + ok, cy)],
              fill=(255, 255, 255, 235))
    return im


def kaydet_sinirli(im, yol, sinir):
    for q in (95, 92, 88, 84, 80, 74):
        im.save(yol, "JPEG", quality=q, optimize=True, subsampling=0 if q >= 88 else 1)
        if yol.stat().st_size <= sinir:
            return q
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaynak-csv", required=True, help="GALERI_V1/GALERI_KAYNAK.csv")
    ap.add_argument("--zip-dizin", required=True, help="cift ZIP'lerinin indirildigi yerel dizin")
    ap.add_argument("--cift", default="ARIES_LEO")
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--medya", default="_work/galeri_v2")
    ap.add_argument("--plaka-betik", default="")
    ap.add_argument("--kartlar-ad", default="DIJITAL_KARTLAR_V3.jpg")
    ap.add_argument("--bes-ad", default="BES_RENK_V2.jpg")
    ap.add_argument("--dizilim-ad", default="GALERI_DIZILIM_V3.jpg")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    medya = Path(a.medya); medya.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    satirlar = list(csv.DictReader(open(a.kaynak_csv, encoding="utf-8")))
    rol = {}
    for r in satirlar:
        rol.setdefault(r["rol"], []).append(r)
    print(f"kaynak CSV: {len(satirlar)} satir, roller {sorted(rol)}", flush=True)

    canli = {}
    for r in satirlar:
        if r["tip"] != "gorsel":
            continue
        yol = medya / f"{int(r['sira']):02d}.jpg"
        if not yol.exists():
            indir(r["url"], yol)
        canli[int(r["sira"])] = Image.open(yol).convert("RGB")
    print(f"canli gorsel: {len(canli)} indirildi | {time.time()-t0:.0f}s", flush=True)

    # --------------------------------------------------- ZIP'ten poster + olcum
    posterler, olcum = [], {}
    for ed in EDISYON_SIRA:
        eslesen = sorted(Path(a.zip_dizin).glob(f"*_{ed}_*.zip"))
        if not eslesen:
            print(f"::warning::{ed} ZIP bulunamadi", flush=True)
            continue
        o, p = zipten_poster(eslesen[0])
        olcum.update(o)
        if p is not None:
            posterler.append(p)
        print(f"  {ed}: {eslesen[0].name} oranlar {sorted(o)} | {time.time()-t0:.0f}s", flush=True)
    print(f"olculen piksel: {olcum}", flush=True)
    K.OLCUM = olcum

    # --------------------------------------------------- kapak: ETIKETSIZ (Serdar karari)
    kapak = canli.get(1)
    if a.plaka_betik:
        r2 = subprocess.run([sys.executable, a.plaka_betik, "--kapak", str(medya / "01.jpg"),
                             "--fonts", a.fonts, "--out", str(out)],
                            capture_output=True, text=True, timeout=1200)
        print((r2.stdout or "").strip()[-600:], flush=True)
        if r2.returncode == 0:
            kapak = Image.open(out / "KAPAK_PLAKA.jpg").convert("RGB")
    print("kapak: canli POD kapagi birebir (etiket/plaka yok)", flush=True)

    # --------------------------------------------------- kartlar + 5 renk
    hatalar = K.qc(K.KART)
    if hatalar:
        for x in hatalar:
            print("QC HATA: " + x, flush=True)
        raise SystemExit(1)
    print("QC PASS: kart metinleri kurallara uygun", flush=True)
    pal = palette(str(medya / f"{int(rol['CRAFTED'][0]['sira']):02d}.jpg"))
    F = Fonts(a.fonts)
    a1, b1 = a.cift.split("_")[0], a.cift.split("_")[-1]
    pair_txt = f"{a1} • {b1}"
    kartlar, kapi_hata = [], []
    for ad, fn in K.CIZ:
        im, kutular, yasak = fn(pal, F, pair_txt, posterler)
        h = K.kutu_kapisi(kutular, yasak)
        kapi_hata += [f"{ad}: {x}" for x in h]
        print(f"  kart {ad} {im.size} | {len(kutular)} metin kutusu | "
              f"yerlesim kapisi {'PASS' if not h else 'FAIL'}", flush=True)
        kartlar.append(im)
    if kapi_hata:
        for x in kapi_hata[:8]:
            print("::error::" + x, flush=True)
        raise SystemExit(3)
    bes = K.bes_renk(pal, F, pair_txt, posterler)
    q = kaydet_sinirli(bes, out / a.bes_ad, 800_000)
    print(f"{a.bes_ad} {bes.size} q{q} {(out/a.bes_ad).stat().st_size/1e3:.0f} KB", flush=True)

    kw, kh, bosluk = 1000, 750, 40
    sayfa = Image.new("RGB", (3 * kw + 4 * bosluk, kh + 2 * bosluk + 90), (250, 250, 248))
    d = ImageDraw.Draw(sayfa)
    for i, (im, ad) in enumerate(zip(kartlar, ["WHAT'S INCLUDED", "PRINT SIZES",
                                               "HOW TO DOWNLOAD & PRINT"])):
        x = bosluk + i * (kw + bosluk)
        sayfa.paste(im.resize((kw, kh), Image.LANCZOS), (x, bosluk))
        d.rectangle([x, bosluk, x + kw - 1, bosluk + kh - 1], outline=(210, 208, 202), width=2)
        d.text((x, bosluk + kh + 16), f"{8+i}. {ad}", font=F.f("sans", 30, 600), fill=(30, 34, 46))
    q = kaydet_sinirli(sayfa, out / a.kartlar_ad, 800_000)
    print(f"{a.kartlar_ad} {sayfa.size} q{q} "
          f"{(out/a.kartlar_ad).stat().st_size/1e3:.0f} KB", flush=True)

    # --------------------------------------------------- 15 kutuluk dizilim
    kare0 = None
    kp = medya / "video_kare0.jpg"
    video = next((r for r in satirlar if r["tip"] == "video"), None)
    if video and shutil.which("ffmpeg"):
        vid = medya / "video.mp4"
        if not vid.exists():
            try:
                indir(video["url"], vid)
            except Exception as ex:                          # noqa: BLE001
                print(f"   video indirilemedi: {str(ex)[:80]}", flush=True)
        if vid.exists():
            subprocess.run(["ffmpeg", "-y", "-i", str(vid), "-frames:v", "1", "-q:v", "2", str(kp)],
                           capture_output=True, timeout=600)
    if kp.exists():
        kare0 = oynat_isareti(Image.open(kp).convert("RGB"))

    oda = [int(r["sira"]) for r in rol.get("ODA", [])][:2]
    symbol = int(rol["SYMBOL_STORY"][0]["sira"]) if rol.get("SYMBOL_STORY") else None
    craft = int(rol["CRAFTED"][0]["sira"]) if rol.get("CRAFTED") else None
    edisyon = [int(r["sira"]) for r in rol.get("EDISYON", [])][:5]
    kutular = [(kapak, "POD kapagi (etiketsiz)"), (kare0, "V11 video, kare 0"), (bes, "YENI gorsel")]
    kutular += [(canli.get(s), f"POD gorsel {s}") for s in oda]
    kutular += [(canli.get(symbol), f"POD gorsel {symbol}"), (canli.get(craft), f"POD gorsel {craft}")]
    kutular += [(k, "YENI kart") for k in kartlar]
    kutular += [(canli.get(s), f"POD gorsel {s}") for s in edisyon]

    kw2, kh2, bo, sut = 380, 380, 34, 5
    sat = (len(kutular) + sut - 1) // sut
    sayfa2 = Image.new("RGB", (sut * kw2 + (sut + 1) * bo, 130 + sat * (kh2 + 100) + bo),
                       (250, 250, 248))
    d2 = ImageDraw.Draw(sayfa2)
    d2.text((bo, 34), f"DIJITAL GALERI DIZILIMI V3 - {a.cift.replace('_', ' + ')} "
            f"(Etsy duzenleme ekrani sirasi)", font=F.f("sans", 34, 700), fill=(28, 38, 62))
    d2.text((bo, 82), "14 gorsel + 1 video. 'YENI' olanlar bu oturumda uretildi.",
            font=F.f("sans", 26, 400), fill=(110, 110, 116))
    for i, (im, kaynak) in enumerate(kutular):
        r_, c_ = divmod(i, sut)
        x, y = bo + c_ * (kw2 + bo), 130 + r_ * (kh2 + 100)
        if im is not None:
            k = im.copy()
            k.thumbnail((kw2 - 8, kh2 - 8), Image.LANCZOS)
            sayfa2.paste(k, (x + (kw2 - k.width) // 2, y + (kh2 - k.height) // 2))
        else:
            d2.text((x + 16, y + kh2 // 2), "(yok)", font=F.f("sans", 26, 400), fill=(150, 150, 150))
        d2.rectangle([x, y, x + kw2 - 1, y + kh2 - 1], outline=(200, 198, 192), width=2)
        d2.text((x, y + kh2 + 10), KUTU[i], font=F.f("sans", 26, 600), fill=(30, 34, 46))
        d2.text((x, y + kh2 + 46), kaynak, font=F.f("sans", 24, 400), fill=(120, 120, 126))
    q = kaydet_sinirli(sayfa2, out / a.dizilim_ad, 800_000)
    print(f"{a.dizilim_ad} {sayfa2.size} q{q} "
          f"{(out/a.dizilim_ad).stat().st_size/1e3:.0f} KB", flush=True)

    (out / "OLCUM_V2.json").write_text(json.dumps(
        {"olculen_piksel": olcum, "poster_sayisi": len(posterler),
         "boy_satirlari": [list(x) for x in K.boy_satirlari(olcum)[0]],
         "dusen_boylar": K.boy_satirlari(olcum)[1]}, indent=2), encoding="utf-8")
    print(f"BITTI | sure {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
