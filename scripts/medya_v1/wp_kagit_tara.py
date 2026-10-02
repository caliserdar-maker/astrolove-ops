#!/usr/bin/env python3
"""WP KAGIT TARAMASI (salt okur; Serdar onayi 2 Eki, TANI 2): 78 cift x 11x14, onayli WARM_PARCHMENT kaynak kagidi
vs VINTAGE_<boy> plate kagidi (TANI 3: --boy ile 16x20 / 18x24 / 24x36 / A2). Uretimle ayni fonksiyonlar (wp_katman: dizi, boyutla, murekkep_maskesi, dE) ve
wp_bakir.qc e_kagit tanimi: dE(plate, kaynak), murekkep maskesi (S - P, kenar=0) 17x17 genisletilmis disinda;
esik ort <= 0.5, p99 <= 3.0. Tarama dusuk cozunurlukte (1/2, INTER_AREA; genisletme 9x9); --tam ciftleri ayrica tam
cozunurlukte (uretimdeki 17x17) olculur (dogrulama). Kod / kilitli dosya / Drive kaynaklari degismez.
Girdi: <kok>/<CIFT>/WARM_PARCHMENT/<boy>.jpg, --plate VINTAGE_<boy>.png, --meta rclone lsjson -M ciktisi.
Cikti: <cik>/KAGIT_TARA_<boy>.json + .md; SINIR satiri (alfabetik = sayfa sirasinda PASS/FAIL gecisleri).
--kesit: 1:1 yalniz kagit kesiti (murekkepsiz ortak pencere), ayni bolge, verilen dosyalardan."""
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


def kesit(a):
    """1:1 yalniz kagit kesiti: --kesit etiket=yol ...; tum goruntuler ilk goruntunun boyutuna wk.boyutla ile getirilir
    (uretimdeki plate boyutlama). Pencere: ilk iki goruntunun ikisinde de murekkep maskesi (birbirine ve plate'e gore,
    15 px genisletilmis) bos olan, aralarindaki dE ortancasi en yuksek pencere (fark en gorunur yer)."""
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    ogeler = [x.split('=', 1) for x in a.kesit]
    A = [wk.dizi(y) for _, y in ogeler]
    wh = (A[0].shape[1], A[0].shape[0])
    A = [wk.boyutla(x, wh) for x in A]
    P = wk.dizi(a.plate); P = wk.boyutla(P, wh)
    ink = np.zeros(A[0].shape[:2], bool)
    for x in A:
        ink |= wk.murekkep_maskesi(x - P, kenar=0)
    ink = cv2.dilate(ink.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
    d = wk.dE(A[0], A[1])
    H, W = ink.shape
    print('KESIT_MUREKKEP_ORANI', round(float(ink.mean()), 3), flush=True)
    en = None
    for n in sorted({a.kesit_px, 300, 200, 128}, reverse=True):   # tum alan (kenar paylari dahil); bos yoksa kucuk pencere
        if n > a.kesit_px:
            continue
        ii = cv2.integral(ink.astype(np.uint8))
        for y in range(0, H - n + 1, max(n // 4, 1)):
            for x in range(0, W - n + 1, max(n // 4, 1)):
                if ii[y + n, x + n] - ii[y, x + n] - ii[y + n, x] + ii[y, x]:
                    continue
                v = float(np.median(d[y:y + n, x:x + n]))
                if en is None or v > en[0]:
                    en = (v, x, y)
        if en is not None:
            break
    if en is None:
        raise SystemExit('murekkepsiz pencere bulunamadi')
    _, x0, y0 = en
    sl = (slice(y0, y0 + n), slice(x0, x0 + n))
    parcalar = [(e, x) for (e, _), x in zip(ogeler, A)] + [('VINTAGE_plate', P)]
    sonuc = {'pencere': {'x': [x0, x0 + n], 'y': [y0, y0 + n], 'boyut': list(wh)}, 'kesitler': []}
    seri = []
    for e, x in parcalar:
        k = np.clip(x[sl], 0, 255).astype(np.uint8)
        Image.fromarray(k).save(cik / f'KESIT_{e}_x{x0}_y{y0}_1e1.png')
        dd = wk.dE(x[sl], P[sl])
        sonuc['kesitler'].append({'etiket': e, 'ort_rgb': [round(float(v), 1) for v in x[sl].reshape(-1, 3).mean(0)],
                                  'plate_dE_ort': round(float(dd.mean()), 2)})
        seri += [k, np.full((n, 8, 3), 255, np.uint8)]
    Image.fromarray(np.concatenate(seri[:-1], 1)).save(cik / f'KESIT_YANYANA_x{x0}_y{y0}_1e1.png')
    (cik / 'KESIT.json').write_text(json.dumps(sonuc, indent=1))
    print('KESIT', json.dumps(sonuc), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kok', required=True)
    ap.add_argument('--plate', required=True)
    ap.add_argument('--meta', default='')
    ap.add_argument('--tam', default='AQUARIUS_CANCER,PISCES_SCORPIO')
    ap.add_argument('--cik', required=True)
    ap.add_argument('--boy', default='11x14')
    ap.add_argument('--kesit', nargs='*', default=None, help='etiket=dosya ... (ilk ikisi pencere secimine girer)')
    ap.add_argument('--kesit-px', type=int, default=400)
    a = ap.parse_args()
    if a.kesit is not None:
        return kesit(a)
    t0 = time.time()
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    meta = {}
    if a.meta and Path(a.meta).exists():
        for m in json.loads(Path(a.meta).read_text()):
            meta[m['Path'].split('/')[0]] = m
    P_ham = wk.dizi(a.plate)
    onbellek = {}
    ciftler = sorted(p.name for p in Path(a.kok).iterdir() if (p / 'WARM_PARCHMENT' / f'{a.boy}.jpg').exists())
    tam = {c for c in a.tam.split(',') if c}
    satir = []
    for i, c in enumerate(ciftler, 1):
        S = wk.dizi(Path(a.kok) / c / 'WARM_PARCHMENT' / f'{a.boy}.jpg')
        wh = (S.shape[1], S.shape[0])
        if wh not in onbellek:
            onbellek[wh] = wk.boyutla(P_ham, wh)
        P = onbellek[wh]
        r = {'cift': c, 'kaynak_px': list(wh), **olc(kucult(S), kucult(P), 9)}
        if c in tam:
            r['tam'] = olc(S, P, 17)
        r['sayfa'] = i
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
    gecis = [{'sayfa': j + 1, 'onceki': satir[j - 1]['cift'], 'cift': satir[j]['cift'], 'tahmin': satir[j]['tahmin']}
             for j in range(1, len(satir)) if satir[j]['tahmin'] != satir[j - 1]['tahmin']]
    R = {'boy': a.boy, 'gecisler': gecis, 'plate_px': [P_ham.shape[1], P_ham.shape[0]], 'esik': {'ort': ESIK_ORT, 'p99': ESIK_P99},
         'yontem': 'dE(plate, kaynak), murekkep_maskesi(S-P, kenar=0) disi; tarama 1/2 cozunurluk genisletme 9, tam 17',
         'satir': satir, 'sure_sn': round(time.time() - t0, 1)}
    (cik / f'KAGIT_TARA_{a.boy}.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    md = ['| cift | dE ort | p99 | tahmin | Drive mtime | btime |', '|---|---|---|---|---|---|']
    for r in sorted(satir, key=lambda r: -r['ort']):
        md.append(f"| {r['cift']} | {r['ort']} | {r['p99']} | {r['tahmin']} | {r['drive']['mtime']} | "
                  f"{r['drive']['btime']} |")
    (cik / f'KAGIT_TARA_{a.boy}.md').write_text('\n'.join(md) + '\n')
    print('SINIR', a.boy, json.dumps(gecis), flush=True)
    print('OZET', json.dumps({'boy': a.boy, 'cift': len(satir), 'fail': sum(r['tahmin'] == 'FAIL' for r in satir),
                              'sure_sn': R['sure_sn']}), flush=True)


if __name__ == '__main__':
    main()
