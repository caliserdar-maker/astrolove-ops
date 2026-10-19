#!/usr/bin/env python3
"""Yil donumu 78 ilan kapak + pin, Y1_v7 kurali (Serdar onayi 19 Eki 2026). Etsy'ye yazmaz; yalniz dosya uretir.

Kural kapak_y1_v7.py (081c3a47) ile birebir: v6 yerlesimi (baslik 210 px, poster 1096x1370 @ v6 yeri, guvenli alan
x 240-2160 / y 247-2153), satir 2 "A & B"; x 250-2150'ye sigmayan ciftte yalniz satir 2 sigan en buyuk boya iner
(SATIR2_78_v7.csv ile ayni hesap). Her ilan kendi posteri (cikti/<CIFT>/poster/4_Layers_8x10.jpg). AQUARIUS'lu 12 ciftte
Q kuyrugu nedeniyle bosluk 120-125 px kabul (Serdar onayi); poster yeri/boyu 78 kapakta ayni.
Zemin (by_kapak.zemin) deterministik (tohum 4): bir kez hesaplanir, her kapakta ayni dizi kullanilir.
Kontrol (her ilan, KONTROL.csv): poster yeri/boyu; poster NCC (kaynak) >= 0.99; satir 2 parcalari (A, &, B) ile baslik
dE76 < 2; satir 2 murekkebi x 250-2150; baslik/satir 2/poster 255x319, 300x300, 340x270 onizlemede ve pin bandinda tam;
pin poster NCC >= 0.99; bosluk >= 146 (AQUARIUS >= 120). Ayrica Y1_v7 ornekleri (Drive Y1_V7) ile fark 0.
Ciktilar: KAPAK/<CIFT>.jpg (2400x2400), PIN/<CIFT>_PIN.jpg (1000x1500), KONTROL.csv, KONTAK_01..07.jpg, OLCUM.txt.
Kaynak (K): by/ (kod, galeri, cikti/<CIFT>/poster/4_Layers_8x10.jpg x 78), Y1_v6.jpg, Y1_V7/Y1_v7_<CIFT>.jpg (2 ornek)
Kullanim: kapak_y1_78.py --kaynak K --cikti OUT [--ciftler A_B,C_D]
"""
import argparse
import csv
import importlib.util
import itertools
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

spec = importlib.util.spec_from_file_location('kv7', Path(__file__).with_name('kapak_y1_v7.py'))
v7m = importlib.util.module_from_spec(spec); spec.loader.exec_module(v7m)
v6m, v5m, v2m = v7m.v6m, v7m.v5m, v7m.v2m
JPEG = v2m.JPEG
GX0, GX1, PAY, BOSLUK, ONIZ = v7m.GX0, v7m.GX1, v7m.PAY, v7m.BOSLUK, v7m.ONIZ
POSTER_YER = (652, 772, 1096, 1370)
BOSLUK_AQUARIUS = 120
SAYFA = 12                                            # kontak sayfasi basina ilan


def kontak(out, satirlar, no):
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
        fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
    except OSError:
        f = fb = ImageFont.load_default(size=22)
    RH, W = 380, 20 + 340 + 15 + 255 + 15 + 340 + 15 + 340 + 15 + 220 + 20
    sh = Image.new('RGB', (W, 20 + RH * len(satirlar)), 'white')
    d = ImageDraw.Draw(sh)
    for i, (cift, kapak, pin, sonuc) in enumerate(satirlar):
        y = 20 + i * RH
        d.text((20, y), f'{cift}  {sonuc}', font=fb, fill=(20, 20, 20) if sonuc == 'PASS' else (200, 0, 0))
        x = 20
        t = kapak.resize((340, 340), Image.LANCZOS); sh.paste(t, (x, y + 34)); x += 355
        for w, h in ONIZ:
            o = v6m.kirp(kapak, w / h)[0].resize((w, h), Image.LANCZOS)
            sh.paste(o, (x, y + 34 + 340 - h))
            d.rectangle((x - 1, y + 34 + 340 - h - 1, x + w, y + 34 + 340), outline=(200, 200, 200))
            x += w + 15
        p = pin.resize((220, 330), Image.LANCZOS); sh.paste(p, (x, y + 34 + 10))
    yol = out / f'KONTAK_{no:02d}.jpg'
    sh.save(yol, quality=88)
    return yol.name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--ciftler', default='')
    g = ap.parse_args()
    K, OUT = Path(g.kaynak).resolve(), Path(g.cikti).resolve()
    (OUT / 'KAPAK').mkdir(parents=True, exist_ok=True); (OUT / 'PIN').mkdir(parents=True, exist_ok=True)
    m = v2m.by_yukle(K)
    c1 = m.hx(m.RENK_BASLIK)
    olc = []

    def kayit(ad, ok, ayrinti):
        olc.append((ad, bool(ok), ayrinti)); print(f"{'PASS' if ok else 'FAIL'} {ad}: {ayrinti}", flush=True)

    # taban: v6 yerlesimi ve Drive Y1_v6 ile fark 0 (kod ve girdi dogru)
    tc, poster = v7m.v6_yerlesim(m, c1)
    v6_im = v5m.ciz5(m, c1, tc, poster)[0]
    fark = np.abs(np.asarray(v2m.jpeg(v6_im)).astype(int) - np.asarray(Image.open(K / 'Y1_v6.jpg').convert('RGB')).astype(int)).max()
    kayit('Y1_v6 yeniden uretim = Drive Y1_v6.jpg', fark == 0, f'fark max {fark}; baslik merkezi y {tc}, poster {poster}')
    zem = m.zemin()
    m.zemin = lambda: zem.copy()                     # deterministik zemin, bir kez hesaplanir

    burclar = sorted(v6m.BURCLAR)
    tum = [f'{a}_{b}' for a, b in itertools.combinations_with_replacement(burclar, 2)]
    ciftler = [c for c in g.ciftler.split(',') if c] or tum
    eksik = [c for c in ciftler if not (K / 'by/cikti' / c / 'poster/4_Layers_8x10.jpg').is_file()]
    kayit('Poster kaynaklari', len(tum) == 78 and not eksik and set(ciftler) <= set(tum),
          f'{len(ciftler)} cift (78 icinden); eksik poster {len(eksik)}{": " + ", ".join(eksik) if eksik else ""}')
    if eksik:
        sys.exit(1)
    pencere = {(w, h): v6m.kirp(Image.new('RGB', (m.S, m.S)), w / h)[1] for w, h in ONIZ}
    P = (v6m.PIN_X0, v6m.PIN_Y0, v6m.PIN_X0 + v6m.PIN_W, v6m.PIN_Y0 + v6m.PIN_H)
    o = 1000 / v6m.PIN_W
    px, py, pw, ph = POSTER_YER
    bx = (int(np.ceil((px - P[0]) * o)) + 3, int(np.ceil((py - P[1]) * o)) + 3, int((px + pw - P[0]) * o) - 3, int((py + ph - P[1]) * o) - 3)
    kb = (bx[0] / o + P[0], bx[1] / o + P[1], bx[2] / o + P[0], bx[3] / o + P[1])

    satirlar, kontak_satir, sayfalar = [], [], []
    t0 = time.time()
    for i, cift in enumerate(ciftler, 1):
        a_ad, b_ad = cift.split('_')
        ns = v7m.sigan_ns(m, a_ad, b_ad)
        im, k, p = v7m.ciz7(m, cift, c1, ns, tc, poster)
        yol = OUT / 'KAPAK' / f'{cift}.jpg'
        im.save(yol, **JPEG)
        v = Image.open(yol).convert('RGB'); va = np.asarray(v)
        hata = []
        if p['poster'] != POSTER_YER:
            hata.append(f'poster yeri {p["poster"]}')
        ref = Image.open(K / 'by/cikti' / cift / 'poster/4_Layers_8x10.jpg').convert('L').resize((pw, ph), Image.LANCZOS).crop((5, 5, pw - 5, ph - 5))
        n = v2m.ncc(np.asarray(v.convert('L'))[py + 5:py + ph - 5, px + 5:px + pw - 5], ref)
        if n < 0.99:
            hata.append(f'poster NCC {n:.4f}')
        vb = v2m.renk_olc(va, k['baslik'])[0]
        dE = max(v2m.de(v2m.renk_olc(va, k[a])[0], vb) for a in ('satir2_A', 'satir2_amp', 'satir2_B'))
        if dE >= 2 or v2m.de(vb, c1) >= 2:
            hata.append(f'dE {dE:.2f}')
        s2 = k['satir2']
        if not (s2[0] >= GX0 + PAY and s2[2] <= GX1 - PAY):
            hata.append(f'satir 2 x {s2[0]}-{s2[2]}')
        G = py - s2[3]
        alt_sinir = BOSLUK_AQUARIUS if 'AQUARIUS' in cift else BOSLUK
        if G < alt_sinir:
            hata.append(f'bosluk {G} < {alt_sinir}')
        ogeler = (k['baslik_murekkep'], s2, k['poster'])
        oniz = {}
        for (w, h), pen in pencere.items():
            oniz[f'{w}x{h}'] = min(min(kk[0] - pen[0], kk[1] - pen[1], pen[2] - kk[2], pen[3] - kk[3]) for kk in ogeler)
            if oniz[f'{w}x{h}'] < 0:
                hata.append(f'onizleme {w}x{h} kesik')
        pim, dikis = v6m.pin6(m, v)
        pyol = OUT / 'PIN' / f'{cift}_PIN.jpg'
        pim.save(pyol, **JPEG)
        pp = Image.open(pyol).convert('L')
        n3 = v2m.ncc(pp.crop(bx), v.convert('L').resize((bx[2] - bx[0], bx[3] - bx[1]), Image.LANCZOS, box=kb))
        pin_ic = all(P[0] <= kk[0] and kk[2] <= P[2] and P[1] <= kk[1] and kk[3] <= P[3] for kk in ogeler)
        if not (pim.size == (1000, 1500) and pin_ic and n3 >= 0.99 and dikis < 4):
            hata.append(f'pin (NCC {n3:.4f}, icinde {pin_ic}, dikis {dikis:.1f})')
        sonuc = 'PASS' if not hata else 'FAIL'
        satirlar.append([cift, f'{a_ad} & {b_ad}', ns, s2[0], s2[2], min(s2[0] - GX0, GX1 - s2[2]), G, 'AQUARIUS' in cift,
                         f'{n:.4f}', f'{dE:.2f}', oniz['255x319'], oniz['300x300'], oniz['340x270'], f'{n3:.4f}', pin_ic, sonuc, '; '.join(hata)])
        kontak_satir.append((cift, v, pim, sonuc))
        if len(kontak_satir) == SAYFA or i == len(ciftler):
            sayfalar.append(kontak(OUT, kontak_satir, len(sayfalar) + 1)); kontak_satir = []
        gec = time.time() - t0
        print(f'[{i}/{len(ciftler)} %{100 * i / len(ciftler):.0f}] {cift}: {sonuc} satir2 {ns}px bosluk {G} NCC {n:.4f} dE {dE:.2f} '
              f'pin {n3:.4f}{" " + "; ".join(hata) if hata else ""} | gecen {gec:.0f} sn, kalan ~{gec / i * (len(ciftler) - i):.0f} sn', flush=True)

    with open(OUT / 'KONTROL.csv', 'w', newline='') as fh:
        cw = csv.writer(fh)
        cw.writerow(['cift', 'satir2', 'satir2_px', 'satir2_x0', 'satir2_x1', 'satir2_yan_pay_240_2160', 'bosluk_poster_px', 'aquarius',
                     'poster_ncc', 'dE_max', 'oniz_255x319_min_pay', 'oniz_300x300_min_pay', 'oniz_340x270_min_pay', 'pin_poster_ncc',
                     'pin_icinde', 'sonuc', 'hata'])
        cw.writerows(satirlar)
    fail = [r for r in satirlar if r[15] != 'PASS']
    kucuk = [r for r in satirlar if r[2] < 150]
    kayit('78 ilan kontrolu', not fail and len(satirlar) == len(ciftler),
          f'{len(satirlar) - len(fail)}/{len(satirlar)} PASS; satir 2 kuculen {len(kucuk)}: ' + ', '.join(f'{r[0]} {r[2]}px' for r in kucuk)
          + f'; bosluk {min(r[6] for r in satirlar)}-{max(r[6] for r in satirlar)} px (AQUARIUS disi en az {min((r[6] for r in satirlar if not r[7]), default=0)}); '
          f'NCC en az {min(float(r[8]) for r in satirlar):.4f}; dE en cok {max(float(r[9]) for r in satirlar):.2f}; '
          f'onizleme en dar pay {min(min(r[10], r[11], r[12]) for r in satirlar)} px; pin NCC en az {min(float(r[13]) for r in satirlar):.4f}'
          + (f'; FAIL: {", ".join(r[0] + " (" + r[16] + ")" for r in fail)}' if fail else ''))
    for cift in ('CANCER_LIBRA', 'SAGITTARIUS_SAGITTARIUS'):
        ref = K / 'Y1_V7' / f'Y1_v7_{cift}.jpg'
        if cift in ciftler and ref.is_file():
            fk = np.abs(np.asarray(Image.open(OUT / 'KAPAK' / f'{cift}.jpg')).astype(int) - np.asarray(Image.open(ref).convert('RGB')).astype(int)).max()
            kayit(f'{cift} = onayli Y1_v7 ornegi', fk == 0, f'fark max {fk}')
    print(f'KONTAK: {", ".join(sayfalar)}; sure {time.time() - t0:.0f} sn')
    fail_ad = [a for a, ok, _ in olc if not ok]
    with open(OUT / 'OLCUM.txt', 'w', encoding='utf-8') as fh:
        fh.write(f'Y1 78 ilan kapak + pin OLCUM (Y1_v7 kurali; Etsy yazma 0)\n')
        for a, ok, ay in olc:
            fh.write(f"{'PASS' if ok else 'FAIL'} {a}: {ay}\n")
        fh.write(f"KONTAK: {', '.join(sayfalar)}\nSONUC: {'PASS' if not fail_ad else 'FAIL ' + ', '.join(fail_ad)}\n")
    print('SONUC:', 'PASS' if not fail_ad else 'FAIL ' + ', '.join(fail_ad))
    sys.exit(1 if fail_ad else 0)


if __name__ == '__main__':
    main()
