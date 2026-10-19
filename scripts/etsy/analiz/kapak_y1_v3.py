#!/usr/bin/env python3
"""Yil donumu kapagi Y1_v3, ORNEK CANCER_LIBRA (19 Eki 2026, Serdar). Etsy'ye yazmaz; yalniz dosya uretir.

Taban: onayli Y1_v2 (kapak_y1_v2.py f620b701; satir 2 + logo baslik rengi #FFF4E6). Tek degisiklik: satir 2 (CANCER logo
LIBRA) alti ile poster ustu arasindaki bosluk >= 3 x mevcut (renderdan olculur). 4:3 penceresi (y 300-2100) korunur:
  a) once baslik blogu (baslik + satir 2 birlikte) yukari, poster asagi; ogeler pencere kenarina en az KENAR px kalir;
  b) yetmezse poster en az oranda, esit olcekle kuculur (alt kenar yerinde kalir).
Renk, font, boyut (baslik/satir 2 px), zemin ayni; poster pikseli yalniz olceklenir (NCC >= 0.99).
Ciktilar (Y1_V3/): Y1_v3.jpg, PIN_Y1_v3.jpg, ONIZ_300x225/300x300/225x300.jpg, KONTAK_Y1_v3.jpg (Y1_v2 | Y1_v3), OLCUM.txt.
QC (PASS/FAIL, herhangi FAIL -> cikis 1): Y1_v2 yeniden uretimi = Drive Y1_v2.jpg (fark 0); bosluk >= 3x; satir 2 ve logo
rengi = baslik (dE76 < 2); baslik/satir 2 px ayni; poster NCC (kaynak) >= 0.99; tasinan ogeler disinda zemin farki 0;
3 onizleme ve pin icinde baslik, satir 2, poster tam.
Kaynak klasoru (K): by/ (kod/by_kapak.py, galeri/, cikti/CANCER_LIBRA/poster/4_Layers_8x10.jpg), Y1_v2.jpg
Kullanim: kapak_y1_v3.py --kaynak K --cikti OUT
"""
import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

spec = importlib.util.spec_from_file_location('kv2', Path(__file__).with_name('kapak_y1_v2.py'))
v2m = importlib.util.module_from_spec(spec); spec.loader.exec_module(v2m)
B1, B2, PAIR, ONIZ, JPEG = v2m.B1, v2m.B2, v2m.PAIR, v2m.ONIZ, v2m.JPEG
P0_, P1_ = 300, 2100                                 # 4:3 / 3:4 penceresi (2400 kare)
KENAR = 20                                           # baslik murekkebi / poster ile pencere kenari arasi en az
OLC = []


def kayit(ad, ok, ayrinti):
    OLC.append((ad, bool(ok), ayrinti))
    print(f"{'PASS' if ok else 'FAIL'} {ad}: {ayrinti}")


def ciz(m, renk2, dy=0, poster=None):
    """kapak_y1_v2.y1_ciz ile ayni adimlar; dy: baslik blogu yukari kaydirma, poster: (px, py, pw) yeni yer/boy."""
    S, PAY = m.S, 60
    c1 = m.hx(m.RENK_BASLIK)
    s1 = 230
    while m.serif(s1).getlength(m.BASLIK, features=['lnum']) > (P1_ - P0_) - 2 * PAY:
        s1 -= 2
    ust = P0_ + 50
    py = ust + s1 + 245
    ph = (P1_ - 50) - py; pw = round(ph / 1.25); ph = round(pw * 1.25)
    px = (S - pw) // 2
    gy = (ust + s1 + py) / 2 + 5 - dy                # satir 2 dikey merkezi, Y1_v2'den dy yukari
    ust -= dy
    if poster:
        px, py, pw = poster; ph = round(pw * 1.25)
    bg = m.poster_yerlestir(m.zemin(), px, py, pw)
    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    f1 = m.serif(s1)
    d.text((S / 2, ust + s1 / 2), m.BASLIK, font=f1, fill=c1, anchor='mm', features=['lnum'])
    bb1 = d.textbbox((S / 2, ust + s1 / 2), m.BASLIK, font=f1, anchor='mm', features=['lnum'])
    tm = Image.new('L', (S, S), 0)                   # baslik murekkep kutusu
    ImageDraw.Draw(tm).text((S / 2, ust + s1 / 2), m.BASLIK, font=f1, fill=255, anchor='mm', features=['lnum'])

    def tw(t, f):
        return sum(f.getlength(c) for c in t) + m.HARF_ARALIK * f.size * (len(t) - 1)

    def yaz(x, t, f):
        for c in t:
            d.text((x, gy), c, font=f, fill=renk2, anchor='lm')
            x += f.getlength(c) + m.HARF_ARALIK * f.size

    ns = m.SATIR2_MAX
    while tw(B1, m.serif(ns)) + tw(B2, m.serif(ns)) + 2 * m.LOGO_BOSLUK + m.LOGO_W > (P1_ - P0_) - 2 * PAY:
        ns -= 2
    f2 = m.serif(ns)
    lg = m.logo_hazirla(renk2)
    top = tw(B1, f2) + m.LOGO_BOSLUK + m.LOGO_W + m.LOGO_BOSLUK + tw(B2, f2)
    x0 = (S - top) / 2
    yaz(x0, B1, f2)
    lx = x0 + tw(B1, f2) + m.LOGO_BOSLUK
    ly = round(gy - lg.height / 2)
    im.paste(lg, (round(lx), ly), lg)
    yaz(lx + m.LOGO_W + m.LOGO_BOSLUK, B2, f2)
    yb = [d.textbbox((x0, gy), B1, font=f2, anchor='lm'), d.textbbox((lx + m.LOGO_W + m.LOGO_BOSLUK, gy), B2, font=f2, anchor='lm')]
    kut = {'baslik': bb1, 'baslik_murekkep': tm.getbbox(),
           'satir2': (x0, min(gy - ns / 2, ly), x0 + top, max(gy + ns / 2, ly + lg.height)),
           'poster': (px, py, px + pw, py + ph),
           'satir2_yazi_' + B1: (x0, yb[0][1], lx - m.LOGO_BOSLUK, yb[0][3]),
           'satir2_logo': (round(lx), ly, round(lx) + lg.width, ly + lg.height),
           'satir2_yazi_' + B2: (lx + m.LOGO_W + m.LOGO_BOSLUK, yb[1][1], x0 + top, yb[1][3])}
    return im, kut, dict(s1=s1, ns=ns, poster=(px, py, pw, ph))


def satir2_murekkep(m, dy=0, poster=None):
    """satir 2 murekkebi: ayni sahne iki renkle cizilir, farkli pikseller = satir 2 (yazi + logo)."""
    a = np.asarray(ciz(m, m.hx(m.RENK_BASLIK), dy, poster)[0]).astype(int)
    b = np.asarray(ciz(m, (0, 0, 0), dy, poster)[0]).astype(int)
    ys, xs = np.where(np.abs(a - b).max(2) > 0)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def kontak(out, ims):
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 26)
        fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
    except OSError:
        f = fb = ImageFont.load_default(size=26)
    CW, KUTU = 880, (840, 840)
    sh = Image.new('RGB', (20 + CW * len(ims), 60 + KUTU[1] + 40 + 300 + 50), 'white')
    d = ImageDraw.Draw(sh)
    for i, (ad, im) in enumerate(ims):
        x = 20 + i * CW
        d.text((x, 14), f'{ad}  {im.size[0]}x{im.size[1]}', font=fb, fill=(20, 20, 20))
        t = im.copy(); t.thumbnail(KUTU, Image.LANCZOS)
        sh.paste(t, (x + (KUTU[0] - t.width) // 2, 60 + (KUTU[1] - t.height) // 2))
        xx, y = x, 60 + KUTU[1] + 40
        for w, h in ONIZ:
            o = v2m.kirp(im, w / h)[0].resize((w, h), Image.LANCZOS)
            sh.paste(o, (xx, y + (300 - h)))
            d.rectangle((xx - 1, y + (300 - h) - 1, xx + w, y + 300), outline=(200, 200, 200))
            d.text((xx, y + 306), f'{w}x{h}', font=f, fill=(90, 90, 90))
            xx += w + 15
    sh.save(out / 'KONTAK_Y1_v3.jpg', quality=92)
    print(f'KONTAK_Y1_v3.jpg {sh.size[0]}x{sh.size[1]}')


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
    v2_im, k0, p0 = ciz(m, c1)
    y2 = Image.open(K / 'Y1_v2.jpg').convert('RGB')
    fark = np.abs(np.asarray(v2m.jpeg(v2_im)).astype(int) - np.asarray(y2).astype(int)).max()
    kayit('Y1_v2 yeniden uretim = Drive Y1_v2.jpg', fark == 0, f'fark max {fark}')

    # 2) olcum: mevcut bosluk ve tasima paylari
    s2 = satir2_murekkep(m)
    T0 = k0['baslik_murekkep'][1]
    px0, py0, pw0, ph0 = p0['poster']
    G0 = py0 - s2[3]
    hedef = 3 * G0
    gerek = hedef - G0
    yukari_max = T0 - (P0_ + KENAR)
    asagi_max = (P1_ - KENAR) - (py0 + ph0)
    yukari = max(0, min(yukari_max, gerek))
    asagi = max(0, min(asagi_max, gerek - yukari))
    kucul = gerek - yukari - asagi                   # poster yuksekligi azaltma (px), alt kenar yerinde
    alt = py0 + ph0 + asagi
    pw = pw0 if kucul <= 0 else int((ph0 - kucul) / 1.25)
    ph = round(pw * 1.25)
    while alt - ph - (s2[3] - yukari) < hedef:       # yuvarlama: bosluk hedefin altina dusmesin
        pw -= 1; ph = round(pw * 1.25)
    px = (m.S - pw) // 2
    py = alt - ph
    print(f'BILGI olcum (Y1_v2): satir 2 murekkep y {s2[1]}-{s2[3]}, poster ust {py0}, bosluk {G0} px; baslik murekkep ust {T0}; '
          f'poster alt {py0 + ph0}; pencere {P0_}-{P1_}, kenar payi {KENAR}')
    print(f'BILGI karar: hedef bosluk {hedef} (+{gerek}); baslik blogu yukari {yukari} (en fazla {yukari_max}), poster asagi {asagi} '
          f'(en fazla {asagi_max}), poster kucultme {max(0, ph0 - ph)} px yukseklik ({pw0}x{ph0} -> {pw}x{ph}, olcek {pw / pw0:.4f})')

    # 3) Y1_v3
    v3_im, k3, p3 = ciz(m, c1, yukari, (px, py, pw))
    v3_im.save(OUT / 'Y1_v3.jpg', **JPEG)
    v3 = Image.open(OUT / 'Y1_v3.jpg').convert('RGB'); v3a = np.asarray(v3)
    s23 = satir2_murekkep(m, yukari, (px, py, pw))
    G3 = py - s23[3]
    kayit('Bosluk satir 2 alti - poster ustu >= 3x', G3 >= hedef,
          f'Y1_v2 {G0} px -> Y1_v3 {G3} px ({G3 / G0:.2f}x); baslik blogu yukari {yukari} px, poster asagi {asagi} px, '
          f'poster {pw0}x{ph0} -> {pw}x{ph} (olcek {pw / pw0:.4f}, {"kucultme yok" if pw == pw0 else f"{ph0 - ph} px kisa"})')
    kayit('Baslik / satir 2 boyutu ayni', (p3['s1'], p3['ns']) == (p0['s1'], p0['ns']), f'baslik {p3["s1"]}px, satir 2 {p3["ns"]}px')
    vb = v2m.renk_olc(v3a, k3['baslik'])[0]
    for k in ('satir2_yazi_' + B1, 'satir2_logo', 'satir2_yazi_' + B2):
        vk = v2m.renk_olc(v3a, k3[k])[0]
        kayit(f'Y1_v3 {k} rengi = baslik', v2m.de(vk, vb) < 2 and v2m.de(vb, c1) < 2,
              f'{f(vk)} / baslik {f(vb)} (kod #{m.RENK_BASLIK}), dE76 {v2m.de(vk, vb):.2f}')
    ref = Image.open(K / 'by/cikti' / PAIR / 'poster/4_Layers_8x10.jpg').convert('L').resize((pw, ph), Image.LANCZOS).crop((5, 5, pw - 5, ph - 5))
    n = v2m.ncc(np.asarray(v3.convert('L'))[py + 5:py + ph - 5, px + 5:px + pw - 5], ref)
    kayit('Y1_v3 poster NCC (kaynak)', n >= 0.99, f'{n:.4f}; poster {pw}x{ph} @({px},{py})')

    # zemin: tasinan ogelerin (eski + yeni; poster golgesi ofset 30/16 px + cv2 sigma 40 cekirdek yaricapi 160 px) disinda fark 0 (JPEG oncesi)
    dis = np.ones((m.S, m.S), bool)
    for k in (k0, k3):
        for a in ('baslik', 'satir2'):
            x0, y0, x1, y1 = k[a]; dis[max(0, int(y0) - 4):int(y1) + 5, max(0, int(x0) - 4):int(x1) + 5] = False
        x0, y0, x1, y1 = k['poster']; dis[max(0, y0 - 200):y1 + 200, max(0, x0 - 200):x1 + 200] = False
    zf = np.abs(np.asarray(v3_im).astype(int) - np.asarray(v2_im).astype(int)).max(2)
    kayit('Zemin ayni (tasinan ogeler disinda)', zf[dis].max() == 0, f'fark max {zf[dis].max()} ({int(dis.sum())} px karsilastirildi)')

    # 4) onizlemeler: ogeler pencere icinde
    ogeler = {'baslik': k3['baslik_murekkep'], 'satir2': s23, 'poster': k3['poster']}
    for w, h in ONIZ:
        o, pen = v2m.kirp(v3, w / h)
        o.resize((w, h), Image.LANCZOS).save(OUT / f'ONIZ_{w}x{h}.jpg', quality=92)
        ic = {a: pen[0] <= k[0] and k[2] <= pen[2] and pen[1] <= k[1] and k[3] <= pen[3] for a, k in ogeler.items()}
        pay = min(min(k[1] - pen[1], pen[3] - k[3]) for k in ogeler.values())
        kayit(f'Onizleme {w}x{h}', all(ic.values()), f'pencere {pen}; ' + ', '.join(f'{a} {"icinde" if v else "KESIK"}' for a, v in ic.items())
              + f'; en dar dikey pay {pay} px')

    # 5) pin 1000x1500 (ayni kural: Y1_v3 x 300-2100 bandi + zemin uzatmasi)
    pim, dikis = v2m.pin(m, v3)
    pim.save(OUT / 'PIN_Y1_v3.jpg', **JPEG)
    ic = all(v2m.PIN_X0 <= k[0] and k[2] <= v2m.PIN_X0 + v2m.PIN_W and v2m.PIN_Y0 <= k[1] and k[3] <= v2m.PIN_Y0 + v2m.PIN_H for k in ogeler.values())
    pp = Image.open(OUT / 'PIN_Y1_v3.jpg').convert('L'); o = 1000 / v2m.PIN_W
    bx = (int(np.ceil((px - v2m.PIN_X0) * o)) + 3, int(np.ceil((py - v2m.PIN_Y0) * o)) + 3,
          int((px + pw - v2m.PIN_X0) * o) - 3, int((py + ph - v2m.PIN_Y0) * o) - 3)
    kk = (bx[0] / o + v2m.PIN_X0, bx[1] / o + v2m.PIN_Y0, bx[2] / o + v2m.PIN_X0, bx[3] / o + v2m.PIN_Y0)
    n3 = v2m.ncc(pp.crop(bx), v3.convert('L').resize((bx[2] - bx[0], bx[3] - bx[1]), Image.LANCZOS, box=kk))
    kayit('PIN_Y1_v3', pim.size == (1000, 1500) and ic and n3 >= 0.99 and dikis < 4,
          f'{pim.size[0]}x{pim.size[1]}; Y1_v3 x {v2m.PIN_X0}-{v2m.PIN_X0 + v2m.PIN_W} bandi + zemin ust/alt {-v2m.PIN_Y0} px (dikis {dikis:.1f}); '
          f'baslik/satir 2/poster icinde {ic}; poster NCC {n3:.4f}')

    kontak(OUT, [('Y1_v2', y2), ('Y1_v3', v3)])
    fail = [a for a, ok, _ in OLC if not ok]
    with open(OUT / 'OLCUM.txt', 'w', encoding='utf-8') as fh:
        fh.write('Y1_v3 OLCUM (CANCER_LIBRA, ornek; Etsy yazma 0)\n')
        for a, ok, ay in OLC:
            fh.write(f"{'PASS' if ok else 'FAIL'} {a}: {ay}\n")
        fh.write(f"SONUC: {'PASS' if not fail else 'FAIL ' + ', '.join(fail)}\n")
    print('SONUC:', 'PASS' if not fail else 'FAIL ' + ', '.join(fail))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
