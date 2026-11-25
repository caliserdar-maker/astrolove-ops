#!/usr/bin/env python3
"""Etsy magaza header (banner), yeni altin, 3 secenek (Serdar 25 Kas 2026 18:43; Merkez gorevi).

Olcu: Etsy resmi "recommended 1600 x 400px" (help.etsy.com/hc/en-us/articles/115015663347, 25 Kas 2026); cikti 3200x800
(ayni 4:1, 2x) + 1600x400 kopya. Mobil kirpma icin Etsy resmi aciklama YOK; kontrol gorselinde resmi olmayan "yatayda orta %60"
(linearity.io Etsy size guide) isaretlenir.
Kaynaklar (uydurma yok):
  - zemin: canli header'in (isbl 3000x750) oge disi piksellerinden OLCULEN eliptik radyal profil (pin78_altin_pin.profil yontemi);
  - poster, 1st anniversary kart, cift ve tek burc kupasi: canli header'dan kesilir (yalniz olcekleme);
  - ornament: canli ornament ilaninin "Choose Your Style" gorselinden (Ivory, Ruby, Sapphire, White) disk + gercek altin ip;
  - yeni altin: Serdar onayli PIN_ALTIN_CANCER_LEO.jpg; yazilar ve semboller pin ad satirindan OLCULEN dikey degradeyle boyanir
    (pin78_altin_pin.boya yontemi), sonsuz logo LOGO_YENI_ALTIN_3000.png'den;
  - burc sembolleri seridi: canli header seridinin glif maskeleri, yeni altinla yeniden boyanir;
  - yazi: Cormorant Garamond (depoda scripts/kapak78/yd_kart/fonts, OFL).
QC (PASS/FAIL): boyut; marka adi ve slogan tum seceneklerde orta %60 icinde; yazi/sembol altin rengi pin ad satiriyla kanal
farki <= 15, diger yazilar <= 25; ogeler kenardan >= 24 px (yalniz B'de sarkan ornament ustu haric) ve birbirine >= 12 px
(etiket dahil, istisna yok); hicbir oge mobil kenar cizgisinde kesilmez; Ivory mobil alanda; 3 secenek kutu IoU < 0.5
(zayif: kavram farkini olcmez, gozle de bakilir).
Kullanim: header_yeni_altin.py --header HEADER_CANLI_isbl_fullxfull.jpg --orn o05.jpg --pin PIN_ALTIN_CANCER_LEO.jpg
          --logo LOGO_YENI_ALTIN_3000.png --out DIR
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT = os.path.join(KOK, 'scripts', 'kapak78', 'yd_kart', 'fonts', 'CormorantGaramond.ttf')
W, H = 3200, 800
S = W / 3000.0                                  # canli header 3000x750 -> 3200x800
PIN_PANEL = (104, 258, 897, 1312)
AD_Y, GLIF_Y = (943, 991), (848, 923)           # pin78_altin_pin: panel ici ad ve glif satiri
MOBIL = (int(W * 0.2), int(W * 0.8))           # resmi olmayan orta %60
ORN = {'Ruby': (664, 878, 286), 'Sapphire': (1501, 875, 281), 'White': (1064, 1621, 285), 'Ivory': (1921, 1625, 285)}  # HoughCircles olcumu


def altin_maske(p):
    return (p[..., 0] > 110) & (p[..., 0] > p[..., 2] + 50)


def degrade(pin, y0, y1):
    """pin78_altin_pin.olc_pin03.degrade: satirdaki altin piksellerin satir ortalamasi (ust -> alt)."""
    a = np.asarray(Image.open(pin).convert('RGB')).astype(float)[PIN_PANEL[1]:PIN_PANEL[3], PIN_PANEL[0]:PIN_PANEL[2]]
    sub = a[y0:y1]; gg = altin_maske(sub.astype(int)) & (sub.sum(2) > 350)
    return np.array([sub[i][gg[i]].mean(0) for i in range(y1 - y0) if gg[i].sum() > 3])


def boya(maske, deg):
    """pin78_altin_pin.boya ile ayni: maske (L) -> RGBA, renk = olculen dikey degrade."""
    m = np.asarray(maske).astype(float) / 255
    ys = np.where(m.max(1) > 0.2)[0]
    y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, m.shape[0] - 1)
    t = np.clip((np.arange(m.shape[0]) - y0) / max(1, y1 - y0), 0, 1)
    idx = np.linspace(0, 1, len(deg))
    col = np.stack([np.interp(t, idx, deg[:, c]) for c in range(3)], -1)
    rgb = np.repeat(col[:, None, :], m.shape[1], 1)
    return Image.fromarray(np.dstack([rgb, m * 255]).clip(0, 255).astype(np.uint8), 'RGBA')


def yazi(t, px, aralik=0.0):
    """metin maskesi; px = buyuk harf yuksekligi; aralik = harf arasi (em orani)."""
    for s in range(px * 3, 8, -1):
        f = ImageFont.truetype(FONT, s)
        b = f.getbbox('H')
        if b[3] - b[1] <= px:
            break
    gen = sum(f.getlength(ch) for ch in t) + aralik * s * (len(t) - 1)
    im = Image.new('L', (int(gen) + 40, int(s * 1.6)), 0); d = ImageDraw.Draw(im); x = 20
    for ch in t:
        d.text((x, int(s * 0.25)), ch, font=f, fill=255); x += f.getlength(ch) + aralik * s
    return im.crop(im.getbbox())


# ------------------------------------------------------------------ kaynaklar
def canli_oge(hdr):
    a = np.asarray(Image.open(hdr).convert('RGB')).astype(float)
    Hh, Ww = a.shape[:2]
    lac = (a[..., 2] > a[..., 0] + 15) & (a.sum(2) < 260)          # lacivert zemin
    yy, xx = np.mgrid[0:Hh, 0:Ww]
    on = np.asarray(Image.fromarray(((~lac) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(21))) > 0
    # zemin: eliptik radyal profil (40 halka), oge ve hale disi
    r = np.sqrt(((xx - Ww / 2) / (Ww / 2)) ** 2 + ((yy - Hh / 2) / (Hh / 2)) ** 2)
    kut = np.linspace(0, r.max() + 1e-6, 41); prof = []
    for i in range(40):
        m = (~on) & (r >= kut[i]) & (r < kut[i + 1])
        prof.append(np.median(a[m], 0) if m.sum() > 50 else None)
    son = None
    for i in range(40):
        prof[i] = prof[i] if prof[i] is not None else son; son = prof[i]
    for i in range(38, -1, -1):
        prof[i] = prof[i] if prof[i] is not None else prof[i + 1]
    prof = np.array(prof, float)
    # urun kutulari (canli olcum, 3000x750): poster, kart, cift kupa, tek kupa
    K = {'poster': (150, 70, 440, 425), 'kart': (610, 65, 905, 430), 'kupa_cift': (2030, 75, 2420, 405), 'kupa_tek': (2495, 75, 2885, 405)}
    oge = {}
    for ad, (x0, y0, x1, y1) in K.items():
        sub = a[y0:y1, x0:x1]
        bgc = np.median(np.concatenate([sub[:4].reshape(-1, 3), sub[-4:].reshape(-1, 3)]), 0)   # kutu kenarindaki zemin
        uz = np.sqrt(((sub - bgc) ** 2).sum(2))
        m = uz > 60                                                     # urun; gri hale/golge daha yakin
        ys, xs = np.where(m)
        bx = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
        sub = sub[bx[1]:bx[3], bx[0]:bx[2]]; m = m[bx[1]:bx[3], bx[0]:bx[2]]; uz = uz[bx[1]:bx[3], bx[0]:bx[2]]
        if ad.startswith('kupa'):
            al = (np.clip((uz - 45) / 30.0, 0, 1) * 255).astype(np.uint8)
        else:
            al = np.full(m.shape, 255, np.uint8)                       # poster ve kart dikdortgen
        oge[ad] = Image.fromarray(np.dstack([sub, al]).astype(np.uint8), 'RGBA')
    # burc sembolleri seridi (2 satir) ve ayrac cizgisi
    s0, s1 = 590, 725
    serit = a[s0:s1]
    gm = np.clip((serit @ np.array([0.299, 0.587, 0.114]) - 30) / 90.0, 0, 1)   # olcum: zemin L ~17, glif L p99.9 ~149 (R-B kucuk)
    satirlar = []
    for y0, y1 in ((0, 70), (70, s1 - s0)):
        satirlar.append(Image.fromarray((gm[y0:y1] * 255).astype(np.uint8), 'L'))
    return prof, kut, oge, satirlar, a


def zemin(prof, kut):
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    kc = (kut[:-1] + kut[1:]) / 2
    out = np.stack([np.interp(r, kc, prof[:, c]) for c in range(3)], -1)
    rng = np.random.default_rng(3)
    out += rng.uniform(-0.5, 0.5, out.shape) + rng.uniform(-0.5, 0.5, out.shape)
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), 'RGB').convert('RGBA')


def ornament(orn, ad):
    """disk (Hough cemberi) + gercek altin ip (krem zeminden doygunlukla ayrilir)."""
    x, y, r = ORN[ad]
    im = Image.open(orn).convert('RGB')
    x0, y0, x1, y1 = x - r - 10, y - int(r * 1.95), x + r + 10, y + r + 10
    a = np.asarray(im.crop((x0, y0, x1, y1))).astype(float)
    hh, ww = a.shape[:2]; yy, xx = np.mgrid[0:hh, 0:ww]
    cx, cy = x - x0, y - y0
    disk = np.clip(r - 3 - np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2), 0, 1.5) / 1.5
    mx, mn = a.max(2), a.min(2); doy = (mx - mn) / np.maximum(mx, 1)
    ip = np.clip((doy - 0.30) / 0.15, 0, 1) * (a[..., 0] > a[..., 2] + 40) * (a[..., 1] > 80) * (yy < cy - r * 0.6) * (np.abs(xx - cx) < r * 0.75)
    ip = np.asarray(Image.fromarray((ip * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(3))).astype(float) / 255
    al = np.maximum(disk, ip)
    o = Image.fromarray(np.dstack([a, al * 255]).astype(np.uint8), 'RGBA')
    o = o.crop(o.getbbox())
    ys, xs = np.where(np.asarray(o.split()[3]) > 128)
    o.info['ip_ust'] = (float(xs[ys == ys.min()].mean()) / o.size[0], ys.min() / o.size[1])   # ipin en ust noktasi (oran)
    return o


def logo_oge(logo):
    a = np.asarray(Image.open(logo).convert('RGB')).astype(float)
    al = np.clip((a[..., 0] - a[..., 2] - 25) / 50.0, 0, 1)
    o = Image.fromarray(np.dstack([a, al * 255]).astype(np.uint8), 'RGBA')
    return o.crop(o.getbbox())


# ------------------------------------------------------------------ yerlesim yardimcilari
class Tuval:
    def __init__(self, bg):
        self.im = bg.copy(); self.kutular = []

    def koy(self, oge, cx, cy, h=None, w=None, ad='', golge=False):
        if h:
            oge = oge.resize((max(1, round(oge.size[0] * h / oge.size[1])), h), Image.LANCZOS)
        elif w:
            oge = oge.resize((w, max(1, round(oge.size[1] * w / oge.size[0]))), Image.LANCZOS)
        x, y = round(cx - oge.size[0] / 2), round(cy - oge.size[1] / 2)
        if golge:
            sh = Image.new('RGBA', oge.size, (0, 0, 0, 0)); sh.putalpha(oge.split()[3].point(lambda v: int(v * 0.55)))
            sh = sh.filter(ImageFilter.GaussianBlur(14)); self.im.alpha_composite(sh, (x + 10, y + 14))
        self.im.alpha_composite(oge, (x, y))
        self.kutular.append({'ad': ad, 'kutu': [x, y, x + oge.size[0], y + oge.size[1]]})
        return x, y, x + oge.size[0], y + oge.size[1]

    def yazi(self, t, px, cx, cy, deg, aralik=0.0, ad=''):
        return self.koy(boya(yazi(t, px, aralik), deg), cx, cy, ad=ad or t)

    def cizgi(self, x0, x1, y, deg, kal=3):
        m = Image.new('L', (x1 - x0, kal), 255)
        self.im.alpha_composite(boya(m, deg[len(deg) // 2:len(deg) // 2 + 1].repeat(2, 0)), (x0, y))


def etiket(T, t, cx, y, deg):
    s1, s2 = t.split('|')
    a = T.yazi(s1, 16, cx, y, deg, aralik=0.22, ad='etiket:' + s1)
    return T.yazi(s2, 16, cx, a[3] + 22, deg, aralik=0.22, ad='etiket:' + s2)


def serit(T, satirlar, deg, y0):
    T.cizgi(int(180 * S), int(2820 * S), y0, deg, kal=3)
    for i, m in enumerate(satirlar):
        m2 = m.resize((W, round(m.size[1] * S)), Image.LANCZOS)
        T.im.alpha_composite(boya(m2, deg), (0, y0 + 22 + i * round(70 * S)))
    T.kutular.append({'ad': 'serit', 'kutu': [0, y0, W, y0 + 22 + round(135 * S)]})


# ------------------------------------------------------------------ 3 secenek
def secenek_a(bg, oge, orn, logo, ad_deg, gl_deg, satirlar):
    """A: canli duzenin yeni altinli hali + ornament: solda poster, kart, Ivory; ortada logo + marka; sagda kupalar, Ruby; altta serit."""
    T = Tuval(bg)
    lb = T.koy(logo, W / 2, 110, w=320, ad='logo')
    t = T.yazi('AstroLoveArt', 96, W / 2, lb[3] + 80, ad_deg, ad='marka')
    t2 = T.yazi('78 Original Zodiac Pair Designs', 32, W / 2, t[3] + 52, ad_deg, ad='slogan')
    T.cizgi(int(W / 2 - 150), int(W / 2 + 150), t2[3] + 32, ad_deg)
    T.yazi('ZODIAC COMPATIBILITY GIFTS', 20, W / 2, t2[3] + 80, ad_deg, aralik=0.32, ad='alt_slogan')
    sira = [('poster', 300, 'ZODIAC COUPLE|POSTERS', 175), ('kart', 300, '1ST ANNIVERSARY|GIFTS', 485), ('Ivory', 290, 'ZODIAC COUPLE|ORNAMENTS', 905),
            ('Ruby', 290, 'ZODIAC COUPLE|ORNAMENTS', 2295), ('kupa_cift', 230, 'ZODIAC COUPLE|MUGS', 2725), ('kupa_tek', 230, 'ZODIAC SIGN|MUGS', 3030)]
    for ad, h, et, cx in sira:
        im = orn[ad] if ad in orn else oge[ad]
        b = T.koy(im, cx, 235, h=h, ad=ad, golge=ad in ('poster', 'kart'))
        etiket(T, et, cx, 425, ad_deg)
    serit(T, satirlar, gl_deg, 530)
    return T


def secenek_b(bg, oge, orn, logo, ad_deg, gl_deg, satirlar):
    """B: ortada buyuk logo ustte, marka altta (dikey blok); solda tavandan sarkan 4 ornament (Ivory dahil); sagda urun kumesi."""
    T = Tuval(bg)
    lb = T.koy(logo, W / 2, 175, w=640, ad='logo')
    t = T.yazi('AstroLoveArt', 100, W / 2, lb[3] + 95, ad_deg, ad='marka')
    t2 = T.yazi('78 Original Zodiac Pair Designs', 34, W / 2, t[3] + 58, ad_deg, ad='slogan')
    T.cizgi(int(W / 2 - 150), int(W / 2 + 150), t2[3] + 34, ad_deg)
    T.yazi('ZODIAC COMPATIBILITY GIFTS', 21, W / 2, t2[3] + 84, ad_deg, aralik=0.32, ad='alt_slogan')
    for ad, cx, cy, h in (('Ruby', 175, 360, 320), ('Sapphire', 470, 480, 320), ('Ivory', 860, 380, 360)):
        ux, uy = orn[ad].info['ip_ust']
        im = orn[ad].resize((round(orn[ad].size[0] * h / orn[ad].size[1]), h), Image.LANCZOS)
        x0 = round(cx - im.size[0] / 2); y0 = round(cy - h / 2)
        px, py = x0 + ux * im.size[0], y0 + uy * h                     # gercek ipin ust noktasi
        ipm = Image.new('L', (3, int(py) + 6), 255)                    # tavandan ipe ince yeni altin cizgi
        T.im.alpha_composite(boya(ipm, gl_deg[len(gl_deg) // 2:len(gl_deg) // 2 + 1].repeat(2, 0)), (round(px) - 1, 0))
        T.koy(im, cx, cy, ad=ad)
    T.koy(oge['poster'], 2330, 290, h=390, ad='poster', golge=True)
    T.koy(oge['kupa_cift'], 2330, 640, h=230, ad='kupa_cift')
    T.koy(oge['kart'], 2800, 300, h=380, ad='kart', golge=True)
    T.koy(oge['kupa_tek'], 2830, 650, h=230, ad='kupa_tek')
    return T


def secenek_c(bg, oge, orn, logo, ad_deg, gl_deg, satirlar):
    """C: vitrin rafi: ustte yatay marka (logo + AstroLoveArt tek satir), altta altin raf cizgisi uzerinde 7 urun yan yana."""
    T = Tuval(bg)
    tm = yazi('AstroLoveArt', 88); lg = logo.resize((300, round(logo.size[1] * 300 / logo.size[0])), Image.LANCZOS)
    top = lg.size[0] + 50 + tm.size[0]; x0 = W / 2 - top / 2
    T.koy(lg, x0 + lg.size[0] / 2, 110, ad='logo')
    T.koy(boya(tm, ad_deg), x0 + lg.size[0] + 50 + tm.size[0] / 2, 110, ad='marka')
    T.yazi('78 ORIGINAL ZODIAC PAIR DESIGNS   ·   ZODIAC COMPATIBILITY GIFTS', 20, W / 2, 215, ad_deg, aralik=0.3, ad='slogan')
    raf = 690
    T.cizgi(140, W - 140, raf, ad_deg, kal=4)
    sira = [('poster', 330, 330), ('Ivory', 300, 830), ('kupa_cift', 280, 1190), ('kart', 330, 1600),
            ('kupa_tek', 280, 2010), ('Sapphire', 300, 2390), ('Ruby', 300, 2870)]
    for ad, h, cx in sira:
        im = orn[ad] if ad in orn else oge[ad]
        T.koy(im, cx, raf - 14 - h / 2, h=h, ad=ad, golge=ad in ('poster', 'kart'))
    return T


# ------------------------------------------------------------------ QC
def qc(T, ad_deg, kaynak, sarkan=False):
    S_ = []
    k = lambda a, ok, d='': S_.append({'kapi': a, 'sonuc': 'PASS' if ok else 'FAIL', 'ayrinti': str(d)})
    im = np.asarray(T.im.convert('RGB')).astype(float)
    k('boyut 3200x800 (4:1)', T.im.size == (W, H), T.im.size)
    K = {b['ad']: b['kutu'] for b in T.kutular}
    for a in ('marka', 'slogan'):
        b = K[a]; k(f'{a} mobil orta %60 icinde', b[0] >= MOBIL[0] and b[2] <= MOBIL[1], b)
    b = K['marka']; sub = im[b[1]:b[3], b[0]:b[2]]; m = altin_maske(sub.astype(int))
    c1 = sub[m].mean(0); c2 = ad_deg.mean(0)
    k('marka yazisi altin rengi pin ad satiriyla kanal farki <= 15', np.abs(c1 - c2).max() <= 15, f'{c1.round()} / {c2.round()}')
    kut = [b for b in T.kutular if b['ad'] != 'serit']
    ic = all(b['kutu'][0] >= 24 and b['kutu'][2] <= W - 24 and b['kutu'][3] <= H - 24 and (b['kutu'][1] >= 24 or b['ad'] in ORN)
             for b in kut) if sarkan else all(b['kutu'][0] >= 24 and b['kutu'][1] >= 24 and b['kutu'][2] <= W - 24 and b['kutu'][3] <= H - 24 for b in kut)
    k('ogeler kenardan >= 24 px (sarkan ornament ustu haric)', ic, [b['ad'] for b in kut if not (b['kutu'][0] >= 24 and b['kutu'][2] <= W - 24 and b['kutu'][3] <= H - 24)])
    cak = []
    for i in range(len(kut)):
        for j in range(i + 1, len(kut)):
            a, b = kut[i]['kutu'], kut[j]['kutu']
            if a[0] < b[2] + 12 and b[0] < a[2] + 12 and a[1] < b[3] + 12 and b[1] < a[3] + 12:
                cak.append((kut[i]['ad'], kut[j]['ad']))
    k('ogeler arasi >= 12 px (istisna yok)', not cak, cak)
    kes = [b['ad'] for b in kut if any(b['kutu'][0] < e < b['kutu'][2] for e in MOBIL)]
    k('hicbir oge/etiket mobil kenar cizgisiyle (resmi olmayan orta %60) kesilmez', not kes, kes)
    k('Ivory ornament mobil orta %60 icinde', MOBIL[0] <= K['Ivory'][0] and K['Ivory'][2] <= MOBIL[1], K['Ivory'])
    kotu = []
    for b in kut:
        if b['ad'] in ('marka', 'slogan', 'alt_slogan') or b['ad'].startswith('etiket:'):
            x0, y0, x1, y1 = b['kutu']; sub = im[y0:y1, x0:x1]; m = altin_maske(sub.astype(int))
            if m.sum() < 20 or np.abs(sub[m].mean(0) - ad_deg.mean(0)).max() > 25:
                kotu.append((b['ad'], sub[m].mean(0).round().tolist() if m.sum() else None))
    k('tum yazilar (slogan, etiket) pin ad altini (kanal farki <= 25, ince yazi kenar karisimi)', not kotu, kotu)
    return S_


def kontrol_gorseli(im, yol):
    c = im.convert('RGB').copy(); d = ImageDraw.Draw(c, 'RGBA')
    d.rectangle((0, 0, MOBIL[0], H), fill=(255, 0, 0, 70)); d.rectangle((MOBIL[1], 0, W, H), fill=(255, 0, 0, 70))
    d.line((MOBIL[0], 0, MOBIL[0], H), fill=(255, 60, 60, 255), width=6); d.line((MOBIL[1], 0, MOBIL[1], H), fill=(255, 60, 60, 255), width=6)
    f = ImageFont.truetype(FONT, 34)
    d.text((MOBIL[0] + 14, 10), 'MOBIL (resmi olmayan tahmin: orta %60)', font=f, fill=(255, 90, 90, 255))
    c.save(yol, quality=92)


def main():
    ap = argparse.ArgumentParser()
    for x in ('header', 'orn', 'pin', 'logo', 'out'):
        ap.add_argument('--' + x, required=True)
    g = ap.parse_args(); os.makedirs(g.out, exist_ok=True)
    prof, kut, oge, satirlar, canli = canli_oge(g.header)
    bg = zemin(prof, kut)
    orn = {a: ornament(g.orn, a) for a in ORN}
    logo = logo_oge(g.logo)
    ad_deg = degrade(g.pin, *AD_Y); gl_deg = degrade(g.pin, *GLIF_Y)
    rapor = {}
    for harf, f in (('A', secenek_a), ('B', secenek_b), ('C', secenek_c)):
        T = f(bg, oge, orn, logo, ad_deg, gl_deg, satirlar)
        yol = os.path.join(g.out, f'HEADER_SECENEK_{harf}_3200x800.jpg')
        T.im.convert('RGB').save(yol, quality=95, subsampling=0)
        T.im.convert('RGB').resize((1600, 400), Image.LANCZOS).save(os.path.join(g.out, f'HEADER_SECENEK_{harf}_1600x400.jpg'), quality=95, subsampling=0)
        kontrol_gorseli(T.im, os.path.join(g.out, f'HEADER_SECENEK_{harf}_MOBIL_KONTROL.jpg'))
        rapor[harf] = {'kapilar': qc(T, ad_deg, canli, sarkan=(harf == 'B')), 'kutular': T.kutular}
    # 3 secenek yerlesim farki: ayni adli oge kutularinin IoU ortalamasi < 0.5
    def iou(a, b):
        ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
        return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)
    fark = {}
    for p, q in (('A', 'B'), ('A', 'C'), ('B', 'C')):
        KA = {b['ad']: b['kutu'] for b in rapor[p]['kutular']}; KB = {b['ad']: b['kutu'] for b in rapor[q]['kutular']}
        ort = [iou(KA[a], KB[a]) for a in KA if a in KB and a in ('poster', 'kart', 'kupa_cift', 'kupa_tek', 'Ivory', 'Ruby', 'logo')]
        fark[p + q] = round(float(np.mean(ort)), 3)
    genel = [{'kapi': '3 secenek yerlesim farkli (urun/logo kutu IoU ort. < 0.5)', 'sonuc': 'PASS' if max(fark.values()) < 0.5 else 'FAIL', 'ayrinti': str(fark)}]
    tum = []
    for harf in 'ABC':
        for s in rapor[harf]['kapilar']:
            print(f"{s['sonuc']} [{harf}] {s['kapi']} | {s['ayrinti']}"); tum.append(s)
    for s in genel:
        print(f"{s['sonuc']} {s['kapi']} | {s['ayrinti']}"); tum.append(s)
    json.dump({'secenekler': rapor, 'genel': genel}, open(os.path.join(g.out, 'QC_HEADER.json'), 'w'), indent=1, default=str)
    raise SystemExit(0 if all(s['sonuc'] == 'PASS' for s in tum) else 1)


if __name__ == '__main__':
    main()
