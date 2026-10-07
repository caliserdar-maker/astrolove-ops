# Tum ogeler icin temiz alfa (7200x10800): yazilar fonttan, semboller potrace vektorden, cember analitik
import numpy as np, cv2, json, time, io, potrace, cairosvg
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
T = time.time()
def log(*a): print(f'[{time.time()-T:6.1f}s]', *a, flush=True)
M = np.load('/home/claude/blender/M_tam.npy', mmap_mode='r')
B = json.load(open('/home/claude/blender/bolgeler.json'))
FONT = '/home/claude/motor_klon/motor/font/'
OUT = {}

def delik_doldur(m, esik):
    n, l, s, _ = cv2.connectedComponentsWithStats(1 - m, connectivity=4)
    for i in range(1, n):
        x, y, w, h, a = s[i]
        if a < esik and x > 0 and y > 0 and x + w < m.shape[1] and y + h < m.shape[0]:
            m[l == i] = 1
    return m

def kucuk_at(m, esik):
    n, l, s, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    for i in range(1, n):
        if s[i][4] < esik: m[l == i] = 0
    return m

def puruz_al(m, k, sg):
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    return (cv2.GaussianBlur(m.astype(np.float32), (0, 0), sg) > 0.5).astype(np.uint8)

def vektor_alfa(m):
    """ikili maske -> potrace -> kenar yumusatilmis alfa (uint8)"""
    H, W = m.shape
    path = potrace.Bitmap(~m.astype(bool)).trace(turdsize=50, alphamax=1.0, opticurve=True, opttolerance=0.2)
    parts = []
    for c in path:
        s = c.start_point; d = f'M{s.x:.2f},{s.y:.2f}'
        for g in c.segments:
            if g.is_corner: d += f' L{g.c.x:.2f},{g.c.y:.2f} L{g.end_point.x:.2f},{g.end_point.y:.2f}'
            else: d += f' C{g.c1.x:.2f},{g.c1.y:.2f} {g.c2.x:.2f},{g.c2.y:.2f} {g.end_point.x:.2f},{g.end_point.y:.2f}'
        parts.append(d + ' Z')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<path fill-rule="evenodd" fill="#000" d="{" ".join(parts)}"/></svg>')
    r = np.asarray(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('LA'))[..., 1]
    return r.copy(), svg

def ekle(ad, x0, y0, al, svg=None):
    ys, xs = np.nonzero(al > 0)
    a, b, c, d = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    p = 8; a, c = max(0, a - p), max(0, c - p); b, d = min(al.shape[0], b + p), min(al.shape[1], d + p)
    OUT[ad] = (x0 + c, y0 + a, al[a:b, c:d].copy())
    if svg: open(f'/home/claude/blender/vektor_{ad}.svg', 'w').write(svg)
    log(ad, 'kutu', x0 + c, y0 + a, d - c, b - a)

def iou(a, b):
    a = a > 127; b = b > 127
    return (a & b).sum() / max((a | b).sum(), 1)

# --- 1 semboller (vektor) ---
def yerlestir(ad, kaynak, kk, mm, ox, oy):
    """temiz kaynak alfayi T5 maskesine olcek+konum eslestirerek koy"""
    src = np.asarray(Image.open(kaynak).convert('L')).astype(np.float32)[kk[1]:kk[3], kk[0]:kk[2]]
    P = 80
    mm = np.pad(mm, P); ox -= P; oy -= P
    hedef = cv2.GaussianBlur(mm.astype(np.float32), (0, 0), 2)
    best = None
    for s in np.arange(0.95, 1.051, 0.005):
        t = cv2.resize(src, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
        r = cv2.matchTemplate(hedef, cv2.GaussianBlur(t / 255, (0, 0), 2), cv2.TM_CCORR_NORMED)
        _, v, _, p = cv2.minMaxLoc(r)
        if best is None or v > best[0]: best = (v, s, p, t)
    v, s, (px, py), t = best
    al = np.zeros_like(mm, np.uint8); h, w = t.shape
    al[py:py + h, px:px + w] = np.clip(t, 0, 255).astype(np.uint8)
    log(ad, 'eslesme', round(v, 4), 'olcek', round(s, 3), 'IoU', round(iou(mm * 255, al), 4))
    ekle(ad, ox, oy, al)

G = '/home/claude/blender/girdi/'
for ad, kk in (('kucuk1', (1038, 897, 1784, 1512)), ('kucuk2', (130, 1666, 811, 2349))):
    x0, y0, x1, y1 = B[ad]['kutu']
    yerlestir(ad, G + 'KUCUK_2.png', kk, np.array(M[y0:y1, x0:x1]), x0, y0)

x0, y0, x1, y1 = B['ana']['kutu']
yerlestir('ana', G + 'ANA_DENEME.png', (100, 4629, 3555, 7475), np.array(M[y0:y1, x0:x1]), x0, y0)
for ad, esik, pk in ():
    x0, y0, x1, y1 = B[ad]['kutu']
    m = np.array(M[y0:y1, x0:x1]); m = kucuk_at(delik_doldur(m, esik), 60)
    if pk: m = puruz_al(m, pk, 2.5)
    al, svg = vektor_alfa(m)
    log(ad, 'IoU maske/vektor', round(iou(m * 255, al), 4))
    ekle(ad, x0, y0, al, svg)

# --- 2 isimler + sonsuz ---
x0, y0, x1, y1 = B['isimler']['kutu']
m = np.array(M[y0:y1, x0:x1])
cols = m.any(0)
def aralik(a, b):  # tam koordinat x araligi -> bolge ici maske
    mm = np.zeros_like(m); mm[:, a - x0:b - x0] = m[:, a - x0:b - x0]; return mm
SON = (3400, 4450)
yerlestir('sonsuz', G + 'LOGO_1.png', (760, 192, 1396, 388), aralik(*SON), x0, y0)

def metin_uydur(ad, metin, fontad, wght, mm, ox, oy):
    """mm: hedef ikili maske (bolge), font boyu + konum en iyi IoU"""
    ys, xs = np.nonzero(mm)
    hb = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    def ciz(p):
        F = ImageFont.truetype(FONT + fontad, p); F.set_variation_by_axes([wght])
        b = F.getbbox(metin, anchor='ls')
        im = Image.new('L', (b[2] - b[0] + 40, b[3] - b[1] + 40), 0)
        ImageDraw.Draw(im).text((20 - b[0], 20 - b[1]), metin, font=F, fill=255, anchor='ls')
        a = np.asarray(im); yy, xx = np.nonzero(a > 127)
        return a, (xx.min(), yy.min(), xx.max() + 1, yy.max() + 1)
    hw = hb[2] - hb[0]
    p = 200
    for _ in range(6):
        a, k = ciz(p); p = int(round(p * hw / (k[2] - k[0])))
    best = None
    for pp in range(p - 3, p + 4):
        a, k = ciz(pp)
        for dx in range(-4, 5, 2):
            for dy in range(-4, 5, 2):
                c = np.zeros_like(mm, np.uint8)
                tx, ty = hb[0] - k[0] + dx, hb[1] - k[1] + dy
                sy0, sx0 = max(0, -ty), max(0, -tx)
                h = min(a.shape[0] - sy0, c.shape[0] - ty - sy0); w = min(a.shape[1] - sx0, c.shape[1] - tx - sx0)
                c[ty + sy0:ty + sy0 + h, tx + sx0:tx + sx0 + w] = a[sy0:sy0 + h, sx0:sx0 + w]
                s = iou(mm * 255, c)
                if best is None or s > best[0]: best = (s, pp, dx, dy, c)
    log(ad, metin, 'punto', best[1], 'IoU', round(best[0], 4))
    ekle(ad, ox, oy, best[4])
    return best

metin_uydur('isim1', 'MAXWELL', 'Cinzel.ttf', 500, aralik(x0, SON[0]), x0, y0)
metin_uydur('isim2', 'QUINN', 'Cinzel.ttf', 500, aralik(SON[1], x1), x0, y0)
x0, y0, x1, y1 = B['tagline']['kutu']
metin_uydur('tagline', 'Perfectly Paired by Zodiac Kisses', 'EBGaramond-Italic.ttf', 400, np.array(M[y0:y1, x0:x1]), x0, y0)

# --- 3 cember (analitik: merkez/yaricap uydurma, aci basina kalinlik, uclarda incelme) ---
x0, y0, x1, y1 = B['cember']['kutu']
m = np.array(M[y0:y1, x0:x1]); ax0, ay0, ax1, ay1 = B['ana']['kutu']
m[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] = 0; m = kucuk_at(m, 2000)
ys, xs = np.nonzero(m); xs = xs + x0; ys = ys + y0
A = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]; bb = xs.astype(np.float64) ** 2 + ys.astype(np.float64) ** 2
cx, cy, c = np.linalg.lstsq(A, bb, rcond=None)[0]; R = np.sqrt(c + cx ** 2 + cy ** 2)
r = np.hypot(xs - cx, ys - cy); t = np.degrees(np.arctan2(ys - cy, xs - cx)) % 360
nb = 720; bi = (t * 2).astype(int) % nb
gen = np.zeros(nb); rm = np.full(nb, R)
for i in range(nb):
    rr = r[bi == i]
    if len(rr) > 3: gen[i] = len(rr) / (R * np.radians(0.5)); rm[i] = np.median(rr)
log('cember merkez', round(cx, 1), round(cy, 1), 'R', round(R, 1), 'kalinlik medyan', round(np.median(gen[gen > 0]), 2))
# bosluk (alt) araligi: kalinlik 0 olan en uzun ardisik aci dizisi
z = np.r_[gen, gen] < 0.5; en = (0, 0); i = 0
while i < 2 * nb:
    if z[i]:
        j = i
        while j < 2 * nb and z[j]: j += 1
        if j - i > en[1] - en[0]: en = (i, j)
        i = j
    else: i += 1
ac_b, ac_s = (en[0] % nb) / 2, (en[1] % nb) / 2  # bosluk baslangic/bitis (derece)
log('bosluk', ac_b, '->', ac_s)
gk = np.median(gen[gen > 0])
var = gen > 0
# kalinlik: medyan sabit, uclarda olculen incelme egrisi yumusatilarak
gs = np.where(var, gen, 0); gs = np.convolve(np.r_[gs[-20:], gs, gs[:20]], np.ones(21) / 21, 'same')[20:-20]
gs = np.minimum(gs, gk); rs = np.convolve(np.r_[rm[-20:], rm, rm[:20]], np.ones(41) / 41, 'same')[20:-20]
gs[~var] = 0
yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
rr = np.hypot(xx - cx, yy - cy); tt = (np.degrees(np.arctan2(yy - cy, xx - cx)) % 360) * 2
del xx, yy
g = np.interp(tt, np.arange(nb + 1), np.r_[gs, gs[0]]).astype(np.float32)
rc = np.interp(tt, np.arange(nb + 1), np.r_[rs, rs[0]]).astype(np.float32)
al = np.clip(g / 2 - np.abs(rr - rc) + 0.5, 0, 1)
al = (al * 255 + 0.5).astype(np.uint8)
log('cember IoU', round(iou(m * 255, al), 4))
ekle('cember', x0, y0, al)
json.dump({'cember': dict(cx=float(cx), cy=float(cy), R=float(R), kalinlik=float(gk), bosluk=[ac_b, ac_s])},
          open('/home/claude/blender/cember.json', 'w'))
np.savez_compressed('/home/claude/blender/alfa_ogeler.npz', **{k: v[2] for k, v in OUT.items()},
                    _konum=np.array([[*OUT[k][:2]] for k in OUT]), _ad=np.array(list(OUT)))
log('bitti')
