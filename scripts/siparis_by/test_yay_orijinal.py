#!/usr/bin/env python3
"""Denetim 20261101C kapi testi (uretimden once): yay_orijinal olcumleri hatayi yakaliyor mu.
O1 kayma: katman 1 px kaydirilip eklenirse kayma olcumu >= 0,9 px (kapi < 0,5 FAIL verir); kaymasiz 0.
O2 olcek: 12x18 yolu (Lanczos 1,5 -> INTER_AREA 1/1,5) korelasyon >= 0,98 ve kayma <= 0,5; yanlis olcek (1,47) kaymada FAIL.
O3 yay izi: eski 8x10'da yay izi medyani > 100, vekil yaysiz zeminde <= 5.
Kullanim: test_yay_orijinal.py <eski 8x10 png>"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yay_olcum as YO  # noqa: E402
import yay_orijinal as YR  # noqa: E402


def mx(s):
    return max(max(abs(x[2]), abs(x[3])) for x in s)


def main():
    eski = np.asarray(Image.open(sys.argv[1]).convert("RGB"))
    yol = YO.eski_yol(eski, (1186.1, 1278.7, 925.0))
    isik, m, _ = YR.katman(eski, yol)
    L = isik.max(2); B = m >= 0.5
    alt = eski[2350:3000]; zem = np.concatenate([alt, alt[::-1]] * 3, 0)[:3000]     # yaysiz vekil zemin (yalniz test)
    hata = []
    # by_ornek3 ile ayni: 255'te kirpilan pikseller (zemin yildizi + yay isigi) kayma olcumunde iki goruntude de 0
    kirp = cv2.dilate(((zem.astype(np.float32) + isik) > 255.5).any(2).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    Lk = np.where(kirp, 0, L)
    o, _ = YR.ekle(zem, isik); L0 = (o.astype(np.float32) - zem).max(2)
    k0 = mx(YR.kayma(Lk, np.where(kirp, 0, L0), B))
    kay = np.roll(isik, 1, axis=1); o1, _ = YR.ekle(zem, kay); L1 = (o1.astype(np.float32) - zem).max(2)
    k1 = mx(YR.kayma(Lk, np.where(kirp, 0, L1), B))
    print(f"O1 kayma: dogru {k0:.3f} px, 1 px kaymis {k1:.3f} px")
    if not (k0 < 0.05 and k1 >= 0.9):
        hata.append("O1")
    z12 = cv2.resize(zem, (3600, 4500), interpolation=cv2.INTER_LANCZOS4)
    o12, _ = YR.ekle(z12, isik, 1.5, 0)
    L12 = cv2.resize(o12.astype(np.float32) - z12, (2400, 3000), interpolation=cv2.INTER_AREA).max(2)
    kor = float(np.corrcoef(L12[B], L[B])[0, 1]); k12 = mx(YR.kayma(L, L12, B))
    yan = np.clip(cv2.resize(isik, (round(2400 * 1.47), round(3000 * 1.47)), interpolation=cv2.INTER_LANCZOS4), 0, None)
    oy = np.zeros((4500, 3600, 3), np.float32); oy[:yan.shape[0], :yan.shape[1]] = yan
    Ly = cv2.resize(oy, (2400, 3000), interpolation=cv2.INTER_AREA).max(2)
    ky = mx(YR.kayma(L, Ly, B))
    print(f"O2 12x18: korelasyon {kor:.4f}, kayma {k12:.3f} px; yanlis olcek 1,47 kayma {ky:.3f} px")
    if not (kor >= 0.98 and k12 <= 0.5 and ky > 0.5):
        hata.append("O2")
    ie, iz = YR.yay_izi(eski, yol), YR.yay_izi(zem, yol)
    print(f"O3 yay izi: eski {ie['medyan']}, vekil yaysiz {iz['medyan']}")
    if not (ie["medyan"] > 100 and iz["medyan"] <= 5):
        hata.append("O3")
    print("PASS" if not hata else f"FAIL {hata}")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
