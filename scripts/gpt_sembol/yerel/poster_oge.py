# Postere ChatGPT oge dokularini uygula (8 Eki 2026): kucuk semboller, sonsuz, isimler, tagline (harf atlasindan),
# cember rengi ana sembolun altinina. Sekil HER ZAMAN bizim alfa (yazim kesin dogru); renk/yuzey ChatGPT.
# Kullanim: python poster_oge.py CIFT TABAN_KLASOR CIKTI_KLASOR   (TABAN: <CIFT>/<CIFT>_GPT_7200x10800.jpg + <CIFT>_alfa.npz)
import sys, os, json, csv, time, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt
Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
def log(*a): print(f'[{time.time()-T0:6.1f}s]', *a, flush=True)
B = '/home/claude/blender/'; DK = B + 'atlas/doku/'; FONT = '/home/claude/motor_klon/motor/font/'
c, TB, OD = sys.argv[1:4]
os.makedirs(f'{OD}/{c}', exist_ok=True)
idx = json.load(open(DK + 'dizin.json'))
def doku(k):
    z = np.load(DK + idx[k]); return z['rgb'].astype(np.float32), z['a'].astype(np.float32) / 255, json.loads(str(z['meta']))
r = {x['cift']: x for x in csv.DictReader(open(B + 'isim_tagline_78.csv'))}[c]
z = np.load(f'{TB}/{c}_alfa.npz'); K = {str(a): (int(x), int(y)) for (x, y), a in zip(z['_konum'], z['_ad'])}
P = np.asarray(Image.open(f'{TB}/{c}/{c}_GPT_7200x10800.jpg').convert('RGB')).astype(np.float32)
log('taban yuklendi')
lab = lambda x: cv2.cvtColor((x.reshape(-1, 1, 3) / 255).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)

def hizala(hedef, kaynak):
    """kaynak alfanin hedef alfaya en iyi oturdugu oteleme (dy, dx): hedef[y,x] ~ kaynak[y+dy, x+dx]"""
    H = max(hedef.shape[0], kaynak.shape[0]) + 80; W = max(hedef.shape[1], kaynak.shape[1]) + 80
    big = np.zeros((H, W), np.float32); big[40:40 + kaynak.shape[0], 40:40 + kaynak.shape[1]] = kaynak
    res = cv2.matchTemplate(big, hedef.astype(np.float32), cv2.TM_CCORR_NORMED)
    _, v, _, p = cv2.minMaxLoc(res)
    return p[1] - 40, p[0] - 40, v

def bindir(ad, renk):
    x, y = K[ad]; a = z[ad].astype(np.float32) / 255; h, w = a.shape
    reg = P[y:y + h, x:x + w]; a3 = a[..., None]
    P[y:y + h, x:x + w] = renk * a3 + reg * (1 - a3)

def sembol_renk(ad, anahtar):
    a = z[ad].astype(np.float32) / 255
    rgb, da, _ = doku(anahtar)
    # boyut farki (sonsuz satir olcegi): murekkep kutusuna gore olcekle
    def kutu(m):
        ys, xs = np.nonzero(m > 0.5); return ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    a0, a1, b0, b1 = kutu(a); c0, c1, d0, d1 = kutu(da)
    f = (b1 - b0) / (d1 - d0)
    if abs(f - 1) > 0.003:
        rgb = cv2.resize(rgb, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC); da = cv2.resize(da, None, fx=f, fy=f, interpolation=cv2.INTER_LINEAR)
    dy, dx, v = hizala(a, da)
    out = np.zeros(a.shape + (3,), np.float32); ok = np.zeros(a.shape, bool)
    ys0, xs0 = max(0, -dy), max(0, -dx)
    for yy in range(1):
        pass
    sy0, sx0 = max(0, dy), max(0, dx)
    hh = min(a.shape[0] - ys0, rgb.shape[0] - sy0); ww = min(a.shape[1] - xs0, rgb.shape[1] - sx0)
    out[ys0:ys0 + hh, xs0:xs0 + ww] = rgb[sy0:sy0 + hh, sx0:sx0 + ww]
    ok[ys0:ys0 + hh, xs0:xs0 + ww] = da[sy0:sy0 + hh, sx0:sx0 + ww] > 0.3
    return doldur(out, ok, a), v

def doldur(out, ok, a):
    eks = (a > 0.01) & ~ok
    if eks.any() and ok.any():
        _, (iy, ix) = distance_transform_edt(~ok, return_indices=True); out[eks] = out[iy[eks], ix[eks]]
    return out

def metin_renk(ad, metin, fontad, wght, punto, tur):
    a = z[ad].astype(np.float32) / 255
    F = ImageFont.truetype(FONT + fontad, punto); F.set_variation_by_axes([wght])
    b = F.getbbox(metin, anchor='ls')
    Wc, Hc = b[2] - b[0] + 200, b[3] - b[1] + 200; ox, oy = 100 - b[0], 100 - b[1]     # kalem, taban
    lab_ = np.zeros((Hc, Wc), np.int32); renk = np.zeros((Hc, Wc, 3), np.float32); ok = np.zeros((Hc, Wc), bool)
    birlesik = np.zeros((Hc, Wc), np.float32)
    for i, ch in enumerate(metin):
        if ch == ' ': continue
        px = ox + F.getlength(metin[:i])
        im = Image.new('L', (Wc, Hc), 0); ImageDraw.Draw(im).text((px, oy), ch, font=F, fill=255, anchor='ls')
        g = np.asarray(im).astype(np.float32) / 255
        birlesik = np.maximum(birlesik, g)
        k = f'{tur}|{ch}'
        if k not in idx: log('ATLASTA YOK', k); continue
        rgb, da, m = doku(k)
        f = punto / m['punto']
        rgb = cv2.resize(rgb, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC); da = cv2.resize(da, None, fx=f, fy=f, interpolation=cv2.INTER_LINEAR)
        X0 = int(round(px - m['kalem_x'] * f)); Y0 = int(round(oy - m['taban_y'] * f))
        ys0, xs0 = max(0, Y0), max(0, X0); ye, xe = min(Hc, Y0 + rgb.shape[0]), min(Wc, X0 + rgb.shape[1])
        if ye <= ys0 or xe <= xs0: continue
        sub = da[ys0 - Y0:ye - Y0, xs0 - X0:xe - X0] > 0.3
        bol = (g[ys0:ye, xs0:xe] > 0.01)
        sec = sub & bol
        renk[ys0:ye, xs0:xe][sec] = rgb[ys0 - Y0:ye - Y0, xs0 - X0:xe - X0][sec]
        ok[ys0:ye, xs0:xe] |= sec
    dy, dx, v = hizala(a, birlesik)          # metin tuvali -> oge alfa
    out = np.zeros(a.shape + (3,), np.float32); okk = np.zeros(a.shape, bool)
    ys0, xs0 = max(0, -dy), max(0, -dx); sy0, sx0 = max(0, dy), max(0, dx)
    hh = min(a.shape[0] - ys0, Hc - sy0); ww = min(a.shape[1] - xs0, Wc - sx0)
    out[ys0:ys0 + hh, xs0:xs0 + ww] = renk[sy0:sy0 + hh, sx0:sx0 + ww]; okk[ys0:ys0 + hh, xs0:xs0 + ww] = ok[sy0:sy0 + hh, sx0:sx0 + ww]
    return doldur(out, okk, a), v

kayit = {}
s1, s2 = c.split('_')
for ad, b in (('kucuk1', s1), ('kucuk2', s2)):
    rk, v = sembol_renk(ad, f'sembol|{b}'); bindir(ad, rk); kayit[ad] = round(v, 4)
rk, v = sembol_renk('sonsuz', 'sembol|SONSUZ'); bindir('sonsuz', rk); kayit['sonsuz'] = round(v, 4)
# isim punto: sonsuz olcegi = satir olcegi (sablonla ayni kural)
_, da, _ = doku('sembol|SONSUZ'); a_s = z['sonsuz'] > 127
olc = (np.ptp(np.nonzero(a_s.any(0))[0]) + 1) / (np.ptp(np.nonzero((da > 0.5).any(0))[0]) + 1)
p = int(round(405 * (olc if olc < 0.999 else 1.0)))
for ad, isim in (('isim1', r['sol_isim']), ('isim2', r['sag_isim'])):
    rk, v = metin_renk(ad, isim.upper(), 'Cinzel.ttf', 500, p, 'buyuk'); bindir(ad, rk); kayit[ad] = round(v, 4)
# tagline punto: sablon kurali (sigmazsa 4'er kucult)
tp = 372; F = ImageFont.truetype(FONT + 'EBGaramond-Italic.ttf', tp); F.set_variation_by_axes([400])
def gen(tp):
    F = ImageFont.truetype(FONT + 'EBGaramond-Italic.ttf', tp); F.set_variation_by_axes([400])
    b = F.getbbox(r['tagline'], anchor='ls'); im = Image.new('L', (b[2] - b[0] + 40, b[3] - b[1] + 40), 0)
    ImageDraw.Draw(im).text((20 - b[0], 20 - b[1]), r['tagline'], font=F, fill=255, anchor='ls')
    xs = np.nonzero(np.asarray(im).max(0) > 127)[0]; return xs.max() + 1 - xs.min()
while gen(tp) > 7200 - 1400: tp -= 4
rk, v = metin_renk('tagline', r['tagline'], 'EBGaramond-Italic.ttf', 400, tp, 'italik'); bindir('tagline', rk); kayit['tagline'] = round(v, 4)
log('ogeler', kayit, 'isim punto', p, 'tagline punto', tp)
# cember: ana sembol altininin a/b ortancasina kaydir
xa, ya = K['ana']; aa = z['ana'] > 200; Lana = lab(P[ya:ya + aa.shape[0], xa:xa + aa.shape[1]][aa])
xc, yc = K['cember']; ac = z['cember'].astype(np.float32) / 255; reg = P[yc:yc + ac.shape[0], xc:xc + ac.shape[1]]
m = ac > 0.6; Lc = lab(reg[m])
kay = np.array([0, np.median(Lana[:, 1]) - np.median(Lc[:, 1]), np.median(Lana[:, 2]) - np.median(Lc[:, 2])], np.float32)
m2 = ac > 0.01; L2 = lab(reg[m2]) + kay * ac[m2][:, None]
reg[m2] = np.clip(cv2.cvtColor(L2.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_Lab2RGB).reshape(-1, 3) * 255, 0, 255)
log('cember a/b kaydirma', np.round(kay[1:], 2))
# olcum: oge basina dE00 (ana ile)
def de00(L1, L2):
    import colour
    return float(colour.delta_E(L1, L2, method='CIE 2000'))
olcum = {}
Lm = np.median(Lana, 0)
for ad in ('kucuk1', 'kucuk2', 'sonsuz', 'isim1', 'isim2', 'tagline', 'cember'):
    x, y = K[ad]; a = z[ad] > 200
    if a.sum() < 50: continue
    Lx = np.median(lab(P[y:y + a.shape[0], x:x + a.shape[1]][a]), 0)
    try: olcum[ad] = round(de00(Lm, Lx), 2)
    except Exception: olcum[ad] = round(float(np.linalg.norm(Lm - Lx)), 2)
log('dE (ana ile)', olcum)
rs = np.random.default_rng(11)
out = np.clip(np.round(P + rs.random(P.shape, dtype=np.float32) - rs.random(P.shape, dtype=np.float32)), 0, 255).astype(np.uint8)
Image.fromarray(out).save(f'{OD}/{c}/{c}_7200x10800.jpg', quality=100, subsampling=0)
on = np.empty((3000, 2000, 3), np.uint8)
for yy in range(0, 10800, 1800):
    bf = cv2.resize(P[yy:yy + 1800], (2000, 500), interpolation=cv2.INTER_AREA)
    bf += rs.random(bf.shape, dtype=np.float32) - rs.random(bf.shape, dtype=np.float32)
    on[yy // 1800 * 500:yy // 1800 * 500 + 500] = np.clip(np.round(bf), 0, 255).astype(np.uint8)
Image.fromarray(on).save(f'{OD}/{c}/{c}_2000.jpg', quality=100, subsampling=0)
json.dump(dict(eslesme=kayit, dE_ana=olcum, isim_punto=p, tagline_punto=tp), open(f'{OD}/{c}/oge_olcum.json', 'w'), indent=1)
log('bitti')
