#!/usr/bin/env python3
"""Yil donumu kapagi Y1_v5, ORNEK CANCER_LIBRA (19 Eki 2026, Serdar). Etsy'ye yazmaz; yalniz dosya uretir.

Taban: Y1_v4 (kapak_y1_v4.py 6eb5e97e). Degisiklik: baslik blogu (baslik + satir 2) esit oranda %10 kucuk (font boyu,
logo genisligi, logo boslugu ve iki satir merkezleri arasi x OLCEK; harf araligi em ile olcekli); acilan yerde poster
esit olcekle olabildigince buyur. Kurallar (4:3 penceresi y 300-2100):
  baslik murekkebi ustu = P0_ + PAY; satir 2 murekkep alti ile poster ustu arasi BOSLUK (146, v4 ile ayni);
  poster alti <= P1_ - PAY; poster yatayda ortali; poster golgesi kirpimda kalabilir.
Renk (#FFF4E6 baslik + satir 2 + logo), font, zemin ayni; poster pikseli yalniz olceklenir (NCC >= 0.99).
Ciktilar (Y1_V5/): Y1_v5.jpg, PIN_Y1_v5.jpg, ONIZ_300x225/300x300/225x300.jpg, KONTAK_Y1_v5.jpg (Y1_v4 | Y1_v5), OLCUM.txt.
QC (PASS/FAIL, herhangi FAIL -> cikis 1): Y1_v4 yeniden uretimi = Drive Y1_v4.jpg (fark 0); blok olcegi (font px ve
murekkep genisligi) %90; bosluk = 146; paylar >= PAY; poster ortali, buyume yazilir; renk dE76 < 2; poster NCC >= 0.99;
tasinan ogeler disinda zemin farki 0; 3 onizleme ve pin icinde baslik, satir 2, poster tam.
Kaynak klasoru (K): by/ (kod/by_kapak.py, galeri/, cikti/CANCER_LIBRA/poster/4_Layers_8x10.jpg), Y1_v4.jpg
Kullanim: kapak_y1_v5.py --kaynak K --cikti OUT
"""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

spec = importlib.util.spec_from_file_location('kv4', Path(__file__).with_name('kapak_y1_v4.py'))
v4m = importlib.util.module_from_spec(spec); spec.loader.exec_module(v4m)
v3m, v2m = v4m.v3m, v4m.v2m
B1, B2, PAIR, ONIZ, JPEG = v2m.B1, v2m.B2, v2m.PAIR, v2m.ONIZ, v2m.JPEG
P0_, P1_ = v3m.P0_, v3m.P1_
OLCEK = 0.90                                         # baslik blogu
PAY = 10                                             # baslik ustu / poster alti ile 4:3 pencere kenari
BOSLUK = 146                                         # satir 2 murekkep alti - poster ustu (Y1_v4)
OLC = []


def kayit(ad, ok, ayrinti):
    OLC.append((ad, bool(ok), ayrinti))
    print(f"{'PASS' if ok else 'FAIL'} {ad}: {ayrinti}")


def taban_olcu(m):
    """Y1_v2/v4 yerlesim olculeri (v3 ciz ile ayni hesap): baslik / satir 2 font px, iki satir merkezleri arasi."""
    PAY_ = 60
    s1 = 230
    while m.serif(s1).getlength(m.BASLIK, features=['lnum']) > (P1_ - P0_) - 2 * PAY_:
        s1 -= 2

    def tw(t, f):
        return sum(f.getlength(c) for c in t) + m.HARF_ARALIK * f.size * (len(t) - 1)
    ns = m.SATIR2_MAX
    while tw(B1, m.serif(ns)) + tw(B2, m.serif(ns)) + 2 * m.LOGO_BOSLUK + m.LOGO_W > (P1_ - P0_) - 2 * PAY_:
        ns -= 2
    ust = P0_ + 50
    py = ust + s1 + 245
    return s1, ns, (ust + s1 + py) / 2 + 5 - (ust + s1 / 2)


def ciz5(m, renk2, tc, poster):
    """baslik blogu OLCEK ile; tc baslik merkezi y, poster (px, py, pw). Dondurur: im, kutular, olculer."""
    S = m.S
    c1 = m.hx(m.RENK_BASLIK)
    s10, ns0, ara0 = taban_olcu(m)
    s1, ns = round(s10 * OLCEK), round(ns0 * OLCEK)
    logo_w, logo_b = round(m.LOGO_W * OLCEK), round(m.LOGO_BOSLUK * OLCEK)
    gy = tc + ara0 * OLCEK
    px, py, pw = poster; ph = round(pw * 1.25)
    bg = m.poster_yerlestir(m.zemin(), px, py, pw)
    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    f1 = m.serif(s1)
    d.text((S / 2, tc), m.BASLIK, font=f1, fill=c1, anchor='mm', features=['lnum'])
    bb1 = d.textbbox((S / 2, tc), m.BASLIK, font=f1, anchor='mm', features=['lnum'])
    tm = Image.new('L', (S, S), 0)
    ImageDraw.Draw(tm).text((S / 2, tc), m.BASLIK, font=f1, fill=255, anchor='mm', features=['lnum'])

    def tw(t, f):
        return sum(f.getlength(c) for c in t) + m.HARF_ARALIK * f.size * (len(t) - 1)

    def yaz(x, t, f):
        for c in t:
            d.text((x, gy), c, font=f, fill=renk2, anchor='lm')
            x += f.getlength(c) + m.HARF_ARALIK * f.size

    f2 = m.serif(ns)
    eski = m.LOGO_W
    m.LOGO_W = logo_w                                # logo_hazirla genisligi modul sabitinden okur
    try:
        lg = m.logo_hazirla(renk2)
    finally:
        m.LOGO_W = eski
    top = tw(B1, f2) + logo_b + logo_w + logo_b + tw(B2, f2)
    x0 = (S - top) / 2
    yaz(x0, B1, f2)
    lx = x0 + tw(B1, f2) + logo_b
    ly = round(gy - lg.height / 2)
    im.paste(lg, (round(lx), ly), lg)
    yaz(lx + logo_w + logo_b, B2, f2)
    yb = [d.textbbox((x0, gy), B1, font=f2, anchor='lm'), d.textbbox((lx + logo_w + logo_b, gy), B2, font=f2, anchor='lm')]
    kut = {'baslik': bb1, 'baslik_murekkep': tm.getbbox(),
           'satir2': (x0, min(gy - ns / 2, ly), x0 + top, max(gy + ns / 2, ly + lg.height)),
           'poster': (px, py, px + pw, py + ph),
           'satir2_yazi_' + B1: (x0, yb[0][1], lx - logo_b, yb[0][3]),
           'satir2_logo': (round(lx), ly, round(lx) + lg.width, ly + lg.height),
           'satir2_yazi_' + B2: (lx + logo_w + logo_b, yb[1][1], x0 + top, yb[1][3])}
    return im, kut, dict(s1=s1, ns=ns, s10=s10, ns0=ns0, logo_w=logo_w, logo_b=logo_b, ara=ara0 * OLCEK, poster=(px, py, pw, ph))


def murekkep(a, b):
    ys, xs = np.where(np.abs(np.asarray(a).astype(int) - np.asarray(b).astype(int)).max(2) > 0)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    g = ap.parse_args()
    K, OUT = Path(g.kaynak).resolve(), Path(g.cikti).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    m = v2m.by_yukle(K)
    c1 = m.hx(m.RENK_BASLIK)
    f = lambda c: '#' + ''.join(f'{round(v):02X}' for v in c)

    # 1) taban: Y1_v4 yeniden uretimi = Drive Y1_v4.jpg
    p4arg = (702, 835, 996)
    v4_im, k4, p4 = v3m.ciz(m, c1, v4m.YUKARI, p4arg)
    y4 = Image.open(K / 'Y1_v4.jpg').convert('RGB')
    fark = np.abs(np.asarray(v2m.jpeg(v4_im)).astype(int) - np.asarray(y4).astype(int)).max()
    kayit('Y1_v4 yeniden uretim = Drive Y1_v4.jpg', fark == 0 and p4['poster'] == (702, 835, 996, 1245), f'fark max {fark}; poster {p4["poster"]}')
    s2_4 = v3m.satir2_murekkep(m, v4m.YUKARI, p4arg)
    t4 = k4['baslik_murekkep']

    # 2) yerlesim: deneme cizimi ile murekkep olculeri, sonra kesin yer
    dp = (702, 835, 996)
    a, k, _ = ciz5(m, c1, 500, dp)
    b = ciz5(m, (0, 0, 0), 500, dp)[0]
    ust_ofs = k['baslik_murekkep'][1] - 500           # baslik murekkebi ustu - merkez
    alt_ofs = murekkep(a, b)[3] - 500                 # satir 2 murekkep alti - baslik merkezi
    tc = P0_ + PAY - ust_ofs
    p_ust = tc + alt_ofs + BOSLUK
    ph_max = (P1_ - PAY) - p_ust
    pw = int(ph_max / 1.25)
    while round(pw * 1.25) > ph_max:
        pw -= 1
    px = (m.S - pw) // 2
    poster = (px, p_ust, pw)

    # 3) Y1_v5
    v5_im, k5, p5 = ciz5(m, c1, tc, poster)
    v5_im.save(OUT / 'Y1_v5.jpg', **JPEG)
    v5 = Image.open(OUT / 'Y1_v5.jpg').convert('RGB'); v5a = np.asarray(v5)
    s2_5 = murekkep(v5_im, ciz5(m, (0, 0, 0), tc, poster)[0])
    t5 = k5['baslik_murekkep']
    px, py, pw, ph = p5['poster']
    G5 = py - s2_5[3]
    w_b, w_s = (t5[2] - t5[0]) / (t4[2] - t4[0]), (s2_5[2] - s2_5[0]) / (s2_4[2] - s2_4[0])
    kayit('Baslik blogu %10 kucuk', (p5['s1'], p5['ns']) == (round(p4['s1'] * OLCEK), round(p4['ns'] * OLCEK)) and abs(w_b - OLCEK) < 0.01 and abs(w_s - OLCEK) < 0.01,
          f'baslik {p4["s1"]} -> {p5["s1"]} px, satir 2 {p4["ns"]} -> {p5["ns"]} px, logo {m.LOGO_W} -> {p5["logo_w"]} px, logo boslugu {m.LOGO_BOSLUK} -> {p5["logo_b"]} px; '
          f'murekkep genisligi baslik {t4[2] - t4[0]} -> {t5[2] - t5[0]} ({w_b:.3f}), satir 2 {s2_4[2] - s2_4[0]} -> {s2_5[2] - s2_5[0]} ({w_s:.3f})')
    kayit('Bosluk satir 2 alti - poster ustu = 146', G5 == BOSLUK, f'{G5} px (Y1_v4 {p4["poster"][1] - s2_4[3]} px); satir 2 murekkep y {s2_5[1]}-{s2_5[3]}, poster ust {py}')
    kayit('Paylar (4:3 pencere y 300-2100)', t5[1] - P0_ >= PAY and P1_ - (py + ph) >= PAY,
          f'baslik murekkebi ust {t5[1]} (pay {t5[1] - P0_} px), poster alt {py + ph} (pay {P1_ - (py + ph)} px); en az {PAY}; '
          f'poster golgesi alt {py + ph + 30}+ (kirpimda kalabilir)')
    kayit('Poster buyudu, ortali', pw > 996 and abs((px + pw / 2) - m.S / 2) <= 0.5,
          f'996x1245 -> {pw}x{ph} (+%{100 * (pw / 996 - 1):.1f} kenar, +%{100 * (pw * ph / (996 * 1245) - 1):.1f} alan) @({px},{py}); merkez x {px + pw / 2}')
    vb = v2m.renk_olc(v5a, k5['baslik'])[0]
    for kk in ('satir2_yazi_' + B1, 'satir2_logo', 'satir2_yazi_' + B2):
        vk = v2m.renk_olc(v5a, k5[kk])[0]
        kayit(f'Y1_v5 {kk} rengi = baslik', v2m.de(vk, vb) < 2 and v2m.de(vb, c1) < 2,
              f'{f(vk)} / baslik {f(vb)} (kod #{m.RENK_BASLIK}), dE76 {v2m.de(vk, vb):.2f}')
    ref = Image.open(K / 'by/cikti' / PAIR / 'poster/4_Layers_8x10.jpg').convert('L').resize((pw, ph), Image.LANCZOS).crop((5, 5, pw - 5, ph - 5))
    n = v2m.ncc(np.asarray(v5.convert('L'))[py + 5:py + ph - 5, px + 5:px + pw - 5], ref)
    kayit('Y1_v5 poster NCC (kaynak)', n >= 0.99, f'{n:.4f}')

    dis = np.ones((m.S, m.S), bool)
    for kk in (k4, k5):
        for a_ in ('baslik', 'satir2'):
            x0, y0, x1, y1 = kk[a_]; dis[max(0, int(y0) - 4):int(y1) + 5, max(0, int(x0) - 4):int(x1) + 5] = False
        x0, y0, x1, y1 = kk['poster']; dis[max(0, y0 - 200):y1 + 200, max(0, x0 - 200):x1 + 200] = False
    zf = np.abs(np.asarray(v5_im).astype(int) - np.asarray(v4_im).astype(int)).max(2)
    kayit('Zemin ayni (tasinan ogeler disinda)', zf[dis].max() == 0, f'fark max {zf[dis].max()} ({int(dis.sum())} px karsilastirildi)')

    # 4) onizlemeler
    ogeler = {'baslik': t5, 'satir2': s2_5, 'poster': k5['poster']}
    for w, h in ONIZ:
        o, pen = v2m.kirp(v5, w / h)
        o.resize((w, h), Image.LANCZOS).save(OUT / f'ONIZ_{w}x{h}.jpg', quality=92)
        ic = {a_: pen[0] <= kk[0] and kk[2] <= pen[2] and pen[1] <= kk[1] and kk[3] <= pen[3] for a_, kk in ogeler.items()}
        pay = min(min(kk[1] - pen[1], pen[3] - kk[3]) for kk in ogeler.values())
        payx = min(min(kk[0] - pen[0], pen[2] - kk[2]) for kk in ogeler.values())
        kayit(f'Onizleme {w}x{h}', all(ic.values()), f'pencere {pen}; ' + ', '.join(f'{a_} {"icinde" if v else "KESIK"}' for a_, v in ic.items())
              + f'; en dar pay dikey {pay} px, yatay {payx} px')

    # 5) pin 1000x1500
    pim, dikis = v2m.pin(m, v5)
    pim.save(OUT / 'PIN_Y1_v5.jpg', **JPEG)
    ic = all(v2m.PIN_X0 <= kk[0] and kk[2] <= v2m.PIN_X0 + v2m.PIN_W and v2m.PIN_Y0 <= kk[1] and kk[3] <= v2m.PIN_Y0 + v2m.PIN_H for kk in ogeler.values())
    pp = Image.open(OUT / 'PIN_Y1_v5.jpg').convert('L'); o = 1000 / v2m.PIN_W
    bx = (int(np.ceil((px - v2m.PIN_X0) * o)) + 3, int(np.ceil((py - v2m.PIN_Y0) * o)) + 3,
          int((px + pw - v2m.PIN_X0) * o) - 3, int((py + ph - v2m.PIN_Y0) * o) - 3)
    kb = (bx[0] / o + v2m.PIN_X0, bx[1] / o + v2m.PIN_Y0, bx[2] / o + v2m.PIN_X0, bx[3] / o + v2m.PIN_Y0)
    n3 = v2m.ncc(pp.crop(bx), v5.convert('L').resize((bx[2] - bx[0], bx[3] - bx[1]), Image.LANCZOS, box=kb))
    kayit('PIN_Y1_v5', pim.size == (1000, 1500) and ic and n3 >= 0.99 and dikis < 4,
          f'{pim.size[0]}x{pim.size[1]}; Y1_v5 x {v2m.PIN_X0}-{v2m.PIN_X0 + v2m.PIN_W} bandi + zemin ust/alt {-v2m.PIN_Y0} px (dikis {dikis:.1f}); '
          f'baslik/satir 2/poster icinde {ic}; poster NCC {n3:.4f}')

    v3m.kontak(OUT, [('Y1_v4', y4), ('Y1_v5', v5)])
    os.replace(OUT / 'KONTAK_Y1_v3.jpg', OUT / 'KONTAK_Y1_v5.jpg')   # v3 kontak duzeni, ad v5
    print('-> KONTAK_Y1_v5.jpg (Y1_v4 | Y1_v5)')
    fail = [a_ for a_, ok, _ in OLC if not ok]
    with open(OUT / 'OLCUM.txt', 'w', encoding='utf-8') as fh:
        fh.write('Y1_v5 OLCUM (CANCER_LIBRA, ornek; Etsy yazma 0)\n')
        for a_, ok, ay in OLC:
            fh.write(f"{'PASS' if ok else 'FAIL'} {a_}: {ay}\n")
        fh.write(f"SONUC: {'PASS' if not fail else 'FAIL ' + ', '.join(fail)}\n")
    print('SONUC:', 'PASS' if not fail else 'FAIL ' + ', '.join(fail))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
