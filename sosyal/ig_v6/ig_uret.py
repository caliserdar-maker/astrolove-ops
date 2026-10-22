"""AstroLoveArt Instagram / Facebook / Threads carousel (4 slides, 1080x1350, 4:5) for one zodiac pair.

Approved design (Serdar, 12 Oct 2026, Gemini & Leo, files in onayli/).
 1 kapak : "{A} & {B}, as one?" + orbit with the gold question mark + "Zodiac art with your names & message" + "Swipe to reveal" + arrow
 2 sembol: "Two signs / Your shared symbol" + orbit with the merged symbol + names from the poster + "Your names, your message"
 3 sahne : the real poster on the wall (no text)
 4 yakin : close-up of the poster's lower part on the wall + navy "Make it yours / ASTROLOVEART / On Etsy"
Poster pixels are only cut, scaled and moved. No sentence-ending full stops, "&" instead of "and".
Reuses lib.py, layouts.py, fonts and PosterR from ../pin_v6.

Usage:
  python3 ig_uret.py --poster AstroLoveArt_Gemini_Leo_2000.jpg --a Gemini --b Leo --out cikti/
  --a = first sign of the pair key (LEFT small sign on the poster), --b = second (RIGHT).
Writes {a}-and-{b}-astroloveart-ig-1.jpg .. -ig-4.jpg
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import PchipInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
PIN = os.path.join(HERE, '..', 'pin_v6')
sys.path.insert(0, PIN)
import pin_uret as PU          # sets the fonts, gives PosterR, fit, ring_mask
import lib
import layouts as L

AS = os.path.join(HERE, 'assets')
W, H = 1080, 1350
NAVY = (18, 24, 52)


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


def build(poster_path, A, B, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    P = PU.PosterR(poster_path)
    prof = P.bg_profile()
    BR = L.bright_ramp(P)
    slug = f'{A.lower()}-and-{B.lower()}'
    box = json.load(open(os.path.join(AS, 'kutular.json')))
    Q = Image.open(os.path.join(AS, 'soru_isareti_v6.png')).convert('RGBA')

    def text(t, frac, max_frac=0.88):
        return PU.fit(lambda s: lib.metal_text(t, s, BR), int(W * frac), W * max_frac)

    def lines(cv, items, cy, gap):
        hs = [i.size[1] for i in items]
        y = cy - (sum(hs) + gap * (len(items) - 1)) / 2
        for i, h in zip(items, hs):
            lib.paste(cv, i, W / 2, y + h / 2); y += h + gap

    def arrow(length=130, w=2.6):
        ss = 4; Lw, Hh = int((length + 20) * ss), int(44 * ss)
        im = Image.new('L', (Lw, Hh), 0); d = ImageDraw.Draw(im)
        y = Hh / 2; x0, x1 = 6 * ss, (length + 6) * ss; hl = 20 * ss
        for (a, b) in [((x0, y), (x1, y)), ((x1 - hl, y - hl * 0.62), (x1, y)), ((x1 - hl, y + hl * 0.62), (x1, y))]:
            d.line([a, b], fill=255, width=int(w * ss))
            for p in (a, b):
                r = w * ss / 2; d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=255)
        m = np.asarray(im.resize((Lw // ss, Hh // ss), Image.LANCZOS)).astype(np.float32) / 255
        return lib.trim(lib.metal_from_mask(m, BR, bevel=0.9))

    def orbit(cv, cy, D, sign_h, raw, ref_h, kind):
        a, b, sw, r = PU.sign_pair(P, sign_h)
        center = PU.fit_center(PU.center_scaled(raw, ref_h, a, b, sign_h, kind), D, a, b)
        lab_gap = 44
        lab_h = lib.metal_text(A.upper(), int(W * L.TYPE['label']['size']), BR, tracking=L.TYPE['label']['tracking'], bevel=0.9).size[1]
        rm = PU.ring_mask(D, max(1.6, sw * 0.30), -sign_h / 2 - 28, sign_h / 2 + lab_gap + lab_h + 26)
        lib.paste(cv, lib.metal_from_mask(rm, P.ramp, bevel=0.9), W / 2, cy, shadow=False)
        lib.paste(cv, a, W / 2 - D / 2, cy); lib.paste(cv, b, W / 2 + D / 2, cy)
        PU.sign_labels(cv, W, D, cy + sign_h / 2 + lab_gap, center.size[0], A, B, BR,
                       int(W * L.TYPE['label']['size']), L.TYPE['label']['tracking'])
        a_ = np.asarray(center)[..., 3].astype(np.float32)
        yy, xx = np.mgrid[0:a_.shape[0], 0:a_.shape[1]]
        gx = (xx * a_).sum() / a_.sum(); gy = (yy * a_).sum() / a_.sum()
        lib.paste(cv, center, W / 2 + (center.size[0] / 2 - gx) * 0.8, cy + (center.size[1] / 2 - gy) * 0.5)

    def save(cv, k):
        p = os.path.join(out_dir, f'{slug}-astroloveart-ig-{k}.jpg')
        cv.save(p, quality=95, subsampling=0)
        return p

    out = {}
    # ---------- 1 cover: the question
    cy, D = H * 0.47, 660
    cv = navy_glow(prof, 0.47)
    orbit(cv, cy, D, 150, Q, 285 * Q.size[1] / 997, 'q')
    lib.paste(cv, text(f'{A} & {B}, as one?', 0.084), W / 2, H * 0.13)
    lib.paste(cv, text('Zodiac art with your names & message', 0.056), W / 2, H * 0.81)
    sw_ = text('Swipe to reveal', 0.040); ar = arrow(130)
    gap = 22; tw = sw_.size[0] + gap + ar.size[0]; x0 = (W - tw) / 2; yb = H * 0.915
    lib.paste(cv, sw_, x0 + sw_.size[0] / 2, yb); lib.paste(cv, ar, x0 + sw_.size[0] + gap + ar.size[0] / 2, yb + 4, shadow=False)
    out['1'] = save(cv, 1)

    # ---------- 2 the answer
    cv = navy_glow(prof, 0.47)
    orbit(cv, cy, D, 120, P.layer(P.merged, only_label=False), 420, 'merged')
    lines(cv, [text('Two signs', 0.070), text('Your shared symbol', 0.070)], H * 0.125, 12)
    names = lib.scale_w(P.layer(P.names_row, only_label=False), round(W * 0.74))
    lib.paste(cv, names, W / 2, H * 0.795)
    lib.paste(cv, text('Your names, your message', 0.054), W / 2, H * 0.795 + names.size[1] / 2 + 72)
    out['2'] = save(cv, 2)

    poster = Image.open(poster_path).convert('RGB')
    # ---------- 3 wall scene, no text
    k = box['IG3']
    img = Image.open(os.path.join(AS, 'IG3_duvar_temiz.png')).convert('RGB')
    img.paste(poster.resize((k['pw'], k['ph']), Image.LANCZOS), (k['px'], k['py']))
    out['3'] = save(img, 3)

    # ---------- 4 close-up + navy text
    k = box['IG4']
    img = Image.open(os.path.join(AS, 'IG4_duvar_temiz.png')).convert('RGB')
    pw = k['x1'] - k['x0']; ph = k['yb']; s = pw / poster.size[0]
    top = poster.size[1] - ph / s
    img.paste(poster.crop((0, round(top), poster.size[0], poster.size[1])).resize((pw, ph), Image.LANCZOS), (k['x0'], 0))

    def flat(t, size, tracking=0.0):
        m = lib.text_mask(t, PU.FR, size, tracking)
        al = (np.clip(m, 0, 1) * 255).astype(np.uint8)
        rgb = np.zeros(al.shape + (3,), np.uint8); rgb[:] = NAVY
        return lib.trim(Image.fromarray(np.dstack([rgb, al]), 'RGBA'))

    items = [flat('Make it yours', int(W * 0.068)), flat('ASTROLOVEART', int(W * 0.032), 0.22), flat('On Etsy', int(W * 0.036))]
    gaps = [40, 14]
    tot = sum(i.size[1] for i in items) + sum(gaps)
    y = (k['yb'] + H) / 2 - tot / 2 + 6
    for i, it in enumerate(items):
        img.paste(it, (round(W / 2 - it.size[0] / 2), round(y)), it); y += it.size[1] + (gaps[i] if i < 2 else 0)
    out['4'] = save(img, 4)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--poster', required=True)
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--out', required=True)
    g = ap.parse_args()
    print(build(g.poster, g.a, g.b, g.out))
