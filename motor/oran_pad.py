#!/usr/bin/env python3
"""Canva oran guvenligi (Serdar 4 Eki): Canva en/boy oranini 3:1 / 1:3 ile sinirliyor, otesini sikistirip yeniden
ciziyor. Mevcut girdi sayfasi yalniz SIYAH BOSLUK eklenerek ORAN_MAX:1 (dikeyde 1:ORAN_MAX) icine alinir.
Ogeler ve olcek piksel piksel korunur, ogeler yeni sayfada ortalanir, kose referansi (referans_kutu) yerinde kalir.
Cikti: DOKU_AI_<AD>_P.png + .json (oge kutulari, halka.sayfa_kaydirma yeni konuma gore; oran_pad.kaydirma).

Kullanim: oran_pad.py --girdi GIRDI_DIR --cikti DIR KUCUK_1A KUCUK_1B CEMBER_UST ...
"""
import argparse, json, math, sys
from pathlib import Path

import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import doku_ai_sayfa as das                                          # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def pad(P, j, ad):
    H, W = P.shape[:2]
    x0, y0, x1, y1 = j['referans_kutu']
    ic = P.copy(); ic[y0:y1, x0:x1] = 0                               # ogeler (referans haric)
    W2, H2 = W, H
    if W / H > das.ORAN_MAX:
        H2 = math.ceil(W / das.ORAN_MAX)
    elif W / H < das.ORAN_MIN:
        W2 = math.ceil(H * das.ORAN_MIN)
    dx, dy = (W2 - W) // 2, (H2 - H) // 2
    N = np.zeros((H2, W2, 3), P.dtype)
    N[dy:dy + H, dx:dx + W] = ic
    if (N[y0:y1, x0:x1] > 0).any():
        raise SystemExit(f'FAIL: {ad} ortalanan ogeler kose referansina degiyor')
    N[y0:y1, x0:x1] = P[y0:y1, x0:x1]
    j2 = json.loads(json.dumps(j))
    j2['boyut'] = [W2, H2]
    for o in j2.get('ogeler', []):
        for k in ('kutu', 'hucre'):
            if k in o:
                o[k] = [o[k][0] + dx, o[k][1] + dy, o[k][2] + dx, o[k][3] + dy]
    if 'halka' in j2:                                                 # halka = sayfa + kaydirma
        sx, sy = j2['halka']['sayfa_kaydirma']; j2['halka']['sayfa_kaydirma'] = [sx - dx, sy - dy]
    j2['oran_pad'] = {'kaynak': f'DOKU_AI_{ad}.png', 'kaynak_boyut': [W, H], 'kaydirma': [dx, dy],
                      'oran_once': round(W / H, 4), 'oran_sonra': das.oran_kapisi(ad + '_P', W2, H2),
                      'not': 'yalniz siyah bosluk; ogeler ve olcek ayni, kose referansi yerinde'}
    return N, j2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--girdi', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('sayfalar', nargs='+')
    a = ap.parse_args()
    G, C = Path(a.girdi), Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    ozet = []
    for ad in a.sayfalar:
        P = np.asarray(Image.open(G / f'DOKU_AI_{ad}.png').convert('RGB'))
        j = json.loads((G / f'DOKU_AI_{ad}.json').read_text())
        N, j2 = pad(P, j, ad)
        f = C / f'DOKU_AI_{ad}_P.png'
        Image.fromarray(N).save(f, optimize=True)
        j2 |= {'dosya': f.name, 'sha256': das.sha(f.read_bytes())}
        (C / f'DOKU_AI_{ad}_P.json').write_text(json.dumps(j2, ensure_ascii=False, indent=1))
        ozet.append({'sayfa': ad + '_P', 'boyut': j2['boyut'], 'oran': j2['oran_pad']['oran_sonra'],
                     'once': [*j2['oran_pad']['kaynak_boyut'], j2['oran_pad']['oran_once']]})
    print(json.dumps(ozet, ensure_ascii=False))


if __name__ == '__main__':
    main()
