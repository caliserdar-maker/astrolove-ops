#!/usr/bin/env python3
"""Iki gorsel arasinda olcek/yerlesim bagimsiz benzerlik (NCC, gri, kucultulmus). SALT YEREL HESAP.
benzerlik(kare, ref): ref, karenin icine iki bicimde oturtulur ve en yuksek NCC dondurulur:
  sigdir  ref kare genisligine olceklenir, dikeyde 4 px adimla kaydirilir (ref kare yuksekliginden kisaysa; tersi icin yatay)
  doldur  ref kareyi tamamen kaplayacak bicimde olceklenip ortadan kirpilir
Kare ve ref once uzun kenari 480 px olacak bicimde kucultulur."""
import numpy as np
from PIL import Image

UZUN = 480


def gri(im, boyut=None):
    im = im.convert('L')
    if boyut:
        im = im.resize(boyut, Image.BILINEAR)
    return np.asarray(im, dtype=np.float32)


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d else 0.0


def benzerlik(kare, ref):
    W, H = kare.size
    o = UZUN / max(W, H)
    W, H = max(1, round(W * o)), max(1, round(H * o))
    k = gri(kare, (W, H))
    rw, rh = ref.size
    en = 0.0
    # sigdir
    if rw / rh >= W / H:
        h = max(1, round(rh * W / rw)); r = gri(ref, (W, h))
        for y in range(0, H - h + 1, 4):
            en = max(en, ncc(k[y:y + h], r))
    else:
        w = max(1, round(rw * H / rh)); r = gri(ref, (w, H))
        for x in range(0, W - w + 1, 4):
            en = max(en, ncc(k[:, x:x + w], r))
    # doldur
    s = max(W / rw, H / rh)
    w, h = max(W, round(rw * s)), max(H, round(rh * s))
    r = gri(ref, (w, h))
    x, y = (w - W) // 2, (h - H) // 2
    return round(max(en, ncc(k, r[y:y + H, x:x + W])), 4)
