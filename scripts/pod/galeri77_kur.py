#!/usr/bin/env python3
"""77 cift galerisi (Serdar 28 Eyl): CL kesin paketinin (86296c5) onayli KREM kaynak kartlari cifte uyarlanir.
Duvar zemini, yazi kontrasti ve QC sonra CL ile ayni hattan gecer (galeri77_cift.sh). Cifte bagli olmayan hicbir
piksel degismez; poster, sembol ve isim yeniden cizilmez (hep ciftin baski dosyasindan / kapaktan kirpim).

Cifte bagli ogeler (olcumler CL kartlarindan; tahmin yok):
  ust etiket 03-14 : 'ASTROLOVE  /  {A} + {B}' Montserrat 500 37 px, (140, taban 121), renk (133,116,83)
                     (CL etiketine NCC 0.97; 02'nin etiketi kart02_duvar_kur.py'de Lato, orada yazilir)
  02 : 3 poster ; 04 : poster bandi ; 13 : poster  -> "sanal onayli kapak posteri": ciftin MB baskisi, CL onayli
       kapaginin poster kirpimina (734,130,2268,2118) CL MB baskisiyla olculen esleme (KAPAK_ESLEME) ile tasinir
       (isik aktarimi yok: onayli kapak eski baski surumunden).
       Sonra CL ile ayni kirpimlar: 02 586x760 (+ cerceve _lip), 04 bant (90,1195,1483,1829), 13 961x1225.
  03 : alt baslik; panel: iki burc sembolu (MB baskidaki kucuk semboller, alfa ayristirma, CL ile ayni olcek),
       etiketler (Montserrat 550 42), birlesik sembol (sanal kapak posterinden, kart03_duzelt yontemi)
  04 : 'Name under {A}' / 'Name under {B}' (ayni burc: 'Left name' / 'Right name'), 'EMILY = {A}    JAMES = {B}'
       (ayni burc: 'EMILY = LEFT    JAMES = RIGHT'); ayni burcta baslik/alt baslik 'side' ile
  05 : 5 kucuk poster = 5 renk baski (kutu oranina merkez kirpim), ayni kutular (kart05v2_kur)
  06/09/10/11 : kart_cila_kur.kur, poster = ciftin baskisi ('baski' kipi); ust etiket ciftin
  07 : 4 cerceve ici = MB baski (rebate kirpik, 4:5 merkez), kart07_kur ic dudak formulu, ayni yerler
  12 : kart09_duzelt duzeni; yakin plan penceresi CL penceresinin altin yogunluguna gore sembol uzerinde secilir
  14 : yalniz ust etiket
Cikti: KREM_DIR/<kart>.jpg (02-14), KREM_DIR/METIN.json (gorunen metinler, metin_qc icin), KREM_DIR/KUR.json
Kullanim: galeri77_kur.py CIFT KAYNAK_DIR CL_MB_BASKI.jpg FONT_DIR KREM_DIR
  KAYNAK_DIR: KAPAK.jpg + BASKI_<RENK>.jpg (5 renk, 11x14 EMILY/JAMES)
"""
import csv
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kart_cila_kur as KC                                     # noqa: E402
from cerceve_master import _lip                                 # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
KREM_CL = os.path.join(ROOT, 'data/pod/cl_galeri_krem_kaynak')
ONAYLI = os.path.join(ROOT, 'data/pod/cl_referans/CL_kapak_onayli_3000x2250.jpg')
SAHNE_DIR = os.path.join(ROOT, 'data/pod/gpt_sahne_cila')
BG = (237, 232, 226); NAVY = (6, 17, 37); SANS_T = (23, 25, 30); NAVY_T = (25, 34, 49)
RENKLER = ['MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY', 'WARM_PARCHMENT']

# --- olculen sabitler (CL krem kartlari + CL MB baski; olcum: galeri77_olc.py) ---
ETIKET = dict(boy=37, w=500, x=140, taban=121, renk=(133, 116, 83), sil=(128, 78, 1300, 134))
KAPAK_KIRP = (734, 130, 2268, 2118)                  # onayli kapakta poster (kart02/04/08 kirpimi)
KAPAK_ESLEME = (24, -10, 3276, 4204)                 # MB baskida -> onayli kapak posteri (olculdu, NCC 0.958); tasan kenar kopyalanir
PANEL_SEMBOL = dict(sol=(1660, 703), sag=(2480, 704), olcek=1.07, azami=(400, 300))   # olcek: CL panel/baski sembol boyu (1.06-1.085)
PANEL_ETIKET = dict(boy=42, w=550, taban=921, renk=(198, 182, 127))
PANEL_BIRLESIK = dict(merkez=(2075, 1644), kutu=(611, 567))
PANEL_SIL = [(1492, 552, 1832, 858), (2285, 552, 2676, 858), (1440, 878, 1880, 934), (2260, 878, 2700, 934),
             (1745, 1343, 2405, 1948)]
MB_KUCUK = (2600, 3000, (400, 1653), (1653, 2900))   # MB baskida kucuk sembol bandi (y 2665-2933 olculdu, 3 cift) ve sol/sag x araligi


def font(yol, boy, w=None):
    f = ImageFont.truetype(yol, boy)
    if w is not None:
        f.set_variation_by_axes([w])
    return f


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum() + 1e-9))


def gri(im):
    return np.asarray(im.convert('RGB')).astype(np.float32).mean(2)


def altin(a):
    """Lacivert zeminde altin murekkep 0-1 (kapak_sembol_qc.altin)."""
    a = np.asarray(a).astype(np.float32)
    return np.clip((a[..., 0] - a[..., 2] - 25.0) / 120.0, 0, 1)


def murekkep_kutu(f, t, x, taban):
    b = f.getbbox(t, anchor='ls')
    return (x + b[0], taban + b[1], x + b[2], taban + b[3])


class Satir:
    """Bir metin satirini ayni font/konumla degistirir: eski murekkep kutusu (+pay) zemin rengiyle silinir,
    yeni metin ayni taban cizgisine, ayni sol murekkep kenarina yazilir."""

    def __init__(self, im):
        self.im = im; self.d = ImageDraw.Draw(im); self.log = []

    def degistir(self, eski, yeni, f, sol, taban, renk, zemin=BG, pay=6, orta=None):
        be = f.getbbox(eski, anchor='ls'); bn = f.getbbox(yeni, anchor='ls')
        if orta is None:
            xe = sol - be[0]; xn = sol - bn[0]
        else:
            xe = orta - (be[0] + be[2]) / 2; xn = orta - (bn[0] + bn[2]) / 2
        ke = murekkep_kutu(f, eski, xe, taban)
        self.d.rectangle((ke[0] - pay, ke[1] - pay, ke[2] + pay, ke[3] + pay), fill=zemin)
        self.d.text((xn, taban), yeni, font=f, fill=renk, anchor='ls')
        self.log.append(dict(eski=eski, yeni=yeni, kutu=murekkep_kutu(f, yeni, xn, taban)))


def ust_etiket(im, FD, A, B):
    d = ImageDraw.Draw(im)
    d.rectangle(ETIKET['sil'], fill=BG)
    f = font(os.path.join(FD, 'Montserrat[wght].ttf'), ETIKET['boy'], ETIKET['w'])
    d.text((ETIKET['x'], ETIKET['taban']), f'ASTROLOVE  /  {A.upper()} + {B.upper()}', font=f, fill=ETIKET['renk'], anchor='ls')


def rebate(B):
    kx, ky = round(B.width * 5 / 279.4), round(B.height * 5 / 355.6)
    return B.crop((kx, ky, B.width - kx, B.height - ky))


def merkez_oran(B, oran):
    """oran = en/boy; genisse yanlardan, uzunsa ust-alttan esit kirpar (germe yok)."""
    if B.width / B.height > oran:
        w = round(B.height * oran); x0 = (B.width - w) // 2; return B.crop((x0, 0, x0 + w, B.height))
    h = round(B.width / oran); y0 = (B.height - h) // 2; return B.crop((0, y0, B.width, y0 + h))


def sanal_kapak(pair_mb, cl_mb):
    """Onayli CL kapaginin poster kirpimi (1534x1988) geometrisinde ciftin MB baskisi (isik aktarimi YOK:
    onayli kapak eski bir baski surumunden; isik haritasi altini turuncuya kaydiriyordu). KAPAK_ESLEME CL MB
    baskisinin onayli kapak posterine en iyi oturdugu kirpim (NCC 0.958, galeri77_olc). Donus: (V, CL esleme NCC)."""
    O = Image.open(ONAYLI).convert('RGB').crop(KAPAK_KIRP)
    def T(im):
        p = 40; a = np.pad(np.asarray(im), ((p, p), (p, p), (0, 0)), mode='edge')
        x0, y0, x1, y1 = KAPAK_ESLEME
        return Image.fromarray(a[y0 + p:y1 + p, x0 + p:x1 + p]).resize(O.size, Image.LANCZOS)
    import cv2
    g = lambda im: cv2.GaussianBlur(np.asarray(im).astype(np.float32).mean(2), (0, 0), 1.5)[40:-40, 40:-40]
    return T(pair_mb), ncc(g(T(cl_mb)), g(O))


def sembol_rgba(cr, bg_rgb=None):
    """kart03_duzelt yontemi: altin murekkebi alfa rampasiyla zeminden ayirir. cr: float32 RGB kirpim."""
    gold = (cr[..., 0] > cr[..., 1]) & (cr[..., 1] > cr[..., 2]) & ((cr[..., 0] - cr[..., 2]) >= 40) & (cr[..., 0] >= 80)
    alan = ndi.binary_dilation(ndi.binary_closing(gold, iterations=3), iterations=4)
    lum = cr.mean(2)
    bgl = float(np.percentile(lum[~alan], 60)); fgl = float(np.percentile(lum[gold], 85))
    alfa = np.clip((lum - bgl) / (fgl - bgl), 0, 1) * alan
    bg = np.median(cr[~alan], axis=0) if bg_rgb is None else bg_rgb
    renk = np.where(alfa[..., None] > 0.04, (cr - (1 - alfa[..., None]) * bg) / np.maximum(alfa[..., None], 0.04), cr)
    return Image.fromarray(np.dstack([np.clip(renk, 0, 255), alfa * 255]).astype(np.uint8), 'RGBA')


def bilesenler(g, esik=0.25, min_alan=400):
    lab, n = ndi.label(g > esik)
    out = []
    for i, s in enumerate(ndi.find_objects(lab)):
        a = int((lab[s] == i + 1).sum())
        if a >= min_alan:
            out.append((s[1].start, s[0].start, s[1].stop, s[0].stop, a))
    return out


def kucuk_semboller(B):
    """MB baskida isimlerin ustundeki iki kucuk burc sembolu (sol, sag) kutulari. Bant MB_KUCUK ile olculdu."""
    y0, y1, (sx0, sx1), (dx0, dx1) = MB_KUCUK
    a = np.asarray(B).astype(np.float32)
    g = altin(a[y0:y1])
    k = []
    for x0_, x1_ in ((sx0, sx1), (dx0, dx1)):
        m = np.zeros_like(g); m[:, x0_:x1_] = g[:, x0_:x1_]
        bs = bilesenler(m, 0.25, 400)
        if not bs:
            raise SystemExit('DUR: kucuk sembol bulunamadi')
        X0 = min(b[0] for b in bs); Y0 = min(b[1] for b in bs); X1 = max(b[2] for b in bs); Y1 = max(b[3] for b in bs)
        k.append((X0, Y0 + y0, X1, Y1 + y0))
    return k


def birlesik_kutu(V):
    """Sanal kapak posterinde (1534x1988) birlesik sembol: halka icindeki buyuk altin bilesenler (halka yayi haric)."""
    a = np.asarray(V).astype(np.float32)
    g = altin(a)
    H, W = g.shape
    lab, n = ndi.label(ndi.binary_closing(g > 0.2, iterations=3))
    bs = []
    for i, s in enumerate(ndi.find_objects(lab)):
        alan = int((lab[s] == i + 1).sum())
        w, h = s[1].stop - s[1].start, s[0].stop - s[0].start
        dolu = alan / max(w * h, 1)
        # buyuk sembol parcalari: kucuk sembol bandinin (V de y ~1262, 0.635 H) ustunde, halka degil (halka: cok genis ve seyrek)
        if alan > 3000 and s[0].stop < 0.615 * H and not (w > 0.6 * W and dolu < 0.08):
            bs.append((s[1].start, s[0].start, s[1].stop, s[0].stop))
    if not bs:
        raise SystemExit('DUR: birlesik sembol bulunamadi')
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)), bs


def kart03(im, V, B_mb, FD, A, B, ayni, bilgi):
    s = Satir(im)
    MON = os.path.join(FD, 'Montserrat[wght].ttf')
    FS = font(MON, 49, 500)
    eski = 'Cancer and Libra, united in an original AstroLove design.'
    taban = 336 - FS.getbbox(eski, anchor='ls')[1]
    s.degistir(eski, f'{A} and {B}, united in an original AstroLove design.', FS, 147, taban, SANS_T)
    d = ImageDraw.Draw(im)
    for k in PANEL_SIL:
        d.rectangle(k, fill=NAVY)
    # iki kucuk sembol (MB baski)
    a = np.asarray(B_mb).astype(np.float32)
    kutular = kucuk_semboller(B_mb)
    PAD = 24
    rg = []
    for (x0, y0, x1, y1) in kutular:
        rg.append(sembol_rgba(a[y0 - PAD:y1 + PAD, x0 - PAD:x1 + PAD]))
    boy = [(k[2] - k[0], k[3] - k[1]) for k in kutular]
    olcek = PANEL_SEMBOL['olcek']
    aw, ah = PANEL_SEMBOL['azami']
    olcek = min(olcek, aw / max(w for w, _ in boy), ah / max(h for _, h in boy))
    for r, (cx, cy), (w, h) in zip(rg, (PANEL_SEMBOL['sol'], PANEL_SEMBOL['sag']), boy):
        r2 = r.resize((round(r.width * olcek), round(r.height * olcek)), Image.LANCZOS)
        im.paste(r2, (round(cx - r2.width / 2), round(cy - r2.height / 2)), r2)
    # etiketler
    FE = font(MON, PANEL_ETIKET['boy'], PANEL_ETIKET['w'])
    for t, (cx, _) in ((A.upper(), PANEL_SEMBOL['sol']), (B.upper(), PANEL_SEMBOL['sag'])):
        b = FE.getbbox(t, anchor='ls')
        d.text((cx - (b[0] + b[2]) / 2, PANEL_ETIKET['taban']), t, font=FE, fill=PANEL_ETIKET['renk'], anchor='ls')
    # birlesik sembol: sanal kapak posterinden (kapaktaki %1.7 yatay sikistirma geri alinir, kart03_duzelt)
    (X0, Y0, X1, Y1), _ = birlesik_kutu(V)
    Va = np.asarray(V).astype(np.float32)
    P2 = 30
    cr = Va[max(Y0 - P2, 0):Y1 + P2, max(X0 - P2, 0):X1 + P2]
    r = sembol_rgba(cr)
    r = r.resize((round(r.width * 1560 / 1534), r.height), Image.LANCZOS)
    w, h = (X1 - X0) * 1560 / 1534, Y1 - Y0
    kw, kh = PANEL_BIRLESIK['kutu']
    o = min(kw / w, kh / h)
    r = r.resize((round(r.width * o), round(r.height * o)), Image.LANCZOS)
    cx, cy = PANEL_BIRLESIK['merkez']
    im.paste(r, (round(cx - r.width / 2), round(cy - r.height / 2)), r)
    bilgi['03'] = dict(kucuk=kutular, kucuk_olcek=round(olcek, 3), birlesik=(X0, Y0, X1, Y1), birlesik_olcek=round(o, 3))
    return s.log


def kart04(im, V, FD, A, B, ayni):
    s = Satir(im)
    MON = os.path.join(FD, 'Montserrat[wght].ttf'); GAR = os.path.join(FD, 'EBGaramond[wght].ttf')
    if ayni:
        FT = font(GAR, 120, 450); FS = font(MON, 49, 500)
        bt = 201 - FT.getbbox('Two signs. One shared symbol.', anchor='ls')[1]
        lt = FT.getbbox('Two signs. One shared symbol.', anchor='ls')[0]
        bs = 336 - FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls')[1]
        ls_ = FS.getbbox('Cancer and Libra, united in an original AstroLove design.', anchor='ls')[0]
        # kart04_kur: d.text((143 - lt, bt)) -> sol murekkep = 143 - lt + b0(metin)
        e1 = 'Each name goes under its own sign.'; e2 = 'Type each name in the field for its sign.'
        s.degistir(e1, 'Each name goes on its own side.', FT, 143 - lt + FT.getbbox(e1, anchor='ls')[0], bt, NAVY_T)
        s.degistir(e2, 'Type each name in the field for its side.', FS, 147 - ls_ + FS.getbbox(e2, anchor='ls')[0], bs, SANS_T)
    # poster bandi
    P = V.resize((1560, 1988), Image.LANCZOS)
    band = P.crop((90, 1195, 1483, 1829)).resize((1280, 583), Image.LANCZOS)
    im.paste(band, (145, 830))
    boy_bul = lambda w, t, g: min(range(20, 200), key=lambda z: abs(font(MON, z, w).getbbox(t, anchor='ls')[2] - font(MON, z, w).getbbox(t, anchor='ls')[0] - g))
    FL = font(MON, boy_bul(500, 'Name under Cancer', 402), 500)
    etiket = ('Left name', 'Right name') if ayni else (f'Name under {A}', f'Name under {B}')
    for eski, yeni, ust in (('Name under Cancer', etiket[0], 832), ('Name under Libra', etiket[1], 1038)):
        taban = ust - FL.getbbox(eski, anchor='ls')[1]
        s.degistir(eski, yeni, FL, 1588, taban, SANS_T)
    FE = font(MON, boy_bul(500, 'EMILY = CANCER    JAMES = LIBRA', 700), 500)
    eski = 'EMILY = CANCER    JAMES = LIBRA'
    yeni = 'EMILY = LEFT    JAMES = RIGHT' if ayni else f'EMILY = {A.upper()}    JAMES = {B.upper()}'
    s.degistir(eski, yeni, FE, 435, 1750 - FE.getbbox(eski, anchor='ls')[1], SANS_T)
    return s.log, band


def kart05(im, baskilar):
    PWD, PHD, PY = 430, 537, 470
    out = {}
    for i, r in enumerate(['MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY', 'WARM_PARCHMENT']):
        p = merkez_oran(baskilar[r], PWD / PHD).resize((PWD, PHD), Image.LANCZOS)
        im.paste(p, (145 + i * 570, PY)); out[r] = (145 + i * 570, PY, PWD, PHD)
    return out


def kart07(im, B_mb):
    PV_W, PV_H = 540, 675
    F = round(PV_W * 20 / 396.4); OW = PV_W + 2 * F
    GAP = (2710 - 4 * OW) / 3
    p = merkez_oran(rebate(B_mb), PV_W / PV_H).resize((PV_W, PV_H), Image.LANCZOS)
    pa = np.asarray(p).astype(np.float32)
    yy = np.arange(PV_H)[:, None]; xx = np.arange(PV_W)[None, :]
    g = 1 - 0.28 * np.exp(-yy / 9.0) - 0.22 * np.exp(-xx / 9.0) - 0.08 * np.exp(-(PV_H - 1 - yy) / 5.0) - 0.08 * np.exp(-(PV_W - 1 - xx) / 5.0)
    q = Image.fromarray(np.clip(pa * g[..., None], 0, 255).astype(np.uint8))
    yer = []
    for i in range(4):
        x = round(145 + i * (OW + GAP)) + F; y = 540 + F
        im.paste(q, (x, y)); yer.append((x, y, PV_W, PV_H))
    return yer, q


def kart12(im, B, B_cl, bilgi):
    """kart09_duzelt duzeni; pencere ciftin sembolu uzerinde (CL penceresinin altin yogunluguna en yakin, CL konumuna yakin)."""
    CIZGI = (136, 120, 94)
    ORTA = (100, 540, 2900, 1900)
    im.paste(BG, ORTA)
    TH = 974; TW = round(B.width * TH / B.height); TX = round((170 + 951) / 2 - TW / 2); TY = 717
    thumb = B.resize((TW, TH), Image.LANCZOS)
    PX0, PY0, PX1, PY1 = 1168, 568, 2822, 1854
    KX0c, KY0c, KW = 1530, 1403, 1150
    KH = round(KW * (PY1 - PY0) / (PX1 - PX0))
    gc = altin(np.asarray(B_cl))
    f0 = float(gc[KY0c:KY0c + KH, KX0c:KX0c + KW].mean())
    g = altin(np.asarray(B))
    S = np.cumsum(np.cumsum(np.pad(g, ((1, 0), (1, 0))), 0), 1)
    y1s = MB_KUCUK[0] - 40                                   # pencere kucuk sembol/isim bandina girmez
    aday = []
    for ky in range(300 + (KY0c - 300) % 10, y1s - KH, 10):          # izgara CL penceresinden gecer
        for kx in range(150 + (KX0c - 150) % 10, B.width - 150 - KW, 10):
            f = (S[ky + KH, kx + KW] - S[ky, kx + KW] - S[ky + KH, kx] + S[ky, kx]) / (KW * KH)
            aday.append((abs(f - f0) / f0 + 0.15 * np.hypot(kx - KX0c, ky - KY0c) / 1000, kx, ky, f))
    _, KX0, KY0, fk = min(aday)
    panel = B.crop((KX0, KY0, KX0 + KW, KY0 + KH)).resize((PX1 - PX0, PY1 - PY0), Image.LANCZOS)
    sil = Image.new('L', im.size, 0)
    for x, y, w, h in ((TX, TY, TW, TH), (PX0, PY0, PX1 - PX0, PY1 - PY0)):
        sil.paste(255, (x + 15, y + 18, x + 15 + w, y + 18 + h))
    alfa = np.asarray(sil.filter(ImageFilter.GaussianBlur(26))).astype(np.float32) / 255
    o = np.asarray(im).astype(np.float32); m = np.zeros(alfa.shape, bool); m[ORTA[1]:ORTA[3], ORTA[0]:ORTA[2]] = True
    o[m] *= (1 - (59 / 232) * alfa[m])[:, None]
    im.paste(Image.fromarray(np.clip(o, 0, 255).astype(np.uint8)))
    im.paste(thumb, (TX, TY)); im.paste(panel, (PX0, PY0))
    d = ImageDraw.Draw(im)
    s = TH / B.height
    bx0, by0 = TX + KX0 * s, TY + KY0 * s; bx1, by1 = TX + (KX0 + KW) * s, TY + (KY0 + KH) * s
    d.rectangle((bx0, by0, bx1, by1), outline=CIZGI, width=3)
    ym = (by0 + by1) / 2
    d.line((bx1, ym, PX0, ym), fill=CIZGI, width=3)
    bilgi['12'] = dict(pencere=(KX0, KY0, KW, KH), altin=round(fk, 4), cl_altin=round(f0, 4))
    return [(TX, TY, TW, TH), (PX0, PY0, PX1 - PX0, PY1 - PY0)], thumb, panel


def kart13(im, V):
    PH = 1225; CX = 679.5; TOP = 595
    P = V.resize((1560, 1988), Image.LANCZOS)
    PW = round(1560 * PH / 1988); poster = P.resize((PW, PH), Image.LANCZOS)
    px = round(CX - PW / 2)
    im.paste(poster, (px, TOP))
    return (px, TOP, PW, PH), poster


def kart02(im, V):
    """kart02_poster_esitle geometrisi: poster 586x760; baski, dijital yigin on yuzu, cerceve ici (_lip)."""
    PW, PH, ALT = 586, 760, 1294
    poster = V.resize((PW, PH), Image.LANCZOS)
    FC = round(PW * 20 / 599.6)
    E_ON, e_kutu = (244, 520, 809, 1295), (172, 496, 809, 1295)
    sx, sy = PW / (E_ON[2] - E_ON[0]), PH / (E_ON[3] - E_ON[1])
    ew, eh = e_kutu[2] - e_kutu[0], e_kutu[3] - e_kutu[1]
    yw, yh = round(ew * sx), round(eh * sy)
    on_x, on_y = round((E_ON[0] - e_kutu[0]) * sx), yh - PH
    dx, dy = round(490 - yw / 2), ALT - yh
    CW = PW + 2 * FC
    cx, cy = round(2512 - CW / 2), ALT - (PH + 2 * FC)
    yer = {'baski': (1500 - PW // 2, ALT - PH), 'dijital': (dx + on_x, dy + on_y), 'cerceve': (cx + FC, cy + FC)}
    im.paste(poster, yer['baski']); im.paste(poster, yer['dijital']); im.paste(_lip(poster), yer['cerceve'])
    return [(x, y, PW, PH) for x, y in yer.values()], poster


def metin_json(A, B, ayni):
    J = json.load(open(os.path.join(ROOT, 'data/pod/cl_galeri_final19_metin.json')))
    esle = [('CANCER + LIBRA', f'{A.upper()} + {B.upper()}'), ('Cancer and Libra', f'{A} and {B}'),
            ('A personal gift for Cancer and Libra couples.', f'A personal gift for {A} and {B} couples.')]
    if ayni:
        esle += [('Name under Cancer', 'Left name'), ('Name under Libra', 'Right name'),
                 ('EMILY = CANCER', 'EMILY = LEFT'), ('JAMES = LIBRA', 'JAMES = RIGHT'),
                 ('Each name goes under its own sign.', 'Each name goes on its own side.'),
                 ('Type each name in the field for its sign.', 'Type each name in the field for its side.')]
    else:
        esle += [('Name under Cancer', f'Name under {A}'), ('Name under Libra', f'Name under {B}'),
                 ('EMILY = CANCER', f'EMILY = {A.upper()}'), ('JAMES = LIBRA', f'JAMES = {B.upper()}')]
    out = {'_not': f'{A} + {B} galerisi (CL metinlerinden cift uyarlamasi, galeri77_kur.py)'}
    for k, v in J.items():
        if k.startswith('_'):
            continue
        yeni = []
        for t in v:
            if k == '03_konsept' and t in ('CANCER', 'LIBRA'):
                t = A.upper() if t == 'CANCER' else B.upper()
            else:
                for e, n in esle:
                    t = t.replace(e, n)
            yeni.append(t)
        out[k] = yeni
    return out


def main():
    CIFT, KAY, CL_MB, FD, OUT = sys.argv[1:6]
    os.makedirs(OUT, exist_ok=True)
    satir = {r['cift']: r for r in csv.DictReader(open(os.path.join(ROOT, 'data/pod/pod78_ids.csv')))}[CIFT]
    A, B = satir['a'], satir['b']
    ayni = A == B
    GAR = os.path.join(FD, 'EBGaramond[wght].ttf'); MON = os.path.join(FD, 'Montserrat[wght].ttf')
    # WP kisisellestirilmis baskisi henuz yoksa (WP plate'leri yeniden uretiliyor, Serdar 28 Eyl) 05 kurulmaz;
    # diger 17 gorsel hazir durur, WP gelince tam kosu 05 ve 19'u tamamlar. Isimsiz WP KULLANILMAZ.
    bas = {r: Image.open(os.path.join(KAY, f'BASKI_{r}.jpg')).convert('RGB') for r in RENKLER
           if os.path.exists(os.path.join(KAY, f'BASKI_{r}.jpg'))}
    if set(RENKLER) - set(bas) - {'WARM_PARCHMENT'}:
        raise SystemExit(f'DUR: baski eksik {sorted(set(RENKLER) - set(bas))}')
    wp_var = 'WARM_PARCHMENT' in bas
    cl_mb = Image.open(CL_MB).convert('RGB')
    bilgi = dict(cift=CIFT, a=A, b=B, ayni_burc=ayni, poster={})
    V, n_v = sanal_kapak(bas['MIDNIGHT_BLUE'], cl_mb)
    bilgi['sanal_kapak_cl_ncc'] = round(n_v, 4)
    if n_v < 0.95:
        raise SystemExit(f'DUR: kapak eslemesi CL onayli kapaga oturmuyor (NCC {n_v:.4f})')
    V.save(os.path.join(OUT, '_sanal_kapak.png'))
    k = lambda ad: Image.open(os.path.join(KREM_CL, ad + '.jpg')).convert('RGB')
    kay = lambda ad, im, q=95: im.save(os.path.join(OUT, ad + '.jpg'), quality=q, subsampling=0)
    loglar = {}

    im = k('02_format'); bilgi['poster']['02_format'] = kart02(im, V)[0]; kay('02_format', im)
    im = k('03_konsept'); ust_etiket(im, FD, A, B); loglar['03'] = kart03(im, V, bas['MIDNIGHT_BLUE'], FD, A, B, ayni, bilgi); kay('03_konsept', im)
    im = k('04_kisisellestirme'); ust_etiket(im, FD, A, B); loglar['04'], _ = kart04(im, V, FD, A, B, ayni)
    bilgi['poster']['04_kisisellestirme'] = [(145, 830, 1280, 583)]; kay('04_kisisellestirme', im)
    # 05: CL akisindaki satir duzeltmesi (kart05_satir) once, sonra cift
    if wp_var:
        subprocess.run([sys.executable, os.path.join(HERE, 'kart05_satir.py'), os.path.join(KREM_CL, '05_renk_ve_dijital.jpg'),
                        MON, os.path.join(OUT, '_k05.png')], check=True, stdout=subprocess.DEVNULL)
        im = Image.open(os.path.join(OUT, '_k05.png')).convert('RGB'); ust_etiket(im, FD, A, B)
        bilgi['poster']['05_renk_ve_dijital'] = list(kart05(im, bas).values()); kay('05_renk_ve_dijital', im)
    bilgi['wp_var'] = wp_var
    # sahne kartlari: ESKI = CL krem kart + ciftin ust etiketi (kart_cila_kur ust etiketi ESKI'den alir)
    for kart, ad, renk in (('06', '06_hediye_sahne', 'MIDNIGHT_BLUE'), ('09', '09_yatak_sahne', 'CHAMPAGNE_IVORY'),
                           ('10', '10_calisma_sahne', 'DEEP_BLACK'), ('11', '11_yemek_sahne', 'PURE_WHITE')):
        e = k(ad); ust_etiket(e, FD, A, B); ey = os.path.join(OUT, f'_eski_{kart}.png'); e.save(ey)
        KC.KARTLAR[kart]['poster'] = 'baski'
        out, b = KC.kur(kart, os.path.join(SAHNE_DIR, KC.SAHNE_DOSYA[kart]), os.path.join(KAY, f'BASKI_{renk}.jpg'), ey, GAR, MON)
        # alt serit ve sahne disi alan CL krem kartla ayni olmali (yalniz ust etiket + poster degisir)
        kay(ad, out); bilgi[ad] = dict(kirp_eks=round(b['kirp_eks'], 4), gorunen=b['gorunen'])
    im = k('07_cerceveler'); ust_etiket(im, FD, A, B); bilgi['poster']['07_cerceveler'] = kart07(im, bas['MIDNIGHT_BLUE'])[0]; kay('07_cerceveler', im)
    im = k('08_boylar'); ust_etiket(im, FD, A, B); kay('08_boylar', im)
    im = k('12_zoom'); ust_etiket(im, FD, A, B); bilgi['poster']['12_zoom'] = kart12(im, bas['MIDNIGHT_BLUE'], cl_mb, bilgi)[0]; kay('12_zoom', im)
    im = k('13_kagit'); ust_etiket(im, FD, A, B); bilgi['poster']['13_kagit'] = [kart13(im, V)[0]]; kay('13_kagit', im)
    subprocess.run([sys.executable, os.path.join(HERE, 'kart11_kur.py'), os.path.join(KREM_CL, '14_surec.jpg'),
                    os.path.join(KREM_CL, '14_surec.jpg'), GAR, MON, os.path.join(OUT, '_k14.jpg')], check=True, stdout=subprocess.DEVNULL)
    im = Image.open(os.path.join(OUT, '_k14.jpg')).convert('RGB'); ust_etiket(im, FD, A, B); kay('14_surec', im)
    json.dump(metin_json(A, B, ayni), open(os.path.join(OUT, 'METIN.json'), 'w'), ensure_ascii=False, indent=1)
    bilgi['satirlar'] = loglar
    json.dump(bilgi, open(os.path.join(OUT, 'KUR.json'), 'w'), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k_: v for k_, v in bilgi.items() if k_ not in ('satirlar', 'poster')}, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
