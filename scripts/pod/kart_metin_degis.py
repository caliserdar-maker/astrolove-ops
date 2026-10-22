#!/usr/bin/env python3
"""Duvar zeminli galeri kartinda tek satir metin degistirme (Serdar 17 Eki, eski 78 cerceve temizligi, gorsel ornegi).
Kartlar kart_duvar_genel.py ciktisidir: yazi disi zemin = duvar (DUVAR.png), fark <= 5 (olculdu, 17 Eki).
Her degisiklik: (silme kutusu, eski metin, yeni metin, font ailesi, hizalama).
  1) kutu icinde eski satirin murekkep kutusu bulunur (|kart - duvar| > 40).
  2) punto ve harf araligi (verilmezse agirlik da) ESKI metni ayni kutuya cizip pikselce en iyi eslesen secilir.
     Ayni stildeki satirlar icin agirlik sabitlenir (agirliklar=(500,)): satir basina uydurma tutarsiz agirlik veriyordu.
  3) renk: eski satirin en koyu %3 piksellerinin medyani.
  4) kutu duvar pikseliyle silinir, yeni metin ayni taban cizgisi + ayni hizalama (sol kenar ya da merkez) ile basilir.
QC: yeni metin kutu icinde kalir; kutu disi piksel degismez (JPEG haric, <= 6); uzun/orta tire yok.
Kullanim (kutuphane): degistir(kart_img, duvar_img, fontlar_dir, [Degisiklik...]) -> (img, rapor)"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

AILE = {"mont": ("Montserrat[wght].ttf", (300, 400, 500, 600)), "gar": ("EBGaramond[wght].ttf", (400, 500))}


def _font(fd, aile, s, w):
    f = ImageFont.truetype(os.path.join(fd, AILE[aile][0]), s)
    f.set_variation_by_axes([w])
    return f


def _gen(f, t, tr):
    if tr == 0:
        b = f.getbbox(t, anchor="ls"); return b[0], b[2]
    x = 0.0; x0 = None; x1 = 0
    for ch in t:
        b = f.getbbox(ch, anchor="ls")
        if ch.strip():
            x0 = x + b[0] if x0 is None else x0; x1 = x + b[2]
        x += f.getlength(ch) + tr
    return x0 or 0, x1


def _ciz(d, xy, t, f, renk, tr):
    if tr == 0:
        d.text(xy, t, font=f, fill=renk, anchor="ls"); return
    x, y = xy
    for ch in t:
        d.text((x, y), ch, font=f, fill=renk, anchor="ls"); x += f.getlength(ch) + tr


def murekkep(K, D, kutu, esik=40):
    x0, y0, x1, y1 = kutu
    d = np.abs(np.asarray(K)[y0:y1, x0:x1].astype(int) - np.asarray(D)[y0:y1, x0:x1].astype(int)).max(2) > esik
    ys, xs = np.nonzero(d)
    return (x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1)


def olc(K, D, fd, kutu, eski, aile, izler=(0,), agirliklar=None):
    """eski metnin murekkep kutusuna en iyi uyan (agirlik, punto, iz, taban, sol, renk)."""
    mk = murekkep(K, D, kutu)
    Ka = np.asarray(K).astype(int)
    pay = (mk[0] - 8, mk[1] - 8, mk[2] + 8, mk[3] + 8)
    hedef = Ka[pay[1]:pay[3], pay[0]:pay[2]]
    koyu = hedef.reshape(-1, 3)[hedef.sum(2).reshape(-1).argsort()[: max(20, hedef.size // 3 // 33)]]
    renk = tuple(int(v) for v in np.median(koyu, 0))
    en = None
    for w in (agirliklar or AILE[aile][1]):
        for tr in izler:
            # puntoyu genislige gore bul
            for s in range(10, 200):
                g0, g1 = _gen(_font(fd, aile, s, w), eski, tr)
                if g1 - g0 >= mk[2] - mk[0]:
                    break
            for s_ in (s - 1, s):
                f = _font(fd, aile, s_, w); g0, g1 = _gen(f, eski, tr); b = f.getbbox(eski, anchor="ls")
                x = mk[0] - g0; y = mk[1] - b[1]
                im = D.crop(pay).copy(); _ciz(ImageDraw.Draw(im), (x - pay[0], y - pay[1]), eski, f, renk, tr)
                e = float(np.abs(np.asarray(im).astype(int) - hedef).mean())
                if en is None or e < en[0]:
                    en = (e, w, s_, tr, y, mk, renk)
    return dict(hata=round(en[0], 2), agirlik=en[1], punto=en[2], iz=en[3], taban=en[4], murekkep=tuple(int(v) for v in en[5]), renk=en[6])


def degistir(K, D, fd, isler):
    """isler: [dict(kutu, eski, yeni(list: [(metin, merkez_x|None)] ya da str), aile, hiza('sol'|'merkez'), izler)]"""
    out = K.copy(); d = ImageDraw.Draw(out); rapor = []
    for i in isler:
        o = olc(K, D, fd, i["kutu"], i["eski"], i["aile"], i.get("izler", (0,)), i.get("agirliklar"))
        out.paste(D.crop(i["kutu"]), i["kutu"][:2])
        f = _font(fd, i["aile"], o["punto"], o["agirlik"])
        renk = i.get("renk") or o["renk"]
        yeniler = i["yeni"] if isinstance(i["yeni"], list) else [(i["yeni"], None)]
        for t, cx in yeniler:
            if not t:
                continue
            g0, g1 = _gen(f, t, o["iz"])
            if i["hiza"] == "sol":
                x = o["murekkep"][0] - g0
            else:
                c = cx if cx is not None else (o["murekkep"][0] + o["murekkep"][2]) / 2
                x = c - (g0 + g1) / 2
            taban = o["taban"] + i.get("dy", 0)
            _ciz(d, (x, taban), t, f, renk, o["iz"])
            kx0, kx1 = x + g0, x + g1
            k = i["kutu"]
            bb = f.getbbox(t, anchor="ls")
            if kx0 < k[0] or kx1 > k[2] or taban + bb[1] < k[1] or taban + bb[3] > k[3]:
                raise SystemExit(f"yeni metin kutu disina tasti: {t!r} {kx0:.0f}-{kx1:.0f} kutu {k}")
            if any(ch in t for ch in "—–"):
                raise SystemExit(f"uzun/orta tire: {t!r}")
        rapor.append(dict(eski=i["eski"], yeni=[t for t, _ in yeniler], **o))
    return out, rapor
