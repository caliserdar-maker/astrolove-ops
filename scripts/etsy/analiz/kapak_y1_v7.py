#!/usr/bin/env python3
"""Yil donumu kapagi Y1_v7, ORNEK CANCER_LIBRA + SAGITTARIUS_SAGITTARIUS (19 Eki 2026, Serdar). Etsy'ye yazmaz.

Taban: onayli Y1_v6 yerlesimi (kapak_y1_v6.py 71ce5aac). Tek degisiklik: satir 2'de sonsuzluk logosu yerine "&":
"BURC & BURC", "&" ayni font (Cormorant 600), ayni boy, ayni renk (#FFF4E6). Iki yanindaki murekkep boslugu esit:
AMP_BOSLUK x ns/150 (150 px'te 50 = v6 logo boslugu). Satir 2 murekkebi yatayda ortali, dikey merkez cizgisi (gy) v6 ile ayni.
Baslik 210 px, poster 1096x1370 @ v6 yeri, guvenli alan x 240-2160 / y 247-2153 (pay 10) ayni.
Kural (Serdar onayli): satir 2 murekkebi x 250-2150'ye sigmiyorsa YALNIZ satir 2 sigan en buyuk boya (1 px adim) iner.
Ciktilar (Y1_V7/): Y1_v7_<CIFT>.jpg, PIN_Y1_v7_<CIFT>.jpg, ONIZ_<CIFT>_<wxh>.jpg (255x319, 300x300, 340x270),
KONTAK_Y1_v7.jpg (Y1_v6 | v7 ornekleri), SATIR2_78_v7.csv, OLCUM.txt. Herhangi FAIL -> cikis 1.
Kaynak (K): by/ (kod, galeri, cikti/<CIFT>/poster/4_Layers_8x10.jpg her ornek icin), Y1_v6.jpg
Kullanim: kapak_y1_v7.py --kaynak K --cikti OUT
"""
import argparse
import csv
import importlib.util
import itertools
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

spec = importlib.util.spec_from_file_location('kv6', Path(__file__).with_name('kapak_y1_v6.py'))
v6m = importlib.util.module_from_spec(spec); spec.loader.exec_module(v6m)
v5m, v2m = v6m.v5m, v6m.v2m                          # v6m yuklenince v5m.OLCEK = 1.0 (v4 boyutu)
JPEG = v2m.JPEG
GX0, GX1, GY0, GY1, PAY, BOSLUK = v6m.GX0, v6m.GX1, v6m.GY0, v6m.GY1, v6m.PAY, v6m.BOSLUK
ONIZ = v6m.ONIZ
AMP_BOSLUK = 50                                      # 150 px'te "&" ile burc adi arasi murekkep boslugu
SINIR = (GX1 - GX0) - 2 * PAY                        # satir 2 murekkep genisligi en cok 1900 (x 250-2150)
ORNEKLER = ['CANCER_LIBRA', 'SAGITTARIUS_SAGITTARIUS']
OLC = []


def kayit(ad, ok, ayrinti):
    OLC.append((ad, bool(ok), ayrinti))
    print(f"{'PASS' if ok else 'FAIL'} {ad}: {ayrinti}")


def v6_yerlesim(m, c1):
    """kapak_y1_v6.main ile ayni hesap: baslik merkezi tc ve poster (px, py, pw)."""
    dp = (702, 835, 996)
    a, k, _ = v5m.ciz5(m, c1, 500, dp)
    ust_ofs = k['baslik_murekkep'][1] - 500
    alt_ofs = v5m.murekkep(a, v5m.ciz5(m, (0, 0, 0), 500, dp)[0])[3] - 500
    tc = GY0 + PAY - ust_ofs
    p_ust = tc + alt_ofs + BOSLUK
    ph_max = (GY1 - PAY) - p_ust
    pw = int(ph_max / 1.25)
    while round(pw * 1.25) > ph_max or pw > SINIR:
        pw -= 1
    return tc, ((m.S - pw) // 2, p_ust, pw)


def parca(m, f, t):
    """t (harf araligi ile) murekkebi: (sol, sag, ust, alt), x=0 ve dikey 'lm' cizgisi y=0'a gore."""
    W, H, X, Y = 4000, 600, 200, 300
    tm = Image.new('L', (W, H), 0); d = ImageDraw.Draw(tm)
    x = X
    for c in t:
        d.text((x, Y), c, font=f, fill=255, anchor='lm')
        x += f.getlength(c) + m.HARF_ARALIK * f.size
    bb = tm.getbbox()
    return bb[0] - X, bb[2] - X, bb[1] - Y, bb[3] - Y


def satir2_plan(m, a_ad, b_ad, ns):
    """'A & B' murekkep yerlesimi: parcalarin cizim x'i (murekkep ortali, S genislik), toplam murekkep genisligi, ust/alt."""
    f = m.serif(ns)
    g = AMP_BOSLUK * ns / 150
    pa, pe, pb = parca(m, f, a_ad), parca(m, f, '&'), parca(m, f, b_ad)
    wa, we, wb = pa[1] - pa[0], pe[1] - pe[0], pb[1] - pb[0]
    top = wa + g + we + g + wb
    x0 = (m.S - top) / 2                             # murekkep baslangici
    xs = [x0 - pa[0], x0 + wa + g - pe[0], x0 + wa + g + we + g - pb[0]]
    return f, xs, top, min(pa[2], pe[2], pb[2]), max(pa[3], pe[3], pb[3])


def sigan_ns(m, a_ad, b_ad):
    ns = 150
    while satir2_plan(m, a_ad, b_ad, ns)[2] > SINIR:
        ns -= 1
    return ns


def satir2_kutu(m, a_ad, b_ad, ns, gy):
    """satir 2 murekkep kutusu, gercek cizim yerinde (ciz7 ile ayni konumlar)."""
    f2, xs, _, _, _ = satir2_plan(m, a_ad, b_ad, ns)
    tm = Image.new('L', (m.S, m.S), 0); d = ImageDraw.Draw(tm)
    for t, x in ((a_ad, xs[0]), ('&', xs[1]), (b_ad, xs[2])):
        for c in t:
            d.text((x, gy), c, font=f2, fill=255, anchor='lm')
            x += f2.getlength(c) + m.HARF_ARALIK * f2.size
    return tm.getbbox()


def ciz7(m, cift, renk2, ns, tc, poster):
    """v6 sahnesi (zemin, baslik 210, poster) + satir 2 'A & B'. Dondurur: im, kutular."""
    S = m.S
    a_ad, b_ad = cift.split('_')
    c1 = m.hx(m.RENK_BASLIK)
    s1, _, ara = v5m.taban_olcu(m)
    gy = tc + ara
    px, py, pw = poster; ph = round(pw * 1.25)
    eski = m.POSTER
    m.POSTER = str(Path(eski).parents[2] / cift / 'poster/4_Layers_8x10.jpg')
    try:
        bg = m.poster_yerlestir(m.zemin(), px, py, pw)
    finally:
        m.POSTER = eski
    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    f1 = m.serif(s1)
    d.text((S / 2, tc), m.BASLIK, font=f1, fill=c1, anchor='mm', features=['lnum'])
    bb1 = d.textbbox((S / 2, tc), m.BASLIK, font=f1, anchor='mm', features=['lnum'])
    tm = Image.new('L', (S, S), 0)
    ImageDraw.Draw(tm).text((S / 2, tc), m.BASLIK, font=f1, fill=255, anchor='mm', features=['lnum'])
    f2, xs, _, _, _ = satir2_plan(m, a_ad, b_ad, ns)
    kut = {'baslik': bb1, 'baslik_murekkep': tm.getbbox(), 'poster': (px, py, px + pw, py + ph)}
    tum = Image.new('L', (S, S), 0)
    for ad, t, x in (('satir2_A', a_ad, xs[0]), ('satir2_amp', '&', xs[1]), ('satir2_B', b_ad, xs[2])):
        pm = Image.new('L', (S, S), 0); pd = ImageDraw.Draw(pm)
        for c in t:
            d.text((x, gy), c, font=f2, fill=renk2, anchor='lm')
            pd.text((x, gy), c, font=f2, fill=255, anchor='lm')
            x += f2.getlength(c) + m.HARF_ARALIK * f2.size
        kut[ad] = pm.getbbox()
        tum.paste(255, mask=pm)
    kut['satir2'] = tum.getbbox()
    return im, kut, dict(s1=s1, ns=ns, gy=gy, poster=(px, py, pw, ph))


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

    # 1) taban: Y1_v6 yeniden uretimi = Drive Y1_v6.jpg
    tc, poster = v6_yerlesim(m, c1)
    v6_im, k6, p6 = v5m.ciz5(m, c1, tc, poster)
    y6 = Image.open(K / 'Y1_v6.jpg').convert('RGB')
    fark = np.abs(np.asarray(v2m.jpeg(v6_im)).astype(int) - np.asarray(y6).astype(int)).max()
    kayit('Y1_v6 yeniden uretim = Drive Y1_v6.jpg', fark == 0 and p6['poster'][2:] == (1096, 1370), f'fark max {fark}; poster {p6["poster"]}, baslik merkezi y {tc}')
    s2_6 = v5m.murekkep(v6_im, v5m.ciz5(m, (0, 0, 0), tc, poster)[0])

    # 2) 78 cift tablosu
    burclar = sorted(v6m.BURCLAR)
    gy = tc + v5m.taban_olcu(m)[2]
    tablo = []
    for a_ad, b_ad in itertools.combinations_with_replacement(burclar, 2):
        w150 = satir2_plan(m, a_ad, b_ad, 150)[2]
        ns = sigan_ns(m, a_ad, b_ad)
        kb = satir2_kutu(m, a_ad, b_ad, ns, gy)
        tablo.append([f'{a_ad}_{b_ad}', f'{a_ad} & {b_ad}', round(w150), w150 <= SINIR, ns, kb[2] - kb[0],
                      min(kb[0] - GX0, GX1 - kb[2]), poster[1] - kb[3]])
    tablo.sort(key=lambda r: -r[2])
    with open(OUT / 'SATIR2_78_v7.csv', 'w', newline='') as fh:
        cw = csv.writer(fh)
        cw.writerow(['cift', 'satir2', 'murekkep_genislik_150px', 'sigar_150px', 'satir2_px', 'murekkep_genislik_son',
                     'yan_pay_240_2160', 'bosluk_poster_px'])
        cw.writerows(tablo)
    kucuk = [r for r in tablo if r[4] < 150]
    kayit('78 cift satir 2 (&) sigma kurali', len(tablo) == 78 and all(r[5] <= SINIR and r[6] >= PAY for r in tablo),
          f'150 px sigan {78 - len(kucuk)}, kuculen {len(kucuk)}: ' + ', '.join(f'{r[0]} {r[2]} -> {r[4]} px' for r in kucuk)
          + f'; en dar yan pay {min(r[6] for r in tablo)} px; SATIR2_78_v7.csv')
    dar = sorted((r for r in tablo if r[7] < BOSLUK), key=lambda r: r[7])
    OLC.append(('BILGI bosluk < 146 olan ciftler', True, f'{len(dar)} cift (satir 2 murekkep alti - poster ustu; nedeni Q kuyrugu, poster yeri v6 ile sabit): '
                + ', '.join(f'{r[0]} {r[7]} px' for r in dar) + f'; digerleri {min((r[7] for r in tablo if r[7] >= BOSLUK), default=0)}-{max(r[7] for r in tablo)} px'))
    print(OLC[-1][2])

    # 3) ornekler
    ims = [('Y1_v6', y6)]
    ns_t = {r[0]: r[4] for r in tablo}
    for cift in ORNEKLER:
        a_ad, b_ad = cift.split('_')
        ns = ns_t[cift]
        im, k, p = ciz7(m, cift, c1, ns, tc, poster)
        yol = OUT / f'Y1_v7_{cift}.jpg'
        im.save(yol, **JPEG)
        v7 = Image.open(yol).convert('RGB'); va = np.asarray(v7)
        s2 = k['satir2']; t7 = k['baslik_murekkep']
        px, py, pw, ph = p['poster']
        G = py - s2[3]
        sol, amp, sag = k['satir2_A'], k['satir2_amp'], k['satir2_B']
        kayit(f'{cift} satir 2', s2[0] >= GX0 + PAY and s2[2] <= GX1 - PAY,
              f'"{a_ad} & {b_ad}" {ns} px (150 px genislik {round(satir2_plan(m, a_ad, b_ad, 150)[2])}), murekkep x {s2[0]}-{s2[2]} ({s2[2] - s2[0]} px), '
              f'& bosluklari sol {amp[0] - sol[2]} / sag {sag[0] - amp[2]} px, & murekkep {amp[2] - amp[0]}x{amp[3] - amp[1]} px')
        kayit(f'{cift} baslik / poster / bosluk', p['s1'] == 210 and (pw, ph) == (1096, 1370) and (px, py) == poster[:2] and G >= BOSLUK,
              f'baslik {p["s1"]} px, poster {pw}x{ph} @({px},{py}), bosluk {G} px (v6 {poster[1] - s2_6[3]} px)')
        ogeler = {'baslik': t7, 'satir2': s2, 'poster': k['poster']}
        paylar = {a_: (kk[0] - GX0, kk[1] - GY0, GX1 - kk[2], GY1 - kk[3]) for a_, kk in ogeler.items()}
        kayit(f'{cift} guvenli alan (pay >= 10)', all(min(v) >= PAY for v in paylar.values()),
              '; '.join(f'{a_} sol/ust/sag/alt {v[0]}/{v[1]}/{v[2]}/{v[3]}' for a_, v in paylar.items()))
        vb = v2m.renk_olc(va, k['baslik'])[0]
        for kk, ad in ((sol, a_ad), (amp, '&'), (sag, b_ad)):
            vk = v2m.renk_olc(va, kk)[0]
            kayit(f'{cift} "{ad}" rengi = baslik', v2m.de(vk, vb) < 2 and v2m.de(vb, c1) < 2,
                  f'{f(vk)} / baslik {f(vb)} (kod #{m.RENK_BASLIK}), dE76 {v2m.de(vk, vb):.2f}')
        ref = Image.open(K / 'by/cikti' / cift / 'poster/4_Layers_8x10.jpg').convert('L').resize((pw, ph), Image.LANCZOS).crop((5, 5, pw - 5, ph - 5))
        n = v2m.ncc(np.asarray(v7.convert('L'))[py + 5:py + ph - 5, px + 5:px + pw - 5], ref)
        kayit(f'{cift} poster NCC (kaynak)', n >= 0.99, f'{n:.4f}')
        # v6 ile fark yalniz satir 2 (+ farkli ciftte poster ici)
        dis = np.ones((m.S, m.S), bool)
        for kk in (k6['satir2'], s2):
            dis[max(0, int(kk[1]) - 4):int(kk[3]) + 5, max(0, int(kk[0]) - 4):int(kk[2]) + 5] = False
        if cift != v2m.PAIR:
            dis[py:py + ph, px:px + pw] = False
        zf = np.abs(np.asarray(im).astype(int) - np.asarray(v6_im).astype(int)).max(2)
        kayit(f'{cift} v6 ile fark yalniz satir 2' + ('' if cift == v2m.PAIR else ' + poster ici'), zf[dis].max() == 0,
              f'disarida fark max {zf[dis].max()} ({int(dis.sum())} px)')
        for w, h in ONIZ:
            o, pen = v6m.kirp(v7, w / h)
            o.resize((w, h), Image.LANCZOS).save(OUT / f'ONIZ_{cift}_{w}x{h}.jpg', quality=92)
            ic = {a_: pen[0] <= kk[0] and kk[2] <= pen[2] and pen[1] <= kk[1] and kk[3] <= pen[3] for a_, kk in ogeler.items()}
            kayit(f'{cift} onizleme {w}x{h}', all(ic.values()), f'pencere {pen}; ' + ', '.join(f'{a_} {"icinde" if v else "KESIK"}' for a_, v in ic.items())
                  + f'; en dar pay dikey {min(min(kk[1] - pen[1], pen[3] - kk[3]) for kk in ogeler.values())} px, '
                  f'yatay {min(min(kk[0] - pen[0], pen[2] - kk[2]) for kk in ogeler.values())} px')
        pim, dikis = v6m.pin6(m, v7)
        pim.save(OUT / f'PIN_Y1_v7_{cift}.jpg', **JPEG)
        P = (v6m.PIN_X0, v6m.PIN_Y0, v6m.PIN_X0 + v6m.PIN_W, v6m.PIN_Y0 + v6m.PIN_H)
        ic = all(P[0] <= kk[0] and kk[2] <= P[2] and P[1] <= kk[1] and kk[3] <= P[3] for kk in ogeler.values())
        pp = Image.open(OUT / f'PIN_Y1_v7_{cift}.jpg').convert('L'); o = 1000 / v6m.PIN_W
        bx = (int(np.ceil((px - P[0]) * o)) + 3, int(np.ceil((py - P[1]) * o)) + 3, int((px + pw - P[0]) * o) - 3, int((py + ph - P[1]) * o) - 3)
        kb = (bx[0] / o + P[0], bx[1] / o + P[1], bx[2] / o + P[0], bx[3] / o + P[1])
        n3 = v2m.ncc(pp.crop(bx), v7.convert('L').resize((bx[2] - bx[0], bx[3] - bx[1]), Image.LANCZOS, box=kb))
        kayit(f'{cift} PIN', pim.size == (1000, 1500) and ic and n3 >= 0.99 and dikis < 4,
              f'{pim.size[0]}x{pim.size[1]}; x {P[0]}-{P[2]} bandi + zemin ust/alt {-P[1]} px (dikis {dikis:.1f}); ogeler icinde {ic}; poster NCC {n3:.4f}')
        ims.append((f'Y1_v7 {cift}', v7))

    v6m.kontak(OUT, ims)
    os.replace(OUT / 'KONTAK_Y1_v6.jpg', OUT / 'KONTAK_Y1_v7.jpg')   # v6 kontak duzeni, ad v7
    print('-> KONTAK_Y1_v7.jpg (Y1_v6 | Y1_v7 CANCER_LIBRA | Y1_v7 SAGITTARIUS_SAGITTARIUS)')
    fail = [a_ for a_, ok, _ in OLC if not ok]
    with open(OUT / 'OLCUM.txt', 'w', encoding='utf-8') as fh:
        fh.write('Y1_v7 OLCUM (CANCER_LIBRA + SAGITTARIUS_SAGITTARIUS, ornek; Etsy yazma 0)\n')
        for a_, ok, ay in OLC:
            fh.write(f"{'BILGI' if a_.startswith('BILGI') else ('PASS' if ok else 'FAIL')} {a_.replace('BILGI ', '')}: {ay}\n")
        fh.write(f"SONUC: {'PASS' if not fail else 'FAIL ' + ', '.join(fail)}\n")
    print('SONUC:', 'PASS' if not fail else 'FAIL ' + ', '.join(fail))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
