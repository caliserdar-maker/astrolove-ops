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

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pod_gallery_sample import (  # noqa: E402
    W, H, REF, TEXT, Fonts, card_base, draw_tracked, mix, numbered_rows,
    palette, paste_shadowed, solve_size, solve_tracking, text_w,
)

EDISYONLAR = ["Midnight Blue", "Deep Black", "Warm Parchment", "Champagne Ivory", "Pure White"]
# 300 DPI'de yaygin baski boylari (cm = inc x 2.54, POD Size Guide bicimi: x ve bir ondalik)
BOYLAR = {
    "2:3": [("4x6", 4, 6), ("8x12", 8, 12), ("12x18", 12, 18), ("16x24", 16, 24),
            ("20x30", 20, 30), ("24x36", 24, 36)],
    "3:4": [("6x8", 6, 8), ("9x12", 9, 12), ("12x16", 12, 16), ("18x24", 18, 24), ("24x32", 24, 32)],
    "4:5": [("8x10", 8, 10), ("16x20", 16, 20), ("24x30", 24, 30)],
    "11:14": [("11x14", 11, 14), ("22x28", 22, 28)],
    "A": [("A5", 5.8, 8.3), ("A4", 8.3, 11.7), ("A3", 11.7, 16.5), ("A2", 16.5, 23.4),
          ("A1", 23.4, 33.1), ("A0", 33.1, 46.8)],
}
ORAN_ADI = {"2:3": "2:3 RATIO", "3:4": "3:4 RATIO", "4:5": "4:5 RATIO",
            "11:14": "11:14 RATIO", "A": "A SERIES"}
A_CM = {"A5": (14.8, 21.0), "A4": (21.0, 29.7), "A3": (29.7, 42.0),
        "A2": (42.0, 59.4), "A1": (59.4, 84.1), "A0": (84.1, 118.9)}   # ISO 216 resmi olculer


def cm(inc):
    """POD Size Guide bicimi: bir ondalik."""
    return f"{inc * 2.54:.1f}"


def boy_satirlari(olculen=None):
    """Oran -> (baslik, 'Up to ...', 'boy . boy . boy in') uclusu.
    olculen: {oran: (px_en, px_boy)} verilirse 300 DPI'de sigmayan boylar dusurulur."""
    satirlar, dusen = [], []
    for oran, liste in BOYLAR.items():
        uygun = liste
        if olculen and oran in olculen:
            en_px, boy_px = olculen[oran]
            uygun = [b for b in liste if b[1] * 300 <= en_px + 2 and b[2] * 300 <= boy_px + 2]
            dusen += [b[0] for b in liste if b not in uygun]
        if not uygun:
            continue
        ad, e, b = uygun[-1]
        buyuk = (f"Up to {ad} in · {cm(e)}×{cm(b)} cm" if oran != "A"
                 else f"Up to {ad} · {e:g}×{b:g} in · {cm(e)}×{cm(b)} cm")
        satirlar.append((ORAN_ADI[oran], buyuk,
                         " · ".join(x[0] for x in uygun) + ("" if oran == "A" else " in")))
    return satirlar, dusen

KART = {
    "INCLUDED": {
        "kicker": "EVERY COLOR IN ONE PURCHASE",
        "title": "What's Included",
        "rows": [
            ("5 COLOR EDITIONS", "Midnight Blue, Deep Black, Warm Parchment, Champagne Ivory, Pure White"),
            ("5 ZIP FILES", "One archive per color, same files in each"),
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
            ("DOWNLOAD", "Open Etsy on a computer or mobile browser, go to Your account,\n"
                         "then Purchases and reviews. Download all 5 ZIP files."),
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
def poster_golgesi(w, h, kayma=(16, 26), blur=26, alpha=95):
    """Yumusak, gercekci dusen golge (kartin acik zeminine)."""
    dx, dy = kayma
    pay = blur * 3
    g = Image.new("RGBA", (w + pay * 2, h + pay * 2), (0, 0, 0, 0))
    ImageDraw.Draw(g).rectangle([pay + dx, pay + dy, pay + dx + w, pay + dy + h], fill=(18, 22, 34, alpha))
    return g.filter(ImageFilter.GaussianBlur(blur)), pay


def poster_yelpazesi(posterler, yukseklik=700, ortusme=0.42):
    """5 edisyon posteri: ARKA PLAN YOK, kademeli dizilim, her birinde yumusak golge.
    Acik posterlerin (Pure White) kenari kaybolmasin diye ince bir kenar cizgisi var."""
    if not posterler:
        return None
    ilk = posterler[0]
    w = max(1, int(round(yukseklik * ilk.width / ilk.height)))
    adim, kademe = int(w * (1 - ortusme)), int(yukseklik * 0.045)
    pay = 90
    tuval = Image.new("RGBA", (w + adim * (len(posterler) - 1) + pay * 2,
                               yukseklik + kademe * (len(posterler) - 1) + pay * 2), (0, 0, 0, 0))
    for i, poster in enumerate(posterler):
        th = poster.convert("RGB").resize((w, yukseklik), Image.LANCZOS)
        x, y = pay + i * adim, pay + i * kademe
        golge, gp = poster_golgesi(w, yukseklik)
        tuval.alpha_composite(golge, (x - gp, y - gp))
        tuval.paste(th, (x, y))
        ImageDraw.Draw(tuval).rectangle([x, y, x + w - 1, y + yukseklik - 1],
                                        outline=(120, 124, 136, 110), width=2)
    return tuval


def oran_diyagrami(pal, F, genislik=880, yukseklik=900, kutular=None):
    """POD Size Guide dilinde GERCEK OLCEKLI oran kutulari: her oranin en buyuk
    boyu, ortak tabana oturmus yan yana, dolgusuz ince cizgi, altinda oran adi."""
    S = 2
    kutular = kutular or [("2:3", 24, 36), ("3:4", 24, 32), ("4:5", 24, 30),
                          ("11:14", 22, 28), ("A SERIES", 33.1, 46.8)]
    img = Image.new("RGBA", (genislik * S, yukseklik * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f_lab = F.f("sans", solve_size(F, "sans", 600, 21) * S, 600)
    f_alt = F.f("sans", solve_size(F, "sans", 400, 17) * S, 400)
    bosluk = 30 * S
    toplam_in = sum(k[1] for k in kutular)
    olcek = min((genislik * S - bosluk * (len(kutular) - 1) - 20 * S) / toplam_in,
                (yukseklik * S - 150 * S) / max(k[2] for k in kutular))
    toplam_px = toplam_in * olcek + bosluk * (len(kutular) - 1)
    x = (genislik * S - toplam_px) / 2
    taban = (yukseklik * S + max(k[2] for k in kutular) * olcek) / 2 - 30 * S
    cizgi = mix(pal["ink"], pal["bg"], 0.35) + (255,)
    d.line([(x - 14 * S, taban), (x + toplam_px + 14 * S, taban)],
           fill=mix(pal["ink"], pal["bg"], 0.62) + (255,), width=max(2, int(1.6 * S)))
    for ad, e, b in kutular:
        w, h = e * olcek, b * olcek
        d.rectangle([x, taban - h, x + w, taban], outline=cizgi, width=max(2, int(2.4 * S)))
        d.text((x + w / 2, taban + 30 * S), ad, font=f_lab,
               fill=mix(pal["ink"], pal["bg"], 0.1) + (255,), anchor="ma")
        d.text((x + w / 2, taban + 64 * S), f"{e:g}x{b:g} in" if not ad.startswith("A") else "A0",
               font=f_alt, fill=mix(pal["ink"], pal["bg"], 0.45) + (255,), anchor="ma")
        x += w + bosluk
    d.text((genislik * S / 2, taban + 118 * S), "REAL SCALE \u00b7 LARGEST SIZE IN EACH RATIO",
           font=f_alt, fill=mix(pal["ink"], pal["bg"], 0.5) + (255,), anchor="ma")
    return img.resize((genislik, yukseklik), Image.LANCZOS)


GOVDE_KAT = 1.30          # aciklama yazilari POD kartina gore %30 buyuk
BOY_KAT = 1.55            # "4x6 . 8x12 ..." satiri eski puntonun 1.55 kati
KENAR_PAY = 70            # metin sinir kutulari kenardan en az bu kadar uzak


def _sar(d, metin, font, en_sinir):
    """Acik satir sonlarini korur, gerekirse kelime sarmasi yapar."""
    ciktilar = []
    for parca in metin.split("\n"):
        aktif = ""
        for kelime in parca.split():
            deneme = (aktif + " " + kelime).strip()
            if d.textlength(deneme, font=font) <= en_sinir or not aktif:
                aktif = deneme
            else:
                ciktilar.append(aktif)
                aktif = kelime
        ciktilar.append(aktif)
    return ciktilar


def satirlar_ciz(d, F, pal, rows, y0=620, y1=1900, en_sinir=1380, boy_satiri=False,
                 merkez=False):
    """POD rozetli satir dili; aciklama %30 buyuk, satir sarmali.
    Doner: cizilen tum metin sinir kutulari [(x0, y0, x1, y1)] (kapi olcumu icin)."""
    r = REF["badge_d"] // 2
    cx, tx = 336, 460
    f_d = F.f("sans", solve_size(F, "sans", 600, REF["digit_h"], "01"), 600)
    f_h = F.f("sans", solve_size(F, "sans", 600, REF["head_cap"]), 600)
    tr_h = solve_tracking(d, f_h, *REF["head_w"])
    f_b = F.f("sans", solve_size(F, "sans", 400, int(REF["body_cap"] * GOVDE_KAT)), 400)
    f_s = F.f("sans", solve_size(F, "sans", 500, int((REF["body_cap"] - 5) * BOY_KAT)), 500)
    govde_h = int(REF["body_cap"] * GOVDE_KAT * 1.52)
    if merkez:                       # blok (rozet + metin) kartin icerik alaninda ortalanir
        en_genis = 0
        for satir in rows:
            en_genis = max(en_genis, text_w(d, satir[0], f_h, tr_h))
            for sat in _sar(d, satir[1], f_b, en_sinir):
                en_genis = max(en_genis, d.textlength(sat, font=f_b))
            if boy_satiri and len(satir) > 2:
                en_genis = max(en_genis, d.textlength(satir[2], font=f_s))
        blok_sol, blok_sag = cx - r, tx + en_genis
        kaydir = int((W - (blok_sag - blok_sol)) / 2 - blok_sol)
        cx, tx = cx + kaydir, tx + kaydir
    kutular = []
    step = (y1 - y0) / len(rows)
    for i, satir in enumerate(rows):
        head, body = satir[0], satir[1]
        boylar = satir[2] if boy_satiri and len(satir) > 2 else None
        govde = _sar(d, body, f_b, en_sinir)
        hb0 = f_h.getbbox("H")
        basl_h = hb0[3] - hb0[1]
        ara = int(basl_h * 0.55)
        blok = basl_h + ara + len(govde) * govde_h + (int(govde_h * 1.2) if boylar else 0)
        cy = y0 + step * (i + 0.5)
        ust = cy - blok / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal["bar"])
        num = f"{i + 1:02d}"
        b0, b1, b2, b3 = f_d.getbbox(num)
        d.text((cx - (b0 + b2) / 2, cy - (b1 + b3) / 2), num, font=f_d, fill=pal["bartext"])
        draw_tracked(d, (tx, ust - hb0[1]), head, f_h, pal["ink"], tracking=tr_h)
        kutular.append((tx, ust - 4, tx + text_w(d, head, f_h, tr_h), ust + basl_h + 4))
        y = ust + basl_h + ara
        for sat in govde:
            d.text((tx, y - f_b.getbbox("H")[1]), sat, font=f_b,
                   fill=mix(pal["ink"], pal["bg"], 0.22))
            kutular.append((tx, y - 2, tx + d.textlength(sat, font=f_b), y + govde_h - 4))
            y += govde_h
        if boylar:
            y += int(govde_h * 0.20)
            d.text((tx, y - f_s.getbbox("H")[1]), boylar, font=f_s,
                   fill=mix(pal["ink"], pal["bg"], 0.26))
            kutular.append((tx, y - 2, tx + d.textlength(boylar, font=f_s), y + govde_h - 4))
    return kutular


def yetim_kapisi(d, rows, F, en_sinir):
    """Sarilan aciklamalarda son satirda tek kelime (yetim) kalmasin."""
    f_b = F.f("sans", solve_size(F, "sans", 400, int(REF["body_cap"] * GOVDE_KAT)), 400)
    hata = []
    for satir in rows:
        sat = _sar(d, satir[1], f_b, en_sinir)
        if len(sat) > 1 and len(sat[-1].split()) < 2:
            hata.append(f"yetim kelime: '{satir[0]}' -> '{sat[-1]}'")
    return hata


def kutu_kapisi(kutular, yasak=None):
    """Olculebilir kapi: kenar payi >= KENAR_PAY ve kutular arasi cakisma = 0."""
    hata = []
    for x0, y0, x1, y1 in kutular:
        if x0 < KENAR_PAY or y0 < KENAR_PAY or x1 > W - KENAR_PAY or y1 > H - KENAR_PAY:
            hata.append(f"kenar payi ihlali: ({int(x0)},{int(y0)})-({int(x1)},{int(y1)})")
    for i in range(len(kutular)):
        for j in range(i + 1, len(kutular)):
            a, b = kutular[i], kutular[j]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                hata.append(f"cakisma: {tuple(int(v) for v in a)} x {tuple(int(v) for v in b)}")
    if yasak:
        for x0, y0, x1, y1 in kutular:
            if x0 < yasak[2] and yasak[0] < x1 and y0 < yasak[3] and yasak[1] < y1:
                hata.append(f"gorsel sutununa tasma: ({int(x0)},{int(y0)})-({int(x1)},{int(y1)})")
    return hata


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
OLCUM = {}          # {oran: (px_en, px_boy)} - koşuda ZIP'ten olculur


def kart_included(pal, F, pair_txt, posterler):
    k = KART["INCLUDED"]
    im, d = card_base(pal, F, k["kicker"], k["title"], pair_txt, k["footer"])
    fan = poster_yelpazesi(posterler, 960)
    yasak = None
    if fan is not None:
        oran = min(1.0, 1080 / fan.width, 1180 / fan.height)
        fan = fan.resize((int(fan.width * oran), int(fan.height * oran)), Image.LANCZOS)
        yer = (2440 - fan.width // 2, 1290 - fan.height // 2)
        im.paste(fan, yer, fan)
        yasak = (yer[0] + 70, yer[1] + 70, yer[0] + fan.width - 70, yer[1] + fan.height - 70)
    kutular = satirlar_ciz(d, F, pal, k["rows"], 620, 1900, en_sinir=1340)
    return im, kutular, yasak


def kart_sizes(pal, F, pair_txt, posterler):
    """Gercek olcekli oran kutulari KALDIRILDI; satirlar tum genisligi kullanir."""
    k = KART["SIZES"]
    im, d = card_base(pal, F, k["kicker"], k["title"], pair_txt, k["footer"])
    satirlar, _ = boy_satirlari(OLCUM or None)
    kutular = satirlar_ciz(d, F, pal, satirlar, 600, 1920, en_sinir=2200, boy_satiri=True,
                           merkez=True)
    return im, kutular, None


def kart_howto(pal, F, pair_txt, posterler):
    k = KART["HOWTO"]
    im, d = card_base(pal, F, k["kicker"], k["title"], pair_txt, k["footer"])
    ikon = indirme_ikonu(pal, 460, 4)
    yer = (2560 - ikon.width // 2, 1270 - ikon.height // 2)
    im.paste(ikon, yer, ikon)
    yasak = (yer[0], yer[1], yer[0] + ikon.width, yer[1] + ikon.height)
    kutular = satirlar_ciz(d, F, pal, k["rows"], 620, 1880, en_sinir=1780)
    return im, kutular, yasak


def bes_renk(pal, F, pair_txt, posterler, yukseklik=1080):
    """5 RENK galeri gorseli (3000x2250): arka plansiz 5 poster + altlarinda edisyon adi."""
    im = Image.new("RGB", (W, H), pal["bg"])
    d = ImageDraw.Draw(im)
    f_kick = F.f("sans", solve_size(F, "sans", 500, REF["kicker_cap"]), 500)
    f_baslik = F.f("serif", solve_size(F, "serif", 500, REF["title_band"][1], "Hxg"), 500)
    f_ad = F.f("sans", solve_size(F, "sans", 600, 26), 600)
    draw_tracked(d, (W / 2, 210), "FIVE COLOR EDITIONS", f_kick, mix(pal["ink"], pal["bg"], 0.35),
                 tracking=solve_tracking(d, f_kick, *REF["kicker_w"]), anchor="c")
    d.text((W / 2, 300), "Five Colors, One Download", font=f_baslik, fill=pal["ink"], anchor="ma")
    d.line([(W / 2 - 240, 520), (W / 2 + 240, 520)], fill=pal["rule"], width=3)

    if not posterler:
        return im
    n = len(posterler)
    bosluk, kenar = 34, 70                                    # ~%20 daha buyuk poster
    pw = int((W - kenar * 2 - bosluk * (n - 1)) / n)
    yukseklik = int(pw * posterler[0].height / posterler[0].width)
    ust, alt = 540, H - 150                                   # rule alti ile alt bar arasi
    if yukseklik + 110 > alt - ust:
        yukseklik = alt - ust - 110
        pw = int(yukseklik * posterler[0].width / posterler[0].height)
    toplam = pw * n + bosluk * (n - 1)
    x0 = (W - toplam) // 2
    y0 = ust + int((alt - ust - (yukseklik + 110)) / 2)
    for i, (poster, ad) in enumerate(zip(posterler, EDISYONLAR)):
        th = poster.convert("RGB").resize((pw, yukseklik), Image.LANCZOS)
        x = x0 + i * (pw + bosluk)
        golge, gp = poster_golgesi(pw, yukseklik, (10, 20), 22, 90)
        im.paste(golge, (x - gp, y0 - gp), golge)
        im.paste(th, (x, y0))
        d.rectangle([x, y0, x + pw - 1, y0 + yukseklik - 1], outline=(120, 124, 136), width=2)
        draw_tracked(d, (x + pw / 2, y0 + yukseklik + 58), ad.upper(), f_ad,
                     mix(pal["ink"], pal["bg"], 0.2), tracking=6, anchor="c")
    d.rectangle([0, H - 150, W, H], fill=pal["bar"])
    f_foot = F.f("sans", solve_size(F, "sans", 500, REF["foot_cap"]), 500)
    draw_tracked(d, (W / 2, H - 105), TEXT["common"]["bond"], f_foot, pal["bartext"],
                 tracking=solve_tracking(d, f_foot, *REF["foot_w"]), anchor="c")
    return im


CIZ = [("WHATS_INCLUDED", kart_included), ("PRINT_SIZES", kart_sizes), ("HOW_TO_DOWNLOAD", kart_howto)]
CIZ_EK = [("BES_RENK", bes_renk)]


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
