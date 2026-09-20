#!/usr/bin/env python3
"""
DIJITAL 78 - POD galeri dilinde 3 yeni dijital bilgi karti (3000x2250).

POD kart sablonu `pod_gallery_sample.py` icinden BIREBIR alinir: ayni olculmus
geometri (REF), ayni palet olcumu (10_/09_ CRAFTED_DETAIL kartindan), ayni
fontlar (Cormorant Garamond + Montserrat), ayni alt bar ve rozetli satirlar.
Degisen yalniz metin ve sag gorseldir.

Yerine gectikleri POD kartlari: Paper & Quality, Size Guide, Shipping & Care.

Kurallar: Ingilizce metinde uzun tire YOK, "studio" YOK, Amerikan yazimi (color).
"""
import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pod_gallery_sample import (  # noqa: E402
    W, H, REF, TEXT, Fonts, card_base, draw_tracked, mix, numbered_rows,
    palette, paste_shadowed, solve_size,
)

EDISYONLAR = ["Champagne Ivory", "Pure White", "Warm Parchment", "Midnight Blue", "Deep Black"]

KART = {
    "INCLUDED": {
        "kicker": "EVERY COLOR IN ONE PURCHASE",
        "title": "What's Included",
        "rows": [
            ("5 COLOR EDITIONS", "Champagne Ivory, Pure White, Warm Parchment, Midnight Blue, Deep Black"),
            ("5 ZIP FILES", "One archive per color edition, all in the same order"),
            ("5 PRINT RATIOS", "2:3, 3:4, 4:5, 11:14 and A series inside every ZIP"),
            ("PRINT AND CARE GUIDE", "A PDF with printing advice in every ZIP"),
            ("THANK YOU NOTE", "A PDF note from us in every ZIP"),
        ],
        "footer": "Five Colors, One Instant Download",
    },
    "SIZES": {
        "kicker": "PRINT AT 300 DPI",
        "title": "Print Sizes",
        "rows": [
            ("2:3 RATIO", "Prints up to 24x36 in (61x91 cm)"),
            ("3:4 RATIO", "Prints up to 24x32 in (61x81 cm)"),
            ("4:5 RATIO", "Prints up to 24x30 in (61x76 cm)"),
            ("11:14 RATIO", "Prints up to 22x28 in (56x71 cm)"),
            ("A SERIES", "Prints up to A0 (84x119 cm)"),
        ],
        "footer": "Full Artwork in Every Ratio, Nothing Cropped",
    },
    "HOWTO": {
        "kicker": "AFTER YOUR PAYMENT CLEARS",
        "title": "How to Download & Print",
        "rows": [
            ("DOWNLOAD", "Open Etsy, go to Your account, then Purchases and reviews"),
            ("UNZIP", "Extract the color edition you want to print"),
            ("CHOOSE", "Pick the JPG that matches your print size"),
            ("PRINT", "At home, at a local print shop or with an online service"),
        ],
        "footer": "Ask for Printing Without Cropping",
    },
}
# Sag gorsel icin oranlar: (ad, en, boy) - basilabilir en buyuk boy (inc), olculen pikselden
ORAN_KUTU = [("2:3", 24, 36), ("3:4", 24, 32), ("4:5", 24, 30), ("11:14", 22, 28), ("A0", 33.1, 46.8)]

UZUN_TIRE = re.compile(r"[—–]")
YASAK = re.compile(r"studio|\bcolour\b", re.I)


def qc(kart):
    h = []
    for ad, k in kart.items():
        metin = " ".join([k["kicker"], k["title"], k["footer"]]
                         + [x for r in k["rows"] for x in r])
        if UZUN_TIRE.search(metin):
            h.append(f"{ad}: uzun tire var")
        m = YASAK.search(metin)
        if m:
            h.append(f"{ad}: yasak ifade '{m.group(0)}'")
        if len(k["rows"]) > 5:
            h.append(f"{ad}: {len(k['rows'])} satir (en fazla 5)")
    return h


# ------------------------------------------------------------------ sag gorseller
def poster_yelpazesi(posterler, yukseklik=640):
    """5 edisyon posteri kademeli yelpaze (soldan saga, sonuncusu onde).
    Olcu sag sutuna (genislik <= 880 px) sigacak sekilde secildi."""
    if not posterler:
        return None
    w = int(yukseklik * 0.75)
    adim, kademe = int(w * 0.21), int(yukseklik * 0.035)
    tuval = Image.new("RGBA", (w + adim * (len(posterler) - 1) + 60,
                               yukseklik + kademe * (len(posterler) - 1) + 60), (0, 0, 0, 0))
    for i, p in enumerate(posterler):
        th = p.convert("RGB").resize((w, yukseklik), Image.LANCZOS)
        golge = Image.new("RGBA", (w + 40, yukseklik + 40), (0, 0, 0, 0))
        ImageDraw.Draw(golge).rectangle([20, 24, 20 + w, 24 + yukseklik], fill=(0, 0, 0, 70))
        x, y = i * adim, i * kademe
        tuval.paste(golge, (x - 10, y - 10), golge)
        tuval.paste(th, (x, y))
        ImageDraw.Draw(tuval).rectangle([x, y, x + w - 1, y + yukseklik - 1],
                                        outline=(255, 255, 255, 150), width=3)
    return tuval


def oran_diyagrami(pal, F, genislik=880, yukseklik=880):
    """5 oran esit YUKSEKLIKTE, 3+2 izgara; etiket kutunun altinda.
    Oran kutulari birbirine gore olcekli degil, ORAN SEKLINI gosterir; en buyuk
    basim boyu metin satirlarinda yazar."""
    S = 2
    img = Image.new("RGBA", (genislik * S, yukseklik * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    notr_cizgi = mix(pal["ink"], pal["bg"], 0.45) + (255,)
    f_lab = F.f("sans", solve_size(F, "sans", 600, 22) * S, 600)
    kutu_h = 330 * S
    etiket_h = 60 * S
    satir_bosluk = 70 * S
    siralar = [ORAN_KUTU[:3], ORAN_KUTU[3:]]
    toplam_h = len(siralar) * (kutu_h + etiket_h) + (len(siralar) - 1) * satir_bosluk
    y = (yukseklik * S - toplam_h) / 2
    for sira in siralar:
        genislikler = [kutu_h * en / boy for _, en, boy in sira]
        bosluk = 46 * S
        x = (genislik * S - sum(genislikler) - bosluk * (len(sira) - 1)) / 2
        for (ad, _, _), w in zip(sira, genislikler):
            d.rectangle([x, y, x + w, y + kutu_h],
                        fill=mix(pal["ink"], pal["bg"], 0.94) + (255,),
                        outline=notr_cizgi, width=5)
            d.text((x + w / 2, y + kutu_h + 14 * S), ad, font=f_lab,
                   fill=mix(pal["ink"], pal["bg"], 0.12) + (255,), anchor="ma")
            x += w + bosluk
        y += kutu_h + etiket_h + satir_bosluk
    return img.resize((genislik, yukseklik), Image.LANCZOS)


INDIRME_IKON = [  # 24x24 izgara, tabler "download" dili: ok + tepsi
    [(12, 3), (12, 15)],
    [(7, 10), (12, 15), (17, 10)],
    [(4, 17), (4, 20), (20, 20), (20, 17)],
]


def indirme_ikonu(pal, size=760, stroke=4):
    S = 4
    img = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = size * S / 24
    col = pal["rule"] + (255,)
    w = stroke * S
    for path in INDIRME_IKON:
        pts = [(x * k, y * k) for x, y in path]
        d.line(pts, fill=col, width=w, joint="curve")
        for x, y in pts:
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=col)
    return img.resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------------ kartlar
def kart_included(pal, F, pair_txt, posterler):
    k = KART["INCLUDED"]
    im, d = card_base(pal, F, k["kicker"], k["title"], pair_txt, k["footer"])
    fan = poster_yelpazesi(posterler, 700)
    if fan is not None:
        oran = min(1.0, 880 / fan.width)
        fan = fan.resize((int(fan.width * oran), int(fan.height * oran)), Image.LANCZOS)
        im.paste(fan, (2430 - fan.width // 2, 1270 - fan.height // 2), fan)
    numbered_rows(d, F, pal, k["rows"], 640, 1900)
    return im


def kart_sizes(pal, F, pair_txt, posterler):
    k = KART["SIZES"]
    im, d = card_base(pal, F, k["kicker"], k["title"], pair_txt, k["footer"])
    diy = oran_diyagrami(pal, F, 880, 900)
    im.paste(diy, (2430 - diy.width // 2, 1270 - diy.height // 2), diy)
    numbered_rows(d, F, pal, k["rows"], 640, 1900)
    return im


def kart_howto(pal, F, pair_txt, posterler):
    k = KART["HOWTO"]
    im, d = card_base(pal, F, k["kicker"], k["title"], pair_txt, k["footer"])
    ikon = indirme_ikonu(pal)
    im.paste(ikon, (2430 - ikon.width // 2, 1270 - ikon.height // 2), ikon)
    numbered_rows(d, F, pal, k["rows"], 640, 1880)
    return im


CIZ = [("WHATS_INCLUDED", kart_included), ("PRINT_SIZES", kart_sizes), ("HOW_TO_DOWNLOAD", kart_howto)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--palet-karti", required=True, help="09_/10_ CRAFTED_DETAIL karti (palet olcumu)")
    ap.add_argument("--posterler", default="", help="5 edisyon posteri, virgulle (yelpaze icin)")
    ap.add_argument("--cift", default="ARIES_LEO")
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    hatalar = qc(KART)
    if hatalar:
        for x in hatalar:
            print("QC HATA: " + x, flush=True)
        raise SystemExit(1)
    print("QC PASS: 3 kart metni kurallara uygun", flush=True)

    pal = palette(a.palet_karti)
    print(f"palet: {pal}", flush=True)
    F = Fonts(a.fonts)
    a1, b1 = a.cift.split("_")[0], a.cift.split("_")[-1]
    pair_txt = f"{a1} • {b1}"
    posterler = [Image.open(p) for p in a.posterler.split(",") if p.strip() and Path(p.strip()).exists()]
    print(f"poster: {len(posterler)}", flush=True)

    yollar = []
    for ad, fn in CIZ:
        im = fn(pal, F, pair_txt, posterler)
        p = out / f"{ad}_{a.cift}.jpg"
        im.save(p, "JPEG", quality=95, optimize=True, subsampling=0)
        yollar.append(p)
        print(f"  {p.name} {im.size} {p.stat().st_size/1e3:.0f} KB", flush=True)
    print("BITTI", flush=True)


if __name__ == "__main__":
    main()
