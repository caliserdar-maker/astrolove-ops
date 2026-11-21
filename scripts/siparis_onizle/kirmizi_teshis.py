"""Kirmizi nokta teshisi (21 Kas, Merkez 23:1x TR; SALT OKUMA, kapi DEGISMEZ). Teslim dosyasindaki her ton < ESIK_TON kumesi (>= ESIK_TON_KUME px)
icin: alan, kutu, TUM piksellerde en parlak R ve ortalama R, en yakin oge pikseline uzaklik (altin surum B ton >= 28, altin surum A ton >= 20,
beyaz yildiz), 2 px icinde hangi maske, en yakin "altin benzeri" kenar piksellerinin (R > 120, R - B > 40, ton >= 8) ton araligi, ve kesit_olcum
surum A (ed601c14) / surum B (bu kod) kararlari. Yalniz SAHTE dosya icin kullanilir; isim / mesaj yok (yalniz koordinat ve renk sayisi).
Kullanim: kirmizi_teshis.py TESLIM_JPG CIKTI_JSON"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kesit_olcum as K  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def maskeler(a):
    R, G, B = (a[..., i].astype(np.float32) for i in range(3))
    ton = 60.0 * (G - B) / np.maximum(R - B, 1)
    taban = (R > 120) & ((R - B) > 40)
    return dict(altin_B=taban & (ton >= 28), altin_A=taban & (ton >= 20), beyaz=(R > 120) & (G > 120) & (B > 120),
                altin_benzeri=taban & (ton >= 8)), ton


def uzaklik(m):
    """Her piksel icin m maskesindeki en yakin piksele Oklid uzakligi (px)."""
    return cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)


def teshis(a):
    mt = K.kirmizi_maske(a, K.ESIK_TON)
    M, ton = maskeler(a)
    U = {k: uzaklik(v) for k, v in M.items() if k != "altin_benzeri"}
    n, lab, st, _ = cv2.connectedComponentsWithStats(mt.astype(np.uint8), connectivity=8)
    yakin_ab = cv2.dilate(M["altin_benzeri"].astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    kumeler = []
    for i in range(1, n):
        ar = int(st[i, 4])
        if ar < K.ESIK_TON_KUME:
            continue
        x, y, w, h = (int(v) for v in st[i, :4])
        k = lab == i
        Rk = a[..., 0][k]
        d = {m: round(float(U[m][k].min()), 2) for m in U}
        cev = np.zeros_like(k); cev[max(0, y - 3):y + h + 3, max(0, x - 3):x + w + 3] = True
        kenar = cev & M["altin_benzeri"] & ~k
        tonlar = ton[kenar]
        A_kenar = d["altin_A"] <= K.SACAK_MESAFE or d["beyaz"] <= K.SACAK_MESAFE
        B_kenar = d["altin_B"] <= K.SACAK_MESAFE or d["beyaz"] <= K.SACAK_MESAFE
        maxR = int(Rk.max())
        A_sacak = A_kenar and ar <= K.ESIK_SACAK_PX
        B_sacak = B_kenar and ar <= K.ESIK_SACAK_PX and maxR <= K.SACAK_MAX_R
        neden_B = None if B_sacak else ("alan" if ar > K.ESIK_SACAK_PX else ("parlak" if maxR > K.SACAK_MAX_R else "oge_uzak"))
        kumeler.append(dict(alan=ar, kutu=[x, y, x + w, y + h], max_R=maxR, ort_R=round(float(Rk.mean()), 1), uzaklik=d,
                            maske_2px=[m for m in ("altin_B", "altin_A", "beyaz") if d[m] <= K.SACAK_MESAFE],
                            yakin_altin_benzeri_ton=[round(float(tonlar.min()), 1), round(float(tonlar.max()), 1)] if tonlar.size else None,
                            yakin_altin_benzeri_px=int(kenar.sum()), A_sacak=bool(A_sacak), B_sacak=bool(B_sacak), B_FAIL_nedeni=neden_B,
                            ic_yakinda_altin_benzeri=bool((yakin_ab & k).any())))
    return dict(ton_px=int(mt.sum()), kume_3px=len(kumeler), A_FAIL=sum(not c["A_sacak"] for c in kumeler),
                B_FAIL=sum(not c["B_sacak"] for c in kumeler), kumeler=kumeler)


if __name__ == "__main__":
    a = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(np.int16)
    o = dict(dosya=Path(sys.argv[1]).name, boyut=[a.shape[1], a.shape[0]], kural=dict(ton=K.ESIK_TON, kume=K.ESIK_TON_KUME, sacak_px=K.ESIK_SACAK_PX,
             mesafe=K.SACAK_MESAFE, max_R=K.SACAK_MAX_R), **teshis(a))
    json.dump(o, open(sys.argv[2], "w"), indent=1)
    print(json.dumps({k: o[k] for k in ("dosya", "boyut", "ton_px", "kume_3px", "A_FAIL", "B_FAIL")}))
    for c in o["kumeler"]:
        print("KUME", json.dumps({k: c[k] for k in ("alan", "kutu", "max_R", "maske_2px", "yakin_altin_benzeri_ton", "A_sacak", "B_sacak", "B_FAIL_nedeni")}))
    sys.exit(0)
