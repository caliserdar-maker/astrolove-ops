#!/usr/bin/env python3
"""kart_cila_kur.py ciktilari icin tek QC (PASS/FAIL, her kart).
 - boyut 3000x2250
 - poster NCC >= 0.99: iki tarafta sigma1 Gauss, kenardan 30 px ic, +-3 px hiza taramasi (kapak_v8_kur.py yontemi)
 - aciklikta beyaz kalinti 0 px: cikti (min>238 & chroma<12) VE beklenen posterde o piksel beyaz degil,
   binary_opening 3x3 (Pure White posterin kendi kagit beyazi kalinti sayilmaz)
 - sahnenin aciklik disi pikselleri girdiyle birebir: kayipsiz kontrol PNG'sinde, panel maskesi ici, fark 0
   (JPEG kodlama farki ayrica raporlanir)
 - aciklik dikdortgen: doluluk >= 0.99, kenar sapmasi <= 1 px (homografi gerekmez)
 - zemin RGB 237,232,226 +-2 (3 nokta); metinlerde uzun/orta tire yok; poster kirpimi <= %3
 - alt yazi: satir sayisi = metin sayisi, satirlar arasi bosluk >= 20 px (koyu piksel bantlari)
 - poster renk sinifi (kaynak dosya/kirpim kutusu dogru mu): NCC kaynagin kendisine olculdugu icin yanlis
   kaynak NCC'yi dusurmez (28 Eyl 1. kosu: sembol karti palet sanildi); MB koyu mavi, DB koyu notr, PW/CI acik
 - acik serit yok (Serdar 28 Eyl): gorunen poster kenarinin 1-5 px disindaki halkada hicbir piksel, 3 px iceride
   poster kenar tonundan VE cerceve tonundan +12'den fazla parlak degil (4 kenar, orta %90); halka ilk cerceve
   pikselinde kesilir (kalici olcut, Serdar 28 Eyl; ayrinti serit())
Kullanim: kart_cila_qc.py CIKIS_KLASORU KONTROL_KLASORU SAHNE_KLASORU BASKI_11x14.jpg CANLI_04.jpg [ONAYLI=06,10,11]
  ONAYLI: v2 geometrisiyle (genisletmesiz) kurulmus onayli kartlar; ayni kurallarla olculur
"""
import os
import re
import sys
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kart_cila_kur import (BG, KARTLAR, cerceve, SAHNE_DOSYA, SX, aciklik, ic_golge, panel_maske, poster_hazirla, sahne_isle,
                           yerlesim)

CIK, KON, SAH, BASKI, C04 = sys.argv[1:6]
ONAYLI = set(sys.argv[6].split(',')) if len(sys.argv) > 6 and sys.argv[6] else set()


def ncc(p, q):
    p = p - p.mean(); q = q - q.mean(); return float((p * q).sum() / np.sqrt((p * p).sum() * (q * q).sum()))


RENK = {  # kart: (ad, kosul(ortalama parlaklik, R, G, B))
    '06': ('Midnight Blue', lambda m, r, g, b: m < 90 and b > r + 5),
    '09': ('Champagne Ivory', lambda m, r, g, b: m > 150 and r > b + 5),
    '10': ('Deep Black', lambda m, r, g, b: m < 70 and abs(b - r) < 20),
    '11': ('Pure White', lambda m, r, g, b: m > 200),
}


def serit(R, V, SY):
    """Gorunen poster dikdortgeni V (panel) etrafinda acik serit: {kenar: (ihlal px, en buyuk asim)}.
    KALICI OLCUT (Serdar 28 Eyl kabul): her satir/sutunda halka = poster kenarinin 1-5 px disi, ILK CERCEVE
    PIKSELINDE (kart_cila_kur.cerceve) kesilir; serit poster ile cerceve ARASINDADIR, cercevenin kendi pahi/parlak
    cizgisi serit degildir. Ihlal: halka pikseli > max(3 px iceride poster tonu, cercevenin 3 px icindeki ton) + 12.
    (Kesilmeyen sabit 1-5 px halka koyu posterlerde cerceve profilini olcup onayli 06/10'u da FAIL veriyordu.)"""
    L = R.astype(np.float32).mean(2); C = cerceve(R)
    x0, y0, x1, y1 = V[0] + SX, V[1] + SY, V[2] + SX, V[3] + SY      # [x0,x1) x [y0,y1)
    iy = range(y0 + (y1 - y0) // 20, y1 - (y1 - y0) // 20); ix = range(x0 + (x1 - x0) // 20, x1 - (x1 - x0) // 20)
    kenarlar = {  # disa dogru dizi (0 = poster kenarinin 1 px disi), 3 px iceride poster tonu
        'sol': lambda i: (L[i, x0 - 1:x0 - 16:-1], C[i, x0 - 1:x0 - 16:-1], L[i, x0 + 2]),
        'sag': lambda i: (L[i, x1:x1 + 15], C[i, x1:x1 + 15], L[i, x1 - 3]),
        'ust': lambda i: (L[y0 - 1:y0 - 16:-1, i], C[y0 - 1:y0 - 16:-1, i], L[y0 + 2, i]),
        'alt': lambda i: (L[y1:y1 + 15, i], C[y1:y1 + 15, i], L[y1 - 3, i]),
    }
    sonuc = {}
    for ad, f in kenarlar.items():
        ihlal, asim = 0, -999.0
        for i in (iy if ad in ('sol', 'sag') else ix):
            dizi, cer, p = f(i)
            j = np.flatnonzero(cer); j = int(j[0]) if len(j) else 5
            halka, c = dizi[:min(j, 5)], dizi[min(j + 2, 14)]
            if len(halka):
                a_ = halka - (max(p, c) + 12)
                ihlal += int((a_ > 0).sum()); asim = max(asim, float(a_.max()))
        sonuc[ad] = (ihlal, round(asim, 1))
    return sonuc


def beyaz(a):
    return (a.min(2) > 238) & ((a.max(2) - a.min(2)) < 12)


hepsi = True
for kart, K in KARTLAR.items():
    R = np.asarray(Image.open(os.path.join(CIK, K['ad'] + '.jpg')).convert('RGB')).astype(np.int16)
    Q = np.asarray(Image.open(os.path.join(KON, K['ad'] + '.png')).convert('RGB')).astype(np.int16)
    G = Image.open(os.path.join(SAH, SAHNE_DOSYA[kart])).convert('RGB')
    kutu, dolu, sapma = aciklik(G)
    sahne, s = sahne_isle(G)
    px_, py_, W, H, pay, MA, V, uzanti = yerlesim(sahne, kutu, s, genislet=kart not in ONAYLI)
    poster, kirp, kirp_eks = poster_hazirla(kart, BASKI if K['poster'] == 'baski' else C04, W, H)
    SY = K['SY']; ox, oy = SX + px_, SY + py_
    X0, Y0, X1, Y1 = V

    # NCC
    P = cv2.GaussianBlur(np.asarray(poster).astype(np.float32)[30:-30, 30:-30].mean(2), (0, 0), 1.0)
    Rg = cv2.GaussianBlur(R.astype(np.float32).mean(2), (0, 0), 1.0)
    n = max(ncc(Rg[oy + 30 + dy:oy + 30 + dy + P.shape[0], ox + 30 + dx:ox + 30 + dx + P.shape[1]], P)
            for dy in range(-3, 4) for dx in range(-3, 4))

    pr, pg, pb = np.asarray(poster).astype(np.float32).reshape(-1, 3).mean(0)
    renk_ok = RENK[kart][1]((pr + pg + pb) / 3, pr, pg, pb)

    # beyaz kalinti (aciklik ici)
    bek = np.asarray(ic_golge(poster, pay)).astype(np.int16)[pay:pay + Y1 - Y0, pay:pay + X1 - X0]
    ref_beyaz = ndi.binary_dilation(beyaz(bek), iterations=2)
    gor = R[SY + Y0:SY + Y1, SX + X0:SX + X1]                          # gorunen poster alani
    kal = ndi.binary_opening(beyaz(gor) & ~ref_beyaz, structure=np.ones((3, 3)))
    kalinti = int(kal.sum())
    ham_beyaz = int(ndi.binary_opening(beyaz(gor), structure=np.ones((3, 3))).sum())
    # gorunen posterin 3 px disindaki halkada beyaz (bilgi)
    halka = np.zeros(R.shape[:2], bool); halka[SY + Y0 - 3:SY + Y1 + 3, SX + X0 - 3:SX + X1 + 3] = True
    halka[SY + Y0:SY + Y1, SX + X0:SX + X1] = False
    sr = serit(R, V, SY)
    serit_ok = all(v[0] == 0 for v in sr.values())
    halka_beyaz = int((beyaz(R) & halka).sum())

    # aciklik disi birebir (kayipsiz kopya, panel maskesi ici)
    S = np.asarray(sahne).astype(np.int16)
    M = np.asarray(panel_maske(sahne.size)) == 255
    M &= ~MA
    fark = np.abs(Q[SY:SY + S.shape[0], SX:SX + S.shape[1]] - S)[M]
    birebir = int(fark.max())
    jpg_fark = float(np.abs(R[SY:SY + S.shape[0], SX:SX + S.shape[1]] - S)[M].mean())

    zemin = all(int(np.abs(R[y, x] - np.array(BG)).max()) <= 2 for x, y in [(60, 1000), (2950, 1000), (60, 2080)])
    metin = ' '.join([K['baslik'], K['alt']] + [t for t, *_ in K['satirlar']])
    tire = bool(re.search(r'[‒-―−]', metin))
    alt = SY + sahne.size[1] + max(s_[3] for s_ in K['satirlar']) + 40
    bolge = R[SY + sahne.size[1] + 10:2120, 300:2700].mean(2) < 150
    satir_var = bolge.any(1).astype(np.int8)
    bas = np.flatnonzero(np.diff(np.r_[0, satir_var]) == 1); son = np.flatnonzero(np.diff(np.r_[satir_var, 0]) == -1)
    bosluk = int((bas[1:] - son[:-1] - 1).min()) if len(bas) > 1 else 999
    yazi_ok = len(bas) == len(K['satirlar']) and bosluk >= 20

    ok = (R.shape[:2] == (2250, 3000) and n >= 0.99 and kalinti == 0 and birebir == 0 and zemin and not tire
          and kirp_eks <= 0.03 and dolu >= 0.99 and sapma <= 1 and alt < 2130 and renk_ok and yazi_ok and serit_ok)
    hepsi &= ok
    print(f"{K['ad']}{' (onayli v2)' if kart in ONAYLI else ''}: boyut {R.shape[1]}x{R.shape[0]} | aciklik girdi {kutu} dolu {dolu:.4f} kenar sapma {sapma} px oran "
          f"{(kutu[2] - kutu[0] + 1) / (kutu[3] - kutu[1] + 1):.4f} -> panel {X1 - X0}x{Y1 - Y0} | kirpim eksen %{kirp_eks * 100:.2f} "
          f"| poster {RENK[kart][0]} RGB {pr:.0f},{pg:.0f},{pb:.0f} {'ok' if renk_ok else 'YANLIS'} | NCC {n:.4f} | kalinti {kalinti} px (ham beyaz {ham_beyaz}, halka {halka_beyaz}) | disari fark {birebir} "
          f"(jpg ort {jpg_fark:.2f}) | zemin {zemin} | tire {tire} | yazi alt ~{alt} satir {len(bas)} bosluk {bosluk} px | serit {' '.join(f'{k} {v[0]}/{v[1]}' for k, v in sr.items())} | uzanti {uzanti} | {'PASS' if ok else 'FAIL'}")
print('GENEL', 'PASS' if hepsi else 'FAIL')
sys.exit(0 if hepsi else 1)
