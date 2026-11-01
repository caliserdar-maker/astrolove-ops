#!/usr/bin/env python3
"""Denetim 20261101E madde 3: YD silme_artik FAIL nedenini OLC (kural degistirmez). v7_qc ile ayni olcum (v7_silme_artik.artik,
sinyal 'koyu', ESIK_YD, maske <video>.silme_maske.png) hem tozlu hem tozsuz videoda; 0,3 / 0,4 / 0,5 sn karelerinde. Ayrica 0,4 sn'de
esigi asan piksellerin koordinatlari (video px), maske kenarina uzakligi ve bilesen sayisi yazilir.
Kullanim: yd_silme_artik_olc.py <video.mp4> <cikti.json>   (<video>.tozsuz.mp4 ve <video>.silme_maske.png yaninda olmali)"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v7_silme_artik as SA  # noqa: E402


def piksel(kare, maske):
    lum = kare @ np.float32([0.299, 0.587, 0.114])
    ex = cv2.medianBlur(np.clip(lum, 0, 255).astype(np.uint8), 31).astype(np.float32) - lum
    a = maske & (ex > SA.ESIK_YD)
    ys, xs = np.where(a)
    ic = cv2.distanceTransform(maske.astype(np.uint8), cv2.DIST_L2, 3)        # maske kenarina uzaklik (iceride)
    n, _ = cv2.connectedComponents(a.astype(np.uint8), 8)
    my = np.where(maske.any(1))[0]
    return dict(n=int(a.sum()), bilesen=int(n - 1), maske_y=[int(my.min()), int(my.max())] if my.size else None,
                artik_y=[int(ys.min()), int(ys.max())] if ys.size else None,
                artik_maske_alt_kenara_uzaklik_px=[int(my.max() - ys.max()), int(my.max() - ys.min())] if ys.size and my.size else None, kenar_uzaklik_max=round(float(ic[a].max()), 1) if a.any() else None,
                kenar_uzaklik_medyan=round(float(np.median(ic[a])), 1) if a.any() else None,
                ornek_xy=[[int(x), int(y), round(float(ex[y, x]), 1)] for x, y in sorted(zip(xs, ys), key=lambda t: -t[1])[:40]])


def main():
    v, cik = sys.argv[1:3]
    m = np.asarray(Image.open(v + ".silme_maske.png").convert("L")) > 127
    sonuc = {}
    for ad, yol in (("tozlu", v), ("tozsuz", v + ".tozsuz.mp4")):
        if not os.path.exists(yol):
            sonuc[ad] = {"hata": "video yok"}; continue
        d = {}
        for sn in (0.3, 0.4, 0.5):
            d[str(sn)] = SA.artik(SA.kare_oku(yol, sn), m, "koyu")
        d["piksel_0.4"] = piksel(SA.kare_oku(yol, 0.4), m)
        sonuc[ad] = d
    sonuc["maske_px"] = int(m.sum()); sonuc["esik"] = SA.ESIK_YD
    json.dump(sonuc, open(cik, "w"), indent=1)
    print(os.path.basename(v), "tozlu 0,4 artik", sonuc["tozlu"].get("0.4", {}).get("artik"), "| tozsuz 0,4 artik",
          sonuc["tozsuz"].get("0.4", {}).get("artik"))


if __name__ == "__main__":
    main()
