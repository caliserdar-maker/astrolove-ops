#!/usr/bin/env python3
"""Tagline olcumu (video karesi, 1080x1350): bant y 990-1070, x 151-927.
Altin maske: R - B > 40 (lacivert zeminde altin); yildizlar ayiklanir (metin satiri = en buyuk yatay bilesen). Satir yogunlugu profili; yogunlugun max'in %50'sini gectigi ilk/son satir =
kucuk harf govdesi ust (x-yuksekligi cizgisi) ve TABAN CIZGISI. x_yuk = taban - ust. Ust uzanti: en ust altin satir.
Altin ortalama: cekirdek (R - B > 90) piksellerin RGB ortalamasi. Genislik: altin sutun araligi."""
import numpy as np
from scipy import ndimage
Y0, Y1, X0, X1 = 990, 1070, 151, 927
def olc(F):
    b = F[Y0:Y1, X0:X1].astype(np.float32)
    m = (b[..., 0] - b[..., 2]) > 40
    # yildizlari ayikla: yatay 25 px genisletilmis maskenin en buyuk bileseni = metin satiri
    lab, n = ndimage.label(ndimage.binary_dilation(m, structure=np.ones((3, 51))))
    m &= lab == (np.argmax(ndimage.sum(m, lab, range(1, n + 1))) + 1)
    prof = m.sum(1).astype(float)
    ks = np.where(prof > 0.5 * prof.max())[0]
    ys, xs = np.where(m)
    cek = ((b[..., 0] - b[..., 2]) > 90) & m
    return {'x_yukseklik': int(ks[-1] - ks[0] + 1), 'taban_y': int(Y0 + ks[-1]), 'ust_y': int(Y0 + ys.min()),
            'genislik': int(xs.max() - xs.min() + 1), 'merkez_x': round(float(X0 + (xs.min() + xs.max()) / 2), 1),
            'altin_ort': [round(float(v), 1) for v in b[cek].mean(0)], 'altin_px': int(cek.sum())}
