#!/usr/bin/env python3
"""BIZIM YILIMIZ (Paper) ornek son islem (13 Eki 2026, Serdar onayli Adim 1). Etsy / musteri YOK.

Tek 8x10 (2400x3000) girdi icin:
  1) eski yol (CI / WP): tarih satiri ekler. Konum ve renk ayni goruntuden olculur:
     - satir 1 (eski yolun bastigi tagline) tabani = alt yazi bandindaki murekkep sutun alt uclarinin MODU
     - satir 2 tabani = satir 1 tabani + 105 px (sartname: 2630 -> 2735), ortali (x 1200)
     - Cinzel 500 buyuk harf, 46 px, harf araligi 10 px (sartname); cizim yeni yolun tarih_ciz() ile ayni
     - renk: eski yolun bastigi ISIMLERIN satir medyan RGB profili, harf yuksekligine gerilir (pilot3/12 altin_isim yontemi)
  2) kart: 8x10 yukseklige olceklenir (2100) ve yanlardan kirpilir -> 1500x2100 (5x7 @300 dpi); kenar payi olculur
  3) kesit: isim satirindan tarih satirina 1:1 yakin plan
  4) metin kapisi: kesitte OCR (tesseract) isimler + satir 1 + satir 2; benzerlik >= 0.85 PASS

Kullanim:
  paper_son.py --girdi X_8x10.jpg --cikti DIR --ad AstroLoveArt_Cancer_Libra_Midnight_Blue --tur poster|kart
               --font CINZEL.ttf [--tarih-ekle "YEAR ONE · 12 JUNE 2025"] --bekle "SERDAR|LENA|Paper Anniversary|YEAR ONE 12 JUNE 2025"
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
W8, H8 = 2400, 3000
KART = (1500, 2100)
TARIH_PX, TARIH_ARALIK, SATIR_ARA = 46, 10, 105   # sartname, 8x10 olcusu


def tarih_ciz(metin, punto, aralik, font, wght=500):
    """motor_gpt/olustur_alfa_sablon.tarih_ciz ile ayni cizim (karakter karakter, sabit harf araligi)."""
    F = ImageFont.truetype(font, punto)
    try:
        F.set_variation_by_axes([wght])
    except Exception:
        pass
    il = [F.getlength(ch) for ch in metin]
    asc, desc = F.getmetrics()
    im = Image.new('L', (int(sum(il) + aralik * (len(metin) - 1)) + 4 * punto, asc + desc + 2 * punto), 0)
    dr = ImageDraw.Draw(im)
    x, taban = 2 * punto, asc + punto
    for ch, w_ in zip(metin, il):
        dr.text((x, taban), ch, font=F, fill=255, anchor='ls')
        x += w_ + aralik
    a = np.asarray(im).astype(np.float32) / 255
    ys, xs = np.nonzero(a > 0.5)
    return a, xs.min(), xs.max() + 1, taban


def koyu_murekkep(P):
    """Eski yol (CI / WP): ogeler zeminden koyu. Yerel zemin = L medyani (buyuk pencere)."""
    L = cv2.cvtColor(P, cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32)
    k = 4
    kucuk = cv2.resize(L, (L.shape[1] // k, L.shape[0] // k), interpolation=cv2.INTER_AREA)
    bg = cv2.resize(cv2.medianBlur(kucuk.astype(np.uint8), 31).astype(np.float32), (L.shape[1], L.shape[0]), interpolation=cv2.INTER_LINEAR)
    return bg - L


def kumeler(sayac, esik=1, bosluk=8):
    """1 boyutlu doluluk dizisinde ardisik kumeler [(bas, son)]."""
    dolu = np.nonzero(sayac >= esik)[0]
    if len(dolu) == 0:
        return []
    out, b, o = [], dolu[0], dolu[0]
    for i in dolu[1:]:
        if i - o > bosluk:
            out.append((b, o + 1)); b = i
        o = i
    out.append((b, o + 1))
    return out


def eski_tarih_ekle(P, metin, font):
    H, W = P.shape[:2]
    s = W / W8
    d = koyu_murekkep(P)
    ink = d > 40                                                        # WP parsomen dokusu (p90 ~11, p99 ~110 yazi dahil) elensin
    ink[:, : int(0.15 * W)] = False; ink[:, int(0.85 * W):] = False      # WP: koyu parsomen kenarlari yazi sanilmasin (yazi ortada)
    # alt yazi bandi: 0.80H..0.95H arasindaki en kalabalik satir kumesi
    y0b, y1b = int(0.80 * H), int(0.95 * H)
    sat = ink[y0b:y1b].sum(1)
    kk = [(a + y0b, b + y0b) for a, b in kumeler(sat, max(int(4 * s), 0.15 * sat.max()), int(10 * s))]   # satir esigi bagil: doku lekeleri yazi satiri sayilmaz
    if not kk:
        raise SystemExit('HATA: alt yazi satiri bulunamadi')
    t0, t1 = max(kk, key=lambda q: ink[q[0]:q[1]].sum())
    bant = ink[t0:t1]
    sut = np.nonzero(bant.any(0))[0]
    alt = np.array([t0 + np.nonzero(bant[:, x])[0].max() for x in sut])
    hist = np.bincount(alt - t0)
    taban1 = int(t0 + np.argmax(np.convolve(hist, np.ones(3), 'same')))
    tx0, tx1 = int(sut.min()), int(sut.max()) + 1
    # isim satiri: alt yazi bandinin ustundeki ilk kume (0.62H..t0)
    y0n = int(0.62 * H)
    satn = ink[y0n:t0].sum(1)
    kn = [(a + y0n, b + y0n) for a, b in kumeler(satn, max(int(4 * s), 0.15 * satn.max()), int(10 * s))]
    if not kn:
        raise SystemExit('HATA: isim satiri bulunamadi')
    n0, n1 = kn[-1]
    yan = np.zeros(W, bool); yan[int(0.15 * W): int(0.42 * W)] = True; yan[int(0.58 * W): int(0.85 * W)] = True   # orta (sonsuz) ve kenarlar haric
    guclu = (d > 55) & yan[None, :]
    prof, satirlar = [], []
    for y in range(n0, n1):
        m = guclu[y]
        if m.sum() >= max(3, 0.2 * guclu[n0:n1].sum(1).max()):
            prof.append(np.median(P[y][m], 0)); satirlar.append(y)
    if len(prof) < 8:
        raise SystemExit('HATA: isim profili olculemedi')
    prof = np.array(prof, np.float32)
    # tarih
    a, il, ir, tb = tarih_ciz(metin, int(round(TARIH_PX * s)), TARIH_ARALIK * s, font)
    ys = np.nonzero((a > 0.5).any(1))[0]; g0, g1 = ys.min(), ys.max() + 1
    gen = ir - il
    x0 = int(round(W / 2 - gen / 2 - il)); taban2 = int(round(taban1 + SATIR_ARA * s)); y0 = taban2 - tb
    if x0 < 0 or x0 + a.shape[1] > W or y0 < 0 or y0 + a.shape[0] > H:
        raise SystemExit('HATA: tarih satiri sayfaya sigmiyor')
    renk = np.zeros((a.shape[0], 3), np.float32)
    for r in range(a.shape[0]):
        t = np.clip((r - g0) / max(g1 - g0 - 1, 1), 0, 1)
        renk[r] = prof[int(round(t * (len(prof) - 1)))]
    bolge = P[y0:y0 + a.shape[0], x0:x0 + a.shape[1]].astype(np.float32)
    al = a[..., None]
    P2 = P.copy()
    P2[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = np.clip(np.round(bolge * (1 - al) + renk[:, None, :] * al), 0, 255).astype(np.uint8)
    bilgi = dict(satir1_taban=taban1, satir1_x=[tx0, tx1], isim_bandi=[int(n0), int(n1)], satir2_taban=taban2,
                 satir2_x=[int(x0 + il), int(x0 + ir)], satir2_ust=int(y0 + g0), punto=int(round(TARIH_PX * s)),
                 profil_satir=len(prof), profil_rgb_ust_orta_alt=[prof[0].round().tolist(), prof[len(prof) // 2].round().tolist(), prof[-1].round().tolist()])
    return P2, bilgi


def murekkep_kutusu(P):
    """Zeminden ayrisan ogeler (yildiz / pariltilar kucuk bilesen olarak elenir). Koyu ve acik zeminde calisir."""
    L = cv2.cvtColor(P, cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32)
    k = 4
    kucuk = cv2.resize(L, (L.shape[1] // k, L.shape[0] // k), interpolation=cv2.INTER_AREA)
    bg = cv2.resize(cv2.medianBlur(kucuk.astype(np.uint8), 31).astype(np.float32), (L.shape[1], L.shape[0]), interpolation=cv2.INTER_LINEAR)
    m = (np.abs(L - bg) > 30).astype(np.uint8)                          # 30: WP parsomen dokusu kenara yapisik bilesen olusturmasin (18'de kenar 0 px)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    tut = np.zeros(n, bool)
    tut[1:] = np.maximum(st[1:, cv2.CC_STAT_WIDTH], st[1:, cv2.CC_STAT_HEIGHT]) >= 50     # yildiz / parilti (< 50 px) haric; cember, sembol, harfler kalir
    ys, xs = np.nonzero(tut[lab])
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def kart_yap(P8):
    """Sartname: ayni tasarim yukseklige olceklenir (3000 -> 2100), yanlardan esit kirpilir (1680 -> 1500)."""
    w = int(round(P8.shape[1] * KART[1] / P8.shape[0]))
    R = cv2.resize(P8, (w, KART[1]), interpolation=cv2.INTER_AREA)
    k = (w - KART[0]) // 2
    K = R[:, k:k + KART[0]].copy()
    x0, y0, x1, y1 = murekkep_kutusu(K)
    pay = dict(sol_px=x0, sag_px=KART[0] - x1, ust_px=y0, alt_px=KART[1] - y1)
    pay.update({k_.replace('_px', '_inc'): round(v / 300, 3) for k_, v in list(pay.items())})
    pay['kirpilan_her_yan_px'] = k
    return K, pay


def kesit(P, bilgi_y=None):
    """Isim satirindan son satira 1:1 yakin plan (genislik = sayfa)."""
    H, W = P.shape[:2]
    y0, y1 = int(0.70 * H), int(0.95 * H)
    return P[y0:y1]


def ocr_kapisi(P_kesit, bekle, gecici):
    # yazi = yerel zeminden belirgin ayrisan pikseller (koyu ya da acik zemin, parsomen dokusu dahil); doku lekeleri kucuk bilesen olarak elenir
    W_ = P_kesit.shape[1]
    Pk = np.ascontiguousarray(P_kesit[:, int(0.12 * W_): int(0.88 * W_)])
    L = cv2.cvtColor(Pk, cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32)
    k = 4
    kucuk = cv2.resize(L, (L.shape[1] // k, L.shape[0] // k), interpolation=cv2.INTER_AREA)
    bg = cv2.resize(cv2.medianBlur(kucuk.astype(np.uint8), 31).astype(np.float32), (L.shape[1], L.shape[0]), interpolation=cv2.INTER_LINEAR)
    m = (np.abs(L - bg) > 30).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    tut = np.zeros(n, bool); tut[1:] = st[1:, cv2.CC_STAT_AREA] >= 25
    b = np.where(tut[lab], 0, 255).astype(np.uint8)
    b = cv2.resize(b, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(gecici, b)
    env = dict(os.environ, OMP_THREAD_LIMIT='1')
    out = subprocess.run(['tesseract', gecici, '-', '--psm', '6'], capture_output=True, text=True, timeout=120, env=env).stdout
    norm = lambda t: re.sub(r'[^A-Z0-9 ]', '', t.upper().replace('·', ' ')).split()
    satirlar = [' '.join(norm(s)) for s in out.splitlines() if norm(s)]
    sonuc = {}
    for e in bekle:
        en = ' '.join(norm(e))
        best = 0.0
        for s in satirlar:
            ws = s.split()
            n = len(en.split())
            for i in range(max(1, len(ws) - n + 1)):
                best = max(best, difflib.SequenceMatcher(None, en, ' '.join(ws[i:i + n])).ratio())
        sonuc[e] = round(best, 3)
    return dict(ocr=satirlar, eslesme=sonuc, PASS=all(v >= 0.85 for v in sonuc.values()))


def kaydet(P, yol, q=95):
    Image.fromarray(P).save(yol, quality=q, subsampling=0, dpi=(300, 300))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--girdi', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--ad', required=True)
    ap.add_argument('--tur', choices=['poster', 'kart'], required=True)
    ap.add_argument('--font', required=True)
    ap.add_argument('--tarih-ekle', default='')
    ap.add_argument('--bekle', required=True)
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    P = np.asarray(Image.open(a.girdi).convert('RGB'))
    rap = dict(girdi=os.path.basename(a.girdi), tur=a.tur, boyut_girdi=list(P.shape[1::-1]))
    if P.shape[:2] != (H8, W8):
        raise SystemExit(f'HATA: girdi 8x10 (2400x3000) degil: {P.shape[1::-1]}')
    if a.tarih_ekle:
        P, rap['tarih_eski_yol'] = eski_tarih_ekle(P, a.tarih_ekle.strip(), a.font)
    bekle = [x for x in a.bekle.split('|') if x]
    if a.tur == 'poster':
        son = f'{a.cikti}/{a.ad}_Paper_8x10.jpg'
        kaydet(P, son, 97)
        ks = kesit(P)
        rap['dosya'] = os.path.basename(son); rap['boyut'] = [W8, H8]
    else:
        K, pay = kart_yap(P)
        son = f'{a.cikti}/{a.ad}_Paper_Kart_5x7.jpg'
        kaydet(K, son, 97)
        ks = kesit(K)
        rap['dosya'] = os.path.basename(son); rap['boyut'] = list(KART); rap['kenar_payi'] = pay
    kp = f'{a.cikti}/KESIT_{a.ad}_{"8x10" if a.tur == "poster" else "Kart_5x7"}.jpg'
    kaydet(ks, kp, 95)
    rap['kesit'] = os.path.basename(kp)
    rap['metin_kapisi'] = ocr_kapisi(ks, bekle, f'{a.cikti}/_ocr_{a.ad}_{a.tur}.png')
    os.remove(f'{a.cikti}/_ocr_{a.ad}_{a.tur}.png')
    im = Image.open(son)
    rap['dpi'] = [round(float(v)) for v in im.info.get('dpi', (0, 0))]
    rap['PASS'] = bool(rap['metin_kapisi']['PASS'] and rap['dpi'] == [300, 300] and list(im.size) == rap['boyut'])
    json.dump(rap, open(f'{a.cikti}/{a.ad}_{a.tur}.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(rap, ensure_ascii=False))
    sys.exit(0 if rap['PASS'] else 1)


if __name__ == '__main__':
    main()
