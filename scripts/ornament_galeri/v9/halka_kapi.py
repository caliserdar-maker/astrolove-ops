#!/usr/bin/env python3
"""halka_kapi.py (25 Kas, Merkez C karari; inceleme 1. tur sonrasi): bordo OLMAYAN ornament diskinin video karelerinde disk kenarina
yabanci (koyu bordo) halka sizmasi kapisi (bordo Kling arka planinin disk kenari, kapak_video.py V_DISK_KENAR yoksa).
Olcu: yalniz IC bant 0,97-1,00R (disk yuzunun kenari). Dis bant (1,00-1,03R) arka plandir (Kling hareketli), yalniz raporlanir.
PASS: her karede ic bant koyu bordo sayisi <= taban + PAY_ORAN x ic bant pikseli. Taban = ilk kare (birebir kapak, SON_KARE).
  Olcum (CANCER_LIBRA Ivory, 25 Kas): taban 39; hatali video en cok 11844 (FAIL); V_DISK_KENAR=1 video en cok 39 (PASS);
  ic bant 27330 px, PAY_ORAN 0,005 -> pay 137 px.
HATA (cikis 2): disk yuzu bordo (0,5-0,9R bandinin > BORDO_DISK_ORAN'i koyu bordo; bordo diskte kapi anlamsiz: onayli Ruby
  videosunda oran 0,836, Ivory 0,008), kare sayisi beklenenden farkli, ffmpeg/ffprobe hatasi, boyut farkli.
Geometri kapak_video.py ile ayni: merkez sahne olcumunden (V_OLC cx, cy), R SET json'dan, kapak_yazi yakinlastirmasi (KATMAN 'yakin').
Koyu bordo: R > 50, G < 70, B < 80, R - G > 30 (altin G >= 130, krem ve yesil sayilmaz).
kullanim: python halka_kapi.py video.mp4 SET.json olc.json katman.npz [kare_sayisi=270] -> son satir JSON; cikis 0 PASS / 1 FAIL / 2 HATA
"""
import json
import subprocess
import sys

import numpy as np

PAY_ORAN = 0.005
IC_BANT = (0.97, 1.00)
DIS_BANT = (1.00, 1.03)
YUZ_BANT = (0.50, 0.90)
BORDO_DISK_ORAN = 0.20
VW, VH = 1440, 1080
KARE_VARSAYILAN = 270


def geometri(set_json, olc_json, katman):
    J = json.load(open(set_json)); O = json.load(open(olc_json))
    k3 = VW / 3000.0
    ko = 3000.0 / O["W"]; pay = (2250 - int(round(O["H"] * ko))) // 2
    cx, cy, R = O["cx"] * ko * k3, (O["cy"] * ko + pay) * k3, J["R"] * k3
    yak = float(np.load(katman)["yakin"])
    x0 = (round(VW * yak) - VW) // 2
    return cx * yak - x0, cy * yak, R * yak


def bordo(kare):
    b, g, r = (kare[..., i].astype(np.int16) for i in range(3))
    return (r > 50) & (g < 70) & (b < 80) & (r - g > 30)


def bordo_sayisi(kare, maske):
    return int((bordo(kare) & maske).sum())


def hata(neden):
    print(json.dumps({"sonuc": "HATA", "neden": neden})); return 2


def main(a):
    if len(a) not in (4, 5):
        print(__doc__); return 2
    video, set_json, olc_json, katman = a[:4]
    beklenen = int(a[4]) if len(a) == 5 else KARE_VARSAYILAN
    try:
        cx, cy, R = geometri(set_json, olc_json, katman)
        p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", video],
                           capture_output=True, text=True, check=True)
        s = json.loads(p.stdout)["streams"][0]
    except Exception as e:  # noqa: BLE001
        return hata(f"girdi/ffprobe: {type(e).__name__}: {str(e)[:150]}")
    if (s["width"], s["height"]) != (VW, VH):
        return hata(f"boyut {s['width']}x{s['height']}")
    yy, xx = np.mgrid[0:VH, 0:VW].astype(np.float32)
    d = np.hypot(xx - cx, yy - cy) / R
    ic = (d >= IC_BANT[0]) & (d < IC_BANT[1]); dis = (d >= DIS_BANT[0]) & (d < DIS_BANT[1]); yuz = (d >= YUZ_BANT[0]) & (d < YUZ_BANT[1])
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    sic, sdis = [], []; yuz_oran = None
    while True:
        raw = dec.stdout.read(VW * VH * 3)
        if len(raw) < VW * VH * 3:
            break
        k = np.frombuffer(raw, np.uint8).reshape(VH, VW, 3); bm = bordo(k)
        if yuz_oran is None:
            yuz_oran = float((bm & yuz).sum()) / float(yuz.sum())
        sic.append(int((bm & ic).sum())); sdis.append(int((bm & dis).sum()))
    if dec.wait() != 0:
        return hata("ffmpeg cozumleme hatasi")
    if len(sic) != beklenen:
        return hata(f"kare {len(sic)} (beklenen {beklenen})")
    if yuz_oran > BORDO_DISK_ORAN:
        return hata(f"disk yuzu bordo (oran {yuz_oran:.3f} > {BORDO_DISK_ORAN}); kapi bordo disk icin degil")
    taban = sic[0]; esik = taban + PAY_ORAN * int(ic.sum())
    kotu = [i for i, n in enumerate(sic) if n > esik]
    sonuc = "PASS" if not kotu else "FAIL"
    print(json.dumps({"sonuc": sonuc, "kare": len(sic), "taban_ic": taban, "esik_ic": round(esik, 1), "en_cok_ic": max(sic),
                      "en_cok_kare": int(np.argmax(sic)), "asan_kare": len(kotu), "ilk_asan": kotu[0] if kotu else None,
                      "dis_bant_bilgi": {"ilk": sdis[0], "en_az": min(sdis), "en_cok": max(sdis)}, "yuz_bordo_oran": round(yuz_oran, 4),
                      "merkez": [round(cx, 1), round(cy, 1)], "R": round(R, 1)}))
    return 0 if sonuc == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
