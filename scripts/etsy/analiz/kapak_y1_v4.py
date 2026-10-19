#!/usr/bin/env python3
"""Yil donumu kapagi Y1_v4, ORNEK CANCER_LIBRA (19 Eki 2026, Serdar). Etsy'ye yazmaz; yalniz dosya uretir.

Taban: onayli Y1_v2 (kapak_y1_v2.py f620b701). Y1_v3 duzeltmesi: poster KUCULMEZ (996x1245, Y1_v2 ile ayni olcek).
Yalniz iki hareket (v3'teki): baslik blogu (baslik + satir 2 birlikte) YUKARI px yukari, poster ASAGI px asagi.
4:3 penceresinde (y 300-2100) baslik murekkebi ve poster kenara en az KENAR px. Renk, font, zemin ayni.
Cizim kapak_y1_v3.py ciz() / satir2_murekkep() ile (poster=(px, py, pw), pw Y1_v2 ile ayni).
Ciktilar (Y1_V4/): Y1_v4.jpg, PIN_Y1_v4.jpg, ONIZ_300x225/300x300/225x300.jpg, KONTAK_Y1_v4.jpg (Y1_v2 | Y1_v4), OLCUM.txt.
QC (PASS/FAIL, herhangi FAIL -> cikis 1): Y1_v2 yeniden uretimi = Drive Y1_v2.jpg (fark 0); poster boyutu = Y1_v2;
kenar paylari >= KENAR; satir 2 ve logo rengi = baslik (dE76 < 2); baslik/satir 2 px ayni; poster NCC (kaynak ve Y1_v2)
>= 0.99; tasinan ogeler disinda zemin farki 0; 3 onizleme ve pin icinde baslik, satir 2, poster tam. Bosluk olculur, yazilir.
Kaynak klasoru (K): by/ (kod/by_kapak.py, galeri/, cikti/CANCER_LIBRA/poster/4_Layers_8x10.jpg), Y1_v2.jpg
Kullanim: kapak_y1_v4.py --kaynak K --cikti OUT
"""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

spec = importlib.util.spec_from_file_location('kv3', Path(__file__).with_name('kapak_y1_v3.py'))
v3m = importlib.util.module_from_spec(spec); spec.loader.exec_module(v3m)
v2m = v3m.v2m
B1, B2, PAIR, ONIZ, JPEG = v2m.B1, v2m.B2, v2m.PAIR, v2m.ONIZ, v2m.JPEG
P0_, P1_, KENAR = v3m.P0_, v3m.P1_, v3m.KENAR
YUKARI, ASAGI = 49, 30                               # Y1_v3 hareketleri (Serdar 19 Eki); poster olcegi degismez
OLC = []


def kayit(ad, ok, ayrinti):
    OLC.append((ad, bool(ok), ayrinti))
    print(f"{'PASS' if ok else 'FAIL'} {ad}: {ayrinti}")


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

    # 1) taban: Y1_v2 yeniden uretimi = Drive Y1_v2.jpg
    v2_im, k0, p0 = v3m.ciz(m, c1)
    y2 = Image.open(K / 'Y1_v2.jpg').convert('RGB')
    fark = np.abs(np.asarray(v2m.jpeg(v2_im)).astype(int) - np.asarray(y2).astype(int)).max()
    kayit('Y1_v2 yeniden uretim = Drive Y1_v2.jpg', fark == 0, f'fark max {fark}')
    s2 = v3m.satir2_murekkep(m)
    px0, py0, pw0, ph0 = p0['poster']
    G0 = py0 - s2[3]

    # 2) Y1_v4: baslik blogu YUKARI, poster ASAGI, poster boyutu ayni
    poster = (px0, py0 + ASAGI, pw0)
    v4_im, k4, p4 = v3m.ciz(m, c1, YUKARI, poster)
    v4_im.save(OUT / 'Y1_v4.jpg', **JPEG)
    v4 = Image.open(OUT / 'Y1_v4.jpg').convert('RGB'); v4a = np.asarray(v4)
    px, py, pw, ph = p4['poster']
    s24 = v3m.satir2_murekkep(m, YUKARI, poster)
    G4 = py - s24[3]
    T4 = k4['baslik_murekkep'][1]
    kayit('Poster boyutu = Y1_v2', (pw, ph) == (pw0, ph0) and px == px0, f'{pw}x{ph} @({px},{py}) (Y1_v2 {pw0}x{ph0} @({px0},{py0}))')
    kayit('Hareketler ve kenar paylari', T4 - P0_ >= KENAR and P1_ - (py + ph) >= KENAR,
          f'baslik blogu yukari {YUKARI} px, poster asagi {ASAGI} px; baslik murekkebi ust {T4} (pencere ustune {T4 - P0_} px), '
          f'poster alt {py + ph} (pencere altina {P1_ - (py + ph)} px); en az {KENAR}')
    print(f'BILGI bosluk (satir 2 murekkep alti - poster ustu): Y1_v2 {G0} px -> Y1_v4 {G4} px ({G4 / G0:.2f}x); '
          f'satir 2 murekkep y {s24[1]}-{s24[3]}, poster ust {py}')
    kayit('Bosluk olcumu', G4 == G0 + YUKARI + ASAGI, f'Y1_v2 {G0} px -> Y1_v4 {G4} px ({G4 / G0:.2f}x; beklenen {G0} + {YUKARI} + {ASAGI} = {G0 + YUKARI + ASAGI})')
    kayit('Baslik / satir 2 boyutu ayni', (p4['s1'], p4['ns']) == (p0['s1'], p0['ns']), f'baslik {p4["s1"]}px, satir 2 {p4["ns"]}px')
    vb = v2m.renk_olc(v4a, k4['baslik'])[0]
    for k in ('satir2_yazi_' + B1, 'satir2_logo', 'satir2_yazi_' + B2):
        vk = v2m.renk_olc(v4a, k4[k])[0]
        kayit(f'Y1_v4 {k} rengi = baslik', v2m.de(vk, vb) < 2 and v2m.de(vb, c1) < 2,
              f'{f(vk)} / baslik {f(vb)} (kod #{m.RENK_BASLIK}), dE76 {v2m.de(vk, vb):.2f}')
    ref = Image.open(K / 'by/cikti' / PAIR / 'poster/4_Layers_8x10.jpg').convert('L').resize((pw, ph), Image.LANCZOS).crop((5, 5, pw - 5, ph - 5))
    g4 = np.asarray(v4.convert('L'))[py + 5:py + ph - 5, px + 5:px + pw - 5]
    n1 = v2m.ncc(g4, ref)
    n2 = v2m.ncc(g4, np.asarray(y2.convert('L'))[py0 + 5:py0 + ph0 - 5, px0 + 5:px0 + pw0 - 5])
    kayit('Y1_v4 poster NCC', n1 >= 0.99 and n2 >= 0.99, f'kaynak poster ile {n1:.4f}, Y1_v2 posteri ile {n2:.4f}')

    # zemin: tasinan ogelerin (eski + yeni; golge ofset 30/16 + cv2 sigma 40 cekirdek yaricapi 160) disinda fark 0
    dis = np.ones((m.S, m.S), bool)
    for k in (k0, k4):
        for a in ('baslik', 'satir2'):
            x0, y0, x1, y1 = k[a]; dis[max(0, int(y0) - 4):int(y1) + 5, max(0, int(x0) - 4):int(x1) + 5] = False
        x0, y0, x1, y1 = k['poster']; dis[max(0, y0 - 200):y1 + 200, max(0, x0 - 200):x1 + 200] = False
    zf = np.abs(np.asarray(v4_im).astype(int) - np.asarray(v2_im).astype(int)).max(2)
    kayit('Zemin ayni (tasinan ogeler disinda)', zf[dis].max() == 0, f'fark max {zf[dis].max()} ({int(dis.sum())} px karsilastirildi)')

    # 3) onizlemeler
    ogeler = {'baslik': k4['baslik_murekkep'], 'satir2': s24, 'poster': k4['poster']}
    for w, h in ONIZ:
        o, pen = v2m.kirp(v4, w / h)
        o.resize((w, h), Image.LANCZOS).save(OUT / f'ONIZ_{w}x{h}.jpg', quality=92)
        ic = {a: pen[0] <= k[0] and k[2] <= pen[2] and pen[1] <= k[1] and k[3] <= pen[3] for a, k in ogeler.items()}
        pay = min(min(k[1] - pen[1], pen[3] - k[3]) for k in ogeler.values())
        kayit(f'Onizleme {w}x{h}', all(ic.values()), f'pencere {pen}; ' + ', '.join(f'{a} {"icinde" if v else "KESIK"}' for a, v in ic.items())
              + f'; en dar dikey pay {pay} px')

    # 4) pin 1000x1500 (ayni kural: Y1_v4 x 300-2100 bandi + zemin uzatmasi)
    pim, dikis = v2m.pin(m, v4)
    pim.save(OUT / 'PIN_Y1_v4.jpg', **JPEG)
    ic = all(v2m.PIN_X0 <= k[0] and k[2] <= v2m.PIN_X0 + v2m.PIN_W and v2m.PIN_Y0 <= k[1] and k[3] <= v2m.PIN_Y0 + v2m.PIN_H for k in ogeler.values())
    pp = Image.open(OUT / 'PIN_Y1_v4.jpg').convert('L'); o = 1000 / v2m.PIN_W
    bx = (int(np.ceil((px - v2m.PIN_X0) * o)) + 3, int(np.ceil((py - v2m.PIN_Y0) * o)) + 3,
          int((px + pw - v2m.PIN_X0) * o) - 3, int((py + ph - v2m.PIN_Y0) * o) - 3)
    kk = (bx[0] / o + v2m.PIN_X0, bx[1] / o + v2m.PIN_Y0, bx[2] / o + v2m.PIN_X0, bx[3] / o + v2m.PIN_Y0)
    n3 = v2m.ncc(pp.crop(bx), v4.convert('L').resize((bx[2] - bx[0], bx[3] - bx[1]), Image.LANCZOS, box=kk))
    kayit('PIN_Y1_v4', pim.size == (1000, 1500) and ic and n3 >= 0.99 and dikis < 4,
          f'{pim.size[0]}x{pim.size[1]}; Y1_v4 x {v2m.PIN_X0}-{v2m.PIN_X0 + v2m.PIN_W} bandi + zemin ust/alt {-v2m.PIN_Y0} px (dikis {dikis:.1f}); '
          f'baslik/satir 2/poster icinde {ic}; poster NCC {n3:.4f}')

    v3m.kontak(OUT, [('Y1_v2', y2), ('Y1_v4', v4)])
    os.replace(OUT / 'KONTAK_Y1_v3.jpg', OUT / 'KONTAK_Y1_v4.jpg')   # v3 kontak duzeni, ad v4
    print('-> KONTAK_Y1_v4.jpg (Y1_v2 | Y1_v4)')
    fail = [a for a, ok, _ in OLC if not ok]
    with open(OUT / 'OLCUM.txt', 'w', encoding='utf-8') as fh:
        fh.write('Y1_v4 OLCUM (CANCER_LIBRA, ornek; Etsy yazma 0)\n')
        for a, ok, ay in OLC:
            fh.write(f"{'PASS' if ok else 'FAIL'} {a}: {ay}\n")
        fh.write(f"SONUC: {'PASS' if not fail else 'FAIL ' + ', '.join(fail)}\n")
    print('SONUC:', 'PASS' if not fail else 'FAIL ' + ', '.join(fail))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
