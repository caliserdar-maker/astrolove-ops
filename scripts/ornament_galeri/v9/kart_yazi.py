# kart_yazi.py  (7 Kas) - G1: kart arka plani AI + urun kodla (set_yerlestir.py), yazi kodla.
# Metinler birebir: /tmp/opsb/scripts/ornament_galeri/kart/ornament_kart.py (K02 37-40, K03 43-48, K04 kaynak galeri kart 4, K05 66-69)
# Tipografi: yd_kart_ornek.py:138-143 (baslik Cormorant 500 170, etiket Manrope 600 68, metin Manrope 400 64, not Manrope 400 58, #2B2220)
# kullanim: python kart_yazi.py giris.jpg cikis.jpg K02|K03|K04|K05
import sys, os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

GIRIS, CIKIS, KART = sys.argv[1], sys.argv[2], sys.argv[3]
FD = os.environ.get("FONT_DIR", str(__import__("pathlib").Path(__file__).resolve().parents[2] / "kapak78" / "yd_kart" / "fonts")) + "/"
RENK = (43, 34, 32)
A, B = os.environ.get("A", "Cancer"), os.environ.get("B", "Libra")   # 8 Kas v9: cift burc adlari (ornament_kart.py:17 AYNI kurali)
AYNI = A == B
NB = " "                            # bolunmez bosluk (birim ayrilmasin)


def font(dosya, boy, agirlik):
    f = ImageFont.truetype(FD + dosya, boy)
    f.set_variation_by_axes([agirlik])
    return f


BAS, ETK, GOV, NOT = font("CormorantGaramond.ttf", 170, 500), font("Manrope.ttf", 68, 600), font("Manrope.ttf", 64, 400), font("Manrope.ttf", 58, 400)

# (baslik, [(etiketler, metin)], alt not)
METIN = {
    "K02": ("Two Signs, One Shared Symbol",
            [([], f"Two {A} signs joined in an original AstroLoveArt design" if AYNI else f"{A} and {B} joined in an original AstroLoveArt design")],
            "Personalized with your two names and your date"),
    "K03": ("Your Names, Your Date",
            [((["First Name", "Second Name"] if AYNI else [f"Name for {A}", f"Name for {B}"]), "Letters A to Z only, printed in capitals"),
             (["Your Date"], "For example JUNE 14, 2025")],
            "Please check your spelling before you order"),
    "K04": ("Size & Details",
            [(["Round Ceramic"], f"2.99{NB}in{NB}(7.6{NB}cm){NB}across, 0.1{NB}in{NB}(2.5{NB}mm){NB}thick"),
             (["Both Sides"], "The same design on both sides, glossy finish"),
             (["String Included"], "Gold-colored string")],
            None),
    "K05": ("Made for You, Step by Step",
            [(["01  Your Preview"], "For every order, we send a preview of your ornament via Etsy Messages"),
             (["02  Your Approval"], "We make your ornament once you approve the preview"),
             (["03  Shipped to You"], "We print your ornament and ship it to you")],
            "Original zodiac fusion symbols designed by AstroLoveArt"),
}

img = Image.open(GIRIS).convert("RGB")
W, H = img.size
g = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2GRAY).astype(np.float32)
# yazi alani: urun ve sahne nesnelerinin sagi. Nesne sinirini olc (yerel std), 120 px pay birak.
std = np.sqrt(np.maximum(cv2.blur(g * g, (41, 41)) - cv2.blur(g, (41, 41)) ** 2, 0))
dolu = std > 9
if os.environ.get("NESNE") == "renk":           # dokulu ketende (K05 kutusuz zemin) nesne = keten renginden belirgin fark
    _bl = cv2.GaussianBlur(np.asarray(img).astype(np.float32), (0, 0), 6)
    _ref = np.median(_bl[:, int(0.75 * W):].reshape(-1, 3), 0)
    dolu = np.linalg.norm(_bl - _ref, axis=2) > 28
sutun = dolu[int(0.08 * H):int(0.92 * H)].mean(0)
sag_nesne = int(np.max(np.where(sutun > 0.01)[0][np.where(sutun > 0.01)[0] < 0.62 * W])) if (sutun[: int(0.62 * W)] > 0.01).any() else 0
X0 = max(1450, sag_nesne + 120)
GEN = W - 210 - X0                       # sag bosluk 210 px (yd_kart_ornek.py:145)
assert GEN >= 800, (X0, GEN)                # dengeli kirma ile 800 px yeterli


def _acgozlu(metin, f, gen):
    sat, cur = [], ""
    for k in metin.split(" "):
        dene = (cur + " " + k).strip()
        if f.getlength(dene) <= gen or not cur:
            cur = dene
        else:
            sat.append(cur); cur = k
    sat.append(cur)
    return sat


def sar(metin, f, gen=None):
    # inceleme t2-16: dengeli kirma (yetim kelime yok): ayni satir sayisini veren en dar genislik
    gen = gen or GEN
    n = len(_acgozlu(metin, f, gen))
    if n == 1:
        return [metin]
    lo, hi = 1, gen
    while hi - lo > 2:
        m = (lo + hi) // 2
        if len(_acgozlu(metin, f, m)) <= n:
            hi = m
        else:
            lo = m
    sat = _acgozlu(metin, f, hi)
    assert max(f.getlength(x) for x in sat) <= gen
    return sat


bas, bloklar, alt = METIN[KART]
bas_s = sar(bas, BAS, W - 110 - X0)          # baslik: sag bosluk 110 px (iki satirda kalsin); govde 210 px
plan = []                                   # (font, metin, satir_yuksekligi, sonra_bosluk)
for s in bas_s:
    plan.append((BAS, s, 170 * 1.15, 0))
plan[-1] = plan[-1][:3] + (80,)
for i, (etk, met) in enumerate(bloklar):
    for e in etk:
        plan.append((ETK, e, 68 * 1.2 + 6, 0))
    for s in sar(met, GOV):
        plan.append((GOV, s, 64 * 1.32, 0))
    plan[-1] = plan[-1][:3] + (64,)
if alt:
    plan[-1] = plan[-1][:3] + (90,)
    for s in sar(alt, NOT):
        plan.append((NOT, s, 58 * 1.2, 0))
yuk = sum(p[2] + p[3] for p in plan) - plan[-1][3]
y = (H - yuk) / 2
assert y > 90, y
d = ImageDraw.Draw(img)
kutu = [X0, int(y), X0, int(y + yuk)]
for f, s, sy, ek in plan:
    d.text((X0, y), s, font=f, fill=RENK)
    kutu[2] = max(kutu[2], int(X0 + f.getlength(s)))
    y += sy + ek
assert kutu[2] <= W - 110
# kontrol: yazi kutusu alti AI'da bos keten mi
alan = dolu[kutu[1] - 30:kutu[3] + 30, kutu[0] - 40:kutu[2] + 40].mean()
img.save(CIKIS, quality=95, subsampling=0)
print(dict(kart=KART, X0=X0, sag_nesne=sag_nesne, genislik=GEN, kutu=kutu, dolu_oran=round(float(alan), 4), satir=len(plan)))
