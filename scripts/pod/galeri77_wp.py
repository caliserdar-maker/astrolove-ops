#!/usr/bin/env python3
"""77 cift galerisi: Warm Parchment 11x14 EMILY/JAMES baskisi hattan uretilemezse (siparis_dosyasi WP yolu
'SISTEM HATASI', sembol_sol ayristirilamiyor) yedek = onayli POD_PRINT WP kaynagi, YALNIZ isim ve mesaj bandi
ciftin MB EMILY/JAMES baskisiyla ayniysa (kaynak zaten EMILY/JAMES + mesaj ise). Yeniden cizim yok.
Olcum: alt %40'ta murekkep satir bantlari (yerel kontrast); sirayla kucuk sembol, isim, mesaj bandi.
Isim ve mesaj bandi murekkep maskeleri kutularina kirpilir, ayni boya olceklenir; isim NCC >= 0.70, mesaj >= 0.80 (ayni metin 0.82+,
farkli isim < 0.5 beklenir). Rapor tek satir; cikis 0 = kullanilabilir.
Kullanim: galeri77_wp.py WP_KAYNAK.jpg MB_EJ_BASKI.jpg
"""
import sys

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def maske(yol):
    a = np.asarray(Image.open(yol).convert('L').resize((1100, 1400), Image.LANCZOS)).astype(np.float32)
    bg = cv2.medianBlur(a.astype(np.uint8), 41).astype(np.float32)
    return np.abs(a - bg) > 18


def bantlar(m):
    H = m.shape[0]
    satir = m.sum(1) > 2
    lab, n = ndi.label(satir)
    out = []
    for s in ndi.find_objects(lab):
        y0, y1 = s[0].start, s[0].stop
        if y0 > 0.58 * H and y1 - y0 >= 25 and y1 < 0.97 * H:      # halka ucu (~14 px) elenir
            out.append((y0, y1))
    return out


def kirp(m, b):
    y0, y1 = b
    ys, xs = np.nonzero(m[y0:y1])
    return m[y0 + ys.min():y0 + ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32)


def ncc(a, b):
    a = cv2.resize(a, (400, 60), interpolation=cv2.INTER_AREA); b = cv2.resize(b, (400, 60), interpolation=cv2.INTER_AREA)
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum() + 1e-9))


if __name__ == '__main__':
    W, M = maske(sys.argv[1]), maske(sys.argv[2])
    bw, bm = bantlar(W), bantlar(M)
    if len(bw) < 3 or len(bm) < 3:
        print(f'WP yedek FAIL: bant bulunamadi (wp {bw}, mb {bm})'); sys.exit(1)
    n_isim = ncc(kirp(W, bw[1]), kirp(M, bm[1])); n_mesaj = ncc(kirp(W, bw[2]), kirp(M, bm[2]))
    ok = n_isim >= 0.70 and n_mesaj >= 0.80     # ayni isimler 0.82-0.87, ayni mesaj 0.93-1.00 (3 cift MB olcumu)
    print(f'WP yedek {"PASS" if ok else "FAIL"}: isim bandi NCC {n_isim:.3f} | mesaj bandi NCC {n_mesaj:.3f} | bantlar wp {bw[:3]} mb {bm[:3]}')
    sys.exit(0 if ok else 1)
