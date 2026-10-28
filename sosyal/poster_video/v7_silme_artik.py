#!/usr/bin/env python3
"""v7 silme artigi olcumu (Merkez 28 Eki: pilot 4570110121 geri alindi; silme sonrasi karede cember icinde sembol artigi).
Hedef maske: poster_video_v7.py ile AYNI ayristirma (PosterV, V7_HALKASIZ=1) ve AYNI v7c silme kurali (betik kaynagindan calistirilir,
kopya kural yok): sembol + sembole yakin altin (R-B fazlasi > YAKIN_T, ilk bos banda kadar). Maske video olcegine (1440x1080) cevrilir.
Olcum: KARE_SN (0,4 sn; silme 0,3 sn'de biter) karesinde maske icinde R-B'nin yerel zemine (31 px medyan) gore fazlasi. Zemin
gurultusu: ayni karede maskenin 6-12 px cevresi (silinmis bolgenin hemen disi). Artik = maske icinde fazla > ESIK olan piksel sayisi.
Kullanim (78 olcum): v7_silme_artik.py olc <poster_video_v7.py> <kapak.jpg> <video.mp4>  -> JSON satir
QC (v7_qc.py): artik(F_kare, maske) fonksiyonu; maske uretimde <video>.silme_maske.png olarak yazilir."""
import json
import os
import sys

import cv2
import numpy as np

KARE_SN = 0.4
ESIK = 20.0          # R-B fazlasi; 78 olcumunden turetildi (bkz. SILME_ARTIK_OLCUM.md)
VW, VH = 1440, 1080


def hedef_maske(pv, kapak):
    """poster_video_v7.py kaynagindan ayristirma + v7c silme kurali -> (video olcekli bool maske, bilgi)"""
    src = open(pv, encoding="utf-8").read()
    bas, son = src.index("try:\n    P = PosterV(tmp)"), src.index("MS_p = np.clip(")
    tmp = os.path.join(os.path.dirname(os.path.abspath(kapak)), "_artik.mp4")
    eski = sys.argv
    sys.argv = [pv, kapak, tmp, "murekkep"]
    os.environ["V7_HALKASIZ"] = "1"; os.environ.setdefault("V7_SILME", "tam")
    g = {"__name__": "v7_silme_artik", "__file__": pv}
    try:
        exec(compile(src[:bas] + "P = PosterV(tmp); os.remove(tmp)\n", pv, "exec"), g)
        exec(compile(src[src.index("def vid(m):"):son], pv, "exec"), g)
    finally:
        sys.argv = eski
    m = g["vid"](g["msym"].astype(np.float32)) > 0.25
    P = g["P"]
    sx0 = min(c[1] for c in P.merged_parts); sx1 = max(c[1] + c[3] for c in P.merged_parts)
    return m, dict(sembol_genislik=int(sx1 - sx0), sembol_parca=len(P.merged_parts), silme_d=g.get("SILME_D"),
                   maske_px=int(m.sum()), poster_w=int(P.w))


def artik(kare_rgb, maske):
    """kare (RGB float) + bool maske -> dict(artik, fazla_max, fazla_p999, zemin_max, zemin_p999)"""
    rb = kare_rgb[..., 0] - kare_rgb[..., 2]
    bg = cv2.medianBlur(np.clip(rb + 128, 0, 255).astype(np.uint8), 31).astype(np.float32) - 128
    ex = rb - bg
    u = maske.astype(np.uint8)
    cevre = (cv2.dilate(u, np.ones((25, 25), np.uint8)) > 0) & ~(cv2.dilate(u, np.ones((13, 13), np.uint8)) > 0)
    e, z = ex[maske], ex[cevre]
    q = lambda a, p: round(float(np.percentile(a, p)), 1) if a.size else 0.0
    return dict(artik=int((e > ESIK).sum()), fazla_max=round(float(e.max()), 1) if e.size else 0.0, fazla_p999=q(e, 99.9),
                zemin_max=round(float(z.max()), 1) if z.size else 0.0, zemin_p999=q(z, 99.9))


def kare_oku(video, sn):
    c = cv2.VideoCapture(video); fps = c.get(cv2.CAP_PROP_FPS) or 30.0
    c.set(cv2.CAP_PROP_POS_FRAMES, int(round(sn * fps)))
    ok, f = c.read(); c.release()
    if not ok:
        raise SystemExit(f"kare okunamadi: {video} {sn}")
    return f[..., ::-1].astype(np.float32)


if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[1] != "olc":
        raise SystemExit(__doc__)
    pv, kapak, video = sys.argv[2:5]
    m, b = hedef_maske(pv, kapak)
    r = artik(kare_oku(video, KARE_SN), m)
    print(json.dumps(dict(b, **r)))
