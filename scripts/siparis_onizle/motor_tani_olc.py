#!/usr/bin/env python3
"""Asama asama zemin halka olcusu (18 Kas, siparis V2B tani; yalniz SAHTE isimli kosu). Her asama dosyasi icin mavi kanal (ve luma):
G3 -> 2B HP60 (3300 olcegi), zemin piksellerinde (altin > 12 genisletme 181 px = HP60 izinin 3 sigmasi, yildiz genisletme 41 px; method B
yan seritleri haric; 3300'den genis asama once 3300'e indirilir) daire yaricapi (zemin_daire=1 -> e 1.0) 2 px bin ortalamasi. Olcu: profil std (es merkezli bilesen), %2.5-97.5
genislik, zemin HP toplam std. Ayrica mavi HP x25 kucuk gorsel. Deger basmaz.
Kullanim: motor_tani_olc.py CIKTI_DIR ETIKET=DOSYA[:olcu] ...   (.npy = uret_tam lineer kayan nokta tuval, srgb'ye cevrilir)"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, str(Path(__file__).resolve().parent))
import zemin_duzelt as Z  # noqa: E402


def srgb(x):
    x = np.clip(x, 0, None)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def yukle(yol):
    if yol.endswith(".npy"):
        return (srgb(np.load(yol)) * 255).astype(np.float32)
    return np.asarray(Image.open(yol).convert("RGB")).astype(np.float32)


def olc(a, cx, cy, yan=None):
    H, W = a.shape[:2]; k = W / 3300.0
    a2 = cv2.GaussianBlur(a, (0, 0), 2 * k); Y = a2.mean(2)
    yil = cv2.dilate(((Y - cv2.GaussianBlur(Y, (0, 0), 20 * k)) > 6).astype(np.uint8), np.ones((int(41 * k) | 1,) * 2, np.uint8)) > 0
    alt = cv2.dilate(((a2[..., 0] - a2[..., 2]) > 12).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(181 * k) | 1,) * 2)) > 0
    bg = ~(yil | alt)
    if yan:
        bg[:, :yan[0]] = False; bg[:, W - yan[1]:] = False
    yy, xx = np.mgrid[0:H, 0:W]
    rb = np.floor(np.hypot(xx - cx, yy - cy) / (2 * k)).astype(np.int32); n = int(rb.max()) + 1
    cnt = np.bincount(rb[bg], minlength=n).astype(np.float64); guv = cnt >= 200 * k * k; guv[:25] = False
    out = dict(zemin_piksel=int(bg.sum()), guvenli_bin=int(guv.sum()))
    hpB = None
    for ad, v in (("B", a[..., 2]), ("Y", 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])):
        b = cv2.GaussianBlur(v.astype(np.float32), (0, 0), 3 * k); hp = b - cv2.GaussianBlur(b, (0, 0), 60 * k)
        p = np.bincount(rb[bg], weights=hp[bg].astype(np.float64), minlength=n)[guv] / cnt[guv]
        out[ad] = dict(profil_std=round(float(p.std()), 4), genislik=round(float(np.percentile(p, 97.5) - np.percentile(p, 2.5)), 4),
                       zemin_hp_std=round(float(hp[bg].std()), 4)) if len(p) > 50 else None
        if ad == "B":
            hpB = hp
    return out, hpB


def main(a):
    cikti = Path(a[0]); cikti.mkdir(parents=True, exist_ok=True); sonuc = {}
    for x in a[1:]:
        etiket, yol = x.split("=", 1); olcu = None
        if ":" in yol:
            yol, olcu = yol.rsplit(":", 1)
        if not Path(yol).exists():
            sonuc[etiket] = dict(hata="dosya yok"); print("YOK", etiket); continue
        A = yukle(yol); H, W = A.shape[:2]
        if not olcu and W > 3300:                    # 7200 genislikli asamalar 3300'e (11x14 ile ayni olcek) kayan noktada INTER_AREA ile indirilir
            A = cv2.resize(A, (3300, int(round(H * 3300 / W))), interpolation=cv2.INTER_AREA); H, W = A.shape[:2]
        if olcu:
            cx, cy, _ = Z.merkez(olcu)
            w, h = Z.OLCU[olcu]; hc = int(round(Z.W0 * h / w)); s = hc / Z.H0; wp = int(round(Z.W0 * s)); ox = (Z.W0 - wp) // 2; f = w / Z.W0
            yan = (int((ox + 24) * f) + 8, int((Z.W0 - ox - wp + 24) * f) + 8) if hc < Z.H0 else None
        else:
            f = W / Z.W0; cx, cy = 3600 * f, 4392 * f; yan = None
        o, hp = olc(A, cx, cy, yan); o.update(dosya=Path(yol).name, boyut=[W, H], merkez=[round(cx, 1), round(cy, 1)])
        q = np.clip(hp * 25 + 128, 0, 255).astype(np.uint8); fk = 900 / max(H, W)
        Image.fromarray(cv2.resize(q, (int(W * fk), int(H * fk)), interpolation=cv2.INTER_AREA)).save(cikti / f"TANI_{etiket}_maviHP.jpg", quality=85)
        sonuc[etiket] = o; print("TANI", etiket, json.dumps(o)); del A, hp
    json.dump(sonuc, open(cikti / "TANI_OZET.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
