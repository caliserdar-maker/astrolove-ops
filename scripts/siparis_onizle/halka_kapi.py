#!/usr/bin/env python3
"""Siparis teslim dosyasi mavi halka kapisi (18 Kas, siparis V2B). Radyal profil motor_tani_olc.olc ile ayni: mavi kanal G3 -> HP60
(3300 olcegi), oge (altin > 12, 181 px) / yildiz (41 px) / yontem B yan seritleri disinda, zemin_daire merkezli 2 px radyal bin ortalamasi.
Kapi olcusu = HALKA BANDI: profilin bant geciren bileseni (Gauss 6 bin - Gauss 50 bin = ~12-100 px; oge halelerinin yavas egilimi ve
gurultu disarida), r 200-1400 px araliginda std (gri duzey). PASS: halka_bant <= ESIK. profil_std yalniz bilgi. Ayrica kontrol goruntusu (mavi HP x25) ve istege bagli --ref ile oge renk farki
(dE00, altin cekirdek pikselleri: medyan ve p99). Deger basmaz, yalniz sayi.
Kullanim: halka_kapi.py DOSYA OLCU CIKTI_DIR --tur baski|onizleme --kaynak KODLAMA_ONCESI.png [--ref REF_DOSYA]"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, str(Path(__file__).resolve().parent))
import motor_tani_olc as MT  # noqa: E402
import zemin_duzelt as Z  # noqa: E402

# 19 Kas (GOREV HALKA_KALICI D): mutlak bant oge halelerini de olcer (yeni yol, halkasiz: CANCER_LEO 0.040, TAURUS_VIRGO 0.045,
# SCORPIO_VIRGO 0.073; kodlama oncesi 0.036 / 0.042 / 0.071), gorunurluge tek basina baglanamaz. ASIL OLCU: KODLAMA BANDI = ayni bant
# olcusu (son dosya - kodlama oncesi kaynak) farkinda. Olcum (yerel, motor ortami): baski FAIL mozjpeg q97 0.048, q98 0.039, eski zincir
# son q97 0.046, q97+kroma100 0.025, YCbCr kroma gurultusuz 0.021; PASS yeni kodlama 0.0087 (iki kaynak). Onizleme FAIL eski yol
# (8 bit LANCZOS q92) 0.241 / 0.254; PASS yeni yol 0.018 / 0.019. Mutlak TAVAN kaba ust sinir: FAIL eski sahte 11x14 0.118, eski yol
# onizleme 0.263, yeni yol eski kaynaktan onizleme 0.130; PASS en yuksek yeni yol 0.073 (baski) / 0.073 (onizleme).
# Gercek uretim (halka_olcum 44429045584, 3 cift 11x14, motor ortami): yeni yol kodlama bandi baski 0.0135 / 0.0136 / 0.0145, onizleme 0.0281 /
# 0.0227 / 0.0240 (oge maskesi bin basina pikseli azaltir, gurultu tabani sentetikten yuksek). Ogeli yerel deneme: yeni 0.0094, q97 0.0303.
# Esik = en yuksek PASS x ~1.4, gorunur en dusuk bilinen FAIL'in altinda (baski: ogeli q97 0.030, temiz q98 0.039; onizleme: eski yol 0.24).
KODLAMA_ESIK = {"baski": 0.020, "onizleme": 0.040}
# 19 Kas (GOREV HALKA_KALICI_2 C): kucuk baski (< 5 MP; yalniz 5x7 1500x2100) bin basina piksel az, gurultu tabani yuksek. Olcum 3 cift 5x7
# (kosu 44481039928): yeni yol 0.0232 / 0.0197 / 0.0242, ayni kaynak mozjpeg q97 (bilinen FAIL) 0.0395 / 0.0382 / 0.0400 -> esik 0.030.
KUCUK_PIKSEL, KODLAMA_ESIK_KUCUK_BASKI = 5_000_000, 0.030
# SINIR (Serdar karar 3, kabul): kodlama bandi yalniz KODLAMANIN ekledigi halkayi gorur; kaynakta (_REF) zaten olan halka yalniz mutlak TAVAN
# (0.10) ile yakalanir. Merkez her Midnight Blue siparisinde tam cozunurluklu gorsel kontrol yapar.


def kodlama_esigi(tur, w, h):
    return KODLAMA_ESIK_KUCUK_BASKI if (tur == "baski" and w * h < KUCUK_PIKSEL) else KODLAMA_ESIK[tur]
TAVAN = {"baski": 0.10, "onizleme": 0.10}
# 19 Kas (inceleme F YUKSEK 1): 2:3 ailesi (12x18, 16x24, 20x30, 24x36) bu tavanla gecemiyor (TAURUS_VIRGO 24x36 yeni yol mutlak 0.1316,
# onizleme 0.1324; CANCER_LEO 0.065, SCORPIO_VIRGO 0.0645). Tavan GEVSETILMEDI (Serdar onayi yok): bu aile siparis-giris'te KAPALI.
ESIKLER = TAVAN
R_ARALIK = (200, 1400)


def de00(L1, a1, b1, L2, a2, b2):
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2; C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p; dh = h2p - h1p
    dh = np.where(C1p * C2p == 0, 0, np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2)); Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2; hs = h1p + h2p
    hpm = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    T = 1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6)) - 0.20 * np.cos(np.radians(4 * hpm - 63))
    dth = 30 * np.exp(-((hpm - 275) / 25) ** 2); Rc = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25.0 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2); Sc = 1 + 0.045 * Cpm; Sh = 1 + 0.015 * Cpm * T; Rt = -np.sin(np.radians(2 * dth)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def halka_bant(hp, A, cx, cy, yan):
    """MT.olc ile ayni zemin maskesi ve 2 px radyal profil (3300 olcegi); profilin 6-50 bin bant gecireni, R_ARALIK icinde std."""
    H, W = A.shape[:2]; k = W / 3300.0
    a2 = cv2.GaussianBlur(A, (0, 0), 2 * k); Y = a2.mean(2)
    yil = cv2.dilate(((Y - cv2.GaussianBlur(Y, (0, 0), 20 * k)) > 6).astype(np.uint8), np.ones((int(41 * k) | 1,) * 2, np.uint8)) > 0
    alt = cv2.dilate(((a2[..., 0] - a2[..., 2]) > 12).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(181 * k) | 1,) * 2)) > 0
    bg = ~(yil | alt)
    if yan:
        bg[:, :yan[0]] = False; bg[:, W - yan[1]:] = False
    yy, xx = np.mgrid[0:H, 0:W]
    rb = np.floor(np.hypot(xx - cx, yy - cy) / (2 * k)).astype(np.int32); n = int(rb.max()) + 1
    cnt = np.bincount(rb[bg], minlength=n).astype(np.float64); guv = cnt >= 200 * k * k; guv[:25] = False
    if guv.sum() < 100:
        return None
    s = np.bincount(rb[bg], weights=hp[bg].astype(np.float64), minlength=n)
    r = np.flatnonzero(guv); p = s[guv] / cnt[guv]
    tum = np.arange(r.min(), r.max() + 1); g = np.interp(tum, r, p).astype(np.float32).reshape(-1, 1)
    bp = (cv2.GaussianBlur(g, (1, 0), sigmaX=0.1, sigmaY=6) - cv2.GaussianBlur(g, (1, 0), sigmaX=0.1, sigmaY=50)).ravel()
    m = (tum * 2 >= R_ARALIK[0]) & (tum * 2 < R_ARALIK[1])
    return round(float(bp[m].std()), 4) if m.sum() > 100 else None


def lab(a):
    return cv2.cvtColor((a / 255).astype(np.float32), cv2.COLOR_RGB2Lab)


def kapi(yol, olcu, cikti, tur, ref=None, esik=None, kaynak=None, tam_kontrol=False):
    """tur: 'baski' (olcunun tam pikseli) ya da 'onizleme' (ayni oran, uzun kenar 2000). Tur boyutla tutmazsa FAIL (19 Kas: eski sessiz
    0.07 -> 0.10 gecisi KALDIRILDI). PASS = kaynak (kodlama oncesi _REF.png) VERILMIS ve kodlama_bant <= KODLAMA_ESIK[tur] ve
    halka_bant <= TAVAN[tur]. esik yalniz olcum icin TAVAN'i degistirir (is akislari vermez)."""
    if tur not in ESIKLER:
        return dict(PASS=False, hata=f"tur {tur!r} (baski | onizleme)")
    esik = ESIKLER[tur] if esik is None else esik
    cikti = Path(cikti); cikti.mkdir(parents=True, exist_ok=True)
    A = np.asarray(Image.open(yol).convert("RGB")).astype(np.float32); H, W = A.shape[:2]
    cx, cy, _ = Z.merkez(olcu); w, h = Z.OLCU[olcu]
    onizleme = tur == "onizleme"
    if (not onizleme and (W, H) != (w, h)) or (onizleme and not (max(W, H) == 2000 and abs(W / H - w / h) < 0.002)):
        return dict(PASS=False, hata=f"boyut {W}x{H} tur {tur} ile tutmuyor ({w}x{h} / uzun kenar 2000)")
    hc = int(round(Z.W0 * h / w)); s = hc / Z.H0; wp = int(round(Z.W0 * s)); ox = (Z.W0 - wp) // 2; f = w / Z.W0
    yan = (int((ox + 24) * f) + 8, int((Z.W0 - ox - wp + 24) * f) + 8) if hc < Z.H0 else None
    k = W / w; cx, cy = cx * k, cy * k
    if yan:
        yan = (int(yan[0] * k) + 1, int(yan[1] * k) + 1)
    o, hp = MT.olc(A, cx, cy, yan)
    bant = halka_bant(hp, A, cx, cy, yan)
    kb = None
    if kaynak:
        Rk = np.asarray(Image.open(kaynak).convert("RGB")).astype(np.float32)
        if Rk.shape != A.shape:
            return dict(PASS=False, hata="kaynak boyutu farkli")
        kk = W / 3300.0; b = cv2.GaussianBlur((A - Rk)[..., 2], (0, 0), 3 * kk); hpk = b - cv2.GaussianBlur(b, (0, 0), 60 * kk); del Rk
        kb = halka_bant(hpk, A, cx, cy, yan)                         # maske A'dan (oge / yildiz / yan serit), bant kodlama farkinda
    q = np.clip(hp * 25 + 128, 0, 255).astype(np.uint8)
    Image.fromarray(q if (onizleme or tam_kontrol) else cv2.resize(q, (W // 2, H // 2), interpolation=cv2.INTER_AREA)).save(cikti / f"KONTROL_maviHP25_{Path(yol).stem}.jpg", quality=90)
    ke = kodlama_esigi(tur, W, H)
    out = dict(dosya=Path(yol).name, olcu=olcu, tur=tur, onizleme=onizleme, halka_bant=bant, kodlama_bant=kb, kodlama_esik=ke,
               tavan=esik, kaynak=Path(kaynak).name if kaynak else None, mavi_profil_std=(o.get("B") or {}).get("profil_std"), olcu_ayrinti=o)
    if ref:
        R = np.asarray(Image.open(ref).convert("RGB")).astype(np.float32)
        if R.shape == A.shape:
            g = cv2.erode((((A[..., 0] - A[..., 2]) > 40) & ((R[..., 0] - R[..., 2]) > 40)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
            la, lr = lab(A)[g], lab(R)[g]; d = de00(*lr.T.astype(np.float64), *la.T.astype(np.float64))
            out["oge_de00"] = dict(ref=Path(ref).name, piksel=int(g.sum()), medyan=round(float(np.median(d)), 3), p99=round(float(np.percentile(d, 99)), 3),
                                   ort=round(float(d.mean()), 3))
        else:
            out["oge_de00"] = dict(hata="boyut farkli")
    out["PASS"] = bool(bant is not None and bant <= esik and kb is not None and kb <= ke)
    json.dump(out, open(cikti / f"HALKA_KAPI_{Path(yol).stem}.json", "w"), indent=1)
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    ref = a[a.index("--ref") + 1] if "--ref" in a else None
    es = float(a[a.index("--esik") + 1]) if "--esik" in a else None   # yalniz olcum / kalibrasyon; is akislari VERMEZ
    tur = a[a.index("--tur") + 1] if "--tur" in a else ""
    kyn = a[a.index("--kaynak") + 1] if "--kaynak" in a else None
    r = kapi(a[0], a[1], a[2], tur, ref, es, kyn, "--tam-kontrol" in a); print("HALKA_KAPI", json.dumps({k: v for k, v in r.items() if k != "olcu_ayrinti"}))
    sys.exit(0 if r["PASS"] else 1)
