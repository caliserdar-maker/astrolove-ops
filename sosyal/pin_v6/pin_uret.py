"""AstroLoveArt Pinterest pins P1, P2, P3 (1000x1500, 2:3) for one zodiac pair.

Approved design (Serdar, 12 Oct 2026, Gemini & Leo). Poster pixels are only cut, scaled and moved.
All added text: EB Garamond; gold made from the poster's own gold (P2, P3), navy on the light wall (P1).
No sentence-ending full stops, "&" instead of "and" in image text.

Usage:
  python3 pin_uret.py --poster AstroLoveArt_Gemini_Leo_2000.jpg --a Gemini --b Leo --out cikti/
  --a = sign under the LEFT small sign on the poster, --b = sign under the RIGHT small sign.
Writes: {a}-and-{b}-zodiac-wall-art-astroloveart-p1.jpg / -p2.jpg / -p3.jpg  and  {a}-and-{b}-parcalar.jpg (QC sheet)
"""
import argparse, json, os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import PchipInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib
import layouts as L

AS = os.path.join(HERE, 'assets')
FR = os.path.join(AS, 'EBGaramond-Regular.ttf')
lib.set_fonts(FR, os.path.join(AS, 'EBGaramond-Italic.ttf'))
NAVY = (18, 24, 52)
W, H = 1000, 1500


# ------------------------------------------------------------------ robust poster parts
class PosterR(lib.Poster):
    """Same as lib.Poster, but every part may consist of several pieces (Aquarius, Libra, Cancer, Pisces...).
    merged = all pieces inside the ring; then the area below the ring is split into horizontal bands:
    band 0 = the two small signs (left half / right half), band 1 = names, bands 2.. = message."""

    def _find_parts(self):
        Wp, Hp = self.w, self.h
        comps = sorted(self.comps, key=lambda c: -c[5])
        rings = [c for c in comps[:6] if c[5] / float(c[3] * c[4]) < 0.03 and c[3] > 0.6 * Wp]
        if not rings:
            raise RuntimeError('halka bulunamadi')
        self.ring = rings[0]
        rx0 = min(c[1] for c in rings); ry0 = min(c[2] for c in rings)
        rx1 = max(c[1] + c[3] for c in rings); ry1 = max(c[2] + c[4] for c in rings)
        ring_ids = {c[0] for c in rings}
        inside = [c for c in comps if c[0] not in ring_ids and c[5] > 50
                  and rx0 < c[1] + c[3] / 2 < rx1 and ry0 < c[2] + c[4] / 2 < ry1]
        if not inside:
            raise RuntimeError('birlesik sembol bulunamadi')
        self.merged_parts = inside
        self.merged = self._union(inside)
        below = sorted([c for c in comps if c[2] > ry1 and c[5] > 300], key=lambda c: c[2])
        bands = []
        for c in below:
            if bands and c[2] <= bands[-1]['y1'] + 40:
                bands[-1]['cs'].append(c); bands[-1]['y1'] = max(bands[-1]['y1'], c[2] + c[4])
            else:
                bands.append({'cs': [c], 'y1': c[2] + c[4]})
        if len(bands) < 3:
            raise RuntimeError(f'beklenen en az 3 satir (burclar, isimler, mesaj), bulunan {len(bands)}')
        left = [c for c in bands[0]['cs'] if c[1] + c[3] / 2 < Wp / 2]
        right = [c for c in bands[0]['cs'] if c[1] + c[3] / 2 >= Wp / 2]
        if not left or not right:
            raise RuntimeError('sol veya sag kucuk burc bulunamadi')
        self.sign_a, self.sign_b = self._union(left), self._union(right)
        self.names_row = self._union(bands[1]['cs'])
        self.msg_row = self._union([c for b in bands[2:] for c in b['cs']])

    def _gold_ramp(self):
        ids = [c[0] for c in self.merged_parts]
        m = np.isin(self.lab, ids) & (self.alpha > 0.98)
        px = self.img[m]
        lum = px @ np.array([0.299, 0.587, 0.114])
        px = px[np.argsort(lum)]
        q = np.linspace(0, len(px) - 1, 256).astype(int)
        ramp = px[q]
        return cv2.GaussianBlur(ramp.reshape(1, 256, 3), (1, 9), 0).reshape(256, 3)


# ------------------------------------------------------------------ shared helpers
def navy_glow(profile, cy_frac, gain=0.70, sigma=0.42):
    rs, prof = profile
    sm = np.stack([gaussian_filter1d(prof[:, c].astype(np.float64), 2.5, mode='nearest') for c in range(3)], 1)
    fine_r = np.linspace(rs[0], rs[-1], 2048)
    fine = np.stack([PchipInterpolator(rs, sm[:, c])(fine_r) for c in range(3)], 1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    r = np.sqrt(((xx - W / 2) / (W * 0.5)) ** 2 + ((yy - H * cy_frac) / (H * 0.5)) ** 2)
    out = np.stack([np.interp(r, fine_r, fine[:, c]) for c in range(3)], -1)
    out *= (1 + gain * np.exp(-(r / sigma) ** 2))[..., None]
    rng = np.random.default_rng(1)
    out += 1.5 * (rng.uniform(-0.5, 0.5, out.shape) + rng.uniform(-0.5, 0.5, out.shape))
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), 'RGB')


def fit(make, size, max_w):
    im = make(size)
    if im.size[0] > max_w:
        im = make(int(size * max_w / im.size[0]))
    return im


def ring_mask(D, w, y0, y1):
    ss = 4; Sz = int(D * ss) + 32
    im = Image.new('L', (Sz, Sz), 0); d = ImageDraw.Draw(im); c = Sz / 2; r = D * ss / 2
    d.ellipse((c - r, c - r, c + r, c + r), outline=255, width=max(1, int(w * ss)))
    m = np.asarray(im.resize((Sz // ss, Sz // ss), Image.LANCZOS)).astype(np.float32) / 255
    n = m.shape[0]; yy, xx = np.mgrid[0:n, 0:n]; yy = yy - n / 2; xx = xx - n / 2
    side = np.abs(xx) > D * 0.25
    dist = np.minimum(np.abs(yy - y0), np.abs(yy - y1))
    inside = (yy > y0) & (yy < y1)
    soft = np.clip(dist / 12.0, 0, 1)
    return np.where(side & inside, 0, np.where(side, m * soft, m))


def build(poster_path, A, B, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    P = PosterR(poster_path)
    prof = P.bg_profile()
    BR = L.bright_ramp(P)
    slug = f'{A.lower()}-and-{B.lower()}'
    pair_caps = f'{A} & {B}'.upper()

    def gold(t, frac, max_frac=0.88):
        return fit(lambda s: lib.metal_text(t, s, BR), int(W * frac), W * max_frac)

    def brand(frac=0.036):
        return lib.metal_text('ASTROLOVEART', int(W * frac), BR, tracking=0.14, bevel=0.9)

    def lines(cv, items, cy, gap):
        hs = [i.size[1] for i in items]
        y = cy - (sum(hs) + gap * (len(items) - 1)) / 2
        for i, h in zip(items, hs):
            lib.paste(cv, i, W / 2, y + h / 2); y += h + gap

    def save(cv, k):
        p = os.path.join(out_dir, f'{slug}-zodiac-wall-art-astroloveart-{k}.jpg')
        cv.save(p, quality=95, subsampling=0)
        return p

    out = {}
    # ---------- P1: wall scene, real poster, navy text
    box = json.load(open(os.path.join(AS, 'P1_kutu.json')))
    img = Image.open(os.path.join(AS, 'P1_duvar_temiz.png')).convert('RGB')
    img.paste(Image.open(poster_path).convert('RGB').resize((box['pw'], box['ph']), Image.LANCZOS), (box['px'], box['py']))

    def flat(t, size, tracking=0.0):
        m = lib.text_mask(t, FR, size, tracking)
        al = (np.clip(m, 0, 1) * 255).astype(np.uint8)
        rgb = np.zeros(al.shape + (3,), np.uint8); rgb[:] = NAVY
        return lib.trim(Image.fromarray(np.dstack([rgb, al]), 'RGBA'))

    def put(im, cy):
        img.paste(im, (round(W / 2 - im.size[0] / 2), round(cy - im.size[1] / 2)), im)

    # two lines on top (Serdar 12 Oct 2026, option C)
    put(fit(lambda s: flat('Personalized zodiac wall art', s), 96, W * 0.86), 120)
    put(fit(lambda s: flat(pair_caps, s, 0.18), 58, W * 0.86), 238)
    put(flat('ASTROLOVEART', 38, 0.24), (box['py'] + box['ph'] + 1438) / 2)
    out['p1'] = save(img, 'p1')

    # ---------- P2: two signs on one orbit, merged symbol in the centre
    cv = navy_glow(prof, 0.47)
    cy, D, sign_h = H * 0.47, 640, 120
    a = lib.scale_h(P.layer(P.sign_a, only_label=False), sign_h)
    b = lib.scale_h(P.layer(P.sign_b, only_label=False), sign_h)
    sw = L.stroke_width(lib.scale_h(P.layer(P.sign_a, only_label=False), 150))
    # sign labels: same size for both, shrunk together if the longer one does not fit beside the frame edge
    lab_size = int(W * L.TYPE['label']['size'])
    mk = lambda t, s: lib.metal_text(t.upper(), s, BR, tracking=L.TYPE['label']['tracking'], bevel=0.9)
    max_lab = 2 * (W / 2 - D / 2 - 40)
    widest = max(mk(A, lab_size).size[0], mk(B, lab_size).size[0])
    if widest > max_lab:
        lab_size = int(lab_size * max_lab / widest)
    lab_a, lab_b = mk(A, lab_size), mk(B, lab_size)
    lab_gap = 44
    rm = ring_mask(D, max(1.6, sw * 0.30), -sign_h / 2 - 28, sign_h / 2 + lab_gap + lab_a.size[1] + 26)
    lib.paste(cv, lib.metal_from_mask(rm, P.ramp, bevel=0.9), W / 2, cy, shadow=False)
    lib.paste(cv, a, W / 2 - D / 2, cy); lib.paste(cv, b, W / 2 + D / 2, cy)
    lib.paste(cv, lab_a, W / 2 - D / 2, cy + sign_h / 2 + lab_gap, shadow=False)
    lib.paste(cv, lab_b, W / 2 + D / 2, cy + sign_h / 2 + lab_gap, shadow=False)
    center = lib.scale_h(P.layer(P.merged, only_label=False), 410)
    if center.size[0] > D * 0.78:
        center = lib.scale_w(center, round(D * 0.78))
    a_ = np.asarray(center)[..., 3].astype(np.float32)
    yy, xx = np.mgrid[0:a_.shape[0], 0:a_.shape[1]]
    gx = (xx * a_).sum() / a_.sum(); gy = (yy * a_).sum() / a_.sum()
    lib.paste(cv, center, W / 2 + (center.size[0] / 2 - gx) * 0.8, cy + (center.size[1] / 2 - gy) * 0.5)
    lines(cv, [gold('Two signs', 0.074), gold('One shared symbol', 0.074)], H * 0.13, 12)
    lib.paste(cv, gold('Zodiac art with your names & message', 0.052), W / 2, H * 0.80)
    lib.paste(cv, brand(), W / 2, H * 0.87, shadow=False)
    out['p2'] = save(cv, 'p2')

    # ---------- P3: large merged symbol + names from the poster + product line
    cv = navy_glow(prof, 0.40)
    lib.paste(cv, fit(lambda s: lib.metal_text(pair_caps, s, BR, tracking=0.16, bevel=1.0), int(W * 0.062), W * 0.86),
              W / 2, H * 0.078, shadow=False)
    merged = lib.scale_h(P.layer(P.merged, only_label=False), 740)
    if merged.size[0] > W * 0.84:
        merged = lib.scale_w(merged, round(W * 0.84))
    a_ = np.asarray(merged)[..., 3].astype(np.float32); yy, xx = np.mgrid[0:a_.shape[0], 0:a_.shape[1]]
    lib.paste(cv, merged, W / 2 + (merged.size[0] / 2 - (xx * a_).sum() / a_.sum()) * 0.8, H * 0.385)
    names = lib.scale_w(P.layer(P.names_row, only_label=False), round(W * 0.80))
    lib.paste(cv, names, W / 2, H * 0.715)
    lib.paste(cv, gold('Zodiac wall art with your names & message', 0.052), W / 2, H * 0.805)
    lib.paste(cv, brand(), W / 2, H * 0.885, shadow=False)
    out['p3'] = save(cv, 'p3')

    # ---------- QC sheet: what was cut from the poster (merged, left sign, right sign, names, message)
    parts = [('BIRLESIK', P.merged), ('SOL ' + A.upper(), P.sign_a), ('SAG ' + B.upper(), P.sign_b),
             ('ISIMLER', P.names_row), ('MESAJ', P.msg_row)]
    sheet = Image.new('RGB', (1500, 420), (20, 24, 40)); d = ImageDraw.Draw(sheet)
    x = 10
    for t, c in parts:
        im = P.layer(c, only_label=False); im.thumbnail((280, 330))
        sheet.paste(im, (x, 60), im); d.text((x, 15), t, fill=(240, 240, 240)); x += 298
    sheet.save(os.path.join(out_dir, f'{slug}-parcalar.jpg'), quality=90)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--poster', required=True)
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--out', required=True)
    g = ap.parse_args()
    print(build(g.poster, g.a, g.b, g.out))
