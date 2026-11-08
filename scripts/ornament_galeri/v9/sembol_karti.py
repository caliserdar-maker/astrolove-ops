#!/usr/bin/env python3
"""Ornament "Two Signs, One Shared Symbol" karti, yeni set (Serdar 8 Kas): yayindaki W02 kartinin duzeni (kart_sablon.sembol_kart AYNEN:
baslik, alt baslik, iki burc + adlari, birlesim cizgisi, ortak sembol, alt not), arka plan yeni setin keteni (AI, bos), uc sembol ve
birlesim cizgisi ALTIN DOKU ("3 sembol de gold doku olsun", "birlesim cizgisi de altin doku olsun").
Altin kaynaklar (hazir, yeni doku): burclar POSTER78_CHATGPT_7200x10800 ayni burc posterlerinden kodla kesilmis <burc>_yeni_gold.png
(poster_burc.py, Drive TEMP/ORNAMENT_POSTER_BURC/20261108_0612_42453767433), ortak sembol Drive ANA_SEMBOL78_KATMAN <CIFT>_ana.png (aynen).
Duzen kapilari: once orijinal tuval + maskelerle (kupa_uretim/sembol/<CIFT>) kart_sablon kapilari (baglac, yerlesim) kosulur; sonra ayni
geometriyle altin + keten cizilir.
kullanim: python sembol_karti.py CIFT zemin.png maske_dizini altin_dizini cikis.jpg
  altin_dizini: <burc>_yeni_gold.png (kucuk harf) ve <CIFT>_ana.png
"""
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KART = Path(os.environ.get("KART_DIR", Path(__file__).resolve().parents[1] / "kart"))
sys.path.insert(0, str(KART))
import kart_sablon as T            # noqa: E402
import yd_kart_ornek as K          # noqa: E402

CIFT, ZEMIN, MASKE, ALTIN, CIKIS = sys.argv[1:6]
a_, b_ = CIFT.split("_")
A, B = a_.capitalize(), b_.capitalize()
AYNI = A == B
ALT = "Personalized with your two names and your date"
AB = f"Two {A} signs joined in an original AstroLoveArt design" if AYNI else f"{A} and {B} joined in an original AstroLoveArt design"
W, H = T.W, T.H

# 1) duzen + kapilar: orijinal tuval ve maskelerle (yayindaki kartla ayni kod yolu)
im0, o0, _, _ = T.sembol_kart(A, B, Path(MASKE) / CIFT, ALT, AB)
yaz0 = list(K.YAZILAR)
K.YAZILAR.clear(); K.SATIRLAR.clear(); K.KUTULAR.clear()

# 2) altin + keten
zem = Image.open(ZEMIN).convert("RGB")
if os.environ.get("ZEMIN_REF"):    # Serdar 8 Kas: arka plan setteki diger kartlarla (K05 keteni) ayni renk ve dokuda; isik/vinyet duzlenir
    _z = np.asarray(zem).astype(np.float32); _r = np.asarray(Image.open(os.environ["ZEMIN_REF"]).convert("RGB")).astype(np.float32)
    _h, _w = _r.shape[:2]; _ref = _r[int(.15 * _h):int(.85 * _h), int(.62 * _w):int(.95 * _w)]   # K05 sahnesinin temiz keten bolgesi
    _hp = lambda a: a - cv2.GaussianBlur(a, (0, 0), 6)
    _tex = _z - cv2.GaussianBlur(_z, (0, 0), 60)
    _olc = np.array([_hp(_ref[..., c]).std() / max(_hp(_z[..., c]).std(), 1e-3) for c in range(3)])
    zem = Image.fromarray(np.clip(np.median(_ref.reshape(-1, 3), 0) + _tex * _olc, 0, 255).astype(np.uint8))
zem = zem.resize((W, H), Image.LANCZOS)
ALTIN_YOL = {"sol.png": Path(ALTIN) / f"{a_.lower()}_yeni_gold.png", "sag.png": Path(ALTIN) / f"{b_.lower()}_yeni_gold.png",
             "ana.png": Path(ALTIN) / f"{CIFT}_ana.png"}
_maske = T.maske
_baglac = T.baglac
_bilgi = {}


# Serdar 8 Kas: Temmuz burc dosyalarinin parlak sarisi "olmayacak"; ton ana sembolun (ornament baskisi altini, ANA_SEMBOL78) altinina
# esitlenir: kanal basina yuzdelik eslemesi (opak pikseller), sekil ve isik deseni ayni kalir; ana sembol AYNEN.
_ana = np.asarray(Image.open(ALTIN_YOL["ana.png"]).convert("RGBA")).astype(np.float32)
_am = _ana[..., 3] > 230
if _am.sum() < 5000:
    raise SystemExit(f"DUR: ana sembol opak piksel {int(_am.sum())} (RGBA altin bekleniyor)")
QS_ = np.linspace(0, 100, 101)
ANA_Q = np.stack([np.percentile(_ana[..., c][_am], QS_) for c in range(3)], 1)          # 101 x 3


def ton_esitle(rgba):
    a = np.asarray(rgba).astype(np.float32)
    m = a[..., 3] > 230
    if m.sum() < 500:
        return rgba
    for c in range(3):
        kq = np.percentile(a[..., c][m], QS_)
        kq = np.maximum.accumulate(kq + np.arange(len(kq)) * 1e-4)
        a[..., c] = np.interp(a[..., c], kq, ANA_Q[:, c])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def altin_maske(yol, h):
    """maske() ile ayni olcek kurali (alfa kutusu kirpilir, yukseklik h), piksel altin dosyasindan; burclarda ton ana sembole esitlenir."""
    ad = Path(yol).name
    g = Image.open(ALTIN_YOL[ad]).convert("RGBA")
    g = g.crop(g.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox())
    g = g.resize((round(g.width * h / g.height), h), Image.LANCZOS)
    # 8 Kas: burclar posterden yeni dokuda (poster_burc.py), ton islemi YOK (Serdar: Temmuz dokusu olmayacak; ton esitleme de "eski doku")
    _bilgi[ad] = [g.width, g.height]
    return g


# birlesim cizgisi altin: kapak yazisi altin paleti (onayli Ruby baskinin altin pikselleri) + kabartma (sol ust isik)
PQ = np.array([0.02, 0.10, 0.25, 0.50, 0.75, 0.90, 0.98], np.float32)
# PAL: birlesim cizgisi paleti altin_boya icinde ana sembol yuzdeliklerinden


def altin_boya(k):
    h = cv2.GaussianBlur(k, (0, 0), 2.0)
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3)
    isik = -(gx * -0.6 + gy * -0.8) * 6.0
    t = np.clip(0.55 + 0.25 * (cv2.GaussianBlur(k, (0, 0), 1.0) - 0.5) + isik, 0.0, 1.0)
    PAL = np.stack([np.interp(PQ * 100, QS_, ANA_Q[:, c]) for c in range(3)], 1).astype(np.float32)   # birlesim cizgisi: ana sembol altini
    return np.stack([np.interp(t, PQ, PAL[:, c]) for c in range(3)], -1).astype(np.float32)


def altin_baglac(im, xs, y0, uy, wmax=9.0, S=4, n=600):
    gecici = Image.new("RGB", (W, H), K.ZEMIN)
    alfa, uc = _baglac(gecici, xs, y0, uy, wmax=wmax, S=S, n=n)
    a = np.asarray(im).astype(np.float32)
    renk = altin_boya(alfa.astype(np.float32))
    a = a * (1 - alfa[..., None]) + renk * alfa[..., None]
    im.paste(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    return alfa, uc


T.maske = altin_maske
T.baglac = altin_baglac
T.baglac_kapisi = lambda im, alfa, uc, **k: dict(not_="1. gecis (orijinal tuval) kapisi gecti")
T.yerlesim_kapisi = lambda kay, tur: dict(not_="1. gecis kapisi gecti")
K.tuval = lambda: zem.copy()
im, o, _, _ = T.sembol_kart(A, B, Path(MASKE) / CIFT, ALT, AB)
yaz = list(K.YAZILAR)
if yaz != yaz0 or yaz != ["Two Signs, One Shared Symbol", AB, A, B, ALT]:
    raise SystemExit(f"DUR: metin {yaz}")
# GEVSETME (Serdar 8 Kas "Gevsetme: %3", yalniz bu cift): SAGITTARIUS_VIRGO ana sembol altin dosyasi maskeden 10 px dar (428 / 438)
GEO_TOL = {"SAGITTARIUS_VIRGO": 0.03}
TOL = GEO_TOL.get(CIFT, 0.02)
if o["baglac"] != o0["baglac"] or any(abs(p - q) > max(4, TOL * q) for p, q in zip(o["sembol"], o0["sembol"])):   # altin ve maske kutusu oranlari az farkli
    raise SystemExit(f"DUR: geometri farkli {o['baglac']} {o0['baglac']} {o['sembol']} {o0['sembol']}")
im.save(CIKIS, quality=95, subsampling=0)
print(dict(kart="SEMBOL_ALTIN", cift=CIFT, geo_tol=TOL, sembol=o["sembol"], sembol_maske=o0["sembol"], altin=_bilgi,
           baglac=o0["baglac_kapisi"], yerlesim=o0.get("yerlesim", {}).get("sonuc") if isinstance(o0.get("yerlesim"), dict) else str(o0.get("yerlesim"))[:80]))
