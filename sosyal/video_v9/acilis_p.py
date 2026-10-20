#!/usr/bin/env python3
"""Acilis P (20 Eki 2026, K1 karari + yeni kapak karari): videonun ilk karesi = yeni pin gorunumunun 9:16 hali.

PIN_V2 kurali (claude/keen-curie-2hza60 d62abf53: pin_v2_ornek.pin_duvari + kapak_p2_78.py PIN bolumu) 1080x1920'ye:
  duvar: data/pod/kapak_sahne_v9.png -> 1213x910 -> 2160x3840 (pin 2000x3000 yerine, ayni 2x olcek) -> leke_azalt GUCLU
         -> aydinlat ACIK-3 -> 1080x1920; sahne oransal olceklendigi icin isik huzmeleri sag ve sol kenarda kalir.
  baslik: "A / & / B" yigini (pin istifi: & %62, satir arasi %12, Q kuyrugu istife girmez), EB Garamond 430, #162641.
  poster: baslik altinda, pin araligi (55 px) ve pin golgesi; poster pikseli yalniz olceklenir (LANCZOS), oran kaynakla ayni.
Yerlesim: pin olcusu (baslik 158 px, poster yuksekligi 990 px, ara 55 px) x s; s, blok TikTok/Reels arayuz alanlarina
(ust %12 = 230 px, alt %20 = 384 px, sag %15 = 162 px; sola da ayni pay, yatay ortali) PAY px payla sigan en buyuk deger.
Blok 9:16 karede yatay ve dikey ortali (merkez 540, 960).
Kullanim: acilis_p.py --poster P.jpg --a Cancer --b Libra --font EBGaramond[wght].ttf --out P_kare.png [--bilgi p.json]
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(KOK, 'scripts', 'pod'))
from duvar_zemin import AYDINLIK, LEKE, aydinlat, leke_azalt  # noqa: E402

W, H = 1080, 1920
RENK = (22, 38, 65)                                   # #162641
UST, ALT, SAG = round(0.12 * H), round(0.20 * H), round(0.15 * W)   # arayuz alanlari (230, 384, 162)
PAY = 20
BOY_P, ARA_P, POSTER_H_P = 158, 55, 990               # PIN_V2 (1000x1500) olculeri
G_P = [(4, 7, 14, 0.10), (1, 2, 3, 0.12)]             # PIN_V2 poster golgesi (dx, dy, sigma, guc)


def duvar916():
    sc = Image.open(os.path.join(KOK, 'data/pod/kapak_sahne_v9.png')).convert('RGB')
    D = leke_azalt(sc.resize((1213, 910), Image.LANCZOS).resize((2 * W, 2 * H), Image.LANCZOS), LEKE['guclu'])
    return aydinlat(D, *AYDINLIK['acik3']).resize((W, H), Image.LANCZOS)


def satir(font, metin, boy):
    """kapak_p2_78.satir: siki kirpilmis alfa maskesi ve taban cizgisinin maske icindeki satiri."""
    f = ImageFont.truetype(font, round(boy)); f.set_variation_by_axes([430])
    t = Image.new('L', (round(f.getlength(metin)) + 200, round(boy * 2.2)), 0)
    bx, by = 100, round(boy * 1.4)
    ImageDraw.Draw(t).text((bx, by), metin, font=f, fill=255, anchor='ls')
    a = np.asarray(t).astype(np.float32) / 255
    ys, xs = np.where(a > 0.05)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1], by - ys.min()


def yigin(font, a, b, boy):
    """PIN_V2 istifi: satirlar ve yuvalar (Q -> O ile olculur), ara %12. Donus: [(maske, x_ofs, y)], blok (w, h)."""
    ms = [satir(font, t, boy * (0.62 if t == '&' else 1)) for t in (a, '&', b)]
    yuva = [satir(font, t.replace('Q', 'O'), boy * (0.62 if t == '&' else 1)) for t in (a, '&', b)]
    ara = round(boy * 0.12)
    bw = max(m.shape[1] for m, _ in ms)
    out, yt = [], 0
    for (m, bl), (ym, yb) in zip(ms, yuva):
        out.append((m, (bw - m.shape[1]) // 2, yt + yb - bl))
        yt += ym.shape[0] + ara
    yh = yt - ara                                    # yuvalara gore blok yuksekligi (pin alt kenar hesabi ile ayni)
    gh = max(y + m.shape[0] for m, _, y in out)      # gercek murekkep alti (Q kuyrugu dahil)
    return out, bw, yh, gh


def golge(im, kutu, katman):
    a = np.asarray(im).astype(np.float32)
    x0, y0, x1, y1 = kutu
    for dx, dy, sg, guc in katman:
        sil = Image.new('L', im.size, 0)
        sil.paste(255, (round(x0 + dx), round(y0 + dy), round(x1 + dx), round(y1 + dy)))
        m = np.asarray(sil.filter(ImageFilter.GaussianBlur(sg))).astype(np.float32) / 255
        a = a * (1 - guc * m)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def lum(c):
    c = np.asarray(c, np.float64) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def yerlesim(font, a, b, oran):
    """En buyuk s: blok (baslik + ara + poster) arayuz alanlari disinda, 9:16 merkezli, PAY payla."""
    hmax = 2 * min(H / 2 - UST, (H - ALT) - H / 2) - 2 * PAY
    wmax = 2 * ((W - SAG) - W / 2) - 2 * PAY
    s = 1.0
    while s > 0.3:
        yg, bw, yh, gh = yigin(font, a, b, BOY_P * s)
        ph = round(POSTER_H_P * s); pw = round(ph * oran)
        blok = yh + round(ARA_P * s) + ph
        if blok <= hmax and max(bw, pw) <= wmax and gh - yh <= round(ARA_P * s) - 4:
            return s, yg, bw, yh, gh, pw, ph, blok, hmax, wmax
        s -= 0.002
    raise SystemExit('P yerlesimi sigmadi')


def p_kare(poster, a, b, font):
    A, B = a.upper(), b.upper()
    P = Image.open(poster).convert('RGB')
    oran = P.width / P.height
    s, yg, bw, yh, gh, pw, ph, blok, hmax, wmax = yerlesim(font, A, B, oran)
    y0 = round(H / 2 - blok / 2)
    py = y0 + yh + round(ARA_P * s); px = (W - pw) // 2
    D = duvar916()
    im = golge(D, (px, py, px + pw, py + ph), [(dx * s, dy * s, sg * s, g) for dx, dy, sg, g in G_P])
    im.paste(P.resize((pw, ph), Image.LANCZOS), (px, py))
    arr = np.asarray(im).astype(np.float32)
    xb = (W - bw) // 2
    kutular = []
    for m, xo, yo in yg:
        x, y = xb + xo, y0 + yo
        h_, w_ = m.shape
        arr[y:y + h_, x:x + w_] = arr[y:y + h_, x:x + w_] * (1 - m[..., None]) + np.array(RENK, np.float32) * m[..., None]
        kutular.append((x, y, x + w_, y + h_))
    kutular = [tuple(int(v) for v in k) for k in kutular]
    bk = (min(k[0] for k in kutular), min(k[1] for k in kutular), max(k[2] for k in kutular), max(k[3] for k in kutular))
    Dl = lum(np.asarray(D).astype(np.float64))
    kontrast = min((float(np.percentile(Dl[k[1]:k[3], k[0]:k[2]], 5)) + 0.05) / (float(lum(np.array(RENK))) + 0.05) for k in kutular)
    bilgi = dict(s=round(s, 3), baslik_px=round(BOY_P * s, 1), amp_px=round(BOY_P * s * 0.62, 1), baslik_kutu=bk,
                 poster_kutu=tuple(int(v) for v in (px, py, px + pw, py + ph)), poster_kaynak=f'{P.width}x{P.height}', blok_y=(int(y0), int(y0 + blok)),
                 blok_h=int(blok), blok_h_max=hmax, genislik_max=wmax, kontrast=round(kontrast, 2),
                 arayuz=dict(ust=UST, alt=H - ALT, sag=W - SAG, pay=PAY), golge=[[round(dx * s, 1), round(dy * s, 1), round(sg * s, 1), g] for dx, dy, sg, g in G_P])
    return np.clip(arr, 0, 255).astype(np.uint8), bilgi


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--poster', required=True)
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--font', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--bilgi')
    g = ap.parse_args()
    k, bi = p_kare(g.poster, g.a, g.b, g.font)
    Image.fromarray(k).save(g.out)
    print(json.dumps(bi))
    if g.bilgi:
        json.dump(bi, open(g.bilgi, 'w'), indent=1)
