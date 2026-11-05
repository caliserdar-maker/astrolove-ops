#!/usr/bin/env python3
"""ESKI YOL (CI + WP) mesaj (tagline) satirinda FONT KERNING'i, siparis basina (Serdar 5 Kas "A"; 5 Kas siparis duzeltmesi).

VARSAYILAN KAPALI. Yalniz TAG_KERNING=raqm (siparis-dijital / siparis-giris girdisi tagline_kerning=raqm) iken etkin.

Neden: eski yol mesaj satirini pilot12.ciz_cap ile cizer (kisisel-v1 pilot6 kopyasi): HARF HARF d.text + getlength; her harf ayri
cizildigi icin (motor BASIC ya da RAQM olsun) harf ciftleri arasinda font kerning'i YOK. "Water" gibi kerning cifti olan metinde W-a boslugu 95 px (4960 px A2), font kerning'iyle ~62 px;
"W ater" iki kelime gibi okunuyor (Merkez + bagimsiz inceleme 5 Kas).

Ne yapar: pilot12.ciz_cap'i AYNI sozlesmeli (kirpilmis L maske, cap ustu, taban; "T" ayni fontla) ama metni RAQM duzeniyle TEK
SEFERDE cizen fonksiyonla degistirir. YALNIZ kern: OZELLIK = kern acik; liga / clig / calt / dlig / rlig KAPALI (inceleme 5 Kas
bulgu 1: varsayilan RAQM fi / fl / ff ligaturu de uygular, harf sekli degisirdi; onay yalniz kerning). Isim satiri (ciz_metin) DEGISMEZ. renk_ref (b8c8c4b) ve
kisisel-v1 kodu DEGISMEZ; sarma calisma aninda (amp_eski.kur deseni).
amp_eski.kur bunun USTUNE kurulur: kerning fonksiyonunun .eski'si kendisidir; amp_eski 'eski' olarak onu alir, boylece "&" iceren
metnin parcalari (amp_eski.dizgi) ve tek JPG & kapisi (surucu.py, getattr(ciz_cap, 'eski')) ayni kerning'li cizimi kullanir.
Raqm yoksa SystemExit (sessiz BASIC'e dusmek YOK).
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, features

MODLAR = ('kapali', 'raqm')
OZELLIK = ['kern', '-liga', '-clig', '-calt', '-dlig', '-rlig']


def raqm_var():
    """Pillow RAQM duzeni kullanilabilir mi (fribidi + harfbuzz). Yoksa SystemExit."""
    if not features.check('raqm'):
        raise SystemExit('HATA TAG_KERNING=raqm ama Pillow RAQM yok (fribidi/harfbuzz); sessiz BASIC yok, uretim durdu')
    return features.version('raqm')


def _font(fp, punto, wght):
    """kisisel_pilot.font_yukle ile ayni (degisken eksen; hata yutulur), yalniz layout_engine=RAQM."""
    f = ImageFont.truetype(str(fp), punto, layout_engine=ImageFont.Layout.RAQM)
    if wght is not None:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def _bbox(a):
    ys, xs = np.nonzero(a)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def ciz_cap_raqm(fp, wght, punto, metin):
    """pilot6.ciz_cap ile ayni sozlesme ve olculer (pad 200, yukseklik punto*3.2 + 2*pad, esik > 40, "T" referansi);
    tek fark: metin tek d.text cagrisiyla RAQM duzeninde (font kerning'i) cizilir."""
    ft = _font(fp, punto, wght)
    pad = 200

    def ciz(t):
        g = int(ft.getlength(t, features=OZELLIK)) + 2 * pad
        im = Image.new("L", (max(g, 10), int(punto * 3.2) + 2 * pad), 0)
        ImageDraw.Draw(im).text((float(pad), pad), t, fill=255, font=ft, features=OZELLIK)
        return im

    tb = _bbox(np.asarray(ciz("T")) > 40)
    s_im = ciz(metin)
    sb = _bbox(np.asarray(s_im) > 40)
    if sb is None or tb is None:
        return None, None, None
    return s_im.crop(sb), tb[1] - sb[1], tb[3] - sb[1]


ciz_cap_raqm.kerning = 'raqm'
ciz_cap_raqm.eski = ciz_cap_raqm          # amp_eski.kur 'eski' olarak bunu alir (& parcalari da kerning'li)


def kurulu(pilot12):
    f = pilot12.ciz_cap
    return bool(getattr(f, 'kerning', None) or getattr(getattr(f, 'eski', None), 'kerning', None))


def kur(pilot12):
    """pilot12.ciz_cap -> ciz_cap_raqm. amp_eski.kur'dan ONCE cagrilmali (sonra cagrilirsa SystemExit: & yolu BASIC kalirdi)."""
    raqm_var()
    if kurulu(pilot12):
        return pilot12.ciz_cap
    if getattr(pilot12.ciz_cap, 'eski', None) is not None:
        raise SystemExit('HATA tag_kerning.kur amp_eski.kur\'dan SONRA cagrildi (& parcalari BASIC kalirdi)')
    ciz_cap_raqm.onceki = pilot12.ciz_cap
    pilot12.ciz_cap = ciz_cap_raqm
    return ciz_cap_raqm


def bosluklar(L, esik=40):
    """Kirpilmis L maskesinde murekkep sutun kumeleri arasi bos kosular (px), soldan saga."""
    dolu = (np.asarray(L) > esik).any(axis=0)
    out, n, ic = [], 0, False
    for v in dolu:
        if v:
            if ic and n:
                out.append(n)
            ic, n = True, 0
        elif ic:
            n += 1
    return out


def surum():
    import PIL
    return {'pillow': PIL.__version__, 'raqm': features.version('raqm'), 'ozellik': OZELLIK}


def harf_aralari(rgb, elemanlar, alan_min=200):
    """RAPOR (kapi degil): son JPG'de & kapisinin buldugu her 'metin' elemaninin kutusunda murekkep bilesenleri (Otsu, koyu
    murekkep) soldan saga; ardisik bilesenler arasi en dar yatay bosluk (satir basina min, px). -> [[px, ...], ...]"""
    import cv2
    out = []
    for e in elemanlar or []:
        if e.get('tur') != 'metin' or not e.get('kutu'):
            continue
        x0, y0, x1, y1 = (int(v) for v in e['kutu'])
        g = cv2.cvtColor(np.ascontiguousarray(rgb[y0:y1, x0:x1]), cv2.COLOR_RGB2GRAY)
        _, m = cv2.threshold(g, 0, 1, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
        c = sorted([i for i in range(1, n) if st[i, 4] >= alan_min], key=lambda i: st[i, 0])
        ara = []
        for a, b in zip(c, c[1:]):
            gl = [int(np.nonzero(lab[y] == b)[0].min() - np.nonzero(lab[y] == a)[0].max() - 1)
                  for y in range(lab.shape[0]) if (lab[y] == a).any() and (lab[y] == b).any()]
            ara.append(min(gl) if gl else None)
        out.append(ara)
    return out
