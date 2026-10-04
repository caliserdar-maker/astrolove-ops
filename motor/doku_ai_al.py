#!/usr/bin/env python3
"""DOKU_AI donusu (Serdar 4 Eki, C adimi): ChatGPT sayfasindan YALNIZ DOKU alinir, sekil bizim vektor maskemizden.

1 hizalama : AI sayfasi gonderilen sayfaya (doku_ai_sayfa.py, 24x36 1:1) olceklenir; ECC (affine) ile kalan olcek /
             kayma / donme olculur (ilk donus: olcek tam 0.8, kayma < 0.3 px).
2 doku     : AI pikseli = doku x kapsama (bizim maske, AI cozunurlugune indirilmis) + siyah x (1 - kapsama)
             -> doku = AI / kapsama (kapsama >= KAPSAMA_MIN ve AI lumasi > KOYU_MIN olan pikseller); kalan maske ici
             pikseller (AI seklinin bizimkinden ince kaldigi kenar) en yakin gecerli dokudan doldurulur (Telea).
             Buyutme: AI px -> 24x36 baski px = sayfa / AI (1.25); kucuk boylarda kucultme.
3 glif     : her glif: RGB doku (hucre boyu, 24x36 px) + alfa = Cinzel 500 punto 408 vektor maskesi (JSON koken_ls).
4 kelime   : kelime vektor maskesi istenen puntoda cizilir; her harfin dokusu bankadan (punto / 408) olceklenip ayni
             kokenle yerlestirilir; alfa = kelime maskesi (sekil sadakati: alfa vektorden, AI'dan degil).
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parent
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
KAPSAMA_MIN = 0.6
KOYU_MIN = 12.0
PUNTO_BANKA = 408


def font(d, p, w):
    f = ImageFont.truetype(str(KOK / 'font' / d), int(round(p)))
    if w:
        f.set_variation_by_axes([w])
    return f


def ecc(O, Ar):
    """O (gonderilen beyaz maske), Ar (AI kapsamasi, sayfa boyuna olceklenmis) -> affine (O -> Ar), cc."""
    wm = np.eye(2, 3, dtype=np.float32)
    cc, wm = cv2.findTransformECC(cv2.GaussianBlur(O, (0, 0), 2), cv2.GaussianBlur(Ar, (0, 0), 2), wm,
                                  cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6),
                                  None, 5)
    return wm, cc


def banka(sayfa_png, sayfa_json, ai_png):
    """-> {karakter: {'rgb': hucre RGB (24x36 px), 'alfa': hucre alfa, 'koken': hucre ici koken, 'dolgu': oran}}, olcum"""
    j = json.loads(Path(sayfa_json).read_text())
    W, H = j['boyut']
    O = np.asarray(Image.open(sayfa_png).convert('L'), np.float32) / 255
    x0, y0, x1, y1 = j['referans_kutu']
    O[y0:y1, x0:x1] = 0
    A = np.asarray(Image.open(ai_png).convert('RGB'), np.float32)
    h, w = A.shape[:2]
    L = A @ LUMA
    zem = float(np.median(L[L <= np.percentile(L, 50)]))
    Ar = cv2.resize(np.clip((L - zem - 15) / 40, 0, 1), (W, H), interpolation=cv2.INTER_LINEAR)
    Ar[y0:y1, x0:x1] = 0
    wm, cc = ecc(O, Ar)
    # AI -> sayfa: once nominal olcek (Lanczos), sonra kalan affine
    Au = cv2.resize(A, (W, H), interpolation=cv2.INTER_LANCZOS4)
    Au = cv2.warpAffine(Au, wm, (W, H), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
    # bizim kapsama, AI cozunurlugunde bulanmis hali (AI pikselinin karisim orani)
    Od = cv2.resize(cv2.resize(O, (w, h), interpolation=cv2.INTER_AREA), (W, H), interpolation=cv2.INTER_LINEAR)
    F = font(j['font'], j['punto'], j['wght'])
    B = {}
    for g in j['glifler']:
        gx0, gy0, gx1, gy1 = g['hucre']
        im = Image.new('L', (gx1 - gx0, gy1 - gy0), 0)
        kx, ky = g['koken_ls'][0] - gx0, g['koken_ls'][1] - gy0
        ImageDraw.Draw(im).text((kx, ky), g['karakter'], font=F, fill=255, anchor='ls')
        al = np.asarray(im, np.float32) / 255
        a = Au[gy0:gy1, gx0:gx1]; k = Od[gy0:gy1, gx0:gx1]
        ok = (k >= KAPSAMA_MIN) & ((a @ LUMA) > KOYU_MIN) & (al > 0.5)
        t = np.where(ok[..., None], a / np.maximum(k, 1e-3)[..., None], 0)
        gerek = cv2.dilate((al > 0).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & ~ok
        u8 = np.clip(np.round(t), 0, 255).astype(np.uint8)
        t = cv2.inpaint(u8, gerek.astype(np.uint8), 5, cv2.INPAINT_TELEA).astype(np.float32)
        B[g['karakter']] = {'rgb': t, 'alfa': al, 'koken': (kx, ky),
                            'dolgu': float((gerek & (al > 0.5)).sum() / max((al > 0.5).sum(), 1))}
    sx = float(np.hypot(wm[0, 0], wm[1, 0])); sy = float(np.hypot(wm[0, 1], wm[1, 1]))
    olc = {'ai_boyut': [w, h], 'sayfa_boyut': [W, H], 'nominal_buyutme': [W / w, H / h], 'ecc_cc': round(float(cc), 4),
           'ecc_ek_olcek': [round(sx, 4), round(sy, 4)], 'ecc_kayma_px': [round(float(wm[0, 2]), 2), round(float(wm[1, 2]), 2)],
           'ecc_donme_der': round(float(np.degrees(np.arctan2(wm[1, 0], wm[0, 0]))), 3)}
    return B, olc


def kelime(metin, B, punto, wght=500, dosya='Cinzel.ttf'):
    """kelime: (rgb, alfa) - alfa vektor maskesi (punto), doku bankadan olcekli. Koken (0, taban)."""
    F = font(dosya, punto, wght)
    s = punto / PUNTO_BANKA
    x0, y0, x1, y1 = F.getbbox(metin, anchor='ls')
    pad = 20
    Wk, Hk = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
    ox, oy = pad - x0, pad - y0
    im = Image.new('L', (Wk, Hk), 0)
    ImageDraw.Draw(im).text((ox, oy), metin, font=F, fill=255, anchor='ls')
    alfa = np.asarray(im, np.float32) / 255
    rgb = np.zeros((Hk, Wk, 3), np.float32); agr = np.zeros((Hk, Wk), np.float32)
    for i, c in enumerate(metin):
        if c == ' ':
            continue
        b = B[c]
        lx = ox + F.getlength(metin[:i + 1]) - F.getlength(c)  # harf koken: onceki harfle kerning dahil
        t = cv2.resize(b['rgb'], None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4)
        m = cv2.resize(cv2.dilate(b['alfa'], np.ones((9, 9), np.uint8)), None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        kx, ky = b['koken'][0] * s, b['koken'][1] * s
        M = np.float32([[1, 0, lx - kx], [0, 1, oy - ky]])
        tw = cv2.warpAffine(t, M, (Wk, Hk), flags=cv2.INTER_LINEAR)
        mw = cv2.warpAffine(m, M, (Wk, Hk), flags=cv2.INTER_LINEAR)
        rgb += tw * mw[..., None]; agr += mw
    rgb = rgb / np.maximum(agr, 1e-3)[..., None]
    return rgb, alfa, (ox, oy)
