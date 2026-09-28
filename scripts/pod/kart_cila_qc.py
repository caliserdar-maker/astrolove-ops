#!/usr/bin/env python3
"""kart_cila_kur.py ciktilari icin tek QC (PASS/FAIL, her kart).
 - boyut 3000x2250
 - poster NCC >= 0.99: iki tarafta sigma1 Gauss, kenardan 30 px ic, +-3 px hiza taramasi (kapak_v8_kur.py yontemi)
 - aciklikta beyaz kalinti 0 px: cikti (min>238 & chroma<12) VE beklenen posterde o piksel beyaz degil,
   binary_opening 3x3 (Pure White posterin kendi kagit beyazi kalinti sayilmaz)
 - sahnenin aciklik disi pikselleri girdiyle birebir: kayipsiz kontrol PNG'sinde, panel maskesi ici, fark 0
   (JPEG kodlama farki ayrica raporlanir)
 - zemin RGB 237,232,226 +-2 (3 nokta); metinlerde uzun/orta tire yok; poster kirpimi <= %3
 - poster renk sinifi (kaynak dosya/kirpim kutusu dogru mu): NCC kaynagin kendisine olculdugu icin yanlis
   kaynak NCC'yi dusurmez (28 Eyl 1. kosu: sembol karti palet sanildi); MB koyu mavi, DB koyu notr, PW/CI acik
Kullanim: kart_cila_qc.py CIKIS_KLASORU KONTROL_KLASORU SAHNE_KLASORU BASKI_11x14.jpg CANLI_04.jpg
"""
import os
import re
import sys
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kart_cila_kur import (BG, KARTLAR, SAHNE_DOSYA, SX, aciklik, ic_golge, panel_aciklik, panel_maske,
                           poster_hazirla, sahne_isle)

CIK, KON, SAH, BASKI, C04 = sys.argv[1:6]


def ncc(p, q):
    p = p - p.mean(); q = q - q.mean(); return float((p * q).sum() / np.sqrt((p * p).sum() * (q * q).sum()))


RENK = {  # kart: (ad, kosul(ortalama parlaklik, R, G, B))
    '06': ('Midnight Blue', lambda m, r, g, b: m < 90 and b > r + 5),
    '09': ('Champagne Ivory', lambda m, r, g, b: m > 150 and r > b + 5),
    '10': ('Deep Black', lambda m, r, g, b: m < 70 and abs(b - r) < 20),
    '11': ('Pure White', lambda m, r, g, b: m > 200),
}


def beyaz(a):
    return (a.min(2) > 238) & ((a.max(2) - a.min(2)) < 12)


hepsi = True
for kart, K in KARTLAR.items():
    R = np.asarray(Image.open(os.path.join(CIK, K['ad'] + '.jpg')).convert('RGB')).astype(np.int16)
    Q = np.asarray(Image.open(os.path.join(KON, K['ad'] + '.png')).convert('RGB')).astype(np.int16)
    G = Image.open(os.path.join(SAH, SAHNE_DOSYA[kart])).convert('RGB')
    kutu, dolu = aciklik(G)
    sahne, s = sahne_isle(G)
    X0, Y0, X1, Y1 = panel_aciklik(kutu, s)
    poster, kirp, kirp_eks = poster_hazirla(kart, BASKI if K['poster'] == 'baski' else C04, X1 - X0, Y1 - Y0)
    SY = K['SY']; ox, oy = SX + X0, SY + Y0

    # NCC
    P = cv2.GaussianBlur(np.asarray(poster).astype(np.float32)[30:-30, 30:-30].mean(2), (0, 0), 1.0)
    Rg = cv2.GaussianBlur(R.astype(np.float32).mean(2), (0, 0), 1.0)
    n = max(ncc(Rg[oy + 30 + dy:oy + 30 + dy + P.shape[0], ox + 30 + dx:ox + 30 + dx + P.shape[1]], P)
            for dy in range(-3, 4) for dx in range(-3, 4))

    pr, pg, pb = np.asarray(poster).astype(np.float32).reshape(-1, 3).mean(0)
    renk_ok = RENK[kart][1]((pr + pg + pb) / 3, pr, pg, pb)

    # beyaz kalinti (aciklik ici)
    bek = np.asarray(ic_golge(poster)).astype(np.int16)
    ref_beyaz = ndi.binary_dilation(beyaz(bek), iterations=2)
    kal = ndi.binary_opening(beyaz(R[oy:SY + Y1, ox:SX + X1]) & ~ref_beyaz, structure=np.ones((3, 3)))
    kalinti = int(kal.sum())
    ham_beyaz = int(ndi.binary_opening(beyaz(R[oy:SY + Y1, ox:SX + X1]), structure=np.ones((3, 3))).sum())
    # acikligin 3 px disindaki halkada beyaz (bilgi)
    halka = np.zeros(R.shape[:2], bool); halka[oy - 3:SY + Y1 + 3, ox - 3:SX + X1 + 3] = True
    halka[oy:SY + Y1, ox:SX + X1] = False
    halka_beyaz = int((beyaz(R) & halka).sum())

    # aciklik disi birebir (kayipsiz kopya, panel maskesi ici)
    S = np.asarray(sahne).astype(np.int16)
    M = np.asarray(panel_maske(sahne.size)) == 255
    M[Y0:Y1, X0:X1] = False
    fark = np.abs(Q[SY:SY + S.shape[0], SX:SX + S.shape[1]] - S)[M]
    birebir = int(fark.max())
    jpg_fark = float(np.abs(R[SY:SY + S.shape[0], SX:SX + S.shape[1]] - S)[M].mean())

    zemin = all(int(np.abs(R[y, x] - np.array(BG)).max()) <= 2 for x, y in [(60, 1000), (2950, 1000), (60, 2080)])
    metin = ' '.join([K['baslik'], K['alt']] + [t for t, *_ in K['satirlar']])
    tire = bool(re.search(r'[‒-―−]', metin))
    alt = SY + sahne.size[1] + max(dy for *_, dy in K['satirlar']) + 40

    ok = (R.shape[:2] == (2250, 3000) and n >= 0.99 and kalinti == 0 and birebir == 0 and zemin and not tire
          and kirp_eks <= 0.03 and dolu == 1.0 and alt < 2130 and renk_ok)
    hepsi &= ok
    print(f"{K['ad']}: boyut {R.shape[1]}x{R.shape[0]} | aciklik girdi {kutu} dolu {dolu:.3f} oran "
          f"{(kutu[2] - kutu[0] + 1) / (kutu[3] - kutu[1] + 1):.4f} -> panel {X1 - X0}x{Y1 - Y0} | kirpim eksen %{kirp_eks * 100:.2f} "
          f"| poster {RENK[kart][0]} RGB {pr:.0f},{pg:.0f},{pb:.0f} {'ok' if renk_ok else 'YANLIS'} | NCC {n:.4f} | kalinti {kalinti} px (ham beyaz {ham_beyaz}, halka {halka_beyaz}) | disari fark {birebir} "
          f"(jpg ort {jpg_fark:.2f}) | zemin {zemin} | tire {tire} | yazi alt ~{alt} | {'PASS' if ok else 'FAIL'}")
print('GENEL', 'PASS' if hepsi else 'FAIL')
sys.exit(0 if hepsi else 1)
