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


def glyph_box(im, thr=32):
    a = np.asarray(im)[..., 3]
    ys, xs = np.nonzero(a > thr)
    return (int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)) if len(xs) else (0, 0)


KAYIT = []
_sign_pair = PU.sign_pair


def sign_pair_kayit(P, sign_h, *a, **k):
    """Wraps pin_uret.sign_pair: records the two sign images ig_uret actually pastes, per target height."""
    sa, sb, sw = _sign_pair(P, sign_h, *a, **k)
    KAYIT.append((sign_h, glyph_box(sa), glyph_box(sb)))
    return sa, sb, sw


PU.sign_pair = sign_pair_kayit


def qc_boy(rec):
    poster = rec['boy_sol'] / max(1, rec['boy_sag'])
    ok, sapma, gen = len(KAYIT) == 2, 0.0, 0.0
    for h, (wa, ha), (wb, hb) in KAYIT:
        d = abs((ha / max(1, hb)) / poster - 1)
        g = max(wa, wb) / h
        sapma, gen = max(sapma, d), max(gen, g)
        ok = ok and ha > 0 and hb > 0 and d <= 0.05 and max(wa, wb) <= 1.3 * h + 0.5
    rec['oran_sapma'] = round(sapma, 4)
    rec['max_gen_oran'] = round(gen, 3)
    rec['cikti_boy'] = ' '.join(f'{h}:{ha}/{hb}' for h, (_, ha), (_, hb) in KAYIT)
    rec['q_boy'] = ok


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
            KAYIT.clear()
            out = IG.build(poster, A, B, os.path.join(g.out, key))
            qc_boy(rec)
            olc = {k: Image.open(v).size for k, v in out.items()}
            rec['q_olcu'] = len(olc) == 4 and all(s == (IG.W, IG.H) for s in olc.values())
            rec['kapak'] = out['1']
            rec['hata'] = ''
        except Exception as e:
            rec.update(q_parca=False, q_boy=False, q_olcu=False,
                       hata=f'{type(e).__name__}: {e}', iz=traceback.format_exc()[-600:])
        rec['PASS'] = all(rec.get(k) for k in ('q_parca', 'q_boy', 'q_olcu'))
        rows.append(rec)
        el = time.time() - t0; eta = el / i * (n - i)
        print(f'[{i}/{n}] {100 * i / n:5.1f}% gecen {el / 60:5.1f} dk kalan {eta / 60:5.1f} dk  {key} '
              f'{"PASS" if rec["PASS"] else "FAIL"} {rec.get("hata", "")}', flush=True)
    keys = ['cift', 'a', 'b', 'poster_olcu', 'PASS', 'q_parca', 'q_boy', 'q_olcu', 'boy_sol', 'boy_sag', 'oran_sapma', 'max_gen_oran', 'cikti_boy', 'hata']
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
