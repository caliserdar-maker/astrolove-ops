# Herhangi bir cift icin temiz alfa (7200x10800). Yerlesim: ciftin mevcut 2000x3000 onizlemesinden (motor ciktisi).
# Semboller KAYNAK maskelerden (GIRDI), yazilar fonttan, sonsuz LOGO_1, cember SCORPIO_VIRGO onayli alfasi (ayni sablon).
# Kullanim: python olustur_alfa_cift.py ONIZLEME.jpg CIKTI.npz ANA_KUTU KUCUK1_SAYFA:KUTU KUCUK2_SAYFA:KUTU ISIM1 ISIM2 "TAGLINE"
import sys, time, json, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
T = time.time()
def log(*a): print(f'[{time.time()-T:6.1f}s]', *a, flush=True)
on, cikti, ana_kutu, k1, k2, isim1, isim2, tag = sys.argv[1:9]
G = '/home/claude/blender/girdi/'; FONT = '/home/claude/motor_klon/motor/font/'
W, H, S = 7200, 10800, 3.6

p = np.asarray(Image.open(on).convert('RGB').resize((2000, 3000), Image.LANCZOS)).astype(np.float32) / 255
hsv = cv2.cvtColor(p, cv2.COLOR_RGB2HSV)
m2 = (np.clip((hsv[..., 1] - 0.25) / 0.2, 0, 1) * np.clip((hsv[..., 2] - 0.22) / 0.2, 0, 1)).astype(np.float32)
# yildizlari ve cemberi yerlesim maskesinden cikar
b2 = (m2 > 0.5).astype(np.uint8)
n_, l_, st_, _ = cv2.connectedComponentsWithStats(b2)
for i in range(1, n_):
    if st_[i, 4] < 120: b2[l_ == i] = 0                                 # yildiz / toz (en kucuk gercek parca '·' > 120 degil ise tagline'da ayri ele alinir)
zs0 = np.load('/home/claude/blender/alfa_ogeler.npz'); K0 = dict(zip([str(a) for a in zs0['_ad']], zs0['_konum']))
cm_ = np.zeros((10800, 7200), np.uint8); cxx, cyy = K0['cember']; ca = zs0['cember']
cm_[cyy:cyy + ca.shape[0], cxx:cxx + ca.shape[1]] = ca
cm2 = cv2.dilate((cv2.resize(cm_, (2000, 3000), interpolation=cv2.INTER_AREA) > 20).astype(np.uint8), np.ones((9, 9), np.uint8))
b2[cm2 > 0] = 0
m2 = m2 * b2
M = cv2.resize(m2, (W, H), interpolation=cv2.INTER_LINEAR) > 0.5      # tam cozunurluk yaklasik maske (yalniz yerlesim icin)

def iou(a, b):
    a = a > 127; b = b > 127
    return (a & b).sum() / max((a | b).sum(), 1)

OUT = {}
def ekle(ad, x0, y0, al):
    ys, xs = np.nonzero(al > 0)
    a, b, c, d = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    q = 8; a, c = max(0, a - q), max(0, c - q); b, d = min(al.shape[0], b + q), min(al.shape[1], d + q)
    OUT[ad] = (x0 + c, y0 + a, al[a:b, c:d].copy())
    log(ad, 'kutu', x0 + c, y0 + a, d - c, b - a)

def temizle(a, oran=0.01):
    b = (a > 0.5).astype(np.uint8)
    n_, l_, st_, _ = cv2.connectedComponentsWithStats(b)
    if n_ <= 1: return b
    buyuk = st_[1:, 4].max()
    for q in range(1, n_):
        if st_[q, 4] < oran * buyuk: b[l_ == q] = 0
    return b

def yerlestir(ad, kaynak, kk, bx):
    """kaynak alfa -> hedef bolge: kutu hizalama (olcek = kutu boyu orani), sonra +-%3 olcek, +-24 px NCC ince ayar (1/2 coz.)"""
    x0, y0, x1, y1 = bx
    mm = temizle(M[y0:y1, x0:x1].astype(np.float32)).astype(np.float32)
    src = np.asarray(Image.open(kaynak).convert('L')).astype(np.float32)[kk[1]:kk[3], kk[0]:kk[2]] / 255
    sb = temizle(src)
    sy, sx = np.nonzero(sb); src = (src * sb)[sy.min():sy.max() + 1, sx.min():sx.max() + 1]
    ys, xs = np.nonzero(mm); hy, hx = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
    s0 = 0.5 * (hy / src.shape[0] + hx / src.shape[1])
    k = 0.5
    hk = cv2.GaussianBlur(cv2.resize(mm, None, fx=k, fy=k, interpolation=cv2.INTER_AREA), (0, 0), 1.0)
    best = None
    for s in np.arange(s0 * 0.97, s0 * 1.0301, s0 * 0.003):
        t = cv2.GaussianBlur(cv2.resize(src, None, fx=s * k, fy=s * k, interpolation=cv2.INTER_AREA), (0, 0), 1.0)
        cy0 = (ys.min() + ys.max()) / 2 * k - t.shape[0] / 2; cx0 = (xs.min() + xs.max()) / 2 * k - t.shape[1] / 2
        R = 12
        pad = np.pad(hk, R + t.shape[0])
        ya, xa = int(round(cy0)) - R + R + t.shape[0], int(round(cx0)) - R + R + t.shape[0]
        pen = pad[ya:ya + t.shape[0] + 2 * R, xa:xa + t.shape[1] + 2 * R]
        r = cv2.matchTemplate(pen, t, cv2.TM_CCORR_NORMED)
        _, v, _, (dx, dy) = cv2.minMaxLoc(r)
        if best is None or v > best[0]: best = (v, s, (cx0 - R + dx) / k, (cy0 - R + dy) / k)
    v, s, px, py = best
    t = cv2.resize(src, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    px, py = int(round(px)), int(round(py))
    al = np.zeros((y1 - y0 + 800, x1 - x0 + 800), np.float32)
    al[py + 400:py + 400 + t.shape[0], px + 400:px + 400 + t.shape[1]] = np.clip(t, 0, 1)
    log(ad, 'eslesme', round(v, 4), 'olcek', round(s, 4), 's0', round(s0, 4))
    ekle(ad, x0 - 400, y0 - 400, (al * 255 + 0.5).astype(np.uint8))

def metin_uydur(ad, metin, fontad, wght, bx):
    x0, y0, x1, y1 = bx
    mm = M[y0:y1, x0:x1].copy()
    n_, l_, st_, _ = cv2.connectedComponentsWithStats(mm.astype(np.uint8))
    buyuk = st_[1:, 4].max()
    for i in range(1, n_):
        if st_[i, 4] < 0.004 * buyuk: mm[l_ == i] = 0
    ys, xs = np.nonzero(mm)
    hb = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    def ciz(pp):
        F = ImageFont.truetype(FONT + fontad, pp); F.set_variation_by_axes([wght])
        b = F.getbbox(metin, anchor='ls')
        im = Image.new('L', (b[2] - b[0] + 40, b[3] - b[1] + 40), 0)
        ImageDraw.Draw(im).text((20 - b[0], 20 - b[1]), metin, font=F, fill=255, anchor='ls')
        a = np.asarray(im); yy, xx = np.nonzero(a > 127)
        return a, (xx.min(), yy.min(), xx.max() + 1, yy.max() + 1)
    pp = 200
    for _ in range(6):
        a, k = ciz(pp); pp = int(round(pp * (hb[2] - hb[0]) / (k[2] - k[0])))
    best = None
    for q in range(pp - 3, pp + 4):
        a, k = ciz(q)
        for dx in range(-6, 7, 2):
            for dy in range(-6, 7, 2):
                c = np.zeros(mm.shape, np.uint8)
                tx, ty = hb[0] - k[0] + dx, hb[1] - k[1] + dy
                sy0, sx0 = max(0, -ty), max(0, -tx)
                h = min(a.shape[0] - sy0, c.shape[0] - ty - sy0); w = min(a.shape[1] - sx0, c.shape[1] - tx - sx0)
                if h <= 0 or w <= 0: continue
                c[ty + sy0:ty + sy0 + h, tx + sx0:tx + sx0 + w] = a[sy0:sy0 + h, sx0:sx0 + w]
                v = iou(mm.astype(np.uint8) * 255, c)
                if best is None or v > best[0]: best = (v, q, c)
    log(ad, metin, 'punto', best[1], 'IoU', round(best[0], 4))
    ekle(ad, x0, y0, best[2])

def bx(a): return [int(v * S) for v in a]   # 2000 olcek kutu -> tam

# --- yerlesim bolgeleri (2000x3000 sablon: SCORPIO_VIRGO ile ayni) ---
akx = [int(v) for v in ana_kutu.split(',')]
yerlestir('ana', G + 'ANA_DENEME.png', akx, bx((250, 350, 1750, 1680)))
for ad, arg, b in (('kucuk1', k1, (250, 1820, 900, 2120)), ('kucuk2', k2, (1100, 1820, 1750, 2120))):
    sayfa, kk = arg.split(':'); yerlestir(ad, G + sayfa + '.png', [int(v) for v in kk.split(',')], bx(b))
# isim satiri: sonsuz merkezde; satir bandi
band = M[int(2120 * S):int(2320 * S)]
cols = band.any(0)
# sonsuz: isim bandinda sablon esleme ile bul (satir ortali, sonsuz merkezde olmayabilir)
bb = bx((150, 2120, 1850, 2320))
lg = np.asarray(Image.open(G + 'LOGO_1.png').convert('L')).astype(np.float32)[192:388, 760:1396] / 255
k = 0.25
hb_ = cv2.GaussianBlur(cv2.resize(M[bb[1]:bb[3], bb[0]:bb[2]].astype(np.float32), None, fx=k, fy=k, interpolation=cv2.INTER_AREA), (0, 0), 1)
tl = cv2.GaussianBlur(cv2.resize(lg, None, fx=k, fy=k, interpolation=cv2.INTER_AREA), (0, 0), 1)
r = np.nan_to_num(cv2.matchTemplate(hb_, tl, cv2.TM_CCORR_NORMED)); _, v_, _, (lx, ly) = cv2.minMaxLoc(r)
sx0 = bb[0] + int(lx / k); sx1 = sx0 + lg.shape[1]
log('sonsuz konum', sx0, sx1, round(v_, 3))
yerlestir('sonsuz', G + 'LOGO_1.png', (760, 192, 1396, 388), (sx0 - 120, bb[1], sx1 + 120, bb[3]))
metin_uydur('isim1', isim1, 'Cinzel.ttf', 500, (bb[0], bb[1], sx0 - 40, bb[3]))
metin_uydur('isim2', isim2, 'Cinzel.ttf', 500, (sx1 + 40, bb[1], bb[2], bb[3]))
metin_uydur('tagline', tag, 'EBGaramond-Italic.ttf', 400, bx((200, 2440, 1800, 2680)))
# cember: SCORPIO_VIRGO onayli (ayni sablon)
zs = np.load('/home/claude/blender/alfa_ogeler.npz'); Ks = dict(zip([str(a) for a in zs['_ad']], zs['_konum']))
OUT['cember'] = (int(Ks['cember'][0]), int(Ks['cember'][1]), zs['cember'])
np.savez_compressed(cikti, **{k: v[2] for k, v in OUT.items()}, _konum=np.array([[*OUT[k][:2]] for k in OUT]), _ad=np.array(list(OUT)))
# kontrol: alfa birlesik vs onizleme maskesi
C = np.zeros((H // 4, W // 4), np.float32)
for k, (x, y, a) in OUT.items():
    a4 = cv2.resize(a.astype(np.float32) / 255, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    y4, x4 = y // 4, x // 4; hh, ww = min(a4.shape[0], C.shape[0] - y4), min(a4.shape[1], C.shape[1] - x4)
    C[y4:y4 + hh, x4:x4 + ww] = np.maximum(C[y4:y4 + hh, x4:x4 + ww], a4[:hh, :ww])
m4 = cv2.resize(m2, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
v = np.zeros(C.shape + (3,), np.uint8); a_ = C > 0.5; b_ = m4 > 0.5
v[a_ & b_] = 200; v[b_ & ~a_] = (0, 0, 255); v[a_ & ~b_] = (255, 128, 0)
cv2.imwrite(cikti.replace('.npz', '_kontrol.png'), v)
log('IoU toplam', round(float((a_ & b_).sum() / (a_ | b_).sum()), 4), 'bitti')
