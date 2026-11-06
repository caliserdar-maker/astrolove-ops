#!/usr/bin/env python3
"""Ornament galeri kartlari 2-6 ORNEK (CANCER_LIBRA). Canli kart sablonu kart_sablon.py + yd_kart_ornek.py (main, AYNEN; SADE stil
#F5F0E7 / #2B2220, Cormorant 170, Manrope 68/64/58, 3000x2250). Metinler ORNAMENT_GALERI_PLAN v2 bolum 2 (D1 evet, D2 stil adlari).
Ornament gorselleri kapak kompozitlerinden kesit (ornament_kes.py; urun pikselleri aynen). ETSY YOK."""
import sys, json, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kart_sablon as T, yd_kart_ornek as K
from ornament_kes import kes
from PIL import ImageDraw
import os
OUT = Path(os.environ.get("ORN_OUT", str(Path(__file__).resolve().parent / "out"))); OUT.mkdir(parents=True, exist_ok=True)
KAPAK_DIR = Path(os.environ["ORN_KAPAK_DIR"])          # <CIFT>_STIL_<RUBY|SAPPHIRE|EMERALD|SADE|FILDISI>.jpg (+ .json), kapak motoru ciktisi
SEMBOL_DIR = Path(os.environ["ORN_SEMBOL_DIR"])        # <CIFT>/sol.png, sag.png, ana.png (dal kupa-printful-sonuc kupa_uretim/sembol)
CIFT = sys.argv[1] if len(sys.argv) > 1 else "CANCER_LIBRA"
A, B = [x.capitalize() for x in CIFT.split("_")]
AYNI = A == B
STIL = [("Ruby", "RUBY"), ("Sapphire", "SAPPHIRE"), ("Emerald", "EMERALD"), ("White", "SADE"), ("Ivory", "FILDISI")]
KAY = lambda k: KAPAK_DIR / f"{CIFT}_STIL_{k}.jpg"
kesit = {ad: kes(KAY(k), ip_ust_pay=230) for ad, k in STIL}
kucuk = {ad: kes(KAY(k), ip_ust_pay=110) for ad, k in STIL}
YASAK = re.compile(r"[+=‐-―−]|(?<!\d)\.(?!\d)")       # nokta (ondalik haric), arti, esittir, tire bicimleri
YASAK_SOZ = re.compile(r"premium|long.lasting|metallic|foil|printful|christmas|ready to hang|real size", re.I)
rap = {}
def kaydet(ad, im, o, beklenen):
    yaz = [t for t in K.YAZILAR]
    for t in yaz:
        if YASAK.search(t) or YASAK_SOZ.search(t):
            raise SystemExit(f"DUR: {ad} yasak karakter/soz: {t!r}")
    if yaz != beklenen:
        raise SystemExit(f"DUR: {ad} metin kapisi: {yaz} != {beklenen}")
    im.save(OUT / f"ORN_{CIFT}_{ad}.jpg", quality=95, subsampling=0)
    rap[ad] = dict(satirlar=yaz, yerlesim=o.get("yerlesim"))
    K.YAZILAR.clear(); K.SATIRLAR.clear(); K.KUTULAR.clear()

# K02 sembol
alt2 = "Personalized with your two names and your date"
ab2 = f"Two {A} signs joined in an original AstroLoveArt design" if AYNI else f"{A} and {B} joined in an original AstroLoveArt design"
im, o, _, _ = T.sembol_kart(A, B, SEMBOL_DIR / CIFT, alt2, ab2)
kaydet("K02_SEMBOL", im, o, ["Two Signs, One Shared Symbol", ab2, A, B, alt2])

# K03 kisisellestirme
N1, N2 = ("First Name", "Second Name") if AYNI else (f"Name for {A}", f"Name for {B}")
b3 = [(None, [N1, N2], "Letters A to Z only, printed in capitals"), (None, ["Your Date"], "For example JUNE 14, 2025")]
alt3 = "Please check your spelling before you order"
im, o, _ = T.yan_kart("Your Names, Your Date", [kesit["Ruby"]], b3, alt3)
kaydet("K03_KISISEL", im, o, ["Your Names, Your Date", N1, N2, "Letters A to Z only, printed in capitals",
                             "Your Date", "For example JUNE 14, 2025", alt3])

# K04 boyut ve detay (alt not yok: plan bolum 2, yeni soz uydurulmaz)
b4 = [(None, ["Round Ceramic"], "2.99 in (7.6 cm) across, 0.1 in (2.5 mm) thick"),
      (None, ["Both Sides"], "The same design on both sides, glossy finish"),
      (None, ["String Included"], "Gold-colored string")]
im, o, _ = T.yan_kart("Size & Details", [kesit["Sapphire"]], b4, "")
# alt not yok (Serdar 6 Kas "a"): baslik alti icerik, alt notun bos biraktigi alanin yarisi kadar asagi (alan + not dikeyde ortali)
from PIL import Image as _I
kay_ = round((K.NOT_Y + K.NOT["boy"] - K.ALAN[1]) / 2); ust_ = round(K.BASLIK_Y + K.BASLIK["boy"] + 60)
icerik = im.crop((0, ust_, im.width, im.height - kay_)); im.paste(_I.new("RGB", (im.width, kay_), K.ZEMIN), (0, ust_)); im.paste(icerik, (0, ust_ + kay_))
o["dikey_kaydirma_px"] = kay_
bek4 = ["Size & Details"]
for _, e, t in b4:
    bek4 += e + K.sar_d(K.METIN, t, T.GEN_KISISEL)
kaydet("K04_BOYUT", im, o, bek4 + [""])

# K05 surec (D1 evet)
b5 = [("01", ["Your Preview"], "For every order, we send a preview of your ornament via Etsy Messages"),
      ("02", ["Your Approval"], "We make your ornament once you approve the preview"),
      ("03", ["Shipped to You"], "We print your ornament and ship it to you")]
alt5 = "Original zodiac fusion symbols designed by AstroLoveArt"
im, o, _ = T.yan_kart("Made for You, Step by Step", [kesit["Emerald"]], b5, alt5, surec=True)
bek5 = ["Made for You, Step by Step"]
gen5 = o["metin_sutunu"]
for n, e, t in b5:
    bek5 += [n] + e + K.sar_d(K.METIN, t, gen5)
kaydet("K05_SUREC", im, o, bek5 + [alt5])

# K06 genel bakis
alt6 = "Every style printed on both sides"
im, o, _ = T.secim_kart("Choose Your Style", [(ad, kucuk[ad]) for ad, _ in STIL], alt6)
kaydet("K06_STIL", im, o, ["Choose Your Style"] + [ad for ad, _ in STIL] + [alt6])
(OUT / f"RAPOR_{CIFT}.json").write_text(json.dumps(rap, indent=1, ensure_ascii=False))
print("PASS", list(rap))
