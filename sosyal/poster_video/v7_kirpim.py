#!/usr/bin/env python3
"""v7 toplu uretim (Merkez 26 Eki): cift basina POSTER_SRC kirpimi OLCULUR (CL sabit (802,326)-(2197,2140) yerine).
Kullanim: v7_kirpim.py <eski_kapak.jpg> <yeni_kapak (V10)> <cikti POSTER_SRC.png> <rapor.json>
Yontem (poster_video_v7.py ile ayni koyu dikdortgen olcumu: parlaklik < 90, 25x25 kapanis, en buyuk bilesen):
  E = eski kapaktaki (canli eski kapak, yedek r1) koyu poster kutusu; Y = yeni V10 kapaktaki kutu.
  Kirpim = E'nin tam yuksekligi; genislik round(E_h x Y_w / Y_h), E'nin yatay merkezinde (yeni kapakta paspartu posterin yanlarini
  ortuyor, gorunen poster oranina gore). CL olcumu: E (787,326)-(2212,2140), Y 1039x1351 -> (802,326)-(2197,2140) = eski sabit
  kirpim birebir.
FAIL (kirpim yazilmaz, cikis 1): kutu bulunamadi; eski kutu goruntu kenarina degiyor; hesaplanan genislik eski kutudan genis.
Rapor: eski kutu, doluluk (bilesen alani / kutu alani), yeni kutu, kirpim, oranlar (degerlendirme OZET'te; esik yok)."""
import json
import sys

import cv2
import numpy as np
from PIL import Image


def kutu(im):
    lum = im.astype(np.float32) @ np.float32([0.299, 0.587, 0.114])
    m = cv2.morphologyEx((lum < 90).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n < 2:
        return None
    bi = 1 + int(np.argmax(st[1:, 4]))
    x, y, w, h, a = (int(v) for v in st[bi])
    return dict(x0=x, y0=y, x1=x + w, y1=y + h, w=w, h=h, doluluk=round(a / float(w * h), 4))


def olc(eski, yeni):
    E, Yk = kutu(eski), kutu(yeni)
    R = dict(eski=E, yeni=Yk, sonuc="FAIL", neden="")
    if not E or not Yk:
        R["neden"] = "koyu poster kutusu bulunamadi"; return R
    H, W = eski.shape[:2]
    if E["x0"] <= 0 or E["y0"] <= 0 or E["x1"] >= W or E["y1"] >= H:
        R["neden"] = "eski kutu goruntu kenarina degiyor"; return R
    gw = int(round(E["h"] * Yk["w"] / Yk["h"]))
    if gw > E["w"]:
        R["neden"] = f"kirpim genisligi {gw} > eski kutu {E['w']}"; return R
    x0 = int(round((E["x0"] + E["x1"]) / 2 - gw / 2))
    R.update(kirpim=[x0, E["y0"], x0 + gw, E["y1"]], oran_yeni=round(Yk["h"] / Yk["w"], 4), oran_kirpim=round(E["h"] / gw, 4),
             sonuc="PASS")
    return R


def main():
    eski_y, yeni_y, out_png, rapor = sys.argv[1:5]
    eski = np.asarray(Image.open(eski_y).convert("RGB")); yeni = np.asarray(Image.open(yeni_y).convert("RGB"))
    R = olc(eski, yeni)
    R.update(eski_olcu=list(eski.shape[1::-1]), yeni_olcu=list(yeni.shape[1::-1]))
    if R["sonuc"] == "PASS":
        Image.fromarray(eski).crop(tuple(R["kirpim"])).save(out_png)
    json.dump(R, open(rapor, "w"), indent=1)
    print("KIRPIM", R["sonuc"], R.get("kirpim"), R["neden"], flush=True)
    return 0 if R["sonuc"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
