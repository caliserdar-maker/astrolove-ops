#!/usr/bin/env python3
"""Denetim 20261101C kapi testi (uretimden once): yay_orijinal olcumleri hatayi yakaliyor mu (vekil yaysiz zemin = eski alt bolge
ayna istifi, YALNIZ test).
O1 kayma: dogru katman < 0,5 px; 1 px kaymis katman >= 0,9 px.
O2 olcek: 12x18 yolu (Lanczos 1,5 -> INTER_AREA 1/1,5) korelasyon >= 0,98, kayma <= 0,5; yanlis olcek 1,47 kaymada > 0,5.
O3 bagimsiz kapi (inceleme E1): dogru katman kazanc 0,95-1,05 ve korelasyon >= 0,98; yari parlak, bulanik (Gauss 2) ve 1 px kaymis
   katman kazanc veya korelasyonda FAIL.
O4 yay izi (inceleme E4): eski yay ve x1,015 / x0,97 olcekli ve 140-215 derece parcasi > esik; vekil yaysiz zemin <= esik.
Kullanim: test_yay_orijinal.py <eski 8x10 png>"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import by_ornek3 as BO  # noqa: E402
import yay_olcum as YO  # noqa: E402
import yay_orijinal as YR  # noqa: E402


def mx(s):
    return max(max(abs(x[1]), abs(x[2])) for x in s)


def main():
    eski = np.asarray(Image.open(sys.argv[1]).convert("RGB"))
    yol = YO.eski_yol(eski, (1186.1, 1278.7, 925.0))
    isik, m, _ = YR.katman(eski, yol)
    L = isik.max(2); B = m >= 0.5
    alt = eski[2350:3000]; zem = np.concatenate([alt, alt[::-1]] * 3, 0)[:3000]
    hata = []
    kirp = cv2.dilate(((zem.astype(np.float32) + isik) > 255.5).any(2).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    Lk = np.where(kirp, 0, L)
    o, _ = YR.ekle(zem, isik); L0 = (o.astype(np.float32) - zem).max(2)
    k0 = mx(YR.kayma(Lk, np.where(kirp, 0, L0), B, yol))
    o1, _ = YR.ekle(zem, np.roll(isik, 1, axis=1)); L1 = (o1.astype(np.float32) - zem).max(2)
    k1 = mx(YR.kayma(Lk, np.where(kirp, 0, L1), B, yol))
    print(f"O1 kayma: dogru {k0:.3f} px, 1 px kaymis {k1:.3f} px")
    if not (k0 < 0.5 and k1 >= 0.9):
        hata.append("O1")
    z12 = cv2.resize(zem, (3600, 4500), interpolation=cv2.INTER_LANCZOS4)
    o12, _ = YR.ekle(z12, isik, 1.5, 0)
    L12 = cv2.resize(o12.astype(np.float32) - z12, (2400, 3000), interpolation=cv2.INTER_AREA).max(2)
    kor = float(np.corrcoef(L12[B], L[B])[0, 1]); k12 = mx(YR.kayma(L, L12, B, yol))
    yan = np.clip(cv2.resize(isik, (round(2400 * 1.47), round(3000 * 1.47)), interpolation=cv2.INTER_LANCZOS4), 0, None)
    oy = np.zeros((4500, 3600, 3), np.float32); oy[:yan.shape[0], :yan.shape[1]] = yan
    ky = mx(YR.kayma(L, cv2.resize(oy, (2400, 3000), interpolation=cv2.INTER_AREA).max(2), B, yol))
    print(f"O2 12x18: korelasyon {kor:.4f}, kayma {k12:.3f} px; yanlis olcek 1,47 kayma {ky:.3f} px")
    if not (kor >= 0.98 and k12 <= 0.5 and ky > 0.5):
        hata.append("O2")
    ok = lambda r: BO.KAZANC[0] <= r["kazanc"] <= BO.KAZANC[1] and r["korelasyon"] >= BO.KAPI_KOR  # noqa: E731
    sonuc = {}
    for ad, K in (("dogru", isik), ("yari", isik * 0.5), ("bulanik", cv2.GaussianBlur(isik, (0, 0), 2)), ("kayik1", np.roll(isik, 1, 1))):
        oo, _ = YR.ekle(zem, K); r, _, _ = YR.bagimsiz(eski, oo, m); sonuc[ad] = (r["kazanc"], r["korelasyon"], ok(r))
    print("O3 bagimsiz (kazanc, korelasyon, gecer):", sonuc)
    if not (sonuc["dogru"][2] and not sonuc["yari"][2] and not sonuc["bulanik"][2] and not sonuc["kayik1"][2]):
        hata.append("O3")
    cx, cy = yol["cx"], yol["cy"]

    def olcekli(f):
        big = cv2.warpAffine(isik, np.float32([[f, 0, cx - cx * f], [0, f, cy - cy * f]]), (2400, 3000))
        return np.clip(zem + np.clip(big, 0, None), 0, 255).astype(np.uint8)
    ang, _ = YR.geometri(3000, 2400, yol); par = isik.copy(); par[~((ang > 140) & (ang < 215))] = 0
    iz = dict(eski=YR.yay_izi(eski, yol)["guc"], x1015=YR.yay_izi(olcekli(1.015), yol)["guc"], x097=YR.yay_izi(olcekli(0.97), yol)["guc"],
              parca=YR.yay_izi(np.clip(zem + par, 0, 255).astype(np.uint8), yol)["guc"], vekil=YR.yay_izi(zem, yol)["guc"])
    print("O4 yay izi gucu:", iz, "esik", BO.IZ_ESIK)
    if not (min(iz["eski"], iz["x1015"], iz["x097"], iz["parca"]) > BO.IZ_ESIK and iz["vekil"] <= BO.IZ_ESIK):
        hata.append("O4")
    print("PASS" if not hata else f"FAIL {hata}")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
