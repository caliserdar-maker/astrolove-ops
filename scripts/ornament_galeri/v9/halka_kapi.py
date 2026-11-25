#!/usr/bin/env python3
"""halka_kapi.py (25 Kas, Merkez C karari): ornament kapak videosunda disk kenarinda yabanci (koyu bordo) halka kapisi.
Olcu: her karede disk kenari bandinda (0,97-1,03R) koyu bordo piksel sayisi. Taban = ilk kare (birebir kapak).
PASS: tum karelerde sayi <= taban * (1 + PAY) (PAY 0,10). FAIL ornegi: 25 Kas ilk Ivory videosu (bordo Kling diski kenardan sizar).
Geometri kapak_video.py ile ayni: merkez ve R sahne olcumunden (V_OLC) ve SET json'dan, cikti karesinde kapak_yazi yakinlastirmasi
(KATMAN 'yakin', ust sabit, yatay ortali) uygulanir.
Koyu bordo: R > 50, G < 70, B < 80, R - G > 30 (altin G >= 130 oldugu icin sayilmaz; krem disk sayilmaz).
kullanim: python halka_kapi.py video.mp4 SET.json olc.json katman.npz  -> son satir JSON, cikis 0 PASS / 1 FAIL / 2 hata
"""
import json
import subprocess
import sys

import numpy as np

PAY = 0.10
BANT = (0.97, 1.03)
VW, VH = 1440, 1080


def geometri(set_json, olc_json, katman):
    J = json.load(open(set_json)); O = json.load(open(olc_json))
    k3 = VW / 3000.0
    ko = 3000.0 / O["W"]; pay = (2250 - int(round(O["H"] * ko))) // 2
    cx, cy, R = O["cx"] * ko * k3, (O["cy"] * ko + pay) * k3, J["R"] * k3
    yak = float(np.load(katman)["yakin"])
    x0 = (round(VW * yak) - VW) // 2
    return cx * yak - x0, cy * yak, R * yak


def bordo_sayisi(kare, maske):
    b, g, r = (kare[..., i].astype(np.int16) for i in range(3))
    k = (r > 50) & (g < 70) & (b < 80) & (r - g > 30)
    return int((k & maske).sum())


def main(a):
    if len(a) != 4:
        print(__doc__); return 2
    video, set_json, olc_json, katman = a
    cx, cy, R = geometri(set_json, olc_json, katman)
    yy, xx = np.mgrid[0:VH, 0:VW].astype(np.float32)
    d = np.hypot(xx - cx, yy - cy) / R
    maske = (d >= BANT[0]) & (d <= BANT[1])
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", video],
                       capture_output=True, text=True, check=True)
    s = json.loads(p.stdout)["streams"][0]
    if (s["width"], s["height"]) != (VW, VH):
        print(json.dumps({"sonuc": "HATA", "neden": f"boyut {s['width']}x{s['height']}"})); return 2
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    sayi = []
    while True:
        raw = dec.stdout.read(VW * VH * 3)
        if len(raw) < VW * VH * 3:
            break
        sayi.append(bordo_sayisi(np.frombuffer(raw, np.uint8).reshape(VH, VW, 3), maske))
    dec.wait()
    if not sayi:
        print(json.dumps({"sonuc": "HATA", "neden": "kare yok"})); return 2
    taban = sayi[0]; esik = taban * (1 + PAY)
    kotu = [i for i, n in enumerate(sayi) if n > esik]
    sonuc = "PASS" if not kotu else "FAIL"
    print(json.dumps({"sonuc": sonuc, "kare": len(sayi), "taban": taban, "esik": round(esik, 1), "en_cok": max(sayi),
                      "en_cok_kare": int(np.argmax(sayi)), "asan_kare": len(kotu), "ilk_asan": kotu[0] if kotu else None,
                      "merkez": [round(cx, 1), round(cy, 1)], "R": round(R, 1)}))
    return 0 if sonuc == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
