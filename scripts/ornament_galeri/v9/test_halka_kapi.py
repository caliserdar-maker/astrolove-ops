#!/usr/bin/env python3
"""halka_kapi.py testi (25 Kas). Ag kapali (socket taklidi). Sentetik 1440x1080 video: bordo zemin + krem disk.
PASS: disk tum karelerde temiz. FAIL: ara karelerde disk kenarinda bordo halka. HATA: yanlis boyut.
Ayrica gercek fonksiyon: bordo_sayisi altin ve kremi saymaz. Cikis 0 = tum durumlar beklenen sonucu verdi."""
import json
import os
import socket
import subprocess
import sys
import tempfile

import numpy as np


def _ag_yok(*a, **k):
    raise RuntimeError("TEST AGI: dis ag cagrisi yasak")


socket.socket = _ag_yok          # emsal: scripts/sosyal/test_metricool_yedek.py
socket.create_connection = _ag_yok

KOD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOD)
import halka_kapi as hk  # noqa: E402

VW, VH = hk.VW, hk.VH
BORDO, KREM, ALTIN = (25, 20, 90), (240, 248, 252), (40, 168, 240)   # BGR


def video_yaz(yol, kareler, w=VW, h=VH):
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", "30", "-i", "-",
                          "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", yol], stdin=subprocess.PIPE)
    for k in kareler:
        p.stdin.write(k.astype(np.uint8).tobytes())
    p.stdin.close(); assert p.wait() == 0


def main():
    d = tempfile.mkdtemp()
    # geometri dosyalari: olc 2400x1792 ve SET (R 3000 olcekte), katman yakinlik 1.08
    olc = dict(W=2400.0, H=1792.0, cx=1200.0, cy=990.0); set_ = dict(R=740.0)
    json.dump(olc, open(f"{d}/olc.json", "w")); json.dump(set_, open(f"{d}/set.json", "w"))
    np.savez(f"{d}/katman.npz", yakin=np.float32(1.08))
    cx, cy, R = hk.geometri(f"{d}/set.json", f"{d}/olc.json", f"{d}/katman.npz")
    yy, xx = np.mgrid[0:VH, 0:VW].astype(np.float32)
    dd = np.hypot(xx - cx, yy - cy) / R
    temiz = np.zeros((VH, VW, 3), np.float32); temiz[:] = BORDO; temiz[dd < 1.0] = KREM
    temiz[(dd > 0.90) & (dd < 0.92)] = ALTIN                           # altin halka (sayilmamali)
    halkali = temiz.copy(); halkali[(dd > 0.975) & (dd < 1.0)] = BORDO   # disk kenarinda bordo halka
    video_yaz(f"{d}/pass.mp4", [temiz] * 12)
    video_yaz(f"{d}/fail.mp4", [temiz] * 3 + [halkali] * 6 + [temiz] * 3)
    video_yaz(f"{d}/boyut.mp4", [temiz[:540, :720]] * 3, 720, 540)
    arg = lambda v: [v, f"{d}/set.json", f"{d}/olc.json", f"{d}/katman.npz"]   # noqa: E731
    hata = []
    for ad, beklenen in (("pass", 0), ("fail", 1), ("boyut", 2)):
        rc = hk.main(arg(f"{d}/{ad}.mp4"))
        print(f"{ad}: cikis {rc} (beklenen {beklenen})")
        if rc != beklenen:
            hata.append(ad)
    k = np.zeros((4, 4, 3), np.uint8); k[0, 0] = ALTIN; k[0, 1] = KREM; k[0, 2] = BORDO
    n = hk.bordo_sayisi(k, np.ones((4, 4), bool))
    print(f"bordo_sayisi: {n} (beklenen 1: yalniz bordo; zemin siyah sayilmaz)")
    if n != 1:
        hata.append("bordo_sayisi")
    print("SONUC", "PASS" if not hata else f"FAIL {hata}")
    return 0 if not hata else 1


if __name__ == "__main__":
    sys.exit(main())
