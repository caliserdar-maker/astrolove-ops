#!/usr/bin/env python3
"""YD 10'lu set kontrol paftasi (Serdar 30 Eki karar 3). ETSY API YOK, ag yok; yalniz yerel klasor okunur.
Kart turu basina (Y01, Y02, Y03, Y05-Y10) tek sayfa: data/pod/yd78_ids.csv sirasiyla 78 kucuk gorsel, her hucrede cift adi,
hucre genisligi en az 300 px (varsayilan 320). ORTAK_Y04 tek gorsel (KONTAK_Y04.jpg). Eksik dosya hucresi kirmizi "YOK".
Cikti: KONTAK_Y<NN>.jpg + OZET.md (pafta, hucre, eksik). Cikis 0 = tum dosyalar var, 1 = eksik var (pafta yine yazilir)."""
import argparse
import csv
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

KARTLAR = (1, 2, 3, 5, 6, 7, 8, 9, 10)
ORTAK = "ORTAK_Y04.jpg"
FONT_YOL = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf")


def font(boy):
    for y in FONT_YOL:
        if Path(y).exists():
            return ImageFont.truetype(y, boy)
    return ImageFont.load_default(size=boy)


def pafta(ogeler, out, hucre_w=320, sutun=10, baslik=""):
    """ogeler: [(etiket, yol|None)]. Hucre: gorsel hucre_w x 3/4 + etiket bandi."""
    hucre_h = hucre_w * 3 // 4
    bant, pay, ust = 34, 8, 60
    sutun = min(sutun, len(ogeler))
    satir = math.ceil(len(ogeler) / sutun)
    W = pay + sutun * (hucre_w + pay)
    H = ust + satir * (hucre_h + bant + pay) + pay
    sayfa = Image.new("RGB", (W, H), (245, 245, 245))
    d = ImageDraw.Draw(sayfa)
    f, fb = font(18), font(30)
    d.text((pay, 14), baslik, fill=(0, 0, 0), font=fb)
    eksik = []
    for i, (etiket, yol) in enumerate(ogeler):
        x = pay + (i % sutun) * (hucre_w + pay)
        y = ust + (i // sutun) * (hucre_h + bant + pay)
        if yol and Path(yol).is_file():
            with Image.open(yol) as im:
                im = im.convert("RGB")
                im.thumbnail((hucre_w, hucre_h), Image.LANCZOS)
                sayfa.paste(im, (x + (hucre_w - im.width) // 2, y + (hucre_h - im.height) // 2))
        else:
            eksik.append(etiket)
            d.rectangle([x, y, x + hucre_w - 1, y + hucre_h - 1], fill=(255, 220, 220), outline=(200, 0, 0), width=3)
            d.text((x + 10, y + 10), "YOK", fill=(200, 0, 0), font=fb)
        d.text((x + 2, y + hucre_h + 6), etiket, fill=(0, 0, 0), font=f)
    sayfa.save(out, quality=90)
    return dict(dosya=Path(out).name, hucre=len(ogeler), hucre_w=hucre_w, boyut=f"{W}x{H}", eksik=eksik)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--ciftler", default="data/pod/yd78_ids.csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--hucre", type=int, default=320)
    ap.add_argument("--kaynak", default="", help="raporda gosterilecek Drive klasoru")
    a = ap.parse_args(argv)
    if a.hucre < 300:
        raise SystemExit("HATA: hucre genisligi en az 300 px (Serdar 30 Eki). DUR.")
    ciftler = [r["cift"].strip() for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig")) if (r.get("cift") or "").strip()]
    if len(ciftler) != 78 or len(set(ciftler)) != 78:
        raise SystemExit(f"HATA: cift listesi 78 tekil degil ({len(ciftler)}). DUR.")
    d, out = Path(a.dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sonuc = []
    for n, k in enumerate(KARTLAR, 1):
        og = [(c, d / f"{c}_Y{k:02d}.jpg") for c in ciftler]
        sonuc.append(pafta(og, out / f"KONTAK_Y{k:02d}.jpg", a.hucre, 10, f"YD Y{k:02d} | 78 cift | {a.kaynak}"))
        print(f"[{n}/{len(KARTLAR) + 1}] KONTAK_Y{k:02d} eksik {len(sonuc[-1]['eksik'])}", flush=True)
    sonuc.append(pafta([("ORTAK_Y04", d / ORTAK)], out / "KONTAK_Y04.jpg", 1200, 1, f"YD Y04 ORTAK | {a.kaynak}"))
    print(f"[{len(KARTLAR) + 1}/{len(KARTLAR) + 1}] KONTAK_Y04 eksik {len(sonuc[-1]['eksik'])}", flush=True)
    toplam_eksik = sum(len(s["eksik"]) for s in sonuc)
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# YD kontrol paftasi\n\n{'PASS' if not toplam_eksik else 'EKSIK'} | pafta {len(sonuc)} | eksik dosya {toplam_eksik}\n"
                f"kaynak: {a.kaynak or a.dir}; cift sirasi {a.ciftler}; hucre {a.hucre} px (Y04 1200 px). Etsy istegi yok.\n\n"
                "| pafta | hucre | boyut | eksik |\n|---|---|---|---|\n")
        f.writelines(f"| {s['dosya']} | {s['hucre']} | {s['boyut']} | {', '.join(s['eksik']) or '-'} |\n" for s in sonuc)
    print(f"KONTAK OZET: pafta {len(sonuc)} eksik {toplam_eksik}")
    return 1 if toplam_eksik else 0


if __name__ == "__main__":
    sys.exit(main())
