#!/usr/bin/env python3
"""SADE kupa baski dosyasi v3 (11 oz 2700x1050 / 15 oz 2700x1140, 300 dpi). KILITLI YERLESIM (Serdar 30.10.2026):
ON: buyuk burc sembolu (Serdar'in kendi sembol dosyasi), altinda musterinin yazisi (isim ya da tarih, Cinzel),
    yazinin iki yaninda birer kucuk dal (soldaki ayna). Uzun yazi kuculurse dallar da ayni oranda kuculur.
    Basik sembol (Kova) kutunun ortasinda kalir (Serdar 30.10 onay, secenek a).
ARKA: tek kucuk dal, hemen altinda nazar, altinda kisisel mesaj (EB Garamond italik). Mesaj ZORUNLU.
HIZA: sembol kutusunun ustu = arka dalin ustu. Sembol (kalinlastirilmis hali dahil) sabit kutuya sigar ve kutunun
      ortasina konur; yazi tabani sabittir (12 burcta ayni yerlesim).
Kullanim: python3 -I baski_sade3.py <glif_png> <dal_goruntu (beyaz zemin)> <on_yazi> <mesaj> <renk r,g,b> <cikti_onek>
Ortam: BOY=15 -> 15 oz (cap 3,35 inc; 2700x1050 cizim 2700x1140'a dikeyde ortalanir).
       GLIF_K (vars. 1.0), KALIN (vars. 1.4): sembol boy ve cizgi kalinligi carpani.
Girdi: bastaki/sondaki bosluk ve satir sonu temizlenir; metin NFC'ye cevrilir; karakter sinirlari BUYUK HARF hali uzerinden.
Hata (cikis kodu 1, dosya yazilmaz, ayni onekli eski dosyalar once silinir): on yazi ya da mesaj bos / harf-rakam yok,
on yazi 12 / mesaj 30 karakteri asar, fontta olmayan, birlesik isaret, gorunmez ya da ic satir sonu karakteri,
yazi 2,2 mm altina inmeden sigmaz, yazi cizim alaninin kenarina degerse, sembol kutuya sigmazsa,
ogeler arasi 14 px kalmaz, renk gecersiz ya da cok acik.
"""
import math, os, sys, time, unicodedata
import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

t0 = time.time()
if len(sys.argv) != 7:
    sys.exit(__doc__)
GLIF, DAL, ON_YAZI, MESAJ, RENK_S, OUT = sys.argv[1:7]
V = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'varlik')) + '/'
CIN, ITA = V + 'font/Cinzel[wght].ttf', V + 'font/EBGaramond-Italic[wght].ttf'

DPI, FW, FH = 300, 2700, 1050
BOY = os.environ.get('BOY', '11')
if BOY not in ('11', '15'):
    sys.exit(f'HATA: BOY 11 ya da 15 olmali ({BOY})')
D_IN = {'11': 3.23, '15': 3.35}[BOY]
RK = D_IN / 2 * DPI
QUARTER = D_IN * math.pi / 4 * DPI
FACE = {'on': FW / 2 - QUARTER, 'arka': FW / 2 + QUARTER}
TW, TH = 484, 525                           # on gorunus tuvali yari boyu (px)
MM = DPI / 25.4
GK = float(os.environ.get('GLIF_K', 1.0))
KALIN = float(os.environ.get('KALIN', 1.4))

# Kilitli olculer (mm, baski ust kenarindan; hedef Canva MAHZePXHFaE'den oranla, Serdar 30.10)
HIZA_UST = 20.5                             # arka dal ustu = on sembol kutusu ustu
DAL_ON = (11.0, 10.0)                       # isim yanindaki dal kutusu (gen x yuk)
DAL_ARKA = (17.0, 15.0)                     # nazar ustundeki dal kutusu
DAL_ARA = 1.5                               # isim ile dal arasi (1,2 mm sinirin ustunde pay; inceleme 30.10)
NAZAR_D = 12.0 * MM                         # nazar capi (px)
DAL_NAZAR_ARA = 1.5                         # dal alti ile nazar ustu arasi
MESAJ_TABAN = 61.0                          # mesaj tabani
SEM_YUK, SEM_GEN = 33.5, 44.0               # sembol kutusu (yukseklik, en genis)
SEM_YAZI_ARA = 7.0                          # sembol kutusu alti ile isim buyuk harf ustu arasi
CAP_ISIM = 5.0 * MM                         # isim buyuk harf yuksekligi (px)
CAP_MESAJ = 28 * 2.027                      # mesaj baslangic boyu (Orchard ile ayni, px)
SATIR_MAX = 860                             # tek satir en genis (px, on gorunus; Orchard kurali)
YAZI_MIN_MM = 2.2                           # isim / mesaj en kucuk buyuk harf (Orchard kurali)
ON_MAX, MESAJ_MAX = 12, 30                  # karakter siniri (Serdar 30.10 onay)
PAY = 14                                    # ogeler arasi en az bosluk (px, 1,2 mm)
ESIK = 0.05                                 # bu alfanin ustu basilir sayilir (bosluk olcumu dahil)


def adim(m):
    print(f'[{time.time() - t0:5.1f}s] {m}', flush=True)


# ---------------- girdi kontrolu (cizmeden once) ----------------
try:
    RENK = np.array([int(v) for v in RENK_S.split(',')], float)
except ValueError:
    sys.exit(f'HATA: renk r,g,b olmali ({RENK_S})')
if RENK.shape != (3,) or RENK.min() < 0 or RENK.max() > 255:
    sys.exit(f'HATA: renk 0-255 arasi 3 deger olmali ({RENK_S})')
if 0.299 * RENK[0] + 0.587 * RENK[1] + 0.114 * RENK[2] > 160:
    sys.exit(f'HATA: renk beyaz kupada okunmayacak kadar acik ({RENK_S})')

ON_YAZI = unicodedata.normalize('NFC', ON_YAZI).strip()
MESAJ = unicodedata.normalize('NFC', MESAJ).strip()
if not ON_YAZI or not MESAJ:
    sys.exit('HATA: on yazi (isim/tarih) ve arka mesaj zorunlu')
TR = any(c in ON_YAZI for c in 'ıİşŞğĞ')    # Turkce yazi: i -> İ, ı -> I (Ingilizce isimde dokunulmaz)
ON_BUYUK = unicodedata.normalize('NFC', (ON_YAZI.replace('i', 'İ').replace('ı', 'I') if TR else ON_YAZI).upper())
if len(ON_BUYUK) > ON_MAX:
    sys.exit(f'HATA: on yazi buyuk harfle {len(ON_BUYUK)} karakter, sinir {ON_MAX}')
if len(MESAJ) > MESAJ_MAX:
    sys.exit(f'HATA: mesaj {len(MESAJ)} karakter, sinir {MESAJ_MAX}')


def metin_kontrol(metin, font, ad):
    cmap = TTFont(font).getBestCmap()
    for c in metin:
        kat = unicodedata.category(c)
        if kat in ('Cc', 'Cf', 'Zl', 'Zp') or (c.isspace() and c != ' '):
            sys.exit(f'HATA: {ad} gorunmez/satir sonu karakteri iceriyor (U+{ord(c):04X})')
        if kat in ('Mn', 'Mc', 'Me'):
            sys.exit(f'HATA: {ad} ayri birlesik isaret iceriyor (U+{ord(c):04X}); musteriyle konusulur')
        if ord(c) not in cmap:
            sys.exit(f'HATA: {ad} fontta olmayan karakter iceriyor: {c!r} (U+{ord(c):04X}); musteriyle konusulur')
    if not any(unicodedata.category(c) in ('Lu', 'Ll', 'Lt', 'Lo', 'Nd') for c in metin):   # kip harfi (Lm, ör. ˆ ʹ) sayilmaz
        sys.exit(f'HATA: {ad} en az bir harf ya da rakam icermeli ({metin!r})')


metin_kontrol(ON_BUYUK, CIN, 'on yazi')
metin_kontrol(MESAJ, ITA, 'mesaj')
for p in (GLIF, DAL, CIN, ITA, V + 'ORCHARD_nazar.png'):
    if not os.path.isfile(p):
        sys.exit(f'HATA: dosya yok: {p}')
CIKTI = [OUT + '_onizleme.jpg', OUT + f'_baski_{BOY}oz.png']
for eski in [f'{OUT}_baski_11oz.png', f'{OUT}_baski_15oz.png', f'{OUT}_onizleme.jpg'] + [c + '.yaziliyor' for c in CIKTI]:
    if os.path.isfile(eski):                # girdi gecerliyse: ayni onekli eski / yarim dosyalar silinir (hata olursa eskisi kullanilmasin)
        os.remove(eski)


# ---------------- yardimcilar ----------------
def alfa_png(p):
    a = np.asarray(Image.open(p).convert('RGBA'))[..., 3].astype(float) / 255
    ys, xs = np.where(a > ESIK)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def dal_yukle(p):
    """Beyaz zeminli dal gorseli -> (renk, alfa), kirpilmis. Beyaz kupaya basilacagi icin beyaz = murekkep yok."""
    im = np.asarray(Image.open(p).convert('RGB')).astype(float)
    a = np.clip((250 - im.min(-1)) / 30, 0, 1)
    lab, n = ndimage.label(a > 0.2)
    if n:
        sz = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
        a = a * np.isin(lab, [i + 1 for i in range(n) if sz[i] >= 0.002 * sz.max()])   # JPG lekelerini at
    ys, xs = np.where(a > ESIK)
    return im[ys.min():ys.max() + 1, xs.min():xs.max() + 1], a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def boyutla(rgb, a, kutu_mm):
    H, W = a.shape
    k = min(kutu_mm[0] * MM / W, kutu_mm[1] * MM / H)
    sz = (max(1, round(W * k)), max(1, round(H * k)))
    r = np.asarray(Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize(sz, Image.LANCZOS)).astype(float)
    aa = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize(sz, Image.LANCZOS)).astype(float) / 255
    return r, aa


def kalinlas(a, carpan):
    if carpan <= 1.0:
        return a
    m = a > 0.5
    d = ndimage.distance_transform_edt(m)
    tepe = (d == ndimage.maximum_filter(d, size=3)) & m & (d > 1)
    cizgi = 2 * np.median(d[tepe]) if tepe.any() else 4.0
    r = (carpan - 1.0) * cizgi / 2
    p = int(np.ceil(r)) + 2
    a = np.pad(a, p)
    dis = ndimage.distance_transform_edt(~(a > 0.5))
    a = np.maximum(a, np.clip(r + 0.5 - dis, 0, 1))
    ys, xs = np.where(a > ESIK)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def yazi(m, font, cap_px, ag, aralik=0.0):
    f = ImageFont.truetype(font, 200)
    f.set_variation_by_axes([ag])
    capH = f.getbbox('H')[3] - f.getbbox('H')[1]
    boy = max(4, round(200 * cap_px / capH))
    f = ImageFont.truetype(font, boy)
    f.set_variation_by_axes([ag])
    d = ImageDraw.Draw(Image.new('L', (1, 1)))
    asc, desc = f.getmetrics()
    pad = int(0.6 * boy) + 4                # Q kuyrugu, aksan, italik tasmasi icin genis pay
    W = int(sum(d.textlength(c, font=f) for c in m) + aralik * (len(m) - 1) + 2 * pad)
    im = Image.new('L', (W, asc + desc + 2 * pad), 0)
    dd = ImageDraw.Draw(im)
    x = pad
    for c in m:
        dd.text((x, pad), c, font=f, fill=255)
        x += d.textlength(c, font=f) + aralik
    a = np.asarray(im).astype(float) / 255
    if (a[:2] > ESIK).any() or (a[-2:] > ESIK).any() or (a[:, :2] > ESIK).any() or (a[:, -2:] > ESIK).any():
        sys.exit(f'HATA: yazi cizim alaninin kenarina degiyor (kesilme riski): {m!r}')
    ys, xs = np.where(a > ESIK)
    if not ys.size:
        sys.exit(f'HATA: yazi bos cikti: {m!r}')
    return a[:, xs.min():xs.max() + 1], pad + asc       # alfa, taban cizgisi (alfa icinde y)


class Tuval:
    """On gorunus tuvali; ogeler kaydedilir, cizimden once tasma ve cakisma kontrol edilir."""

    def __init__(self, ad):
        self.ad, self.im, self.ogeler = ad, np.full((2 * TH, 2 * TW, 3), 255.0), []

    def ekle(self, ad, a, x0, y0, rgb=None, carp=None):
        x0, y0 = int(round(x0 + TW)), int(round(y0 + TH))
        h, w = a.shape
        if x0 < 0 or y0 < 0 or x0 + w > 2 * TW or y0 + h > 2 * TH:
            sys.exit(f'HATA {self.ad}: {ad} tuvalden tasiyor ({x0},{y0},{w}x{h})')
        self.ogeler.append((ad, a, x0, y0, rgb, carp))

    def kontrol(self):
        """Her oge cifti arasinda en az PAY px bosluk (basilan her piksel, alfa > ESIK)."""
        enaz = {}
        for i, (ad1, a1, x1, y1, *_) in enumerate(self.ogeler):
            m = np.zeros(self.im.shape[:2], bool)
            m[y1:y1 + a1.shape[0], x1:x1 + a1.shape[1]] = a1 > ESIK
            uz = ndimage.distance_transform_edt(~m)
            for ad2, a2, x2, y2, *_ in self.ogeler[i + 1:]:
                b = uz[y2:y2 + a2.shape[0], x2:x2 + a2.shape[1]][a2 > ESIK]
                d = float(b.min()) if b.size else 999.0
                enaz[f'{ad1}~{ad2}'] = d
                if d < PAY:
                    sys.exit(f'HATA {self.ad}: {ad1} ile {ad2} arasi {d:.0f} px (en az {PAY})')
        return enaz

    def ciz(self):
        for ad, a, x0, y0, rgb, carp in self.ogeler:
            h, w = a.shape
            bolge = self.im[y0:y0 + h, x0:x0 + w]
            if carp is not None:
                bolge *= carp / 255.0
            else:
                renk = rgb if rgb is not None else RENK
                bolge[:] = bolge * (1 - a[..., None]) + renk * a[..., None]
        return self.im


def kaydet_hepsi(isler):
    """isler: [(PIL goruntu, yol, kw)]. Hepsi once gecici adla yazilir; hepsi bitince yerine konur.
    Herhangi bir hata olursa gecici dosyalar silinir, hicbir cikti kalmaz."""
    geciciler = []
    try:
        for im, yol, kw in isler:
            gecici = yol + '.yaziliyor'
            geciciler.append(gecici)
            im.save(gecici, format='PNG' if yol.endswith('.png') else 'JPEG', **kw)
        for im, yol, kw in isler:
            os.replace(yol + '.yaziliyor', yol)
    except Exception as e:
        for g in geciciler:
            if os.path.isfile(g):
                os.remove(g)
        for im, yol, kw in isler:
            if os.path.isfile(yol):
                os.remove(yol)
        sys.exit(f'HATA: dosya yazilamadi: {e}')


dal_rgb, dal_a = dal_yukle(DAL)
dal_ust = HIZA_UST * MM - TH

# ---------------- ARKA: dal + nazar + mesaj ----------------
arka = Tuval('arka')
r, a = boyutla(dal_rgb, dal_a, DAL_ARKA)
arka.ekle('dal', a, -a.shape[1] / 2, dal_ust, rgb=r)
nazar_ust = dal_ust + a.shape[0] + DAL_NAZAR_ARA * MM
nz = np.asarray(Image.open(V + 'ORCHARD_nazar.png').convert('RGB')).astype(float)
ys, xs = np.where(nz.min(-1) < 250)
nz = nz[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
nzs = np.asarray(Image.fromarray(nz.astype(np.uint8)).resize((round(NAZAR_D),) * 2, Image.LANCZOS)).astype(float)
arka.ekle('nazar', (nzs.min(-1) < 250).astype(float), -nzs.shape[1] / 2, nazar_ust, carp=nzs)
cap = CAP_MESAJ
while True:                                 # tek satir, en fazla SATIR_MAX px, en az 2,2 mm
    ma, mb = yazi(MESAJ, ITA, cap, 600)
    if ma.shape[1] <= SATIR_MAX or cap - 0.25 < YAZI_MIN_MM * MM:
        break
    cap -= 0.25
if ma.shape[1] > SATIR_MAX:
    sys.exit(f'HATA: mesaj {YAZI_MIN_MM} mm ile tek satira sigmiyor ({ma.shape[1]} px > {SATIR_MAX})')
mes_cap = cap
arka.ekle('mesaj', ma, -ma.shape[1] / 2, MESAJ_TABAN * MM - TH - mb)
ark_ara = arka.kontrol()

# ---------------- ON: sembol (sabit kutu) + yazi + iki dal ----------------
on = Tuval('on')
g0 = alfa_png(GLIF)
H0, W0 = g0.shape
kut_h, kut_w = SEM_YUK * MM * GK, SEM_GEN * MM * GK


def sembol(k):
    g = np.asarray(Image.fromarray((g0 * 255).astype(np.uint8)).resize((round(W0 * k), round(H0 * k)), Image.LANCZOS)).astype(float) / 255
    return kalinlas(g, KALIN)


k = min(kut_h / H0, kut_w / W0)
for _ in range(4):                          # kalinlastirilmis sembol kutuya sigana kadar kucult
    gl = sembol(k)
    f = min(kut_h / gl.shape[0], kut_w / gl.shape[1])
    if f >= 1:
        break
    k *= f * 0.998
if gl.shape[0] > kut_h + 1 or gl.shape[1] > kut_w + 1:
    sys.exit(f'HATA: sembol kutuya sigmiyor ({gl.shape[1] / MM:.1f}x{gl.shape[0] / MM:.1f} mm)')
on.ekle('sembol', gl, -gl.shape[1] / 2, dal_ust + kut_h / 2 - gl.shape[0] / 2)
TABAN = dal_ust + kut_h + SEM_YAZI_ARA * MM + CAP_ISIM          # sabit yazi tabani
on_rgb, on_a = boyutla(dal_rgb, dal_a, (DAL_ON[0] * 4, DAL_ON[1] * 4))   # ara boy (hiz icin; son boyun 4 kati)
cap = CAP_ISIM
while True:                                 # yazi + iki dal tek satir SATIR_MAX px'e sigar; sigmazsa yazi kuculur (taban sabit)
    ia, ib = yazi(ON_BUYUK, CIN, cap, 600, cap * 0.18)
    oran = cap / CAP_ISIM                   # dallar yaziyla orantili kuculur (Serdar 30.10 onay); normal isimde oran 1
    dr, da = boyutla(on_rgb, on_a, (DAL_ON[0] * oran, DAL_ON[1] * oran))
    toplam = ia.shape[1] + 2 * (DAL_ARA * MM + da.shape[1])
    if toplam <= SATIR_MAX or cap - 0.25 < YAZI_MIN_MM * MM:
        break
    cap -= 0.25
if toplam > SATIR_MAX:
    sys.exit(f'HATA: on yazi {YAZI_MIN_MM} mm ile dallarla birlikte sigmiyor ({toplam:.0f} px > {SATIR_MAX})')
on.ekle('yazi', ia, -ia.shape[1] / 2, TABAN - ib)
orta_y = TABAN - cap / 2
dx = ia.shape[1] / 2 + DAL_ARA * MM
on.ekle('dal_sol', da[:, ::-1], -dx - da.shape[1], orta_y - da.shape[0] / 2, rgb=dr[:, ::-1])
on.ekle('dal_sag', da, dx, orta_y - da.shape[0] / 2, rgb=dr)
on_ara = on.kontrol()

# ---------------- ciz + silindir acilimi ----------------
tv = {'on': on.ciz(), 'arka': arka.ciz()}
baski = np.full((FH, FW, 3), 255.0)
yy = np.arange(FH)
for yuz in ('on', 'arka'):
    u = np.arange(FW)
    th = (u - FACE[yuz]) / RK
    ok = np.abs(th) < math.asin(min(1.0, TW / RK))
    xv = RK * np.sin(th[ok]) + TW
    oy = (FH - 2 * TH) // 2
    for c in range(3):
        col = ndimage.map_coordinates(tv[yuz][..., c], [np.repeat(yy[:, None] - oy, ok.sum(), 1),
                                                        np.repeat(xv[None, :], FH, 0)], order=1, mode='constant', cval=255)
        baski[:, np.where(ok)[0], c] = np.minimum(baski[:, np.where(ok)[0], c], col)
baski = np.clip(baski, 0, 255).astype(np.uint8)
if BOY == '15':
    b15 = np.full((1140, FW, 3), 255, np.uint8)
    b15[45:45 + FH] = baski
    baski = b15
pv = np.full((2 * TH + 40, 4 * TW + 60, 3), 235.0)
pv[20:20 + 2 * TH, 20:20 + 2 * TW] = tv['on']
pv[20:20 + 2 * TH, 40 + 2 * TW:40 + 4 * TW] = tv['arka']
kaydet_hepsi([(Image.fromarray(np.clip(pv, 0, 255).astype(np.uint8)), CIKTI[0], dict(quality=92)),
              (Image.fromarray(baski), CIKTI[1], dict(dpi=(300, 300)))])
sem_ust = (dal_ust + kut_h / 2 - gl.shape[0] / 2 + TH) / MM
adim(f'OK {BOY}oz | sembol {gl.shape[1] / MM:.1f}x{gl.shape[0] / MM:.1f} mm, ust {sem_ust:.2f} mm | on yazi cap {cap / MM:.2f} mm, '
     f'satir {toplam / MM:.1f} mm | mesaj cap {mes_cap / MM:.2f} mm, gen {ma.shape[1] / MM:.1f} mm | en az aralik on '
     f'{min(on_ara.values()) / MM:.2f} mm, arka {min(ark_ara.values()) / MM:.2f} mm | {OUT}_baski_{BOY}oz.png')
