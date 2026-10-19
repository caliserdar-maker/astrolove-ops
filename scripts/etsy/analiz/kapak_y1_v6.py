#!/usr/bin/env python3
"""Yil donumu kapagi Y1_v6, ORNEK CANCER_LIBRA (19 Eki 2026, Serdar). Etsy'ye yazmaz; yalniz dosya uretir.

Yeni Etsy kirpim olcumu (19 Eki): arama 4:5 dikey (kare kapakta sag/sol %10), magaza 1:1, "More from this shop" ~34:27
(ust/alt ~%10,3). Kare tuvalde (2400) guvenli alan x 240-2160, y 247-2153; her oge bu alanda en az PAY px kalir.
Baslik ve satir 2 Y1_v4 boyutunda (210 / 150 px, logo 160, logo boslugu 50, iki satir arasi ayni): kapak_y1_v5.ciz5
OLCEK = 1.0 ile cizilir. Baslik murekkebi ustu = 247 + PAY; satir 2 murekkep alti ile poster ustu arasi BOSLUK (146);
poster esit olcekle en buyuk, alt kenari <= 2153 - PAY, yatayda ortali. Renk (#FFF4E6), font, zemin ayni.
Onizleme: 255x319 (4:5), 300x300, 340x270 (34:27) merkez kirpim. Pin 1000x1500: guvenli bant x 240-2160 (1920 genis),
y -240..2640 (ust/alt 240 px zemin uzatmasi, ayni formul).
Ayrica: 78 ciftin satir 2'si (BURC logo BURC) 150 px'te cizilir, murekkep genisligi x 240-2160 (pay PAY) ile karsilastirilir.
Ciktilar (Y1_V6/): Y1_v6.jpg, PIN_Y1_v6.jpg, ONIZ_255x319/300x300/340x270.jpg, KONTAK_Y1_v6.jpg (Y1_v4 | Y1_v6),
SATIR2_78.csv, OLCUM.txt. Herhangi FAIL -> cikis 1 (78 cift olcumu bilgi, FAIL saymaz).
Kaynak klasoru (K): by/ (kod/by_kapak.py, galeri/, cikti/CANCER_LIBRA/poster/4_Layers_8x10.jpg), Y1_v4.jpg
Kullanim: kapak_y1_v6.py --kaynak K --cikti OUT
"""
import argparse
import csv
import importlib.util
import itertools
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

spec = importlib.util.spec_from_file_location('kv5', Path(__file__).with_name('kapak_y1_v5.py'))
v5m = importlib.util.module_from_spec(spec); spec.loader.exec_module(v5m)
v5m.OLCEK = 1.0                                      # Serdar: yazilar kuculmez (v4 boyutu)
v4m, v3m, v2m = v5m.v4m, v5m.v3m, v5m.v2m
B1, B2, PAIR, JPEG = v2m.B1, v2m.B2, v2m.PAIR, v2m.JPEG
GX0, GX1, GY0, GY1 = 240, 2160, 247, 2153            # guvenli alan (kare 2400)
PAY = 10
BOSLUK = 146
ONIZ = [(255, 319), (300, 300), (340, 270)]
PIN_X0, PIN_W, PIN_Y0, PIN_H = 240, 1920, -240, 2880  # 2:3; 1920x2880 -> 1000x1500
BURCLAR = ['ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO', 'SAGITTARIUS', 'CAPRICORN', 'AQUARIUS', 'PISCES']
OLC = []


def kayit(ad, ok, ayrinti):
    OLC.append((ad, bool(ok), ayrinti))
    print(f"{'PASS' if ok else 'FAIL'} {ad}: {ayrinti}")


def kirp(im, oran):
    return v2m.kirp(im, oran)


def pin6(m, im):
    a = np.asarray(im).astype(np.float32)
    out = np.empty((PIN_H, PIN_W, 3), np.float32)
    ust = -PIN_Y0
    out[:ust] = v2m.zemin_bant(m, PIN_Y0, 0, PIN_X0, PIN_X0 + PIN_W, 11)
    out[ust:ust + m.S] = a[:, PIN_X0:PIN_X0 + PIN_W]
    out[ust + m.S:] = v2m.zemin_bant(m, m.S, PIN_Y0 + PIN_H, PIN_X0, PIN_X0 + PIN_W, 12)
    dikis = max(np.abs(out[ust - 3:ust].mean((0, 1)) - out[ust:ust + 3].mean((0, 1))).max(),
                np.abs(out[ust + m.S - 3:ust + m.S].mean((0, 1)) - out[ust + m.S:ust + m.S + 3].mean((0, 1))).max())
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).resize((1000, 1500), Image.LANCZOS), float(dikis)


def satir2_genislik(m, a_ad, b_ad, ns=150):
    """satir 2'yi bos tuvale ciz (v4 yerlesimi: harf araligi, logo 160, bosluk 50), murekkep x araligi."""
    S = m.S
    f = m.serif(ns)
    tm = Image.new('L', (S + 1200, 300), 0); d = ImageDraw.Draw(tm)

    def tw(t):
        return sum(f.getlength(c) for c in t) + m.HARF_ARALIK * f.size * (len(t) - 1)
    top = tw(a_ad) + m.LOGO_BOSLUK + m.LOGO_W + m.LOGO_BOSLUK + tw(b_ad)
    x = (S + 1200 - top) / 2; x00 = x
    for t in (a_ad, None, b_ad):
        if t is None:
            d.rectangle((round(x), 140, round(x) + m.LOGO_W - 1, 160), fill=255)   # logo kutusu (genislik LOGO_W)
            x += m.LOGO_W + m.LOGO_BOSLUK
            continue
        for c in t:
            d.text((x, 150), c, font=f, fill=255, anchor='lm')
            x += f.getlength(c) + m.HARF_ARALIK * f.size
        x += m.LOGO_BOSLUK - m.HARF_ARALIK * f.size
    bb = tm.getbbox()
    return bb[2] - bb[0], top


def kontak(out, ims):
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 26)
        fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
    except OSError:
        f = fb = ImageFont.load_default(size=26)
    CW, KUTU, RH = 980, (840, 840), 320
    sh = Image.new('RGB', (20 + CW * len(ims), 60 + KUTU[1] + 40 + RH + 50), 'white')
    d = ImageDraw.Draw(sh)
    for i, (ad, im) in enumerate(ims):
        x = 20 + i * CW
        d.text((x, 14), f'{ad}  {im.size[0]}x{im.size[1]}', font=fb, fill=(20, 20, 20))
        t = im.copy(); t.thumbnail(KUTU, Image.LANCZOS)
        sh.paste(t, (x + (KUTU[0] - t.width) // 2, 60 + (KUTU[1] - t.height) // 2))
        xx, y = x, 60 + KUTU[1] + 40
        for w, h in ONIZ:
            o = kirp(im, w / h)[0].resize((w, h), Image.LANCZOS)
            sh.paste(o, (xx, y + (RH - h)))
            d.rectangle((xx - 1, y + (RH - h) - 1, xx + w, y + RH), outline=(200, 200, 200))
            d.text((xx, y + RH + 6), f'{w}x{h}', font=f, fill=(90, 90, 90))
            xx += w + 15
    sh.save(out / 'KONTAK_Y1_v6.jpg', quality=92)
    print(f'KONTAK_Y1_v6.jpg {sh.size[0]}x{sh.size[1]} (Y1_v4 | Y1_v6)')


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
    kayit('Y1_v4 yeniden uretim = Drive Y1_v4.jpg', fark == 0, f'fark max {fark}; poster {p4["poster"]}')

    # 2) yerlesim (deneme cizimi ile murekkep ofsetleri)
    dp = (702, 835, 996)
    a, k, _ = v5m.ciz5(m, c1, 500, dp)
    ust_ofs = k['baslik_murekkep'][1] - 500
    alt_ofs = v5m.murekkep(a, v5m.ciz5(m, (0, 0, 0), 500, dp)[0])[3] - 500
    tc = GY0 + PAY - ust_ofs
    p_ust = tc + alt_ofs + BOSLUK
    ph_max = (GY1 - PAY) - p_ust
    pw = int(ph_max / 1.25)
    while round(pw * 1.25) > ph_max or pw > (GX1 - GX0) - 2 * PAY:
        pw -= 1
    poster = ((m.S - pw) // 2, p_ust, pw)

    # 3) Y1_v6
    v6_im, k6, p6 = v5m.ciz5(m, c1, tc, poster)
    v6_im.save(OUT / 'Y1_v6.jpg', **JPEG)
    v6 = Image.open(OUT / 'Y1_v6.jpg').convert('RGB'); v6a = np.asarray(v6)
    s2 = v5m.murekkep(v6_im, v5m.ciz5(m, (0, 0, 0), tc, poster)[0])
    t6 = k6['baslik_murekkep']
    px, py, pw, ph = p6['poster']
    G = py - s2[3]
    kayit('Yazi boyutu = Y1_v4', (p6['s1'], p6['ns'], p6['logo_w'], p6['logo_b']) == (p4['s1'], p4['ns'], m.LOGO_W, m.LOGO_BOSLUK),
          f'baslik {p6["s1"]} px, satir 2 {p6["ns"]} px, logo {p6["logo_w"]}, logo boslugu {p6["logo_b"]} (Y1_v4 {p4["s1"]}/{p4["ns"]}); '
          f'murekkep genisligi baslik {t6[2] - t6[0]}, satir 2 {s2[2] - s2[0]}')
    kayit('Bosluk satir 2 alti - poster ustu >= 146', G >= BOSLUK, f'{G} px; satir 2 murekkep y {s2[1]}-{s2[3]}, poster ust {py}')
    ogeler = {'baslik': t6, 'satir2': s2, 'poster': k6['poster']}
    paylar = {a_: (kk[0] - GX0, kk[1] - GY0, GX1 - kk[2], GY1 - kk[3]) for a_, kk in ogeler.items()}
    kayit('Guvenli alan x 240-2160, y 247-2153 (pay >= 10)', all(min(v) >= PAY for v in paylar.values()),
          '; '.join(f'{a_} sol/ust/sag/alt {v[0]}/{v[1]}/{v[2]}/{v[3]}' for a_, v in paylar.items())
          + f'; poster golgesi alt {py + ph + 30}+ (kirpimda kalabilir)')
    kayit('Poster buyudu, ortali', pw > 996 and abs((px + pw / 2) - m.S / 2) <= 0.5,
          f'996x1245 -> {pw}x{ph} (+%{100 * (pw / 996 - 1):.1f} kenar, +%{100 * (pw * ph / (996 * 1245) - 1):.1f} alan) @({px},{py}); merkez x {px + pw / 2}')
    vb = v2m.renk_olc(v6a, k6['baslik'])[0]
    for kk in ('satir2_yazi_' + B1, 'satir2_logo', 'satir2_yazi_' + B2):
        vk = v2m.renk_olc(v6a, k6[kk])[0]
        kayit(f'Y1_v6 {kk} rengi = baslik', v2m.de(vk, vb) < 2 and v2m.de(vb, c1) < 2,
              f'{f(vk)} / baslik {f(vb)} (kod #{m.RENK_BASLIK}), dE76 {v2m.de(vk, vb):.2f}')
    ref = Image.open(K / 'by/cikti' / PAIR / 'poster/4_Layers_8x10.jpg').convert('L').resize((pw, ph), Image.LANCZOS).crop((5, 5, pw - 5, ph - 5))
    n = v2m.ncc(np.asarray(v6.convert('L'))[py + 5:py + ph - 5, px + 5:px + pw - 5], ref)
    kayit('Y1_v6 poster NCC (kaynak)', n >= 0.99, f'{n:.4f}')
    dis = np.ones((m.S, m.S), bool)
    for kk in (k4, k6):
        for a_ in ('baslik', 'satir2'):
            x0, y0, x1, y1 = kk[a_]; dis[max(0, int(y0) - 4):int(y1) + 5, max(0, int(x0) - 4):int(x1) + 5] = False
        x0, y0, x1, y1 = kk['poster']; dis[max(0, y0 - 200):y1 + 200, max(0, x0 - 200):x1 + 200] = False
    zf = np.abs(np.asarray(v6_im).astype(int) - np.asarray(v4_im).astype(int)).max(2)
    kayit('Zemin ayni (tasinan ogeler disinda)', zf[dis].max() == 0, f'fark max {zf[dis].max()} ({int(dis.sum())} px karsilastirildi)')

    # 4) onizlemeler
    for w, h in ONIZ:
        o, pen = kirp(v6, w / h)
        o.resize((w, h), Image.LANCZOS).save(OUT / f'ONIZ_{w}x{h}.jpg', quality=92)
        ic = {a_: pen[0] <= kk[0] and kk[2] <= pen[2] and pen[1] <= kk[1] and kk[3] <= pen[3] for a_, kk in ogeler.items()}
        py_ = min(min(kk[1] - pen[1], pen[3] - kk[3]) for kk in ogeler.values())
        px_ = min(min(kk[0] - pen[0], pen[2] - kk[2]) for kk in ogeler.values())
        kayit(f'Onizleme {w}x{h}', all(ic.values()), f'pencere {pen}; ' + ', '.join(f'{a_} {"icinde" if v else "KESIK"}' for a_, v in ic.items())
              + f'; en dar pay dikey {py_} px, yatay {px_} px')

    # 5) pin 1000x1500 (guvenli bant x 240-2160)
    pim, dikis = pin6(m, v6)
    pim.save(OUT / 'PIN_Y1_v6.jpg', **JPEG)
    ic = all(PIN_X0 <= kk[0] and kk[2] <= PIN_X0 + PIN_W and PIN_Y0 <= kk[1] and kk[3] <= PIN_Y0 + PIN_H for kk in ogeler.values())
    pp = Image.open(OUT / 'PIN_Y1_v6.jpg').convert('L'); o = 1000 / PIN_W
    bx = (int(np.ceil((px - PIN_X0) * o)) + 3, int(np.ceil((py - PIN_Y0) * o)) + 3, int((px + pw - PIN_X0) * o) - 3, int((py + ph - PIN_Y0) * o) - 3)
    kb = (bx[0] / o + PIN_X0, bx[1] / o + PIN_Y0, bx[2] / o + PIN_X0, bx[3] / o + PIN_Y0)
    n3 = v2m.ncc(pp.crop(bx), v6.convert('L').resize((bx[2] - bx[0], bx[3] - bx[1]), Image.LANCZOS, box=kb))
    kayit('PIN_Y1_v6', pim.size == (1000, 1500) and ic and n3 >= 0.99 and dikis < 4,
          f'{pim.size[0]}x{pim.size[1]}; Y1_v6 x {PIN_X0}-{PIN_X0 + PIN_W} bandi + zemin ust/alt {-PIN_Y0} px (dikis {dikis:.1f}); '
          f'baslik/satir 2/poster icinde {ic}; poster NCC {n3:.4f}')

    # 6) 78 cift satir 2 genisligi (150 px)
    ref_w = s2[2] - s2[0]
    olcum_cl = satir2_genislik(m, B1, B2)[0]
    sat = []
    for a_ad, b_ad in itertools.combinations_with_replacement(sorted(BURCLAR), 2):
        w_, _ = satir2_genislik(m, a_ad, b_ad)
        w_ += ref_w - olcum_cl                       # logo kutusu yerine gercek logo murekkebi farki (CANCER_LIBRA ile kalibre)
        ns_ = 150
        while ns_ > 60 and satir2_genislik(m, a_ad, b_ad, ns_)[0] + ref_w - olcum_cl > (GX1 - GX0) - 2 * PAY:
            ns_ -= 2                                 # sigan en buyuk satir 2 font boyu (logo 160 / bosluk 50 sabit)
        sat.append((f'{a_ad}_{b_ad}', w_, w_ <= (GX1 - GX0) - 2 * PAY, ns_))
    sat.sort(key=lambda r: -r[1])
    with open(OUT / 'SATIR2_78.csv', 'w', newline='') as fh:
        cw = csv.writer(fh); cw.writerow(['cift', 'murekkep_genislik_150px', 'x_240_2160_pay10_sigar', 'sigan_en_buyuk_satir2_px'])
        cw.writerows(sat)
    sigmayan = [r for r in sat if not r[2]]
    print(f'BILGI 78 cift satir 2 (150 px): en uzun {sat[0][0]} {sat[0][1]} px (sinir {(GX1 - GX0) - 2 * PAY} px = x 250-2150), '
          f'sigmayan {len(sigmayan)}: {", ".join(f"{r[0]} {r[1]} px (sigan {r[3]} px)" for r in sigmayan)}')
    OLC.append(('BILGI 78 cift satir 2', True, f'en uzun {sat[0][0]} {sat[0][1]} px; sinir 1900 px (x 250-2150); sigmayan {len(sigmayan)} cift'
                + (f': {", ".join(f"{r[0]} (sigan {r[3]} px)" for r in sigmayan)}' if sigmayan else '') + '; ayrinti SATIR2_78.csv'))

    kontak(OUT, [('Y1_v4', y4), ('Y1_v6', v6)])
    fail = [a_ for a_, ok, _ in OLC if not ok]
    with open(OUT / 'OLCUM.txt', 'w', encoding='utf-8') as fh:
        fh.write('Y1_v6 OLCUM (CANCER_LIBRA, ornek; Etsy yazma 0)\n')
        for a_, ok, ay in OLC:
            fh.write(f"{'BILGI' if a_.startswith('BILGI') else ('PASS' if ok else 'FAIL')} {a_.replace('BILGI ', '')}: {ay}\n")
        fh.write(f"SONUC: {'PASS' if not fail else 'FAIL ' + ', '.join(fail)}\n")
    print('SONUC:', 'PASS' if not fail else 'FAIL ' + ', '.join(fail))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
