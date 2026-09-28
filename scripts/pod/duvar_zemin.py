#!/usr/bin/env python3
"""Galeri kartlari icin kapak duvari zemini + yazi kontrasti (Serdar 28 Eyl karari).
Onayli gorseller (01 kapak, 06/09/10/11 sahne) haric 14 gorselin zemini = kapagin duvari:
data/pod/kapak_sahne_v9.png kapakla ayni isleme: 1213x910'a LANCZOS -> 3000x2250 LANCZOS (kapak_v9_toplu + kapak_v8_kur).
Yazi kontrasti WCAG: >= 4.5:1, arkadaki duvarin en koyu %5'ine (koyu yazi icin en kotu durum) karsi olculur.
Saglanmazsa yazi rengi ayni tonda koyulastirilir (lacivert/kahve); duvar degismez.
"""
import numpy as np
from PIL import Image

KREM = (237, 232, 226)


def duvar(yol):
    return Image.open(yol).convert('RGB').resize((1213, 910), Image.LANCZOS).resize((3000, 2250), Image.LANCZOS)


def _lin(c):
    c = np.asarray(c, np.float64) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lum(rgb):
    """WCAG goreli parlaklik; rgb (...,3)."""
    l = _lin(rgb)
    return l[..., 0] * 0.2126 + l[..., 1] * 0.7152 + l[..., 2] * 0.0722


def kontrast(l1, l2):
    a, b = max(l1, l2), min(l1, l2)
    return (a + 0.05) / (b + 0.05)


def duvar_lum(D, kutu, yuzde=5):
    """Yazi kutusu (x0,y0,x1,y1) arkasindaki duvarin yuzdelik parlakligi (koyu yazi icin %5 = en kotu)."""
    x0, y0, x1, y1 = (int(v) for v in kutu)
    a = np.asarray(D)[max(y0, 0):y1, max(x0, 0):x1].reshape(-1, 3)
    return float(np.percentile(lum(a), yuzde))


def yazi_rengi(renk, lw, esik=4.5):
    """Koyu yazi rengini, duvar parlakligi lw'ye karsi kontrast >= esik olana dek ayni tonda koyulastirir."""
    k = 1.0
    r = tuple(int(v) for v in renk)
    while kontrast(float(lum(np.array(r))), lw) < esik and k > 0.05:
        k -= 0.02
        r = tuple(int(round(v * k)) for v in renk)
    return r
