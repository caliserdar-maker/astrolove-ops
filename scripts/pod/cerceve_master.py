#!/usr/bin/env python3
"""Master cerceve sistemi (ChatGPT karari + Serdar set kurali, 27 Eyl 2026).
Tek kaynak: kapak, kart 02/07/12/14/15/16 ve sahneler ayni fonksiyonlari kullanir.
- Her kaplama kendi GERCEK Prodigi fotografindan; hicbir sey cizilmez.
  AG: 059 on cephe bos cerceve, 9 parca. BK/WH/NA: chevron fotografindan FxF gercek
  miter kose blogu (4 koseye aynalanir) + ayni kolun duz seritleri.
- Set kurali: cerceve rengi SABIT (dusuk yogunluklu ortam isigi disinda oynanmaz);
  sahne atmosferi set koridoruna cekilir (beyaz dengesi DUVAR oranina dogru, %40 guc, +-%6 sinir).
- Golge iki katman: temas (keskin, yakin) + duvar (yumusak), yon alt-sag.
QC yardimi: renk_kilidi() cerceve yuz ortalamasini kaynak referansla karsilastirir.
"""
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

DUVAR = (216, 209, 202)


def _maske(im):
    a = np.asarray(im).astype(int); m = (255 - a.min(2)) > 10
    m = ndimage.binary_opening(m, iterations=2); lab, k = ndimage.label(m)
    return lab == (np.argmax(ndimage.sum(m, lab, range(1, k + 1))) + 1)


def _dondur(src, aci):
    return src.rotate(aci, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))


def _ilk(v):
    kop = np.where(np.diff(v) > 1)[0]
    return v[:kop[0] + 1] if len(kop) else v


def parcalar(yol):
    """Chevron fotografini Γ konumuna dondurur; FxF gercek miter KOSE blogu + dikey/yatay duz seritler."""
    src = Image.open(yol).convert('RGB')
    m0 = _maske(_dondur(src, -45)); ys, xs = np.where(m0); y0 = ys.min()
    Yy = np.arange(y0 + 400, y0 + 1150, 10)
    Xx = np.array([np.where(m0[y, :])[0].min() for y in Yy])
    aci = float(np.degrees(np.arctan(np.polyfit(Yy, Xx, 1)[0])))
    im = _dondur(src, -45 - aci); m = _maske(im)
    dis, ic = [], []
    ys, xs = np.where(m); y0 = ys.min()
    for y in range(y0 + 400, y0 + 1150, 10):
        v = _ilk(np.where(m[y, :])[0]); dis.append(v.min()); ic.append(v.max())
    x_dis, x_ic = max(dis) + 1, min(ic)
    dis2, ic2 = [], []
    for x in range(x_dis + 400, x_dis + 1150, 10):
        v = _ilk(np.where(m[:, x])[0]); dis2.append(v.min()); ic2.append(v.max())
    y_dis, y_ic = max(dis2) + 1, min(ic2)
    fs = min(x_ic - x_dis, y_ic - y_dis)
    kose = im.crop((x_dis, y_dis, x_dis + fs, y_dis + fs))
    s_v = im.crop((x_dis, y_dis + 400, x_dis + fs, y_dis + 1150))
    s_h = im.crop((x_dis + 400, y_dis, x_dis + 1150, y_dis + fs))
    return kose, s_v, s_h


def _lip(poster):
    pa = np.asarray(poster).astype(np.float32)
    PH, PW = pa.shape[:2]
    yy = np.arange(PH)[:, None]; xx = np.arange(PW)[None, :]
    g = 1 - 0.22 * np.exp(-yy / 10.0) - 0.16 * np.exp(-xx / 10.0) - 0.06 * np.exp(-(PH - 1 - yy) / 5.0) - 0.06 * np.exp(-(PW - 1 - xx) / 5.0)
    return Image.fromarray(np.clip(pa * g[..., None], 0, 255).astype(np.uint8))


def cerceve_chevron(yol, poster, F):
    """BK/WH/NA master kompozit: gercek kose bloklari + duz seritler + ic dudak golgesi."""
    PW, PH = poster.size; OW, OH = PW + 2 * F, PH + 2 * F
    fr = Image.new('RGB', (OW, OH)); fr.paste(_lip(poster), (F, F))
    kose, s_v, s_h = parcalar(yol)
    K = kose.resize((F, F), Image.LANCZOS)
    V = s_v.resize((F, OH - 2 * F), Image.LANCZOS)
    Hs = s_h.resize((OW - 2 * F, F), Image.LANCZOS)
    fr.paste(Hs, (F, 0)); fr.paste(Hs.transpose(Image.FLIP_TOP_BOTTOM), (F, OH - F))
    fr.paste(V, (0, F)); fr.paste(V.transpose(Image.FLIP_LEFT_RIGHT), (OW - F, F))
    fr.paste(K, (0, 0)); fr.paste(K.transpose(Image.FLIP_LEFT_RIGHT), (OW - F, 0))
    fr.paste(K.transpose(Image.FLIP_TOP_BOTTOM), (0, OH - F))
    fr.paste(K.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM), (OW - F, OH - F))
    return fr


def cerceve_blank(yol, poster, F):
    """AG master kompozit: Prodigi 059 on cephe bos cerceve, 9 parca. Olculen dis (455,282)-(1543,1672), kirpim 46 px."""
    src = Image.open(yol).convert('RGB'); X0, Y0, X1, Y1, f = 455, 282, 1544, 1673, 46
    PW, PH = poster.size; OW, OH = PW + 2 * F, PH + 2 * F
    fr = Image.new('RGB', (OW, OH)); fr.paste(_lip(poster), (F, F))
    r = lambda b, w, h: src.crop(b).resize((w, h), Image.LANCZOS)
    fr.paste(r((X0 + f, Y0, X1 - f, Y0 + f), OW - 2 * F, F), (F, 0))
    fr.paste(r((X0 + f, Y1 - f, X1 - f, Y1), OW - 2 * F, F), (F, OH - F))
    fr.paste(r((X0, Y0 + f, X0 + f, Y1 - f), F, OH - 2 * F), (0, F))
    fr.paste(r((X1 - f, Y0 + f, X1, Y1 - f), F, OH - 2 * F), (OW - F, F))
    fr.paste(r((X0, Y0, X0 + f, Y0 + f), F, F), (0, 0)); fr.paste(r((X1 - f, Y0, X1, Y0 + f), F, F), (OW - F, 0))
    fr.paste(r((X0, Y1 - f, X0 + f, Y1), F, F), (0, OH - F)); fr.paste(r((X1 - f, Y1 - f, X1, Y1), F, F), (OW - F, OH - F))
    return fr


def set_grade(sahne):
    """Sahne atmosferini set koridoruna ceker: beyaz dengesi DUVAR oranina dogru %40, kanal basina +-%6 sinir."""
    a = np.asarray(sahne).astype(np.float32)
    ort = a.reshape(-1, 3).mean(0)
    hedef = np.array(DUVAR, np.float32) / np.mean(DUVAR) * ort.mean()
    kazanc = np.clip(1 + 0.4 * (hedef / ort - 1), 0.94, 1.06)
    return Image.fromarray(np.clip(a * kazanc[None, None, :], 0, 255).astype(np.uint8)), [round(float(k), 3) for k in kazanc]


def sahne_isik(fr, sahne, kutu, guc=0.12):
    """Cerceveye sahnenin renk sicakligini dusuk yogunlukta verir; kaplamanin gercek rengi korunur.
    kutu: cercevenin sahnedeki (x0,y0,x1,y1) yeri; ortam rengi cevresinden olculur."""
    a = np.asarray(sahne).astype(np.float32)
    x0, y0, x1, y1 = kutu; p = 40
    cev = np.concatenate([a[max(0, y0 - p):y0, x0:x1].reshape(-1, 3), a[y1:y1 + p, x0:x1].reshape(-1, 3)])
    if len(cev) == 0:
        return fr
    ton = cev.mean(0); ton = ton / ton.mean()
    fa = np.asarray(fr).astype(np.float32) * (1 + guc * (ton - 1))[None, None, :]
    return Image.fromarray(np.clip(fa, 0, 255).astype(np.uint8))


def temas_golge(sahne, kutu):
    """Iki katman golge sahneye, cerceve yapistirilmadan ONCE: temas (dx4 dy6 s6 0.30) + yumusak (dx12 dy16 s24 0.14)."""
    x0, y0, x1, y1 = kutu
    a = np.asarray(sahne).astype(np.float32)
    for dx, dy, sg, guc in [(12, 16, 24, 0.14), (4, 6, 6, 0.30)]:
        sil = Image.new('L', sahne.size, 0)
        sil.paste(255, (x0 + dx, y0 + dy, x1 + dx, y1 + dy))
        m = np.asarray(sil.filter(ImageFilter.GaussianBlur(sg))).astype(np.float32) / 255
        a = a * (1 - guc * m)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def renk_kilidi(cikti_arr, kutu, F, referans_ort):
    """QC: ciktida cerceve yuzunun (ust kenar orta bandi) ortalama rengi, kaynak referansindan sapmasi."""
    x0, y0, x1, y1 = kutu
    bant = cikti_arr[y0 + 2:y0 + F - 2, (x0 + x1) // 2 - 100:(x0 + x1) // 2 + 100].reshape(-1, 3).mean(0)
    return float(np.abs(bant - np.asarray(referans_ort, np.float32)).max())
