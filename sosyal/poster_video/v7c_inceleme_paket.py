#!/usr/bin/env python3
"""v7c 78 bagimsiz inceleme paketi (Merkez 28 Eki). Etsy yok. Cift basina (yeni = TAM78, eski = BIRLESIK):
 - <out>/kare/<CIFT>_yeni_04.jpg, _yeni_07.jpg, _eski_04.jpg (tam kare 1440x1080, JPEG 85)
 - <out>/kutu/<CIFT>.jpg: isim ve mesaj kutusu (+24 px) kirpimi, eski (ust) / yeni (alt), 0 / 0,2 / 0,4 / 1 / 3 / 5 / 5,9 sn
 - <out>/olcum/<CIFT>.json: ffprobe (kare, sure, fps, olcu) yeni ve eski; kare basina isim / mesaj kutusu yeni-eski farki dizisi
Kullanim: v7c_inceleme_paket.py <poster_video_v7.py> <kapak.jpg> <yeni.mp4> <eski.mp4> <out> <CIFT>"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v7_qc as Q  # noqa: E402
import v7_silme_artik as SA  # noqa: E402

SN = [0, 0.2, 0.4, 1.0, 3.0, 5.0, 5.9]


def kutu(m, pay=24):
    ys, xs = np.where(m)
    return max(0, xs.min() - pay), max(0, ys.min() - pay), min(m.shape[1], xs.max() + pay), min(m.shape[0], ys.max() + pay)


def main():
    pv, kapak, yeni, eski, out, c = sys.argv[1:7]
    for d in ("kare", "kutu", "olcum"):
        os.makedirs(f"{out}/{d}", exist_ok=True)
    F, pf = Q.kareler(yeni); E, pe = Q.kareler(eski)
    for ad, A, t in (("yeni_04", F, 0.4), ("yeni_07", F, 0.7), ("eski_04", E, 0.4)):
        Image.fromarray(A[int(round(t * 30))]).save(f"{out}/kare/{c}_{ad}.jpg", quality=85)
    g = SA.ayristir(pv, kapak)
    R = dict(cift=c, yeni=pf, eski=pe)
    try:
        fn = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    except OSError:
        fn = ImageFont.load_default()
    seritler = []
    for ad, k in (("isim", "names_row"), ("mesaj", "msg_row")):
        m = SA.kutu_maske(g, (k,))
        n = min(len(F), len(E))
        R[f"{ad}_kutu"] = [int(v) for v in kutu(m, 0)]
        R[f"{ad}_fark"] = [round(float(np.abs(F[i][m].astype(np.float32) - E[i][m].astype(np.float32)).mean()), 2) for i in range(n)]
        x0, y0, x1, y1 = kutu(m)
        w, h = x1 - x0, y1 - y0
        s = min(3.0, 220 / max(h, 1), 300 / max(w, 1))
        tw, th = max(1, int(w * s)), max(1, int(h * s))
        im = Image.new("RGB", (len(SN) * (tw + 4), 2 * th + 44), (255, 255, 255)); d = ImageDraw.Draw(im)
        for j, t in enumerate(SN):
            i = min(n - 1, int(round(t * 30)))
            d.text((j * (tw + 4) + 2, 2), f"{ad} {t:g} sn".replace(".", ","), fill=(0, 0, 0), font=fn)
            im.paste(Image.fromarray(E[i][y0:y1, x0:x1]).resize((tw, th), Image.LANCZOS), (j * (tw + 4), 22))
            im.paste(Image.fromarray(F[i][y0:y1, x0:x1]).resize((tw, th), Image.LANCZOS), (j * (tw + 4), 24 + th))
        seritler.append(im)
    W = max(s.width for s in seritler)
    T = Image.new("RGB", (W, sum(s.height for s in seritler) + 30), (255, 255, 255)); d = ImageDraw.Draw(T)
    d.text((4, 4), f"{c}: her serit ust = ESKI (BIRLESIK), alt = YENI (v7c)", fill=(0, 0, 0), font=fn)
    y = 30
    for s in seritler:
        T.paste(s, (0, y)); y += s.height
    T.save(f"{out}/kutu/{c}.jpg", quality=88)
    json.dump(R, open(f"{out}/olcum/{c}.json", "w"))
    print(c, "kare", pf["kare"], pe["kare"], "sure", pf["sure_sn"], pe["sure_sn"],
          "isim max", max(R["isim_fark"]), "mesaj max", max(R["mesaj_fark"]), R["mesaj_kutu"], flush=True)


if __name__ == "__main__":
    main()
