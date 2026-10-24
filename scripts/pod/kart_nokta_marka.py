#!/usr/bin/env python3
"""23 eski galerili poster ilani, hedef galeri kart metni duzeltmesi (Serdar 24 Eki B1). Etsy'ye YAZMAZ.
Girdi: hedef galeri dosyalari (GALERI_YAYIN/YEDEK/<ilan>_<CIFT>/NN_<id>.jpg, 17 Eki galerisinin Etsy kopyasi, 3000x2250) +
duvar zemini (duvar_zemin.py kapak_sahne_v9 guclu acik3; kartlarin yazi disi zemini, medyan fark 2 olculdu 24 Eki) + fontlar.
Kural (Serdar 24 Eki):
  - kose etiketi "ASTROLOVE / A + B" -> "ASTROLOVEART / A & B" (cift adi ilana gore, "+" yok, marka AstroLoveArt)
  - kart baslik ve yazilarinda cumle sonu noktasi, "+", "=" yok (ondalik sayi, ornegin 29.7 cm, kalir)
  - "Fine art" ifadesi ve cercevesiz maket + "Frame not included" yazisi KALIR
  - sira 3 gorsel yazisi "AstroLoveArt"
Yontem: her satir kart_metin_degis.degistir ile (eski satirin font/punto/renk/taban olcumu, kutu duvarla silinir, yeni satir ayni
hizalama ile basilir). Font ailesi satir basina olcumle secilir (mont / gar / lato, en dusuk eslesme hatasi).
QC (kart basina PASS/FAIL):
  - her satirda olcum hatasi < 40 (17 Eki eski78 esigi); silinen kutuda yazi disi zemin duvara yakin (p99 <= 16)
  - degisiklik kutulari disinda piksel AYNI (kayipsiz ara goruntu); JPEG sonrasi kutu disi p99.9 <= 12, max <= 45 (eski78 esigi)
  - OCR (tesseract): kartta Art'siz "ASTROLOVE /" yok, "+" ve "=" yok, cumle sonu noktasi yok; yeni satirlar okunur
Cikti: OUT/NN_<id>.jpg (degisen kartlar, JPEG 95), OUT/ONCE_SONRA/NN.jpg (satir kutulari isaretli), OUT/RAPOR.json.
Kullanim: kart_nokta_marka.py --hedef-dir D --duvar duvar.png --fd FONTS --cift ARIES_VIRGO --out OUT [--kart 02,03]"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw
import PIL  # noqa: E402
if PIL.__version__ != "11.0.0" and os.environ.get("PILLOW_SERBEST") != "1":   # Serdar 24 Eki: yerel = Actions (requirements.txt)
    raise SystemExit(f"DUR: Pillow {PIL.__version__}; uretim ve test Actions ile ayni Pillow 11.0.0 ile kosar (glif yerlesimi farki)")

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kart_metin_degis as KM  # noqa: E402

ETIKET_KUTU = (130, 78, 1300, 142)   # 24 Eki: uzun ciftler (AQUARIUS + SAGITTARIUS) icin genis; y 78-142 arasinda baska yazi yok


def S(kutu, eski, yeni, hiza="sol", aile="oto", genis=0, agirlik=None, ara=None, parca=None):
    """ara=(x0, x1): kutunun x sinirlari her kartta eski satirin OLCULEN murekkebinden alinir (burc adina bagli satirlar; 24 Eki
    22 ilan TASMA bulgusu: sabit kutu pilot ARIES_VIRGO'ya gore, satir yeri/uzunlugu cifte gore degisiyor). parca=k: satirdaki
    k. parca (aralarinda > ARA_BOSLUK px bos sutun olan murekkep obekleri; kart 4 EMILY / JAMES), None: aradaki tum murekkep."""
    return dict(kutu=kutu, eski=eski, yeni=yeni, hiza=hiza, aile=aile, genis=genis, agirlik=agirlik, ara=ara, parca=parca)


ARA_BOSLUK, ARA_PAY = 30, 12   # olculu kutu: kelime arasi < 30 px (Montserrat/Garamond 37-57 pt), ogeler arasi >= 45 px


def olcu_kutu(M, op):
    """-> (kutu, hata). Eski satirin murekkep sutunlarini ara icinde olcer; kutu = secilen obek +- ARA_PAY."""
    x0, y0, x1, y1 = op["kutu"]; a0, a1 = op["ara"]
    sut = M[y0:y1, a0:a1].sum(0) >= 2
    obek, bas, son = [], None, None
    for i in np.flatnonzero(sut):
        if bas is not None and i - son <= ARA_BOSLUK:
            son = i
        else:
            if bas is not None:
                obek.append((bas, son))
            bas = son = i
    if bas is not None:
        obek.append((bas, son))
    if not obek:
        return None, "olculu kutu: ara icinde murekkep yok"
    if op["parca"] is not None:
        if op["parca"] >= len(obek):
            return None, f"olculu kutu: {len(obek)} parca var, {op['parca']}. istendi"
        b, e = obek[op["parca"]]
    else:
        b, e = obek[0][0], obek[-1][1]
    if b <= 1 or e >= a1 - a0 - 2:
        return None, f"TASMA, eski satir olcum araliginin kenarina degiyor (ara x {a0}-{a1})"
    return (int(a0 + b - ARA_PAY), y0, int(a0 + e + 1 + ARA_PAY), y1), None


def ozellik(a, b):
    """kart sira -> satir islemleri. a, b: burc adi (Aries, Virgo)."""
    A, B = a.upper(), b.upper()
    sol, sag = ("LEFT", "RIGHT") if A == B else (A, B)
    # galeri77_kur.py:7 etiket 03-14 'ASTROLOVE  /  A + B' (cift bosluk, Montserrat 500 37); kart02_duvar_kur.py:64 tek bosluk (Lato)
    et = S(ETIKET_KUTU, f"ASTROLOVE  /  {A} + {B}", f"ASTROLOVEART  /  {A} & {B}", aile="mont", agirlik=500)
    et2 = S(ETIKET_KUTU, f"ASTROLOVE / {A} + {B}", f"ASTROLOVEART / {A} & {B}")
    renk = [S((1090, 2068, 1912, 2120), "Poster color. Format selected separately.", "Poster color, format selected separately",
              "merkez")]
    return {
        2: [et2, S((135, 165, 965, 282), "Choose your format.", "Choose your format"),
            S((140, 322, 905, 384), "One design, two ways to enjoy it.", "One design, two ways to enjoy it"),
            # sol sutun uc satir birlikte yeniden yazilir (ayni ton; kart02_iki_sutun.py: Lato 38)
            S((640, 1526, 1400, 1569), "One print-ready JPG in your chosen color", "One print-ready JPG in your chosen color", "merkez",
              aile="lato"),
            S((640, 1572, 1400, 1614), "and size. 300 dpi. Delivered to your", "and size, 300 dpi, delivered to your", "merkez",
              aile="lato"),
            S((640, 1617, 1400, 1662), "Etsy order within 24 hours.", "Etsy order within 24 hours", "merkez", aile="lato"),
            S((1500, 1526, 2420, 1569), "Premium matte art paper, long-lasting inks.", "Premium matte art paper, long-lasting inks", "merkez"),
            S((1500, 1572, 2420, 1614), "Unframed, ready for your frame.", "Unframed, ready for your frame", "merkez"),
            S((1130, 1828, 1870, 1885), f"A personal gift for {a} and {b} couples.", f"A personal gift for {a} and {b} couples", "merkez",
              ara=(400, 2600))],
        3: [et, S((135, 192, 1580, 326), "Two signs. One shared symbol.", "Two signs, one shared symbol"),
            S((140, 330, 1520, 392), f"{a} and {b}, united in an original AstroLove design.",
              f"{a} and {b}, united in an original AstroLoveArt design", genis=200, ara=(100, 2600)),
            S((336, 772, 935, 820), "Your individual identities.", "Your individual identities"),
            S((336, 1252, 1140, 1308), "A design that brings you together.", "A design that brings you together"),
            S((340, 1782, 1055, 1838), "Personalized with your names.", "Personalized with your names")],
        4: [et, S((138, 192, 1790, 326), "Each name goes under its own sign.", "Each name goes under its own sign"),
            S((138, 330, 1130, 392), "Type each name in the field for its sign.", "Type each name in the field for its sign"),
            # ayni burclu ciftte kart 4 baska sablon: "EMILY = LEFT  JAMES = RIGHT" (24 Eki: ARIES_ARIES, AQUARIUS_AQUARIUS)
            S((428, 1744, 740, 1788), f"EMILY = {sol}", f"EMILY: {sol}", ara=(300, 2200), parca=0),
            S((755, 1744, 1100, 1788), f"JAMES = {sag}", f"JAMES: {sag}", ara=(300, 2200), parca=1),
            S((890, 1890, 2110, 1966), "Names print in capitals. Your message prints as you type it.",
              "Names print in capitals and your message prints as you type it", "merkez", genis=60),
            S((1190, 2004, 1810, 2038), "We send you a preview before we finalize your order.",
              "We send you a preview before we finalize your order", "merkez")],
        5: [et, S((135, 192, 1100, 327), "A gift for your story.", "A gift for your story"),
            S((140, 330, 2000, 392), "For anniversaries, engagements, weddings, Valentine’s Day and birthdays.",
              "For anniversaries, engagements, weddings, Valentine’s Day and birthdays"),
            S((890, 1950, 2110, 2014), "Your two names and your own message, in one shared symbol.",
              "Your two names and your own message, in one shared symbol", "merkez")],
        6: [et, S((135, 190, 1575, 300), "Find the right fit for your wall.", "Find the right fit for your wall"),
            S((140, 325, 1110, 390), "13 sizes, grouped by print proportions.", "13 sizes, grouped by print proportions"),
            S((1080, 1952, 1920, 1998), "Every size is available as a print and as a digital file.",
              "Every size is available as a print and as a digital file", "merkez")],
        7: [et, S((135, 192, 1520, 327), "Made for the room you share.", "Made for the room you share"),
            S((138, 330, 1540, 392), "A calm, personal piece for your bedroom or living room.",
              "A calm, personal piece for your bedroom or living room"),
            S((1210, 1884, 1790, 1950), "Shown in Champagne Ivory.", "Shown in Champagne Ivory", "merkez"),
            S((1248, 1971, 1756, 2010), "Five colors and thirteen sizes.", "Five colors and thirteen sizes", "merkez")],
        8: [et, S((135, 192, 1560, 327), "Deep Black, bold and modern.", "Deep Black, bold and modern"),
            S((138, 330, 1385, 392), "A modern look for a living room, hallway or office.", "A modern look for a living room, hallway or office"),
            S((1272, 1884, 1728, 1950), "Shown in Deep Black.", "Shown in Deep Black", "merkez"),
            S((1178, 1971, 1828, 2018), "Every color comes in all thirteen sizes.", "Every color comes in all thirteen sizes", "merkez")],
        9: [et, S((135, 192, 1375, 327), "Pure White, calm and airy.", "Pure White, calm and airy"),
            S((140, 330, 1305, 392), "Light and calm, for a dining room or entryway.", "Light and calm, for a dining room or entryway"),
            S((1270, 1884, 1730, 1936), "Shown in Pure White.", "Shown in Pure White", "merkez"),
            S((1112, 1971, 1892, 2020), "Prints ship unframed, ready for your frame.", "Prints ship unframed, ready for your frame", "merkez")],
        10: [et, S((135, 188, 1022, 312), "Look a little closer.", "Look a little closer"),
             S((138, 328, 1040, 391), "A close view of the original artwork.", "A close view of the original artwork"),
             S((805, 1964, 2198, 2028), "Printed gold effect. No metallic foil or raised surface.",
               "Printed gold effect, no metallic foil or raised surface", "merkez"),
             S((975, 2053, 2025, 2102), "Artwork enlargement, not a physical print photograph.",
               "Artwork enlargement, not a physical print photograph", "merkez")],
        11: [et, S((135, 192, 1435, 327), "Fine art, down to the paper.", "Fine art, down to the paper"),
             S((146, 330, 1075, 391), "Printed on premium matte art paper.", "Printed on premium matte art paper"),
             S((1356, 671, 2315, 728), "A smooth matte art paper with rich detail.", "A smooth matte art paper with rich detail"),
             S((1356, 1027, 2325, 1084), "A refined surface without a glossy coating.", "A refined surface without a glossy coating"),
             S((1356, 1385, 2310, 1458), "Deep, even color across the whole design.", "Deep, even color across the whole design"),
             S((1356, 1737, 2255, 1794), "Printed after you approve your preview.", "Printed after you approve your preview"),
             S((795, 1952, 2210, 1998), "Print option: an unframed fine art print. Gold tones are printed color, not metallic foil.",
               "Print option: an unframed fine art print with gold tones in printed color, not metallic foil", "merkez", genis=40)],
        12: [et, S((135, 192, 1392, 327), "Made for you, step by step.", "Made for you, step by step"),
             S((146, 331, 850, 391), "Every print is made to order.", "Every print is made to order"),
             S((334, 884, 866, 942), "24 hours of your order.", "24 hours of your order"),
             S((1789, 818, 2815, 876), "We print as soon as you approve. No reply in", "We print once you approve, or as shown if"),
             S((1789, 884, 2478, 942), "24 hours? We print as shown.", "there is no reply within 24 hours", genis=200),
             S((334, 1464, 680, 1522), "after approval.", "after approval"),
             S((1789, 1465, 2418, 1514), "size. US orders are tracked.", "size, and US orders are tracked", genis=100),
             S((910, 1894, 2090, 1948), "See the listing for the delivery estimate to your address.",
               "See the listing for the delivery estimate to your address", "merkez")],
        13: renk, 14: renk, 15: renk, 16: renk, 17: renk,
    }


def murekkep_maske(K, D, esik=40):
    return np.abs(np.asarray(K).astype(int) - np.asarray(D).astype(int)).max(2) > esik


def aile_sec(K, D, fd, op):
    if op["aile"] != "oto":
        return op["aile"], KM.olc(K, D, fd, op["kutu"], op["eski"], op["aile"])
    en = None
    for aile in ("mont", "gar", "lato"):
        try:
            o = KM.olc(K, D, fd, op["kutu"], op["eski"], aile)
        except Exception:   # noqa: BLE001
            continue
        if en is None or o["hata"] < en[1]["hata"]:
            en = (aile, o)
    return en


def nokta_sil(Y, Ka, Dk, kutu, hiza):
    """Yalniz cumle sonu noktasi duser: satir yeniden yazilmaz. Satir murekkebi alfa olarak (|K - D| renk yonune izdusum) duvar
    zemine yeniden bindirilir, en sagdaki nokta bileseni cikarilir; merkezli satir nokta genisliginin yarisi kadar saga kayar.
    Donus: rapor sozlugu; uygun nokta bileseni yoksa ValueError."""
    from scipy.ndimage import binary_dilation, label
    x0, y0, x1, y1 = kutu
    K_ = Ka[y0:y1, x0:x1]; D_ = Dk[y0:y1, x0:x1]
    v = (K_ - D_).astype(float)
    M = np.abs(v).max(2) > 40
    lab, n = label(M, structure=np.ones((3, 3)))
    bb = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(xs) >= 6:   # JPEG kirintisi (1-5 px) bilesen sayilmaz; kucuk puntoda nokta ~10-16 px
            bb.append((xs.min(), ys.min(), xs.max(), ys.max(), i, len(xs)))
    if len(bb) < 2:
        raise ValueError(f"bilesen {len(bb)}")
    M_tum = M                               # alfa icin TUM bilesenler (kucuk puntoda i noktasi 5 px; 24 Eki inceleme: "finalıze")
    M = np.isin(lab, [b[4] for b in bb])    # nokta adayi secimi icin kirintisiz
    ys_all, xs_all = np.nonzero(M)
    yuk = ys_all.max() - ys_all.min() + 1
    nk = max(bb, key=lambda b: b[0])
    digerleri = [b for b in bb if b[4] != nk[4]]
    sag_diger = max(b[2] for b in digerleri)
    w, h = nk[2] - nk[0] + 1, nk[3] - nk[1] + 1
    if not (w <= 0.35 * yuk and h <= 0.35 * yuk and nk[0] > sag_diger - 2 and abs(w - h) <= max(3, 0.5 * max(w, h))):
        raise ValueError(f"en sagdaki bilesen nokta degil (w {w} h {h} satir {yuk})")
    guc = np.abs(v).max(2)
    cekirdek = guc >= np.percentile(guc[M], 70)
    C = np.median(K_[cekirdek], 0)
    c = C - D_.reshape(-1, 3).mean(0)
    a = np.clip((v * c).sum(2) / max(float((c * c).sum()), 1.0), 0, 1)
    a[~binary_dilation(M_tum, iterations=3)] = 0
    nokta_m = binary_dilation(lab == nk[4], iterations=3)
    once = float(a[~nokta_m].sum())
    a[nokta_m] = 0
    if once <= 0 or abs(float(a.sum()) / once - 1) > 0.01:   # nokta disinda murekkep kaybi olmamali (alfa yeniden kurulumu)
        raise ValueError(f"nokta disi murekkep kaybi ({float(a.sum()) / max(once, 1):.3f})")
    dx = 0
    if hiza == "merkez":
        dx = int(round((nk[2] - sag_diger) / 2))
        a = np.roll(a, dx, axis=1); a[:, :dx] = 0
    yeni = D_ + a[..., None] * (C - D_)
    # bilesen kapisi (24 Eki inceleme, "finalıze"): yeniden kurulan satirda noktadan baska murekkep bileseni kaybolmamali
    say0 = sum(1 for i in range(1, n + 1) if (lab == i).sum() >= 3)
    lab1, n1 = label(np.abs(yeni - D_).max(2) > 40, structure=np.ones((3, 3)))
    say1 = sum(1 for i in range(1, n1 + 1) if (lab1 == i).sum() >= 3)
    if say1 < say0 - 1:
        raise ValueError(f"bilesen kaybi: ozgun {say0}, nokta silinince {say1} (beklenen {say0 - 1})")
    Y[y0:y1, x0:x1] = np.clip(np.round(yeni), 0, 255).astype(np.uint8)
    return dict(kip="nokta", nokta=(int(nk[0] + x0), int(nk[1] + y0), int(w), int(h)), kayma=dx, renk=[int(t) for t in C],
                bilesen=(say0, say1))


def panel_ort(img):
    """Kart OCR'indan once koyu poster/onizleme panellerini beyazla ortere (24 Eki AQUARIUS_LIBRA: panel icindeki altin el yazisi
    'lt Reozn VU a Fhe Baan.' okundu, yanlis 'cumle sonu noktasi'). Duzenlenen tum satirlar duvar zemininde (ozellik kutulari)."""
    from scipy.ndimage import binary_closing, label
    L = np.asarray(img.convert("L"))
    m, n = label(binary_closing(L < 70, iterations=8))
    Y = np.asarray(img.convert("RGB")).copy()
    for k in range(1, n + 1):
        ys, xs = np.nonzero(m == k)
        if ys.size > 100_000:
            Y[ys.min():ys.max() + 1, xs.min():xs.max() + 1] = 255
    return Image.fromarray(Y)


PANEL_KART = {4}   # Serdar 24 Eki: panel ortme yalniz kart 4'te (kart 9'da ortme OCR'i bozdu: "...WALL ART Bame te.", ARIES_LIBRA olcumu)


def ocr(img, panel=False):
    b = io.BytesIO(); (panel_ort(img) if panel else img).save(b, "PNG")
    r = subprocess.run(["tesseract", "-", "-", "--psm", "3"], input=b.getvalue(), capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def kutle(A, Dc, renk):
    """murekkep kutlesi: (A - D) farkinin yazi rengi yonune izdusumu (0-1), toplam. A, Dc: ayni bolge (numpy)."""
    v = A.astype(float) - Dc.astype(float)
    c = np.asarray(renk, float) - Dc.reshape(-1, 3).mean(0)
    return float(np.clip((v * c).sum(2) / max(float((c * c).sum()), 1.0), 0, 1).sum())


def agirlik_sec(K, D, fd, kutu, eski, aile, renk):
    """24 Eki: olcum hatasi agirligi ayirt etmiyor (300/600 secti). Agirlik = ozgun satirin murekkep kutlesine en yakin cizim."""
    from PIL import ImageDraw as _D
    Ka = np.asarray(K); Dk = np.asarray(D)
    x0, y0, x1, y1 = kutu
    m0 = kutle(Ka[y0:y1, x0:x1], Dk[y0:y1, x0:x1], renk)
    en = None
    for w in KM.AILE[aile][1]:
        o = KM.olc(K, D, fd, kutu, eski, aile, agirliklar=(w,))
        f = KM._font(fd, aile, o["punto"], w); g0, _ = KM._gen(f, eski, o["iz"])
        im = D.crop(kutu).copy()
        KM._ciz(_D.Draw(im), (o["murekkep"][0] - g0 - x0, o["taban"] - y0), eski, f, renk, o["iz"])
        m = kutle(np.asarray(im), Dk[y0:y1, x0:x1], renk)
        oran = m / max(m0, 1.0)
        if en is None or abs(oran - 1) < abs(en[1] - 1):
            en = (w, oran, o)
    return en


def renk_sec(K, D, fd, kutu, eski, aile, w, renk):
    from PIL import ImageDraw as _D
    Ka = np.asarray(K).astype(int); x0, y0, x1, y1 = kutu
    o = KM.olc(K, D, fd, kutu, eski, aile, agirliklar=(w,))
    f = KM._font(fd, aile, o["punto"], w); g0, _ = KM._gen(f, eski, o["iz"])
    zem = np.asarray(D.crop(kutu)).reshape(-1, 3).mean(0)
    en = None
    for t in (0.0, 0.1, 0.2, 0.3, 0.4):
        r_ = tuple(int(round(c + t * (z - c))) for c, z in zip(renk, zem))
        im = D.crop(kutu).copy(); KM._ciz(_D.Draw(im), (o["murekkep"][0] - g0 - x0, o["taban"] - y0), eski, f, r_, o["iz"])
        e = float(np.abs(np.asarray(im).astype(int) - Ka[y0:y1, x0:x1]).mean())
        if en is None or e < en[0]:
            en = (e, r_)
    return en[1]


def ocr_satir(img):
    # gri ton (24 Eki ARIES_LEO: RGB kirpimda 'JAMES: LEO' -> 'SAMES- EE', gri tonda dogru okunuyor)
    b = io.BytesIO(); img.convert("L").save(b, "PNG")
    r = subprocess.run(["tesseract", "-", "-", "--psm", "7"], input=b.getvalue(), capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def kart_isle(yol, D, fd, ops, out, sira):
    K = Image.open(yol).convert("RGB")
    M = murekkep_maske(K, D)
    Dk = np.asarray(D).astype(int); Ka = np.asarray(K).astype(int)
    isler, rapor, hata, noktalar = [], [], [], []
    olculu = []
    for op in ops:
        if op.get("ara"):
            kutu, h = olcu_kutu(M, op)
            if h:
                hata.append(f"r{sira} '{op['eski'][:30]}': {h}"); continue
            op = dict(op, kutu=kutu)
        olculu.append(op)
    ops = olculu
    for op in ops:   # tasma kapisi (Serdar 24 Eki: uzun burc adlari): eski satirin murekkebi kutunun sol/sag kenarina degiyorsa
        g = op["genis"]; x0, y0, x1, y1 = op["kutu"]   # satir kutuya sigmiyor; olcum ve silme yanlis olur -> FAIL
        kx0, kx1 = (x0 - g // 2, x1 + g // 2) if op["hiza"] == "merkez" else (x0, x1 + g)
        alt_ = M[y0:y1, max(0, kx0):min(K.width, kx1)]
        if alt_.shape[1] > 4 and (alt_[:, :2].any() or alt_[:, -2:].any()):
            hata.append(f"r{sira} '{op['eski'][:30]}': TASMA, eski satir kutunun kenarina degiyor (kutu x {kx0}-{kx1})")
    if hata:
        return None, [], hata
    for op in ops:
        if op["eski"].endswith(".") and op["yeni"] == op["eski"][:-1] and op["aile"] == "oto":
            noktalar.append(op); continue
        x0, y0, x1, y1 = op["kutu"]
        g = op["genis"]
        if op["hiza"] == "merkez":
            kutu = (max(0, x0 - g // 2), y0, min(K.width, x1 + g // 2), y1)
        else:
            kutu = (x0, y0, min(K.width, x1 + g), y1)
        # genisletilen alanda baska murekkep olmamali (yeni metin yazinin ustune binmesin)
        ek = np.zeros_like(M); ek[kutu[1]:kutu[3], kutu[0]:kutu[2]] = True; ek[y0:y1, x0:x1] = False
        if (M & ek).sum() > 20:
            hata.append(f"r{sira} '{op['eski'][:30]}': genisletme alaninda murekkep {(M & ek).sum()} px")
        try:
            aile, o = aile_sec(K, D, fd, op)
        except Exception as e:   # noqa: BLE001
            hata.append(f"r{sira} '{op['eski'][:30]}': olcum hatasi {e}"); continue
        mk = o["murekkep"]
        # silinen kutuda yazi disi zemin duvara yakin mi (duvarla silmek iz birakmasin)
        sub = np.abs(Ka[kutu[1]:kutu[3], kutu[0]:kutu[2]] - Dk[kutu[1]:kutu[3], kutu[0]:kutu[2]]).max(2)
        msub = M[kutu[1]:kutu[3], kutu[0]:kutu[2]]
        from scipy.ndimage import binary_dilation
        zem = sub[~binary_dilation(msub, iterations=6)]
        z99 = float(np.percentile(zem, 99)) if zem.size else 0.0
        r = dict(sira=sira, eski=op["eski"], yeni=op["yeni"], aile=aile, hata=o["hata"], punto=o["punto"], agirlik=o["agirlik"],
                 murekkep=mk, kutu=kutu, zemin_p99=round(z99, 1))
        if o["hata"] >= 40:
            hata.append(f"r{sira} '{op['eski'][:30]}': olcum hatasi {o['hata']} >= 40 (aile {aile})")
        if z99 > 16:
            hata.append(f"r{sira} '{op['eski'][:30]}': kutu zemini duvardan farkli (p99 {z99:.1f} > 16)")
        # renk: satirin cekirdek murekkep pikselleri (en koyu %3 kalin gosteriyordu, 24 Eki kart 02)
        x0_, y0_, x1_, y1_ = mk
        v_ = np.abs(Ka[y0_:y1_, x0_:x1_] - Dk[y0_:y1_, x0_:x1_]).max(2)
        cek = v_ >= np.percentile(v_[v_ > 40], 70) if (v_ > 40).any() else v_ > 40
        renk = tuple(int(t) for t in np.median(Ka[y0_:y1_, x0_:x1_][cek], 0)) if cek.any() else None
        r["renk"] = renk
        agr = o["agirlik"]
        if op.get("agirlik"):   # belgeli agirlik (galeri77_kur.py:7 etiket Montserrat 500)
            agr = op["agirlik"]; o2 = KM.olc(K, D, fd, kutu, op["eski"], aile, agirliklar=(agr,))
            r.update(agirlik=agr, punto=o2["punto"], hata=o2["hata"])
        elif renk and len(KM.AILE[aile][1]) > 1:
            agr, oran, o2 = agirlik_sec(K, D, fd, kutu, op["eski"], aile, renk)
            r.update(agirlik=agr, kutle_orani=round(oran, 3), punto=o2["punto"], hata=o2["hata"])
            if abs(oran - 1) > 0.12:
                hata.append(f"r{sira} '{op['eski'][:30]}': murekkep kutlesi tutmuyor (oran {oran:.2f}, agirlik {agr})")
        if renk and op.get("agirlik"):   # yalniz belgeli etiket: cekirdek renk ile zemin arasi, ESKI satiri en iyi tekrar ureten
            # (24 Eki: etikette cekirdek renk koyu kaliyordu; govde satirlarinda bu secim soluk yapiyordu, kullanilmaz)
            renk = renk_sec(K, D, fd, kutu, op["eski"], aile, agr, renk); r["renk"] = renk
        rapor.append(r)
        isler.append(dict(kutu=kutu, eski=op["eski"], yeni=op["yeni"], aile=aile, hiza=op["hiza"], agirliklar=(agr,), ara=op.get("ara"),
                          renk=renk))
    if hata:
        return None, rapor, hata
    Y0 = np.asarray(K).copy()
    for op in noktalar:
        try:
            r = nokta_sil(Y0, Ka, Dk, op["kutu"], op["hiza"])
        except ValueError as e:
            hata.append(f"r{sira} '{op['eski'][:30]}': nokta silinemedi ({e})"); continue
        r.update(sira=sira, eski=op["eski"], yeni=op["yeni"], kutu=op["kutu"]); rapor.append(r)
        isler_k = dict(kutu=op["kutu"], eski=op["eski"], yeni=op["yeni"], aile=None, hiza=op["hiza"], kip="nokta", ara=op.get("ara"))
        isler.append(isler_k)
    if hata:
        return None, rapor, hata
    yaz = [i for i in isler if i.get("kip") != "nokta"]
    try:
        Y, _ = KM.degistir(Image.fromarray(Y0), D, fd, yaz) if yaz else (Image.fromarray(Y0), [])
    except SystemExit as e:
        return None, rapor, [f"r{sira}: {e}"]
    # kutu disi ayni (kayipsiz), JPEG sonrasi esik
    dis = np.ones((K.height, K.width), bool)
    for i in isler:
        k = i["kutu"]; dis[k[1]:k[3], k[0]:k[2]] = False
    fark0 = np.abs(np.asarray(Y).astype(int) - Ka).max(2)[dis]
    if fark0.max() != 0:
        hata.append(f"r{sira}: kutu disinda piksel degisti (max {fark0.max()})")
    ad = os.path.basename(yol)
    os.makedirs(os.path.join(out, "_ARA"), exist_ok=True)   # kapilardan gecene kadar ara klasorde (FAIL kart yuklemeye gitmesin)
    p = os.path.join(out, "_ARA", ad); Y.save(p, quality=95, subsampling=0)
    J = np.asarray(Image.open(p).convert("RGB")).astype(int)
    d = np.abs(J - Ka).max(2)[dis]
    p999, mx = float(np.percentile(d, 99.9)), int(d.max())
    if p999 > 12 or mx > 45:
        hata.append(f"r{sira}: JPEG sonrasi kutu disi fark p99.9 {p999:.1f} / max {mx} (esik 12 / 45)")
    Yj = Image.open(p).convert("RGB")
    t = ocr(Yj, panel=sira in PANEL_KART)
    tt = " ".join(t.split())
    ocr_hata = []
    if re.search(r"ASTROLOVE\s*/", tt):
        ocr_hata.append("Art'siz ASTROLOVE /")
    for sat in t.splitlines():   # yazi satiri: en az 3 harf sozcugu, rakam yok (boy etiketleri OCR'da x -> + / = okunuyor)
        s_ = sat.strip()
        if len(re.findall(r"[A-Za-z]{2,}", s_)) < 3 or re.search(r"\d", s_):
            continue
        if s_.endswith("."):
            ocr_hata.append(f"cumle sonu noktasi: {s_[-40:]!r}")
        if "+" in s_ or "=" in s_:
            ocr_hata.append(f"'+' ya da '=': {s_[-40:]!r}")
    import difflib
    for i in isler:   # her degisen satir kendi kutusunda okunur; ozgun satir da okunamiyorsa (acik zemin) atlanir
        k = i["kutu"]
        def oku(im):
            return " ".join(ocr_satir(im.crop(k)).split())
        if i.get("ara"):   # burca bagli satir: kaynak kartta beklenen eski metin gercekten var mi (24 Eki: ARIES_ARIES kart 4
            # "EMILY = LEFT" iken "EMILY = ARIES" varsayildi, olcum/kutle kapisi farki gormedi, yanlis metin PASS oldu)
            eo_ = difflib.SequenceMatcher(None, oku(K).lower(), i["eski"].lower()).ratio()
            if eo_ < 0.8:
                ocr_hata.append(f"eski satir beklenen metin degil ({eo_:.2f}): {i['eski'][:40]!r} -> {oku(K)[:40]!r}")
        yo = oku(Yj); bnz = difflib.SequenceMatcher(None, yo.lower(), i["yeni"].lower()).ratio()
        i["ocr"] = yo; i["ocr_benzerlik"] = round(bnz, 2)
        if bnz < 0.8:
            eo = difflib.SequenceMatcher(None, oku(K).lower(), i["eski"].lower()).ratio()
            if eo >= 0.8:
                ocr_hata.append(f"yeni satir okunamadi ({bnz:.2f}): {i['yeni'][:40]!r} -> {yo[:40]!r}")
            else:
                i["ocr_atlandi"] = f"ozgun satir da okunamiyor ({eo:.2f})"
        if yo.endswith(".") or "+" in yo or "=" in yo:
            ocr_hata.append(f"satir sonu nokta / + / =: {yo[-40:]!r}")
    hata += [f"r{sira} OCR: {x}" for x in ocr_hata]
    # once/sonra
    os.makedirs(os.path.join(out, "ONCE_SONRA"), exist_ok=True)
    w = 1500; h = round(K.height * w / K.width)
    O = Image.new("RGB", (2 * w + 30, h), "white")
    a_ = K.copy(); b_ = Image.open(p).convert("RGB")
    for im in (a_, b_):
        dr = ImageDraw.Draw(im)
        for i in isler:
            dr.rectangle(i["kutu"], outline=(220, 30, 30), width=3)
    O.paste(a_.resize((w, h)), (0, 0)); O.paste(b_.resize((w, h)), (w + 30, 0))
    O.save(os.path.join(out, "ONCE_SONRA", f"{sira:02d}.jpg"), quality=85)
    for r in rapor:
        r.update(jpeg_p999=round(p999, 1), jpeg_max=mx)
    if not hata:   # yalniz PASS kart cikti kokune (galeri23-duzelt bunu hedefe kopyalar); FAIL kart FAIL/ altinda kalir
        son = os.path.join(out, ad); os.replace(p, son); p = son
    else:
        os.makedirs(os.path.join(out, "FAIL"), exist_ok=True)
        son = os.path.join(out, "FAIL", ad); os.replace(p, son); p = None
    return p, rapor, hata


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hedef-dir", required=True)
    ap.add_argument("--duvar", required=True)
    ap.add_argument("--fd", required=True)
    ap.add_argument("--cift", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--kart", default="", help="yalniz bu siralar (virgullu); bos = hepsi")
    ap.add_argument("--manifest", default="", help="hedef manifest: dosya NN_<manifestteki id>.jpg secilir (24 Eki: YEDEK klasorunde "
                    "ayni siranin eski surumleri de var, kosu 40064765818)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    b1, b2 = [x.capitalize() for x in a.cift.split("_")]
    oz = ozellik(b1, b2)
    secim = {int(x) for x in a.kart.split(",") if x} or set(oz)
    D = Image.open(a.duvar).convert("RGB")
    if a.manifest:
        man = json.load(open(a.manifest, encoding="utf-8"))
        dosya = {int(g["rank"]): os.path.join(a.hedef_dir, f"{int(g['rank']):02d}_{g['listing_image_id']}.jpg") for g in man["galeri"]}
    else:
        dosya = {}
        for f in sorted(os.listdir(a.hedef_dir)):
            if re.match(r"^\d\d_\d+\.jpg$", f):
                n = int(f.split("_", 1)[0])
                if n in dosya:
                    raise SystemExit(f"DUR: sira {n} icin birden cok dosya ({os.path.basename(dosya[n])}, {f}); --manifest verin")
                dosya[n] = os.path.join(a.hedef_dir, f)
    R, tum_hata = {}, []
    for sira in sorted(secim):
        if sira not in dosya or not os.path.exists(dosya[sira]):
            tum_hata.append(f"r{sira}: hedef dosya yok ({os.path.basename(dosya.get(sira, '?'))})"); continue
        if D.size != Image.open(dosya[sira]).size:
            tum_hata.append(f"r{sira}: boyut duvarla ayni degil"); continue
        p, rapor, hata = kart_isle(dosya[sira], D, a.fd, oz[sira], a.out, sira)
        R[sira] = dict(dosya=os.path.basename(dosya[sira]), cikti=p and os.path.basename(p), satirlar=rapor, hata=hata,
                       sonuc="FAIL" if hata else "PASS")
        tum_hata += hata
        print(f"r{sira:02d} {'FAIL' if hata else 'PASS'} satir {len(rapor)} | " + (" ; ".join(hata) if hata else
              " ".join(f"{x['aile']}:{x['hata']}" if x.get('kip') != 'nokta' else f"nokta:{x['kayma']}" for x in rapor)), flush=True)
    ozet = dict(cift=a.cift, kart=len(R), pass_=sum(v["sonuc"] == "PASS" for v in R.values()), hata=tum_hata)
    with open(os.path.join(a.out, "RAPOR.json"), "w", encoding="utf-8") as f:
        json.dump(dict(ozet=ozet, kartlar=R), f, ensure_ascii=False, indent=1)
    print("KART_NOKTA_MARKA", json.dumps(ozet, ensure_ascii=False)[:600], flush=True)
    sys.exit(0 if not tum_hata else 1)


if __name__ == "__main__":
    main()
