#!/usr/bin/env python3
"""Zemin halka duzeltmesi (18 Kas 2026, siparis 42******47 V2; Serdar "1"). YALNIZ ZEMIN.

Kok neden (olcum, RAPOR_DENETIM_SIPARIS_42******47_V2): MB zemini motor_gpt/uret_tam.py'de zemin_profil.json radyal profilinden
uretilir; profil radyal yonde dalgali (egim bir hizlanip yavaslar). Mavi kanalda (6-64 duzey) bu dalga es merkezli halka olarak gorunur.
Ayni halka deseni (periyot ~271 px, 3300 olcegi) profilden kayan noktada sentetik uretilen zeminde, deneme 11x14 dosyasinda, ana kopyada
ve Ekim standart posterinde var: yani olcu / JPEG adiminda dogmuyor, zemin modelinde. Halka kapisi (kapi g 'halka') ise yalniz JPEG'in
kayan nokta kaynaga gore ekledigi farki 2 kose kutusunda olcuyordu: modelin kendi halkasini goremez.

Duzeltme (teslim dosyasi uzerinde, oge cekirdegi haric): her kanalda zemin piksellerinin (altin ve yildiz disi, aykiri deger atilmis)
elips yaricapina gore ortalama profili p(r) (1 px bin); guvenli bin = ornek >= 30 ve halka alaninin >= %60'i (cember yayi / sembol
ortusu dusuk ornek). D(r) = G60(p) - p (yalniz <= ~60 px halka bileseni; genis egrilik ve ortalama ton korunur), |D| <= 1.5 duzey;
guvenli olmayan binlerde komsu guvenli binlerden ara deger. Pikselde D(r) * w, w = altin cekirdek (R - B > 40, 5 px genisletme)
disinda 1 (sigma 1.5 yumusak gecis). Sonra TPDF 0.5 titresim (yalniz w > 0), mozjpeg q97 4:4:4, JFIF 300 dpi.
Kapi (halka_bant): mavi kanal profilinin G10 - G120 bandinin %2.5-%97.5 genisligi <= ESIK (0.6; olcum: deneme halkali 0.93 FAIL,
duzeltilmis 0.46 PASS, profilden kayan nokta sentetik 0.46).
Kullanim: zemin_duzelt.py GIRIS.jpg CIKIS.jpg OLCU CJPEG [--ozet OZET.json]   -> cikis 0 = duzeltilmis dosya kapidan gecti
Deger basmaz (isim / mesaj yok); yalniz sayi."""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
W0, H0 = 7200, 10800
ZEMIN_MERKEZ = (3600.0, 4392.0, 0.8)          # zemin_profil.json cx, cy (olcek 2000) x 3.6; e
OLCU = {'8x10': (2400, 3000), '16x20': (4800, 6000), '24x30': (7200, 9000), '11x14': (3300, 4200), '12x16': (3600, 4800),
        '18x24': (5400, 7200), '12x18': (3600, 5400), '16x24': (4800, 7200), '20x30': (6000, 9000), '24x36': (7200, 10800),
        'A4': (2480, 3508), 'A3': (3508, 4961), 'A2': (4961, 7016), '5x7': (1500, 2100)}     # motor_gpt/olcu.py:17 (d2b414ee)
ESIK = 0.6
SIGMA_R = 60.0
SINIR = 1.5


def merkez(olcu):
    """Zemin merkezi hedef pikselde (olcu.py donustur ile ayni geometri: 2:3 -> A, digerleri yontem B)."""
    w, h = OLCU[olcu]; hc = int(round(W0 * h / w)); cx, cy, e = ZEMIN_MERKEZ
    if hc >= H0:                                   # yontem A / 2:3: pencere ortadan kirpilir (olcu.py: y0 icerik kutusu ortasi)
        f = w / W0; y0 = (H0 - hc) / 2
        return cx * f, (cy - y0) * f, e
    s = hc / H0; wp = int(round(W0 * s)); ox = (W0 - wp) // 2; f = w / W0
    return (ox + cx * s) * f, cy * s * f, e


def maskeler(a):
    H, W = a.shape[:2]; k = W / 3300.0
    Y = a.mean(2)
    yildiz = cv2.dilate(((Y - cv2.GaussianBlur(Y, (0, 0), 20 * k)) > 3).astype(np.uint8), np.ones((int(15 * k) | 1,) * 2, np.uint8)) > 0
    altin = cv2.dilate(((a[..., 0] - a[..., 2]) > 12).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(61 * k) | 1,) * 2)) > 0
    cekirdek = cv2.dilate(((a[..., 0] - a[..., 2]) > 40).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    return ~(yildiz | altin), cekirdek


def profil(a, rb, n, bg, c, k):
    v = a[..., c]
    dev = np.abs(v - cv2.GaussianBlur(v, (0, 0), 15 * k)); use = bg & (dev < 3)
    cnt = np.bincount(rb[use], minlength=n).astype(np.float64)
    s = np.bincount(rb[use], weights=v[use].astype(np.float64), minlength=n)
    return cnt, s


def _g(x, sg):
    return cv2.GaussianBlur(x.reshape(-1, 1).astype(np.float32), (1, 0), sigmaX=0.1, sigmaY=sg, borderType=cv2.BORDER_REFLECT).ravel()


def halka_bant(a, cx, cy, e):
    """Kapi olcusu: kanal basina radyal profilin G10 - G120 bandi genisligi (3300 olcegi px). Doner (B, sozluk)."""
    H, W = a.shape[:2]; k = W / 3300.0
    yy, xx = np.mgrid[0:H, 0:W]
    rb = np.floor(np.hypot(xx - cx, (yy - cy) * e) / k).astype(np.int32); n = int(rb.max()) + 1; idx = np.arange(n)
    tum = np.bincount(rb.ravel(), minlength=n).astype(np.float64)
    bg, _ = maskeler(a); out = {}
    for c, ad in enumerate("RGB"):
        cnt, s = profil(a, rb, n, bg, c, k)
        guv = (cnt >= 30) & (cnt >= 0.6 * tum); guv[:50] = False
        if guv.sum() < 100:
            out[ad] = None; continue
        p = np.interp(idx, idx[guv], s[guv] / cnt[guv])
        q = (_g(p, 10) - _g(p, 120))[guv]
        out[ad] = round(float(np.percentile(q, 97.5) - np.percentile(q, 2.5)), 4)
    out["guvenli_bin"] = int(guv.sum())
    return out.get("B"), out


def duzelt(a, cx, cy, e):
    H, W = a.shape[:2]; k = W / 3300.0
    yy, xx = np.mgrid[0:H, 0:W]
    rb = np.floor(np.hypot(xx - cx, (yy - cy) * e) / k).astype(np.int32); n = int(rb.max()) + 1; idx = np.arange(n)
    tum = np.bincount(rb.ravel(), minlength=n).astype(np.float64)
    bg, cek = maskeler(a)
    w = cv2.GaussianBlur((~cek).astype(np.float32), (0, 0), 1.5)
    out = a.copy(); bilgi = {}
    for c, ad in enumerate("RGB"):
        cnt, s = profil(a, rb, n, bg, c, k)
        guv = (cnt >= 30) & (cnt >= 0.6 * tum)
        p = np.interp(idx, idx[guv], s[guv] / cnt[guv])
        D = np.clip(_g(p, SIGMA_R) - p, -SINIR, SINIR)
        D = np.interp(idx, idx[guv], D[guv])
        out[..., c] = a[..., c] + D[rb] * w
        bilgi[ad] = dict(D_max=round(float(np.abs(D).max()), 3), D_p99=round(float(np.percentile(np.abs(D[guv]), 99)), 3))
    bilgi["guvenli_bin_orani"] = round(float(guv.mean()), 3)
    return out, w, cek, bilgi


def dpi_yaz(yol, dpi=300):
    """JFIF APP0 yogunlugu (motor_gpt/teslim_jpg.dpi_yaz ile ayni)."""
    b = bytearray(open(yol, "rb").read())
    if b[2:4] == b"\xff\xe0" and b[6:11] == b"JFIF\x00":
        b[13] = 1; b[14:16] = dpi.to_bytes(2, "big"); b[16:18] = dpi.to_bytes(2, "big")
        open(yol, "wb").write(bytes(b))
        return True
    return False


def main(a):
    giris, cikis, olcu, cjpeg = a[0], a[1], a[2], a[3]
    ozet_yol = a[a.index("--ozet") + 1] if "--ozet" in a else None
    im = Image.open(giris); A = np.asarray(im.convert("RGB")).astype(np.float32)
    if [im.size[0], im.size[1]] != list(OLCU[olcu]):
        print("HATA: olcu boyutu tutmuyor"); return 2
    cx, cy, e = merkez(olcu)
    once, once_d = halka_bant(A, cx, cy, e)
    P, w, cek, bilgi = duzelt(A, cx, cy, e)
    rng = np.random.default_rng(18)
    tp = (rng.random(P.shape, dtype=np.float32) - rng.random(P.shape, dtype=np.float32)) * 0.5
    U = np.clip(np.round(P + tp * (w[..., None] > 0)), 0, 255).astype(np.uint8)
    ppm = cikis + ".ppm"; Image.fromarray(U).save(ppm)
    subprocess.run([cjpeg, "-quality", "97", "-sample", "1x1", "-optimize", "-progressive", "-outfile", cikis, ppm], check=True)
    os.remove(ppm); dpi_ok = dpi_yaz(cikis)
    it = Image.open(cikis); B = np.asarray(it.convert("RGB")).astype(np.float32)
    sonra, sonra_d = halka_bant(B, cx, cy, e)
    ic = cv2.erode(cek.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    lab = lambda x: cv2.cvtColor((x / 255).astype(np.float32).reshape(-1, 1, 3), cv2.COLOR_RGB2Lab).reshape(-1, 3)
    bgm = (w > 0.99) & ~ic
    from PIL import JpegImagePlugin
    oz = dict(olcu=olcu, merkez=[round(cx, 1), round(cy, 1), e], duzeltme=bilgi, sigma_r=SIGMA_R, sinir=SINIR,
              halka_bant=dict(once=once_d, sonra=sonra_d, esik=ESIK, once_FAIL=bool(once is not None and once > ESIK),
                              PASS=bool(sonra is not None and sonra <= ESIK)),
              oge_cekirdek=dict(piksel=int(ic.sum()), max_fark=round(float(np.abs(B[ic] - A[ic]).max()), 2) if ic.any() else None,
                                ort_fark=round(float(np.abs(B[ic] - A[ic]).mean()), 3) if ic.any() else None),
              zemin_ton=dict(lab_once=[round(float(x), 3) for x in lab(A[bgm]).mean(0)], lab_sonra=[round(float(x), 3) for x in lab(B[bgm]).mean(0)]),
              teslim=dict(boyut=list(it.size), dpi=[round(float(x)) for x in it.info.get("dpi", (0, 0))], dpi_yazildi=dpi_ok,
                          ornekleme_444=JpegImagePlugin.get_sampling(it) == 0, bayt=os.path.getsize(cikis)))
    L0, L1 = np.array(oz["zemin_ton"]["lab_once"]), np.array(oz["zemin_ton"]["lab_sonra"])
    oz["zemin_ton"]["dE76_ortalama"] = round(float(np.linalg.norm(L1 - L0)), 3)
    oz["teslim"]["PASS"] = bool(oz["teslim"]["boyut"] == list(OLCU[olcu]) and oz["teslim"]["dpi"] == [300, 300]
                                and oz["teslim"]["ornekleme_444"] and oz["teslim"]["bayt"] < 20_000_000)
    oz["PASS"] = bool(oz["halka_bant"]["PASS"] and oz["teslim"]["PASS"] and oz["oge_cekirdek"]["max_fark"] is not None
                      and oz["oge_cekirdek"]["ort_fark"] <= 1.0 and oz["zemin_ton"]["dE76_ortalama"] <= 0.5)
    if ozet_yol:
        json.dump(oz, open(ozet_yol, "w"), indent=1)
    print("ZEMIN_DUZELT", json.dumps(oz))
    return 0 if oz["PASS"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
