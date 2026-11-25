#!/usr/bin/env python3
"""halka_kapi.py testi (25 Kas, inceleme 1. tur sonrasi). Ag kapali (socket taklidi); yalniz yerel ffmpeg.
Sentetik 1440x1080 video: krem disk + HAREKETLI bordo arka plan (dis bant kare kare degisir; kapi bunu saymamali).
Durumlar ve beklenen cikis: temiz 0 | belirgin halka 1 | SINIRA YAKIN halka (pay+~60 px) 1 | sinir alti halka (pay-~60 px) 0 |
bordo disk 2 | kare sayisi farkli 2 | boyut farkli 2. Ayrica bordo_sayisi: altin, krem, siyah sayilmaz.
Cikis 0 = tum durumlar beklenen sonucu verdi."""
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
                          "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv444p", yol], stdin=subprocess.PIPE)
    for k in kareler:
        p.stdin.write(np.clip(k, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); assert p.wait() == 0


def main():
    d = tempfile.mkdtemp()
    olc = dict(W=2400.0, H=1792.0, cx=1200.0, cy=990.0); set_ = dict(R=740.0)
    json.dump(olc, open(f"{d}/olc.json", "w")); json.dump(set_, open(f"{d}/set.json", "w"))
    np.savez(f"{d}/katman.npz", yakin=np.float32(1.08))
    cx, cy, R = hk.geometri(f"{d}/set.json", f"{d}/olc.json", f"{d}/katman.npz")
    yy, xx = np.mgrid[0:VH, 0:VW].astype(np.float32)
    dd = np.hypot(xx - cx, yy - cy) / R
    ic = (dd >= hk.IC_BANT[0]) & (dd < hk.IC_BANT[1]); pay = hk.PAY_ORAN * int(ic.sum())

    def kare(i, disk=KREM, halka_px=0):
        k = np.zeros((VH, VW, 3), np.float32)
        k[:] = (40, 90, 40) if i % 2 else BORDO                        # hareketli arka plan: bordo / yesil sirayla
        k[dd < 1.0] = disk; k[(dd > 0.90) & (dd < 0.92)] = ALTIN
        if halka_px:                                                   # ic bandin ust yayinda tam halka_px piksel bordo
            yy_, xx_ = np.nonzero(ic & (yy < cy)); sec = np.argsort(xx_)[:halka_px]
            k[yy_[sec], xx_[sec]] = BORDO
        return k

    n = 12
    video_yaz(f"{d}/temiz.mp4", [kare(i) for i in range(n)])
    video_yaz(f"{d}/belirgin.mp4", [kare(i, halka_px=(4000 if 3 <= i < 9 else 0)) for i in range(n)])
    video_yaz(f"{d}/sinir_ustu.mp4", [kare(i, halka_px=(int(pay) + 60 if i == 6 else 0)) for i in range(n)])
    video_yaz(f"{d}/sinir_alti.mp4", [kare(i, halka_px=(int(pay) - 60 if i == 6 else 0)) for i in range(n)])
    video_yaz(f"{d}/bordo_disk.mp4", [kare(i, disk=BORDO) for i in range(n)])
    video_yaz(f"{d}/boyut.mp4", [kare(0)[:540, :720]] * 3, 720, 540)
    arg = lambda v, k=n: [f"{d}/{v}.mp4", f"{d}/set.json", f"{d}/olc.json", f"{d}/katman.npz", str(k)]   # noqa: E731
    hata = []
    for ad, a, beklenen in (("temiz", arg("temiz"), 0), ("belirgin", arg("belirgin"), 1), ("sinir_ustu", arg("sinir_ustu"), 1),
                            ("sinir_alti", arg("sinir_alti"), 0), ("bordo_disk", arg("bordo_disk"), 2),
                            ("kare_sayisi", arg("temiz", 270), 2), ("boyut", arg("boyut", 3), 2)):
        rc = hk.main(a)
        print(f"{ad}: cikis {rc} (beklenen {beklenen})")
        if rc != beklenen:
            hata.append(ad)
    k = np.zeros((4, 4, 3), np.uint8); k[0, 0] = ALTIN; k[0, 1] = KREM; k[0, 2] = BORDO
    m = hk.bordo_sayisi(k, np.ones((4, 4), bool))
    print(f"bordo_sayisi: {m} (beklenen 1)")
    if m != 1:
        hata.append("bordo_sayisi")
    print("SONUC", "PASS" if not hata else f"FAIL {hata}")
    return 0 if not hata else 1


if __name__ == "__main__":
    sys.exit(main())
