#!/usr/bin/env python3
"""WP KAGIT TARAMASI (salt okur; Serdar onayi 2 Eki, TANI 2): 78 cift x 11x14, onayli WARM_PARCHMENT kaynak kagidi
vs VINTAGE_11x14 plate kagidi. Uretimle ayni fonksiyonlar (wp_katman: dizi, boyutla, murekkep_maskesi, dE) ve
wp_bakir.qc e_kagit tanimi: dE(plate, kaynak), murekkep maskesi (S - P, kenar=0) 17x17 genisletilmis disinda;
esik ort <= 0.5, p99 <= 3.0. Tarama dusuk cozunurlukte (1/2, INTER_AREA; genisletme 9x9); --tam ciftleri ayrica tam
cozunurlukte (uretimdeki 17x17) olculur (dogrulama). Kod / kilitli dosya / Drive kaynaklari degismez.
Girdi: <kok>/<CIFT>/WARM_PARCHMENT/11x14.jpg, --plate VINTAGE_11x14.png, --meta rclone lsjson -M ciktisi.
Cikti: <cik>/KAGIT_TARA.json + KAGIT_TARA.md."""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_katman as wk                                           # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ESIK_ORT, ESIK_P99 = 0.5, 3.0


def olc(S, P, genis):
    """e_kagit tanimi: dE(P, S), (murekkep_maskesi(S - P) genisletilmis) disinda."""
    ink = wk.murekkep_maskesi(S - P, kenar=0)
    haric = cv2.dilate(ink.astype(np.uint8), np.ones((genis, genis), np.uint8)).astype(bool)
    d = wk.dE(P, S)[~haric]
    ort, p99 = float(d.mean()), float(np.percentile(d, 99))
    return {'ort': round(ort, 3), 'p99': round(p99, 2), 'px': int(d.size),
            'tahmin': 'PASS' if ort <= ESIK_ORT and p99 <= ESIK_P99 else 'FAIL'}


def kucult(A, k=2):
    return cv2.resize(A, (A.shape[1] // k, A.shape[0] // k), interpolation=cv2.INTER_AREA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kok', required=True)
    ap.add_argument('--plate', required=True)
    ap.add_argument('--meta', default='')
    ap.add_argument('--tam', default='AQUARIUS_CANCER,PISCES_SCORPIO')
    ap.add_argument('--cik', required=True)
    a = ap.parse_args()
    t0 = time.time()
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    meta = {}
    if a.meta and Path(a.meta).exists():
        for m in json.loads(Path(a.meta).read_text()):
            meta[m['Path'].split('/')[0]] = m
    P_ham = wk.dizi(a.plate)
    onbellek = {}
    ciftler = sorted(p.name for p in Path(a.kok).iterdir() if (p / 'WARM_PARCHMENT' / '11x14.jpg').exists())
    tam = {c for c in a.tam.split(',') if c}
    satir = []
    for i, c in enumerate(ciftler, 1):
        S = wk.dizi(Path(a.kok) / c / 'WARM_PARCHMENT' / '11x14.jpg')
        wh = (S.shape[1], S.shape[0])
        if wh not in onbellek:
            onbellek[wh] = wk.boyutla(P_ham, wh)
        P = onbellek[wh]
        r = {'cift': c, 'kaynak_px': list(wh), **olc(kucult(S), kucult(P), 9)}
        if c in tam:
            r['tam'] = olc(S, P, 17)
        m = meta.get(c) or {}
        md = m.get('Metadata') or {}
        r['drive'] = {'mtime': m.get('ModTime'), 'btime': md.get('btime'), 'boyut': m.get('Size'),
                      'md5': (m.get('Hashes') or {}).get('md5'), 'aciklama': md.get('description'),
                      'sahip': md.get('owner'), 'son_duzenleyen': md.get('last-modifying-user')}
        satir.append(r)
        g = time.time() - t0
        print('KAGIT', json.dumps(r, ensure_ascii=False), flush=True)
        print(f'[{i}/{len(ciftler)}] {c} | gecen {g:.0f}s | kalan ~{g / i * (len(ciftler) - i):.0f}s | '
              f'%{100 * i // len(ciftler)}', flush=True)
        del S
    R = {'plate_px': [P_ham.shape[1], P_ham.shape[0]], 'esik': {'ort': ESIK_ORT, 'p99': ESIK_P99},
         'yontem': 'dE(plate, kaynak), murekkep_maskesi(S-P, kenar=0) disi; tarama 1/2 cozunurluk genisletme 9, tam 17',
         'satir': satir, 'sure_sn': round(time.time() - t0, 1)}
    (cik / 'KAGIT_TARA.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    md = ['| cift | dE ort | p99 | tahmin | Drive mtime | btime |', '|---|---|---|---|---|---|']
    for r in sorted(satir, key=lambda r: -r['ort']):
        md.append(f"| {r['cift']} | {r['ort']} | {r['p99']} | {r['tahmin']} | {r['drive']['mtime']} | "
                  f"{r['drive']['btime']} |")
    (cik / 'KAGIT_TARA.md').write_text('\n'.join(md) + '\n')
    print('OZET', json.dumps({'cift': len(satir), 'fail': sum(r['tahmin'] == 'FAIL' for r in satir),
                              'sure_sn': R['sure_sn']}), flush=True)


if __name__ == '__main__':
    main()
