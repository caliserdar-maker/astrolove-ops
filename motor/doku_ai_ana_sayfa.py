#!/usr/bin/env python3
"""DOKU_AI ANA SEMBOL deneme sayfasi (Serdar 4 Eki, ASAMA 2): ana sembol Canva'da yeniden dokulanir, sekil DEGISMEZ.

Sayfa: siyah zemin, duz beyaz maske = ana sembol asset alfasi (24x36 poster olceginde), 2x2 izgara (hucre payi PAY px).
Olcek: 16x20 orijinal posterden NCC eslesme olcegi (ana16.json) x 24x36 / 16x20 (SCORPIO_VIRGO sabiti 0.500657 /
16x20 olcegi). Istisna: NCC < NCC_MIN (asset cizimi posterden farkli; AQUARIUS_LEO / AQUARIUS_TAURUS gibi) -> FAIL,
sekil posterden alinmali (bu sayfa onu yapmaz, durur).
Kose referansi: ONAYLI Canva dokusu, cila sonrasi kucuk semboller (CANCER: KUCUK_1A_P, LIBRA: KUCUK_2 v2), siyah
zemin ustunde, ust seritte; ana sembollerle cakisma kontrol edilir.

Kullanim: doku_ai_ana_sayfa.py --main-dir DIR --ana16 ana16.json --set S17 --sayfa-json DIR --cikti DIR CANCER_LIBRA ...
"""
import argparse, hashlib, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import doku_ai_sayfa as das                                          # noqa: E402

Image.MAX_IMAGE_PIXELS = None
PAY = 60
NCC_MIN = 0.95
SV_24 = 0.500657280135945                                            # SCORPIO_VIRGO_MB_24x36 buyuk_sembol olcek
REF = [('CANCER', 'KUCUK_1A_P'), ('LIBRA', 'KUCUK_2')]


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def referans_kes(S, J, oge, sayfa):
    """cila sonrasi kucuk sembol: doku x alfa (siyah zemin), oge kutusu."""
    z = np.load(Path(S) / f'{sayfa}.npz')
    j = json.loads((Path(J) / f'DOKU_AI_{sayfa}.json').read_text())
    x0, y0, x1, y1 = [o['kutu'] for o in j['ogeler'] if o['oge'] == oge][0]
    return z['t1'][y0:y1, x0:x1].astype(np.float32) * (z['O'][y0:y1, x0:x1, None].astype(np.float32) / 255)


def main():
    ap = argparse.ArgumentParser()
    for k in ('main-dir', 'ana16', 'set', 'sayfa-json', 'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--ad', default='ANA_DENEME')
    ap.add_argument('ciftler', nargs='+')
    a = ap.parse_args()
    C = Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    A16 = json.loads(Path(a.ana16).read_text())['p']
    k24 = SV_24 / A16['SCORPIO_VIRGO']['tm']['olcek16']
    ms = []
    for c in a.ciftler:
        tm = A16[c]['tm']
        if tm['ncc'] < NCC_MIN:
            sys.exit(f'FAIL: {c} asset posterle eslesmiyor (NCC {tm["ncc"]}); sekil posterden alinmali')
        f = Path(a.main_dir) / f'main_{c.lower()}_gold.png'
        al = np.asarray(Image.open(f).convert('RGBA'))[..., 3]
        ys, xs = np.nonzero(al > 0)
        kk = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        s = tm['olcek16'] * k24
        al = al[kk[1]:kk[3], kk[0]:kk[2]].astype(np.float32)
        m = cv2.resize(al, (round(al.shape[1] * s), round(al.shape[0] * s)), interpolation=cv2.INTER_AREA)
        ms.append((c, m, {'kaynak': f.name, 'sha256': sha(f), 'kaynak_kirp': kk, 'olcek': round(s, 5),
                          'olcek_kaynagi': f'16x20 orijinal {c}.jpg NCC {tm["ncc"]} olcek {tm["olcek16"]} x {k24:.5f} '
                                           f'(SCORPIO_VIRGO 24x36 sabiti {SV_24:.5f} / 16x20 {A16["SCORPIO_VIRGO"]["tm"]["olcek16"]})',
                          'sekil': 'asset alfasi (posterle NCC eslesmesi, istisna degil)'}))
    # ust serit: referans (CANCER + LIBRA, onayli Canva dokusu)
    rf = [(o, referans_kes(a.set, a.sayfa_json, o, sf), sf) for o, sf in REF]
    rh = max(r.shape[0] for _, r, _ in rf) + 2 * PAY
    rw = sum(r.shape[1] for _, r, _ in rf) + 3 * PAY
    cw = max(m.shape[1] for _, m, _ in ms) + 2 * PAY
    ch = max(m.shape[0] for _, m, _ in ms) + 2 * PAY
    W, H = max(2 * cw, rw), rh + 2 * ch
    das.oran_kapisi(a.ad, W, H)
    P = np.zeros((H, W, 3), np.float32)
    x = PAY
    rkay = []
    for o, r, sf in rf:
        P[PAY:PAY + r.shape[0], x:x + r.shape[1]] = r
        rkay.append({'oge': o, 'kutu': [x, PAY, x + r.shape[1], PAY + r.shape[0]], 'kaynak': f'{sf}.npz (cila sonrasi t1 x O)'})
        x += r.shape[1] + PAY
    kay = []
    x_off = (W - 2 * cw) // 2
    for i, (c, m, bil) in enumerate(ms):
        gx, gy = i % 2, i // 2
        hx0, hy0 = x_off + gx * cw, rh + gy * ch
        x0, y0 = hx0 + (cw - m.shape[1]) // 2, hy0 + (ch - m.shape[0]) // 2
        P[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] = np.maximum(P[y0:y0 + m.shape[0], x0:x0 + m.shape[1]], m[..., None])
        kay.append({'oge': c, 'hucre': [hx0, hy0, hx0 + cw, hy0 + ch], 'kutu': [x0, y0, x0 + m.shape[1], y0 + m.shape[0]],
                    'pay_min_px': int(min(x0 - hx0, y0 - hy0, hx0 + cw - x0 - m.shape[1], hy0 + ch - y0 - m.shape[0]))} | bil)
    # kapilar: hucre payi, referans - sembol cakismasi
    if min(o['pay_min_px'] for o in kay) < 30:
        sys.exit('FAIL: hucre payi < 30 px')
    for r in rkay:
        for o in kay:
            p, q = r['kutu'], o['kutu']
            if not (p[2] <= q[0] or q[2] <= p[0] or p[3] <= q[1] or q[3] <= p[1]):
                sys.exit(f'FAIL: referans {r["oge"]} {o["oge"]} ile cakisiyor')
    f = C / f'DOKU_AI_{a.ad}.png'
    Image.fromarray(np.clip(np.round(P), 0, 255).astype(np.uint8)).save(f, optimize=True)
    j = {'tur': 'ana_sembol', 'boyut': [W, H], 'oran': das.oran_kapisi(a.ad, W, H), 'pay_px': PAY,
         'referans_kutu': [0, 0, rw, rh],
         'referans': 'ONAYLI Canva dokusu, cila sonrasi: CANCER (KUCUK_1A_P), LIBRA (KUCUK_2 v2); siyah zemin',
         'referans_ogeler': rkay, 'ogeler': kay, 'olcek': '24x36 baski, 300 dpi, 1:1',
         'dosya': f.name, 'sha256': sha(f)}
    (C / f'DOKU_AI_{a.ad}.json').write_text(json.dumps(j, ensure_ascii=False, indent=1))
    print(json.dumps({'sayfa': a.ad, 'boyut': [W, H], 'oran': j['oran'],
                      'ogeler': [[o['oge'], o['olcek'], o['kutu'], o['pay_min_px']] for o in kay]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
