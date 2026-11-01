#!/usr/bin/env python3
"""1st Anniversary (YD) Starlit 12x18 ORNEK 3 (Merkez 31 Eki, Serdar karari a: yeni yuksek cozunurluklu zemin). ETSY YOK, toplu uretim yok.
Kural (Serdar 31 Eki): hicbir oge tek yonde uzatilmaz / basilmaz; yalniz esit oranli olcek; desen kopyasi / aynalama yok; urun sembolu yapay
zekadan gecmez (Real-ESRGAN YALNIZ zemin dokusuna uygulanir).
Adimlar (12x18 = 3600x5400, 300 dpi; 8x10 karsilastirma 2400x3000 ayni ayarlarla):
  1) zemin: Canva Starlit 2:3 doku (2400x3600, TEMP/YD_ZEMIN_YENI/1_Starlit_2x3_kaynak.png). 12x18: Real-ESRGAN x2plus (resmi agirlik,
     spandrel ile, CPU, karolu) 4800x7200 -> esit olcekle 3600x5400 (INTER_AREA). 8x10: kaynagin ortasindan 2400x3000 (olcek yok).
  2) ince cerceve: 8x10 zeminindeki cizginin OLCULEN profili (renk, kalinlik) ile kodla; dort kenar payi ESIT = 8x10 yan payi (89 px @2400)
     x olcek (12x18: 1.5 -> 134 px). (8x10'da ust / alt pay 56 / 48 idi; Merkez: dort kenar esit.)
  3) yay (Denetim 20261101C, Serdar 1 Kas "orijinal yayi istiyorum"): kodla CIZILMEZ. Canva'da yay ayri oge degil (DAHZk1niiMA s.2 yalniz
     zemin gorseli); eski 8x10 zeminden PIKSEL olarak alinir (yay_orijinal.katman: yerel zemin cikarimi, yalniz isik, yay bandi maskesi;
     yay ustu isiltiler ve tepe yildizi yayla birlikte, ayri ekleme yok). 8x10 olcek 1 kayma 0; 12x18 yalniz esit oranli 1,5 (Lanczos).
     Kapi: 8x10 bant ort mutlak fark <= 2, kayma 0 (< 0,5 px); 12x18 1/1,5 kucultmede korelasyon >= 0,98, kayma <= 0,5 px @2400;
     yeni zeminde eski yol uzerinde yay izi medyani <= 5 gri.
  4) (eski adim: tepe yildizi / isiltiler ayri eklenmez; 3. adimdaki katmanin parcasidir.)
  5) sembol, burc isaretleri, isimler, baslik, tarih: by_poster (KOD_REF, degistirilmeden) 8x10 yerlesiminin esit olcekli hali, dikeyde
     ortali (12x18'de 8x10 blok 3600x4500, ust / alt 450 px). 12x18: by_poster SCALE=BY_SCALE (vars. 2: 4800x6000) cizilir, esit olcekle 3600x4500'e (INTER_AREA)
     -> 3600x4500; yalniz ogelerin degistirdigi pikseller (fark > 2, 3 px yumusak maske) zemine aktarilir (zemin bit duzeyinde korunur).
Kullanim: by_ornek3.py --kod <bizim-yilimiz> --zemin <2:3 png> --esrgan <x2plus.pth> --out <dir> [--pair CANCER_LIBRA --n1 EMMA --n2 JAMES]"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yay_olcum as YO  # noqa: E402  (Denetim 20261101B: yay sirti olcumu / kapi)
import yay_orijinal as YR  # noqa: E402  (Denetim 20261101C: orijinal yay piksel katmani)

ESKI = "z/Baski_2400x3000_Buyutulmus/1_Starlit_8x10_300ppi.png"
YAY = dict(cx=1187.0, cy=1251.0, r=936.0)                         # @2400x3000 (31 Eki olcum); bos aci araligi eski zeminden olculur
CERCEVE_PAY = 89                                                   # @2400 yan pay (31 Eki olcum: 89 / 90)
YILDIZ = (1040, 150, 1360, 500)                                    # @2400 tepe yildiz kirpim kutusu (x0, y0, x1, y1)
YILDIZ_MERKEZ = (1197, 260)
ISILTI = ((252, 1311), (1661, 481), (1990, 819))                    # @2400 yay ustu isilti merkezleri (178,2 / 300,5 / 330,0 derece; olcum 1 Kas,
                                                                    # yay_olcum isilti sektorlerinde en parlak nokta)
ISILTI_YARI = 120                                                   # kirpim yari genisligi (70'te 330 derece halesi kutu kenarina degiyordu)
YOL_SEED = (1186.1, 1278.7, 925.0)                                 # @2400 eski yay sirti en iyi daire (f6078af3 olcumu); yalniz baslangic
KAPI_8x10 = dict(en_buyuk=1.5, medyan=0.5)                          # Serdar 1 Kas karar 1a: 8x10 cikti px; 12x18 = x 1,5 (1,0 eski yayin taneli
                                                                    # 1,75-3,25 / 14 derece bolgesinde sirt olcum gurultusunun altindaydi)
BY_SCALE = int(os.environ.get("BY_SCALE", "2"))                    # by_poster cizim olcegi (12x18 icin sonra esit olcekle 3600x4500)
KAPI_FARK = 2.0       # Denetim 20261101C: 8x10 yay bandinda ortalama mutlak fark <= 2/255, kayma 0 px
KAPI_KOR = 0.98       # 12x18: 1/1,5 kucultulmus yay bandi ile eski 8x10 yay korelasyonu >= 0,98
KAPI_KAYMA12 = 0.5    # 12x18: konum farki <= 0,5 px @2400
IZ_ESIK = 5.0         # yeni zeminde eski yol uzerinde yay izi medyani <= 5 gri (eski yay: ~187; ONERI esik)


# ---------------------------------------------------------------- Real-ESRGAN (yalniz zemin)
def esrgan(img, agirlik, karo=384, pay=24):
    import torch
    from spandrel import ModelLoader
    torch.set_num_threads(os.cpu_count() or 4)
    m = ModelLoader().load_from_file(agirlik).eval()
    s = m.scale
    a = img.astype(np.float32) / 255.0
    H, W = a.shape[:2]
    out = np.zeros((H * s, W * s, 3), np.float32)
    n = 0
    top = ((H + karo - 1) // karo) * ((W + karo - 1) // karo)
    for y in range(0, H, karo):
        for x in range(0, W, karo):
            y0, x0 = max(0, y - pay), max(0, x - pay)
            y1, x1 = min(H, y + karo + pay), min(W, x + karo + pay)
            t = torch.from_numpy(a[y0:y1, x0:x1].transpose(2, 0, 1)[None])
            with torch.no_grad():
                r = m(t)[0].numpy().transpose(1, 2, 0)
            yy, xx = (y - y0) * s, (x - x0) * s
            hh, ww = min(karo, H - y) * s, min(karo, W - x) * s
            out[y * s:y * s + hh, x * s:x * s + ww] = r[yy:yy + hh, xx:xx + ww]
            n += 1
            if n % 20 == 0 or n == top:
                print(f"ESRGAN {n}/{top} karo", flush=True)
    return np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8), s


# ---------------------------------------------------------------- 8x10 zeminden olcum
def olc(eski):
    a = eski.astype(np.float32)
    g = a.mean(2)
    # cerceve: sol kenar dikey cizgi, satir 1000-2000, x 70-110
    p = g[1000:2000, 70:110].mean(0); z = np.median(p[:8])
    i = int(np.argmax(p)); prof = p - z
    yar = np.where(prof >= prof[i] / 2)[0]
    cer_renk = a[1000:2000, 70 + i].mean(0); cer_zemin = a[1000:2000, 70:76].reshape(-1, 3).mean(0)
    cer = dict(x=70 + i, fwhm=float(yar.max() - yar.min() + 1), renk=cer_renk.tolist(), zemin=cer_zemin.tolist(),
               opaklik=float(np.clip((cer_renk - cer_zemin).sum() / max(1.0, (np.array([235, 215, 170]) - cer_zemin).sum()), 0, 1)))
    # yay: 0 ve 180 derecede radyal profil (parlak ve temiz kisimlar)
    pr, rk = [], []
    for ang in (0.0, 180.0, 200.0, 340.0):
        t = np.radians(ang); v = []
        for d in np.arange(-15, 16):
            x = YAY["cx"] + (YAY["r"] + d) * np.cos(t); y = YAY["cy"] + (YAY["r"] + d) * np.sin(t)
            v.append(a[int(round(y)), int(round(x))])
        v = np.array(v); gv = v.mean(1); pr.append(gv); rk.append(v[int(np.argmax(gv))])
    pr = np.array(pr); zz = np.median(pr[:, :5]); tepe = pr.max(1) - zz
    yar = [np.where(p - zz >= (p.max() - zz) / 2)[0] for p in pr]
    yay = dict(fwhm=float(np.median([y.max() - y.min() + 1 for y in yar])), tepe_renk=np.median(np.array(rk), 0).tolist(),
               tepe_fark=float(np.median(tepe)))
    # yay bos aci araligi (inceleme 31 Eki: 60-120 yanlis): 5 derecelik dilimlerde yay kontrasti (r +- 8 en parlak - r +- 20..30 medyani)
    kon = []
    for ang in range(0, 360, 5):
        t = np.radians(ang + 2.5)
        v = [g[int(round(YAY["cy"] + (YAY["r"] + d) * np.sin(t))), int(round(YAY["cx"] + (YAY["r"] + d) * np.cos(t)))] for d in range(-30, 31)]
        v = np.array(v); kon.append(float(v[22:39].max() - np.median(np.r_[v[:11], v[-11:]])))
    var = np.array(kon) >= 30
    en, bas, i = 0, 0, 0
    while i < 72 * 2:                                   # dairesel en uzun bos dilim dizisi
        if not var[i % 72]:
            j = i
            while j < i + 72 and not var[j % 72]:
                j += 1
            if j - i > en:
                en, bas = j - i, i
            i = j
        i += 1
    yay["bos"] = [(bas % 72) * 5.0, ((bas + en) % 72) * 5.0]
    yay["kontrast_5derece"] = [round(x) for x in kon]
    return dict(cerceve=cer, yay=yay)


# ---------------------------------------------------------------- cizim (esit olcek k = genislik / 2400)
def cerceve(img, k, o):
    H, W = img.shape[:2]
    pay = round(CERCEVE_PAY * k)
    sig = max(0.6, o["cerceve"]["fwhm"] * k / 2.355)
    m = np.zeros((H, W), np.float32)
    cv2.rectangle(m, (pay, pay), (W - 1 - pay, H - 1 - pay), 1.0, 1, lineType=cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), sig); m /= max(m.max(), 1e-6)
    renk = np.array(o["cerceve"]["renk"], np.float32); zem = np.array(o["cerceve"]["zemin"], np.float32)
    ek = (renk - zem)[None, None]                                    # olculen fark katmani (toplamali; zemin dokusu korunur)
    out = img.astype(np.float32) + m[..., None] * ek
    return np.clip(out, 0, 255).astype(np.uint8), dict(pay_px=pay, sigma=round(sig, 2))


def yay_yolu(eski):
    """Yayin ESKI 8x10'daki GERCEK yolu (Serdar 31 Eki, Gorev C: yay tepesi eski gercek sekliyle). 31 Eki cemberi (1187,1251,936) eski
    yayin sirtindan medyan 24 px, p95 39 px sapiyordu (tepe ~40 px yukarida; olcum 31 Eki aksam). Sirt: her 0,5 derecede yaricap
    dogrultusunda en parlak nokta (parlaklik farki > 80); en iyi daire merkezi etrafinda r(aci) tablosu, 3 derece dairesel yumusatma;
    sirt bulunmayan acilar (alt aciklik, tepe yildizinin arkasi) dairesel dogrusal ara degerle doldurulur; alt aciklik = sirtsiz en uzun
    dairesel aralik (tepe yildizi sektoru 258-282 haric). -> dict(cx, cy, r (720 deger, 0,5 derece), bos, artik)"""
    a = eski.astype(np.float32)
    g = a[..., 0] * 0.5 + a[..., 1] * 0.4 + a[..., 2] * 0.1
    cx0, cy0, r0 = YAY["cx"], YAY["cy"], YAY["r"]
    P, var = [], np.zeros(720, bool)
    for i in range(720):
        t = np.radians(i / 2)
        rs = np.arange(r0 - 110, r0 + 40, 0.5)
        xs, ys = cx0 + rs * np.cos(t), cy0 + rs * np.sin(t)
        v = cv2.remap(g, xs.astype(np.float32)[None], ys.astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        v = cv2.GaussianBlur(v[None], (0, 0), 1.5)[0]
        j = int(v.argmax())
        if v[j] - np.median(v) > 80 and not (258 <= i / 2 <= 282):
            P.append((xs[j], ys[j])); var[i] = True
    P = np.array(P)
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
    sol = np.linalg.lstsq(A, P[:, 0] ** 2 + P[:, 1] ** 2, rcond=None)[0]
    cx, cy = float(sol[0]), float(sol[1]); rb = float(np.sqrt(sol[2] + cx ** 2 + cy ** 2))
    ang = (np.degrees(np.arctan2(P[:, 1] - cy, P[:, 0] - cx)) + 360) % 360
    rr = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
    o = np.argsort(ang); ang, rr = ang[o], rr[o]
    tab = np.interp(np.arange(720) / 2, np.r_[ang - 360, ang, ang + 360], np.r_[rr, rr, rr])
    ek = np.r_[tab[-12:], tab, tab[:12]]
    tab = np.convolve(ek, cv2.getGaussianKernel(25, 6).ravel(), "same")[12:-12]       # 3 derece (6 ornek) dairesel yumusatma
    # alt aciklik: YENI merkez etrafinda sirt acilari arasindaki en buyuk dairesel bosluk (tepe yildizi boslugu daha kisa)
    bosluk = np.diff(np.r_[ang, ang[0] + 360])
    gi = int(np.argmax(bosluk))
    b0, b1 = round(float(ang[gi]) % 360, 1), round(float(ang[gi] + bosluk[gi]) % 360, 1)
    art = np.abs(rr - np.interp(ang, np.arange(720) / 2, tab))
    daire_art = np.abs(np.hypot(P[:, 0] - cx0, P[:, 1] - cy0) - r0)
    return dict(cx=cx, cy=cy, r=tab, bos=[b0, b1], en_iyi_daire_r=rb,
                artik=dict(yol_medyan=round(float(np.median(art)), 2), yol_p95=round(float(np.percentile(art, 95)), 2),
                           eski_daire_medyan=round(float(np.median(daire_art)), 2), eski_daire_p95=round(float(np.percentile(daire_art, 95)), 2),
                           sirt_nokta=int(len(P))))


def yay(img, k, oy, o, yol=None):
    H, W = img.shape[:2]
    sig = max(0.8, o["yay"]["fwhm"] * k / 2.355)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    if yol is None:   # eski davranis (daire)
        cx, cy, r = YAY["cx"] * k, YAY["cy"] * k + oy, YAY["r"] * k
        d = np.hypot(xx - cx, yy - cy) - r
        ang = (np.degrees(np.arctan2(yy - cy, xx - cx)) + 360) % 360
        b0, b1 = o["yay"]["bos"]
    else:             # eski 8x10'daki gercek yol, esit olcek
        cx, cy = yol["cx"] * k, yol["cy"] * k + oy
        ang = (np.degrees(np.arctan2(yy - cy, xx - cx)) + 360) % 360
        d = np.hypot(xx - cx, yy - cy) - YO.tablo_r(np.asarray(yol["r"]) * k, ang)   # 0,25 derece tablo (yay_olcum.eski_yol)
        r = float(np.median(yol["r"]) * k)
        b0, b1 = yol["bos"]
    if yol is not None and yol.get("sonum") is not None:   # Serdar 1 Kas madde 3: uc sonumu eski yayin olculen kontrastindan (yay_olcum.uc_sonumu)
        sonum = YO.tablo_r(np.asarray(yol["sonum"]), ang)
    else:             # aciklik kenarinda 12 derecelik yumusak sonum (31 Eki)
        uz = np.minimum(np.abs(((ang - b0 + 180) % 360) - 180), np.abs(((ang - b1 + 180) % 360) - 180))
        icerde = (ang > b0) & (ang < b1) if b0 < b1 else (ang > b0) | (ang < b1)
        sonum = np.where(icerde, 0.0, np.clip(uz / 12.0, 0, 1))
    cekirdek = np.exp(-0.5 * (d / sig) ** 2)
    hale = 0.18 * np.exp(-0.5 * (d / (sig * 6)) ** 2)                 # hafif isik halesi
    m = (cekirdek + hale) * sonum
    renk = np.array(o["yay"]["tepe_renk"], np.float32)
    out = img.astype(np.float32)
    out = out + m[..., None] * (renk[None, None] - out) * 0.92
    return np.clip(out, 0, 255).astype(np.uint8), dict(merkez=[round(cx, 1), round(cy, 1)], r=round(r, 1), sigma=round(sig, 2),
                                                       bos_aci=[b0, b1], yol="eski_gercek" if yol is not None else "daire"), (cekirdek * sonum) > 0.1


def yay_profil(eski, yol):
    """Yay kesit profili GERCEK yol uzerinde (inceleme 1 Kas madde 4: 31 Eki olc() profili YAY dairesi etrafinda +-15 px aliyordu; gercek yol
    200 / 340 derecede 18-21 px disarida, fwhm 4,5 px cikiyordu, eski yayda 7-9 px). Temiz acilar: 150-170, 185-250, 290-298, 305-322, 335-355
    (isilti / tepe yildizi sektorleri ve uclar disi), 5 derecede bir; radyal +-20 px, tek aci (teget ortalama yok). -> fwhm, tepe_fark, tepe_renk"""
    a = eski.astype(np.float32); g = YO.gri(eski)
    acilar = [x for x in np.r_[np.arange(150, 171, 5), np.arange(185, 251, 5), np.arange(290, 299, 4), np.arange(305, 323, 5), np.arange(335, 356, 5)]
              if not YO.sektorde([x], yol["isilti"])[0]]
    fw, tf, rk = [], [], []
    for th in acilar:
        t = np.radians(th); r0 = float(YO.tablo_r(np.asarray(yol["r"]), th))
        ds = np.arange(-20, 20.5, 0.5)
        xs, ys = yol["cx"] + (r0 + ds) * np.cos(t), yol["cy"] + (r0 + ds) * np.sin(t)
        v = cv2.remap(g, xs.astype(np.float32)[None], ys.astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        z = float(np.median(np.r_[v[:8], v[-8:]])); j = int(v.argmax())
        if not 10 <= j <= len(v) - 11:
            continue
        yar = np.where(v - z >= (v[j] - z) / 2)[0]
        fw.append((yar.max() - yar.min() + 1) * 0.5); tf.append(v[j] - z)
        rk.append(cv2.remap(a, np.float32([[xs[j]]]), np.float32([[ys[j]]]), cv2.INTER_LINEAR)[0, 0])
    return dict(fwhm=float(np.median(fw)), tepe_fark=float(np.median(tf)), tepe_renk=np.median(np.array(rk), 0).tolist(), aci_sayisi=len(fw),
                fwhm_aralik=[round(float(np.min(fw)), 1), round(float(np.max(fw)), 1)], kaynak="gercek yol uzerinde (yay_profil)")


def uc_kalibre(o, yol, zem=None):
    global YAY_RENK_GRI
    t_ = o["yay"]["tepe_renk"]; YAY_RENK_GRI = 0.5 * t_[0] + 0.4 * t_[1] + 0.1 * t_[2]
    """Serdar 1 Kas madde 3: uc sonumu MUTLAK kontrastla eslesir. Yeni yay sonumsuz olarak GERCEK yeni zemine (8x10 kirpimi; inceleme:
    duz renk kaynaksizdi) cizilir, cizilen yay (zemin cikarilmis) sirt kontrasti olculur -> plato; uc bolgesinde sonum = eski kontrast /
    yeni plato (en cok 1); kesis aramasi."""
    duz = dict(yol, sonum=np.where(np.asarray(yol["sonum"]) > 0, 1.0, 0.0))
    if zem is None:
        zem = np.full((3000, 2400, 3), (20, 28, 48), np.uint8)
    z = yay(zem, 1.0, 0, o, duz)[0]
    Pn = YO.sirt(fark_gri(z, zem), yol["cx"], yol["cy"], np.asarray(yol["r"]), bant=14.0, esik=25.0, tur=1, teget=0.0)
    plato = float(np.median(Pn[:, 4]))
    eski_plato = float(np.median(yol["P_kapi"][:, 4]))
    # uc duzeltmesi: kesis noktasi aramasi (0,25 derece adim, +-1 derece). Olculen uc kesisle dogrusal degismiyor (sonuk kuyrukta kontrast
    # esige yakin): her adayda duz zeminde ciz, iki ucu ayni yontemle olc, her uc icin eskiye en yakin kesis secilir.
    ue = YO.uclar(yol["P"], yol["bos"])
    aday = {}
    for d in np.arange(-1.0, 1.01, 0.25):
        bb = [(yol["bos"][0] + d) % 360, (yol["bos"][1] - d) % 360]         # d > 0: iki ucta da yay acikliga d derece uzar
        z = yay(zem, 1.0, 0, o, dict(yol, sonum=YO.uc_sonumu(yol["P_kapi"], bb, plato=plato)))[0]
        aday[round(float(d), 2)] = YO.uclar(YO.sirt(fark_gri(z, zem), yol["cx"], yol["cy"], np.asarray(yol["r"]), bant=14.0, esik=25.0, tur=1,
                                                    teget=0.0), yol["bos"])
    hata = lambda i, d: abs(((aday[d][i] - ue[i] + 180) % 360) - 180)       # noqa: E731
    d0 = min(aday, key=lambda d: (hata(0, d), abs(d))); d1 = min(aday, key=lambda d: (hata(1, d), abs(d)))
    bos2 = [round((yol["bos"][0] + d0) % 360, 2), round((yol["bos"][1] - d1) % 360, 2)]
    son = YO.uc_sonumu(yol["P_kapi"], bos2, plato=plato)
    return son, dict(yeni_plato=round(plato, 1), eski_plato=round(eski_plato, 1), uc_bolge_derece=YO.UC_BOLGE, aciklik_olcum=yol["bos"],
                     aciklik_cizim=bos2, uc_uzatma_derece=[d0, d1],
                     uc_eski=ue, uc_kalibre=[aday[d0][0], aday[d1][1]])


YAY_RENK_GRI = None   # main / uc_kalibre doldurur (o["yay"]["tepe_renk"] grisi)


def fark_gri(img, zem):
    """cizilen yay ORTUCULUGU x 255: (gri(cikti) - gri(yay oncesi zemin)) / (gri(yay rengi) - gri(zemin)) (yay cizimi out = zem + m x (renk -
    zem) x 0,92). Zemin yildizi / dokusu olcume girmez; parlak zemin noktasinin ustunde de yay ayni guclu olculur (fark yontemi orada
    sirti kaydiriyordu). Yay rengi tanimsizsa duz fark."""
    gz = YO.gri(zem); d = YO.gri(img) - gz
    if YAY_RENK_GRI is None:
        return np.clip(d, 0, None).astype(np.float32)
    return (np.clip(d / np.maximum(YAY_RENK_GRI - gz, 20.0), 0, 1.2) * 200.0).astype(np.float32)


def k2400(img, k, oy):
    """olcum 8x10 olceginde (@2400): 12x18 esit olcekle 2400 genislige indirilir (INTER_AREA), ofset oy / k (Merkez: 12x18'i 1,5'e bolerek)"""
    if k == 1:
        return img, oy
    H, W = img.shape[:2]
    return cv2.resize(img, (round(W / k), round(H / k)), interpolation=cv2.INTER_AREA), oy / k


KAPSAMA = 0.99      # eski sirt acilarinin en az %99'u yeni sirtta bulunmali; 1 dereceden uzun ardisik eksik blok FAIL (inceleme madde 1)
UC_ESIK = 0.5       # derece: her uc eski ucla en cok bu kadar farkli (madde 3; @2400 ~8 px)


def yay_kapisi(s8, son, yol, once8="", once12="", z8=None, z12=None):
    """YAY KAPISI (Denetim 20261101B, Serdar karar 1a): cikti yayi eski 8x10 yayindan ayni acida radyal; 8x10 en buyuk <= 1,5, medyan
    <= 0,5 px; 12x18 x 1,5 (12x18 cikti olcegi, olcum @2400'de yapilip x 1,5). Olcum CIZILEN katmanda (cikti - yay oncesi zemin; z8 / z12),
    tekil nokta ATILMAZ (tur 1), teget ortalama yok (dar sapma gizlenmez); kapsama >= %99 ve 1 dereceden uzun eksik blok yok; iki uc eski
    uclardan <= 0,5 derece. isilti / tepe yildizi sektorleri kapi disi (listelenir). once8 / once12: onceki cikti (f6078af3), tam goruntude,
    genis bant 60 px (bilgi; zemin cikarimi yok). -> (kapi, cizgiler @2400)"""
    kapi, cizgi = {}, {}
    ue = YO.uclar(yol["P"], yol["bos"])
    hedef = np.round(yol["P_kapi"][:, 0] * 4).astype(int)
    for ad, (img, zem, k_, oy_) in {"8x10": (s8, z8, 1.0, 0), "12x18": (son, z12, 1.5, 450)}.items():
        if img is None:
            continue
        im2, oy2 = k2400(img, k_, oy_)
        g = fark_gri(im2, k2400(zem, k_, oy_)[0]) if zem is not None else YO.gri(im2)
        dk = 0.5 / k_ - 0.5            # INTER_AREA kucultmede piksel merkezi kaymasi (k 1,5: -0,167 px); olcum kaymis merkezde, sonuc geri
        Pn = YO.sirt(g, yol["cx"] + dk, yol["cy"] + oy2 + dk, np.asarray(yol["r"]), k=1.0, bant=14.0, esik=25.0, tur=1, teget=0.0)
        Pn[:, 1] -= dk; Pn[:, 2] -= dk
        oz, fark = YO.kiyas(yol["P_kapi"], Pn, yol["cx"], yol["cy"], 1.0, oy2)
        px = {x: round(oz[x] * k_, 3) for x in ("medyan", "p95", "en_buyuk")}
        esik = {x: v * k_ for x, v in KAPI_8x10.items()}
        bulunan = set(np.round(fark[:, 0] * 4).astype(int).tolist()) if len(fark) else set()
        eksik = sorted(set(hedef.tolist()) - bulunan)
        blok, en_blok = 0, 0
        for i, e in enumerate(eksik):
            blok = blok + 1 if i and e == eksik[i - 1] + 1 else 1; en_blok = max(en_blok, blok)
        ub = YO.uclar(Pn, yol["bos"])
        fd = [round(((ub[i] - ue[i] + 180) % 360) - 180, 2) for i in (0, 1)]
        r_ort = float(np.median(yol["r"]))
        uc = dict(eski=ue, yeni=ub, fark_derece=fd, fark_cikti_px=[round(abs(x) * np.pi / 180 * r_ort * k_, 1) for x in fd])
        kap = round(1 - len(eksik) / max(1, len(hedef)), 4)
        kapi[ad] = dict(cikti_px=px, at2400=oz, esik_px=esik, kapsama=kap, en_uzun_eksik_derece=en_blok * 0.25, uclar=uc,
                        eksik_acilar=[e / 4 for e in eksik][:40],
                        haric_sektor=yol["isilti"],
                        en_kotu_acilar=[[round(a_, 2), round(f_ * k_, 2)] for a_, f_ in fark[np.argsort(-np.abs(fark[:, 1]))[:5]]],
                        pass_=bool(px["en_buyuk"] <= esik["en_buyuk"] and px["medyan"] <= esik["medyan"] and kap >= KAPSAMA and en_blok * 0.25 <= 1.0
                                   and all(abs(x) <= UC_ESIK for x in fd)))
        cizgi[ad] = Pn
    if once8 and once12:
        kapi["once"] = {}
        for ad, (yolp, k_, oy_) in {"8x10": (once8, 1.0, 0), "12x18": (once12, 1.5, 450)}.items():
            try:
                im2, oy2 = k2400(np.asarray(Image.open(yolp).convert("RGB")), k_, oy_)
                Pn = YO.sirt(YO.gri(im2), yol["cx"], yol["cy"] + oy2, np.asarray(yol["r"]), k=1.0, bant=60.0, esik=25.0, tur=2, teget=0.0)
                oz, fark = YO.kiyas(yol["P_kapi"], Pn, yol["cx"], yol["cy"], 1.0, oy2)
                kapi["once"][ad] = dict(cikti_px={x: round(oz[x] * k_, 3) for x in ("medyan", "p95", "en_buyuk")}, ortak_aci=oz["n"],
                                        uclar=YO.uclar(Pn, yol["bos"]), bant_px_2400=60,
                                        en_kotu_acilar=[[round(a_, 2), round(f_ * k_, 2)] for a_, f_ in fark[np.argsort(-np.abs(fark[:, 1]))[:5]]])
                cizgi["once_" + ad] = Pn
            except Exception as e:   # noqa: BLE001  (bilgi olcumu; uretimi dusurmez)
                kapi["once"][ad] = dict(hata=f"{type(e).__name__}: {str(e)[:150]}")
    else:
        kapi["once"] = dict(hata="onceki cikti verilmedi (--once-8x10 / --once-12x18)")
    return kapi, cizgi


def bindirme(img, P_eski, P_yeni, yol_):
    """BINDIRME_8x10: eski yay sirti KIRMIZI, yeni (cikti) sirti YESIL, 8x10 uzerinde (koyulastirilmis); ust: tum goruntu (cizgi 5 px, ayni
    yerde ust uste -> SARI); alt: 4 yakin plan x6 (sirt noktalari 1 px): sag uc ~40, sag yan ~15, sol uc ~140, sol yan ~200 derece."""
    H, W = img.shape[:2]
    base = (img.astype(np.float32) * 0.45).astype(np.uint8)

    def maske(P, kal):
        m = np.zeros((H, W), np.uint8)
        o = np.argsort(P[:, 0]); Q = P[o]
        kop = np.where(np.diff(Q[:, 0]) > 1.0)[0] + 1                   # buyuk aci boslugunda cizgi kopar (aciklik, isilti)
        for parca in np.split(Q, kop):
            if len(parca) > 1:
                cv2.polylines(m, [np.round(parca[:, 1:3] * 4).astype(np.int32)], False, 255, kal, cv2.LINE_AA, shift=2)
        return m > 0

    def boya(b, me, my):
        c = b.copy(); c[me, 0] = 255; c[my, 1] = 255
        c[me & ~my, 1:] //= 3; c[my & ~me, 0] //= 3; c[my & ~me, 2] //= 3
        return c
    ust = boya(base, maske(P_eski, 5), maske(P_yeni, 5))
    ince = boya(base, maske(P_eski, 1), maske(P_yeni, 1))
    yak = []
    for th in (40.0, 15.0, 140.0, 200.0):
        i = int(np.argmin(np.abs(((P_eski[:, 0] - th + 180) % 360) - 180)))
        x, y = int(P_eski[i, 1]), int(P_eski[i, 2])
        k = ince[max(0, y - 40):y + 40, max(0, x - 40):x + 40]
        yak.append(cv2.resize(k, (480, 480), interpolation=cv2.INTER_NEAREST))
    alt = np.concatenate(yak, 1)
    ust = cv2.resize(ust, (alt.shape[1], round(alt.shape[1] * H / W)), interpolation=cv2.INTER_AREA)
    Image.fromarray(np.concatenate([ust, alt], 0)).save(yol_, quality=92)


def yildiz_katmani(eski):
    """8x10 zeminden YALNIZ tepe yildizi (inceleme 31 Eki: medyan cikarimi cekirdegi bosaltiyor, eski yay / noktalar kopyalaniyordu, kutu
    kenari sert): yerel zemin = morfolojik acma (elips 45) + bulanik; isik = kirpim - zemin; eski yay bandi (isin disinda) sifirlanir;
    yalniz yildiz merkezine bagli parca (esik 20) alinir, 5 px genisletilip 2,5 px yumusatilir (kenarda 0)."""
    x0, y0, x1, y1 = YILDIZ
    p = eski[y0:y1, x0:x1].astype(np.float32)
    halka = np.r_[p[:6].reshape(-1, 3), p[-6:].reshape(-1, 3), p[:, :6].reshape(-1, 3), p[:, -6:].reshape(-1, 3)]
    zem = np.median(halka, 0)[None, None]                              # duz koyu lacivert (cekirdegi bosaltmaz; inceleme 31 Eki)
    isik = np.clip(p - zem, 0, 255)
    L = isik.max(2)
    cx, cy = YILDIZ_MERKEZ[0] - x0, YILDIZ_MERKEZ[1] - y0
    # eski yay bandi: her sutunda eski y 335-395 (yatay isinin ~300 altinda) en parlak satir, isin disinda 2. derece uydurma
    xs = np.arange(L.shape[1]); dis = np.abs(xs - cx) > 25
    r0, r1 = 335 - y0, 395 - y0
    ys = r0 + np.argmax(L[r0:r1], axis=0)
    c = np.polyfit(xs[dis], ys[dis], 2); ya = np.polyval(c, xs)
    yy = np.arange(L.shape[0])[:, None]
    bant = (np.abs(yy - ya[None]) <= 8) & (np.abs(xs - cx) > 9)[None]
    L2 = np.where(bant, 0, L)
    n, lab = cv2.connectedComponents((L2 > 45).astype(np.uint8), 8)        # 45: toz / nokta disarida (olcum 31 Eki)
    if lab[cy, cx] == 0:
        raise SystemExit("DUR: yildiz merkezi esigin altinda")
    m = (lab == lab[cy, cx]).astype(np.uint8)
    m = cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 2.5)
    m[:4] = m[-4:] = 0; m[:, :4] = m[:, -4:] = 0
    return isik * m[..., None], dict(zemin=[round(float(v), 1) for v in zem.ravel()], yay_bandi_polinom=[round(float(v), 6) for v in c], parca_px=int((lab == lab[cy, cx]).sum()))


def yildiz(img, k, oy, eski):
    x0, y0, x1, y1 = YILDIZ
    isik, bilgi = yildiz_katmani(eski)
    w, h = round((x1 - x0) * k), round((y1 - y0) * k)
    if k != 1:
        isik = cv2.resize(isik, (w, h), interpolation=cv2.INTER_CUBIC if k > 1 else cv2.INTER_AREA)
    X, Y = round(x0 * k), round(y0 * k + oy)
    out = img.astype(np.float32)
    out[Y:Y + h, X:X + w] = 255 - (255 - out[Y:Y + h, X:X + w]) * (255 - np.clip(isik, 0, 255)) / 255   # ekran karisimi
    return np.clip(out, 0, 255).astype(np.uint8), dict(kutu=[X, Y, X + w, Y + h], **bilgi)


def isilti_katmani(eski, merkez, yol, yari=ISILTI_YARI):
    """Serdar 1 Kas madde 2 (a): yay USTUNDEKI isilti yildizi, tepe yildiziyla ayni yontem: duz zemin (kirpim kenar halkasi medyani) cikarimi,
    yalniz isik katmani; eski yay ISIGI bant icinde (|r - r(aci)| <= 12 px) yildizdan uzak bant profilinin cikarimiyla atilir (isinlar
    korunur); esik 45 ile merkeze bagli parca (kirpim kenarina 12 px'ten yakinsa DUR), 5 px genisletme + 2,5 px yumusatma, kenarda 0.
    300 derecedeki "isilti" eski zeminde yildiz degil toz kumesidir (inceleme 1 Kas); Serdar karari 1a ile eklenir, raporda yazilir."""
    mx, my = merkez
    x0, y0, x1, y1 = mx - yari, my - yari, mx + yari, my + yari
    p = eski[y0:y1, x0:x1].astype(np.float32)
    halka = np.r_[p[:6].reshape(-1, 3), p[-6:].reshape(-1, 3), p[:, :6].reshape(-1, 3), p[:, -6:].reshape(-1, 3)]
    zem = np.median(halka, 0)[None, None]
    isik = np.clip(p - zem, 0, 255)
    L = isik.max(2)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    ang = (np.degrees(np.arctan2(yy - yol["cy"], xx - yol["cx"])) + 360) % 360
    d = np.hypot(xx - yol["cx"], yy - yol["cy"]) - YO.tablo_r(np.asarray(yol["r"]), ang)
    # eski yay ISIGI cikarilir (inceleme madde 3; sifirlama capraz isinlari koparip kesik birakiyordu): bant |d| <= 12 icin her tam
    # sayi uzaklikta, yildiz merkezinden > 45 px uzak bant piksellerinin medyan isigi (yay + noktali hale profili) cikarilir; isinlar kalir
    bant = np.abs(d) <= 12
    rr = np.hypot(xx - mx, yy - my); di = np.round(d).astype(int); uzak = rr > 45
    for dd in range(-12, 13):
        sec = bant & (di == dd) & (rr > 9)           # yildiz cekirdegi (9 px) korunur (yay isigi ciksa cekirdek esigin altina dusuyordu)
        ref = sec & uzak
        if ref.any():
            isik[sec] = np.clip(isik[sec] - np.median(isik[ref], 0)[None], 0, None)
    L = isik.max(2); L2 = L
    n, lab = cv2.connectedComponents((L2 > 45).astype(np.uint8), 8)
    if lab[yari, yari] == 0:
        raise SystemExit(f"DUR: isilti merkezi {merkez} esigin altinda")
    m = (lab == lab[yari, yari]).astype(np.uint8)
    ys_, xs_ = np.where(m > 0)
    if min(xs_.min(), ys_.min(), 2 * yari - 1 - xs_.max(), 2 * yari - 1 - ys_.max()) < 12:
        raise SystemExit(f"DUR: isilti {merkez} parcasi kirpim kenarina degiyor (duz kesik olur); ISILTI_YARI buyutulmeli")
    m = cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 2.5)
    m[:4] = m[-4:] = 0; m[:, :4] = m[:, -4:] = 0
    return isik * m[..., None], (x0, y0, x1, y1), dict(merkez=list(merkez), zemin=[round(float(v), 1) for v in zem.ravel()],
                                                       parca_px=int((lab == lab[yari, yari]).sum()))


def isiltilar(img, k, oy, eski, yol):
    """3 isilti katmani esit olcekle ayni yere, ekran karisimi (tepe yildizi ile ayni)."""
    out = img.astype(np.float32); bilgi = []
    for mz in ISILTI:
        isik, (x0, y0, x1, y1), b = isilti_katmani(eski, mz, yol)
        w, h = round((x1 - x0) * k), round((y1 - y0) * k)
        if k != 1:
            isik = cv2.resize(isik, (w, h), interpolation=cv2.INTER_CUBIC)
        X, Y = round(x0 * k), round(y0 * k + oy)
        out[Y:Y + h, X:X + w] = 255 - (255 - out[Y:Y + h, X:X + w]) * (255 - np.clip(isik, 0, 255)) / 255
        bilgi.append(dict(kutu=[X, Y, X + w, Y + h], **b))
    return np.clip(out, 0, 255).astype(np.uint8), bilgi


def isilti_yakin(eski, yeni, yol_):
    """ISILTI_YAKIN_8x10.jpg: her isilti icin eski (ust) / yeni (alt) 160x160 kirpim x3, yan yana."""
    sut = []
    for mx, my in ISILTI:
        a = eski[my - 80:my + 80, mx - 80:mx + 80]; b = yeni[my - 80:my + 80, mx - 80:mx + 80]
        sut.append(np.concatenate([cv2.resize(a, (480, 480), interpolation=cv2.INTER_NEAREST),
                                   np.full((12, 480, 3), 230, np.uint8), cv2.resize(b, (480, 480), interpolation=cv2.INTER_NEAREST)], 0))
        sut.append(np.full((972, 12, 3), 230, np.uint8))
    Image.fromarray(np.concatenate(sut[:-1], 1)).save(yol_, quality=92)


# ---------------------------------------------------------------- by_poster ogeleri
def by_poster(kod, scale, pair, n1, n2):
    os.environ.update(BY_ROOT=str(kod), PAIR=pair, NAME1=n1, NAME2=n2, DATE="12 JUNE 2025", HEADING="Paper Anniversary", LINE="",
                      SCALE=str(scale), STYLE="1", OUT="/tmp/_by_ornek3")
    spec = importlib.util.spec_from_file_location(f"by_poster_s{scale}", Path(kod, "kod", "by_poster.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    asil = m.gold_layer

    def gold_layer(tex, k=1.0):
        """by_poster.gold_layer ile ayni; YALNIZ doku ortalamasi SCALE'den bagimsiz (31 Eki olcum: by_poster float32
        'a.reshape(-1, 3).mean(0)' SCALE 2'de 28,8 M pikselde R ortalamasini 149 buluyor (SCALE 1: 231,6; float64 dogru deger 224,4)
        -> SCALE 2'de altin koyu / zeytin). Onayli 8x10 gorunumu icin SCALE 1'deki deger kullanilir. by_poster.py degistirilmedi."""
        t = np.array(Image.open(tex).convert("RGB"))
        if m.SCALE > 1:
            t = cv2.resize(t, None, fx=m.SCALE, fy=m.SCALE, interpolation=cv2.INTER_CUBIC)
        tile = np.concatenate([np.concatenate([t, t[:, ::-1]], 1), np.concatenate([t[::-1], t[::-1, ::-1]], 1)], 0)
        reps = (m.H // tile.shape[0] + 1, m.W // tile.shape[1] + 1, 1)
        a = np.tile(tile, reps)[:m.H, :m.W].astype(np.float32)
        low = cv2.GaussianBlur(a, (0, 0), m.P(60)) + 1e-3
        # ortalama, onayli 8x10 (SCALE 1) ciktisinin kullandigi degerin AYNISI: 2400x3000 dosemede by_poster'in float32 ortalamasi
        t1 = np.array(Image.open(tex).convert("RGB"))
        d1 = np.concatenate([np.concatenate([t1, t1[:, ::-1]], 1), np.concatenate([t1[::-1], t1[::-1, ::-1]], 1)], 0)
        a1 = np.tile(d1, (3000 // d1.shape[0] + 1, 2400 // d1.shape[1] + 1, 1))[:3000, :2400].astype(np.float32)
        mean = a1.reshape(-1, 3).mean(0)
        a = np.clip(a / low, 0.6, 1.6) * (0.75 * mean + 0.25 * low) * np.array(k if isinstance(k, tuple) else (k, k, k), np.float32)
        return np.clip(a, 0, 255)
    if scale == 1:
        g1, g2 = asil, gold_layer
        tx = f"{m.Z}/Altin_1024x1024/1_Starlit_Altin_1024.png"
        if np.abs(g1(tx) - g2(tx)).max() > 0.5:
            raise SystemExit("DUR: gold_layer kopyasi SCALE 1'de by_poster'dan farkli")
    m.gold_layer = gold_layer
    return m


def ogeler(bp, blok):
    """blok: HxW (by_poster W,H) zemin -> ogeler cizilmis hali"""
    bp.bgimg = lambda name: Image.fromarray(blok)
    return np.asarray(bp.starlit().convert("RGB"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kod", required=True); ap.add_argument("--zemin", required=True); ap.add_argument("--esrgan", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--pair", default="CANCER_LIBRA")
    ap.add_argument("--n1", default="EMMA"); ap.add_argument("--n2", default="JAMES")
    ap.add_argument("--esrgan-hazir", default="", help="onceden buyutulmus 3600x5400 zemin (yerel deneme)")
    ap.add_argument("--once-8x10", default="", help="ONCE olcumu: onceki STARLIT_8x10.jpg (koşu 41238698983)")
    ap.add_argument("--once-12x18", default="", help="ONCE olcumu: onceki STARLIT_12x18.jpg")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    kaynak = np.asarray(Image.open(a.zemin).convert("RGB"))
    if kaynak.shape[:2] != (3600, 2400):
        raise SystemExit(f"DUR: zemin kaynagi {kaynak.shape[1]}x{kaynak.shape[0]} (2400x3600 beklenir)")
    eski = np.asarray(Image.open(Path(a.kod, ESKI)).convert("RGB"))
    o = olc(eski)
    # Denetim 20261101B (Serdar 1 Kas "elips hatali"): yol eski 8x10 sirtindan 0,25 derecede (yay_olcum.eski_yol). f6078af3 yay_yolu sonuk
    # sag ucu (0-40 derece, kontrast < 80) kaciriyor, aciklik boyunca dogrusal ara degerle 10-16 px iceri ciziyordu; uclarin ice kivrimi
    # (40-45 / 130-145 derece, daireden 13-22 px) da kayboluyordu. Daire / elips ikisi de eski yola oturmuyor (rap["eski_yay_oturtma"]).
    yol = YO.eski_yol(eski, YOL_SEED)                      # yalniz yay bandi maskesi icin olcum (cizim yok)
    # Denetim 20261101C (Serdar 1 Kas: "orijinal yayi istiyorum"): yay eski 8x10'dan PIKSEL olarak (yay_orijinal.katman); kod cizimi,
    # profil, sonum, ayri tepe yildizi / isilti eklemesi YOK (isiltiler ve tepe yildizi yayla birlikte gelir)
    isik, maske, bilgi = YR.katman(eski, yol)
    rap = dict(olcum_8x10=o, kaynak=dict(boyut=[2400, 3600]), yay_yontem="eski 8x10 piksel isik katmani (yay_orijinal.py)", yay_katman=bilgi,
               yay_yolu=dict(merkez=[round(yol["cx"], 2), round(yol["cy"], 2)], bos=yol["bos"], isilti_sektor=yol["isilti"]))
    # yeni zeminde yay var mi (cift yay / eski yay izi): eski yol uzerinde sirt - 30..40 px halka, 0,5 derece kutular
    iz8 = YR.yay_izi(kaynak[300:3300], yol); iz_eski = YR.yay_izi(eski, yol)
    rap["yeni_zemin_yay_izi"] = dict(yeni_8x10_kirpim=iz8, eski_8x10=iz_eski, esik_medyan=IZ_ESIK, pass_=bool(iz8["medyan"] <= IZ_ESIK),
                                     not_="gri seviye; esik 5 ONERI (olcumden: eski yay 187, yaysiz vekil zemin -0,7)")
    # ---- 12x18
    if a.esrgan_hazir:
        z12 = np.asarray(Image.open(a.esrgan_hazir).convert("RGB")); s = 2
    else:
        z2, s = esrgan(kaynak, a.esrgan)
        z12 = cv2.resize(z2, (3600, 5400), interpolation=cv2.INTER_AREA)       # esit olcek (x ve y ayni oran)
        geri = cv2.resize(z2, (2400, 3600), interpolation=cv2.INTER_AREA).astype(np.float32)
        fe = np.abs(geri - kaynak.astype(np.float32)).max(2)
        rap["esrgan_kapi"] = dict(geri_ort_fark=round(float(fe.mean()), 3), geri_p999=round(float(np.percentile(fe, 99.9)), 2),
                                  not_="BILGI (engellemez); zemin dokusu yalniz, yay / sembol ESRGAN'dan gecmez")
        print("ESRGAN olcum", rap["esrgan_kapi"], flush=True)
    k, oy = 1.5, 450
    iz12 = YR.yay_izi(cv2.resize(z12[oy:oy + 4500], (2400, 3000), interpolation=cv2.INTER_AREA), yol)
    rap["yeni_zemin_yay_izi"]["yeni_12x18_blok_2400"] = iz12
    rap["yeni_zemin_yay_izi"]["pass_"] = bool(rap["yeni_zemin_yay_izi"]["pass_"] and iz12["medyan"] <= IZ_ESIK)
    z, rc = cerceve(z12, k, o); z12_once = z.copy()
    z, ry = YR.ekle(z, isik, k, oy)
    bp = by_poster(a.kod, BY_SCALE, a.pair, a.n1, a.n2)
    blok = z[oy:oy + 4500]
    buyuk = cv2.resize(blok, (2400 * BY_SCALE, 3000 * BY_SCALE), interpolation=cv2.INTER_LANCZOS4)
    ciz = cv2.resize(ogeler(bp, buyuk), (3600, 4500), interpolation=cv2.INTER_AREA)
    geri = cv2.resize(buyuk, (3600, 4500), interpolation=cv2.INTER_AREA)
    fark = (np.abs(ciz.astype(np.int16) - geri.astype(np.int16)).max(2) > 2).astype(np.float32)
    mk = cv2.GaussianBlur(cv2.dilate(fark, np.ones((5, 5), np.uint8)), (0, 0), 1.5)[..., None]
    son = z.copy()
    son[oy:oy + 4500] = np.clip(blok * (1 - mk) + ciz * mk, 0, 255).astype(np.uint8)
    ogem = cv2.dilate(fark.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    yay12 = cv2.resize(maske, (3600, 4500), interpolation=cv2.INTER_LINEAR) > 0.05
    kes12 = int((ogem & yay12).sum())                                  # KAPI: yay hicbir ogeye (8 px pay) degmez
    rap["12x18"] = dict(yay_oge_kesisim_px=kes12, boyut=[3600, 5400], esrgan_olcek=s, esit_olcek=k, dikey_ofset=oy, cerceve=rc, yay=ry,
                        oge_alani_px=int((fark > 0).sum()))
    # ---- 8x10 (ayni ayarlar, olcek 1, kayma 0)
    z8 = kaynak[300:3300].copy()
    z8, rc8 = cerceve(z8, 1.0, o); z8_once = z8.copy()
    z8, ry8 = YR.ekle(z8, isik, 1.0, 0)
    bp1 = by_poster(a.kod, 1, a.pair, a.n1, a.n2)
    s8 = ogeler(bp1, z8)
    oge8 = cv2.dilate((np.abs(s8.astype(np.int16) - z8.astype(np.int16)).max(2) > 2).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    kes8 = int((oge8 & (maske > 0.05)).sum())
    rap["8x10"] = dict(yay_oge_kesisim_px=kes8, boyut=[2400, 3000], kaynak_kirpim="satir 300:3300 (olcek yok)", cerceve=rc8, yay=ry8)
    # ---- KAPI (yay bandi = maske >= 0,5; oge pikselleri haric)
    B8 = (maske >= 0.5) & ~oge8
    L_eski = isik.max(2)
    L8 = (z8.astype(np.float32) - z8_once.astype(np.float32)).max(2)
    f8 = np.abs(L8 - L_eski)[B8]
    # 255'te kirpilan pikseller (yeni zemin yildizi + yay isigi > 255) kayma degil parlaklik siniri: kayma olcumunde iki goruntude de 0
    kirp8 = cv2.dilate(((z8_once.astype(np.float32) + isik) > 255.5).any(2).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    s8k = YR.kayma(np.where(kirp8, 0, L_eski), np.where(kirp8, 0, L8), B8)
    har = maske > 0.01
    Lb_e = np.clip(eski.astype(np.float32) - YR.yerel_zemin(eski, har | YR.parlak(eski)), 0, None).max(2)
    Lb_8 = np.clip(z8.astype(np.float32) - YR.yerel_zemin(z8, har | YR.parlak(z8)), 0, None).max(2)
    bant8 = (maske >= 0.5) & (np.abs(YR.geometri(3000, 2400, yol)[1]) <= 8)
    sb = YR.kayma(Lb_e * bant8, Lb_8 * bant8, bant8)
    k8 = dict(ort_mutlak_fark=round(float(f8.mean()), 3), p99=round(float(np.percentile(f8, 99)), 2), bant_px=int(B8.sum()),
              kirpilan_255_px=ry8["kirpilan_255_px"], kayma_disi_kirpik_px=int(kirp8.sum()),
              kayma_katman_max=round(float(max(max(abs(x[2]), abs(x[3])) for x in s8k)), 3) if s8k else None,
              kayma_bagimsiz_max=round(float(max(max(abs(x[2]), abs(x[3])) for x in sb)), 3) if sb else None,
              bagimsiz_ort_mutlak_fark=round(float(np.abs(Lb_8 - Lb_e)[B8].mean()), 3),
              bagimsiz_korelasyon=round(float(np.corrcoef(Lb_8[B8], Lb_e[B8])[0, 1]), 4),
              not_="katman: (cikti - yay oncesi zemin) ile eski isik katmani; bagimsiz: eski ve cikti ayni yerel zemin cikarimiyla "
                   "yeniden olculur (yeni zemin dokusu gurultusu dahil, BILGI); kayma: 24 pencere faz korelasyonu, px")
    k8["pass_"] = bool(k8["ort_mutlak_fark"] <= KAPI_FARK and k8["kayma_katman_max"] is not None and k8["kayma_katman_max"] < 0.5
                       and k8["kayma_bagimsiz_max"] is not None and k8["kayma_bagimsiz_max"] < 0.5)
    L12 = cv2.resize((son[oy:oy + 4500].astype(np.float32) - z12_once[oy:oy + 4500].astype(np.float32)), (2400, 3000),
                     interpolation=cv2.INTER_AREA).max(2)
    oge12_2400 = cv2.resize(ogem.astype(np.uint8), (2400, 3000), interpolation=cv2.INTER_NEAREST) > 0
    B12 = (maske >= 0.5) & ~oge12_2400
    kirp12 = ((z12_once[oy:oy + 4500].astype(np.float32) + np.clip(cv2.resize(isik, (3600, 4500), interpolation=cv2.INTER_LANCZOS4), 0, None))
              > 255.5).any(2).astype(np.uint8)
    kirp12 = cv2.dilate(cv2.resize(kirp12, (2400, 3000), interpolation=cv2.INTER_AREA), np.ones((7, 7), np.uint8)) > 0
    s12 = YR.kayma(np.where(kirp12, 0, L_eski), np.where(kirp12, 0, L12), B12)
    k12 = dict(korelasyon=round(float(np.corrcoef(L12[B12], L_eski[B12])[0, 1]), 5),
               ort_mutlak_fark_2400=round(float(np.abs(L12 - L_eski)[B12].mean()), 3), bant_px=int(B12.sum()),
               kirpilan_255_px=ry["kirpilan_255_px"],
               kayma_max_2400=round(float(max(max(abs(x[2]), abs(x[3])) for x in s12)), 3) if s12 else None,
               not_="12x18 cikti yay katmani (cikti - yay oncesi zemin) INTER_AREA ile 1/1,5 kucultulup eski isik katmaniyla kiyas")
    k12["pass_"] = bool(k12["korelasyon"] >= KAPI_KOR and k12["kayma_max_2400"] is not None and k12["kayma_max_2400"] <= KAPI_KAYMA12)
    rap["yay_kapi"] = {"8x10": k8, "12x18": k12, "esik": dict(fark_8x10=KAPI_FARK, kor_12x18=KAPI_KOR, kayma_12x18=KAPI_KAYMA12,
                                                                kayma_8x10="< 0,5 px (tam sayi 0)")}
    # ---- gorseller (gercek oran)
    Image.fromarray(son).save(out / "ORNEK3_12x18_v3.jpg", quality=95, subsampling=0, dpi=(300, 300))
    Image.fromarray(s8).save(out / "STARLIT_8x10_v3.jpg", quality=95, subsampling=0, dpi=(300, 300))
    h = 1500
    ey = Image.new("RGB", (2 * round(2400 * h / 3000) + 60, h + 40), (230, 230, 230))
    ey.paste(Image.fromarray(eski).resize((round(2400 * h / 3000), h), Image.LANCZOS), (20, 20))
    ey.paste(Image.fromarray(s8).resize((round(2400 * h / 3000), h), Image.LANCZOS), (round(2400 * h / 3000) + 40, 20))
    ey.save(out / "ESKI_YENI_8x10.jpg", quality=90)
    yakin_12x18(eski, son, yol, oy, out / "ESKI_YENI_12x18_YAKIN.jpg")
    a12 = Image.fromarray(son).resize((round(3600 * h / 5400), h), Image.LANCZOS)
    a8 = Image.fromarray(s8).resize((round(2400 * h / 3000), h), Image.LANCZOS)
    kt = Image.new("RGB", (a12.width + a8.width + 60, h + 40), (230, 230, 230)); kt.paste(a12, (20, 20)); kt.paste(a8, (a12.width + 40, 20))
    kt.save(out / "KONTAK_ORNEK3_v3.jpg", quality=88)
    kt.resize((kt.width * 450 // kt.height, 450), Image.LANCZOS).save(out / "ONIZLEME_KUCUK.jpg", quality=70)
    yk = k8["pass_"] and k12["pass_"] and rap["yeni_zemin_yay_izi"]["pass_"]
    rap["sonuc"] = "PASS" if kes12 == 0 and kes8 == 0 and yk else ("FAIL (yay kapisi)" if not yk else "FAIL (yay ogeye degiyor)")
    (out / "OLCUM.json").write_text(json.dumps(rap, indent=1, default=float), encoding="utf-8")
    print(json.dumps(rap, indent=1, default=float))
    return 0 if rap["sonuc"] == "PASS" else 1


def yakin_12x18(eski, son, yol, oy, yol_):
    """ESKI_YENI_12x18_YAKIN.jpg: ayni bolge; ust sira eski 8x10 x1,5 (Lanczos, yalniz gosterim), alt sira yeni 12x18 (gercek piksel).
    Bolgeler: tepe yildizi, sol uc, sag uc (uclar eski olculen bos acidan)."""
    yer = [(1197.0, 300.0)]
    for a_ in (yol["bos"][1], yol["bos"][0]):
        t = np.radians(a_); r = float(YO.tablo_r(np.asarray(yol["r"]), (a_ + (2.0 if a_ == yol["bos"][1] else -2.0)) % 360))
        yer.append((yol["cx"] + r * np.cos(t), yol["cy"] + r * np.sin(t)))
    yari = 140; sut = []
    for x, y in yer:
        x0, y0 = int(round(x)) - yari, int(round(y)) - yari
        e = cv2.resize(eski[y0:y0 + 2 * yari, x0:x0 + 2 * yari], (3 * yari, 3 * yari), interpolation=cv2.INTER_LANCZOS4)
        X0, Y0 = round(x0 * 1.5), round(y0 * 1.5) + oy
        n = son[Y0:Y0 + 3 * yari, X0:X0 + 3 * yari]
        sut.append(np.concatenate([e, np.full((10, 3 * yari, 3), 230, np.uint8), n], 0))
        sut.append(np.full((6 * yari + 10, 10, 3), 230, np.uint8))
    Image.fromarray(np.concatenate(sut[:-1], 1)).save(yol_, quality=92)

if __name__ == "__main__":
    sys.exit(main())
