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
ESIK = 15.0          # R-B fazlasi. 78 olcumu (video-v7-silme-duzelt 40652593650, OLCUM.csv): zemin en buyuk 13 (AQUARIUS_PISCES);
                    # eski videolarda maske ici en buyuk fazla en az 17 (LIBRA_SAGITTARIUS); v7c ornekleri en fazla 4. Esik 13 + 2.
ESIK_YD = 15.0       # YD 'koyu' (yerel kagida gore koyuluk). Yerel olcum, tek cift (AQUARIUS_AQUARIUS Y01, 28 Eki): v7c maske icinde 0,4 sn
                    # eski video artik 148 px (fazla en buyuk 136,5), v7c en buyuk 4,2; maske cevresi (silinmemis kagit) p99,9 9,0, en buyuk
                    # 18,6 (lifler). Esik 10 / 15 / 20 ile eski 171 / 148 / 133, yeni 0. GECICI: YD esikleri ayri karar (Merkez 28 Eki).
VW, VH = 1440, 1080


def ayristir(pv, kapak):
    """poster_video_v7.py kaynagindan ayristirma + v7c silme kurali; uretim betiginin global sozlugu (P, vid, msym, SILME_D ...)"""
    src = open(pv, encoding="utf-8").read()
    bas, son = src.index("try:\n    P = PosterV(tmp)"), src.index("MS_p = np.clip(")
    tmp = os.path.join(os.path.dirname(os.path.abspath(kapak)), f"_artik_{os.getpid()}.mp4")   # paralel cagrilar cakismasin (28 Eki)
    eski = sys.argv
    sys.argv = [pv, kapak, tmp, "murekkep"]
    os.environ["V7_HALKASIZ"] = "1"; os.environ.setdefault("V7_SILME", "tam")
    g = {"__name__": "v7_silme_artik", "__file__": pv}
    try:
        exec(compile(src[:bas] + "P = PosterV(tmp); os.remove(tmp)\n", pv, "exec"), g)
        exec(compile(src[src.index("def vid(m):"):son], pv, "exec"), g)
    finally:
        sys.argv = eski
    return g


def kutu_maske(g, kutular=("names_row", "msg_row")):
    """isim / mesaj kutulari (poster olcegi, pay yok) -> video olcekli bool maske (v7c 78 karsilastirmasi: bu alanlar degismemeli)"""
    P = g["P"]; m = np.zeros(P.alpha.shape, np.float32)
    for k in kutular:
        _, x, y, w, h, _ = getattr(P, k)
        m[y:y + h, x:x + w] = 1
    return g["vid"](m) > 0.5


def hedef_maske(pv, kapak):
    """poster_video_v7.py kaynagindan ayristirma + v7c silme kurali -> (video olcekli bool maske, bilgi)"""
    g = ayristir(pv, kapak)
    m = g["vid"](g["msym"].astype(np.float32)) > 0.25
    P = g["P"]
    sx0 = min(c[1] for c in P.merged_parts); sx1 = max(c[1] + c[3] for c in P.merged_parts)
    return m, dict(sembol_genislik=int(sx1 - sx0), sembol_parca=len(P.merged_parts), silme_d=g.get("SILME_D"),
                   maske_px=int(m.sum()), poster_w=int(P.w))


def artik(kare_rgb, maske, sinyal="rb"):
    """kare (RGB float) + bool maske -> dict(artik, fazla_max, fazla_p999, zemin_max, zemin_p999)
    sinyal 'rb' (poster, altin murekkep): R-B'nin yerel zemine (31 px medyan) gore fazlasi, esik ESIK.
    sinyal 'koyu' (YD, krem kagitta yesil murekkep; yd_video ic.json silme_sinyal): parlakligin yerel kagida (31 px medyan) gore
    koyulugu, renk kosulu yok (silinmis bolge duz kagit dolgusu; soluk murekkep kenari da sayilir), esik ESIK_YD."""
    if sinyal == "koyu":
        lum = kare_rgb @ np.float32([0.299, 0.587, 0.114])
        ex = cv2.medianBlur(np.clip(lum, 0, 255).astype(np.uint8), 31).astype(np.float32) - lum
        esik = ESIK_YD
    else:
        rb = kare_rgb[..., 0] - kare_rgb[..., 2]
        bg = cv2.medianBlur(np.clip(rb + 128, 0, 255).astype(np.uint8), 31).astype(np.float32) - 128
        ex = rb - bg
        esik = ESIK
    u = maske.astype(np.uint8)
    cevre = (cv2.dilate(u, np.ones((25, 25), np.uint8)) > 0) & ~(cv2.dilate(u, np.ones((13, 13), np.uint8)) > 0)
    e, z = ex[maske], ex[cevre]
    q = lambda a, p: round(float(np.percentile(a, p)), 1) if a.size else 0.0
    return dict(artik=int((e > esik).sum()), fazla_max=round(float(e.max()), 1) if e.size else 0.0, fazla_p999=q(e, 99.9),
                zemin_max=round(float(z.max()), 1) if z.size else 0.0, zemin_p999=q(z, 99.9))


def poster_kutusu(log_yol, kapak_w, vw=VW):
    """uretim logundaki 'poster kapakta X,Y WxH' -> video olceginde (x0, y0, x1, y1); bulunamazsa None"""
    import re
    for l in open(log_yol, encoding="utf-8"):
        m = re.match(r"poster kapakta (\d+),(\d+) (\d+)x(\d+)", l)
        if m:
            x, y, w, h = (int(v) for v in m.groups()); k = vw / kapak_w
            return round(x * k), round(y * k), round((x + w) * k), round((y + h) * k)
    return None


def halka_ici(kare_rgb, kutu):
    """maskeden BAGIMSIZ kalinti olcumu (inceleme 28 Eki bulgu 1: silme_artik kendi maskesine kor). 0,4 sn karesinde poster kutusu
    icinde R-B fazlasi > 12 olan en buyuk parca = altin halka; en kucuk kareler daire uydurmasi; halka ici = merkeze uzaklik < r - 7 ve
    y < cy + 0,55 r (alt bant: kucuk burclar ve toz baslangici disarida). Artik = halka icinde R-B fazlasi > ESIK piksel sayisi.
    Bagimsiz inceleme olcumu (78 TAM78 0,4 sn JPEG kare): halka merkez (721,6, 585,3) r 182,3; yeni en buyuk 14, eski 72/78 > 15."""
    rb = kare_rgb[..., 0] - kare_rgb[..., 2]
    ex = rb - (cv2.medianBlur(np.clip(rb + 128, 0, 255).astype(np.uint8), 31).astype(np.float32) - 128)
    x0, y0, x1, y1 = kutu
    sub = (ex[y0:y1, x0:x1] > 12).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(sub, 8)
    if n < 2:
        return dict(hata="halka bulunamadi")
    i = 1 + int(np.argmax(st[1:, 4]))
    ys, xs = np.where(lab == i); xs = xs + x0; ys = ys + y0
    A = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]
    cx, cy, k = np.linalg.lstsq(A, (xs ** 2 + ys ** 2).astype(np.float64), rcond=None)[0]
    r = float(np.sqrt(k + cx * cx + cy * cy))
    if not 0.25 * (x1 - x0) < r < 0.6 * (x1 - x0):
        return dict(hata=f"halka uydurmasi gecersiz r {r:.1f}", cx=round(float(cx), 1), cy=round(float(cy), 1))
    Y, X = np.mgrid[:ex.shape[0], :ex.shape[1]]
    ic = (np.hypot(X - cx, Y - cy) < r - 7) & (Y < cy + 0.55 * r)
    e = ex[ic]
    return dict(artik=int((e > ESIK).sum()), fazla_max=round(float(e.max()), 1), fazla_p999=round(float(np.percentile(e, 99.9)), 1),
                cx=round(float(cx), 1), cy=round(float(cy), 1), r=round(r, 1), ic_px=int(ic.sum()))


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
