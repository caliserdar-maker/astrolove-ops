"""Batch run of ig_uret.build for many pairs + PASS/FAIL QC + cover contact sheet.

Usage:
  python3 ig_toplu.py --posters <dir with PAIR.jpg 2000x3000> --out <dir> [--pairs CAPRICORN_SAGITTARIUS,...] [--kontak]
Pair key is alphabetic (CLAUDE.md): first sign = --a (left small sign), second = --b (right).
Each pair is written to its own folder <out>/<PAIR>/ (4 slides).
QC per pair (all must hold):
  q_parca : PosterR found the parts (merged, left sign, right sign, names), each non-empty, no exception
  q_boy   : in slides 1 and 2 the two small signs keep the poster's height relation
            (output height ratio / poster height ratio within 1 +- 0.05) and no sign is wider than 1.3 x target height.
            Measured on the actual sign images ig_uret pastes (alpha bbox), poster heights from PosterR.
  q_bosluk: in slides 1 and 2 the centre symbol leaves >= 30 px free on both sides to the small signs
            (horizontal gap between the pasted alpha bboxes on the slide).
  q_olcu  : 4 files, each 1080x1350
Writes QC.csv, QC.json, FAIL.txt; with --kontak also KONTAK_IG1.jpg (all cover slides).
"""
import argparse, csv, json, os, sys, time, traceback
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'pin_v6'))
import ig_uret as IG
import pin_uret as PU
from pin_toplu import contact


def qc_poster(P):
    parts = [P.merged, P.sign_a, P.sign_b, P.names_row]
    return {'q_parca': all(c is not None and c[3] > 0 and c[4] > 0 for c in parts),
            'boy_sol': int(P.sign_a[4]), 'boy_sag': int(P.sign_b[4])}


def glyph_bbox(im, thr=32):
    a = np.asarray(im)[..., 3]
    ys, xs = np.nonzero(a > thr)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1) if len(xs) else None


# Instrumentation: record the sign / centre images ig_uret actually pastes and where (no change to the output).
SIGNS, CENTERS, PASTES = [], [], []
_sign_pair, _fit_center, _paste = PU.sign_pair, PU.fit_center, IG.lib.paste


def sign_pair_kayit(P, sign_h, *a, **k):
    res = _sign_pair(P, sign_h, *a, **k)
    SIGNS.append((sign_h, res[0], res[1]))
    return res


def fit_center_kayit(*a, **k):
    c = _fit_center(*a, **k)
    CENTERS.append(c)
    return c


def paste_kayit(canvas, layer, *a, **k):
    r = _paste(canvas, layer, *a, **k)
    PASTES.append((layer, r[0], r[1]))
    return r


PU.sign_pair, PU.fit_center, IG.lib.paste = sign_pair_kayit, fit_center_kayit, paste_kayit


def on_slide(layer):
    """alpha bbox of a pasted layer in slide coordinates (last paste of that exact object)."""
    for lay, x, y in reversed(PASTES):
        if lay is layer:
            b = glyph_bbox(layer)
            return None if b is None else (x + b[0], y + b[1], x + b[2], y + b[3])
    return None


def qc_boy(rec):
    poster = rec['boy_sol'] / max(1, rec['boy_sag'])
    ok_b, ok_g, sapma, gen, boy, bos = len(SIGNS) == 2, len(CENTERS) == 2, 0.0, 0.0, [], []
    for i, (h, sa, sb) in enumerate(SIGNS):
        A, B = glyph_bbox(sa), glyph_bbox(sb)
        wa, ha = (A[2] - A[0], A[3] - A[1]) if A else (0, 0)
        wb, hb = (B[2] - B[0], B[3] - B[1]) if B else (0, 0)
        d = abs((ha / max(1, hb)) / poster - 1)
        sapma, gen = max(sapma, d), max(gen, max(wa, wb) / h)
        ok_b = ok_b and ha > 0 and hb > 0 and d <= 0.05 and max(wa, wb) <= 1.3 * h + 0.5
        boy.append(f'{h}:{ha}/{hb}')
        a_, b_, c_ = on_slide(sa), on_slide(sb), on_slide(CENTERS[i]) if i < len(CENTERS) else None
        if None in (a_, b_, c_):
            ok_g = False; bos.append(f'{h}:?')
            continue
        gl, gr = c_[0] - a_[2], b_[0] - c_[2]
        ok_g = ok_g and gl >= 30 and gr >= 30
        bos.append(f'{h}:{gl}/{gr}')
    rec['oran_sapma'] = round(sapma, 4)
    rec['max_gen_oran'] = round(gen, 3)
    rec['cikti_boy'] = ' '.join(boy)
    rec['bosluk_sol_sag'] = ' '.join(bos)
    rec['q_boy'], rec['q_bosluk'] = ok_b, ok_g


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
        rec = {'cift': key, 'a': A, 'b': B, 'kapak': ''}
        try:
            poster = os.path.join(g.posters, key + '.jpg')
            sz = Image.open(poster).size
            rec['poster_olcu'] = f'{sz[0]}x{sz[1]}'
            rec.update(qc_poster(PU.PosterR(poster)))
            SIGNS.clear(); CENTERS.clear(); PASTES.clear()
            out = IG.build(poster, A, B, os.path.join(g.out, key))
            qc_boy(rec)
            olc = {k: Image.open(v).size for k, v in out.items()}
            rec['q_olcu'] = len(olc) == 4 and all(s == (IG.W, IG.H) for s in olc.values())
            rec['kapak'] = out['1']
            rec['hata'] = ''
        except Exception as e:
            rec.update(q_parca=False, q_boy=False, q_bosluk=False, q_olcu=False,
                       hata=f'{type(e).__name__}: {e}', iz=traceback.format_exc()[-600:])
        rec['PASS'] = all(rec.get(k) for k in ('q_parca', 'q_boy', 'q_bosluk', 'q_olcu'))
        rows.append(rec)
        el = time.time() - t0; eta = el / i * (n - i)
        print(f'[{i}/{n}] {100 * i / n:5.1f}% gecen {el / 60:5.1f} dk kalan {eta / 60:5.1f} dk  {key} '
              f'{"PASS" if rec["PASS"] else "FAIL"} {rec.get("hata", "")}', flush=True)
    keys = ['cift', 'a', 'b', 'poster_olcu', 'PASS', 'q_parca', 'q_boy', 'q_bosluk', 'q_olcu', 'boy_sol', 'boy_sag', 'oran_sapma', 'max_gen_oran', 'cikti_boy', 'bosluk_sol_sag', 'hata']
    with open(os.path.join(g.out, 'QC.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    json.dump(rows, open(os.path.join(g.out, 'QC.json'), 'w'), indent=1, default=str)
    fails = [r['cift'] for r in rows if not r['PASS']]
    open(os.path.join(g.out, 'FAIL.txt'), 'w').write('\n'.join(fails) + ('\n' if fails else ''))
    if g.kontak:
        ok = [r for r in rows if r['kapak']]
        contact([(r['kapak'], r['cift'] + ('' if r['PASS'] else '  FAIL')) for r in ok],
                270, 13, os.path.join(g.out, 'KONTAK_IG1.jpg'), f'IG 1 kapak x {len(ok)}')
    print(f'OZET PASS {n - len(fails)}/{n} FAIL {len(fails)}: {" ".join(fails) or "yok"}')
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
