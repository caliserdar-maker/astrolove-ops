#!/usr/bin/env python3
"""SADE kupa baski dosyasi, CANLI Orchard tasarimi uzerine (Serdar 31 Eki 2026): on ve arka susleme (cicek/meyve dallari)
canli cift kupayla AYNI (kes_suslme.py katmani). ON: cift sembolu yerine tek burc sembolu (ayni kutu), altinda tek isim
(cift kupadaki isim satiri yerinde; sonsuz isareti, kucuk burc isaretleri ve burc adlari YOK). ARKA: yalniz mesaj
(nazar ve imza YOK). baski_kes.py'den turetilmistir; olculer onayli gorselden (kes json, yerlesim).
Kullanim: python3 -I baski_kes_sade.py <kes_onek> <glif_png> <isim> <mesaj> <renk r,g,b> <cikti_onek>
Mesaj canli cift kupadaki mesaj tabaninda (yeri degismez).
"""
import json, math, os, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

t0 = time.time()
if len(sys.argv) != 7:
    sys.exit(__doc__)
KES, GLIF, ISIM, MESAJ, RENK_S, OUT = sys.argv[1:7]
ISIM, MESAJ = ' '.join(ISIM.split()), ' '.join(MESAJ.split())
if not ISIM or not MESAJ:
    sys.exit('HATA: isim ve mesaj zorunlu')
V_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'varlik')) + '/'
GAR, ITA = V_DIR + 'font/EBGaramond[wght].ttf', V_DIR + 'font/EBGaramond-Italic[wght].ttf'
RENK = np.array([int(v) for v in RENK_S.split(',')], float)

DPI, FW, FH = 300, 2700, 1050
D_IN = float(os.environ.get('D_IN', 3.23))          # 11 oz cap 8,2 cm
RK = D_IN / 2 * DPI
QUARTER = D_IN * math.pi / 4 * DPI
FACE = {'on': FW / 2 - QUARTER, 'arka': FW / 2 + QUARTER}
TW, TH = 484, 525                                   # on gorunus tuvali: x +-484 (yaricap), y = tum baski yuksekligi
MM = DPI / 25.4
PAY = 14                                            # yazi ile susleme arasi en az bosluk (px)

g = json.load(open(f'{KES}_kes.json'))
s = g['s']


def adim(m):
    print(f'[{time.time() - t0:5.1f}s] {m}', flush=True)


def T(yuz, x, y):
    """onayli gorsel px -> on gorunus px"""
    G = g[yuz]
    return (x - G['xc']) * s, (y - G['orta']) * s


def alfa(p):
    a = np.asarray(Image.open(p).convert('RGBA'))[..., 3].astype(float) / 255
    ys, xs = np.where(a > 0.05)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def olcek(a, kutu=None, w=None):
    H, W = a.shape
    k = min(kutu[0] / W, kutu[1] / H) if kutu else w / W
    return np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((max(1, round(W * k)), max(1, round(H * k))),
                                                                          Image.LANCZOS)).astype(float) / 255


def bas(tv, a, cx, cy):
    a = np.maximum(a, ndimage.grey_dilation(a, size=(3, 3)) * 0.85)   # cizgi ~1 px kalin (onayli gorunum)
    h, w = a.shape
    x0, y0 = int(round(cx - w / 2 + TW)), int(round(cy - h / 2 + TH))
    tv[y0:y0 + h, x0:x0 + w] = tv[y0:y0 + h, x0:x0 + w] * (1 - a[..., None]) + RENK * a[..., None]


def yazi(m, font, cap_px, ag, aralik=0.0):
    f = ImageFont.truetype(font, 200)
    f.set_variation_by_axes([ag])
    capH = f.getbbox('H')[3] - f.getbbox('H')[1]
    f = ImageFont.truetype(font, max(4, round(200 * cap_px / capH)))
    f.set_variation_by_axes([ag])
    d = ImageDraw.Draw(Image.new('L', (1, 1)))
    asc, desc = f.getmetrics()
    W = int(sum(d.textlength(c, font=f) for c in m) + aralik * (len(m) - 1) + 40)
    im = Image.new('L', (W, asc + desc + 40), 0)
    dd = ImageDraw.Draw(im)
    x = 20
    for c in m:
        dd.text((x, 20), c, font=f, fill=255)
        x += d.textlength(c, font=f) + aralik
    a = np.asarray(im).astype(float) / 255
    ys, xs = np.where(a > 0.05)
    return a[:, xs.min():xs.max() + 1], 20 + asc


def koy(tv, a, base, xsol, taban):
    h, w = a.shape
    x0, y0 = int(round(xsol + TW)), int(round(taban - base + TH))
    tv[y0:y0 + h, x0:x0 + w] = tv[y0:y0 + h, x0:x0 + w] * (1 - a[..., None]) + RENK * a[..., None]


def susleme_tuval(yuz, dosya):
    tv = np.full((2 * TH, 2 * TW, 3), 255.0)
    img = np.asarray(Image.open(dosya).convert('RGB')).astype(float)
    sx, sy = g[yuz]['sol_ust_fv']
    x0, y0 = int(round(sx + TW)), int(round(sy + TH))
    h, w = img.shape[:2]
    # tuval disina tasan kisim kirpilir
    ax0, ay0 = max(0, -x0), max(0, -y0)
    bx0, by0 = max(0, x0), max(0, y0)
    bx1, by1 = min(2 * TW, x0 + w), min(2 * TH, y0 + h)
    tv[by0:by1, bx0:bx1] = np.minimum(tv[by0:by1, bx0:bx1], img[ay0:ay0 + by1 - by0, ax0:ax0 + bx1 - bx0])
    return tv


def serbest(mask, y0, y1, cx):
    rows = mask[int(y0) + TH:int(y1) + TH].any(0)
    sol = np.where(rows[:int(cx) + TW])[0]
    sag = np.where(rows[int(cx) + TW:])[0]
    l = (sol.max() - TW) if len(sol) else -TW
    r = (int(cx) + sag.min()) if len(sag) else TW
    return 2 * min(cx - l, r - cx) - 2 * PAY


def satir(tv, mask, m, font, cap0, ag, cx, taban, aralik=0.0, min_cap=None, maxw_sabit=None, aralik_min=0.15, min_cap2=None,
          mesafe=None):
    """mesafe: susleme uzaklik haritasi (on tuval px); verilirse yazinin her pikseli suslemeden en az PAY px uzak olmali (2B)."""
    cap, ar = cap0, aralik
    while True:
        a, base = yazi(m, font, cap, ag, ar * cap / cap0)
        h = a.shape[0]
        maxw = maxw_sabit or serbest(mask, taban - cap * 1.1, taban + cap * 0.3, cx)
        sigar = a.shape[1] <= maxw
        if sigar and mesafe is not None:
            x0, y0 = int(round(cx - a.shape[1] / 2 + TW)), int(round(taban - base + TH))
            bolge = mesafe[y0:y0 + h, x0:x0 + a.shape[1]]
            sigar = bolge[a[:bolge.shape[0], :bolge.shape[1]] > 0.3].min() >= PAY
        if sigar:
            break
        if ar > aralik * aralik_min:
            ar -= aralik * 0.05
        elif min_cap is None or cap - 0.25 >= min_cap - 1e-6:
            cap -= 0.25
        elif ar > 0:                      # alt sinirdayiz: punto sabit, harf araligi sifira kadar daralir
            ar = max(0.0, ar - aralik * 0.03)
        elif min_cap2 is not None and cap - 0.25 >= min_cap2 - 1e-6:   # istisna: aralik sifirken punto ikinci sinira kadar
            cap -= 0.25
        else:
            break
    koy(tv, a, base, cx - a.shape[1] / 2, taban)
    return cap, not sigar


# ---------------- ON ----------------
on = susleme_tuval('on', f'{KES}_on.png')
MASK_ON = on.min(-1) < 245
L = g['yerlesim']
cx, _ = T('on', L['on_merkez_x'], 0)
_, y_sem = T('on', 0, L['sembol_y'])
SEMBOL_K = float(os.environ.get('SEMBOL_K', 1.30))    # en buyuk sembol boyu: cift sembol kutusunun 1,30 kati (Serdar 31 Eki "daha buyuk")
KALIN = float(os.environ.get('KALIN', 1.45))          # cizgi kalinligi carpani (Serdar 31 Eki "daha kalin")
BOSLUK = float(os.environ.get('BOSLUK', 2.5)) * MM     # sembol ile susleme dali arasi en az (mm); sigmazsa sembol kuculur
UZAK = ndimage.distance_transform_edt(~MASK_ON)
g0 = alfa(GLIF)


def sembol_yap(k):
    a = olcek(g0, kutu=(L['sembol_w'] * s * k, L['sembol_h'] * s * k))
    ciz = 2 * ndimage.distance_transform_edt(a > 0.5).max()
    r = max(0.0, (KALIN - 1) * ciz / 2)
    if r > 0:                                                    # dis kenari esit kalinlastir (yumusak kenar korunur)
        p_ = int(np.ceil(r)) + 2
        a = np.pad(a, p_)
        a = np.clip(np.maximum(a, 1 - (ndimage.distance_transform_edt(a < 0.5) - r)), 0, 1)
        ys, xs = np.where(a > 0.02)
        a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    m = np.zeros(MASK_ON.shape, bool)
    x0, y0 = int(round(cx - a.shape[1] / 2 + TW)), int(round(y_sem - a.shape[0] / 2 + TH))
    m[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = a > 0.3
    return a, ciz, ciz + 2 * r, UZAK[m].min()


k = SEMBOL_K
while True:
    ana, _cizgi, _cizgi2, _uzak = sembol_yap(k)
    if _uzak >= BOSLUK or k <= 0.8:
        break
    k -= 0.02
if _uzak < PAY:
    sys.exit(f'HATA: sembol susleme dalina {_uzak:.0f} px (en az {PAY})')
bas(on, ana, cx, y_sem)
# isim satiri: tek isim, cift kupadaki isim satiri yerinde ve boyunda
_, t_isim = T('on', 0, L['isim_taban'])
ISIM_CAP = L['isim_cap'] * s
isim_cap, isim_tasti = satir(on, MASK_ON, ISIM.upper(), GAR, ISIM_CAP, 680, cx, t_isim, aralik=ISIM_CAP * 0.06,
                             min_cap=2.2 * MM, mesafe=ndimage.distance_transform_edt(~MASK_ON))
burc_tasti = False
adim(f'on: sembol {ana.shape[1] / MM:.1f}x{ana.shape[0] / MM:.1f} mm (K {k:.2f}, kalin {KALIN}, cizgi {_cizgi:.0f}->{_cizgi2:.0f} px, dala {_uzak:.0f} px), isim cap {isim_cap / MM:.2f} mm')

# ---------------- ARKA ----------------
arka = susleme_tuval('arka', f'{KES}_arka.png')
MASK_AR = arka.min(-1) < 245
ax, _ = T('arka', L['arka_merkez_x'], 0)
_, t_mes = T('arka', 0, L['mesaj_taban'])
mes_cap, mes_tasti = satir(arka, MASK_AR, MESAJ, ITA, L['mesaj_cap'] * s, 600, ax, t_mes, min_cap=2.2 * MM,
                           maxw_sabit=860)
adim(f'arka: mesaj cap {mes_cap / MM:.2f} mm (nazar ve imza yok)')

# ---------------- silindir -> baski ----------------
baski = np.full((FH, FW, 3), 255.0)
yy = np.arange(FH)
for yuz, tv in (('on', on), ('arka', arka)):
    u = np.arange(FW)
    th = (u - FACE[yuz]) / RK
    ok = np.abs(th) < math.asin(min(1.0, TW / RK))
    xv = RK * np.sin(th[ok]) + TW
    oy = (FH - 2 * TH) // 2
    for c in range(3):
        col = ndimage.map_coordinates(tv[..., c], [np.repeat(yy[:, None] - oy, ok.sum(), 1),
                                                   np.repeat(xv[None, :], FH, 0)], order=1, mode='constant', cval=255)
        baski[:, np.where(ok)[0], c] = np.minimum(baski[:, np.where(ok)[0], c], col)
Image.fromarray(np.clip(baski, 0, 255).astype(np.uint8)).save(OUT + '_baski_11oz.png', dpi=(300, 300))
pv = np.full((2 * TH + 40, 4 * TW + 60, 3), 235.0)
pv[20:20 + 2 * TH, 20:20 + 2 * TW] = on
pv[20:20 + 2 * TH, 40 + 2 * TW:40 + 4 * TW] = arka
Image.fromarray(np.clip(pv, 0, 255).astype(np.uint8)).save(OUT + '_onizleme.jpg', quality=92)
adim(f'kaydedildi {OUT}_baski_11oz.png; tasma: isim {isim_tasti}, mesaj {mes_tasti}')
