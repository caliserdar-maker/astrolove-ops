#!/usr/bin/env python3
"""Denetim 20261101C (Serdar 1 Kas: "yay olmamis, orijinal yayi istiyorum"): yay KODLA CIZILMEZ; eski 8x10 zemindeki ORIJINAL yay
PIKSEL olarak alinir. Canva kontrolu (1 Kas): Starlit 2:3 tasariminda (DAHZk1niiMA s.2) yalniz zemin gorseli var, yay ayri oge degil;
8x10 Starlit Canva tasarimi bulunmadi; eski 8x10 / 5x7 zeminleri tek parca raster (yay gomulu).

Yontem (tepe yildizi yontemi, yay bandi maskesiyle):
  1) yerel zemin: eski 8x10'un normalize konvolusyonu (Gauss sigma ZEMIN_SIGMA), yay bandi (|d| <= HARIC_D), parlak noktalar ve yaya bagli
     parcalar disarida tutularak (zemin tahmini yay / isiltilardan beslenmez).
  2) isik katmani = max(0, eski - yerel zemin) (yalniz isik; tepe yildizi yontemi).
  3) maske = yay bandi (|d| <= BANT_TAM tam, BANT_SON'a kadar kosinus azalma; aciklikta UC_PAY derece pay) BIRLESIM yaya bagli parlak
     parcalar (isik > PARCA_ESIK, cekirdek |d| <= 3 ile kesisen bilesenler: yay ustu isiltiler ve tepe yildizi oldugu gibi; ayri ekleme yok),
     5 px genisletme + 2,5 px yumusatma (tepe yildizi yontemi). Yay ustu isilti sektorlerinde (+-2 derece, |d| <= 120) esik alti altin
     hale de alinir: agirlik = altin secimi (dR - dB), mavi zemin dokusu alinmaz.
  4) yeni zemine TOPLAMALI eklenir: 8x10 olcek 1 kayma 0; 12x18 yalniz esit oranli 1,5 (Lanczos), dikey ofset 450. AI yok, ayna / kopya yok.
d: piksel yaricapi - eski yay sirt tablosu r(aci) (yay_olcum.eski_yol; yalniz maske icin olcum, cizim yok)."""
import cv2
import numpy as np

import yay_olcum as YO

ZEMIN_SIGMA = 16.0     # px @2400: yerel zemin olcegi
HARIC_D = 24.0         # px: zemin tahmininden disarida tutulan yay bandi (olcum 1 Kas: radyal profil |d| >= 24'te zemine iner)
BANT_TAM = 16.0        # px: maske tam (cekirdek +-5, koyu halka +-8, noktali hale +-12..16)
BANT_SON = 22.0        # px: maske 0
UC_PAY = 1.5           # derece: yay uclarindan acikliga dogru maske payi (uc kesilmesin)
PARCA_ESIK = 45.0      # tepe yildizi yontemindeki esik (isik L2 > 45)
PARCA_YARICAP = 160.0  # px: yaya bagli parca aramasinin bant genisligi (isilti isinlari / tepe yildizi)
HALE_D = 120.0         # px: yay ustu isilti sektorlerinde (yay_olcum.isilti_sektorleri, +-HALE_PAY derece) altin hale bolgesi
HALE_PAY = 2.0
SICAK = (8.0, 16.0)    # altin secimi: w = clip((dR - dB - 8) / 16, 0, 1) (olcum 1 Kas: zemin dokusu dR-dB p99 9,6-14,5; tepe hale p90 16,3,
                       # 330 derece hale p90 109)


def geometri(H, W, yol, k=1.0, oy=0.0):
    """H x W tuvalde (olcek k, dikey ofset oy) eski yay yoluna gore aci ve isaretli uzaklik (px, @2400 olceginde)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x = (xx + 0.5) / k - 0.5; y = (yy - oy + 0.5) / k - 0.5
    ang = (np.degrees(np.arctan2(y - yol["cy"], x - yol["cx"])) + 360) % 360
    d = np.hypot(x - yol["cx"], y - yol["cy"]) - YO.tablo_r(np.asarray(yol["r"]), ang)
    return ang, d


def aciklikta(ang, bos, pay=0.0):
    b0, b1 = bos[0] + pay, bos[1] - pay
    return ((ang - b0) % 360) < ((b1 - b0) % 360)


def yerel_zemin(img, haric, sigma=ZEMIN_SIGMA):
    """normalize konvolusyon: haric (bool) pikseller zemin tahminine girmez."""
    w = (~haric).astype(np.float32)
    ws = cv2.GaussianBlur(w, (0, 0), sigma)
    a = img.astype(np.float32)
    z = np.stack([cv2.GaussianBlur(a[..., c] * w, (0, 0), sigma) for c in range(3)], -1) / np.maximum(ws, 1e-4)[..., None]
    # cok genis harici bolgede (ws ~ 0) daha genis olcek
    zz = np.stack([cv2.GaussianBlur(a[..., c] * w, (0, 0), sigma * 4) for c in range(3)], -1) / np.maximum(
        cv2.GaussianBlur(w, (0, 0), sigma * 4), 1e-4)[..., None]
    t = np.clip(ws / 0.05, 0, 1)[..., None]
    return z * t + zz * (1 - t)


def parlak(img, esik=20.0):
    g = img.astype(np.float32).mean(2)
    return cv2.dilate(((g - cv2.GaussianBlur(g, (0, 0), 12)) > esik).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0


def katman(eski, yol):
    """eski 8x10 (2400x3000) -> (isik katmani float32 HxWx3, maske HxW 0..1, bilgi)."""
    H, W = eski.shape[:2]
    ang, d = geometri(H, W, yol)
    acik = aciklikta(ang, yol["bos"], UC_PAY)
    cekirdek = (np.abs(d) <= 3) & ~aciklikta(ang, yol["bos"])
    # yaya bagli parlak parcalar (ilk tahmin: duz zemin)
    z0 = yerel_zemin(eski, ((np.abs(d) <= HARIC_D) & ~acik) | parlak(eski))
    L0 = np.clip(eski - z0, 0, None).max(2)
    yakin = np.abs(d) <= PARCA_YARICAP
    n, lab = cv2.connectedComponents(((L0 > PARCA_ESIK) & yakin).astype(np.uint8), 8)
    ids = np.unique(lab[cekirdek & (lab > 0)])
    parca = np.isin(lab, ids) & (lab > 0)
    # son zemin: bant + parcalar (genisletilmis) + parlak noktalar haric
    haric = ((np.abs(d) <= HARIC_D) & ~acik) | cv2.dilate(parca.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool) | parlak(eski)
    z = yerel_zemin(eski, haric)
    isik = np.clip(eski.astype(np.float32) - z, 0, None)
    # maske
    ad = np.abs(d)
    bant = np.where(ad <= BANT_TAM, 1.0, np.where(ad >= BANT_SON, 0.0, 0.5 * (1 + np.cos(np.pi * (ad - BANT_TAM) / (BANT_SON - BANT_TAM)))))
    bant = (bant * ~acik).astype(np.float32)
    pm = cv2.GaussianBlur(cv2.dilate(parca.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 2.5)
    # isilti / tepe yildizi altin halesi (esigin altindaki toz ve parilti): yalniz olculen isilti sektorlerinde, yalniz altin isik
    pad = [(a - HALE_PAY, b + HALE_PAY) for a, b in yol["isilti"]]
    sek = YO.sektorde(ang.ravel(), pad).reshape(H, W) & (np.abs(d) <= HALE_D)
    sek = cv2.GaussianBlur(sek.astype(np.float32), (0, 0), 8.0)
    sicak = np.clip((isik[..., 0] - isik[..., 2] - SICAK[0]) / SICAK[1], 0, 1)
    m = np.maximum(np.maximum(bant, pm), sek * sicak)
    m[:4] = m[-4:] = 0; m[:, :4] = m[:, -4:] = 0
    # aciklik ici kalan bantsiz parca var mi (uc payi disinda yaya bagli olmayan) -> bilgi
    bilgi = dict(parca_sayisi=int(len(ids)), parca_px=int(parca.sum()), maske_px=int((m > 0.01).sum()),
                 zemin_sigma=ZEMIN_SIGMA, bant=[BANT_TAM, BANT_SON], uc_pay_derece=UC_PAY, parca_esik=PARCA_ESIK,
                 hale=dict(d=HALE_D, pay=HALE_PAY, sicak=list(SICAK), sektor=[list(map(float, x)) for x in yol["isilti"]]))
    return isik * m[..., None], m, bilgi


def ekle(img, isik, k=1.0, oy=0):
    """toplamali ekleme; k != 1 yalniz esit oranli Lanczos (x ve y ayni oran)."""
    if k != 1:
        h, w = isik.shape[:2]
        isik = np.clip(cv2.resize(isik, (round(w * k), round(h * k)), interpolation=cv2.INTER_LANCZOS4), 0, None)
    h, w = isik.shape[:2]
    out = img.astype(np.float32)
    out[oy:oy + h, :w] += isik
    kirp = int(((out[oy:oy + h, :w]) > 255.5).any(2).sum())
    return np.clip(np.round(out), 0, 255).astype(np.uint8), dict(olcek=k, dikey_ofset=oy, kirpilan_255_px=kirp)


def yay_izi(zem8, yol):
    """yeni zeminde (8x10 kirpim) eski yol uzerinde yay var mi: aci basina [g(|d|<=2) ort - g(30<=|d|<=40) ort], aciklik / isilti disi medyan."""
    H, W = zem8.shape[:2]
    ang, d = geometri(H, W, yol)
    g = zem8.astype(np.float32).mean(2)
    ok = ~aciklikta(ang, yol["bos"]) & ~YO.sektorde(ang.ravel(), yol["isilti"]).reshape(H, W)
    a = np.floor(ang * 2).astype(int)                 # 0,5 derece kutular
    ic = ok & (np.abs(d) <= 2); dis = ok & (np.abs(d) >= 30) & (np.abs(d) <= 40)
    si = np.bincount(a[ic], g[ic], 720); ni = np.bincount(a[ic], None, 720)
    sd = np.bincount(a[dis], g[dis], 720); nd = np.bincount(a[dis], None, 720)
    v = (ni > 0) & (nd > 0)
    k = si[v] / ni[v] - sd[v] / nd[v]
    return dict(medyan=round(float(np.median(k)), 2), p90=round(float(np.percentile(k, 90)), 2), kutu=int(v.sum()))


def kayma(a, b, m, pencere=256):
    """yay boyunca pencerelerde alt-piksel faz korelasyonu (a'ya gore b kaymasi), px. m: bant maskesi (bool)."""
    ys, xs = np.where(m)
    H, W = a.shape[:2]
    hn = np.outer(np.hanning(pencere), np.hanning(pencere)).astype(np.float32)
    sonuc = []
    for t in np.linspace(0, len(ys) - 1, 24).astype(int):
        y0 = int(np.clip(ys[t] - pencere // 2, 0, H - pencere)); x0 = int(np.clip(xs[t] - pencere // 2, 0, W - pencere))
        pa = a[y0:y0 + pencere, x0:x0 + pencere].astype(np.float32); pb = b[y0:y0 + pencere, x0:x0 + pencere].astype(np.float32)
        if pa.std() < 1 or pb.std() < 1:
            continue
        (dx, dy), r = cv2.phaseCorrelate(pa, pb, hn)
        sonuc.append((x0 + pencere // 2, y0 + pencere // 2, float(dx), float(dy), float(r)))
    return sonuc
