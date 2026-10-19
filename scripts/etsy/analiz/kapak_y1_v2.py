#!/usr/bin/env python3
"""Yil donumu kapagi Y1 renk duzeltmesi, ORNEK CANCER_LIBRA (19 Eki 2026). Etsy'ye yazmaz; yalniz dosya uretir.

Taban: onayli Y1 (Drive KAPAK_ADAY_20261019/Y1.jpg), kapak_aday.py (a67e737) yil_ailesi Y1 yerlesimi ve bizim-yilimiz-v3
kod/by_kapak.py tasarim ogeleri. Tek degisiklik: "CANCER logo LIBRA" satiri (yazi + sonsuzluk logosu) RENK_SATIR2 yerine
basligin rengi RENK_BASLIK ile cizilir. Zemin, yazi tipi, boyutlar, poster yeri/olcegi ayni; poster pikseli degismez.
Ciktilar: Y1_v2.jpg (2400x2400), ONIZ_<wxh>.jpg (300x225, 300x300, 225x300 merkez kirpim), PIN_Y1_v2.jpg (1000x1500:
Y1_v2'nin x 300-2100 bandi, ustte/altta 150 px ayni formulle uzatilan zemin), KONTAK_Y1_v2.jpg, OLCUM.txt.
QC (her satir PASS/FAIL, herhangi FAIL -> cikis 1):
  Y1 yeniden uretimi = Drive Y1.jpg (fark max 0); baslik rengi Y1 piksellerinden olculur, koddaki deger ile dE76;
  Y1_v2'de satir 2 yazisi ve logo ile baslik arasinda dE76 < 2; satir 2 kutusu (+16 px JPEG blok payi) disinda
  Y1 ile fark 0; poster NCC >= 0.99 (Y1 ile ve kaynak posterle); baslik/satir 2/poster 4:3, 1:1, 3:4 ve pin icinde.
Kaynak klasoru (K): by/ (kod/by_kapak.py, galeri/, cikti/CANCER_LIBRA/poster/4_Layers_8x10.jpg), Y1.jpg
Kullanim: kapak_y1_v2.py --kaynak K --cikti OUT
"""
import argparse
import importlib.util
import io
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PAIR, B1, B2 = 'CANCER_LIBRA', 'CANCER', 'LIBRA'
ONIZ = [(300, 225), (300, 300), (225, 300)]
PIN_W, PIN_H, PIN_X0, PIN_Y0 = 1800, 2700, 300, -150     # 2400 tuvalde pin bandi, sonra 1000x1500
JPEG = dict(quality=95, subsampling=0, dpi=(300, 300))
OLC = []


def kayit(ad, ok, ayrinti):
    OLC.append((ad, bool(ok), ayrinti))
    print(f"{'PASS' if ok else 'FAIL'} {ad}: {ayrinti}")


def ncc(a, b):
    a = np.asarray(a, np.float64).ravel(); b = np.asarray(b, np.float64).ravel()
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def kirp(im, oran):
    w, h = im.size
    if w / h > oran:
        nw = round(h * oran); x = (w - nw) // 2
        return im.crop((x, 0, x + nw, h)), (x, 0, x + nw, h)
    nh = round(w / oran); y = (h - nh) // 2
    return im.crop((0, y, w, y + nh)), (0, y, w, y + nh)


def jpeg(im):
    b = io.BytesIO(); im.save(b, 'JPEG', **JPEG)
    return Image.open(io.BytesIO(b.getvalue())).convert('RGB')


def lab(rgb):
    return cv2.cvtColor(np.array([[rgb]], np.float32) / 255, cv2.COLOR_RGB2LAB)[0, 0]


def de(a, b):
    return float(np.linalg.norm(lab(a) - lab(b)))


def renk_olc(arr, kutu):
    """kutu icindeki yazi cekirdegi: parlaklik ust %10 (zemin koyu bordo); medyan RGB."""
    x0, y0, x1, y1 = (int(round(v)) for v in kutu)
    p = arr[y0:y1, x0:x1].reshape(-1, 3).astype(np.float32)
    L = p.mean(1)
    c = p[L >= np.percentile(L, 90)]
    return tuple(float(v) for v in np.median(c, 0)), len(c)


def by_yukle(K):
    os.environ.update(BY_ROOT=str(K / 'by'), PAIR=PAIR, OUT=str(K / '_kullanilmaz.jpg'))
    spec = importlib.util.spec_from_file_location('by_kapak', K / 'by/kod/by_kapak.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def y1_ciz(m, renk2):
    """kapak_aday.py (a67e737) yil_ailesi Y1 ile ayni adimlar; yalniz satir 2 + logo rengi parametre."""
    S, P0_, P1_, PAY = m.S, 300, 2100, 60
    c1 = m.hx(m.RENK_BASLIK)
    s1 = 230
    while m.serif(s1).getlength(m.BASLIK, features=['lnum']) > (P1_ - P0_) - 2 * PAY:
        s1 -= 2
    ust = P0_ + 50
    py = ust + s1 + 245
    ph = (P1_ - 50) - py; pw = round(ph / 1.25); ph = round(pw * 1.25)
    px = (S - pw) // 2
    bg = m.poster_yerlestir(m.zemin(), px, py, pw)
    gy = (ust + s1 + py) / 2 + 5
    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    f1 = m.serif(s1)
    d.text((S / 2, ust + s1 / 2), m.BASLIK, font=f1, fill=c1, anchor='mm', features=['lnum'])
    bb1 = d.textbbox((S / 2, ust + s1 / 2), m.BASLIK, font=f1, anchor='mm', features=['lnum'])

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
    # olcum kutulari: yazi kutulari font bbox'tan, logo yapistirma yerinden
    yb = [d.textbbox((x0, gy), B1, font=f2, anchor='lm'), d.textbbox((lx + m.LOGO_W + m.LOGO_BOSLUK, gy), B2, font=f2, anchor='lm')]
    kut = {'baslik': bb1, 'satir2': (x0, min(gy - ns / 2, ly), x0 + top, max(gy + ns / 2, ly + lg.height)),
           'poster': (px, py, px + pw, py + ph + 30),
           'satir2_yazi_' + B1: (x0, yb[0][1], lx - m.LOGO_BOSLUK, yb[0][3]),
           'satir2_logo': (round(lx), ly, round(lx) + lg.width, ly + lg.height),
           'satir2_yazi_' + B2: (lx + m.LOGO_W + m.LOGO_BOSLUK, yb[1][1], x0 + top, yb[1][3])}
    return im, kut, dict(s1=s1, ns=ns, poster=(px, py, pw, ph))


def zemin_bant(m, y0, y1, x0, x1, tohum):
    """by_kapak.zemin() formulu, 0-S disindaki satirlar icin (pin uzatmasi)."""
    S = m.S
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    r = np.sqrt(((xx - S * 0.5) / (S * 0.72)) ** 2 + ((yy - S * m.GRAD_Y) / (S * 0.72)) ** 2)
    k = (np.clip(r, 0, 1) ** 1.6)[..., None]
    bg = np.array(m.hx(m.GRAD_ORTA), np.float32) * (1 - k) + np.array(m.hx(m.GRAD_KENAR), np.float32) * k
    bg *= (1 - m.UST_KOYU * np.clip(1 - yy / (S * 0.42), 0, 1) ** 1.4)[..., None]
    rng = np.random.default_rng(tohum)
    bg += cv2.GaussianBlur(rng.normal(0, 1, yy.shape).astype(np.float32), (0, 0), 1.3)[..., None] * 255 * 0.018
    return bg


def pin(m, v2):
    a = np.asarray(v2).astype(np.float32)
    out = np.empty((PIN_H, PIN_W, 3), np.float32)
    ust = -PIN_Y0
    out[:ust] = zemin_bant(m, PIN_Y0, 0, PIN_X0, PIN_X0 + PIN_W, 11)
    out[ust:ust + m.S] = a[:, PIN_X0:PIN_X0 + PIN_W]
    out[ust + m.S:] = zemin_bant(m, m.S, PIN_Y0 + PIN_H, PIN_X0, PIN_X0 + PIN_W, 12)
    dikis = max(np.abs(out[ust - 3:ust].mean((0, 1)) - out[ust:ust + 3].mean((0, 1))).max(),
                np.abs(out[ust + m.S - 3:ust + m.S].mean((0, 1)) - out[ust + m.S:ust + m.S + 3].mean((0, 1))).max())
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).resize((1000, 1500), Image.LANCZOS)
    return im, float(dikis)


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
            o = kirp(im, w / h)[0].resize((w, h), Image.LANCZOS)
            sh.paste(o, (xx, y + (300 - h)))
            d.rectangle((xx - 1, y + (300 - h) - 1, xx + w, y + 300), outline=(200, 200, 200))
            d.text((xx, y + 306), f'{w}x{h}', font=f, fill=(90, 90, 90))
            xx += w + 15
    sh.save(out / 'KONTAK_Y1_v2.jpg', quality=92)
    print(f'KONTAK_Y1_v2.jpg {sh.size[0]}x{sh.size[1]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    g = ap.parse_args()
    K, OUT = Path(g.kaynak).resolve(), Path(g.cikti).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    m = by_yukle(K)
    c1, c2 = m.hx(m.RENK_BASLIK), m.hx(m.RENK_SATIR2)
    y1 = Image.open(K / 'Y1.jpg').convert('RGB')
    y1a = np.asarray(y1)

    # 1) taban: Y1 yeniden uretimi = Drive Y1
    r_im, kut, p = y1_ciz(m, c2)
    fark = np.abs(np.asarray(jpeg(r_im)).astype(int) - y1a.astype(int)).max()
    kayit('Y1 yeniden uretim = Drive Y1.jpg', fark == 0 and y1.size == (m.S, m.S), f'fark max {fark}; baslik {p["s1"]}px, satir2 {p["ns"]}px, poster {p["poster"]}')

    # 2) renk olcumu (Drive Y1 pikselleri)
    rb, nb = renk_olc(y1a, kut['baslik'])
    rs, ns_ = renk_olc(y1a, kut['satir2_yazi_' + B1])
    rl, nl = renk_olc(y1a, kut['satir2_logo'])
    f = lambda c: '#' + ''.join(f'{round(v):02X}' for v in c)
    kayit('Y1 baslik rengi (olcum) ~ kod RENK_BASLIK', de(rb, c1) < 2,
          f'olculen {f(rb)} ({nb} px, ust %10 parlaklik medyani), kod #{m.RENK_BASLIK}, dE76 {de(rb, c1):.2f}')
    print(f'BILGI Y1 satir 2 olculen: yazi {f(rs)} ({ns_} px), logo {f(rl)} ({nl} px); kod #{m.RENK_SATIR2}; baslikla dE76 {de(rs, rb):.1f} / {de(rl, rb):.1f}')

    # 3) Y1_v2: satir 2 + logo = baslik rengi
    v2_im, kut2, _ = y1_ciz(m, c1)
    ham = np.asarray(v2_im).astype(int)
    v2_im.save(OUT / 'Y1_v2.jpg', **JPEG)
    v2 = Image.open(OUT / 'Y1_v2.jpg').convert('RGB'); v2a = np.asarray(v2)
    vb = renk_olc(v2a, kut2['baslik'])[0]
    for k in ('satir2_yazi_' + B1, 'satir2_logo', 'satir2_yazi_' + B2):
        vk = renk_olc(v2a, kut2[k])[0]
        kayit(f'Y1_v2 {k} rengi = baslik', de(vk, vb) < 2, f'{f(vk)} / baslik {f(vb)}, dE76 {de(vk, vb):.2f}')

    # 4) degisim yalniz satir 2 kutusunda
    k2 = kut2['satir2']                              # floor/ceil + 2 px kenar yumusatma payi
    x0, y0, x1, y1_ = int(np.floor(k2[0])) - 2, int(np.floor(k2[1])) - 2, int(np.ceil(k2[2])) + 3, int(np.ceil(k2[3])) + 3
    dis = np.ones(ham.shape[:2], bool); dis[y0:y1_, x0:x1] = False
    ham_fark = np.abs(ham - np.asarray(r_im).astype(int)).max(2)
    dis16 = np.ones(ham.shape[:2], bool); dis16[max(0, y0 - 16):y1_ + 16, max(0, x0 - 16):x1 + 16] = False
    jfark = np.abs(v2a.astype(int) - y1a.astype(int)).max(2)
    kayit('Y1_v2 degisim yalniz satir 2', ham_fark[dis].max() == 0 and jfark[dis16].max() == 0 and ham_fark[~dis].max() > 0,
          f'satir 2 kutusu x {x0}-{x1} y {y0}-{y1_}; disarida fark (JPEG oncesi) {ham_fark[dis].max()}, (JPEG, +16 px) {jfark[dis16].max()}; '
          f'icerde degisen piksel {int((ham_fark[~dis] > 0).sum())}')
    px, py, pw, ph = p['poster']
    n1 = ncc(v2a[py + 5:py + ph - 5, px + 5:px + pw - 5].mean(2), y1a[py + 5:py + ph - 5, px + 5:px + pw - 5].mean(2))
    ref = Image.open(K / 'by/cikti' / PAIR / 'poster/4_Layers_8x10.jpg').convert('L').resize((pw, ph), Image.LANCZOS).crop((5, 5, pw - 5, ph - 5))
    n2 = ncc(np.asarray(v2.convert('L'))[py + 5:py + ph - 5, px + 5:px + pw - 5], ref)
    kayit('Y1_v2 poster NCC', n1 >= 0.99 and n2 >= 0.99, f'Y1 ile {n1:.4f}, kaynak poster ile {n2:.4f}; poster {pw}x{ph} @({px},{py}) (Y1 ile ayni)')

    # 5) onizlemeler
    for w, h in ONIZ:
        o, pen = kirp(v2, w / h)
        o.resize((w, h), Image.LANCZOS).save(OUT / f'ONIZ_{w}x{h}.jpg', quality=92)
        ic = {a: pen[0] <= k[0] and k[2] <= pen[2] and pen[1] <= k[1] and k[3] <= pen[3] for a, k in kut2.items() if a in ('baslik', 'satir2', 'poster')}
        kayit(f'Onizleme {w}x{h}', all(ic.values()), f'pencere {pen}; ' + ', '.join(f'{a} {"icinde" if v else "KESIK"}' for a, v in ic.items()))

    # 6) pin 1000x1500
    pim, dikis = pin(m, v2)
    pim.save(OUT / 'PIN_Y1_v2.jpg', **JPEG)
    pk = {a: kut2[a] for a in ('baslik', 'satir2', 'poster')}
    ic = all(PIN_X0 <= k[0] and k[2] <= PIN_X0 + PIN_W and PIN_Y0 <= k[1] and k[3] <= PIN_Y0 + PIN_H for k in pk.values())
    pp = Image.open(OUT / 'PIN_Y1_v2.jpg').convert('L'); o = 1000 / PIN_W
    bx = (int(np.ceil((px - PIN_X0) * o)) + 3, int(np.ceil((py - PIN_Y0) * o)) + 3,
          int((px + pw - PIN_X0) * o) - 3, int((py + ph - PIN_Y0) * o) - 3)
    kaynak_kutu = (bx[0] / o + PIN_X0, bx[1] / o + PIN_Y0, bx[2] / o + PIN_X0, bx[3] / o + PIN_Y0)   # pin kutusunun Y1_v2 karsiligi
    n3 = ncc(pp.crop(bx), v2.convert('L').resize((bx[2] - bx[0], bx[3] - bx[1]), Image.LANCZOS, box=kaynak_kutu))
    kayit('PIN_Y1_v2', pim.size == (1000, 1500) and ic and n3 >= 0.99 and dikis < 4,
          f'{pim.size[0]}x{pim.size[1]}; Y1_v2 x {PIN_X0}-{PIN_X0 + PIN_W} bandi, zemin ust/alt {-PIN_Y0} px uzatma (dikis farki {dikis:.1f}); baslik/satir2/poster icinde {ic}; poster NCC {n3:.4f}')

    kontak(OUT, [('Y1 (eski)', y1), ('Y1_v2', v2)])
    fail = [a for a, ok, _ in OLC if not ok]
    with open(OUT / 'OLCUM.txt', 'w', encoding='utf-8') as fh:
        fh.write('Y1_v2 OLCUM (CANCER_LIBRA, ornek; Etsy yazma 0)\n')
        for a, ok, ay in OLC:
            fh.write(f"{'PASS' if ok else 'FAIL'} {a}: {ay}\n")
        fh.write(f"SONUC: {'PASS' if not fail else 'FAIL ' + ', '.join(fail)}\n")
    print('SONUC:', 'PASS' if not fail else 'FAIL ' + ', '.join(fail))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
