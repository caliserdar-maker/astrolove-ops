"""Temiz metin katmani: eski metni olcerek font/boyut/agirlik/izleme uydurur, zemini duz renkle siler,
yeni metni ayni taban cizgisine native font ile yazar (bitmap yama yok)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
FD = os.environ.get('FONT_DIR', '/home/user/astrolove-ops/work/fonts/')
FONTS = {'mont': FD + 'Montserrat[wght].ttf', 'ebg': FD + 'EBGaramond[wght].ttf'}
_cache = {}
def font(key, size, w):
    k = (key, size, w)
    if k not in _cache:
        f = ImageFont.truetype(FONTS[key], size=size); f.set_variation_by_axes([w]); _cache[k] = f
    return _cache[k]

def render_mask(text, key, size, w, track, W=None, H=None, x=0, base=0):
    f = font(key, size, w)
    width = int(sum(f.getlength(ch) for ch in text) + track * size * len(text) + size * 2)
    W = W or width; H = H or int(size * 2.2)
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    xx = x
    for ch in text:
        d.text((xx, base), ch, font=f, fill=255, anchor='ls')
        xx += f.getlength(ch) + track * size
    return np.asarray(im).astype(np.float64) / 255.0

def ink_of(card, box, bg):
    x0, y0, x1, y1 = box
    c = card[y0:y1, x0:x1]
    d = np.abs(c - bg).max(2)
    m = d > 0.5 * d.max()
    ys, xs = np.where(m)
    core = d >= 0.9 * d.max()
    ink = np.median(c[core], 0)
    return (xs.min() + x0, ys.min() + y0, xs.max() + x0 + 1, ys.max() + y0 + 1), ink, np.clip(d / max(np.abs(ink - bg).max(), 1), 0, 1)

def _w(text, key, size, w, track):
    f = font(key, size, w)
    return sum(f.getlength(ch) for ch in text) + track * size * (len(text) - 1)

def fit(card, box, text, key, bg, weights=(300, 400, 500, 600)):
    """Murekkep: kalin cekirdek pikseller (sabit). Boyut kesirli; izleme genislikten analitik; ofset +-3 px;
    secim olcutu yeniden kurma MSE."""
    (bx0, by0, bx1, by1), ink0, cov = ink_of(card, box, bg)
    pad = 5
    tgt = card[by0 - pad:by1 + pad, bx0 - pad:bx1 + pad]
    Ht, Wt = by1 - by0, bx1 - bx0
    best = None
    for w in weights:
        # boyutu yukseklikten bul
        sizes = []
        for size in np.arange(max(6, Ht * 0.7), Ht * 2.6, 0.25):
            m = render_mask(text, key, float(size), w, 0.0, x=10, base=int(size * 1.6))
            ys = np.where(m.max(1) > 0.5)[0]
            if ys.max() - ys.min() + 1 >= Ht - 0.5: sizes = [size - 0.25, size, size + 0.25]; break
        for size in sizes:
            size = float(size)
            m0 = render_mask(text, key, size, w, 0.0, x=10, base=int(size * 1.6))
            xs = np.where(m0.max(0) > 0.5)[0]
            track = (Wt - (xs.max() - xs.min() + 1)) / (size * max(len(text) - 1, 1))
            if abs(track) > 0.15: continue
            m = render_mask(text, key, size, w, track, x=10, base=int(size * 1.6))
            ys = np.where(m.max(1) > 0.5)[0]; xs = np.where(m.max(0) > 0.5)[0]
            for ddy in range(-2, 3):
                for ddx in range(-2, 3):
                    y0 = ys.min() - pad + ddy; x0 = xs.min() - pad + ddx
                    if y0 < 0 or x0 < 0: continue
                    sub = m[y0:y0 + tgt.shape[0], x0:x0 + tgt.shape[1]]
                    mm = np.zeros(tgt.shape[:2]); mm[:sub.shape[0], :sub.shape[1]] = sub
                    rec = bg * (1 - mm[..., None]) + ink0 * mm[..., None]
                    err = float(((rec - tgt) ** 2).mean())
                    if best is None or err < best['mse']:
                        best = dict(mse=err, key=key, w=w, track=float(track), size=size,
                                    ox=int(bx0 - pad - x0 + 10), oy=int(by0 - pad - y0), base0=int(size * 1.6),
                                    ink=[float(v) for v in ink0])
    best['box'] = [int(bx0), int(by0), int(bx1), int(by1)]
    return best

def replace(card, box, old, new, key, align='left', weights=(300, 400, 500, 600), pad=5, bg=None):
    if bg is None:
        bg = np.median(np.concatenate([card[box[1] - 3, box[0]:box[2]], card[box[3] + 2, box[0]:box[2]]]), 0)
    p = fit(card, box, old, key, bg, weights)
    bx0, by0, bx1, by1 = p['box']
    H, W = card.shape[:2]
    card = card.copy(); card[by0 - pad:by1 + pad, bx0 - pad:bx1 + pad] = bg
    # eski metnin kart koordinatinda taban cizgisi ve baslangic x'i
    base = p['oy'] + p['base0']; x_old = p['ox']
    if align == 'center':
        f = font(key, p['size'], p['w'])
        m_old = render_mask(old, key, p['size'], p['w'], p['track'], base=p['base0'])
        m_new = render_mask(new, key, p['size'], p['w'], p['track'], base=p['base0'])
        xo = np.where(m_old.max(0) > 0.35)[0]; xn = np.where(m_new.max(0) > 0.35)[0]
        x_new = x_old + (xo.min() + xo.max()) / 2 - (xn.min() + xn.max()) / 2
    else:
        x_new = x_old
    full = render_mask(new, key, p['size'], p['w'], p['track'], W=W, H=H, x=x_new, base=base)
    ink = np.array(p['ink'])
    card = card * (1 - full[..., None]) + ink * full[..., None]
    # dogrulama: eski metni ayni parametrelerle ciz, orijinalle MAE
    p.update(new=new, align=align)
    return card, p

def draw_with(card, p, new, cx=None, x=None, base=None):
    """Uydurulmus parametrelerle (p) yeni metni ciz. cx: merkez, x: sol baslangic (render kaydi)."""
    H, W = card.shape[:2]
    if cx is not None:
        m = render_mask(new, p['key'], p['size'], p['w'], p['track'], x=10, base=p['base0'])
        xs = np.where(m.max(0) > 0.35)[0]; x = cx - (xs.min() + xs.max()) / 2 + 10
    full = render_mask(new, p['key'], p['size'], p['w'], p['track'], W=W, H=H, x=x, base=base)
    ink = np.array(p['ink'])
    return card * (1 - full[..., None]) + ink * full[..., None]
