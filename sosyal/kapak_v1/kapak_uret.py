"""AstroLoveArt video cover (Reel / FB Reel / TikTok / YouTube Shorts), 1080x1920 (9:16), one zodiac pair.

Approved design (Serdar, 13 Oct 2026, Gemini & Leo, onayli/kapak_gemini_leo.jpg):
 - navy glow background (same as IG slides)
 - large merged symbol from the poster, upper middle
 - under it: sign A (left) with its name below, the AstroLoveArt infinity logo in the middle,
   sign B (right) with its name below
 - no other text; everything sits inside the centre 3:4 area that the Instagram profile grid shows
Poster pixels are only cut, scaled and moved. The logo is cut once from the approved Gemini & Leo
poster's names row (assets/logo_sonsuz.png), so it is identical on all 78 covers.

Usage:
  python3 kapak_uret.py --poster AstroLoveArt_Gemini_Leo_2000.jpg --a Gemini --b Leo --out cikti/
  --a = first sign of the pair key (LEFT small sign on the poster), --b = second (RIGHT).
Writes {a}-and-{b}-astroloveart-kapak.jpg and prints a QC dict (PASS/FAIL).
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'ig_v6'))
import ig_uret as IGU            # navy_glow; also loads pin_v6 (PosterR, sign_pair, fit, lib, layouts)
PU, lib, L = IGU.PU, IGU.lib, IGU.L

W, H = 1080, 1920
LOGO = os.path.join(HERE, 'assets', 'logo_sonsuz.png')
GRID_TOP, GRID_BOT = (H - 1440) // 2, (H - 1440) // 2 + 1440   # centre 3:4 band shown in the profile grid
MARGIN = 30


def build(poster_path, A, B, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    IGU.W, IGU.H = W, H                      # navy_glow reads the module's canvas size
    P = PU.PosterR(poster_path)
    BR = L.bright_ramp(P)
    cv = IGU.navy_glow(P.bg_profile(), 0.44)
    rects = {}

    def put(name, im, cx, cy, shadow=True):
        lib.paste(cv, im, cx, cy, shadow=shadow)
        a = np.asarray(im)[..., 3] > 20
        ys, xs = np.where(a)
        x0 = round(cx - im.size[0] / 2); y0 = round(cy - im.size[1] / 2)
        rects[name] = (x0 + xs.min(), y0 + ys.min(), x0 + xs.max(), y0 + ys.max())

    # merged symbol
    merged = lib.scale_h(P.layer(P.merged, only_label=False), 660)
    if merged.size[0] > W * 0.78:
        merged = lib.scale_w(merged, round(W * 0.78))
    a_ = np.asarray(merged)[..., 3].astype(np.float32)
    yy, xx = np.mgrid[0:a_.shape[0], 0:a_.shape[1]]
    cy = H * 0.40
    put('birlesik', merged, W / 2 + (merged.size[0] / 2 - (xx * a_).sum() / a_.sum()) * 0.8, cy)

    # signs with their names below, logo between the signs
    sa, sb, sw, r = PU.sign_pair(P, 160)
    ls = 86
    mk = lambda t, s: lib.metal_text(t.upper(), s, BR, tracking=0.18, bevel=1.0)
    la, lb = mk(A, ls), mk(B, ls)
    while max(la.size[0], lb.size[0]) > W * 0.37:
        ls -= 2
        la, lb = mk(A, ls), mk(B, ls)
    ys = cy + merged.size[1] / 2 + 150
    yl = ys + 124 + max(la.size[1], lb.size[1]) / 2
    off = max(260, max(la.size[0], lb.size[0]) / 2 + 60)
    put('burc_a', sa, W / 2 - off, ys); put('ad_a', la, W / 2 - off, yl, shadow=False)
    put('burc_b', sb, W / 2 + off, ys); put('ad_b', lb, W / 2 + off, yl, shadow=False)
    put('logo', lib.scale_w(Image.open(LOGO).convert('RGBA'), 150), W / 2, ys)

    slug = f'{A.lower()}-and-{B.lower()}'
    path = os.path.join(out_dir, f'{slug}-astroloveart-kapak.jpg')
    cv.save(path, quality=95, subsampling=0)

    # QC: everything inside the 3:4 grid band and the frame, no element touches another
    def gap(p, q):
        dx = max(q[0] - p[2], p[0] - q[2]); dy = max(q[1] - p[3], p[1] - q[3])
        return max(dx, dy)
    hata = []
    for k, (x0, y0, x1, y1) in rects.items():
        if x0 < MARGIN or x1 > W - MARGIN or y0 < GRID_TOP + MARGIN or y1 > GRID_BOT - MARGIN:
            hata.append(f'{k} izgara alani disinda {rects[k]}')
    names = list(rects)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            g = gap(rects[names[i]], rects[names[j]])
            if g < 24:
                hata.append(f'{names[i]}-{names[j]} bosluk {g}px < 24')
    qc = {'cift': f'{A.upper()}_{B.upper()}', 'dosya': os.path.basename(path), 'boyut': list(cv.size),
          'ad_punto': ls, 'kutular': {k: [int(v) for v in r_] for k, r_ in rects.items()},
          'sonuc': 'PASS' if not hata and cv.size == (W, H) else 'FAIL', 'hata': hata}
    return path, qc


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--poster', required=True)
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--out', required=True)
    g = ap.parse_args()
    p, qc = build(g.poster, g.a, g.b, g.out)
    print(json.dumps(qc, ensure_ascii=False))
    sys.exit(0 if qc['sonuc'] == 'PASS' else 1)
