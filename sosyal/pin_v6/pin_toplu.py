"""Batch run of pin_uret.build for many pairs + PASS/FAIL QC + contact sheets.

Usage:
  python3 pin_toplu.py --posters <dir with PAIR.jpg 2000x3000> --out <dir> [--pairs CAPRICORN_SAGITTARIUS,...] [--kontak]
Pair key is alphabetic (CLAUDE.md): first sign = --a (left small sign), second = --b (right).
QC per pair (all must hold):
  q_parca : 5 parts found (merged, left sign, right sign, names, message), each non-empty
  q_boy   : left / right small sign heights within 25% of each other (max/min <= 1.25)
  q_halka : every merged-symbol pixel lies inside the ring's inner radius
  q_olcu  : p1, p2, p3 are 1000x1500
Writes QC.csv, QC.json, FAIL.txt; with --kontak also KONTAK_P2.jpg and KONTAK_PARCA.jpg.
"""
import argparse, csv, json, os, sys, time, traceback
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pin_uret as PU


def qc_poster(P):
    r = {}
    parts = [P.merged, P.sign_a, P.sign_b, P.names_row, P.msg_row]
    r['q_parca'] = all(c is not None and c[3] > 0 and c[4] > 0 for c in parts)
    ha, hb = int(P.sign_a[4]), int(P.sign_b[4])
    r['boy_sol'], r['boy_sag'] = ha, hb
    r['boy_oran'] = round(max(ha, hb) / max(1, min(ha, hb)), 3)
    r['q_boy'] = r['boy_oran'] <= 1.25
    # ring = open arc (gap at the bottom): centre from a least-squares circle fit, inner radius = 1st pct distance
    comps = sorted(P.comps, key=lambda c: -c[5])
    ring_ids = [c[0] for c in comps[:6] if c[5] / float(c[3] * c[4]) < 0.03 and c[3] > 0.6 * P.w]
    ry, rx = np.nonzero(np.isin(P.lab, ring_ids))
    M = np.c_[2 * rx, 2 * ry, np.ones(len(rx))].astype(np.float64)
    cx, cy, _ = np.linalg.lstsq(M, (rx.astype(np.float64) ** 2 + ry.astype(np.float64) ** 2), rcond=None)[0]
    r_in = float(np.percentile(np.hypot(rx - cx, ry - cy), 1))
    my, mx = np.nonzero(np.isin(P.lab, [c[0] for c in P.merged_parts]))
    r_max = float(np.hypot(mx - cx, my - cy).max())
    r['halka_ic_r'], r['sembol_max_r'] = round(r_in, 1), round(r_max, 1)
    r['q_halka'] = r_max < r_in
    r['merged_parca_sayisi'] = len(P.merged_parts)
    return r


def label_font(size):
    try:
        return ImageFont.truetype(PU.FR, size)
    except Exception:
        return ImageFont.load_default()


def contact(paths_labels, tw, cols, out, title):
    ims = []
    for p, lab in paths_labels:
        im = Image.open(p).convert('RGB'); im.thumbnail((tw, 10 ** 6)); ims.append((im, lab))
    th = max(i.size[1] for i, _ in ims); lh = 34
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (tw + 10) + 10, rows * (th + lh + 10) + 70), (245, 243, 238))
    d = ImageDraw.Draw(sheet); f = label_font(24)
    d.text((14, 18), title, fill=(18, 24, 52), font=label_font(32))
    for k, (im, lab) in enumerate(ims):
        x = 10 + (k % cols) * (tw + 10); y = 70 + (k // cols) * (th + lh + 10)
        d.text((x, y + 4), lab, fill=(18, 24, 52), font=f)
        sheet.paste(im, (x, y + lh))
    sheet.save(out, quality=88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--posters', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--pairs', default='')
    ap.add_argument('--kontak', action='store_true')
    g = ap.parse_args()
    os.makedirs(g.out, exist_ok=True)
    pairs = [p.strip() for p in g.pairs.split(',') if p.strip()] or \
        sorted(os.path.splitext(f)[0] for f in os.listdir(g.posters) if f.endswith('.jpg'))
    rows, t0, n = [], time.time(), len(pairs)
    for i, key in enumerate(pairs, 1):
        A, B = [s.capitalize() for s in key.split('_')]
        rec = {'cift': key, 'a': A, 'b': B}
        try:
            poster = os.path.join(g.posters, key + '.jpg')
            sz = Image.open(poster).size
            rec['poster_olcu'] = f'{sz[0]}x{sz[1]}'
            out = PU.build(poster, A, B, g.out)
            rec.update(qc_poster(PU.PosterR(poster)))
            olc = {k: Image.open(v).size for k, v in out.items()}
            rec['q_olcu'] = all(s == (1000, 1500) for s in olc.values()) and len(olc) == 3
            rec['hata'] = ''
        except Exception as e:
            rec.update(q_parca=False, q_boy=False, q_halka=False, q_olcu=False,
                       hata=f'{type(e).__name__}: {e}', iz=traceback.format_exc()[-600:])
        rec['PASS'] = all(rec.get(k) for k in ('q_parca', 'q_boy', 'q_halka', 'q_olcu'))
        rows.append(rec)
        el = time.time() - t0; eta = el / i * (n - i)
        print(f'[{i}/{n}] {100 * i / n:5.1f}% gecen {el / 60:5.1f} dk kalan {eta / 60:5.1f} dk  {key} '
              f'{"PASS" if rec["PASS"] else "FAIL"} {rec.get("hata", "")}', flush=True)
    keys = ['cift', 'a', 'b', 'poster_olcu', 'PASS', 'q_parca', 'q_boy', 'q_halka', 'q_olcu', 'boy_sol', 'boy_sag',
            'boy_oran', 'halka_ic_r', 'sembol_max_r', 'merged_parca_sayisi', 'hata']
    with open(os.path.join(g.out, 'QC.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    json.dump(rows, open(os.path.join(g.out, 'QC.json'), 'w'), indent=1, default=str)
    fails = [r['cift'] for r in rows if not r['PASS']]
    open(os.path.join(g.out, 'FAIL.txt'), 'w').write('\n'.join(fails) + ('\n' if fails else ''))
    if g.kontak:
        ok = [r for r in rows if not r.get('hata')]
        sl = lambda r: f"{r['a'].lower()}-and-{r['b'].lower()}"
        contact([(os.path.join(g.out, f'{sl(r)}-zodiac-wall-art-astroloveart-p2.jpg'), r['cift']) for r in ok],
                240, 13, os.path.join(g.out, 'KONTAK_P2.jpg'), f'P2 x {len(ok)}')
        contact([(os.path.join(g.out, f'{sl(r)}-parcalar.jpg'), r['cift'] + ('' if r['PASS'] else '  FAIL')) for r in ok],
                600, 6, os.path.join(g.out, 'KONTAK_PARCA.jpg'), f'Parcalar x {len(ok)}')
    print(f'OZET PASS {n - len(fails)}/{n} FAIL {len(fails)}: {" ".join(fails) or "yok"}')
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
