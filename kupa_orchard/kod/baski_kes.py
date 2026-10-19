#!/usr/bin/env python3
"""Orchard baski dosyasi (11 oz 2700x1050, 300 dpi): susleme ONAYLI GORSELDEN kesilmis katmandir (kes_suslme.py ciktisi).
Sembol, isimler, burc adlari, mesaj ve imza onayli gorseldeki yerlerine ayni olcekle (s) yerlestirilir.
Kullanim: python3 -I baski_kes.py <kes_onek> <sembol_klasoru> <isim1> <isim2> <burc1> <burc2> <mesaj> <renk r,g,b> <cikti_onek>
"""
import json, math, os, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

t0 = time.time()
KES, SEM, ISIM1, ISIM2, B1, B2, MESAJ, RENK_S, OUT = sys.argv[1:10]
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
ana = olcek(alfa(f'{SEM}/ana.png'), kutu=(L['sembol_w'] * s, L['sembol_h'] * s))
if not os.environ.get('SEMBOL_YOK'):
    bas(on, ana, cx, y_sem)
# isim satiri
_, t_isim = T('on', 0, L['isim_taban'])
ISIM_CAP = L['isim_cap'] * s
son = alfa(V_DIR + 'sonsuz.png')
maxw_isim = serbest(MASK_ON, t_isim - ISIM_CAP * 1.1, t_isim + 5, cx)
cap = ISIM_CAP
while True:
    sik = cap < ISIM_CAP * 0.8
    n1, b1 = yazi(ISIM1.upper(), GAR, cap, 680, cap * (0.02 if sik else 0.06))
    n2, b2 = yazi(ISIM2.upper(), GAR, cap, 680, cap * (0.02 if sik else 0.06))
    sm = olcek(son, w=cap * 1.25)
    gap = cap * (0.32 if sik else 0.45)
    tw = n1.shape[1] + 2 * gap + sm.shape[1] + n2.shape[1]
    if tw <= maxw_isim or cap <= 2.2 * MM:
        break
    cap -= 0.5
isim_cap, isim_tasti = cap, tw > maxw_isim
x = cx - tw / 2
koy(on, n1, b1, x, t_isim)
C1 = x + n1.shape[1] / 2
x += n1.shape[1] + gap
bas(on, sm, x + sm.shape[1] / 2, t_isim - cap / 2)
x += sm.shape[1] + gap
koy(on, n2, b2, x, t_isim)
C2 = x + n2.shape[1] / 2
# glifler: D araligi
hD = (C2 - C1) * 0.82 / 2
_, y_glif = T('on', 0, L['glif_y'])
for ad, xx in (('sol', cx - hD), ('sag', cx + hD)):
    if not os.environ.get('GLIF_YOK'):
        bas(on, olcek(alfa(f'{SEM}/{ad}.png'), kutu=(L['glif_w'] * s, L['glif_h'] * s)), xx, y_glif)
# burc adlari
_, t_burc = T('on', 0, L['burc_taban'])
t_burc -= float(os.environ.get('BURC_DY', 0))          # BURC_DY: burc satirini px yukari tasir (yalniz sorunlu ornekler)
_hedef_b = on.copy() if os.environ.get('BURC_YOK') else on   # BURC_YOK: olcum icin burc satiri cizilmez
burc_cap, burc_tasti = satir(_hedef_b, MASK_ON, f'{B1.upper()} · {B2.upper()}', GAR, L['burc_cap'] * s, 640, cx, t_burc,
                             aralik=L['burc_cap'] * s * 0.27, min_cap=1.95 * MM,
                             min_cap2=float(os.environ.get('BURC_MIN', 1.70)) * MM,
                             mesafe=ndimage.distance_transform_edt(~MASK_ON))   # 2B en az PAY (Serdar+ChatGPT 18.10: dala en az 1,2 mm)   # istisna (Serdar+ChatGPT 18.10): sigmazsa aralik 0, sonra en az 1,70 mm
adim(f'on: isim cap {isim_cap / MM:.2f} mm (sinir {maxw_isim:.0f} px), burc cap {burc_cap / MM:.2f} mm')

# ---------------- ARKA ----------------
arka = susleme_tuval('arka', f'{KES}_arka.png')
nx, ny = T('arka', L['nazar_x'], L['nazar_y'])
nz = np.asarray(Image.open(V_DIR + 'ORCHARD_nazar.png').convert('RGB')).astype(float)
ys, xs = np.where(nz.min(-1) < 250)
nz = nz[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
nzs = np.asarray(Image.fromarray(nz.astype(np.uint8)).resize((round(L['nazar_d'] * s),) * 2, Image.LANCZOS)).astype(float)
h, w = nzs.shape[:2]
x0, y0 = int(round(nx - w / 2 + TW)), int(round(ny - h / 2 + TH))
arka[y0:y0 + h, x0:x0 + w] *= nzs / 255.0
MASK_AR = arka.min(-1) < 245
ax, _ = T('arka', L['arka_merkez_x'], 0)
_, t_mes = T('arka', 0, L['mesaj_taban'])
_hedef_m = np.full_like(arka, 255.0) if os.environ.get('MESAJ_YOK') else arka
mes_cap, mes_tasti = satir(_hedef_m, MASK_AR, MESAJ, ITA, L['mesaj_cap'] * s, 600, ax, t_mes, min_cap=2.2 * MM,
                           maxw_sabit=860)
_, t_imza = T('arka', 0, L['imza_taban'])
_hedef_i = np.full_like(arka, 255.0) if os.environ.get('IMZA_YOK') else arka
imza_cap, _ = satir(_hedef_i, MASK_AR, f'{ISIM1} & {ISIM2}', GAR, L['imza_cap'] * s, 640, ax, t_imza, maxw_sabit=760)
adim(f'arka: mesaj cap {mes_cap / MM:.2f} mm, imza cap {imza_cap / MM:.2f} mm, nazar {L["nazar_d"] * s / MM:.1f} mm')

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
adim(f'kaydedildi {OUT}_baski_11oz.png; tasma: isim {isim_tasti}, burc {burc_tasti}, mesaj {mes_tasti}')
