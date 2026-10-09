#!/usr/bin/env python3
"""WP tagline cift baski kaniti (Serdar 9 Eki). Yerel dosyalardan, Drive'a yazmaz.
yanyana : eski | yeni tam cozunurluk JPEG (q 92) + kapinin isaretledigi yerin (yoksa mesaj bandinin) 1:1 kesiti.
renk_md5: renk ciktisindaki her goruntu dosyasi ve PDF icindeki goruntu akisi -> md5 listesi (json)."""
import argparse, hashlib, json, sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def yanyana(a):
    E = np.asarray(Image.open(a.eski).convert('RGB')); Y = np.asarray(Image.open(a.yeni).convert('RGB'))
    if E.shape != Y.shape:
        raise SystemExit(f'HATA: boyut {E.shape} != {Y.shape}')
    H, W = E.shape[:2]
    ara = np.full((H, 24, 3), 255, np.uint8)
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.concatenate([E, ara, Y], 1)).save(cik / f'{a.ad}_ESKI_YENI_TAM.jpg', quality=92)
    k = json.loads(a.kutu) if a.kutu else None
    if k:
        x0, y0, x1, y1 = k
    else:
        x0, y0, x1, y1 = W // 4, int(H * 0.80), 3 * W // 4, int(H * 0.86)
    p = int(0.06 * W)
    y0, y1 = max(0, y0 - p), min(H, y1 + p)
    x0, x1 = max(0, min(x0 - p, W // 2 - int(0.3 * W))), min(W, max(x1 + p, W // 2 + int(0.3 * W)))
    e, y = E[y0:y1, x0:x1], Y[y0:y1, x0:x1]
    Image.fromarray(np.concatenate([e, np.full((8, e.shape[1], 3), 255, np.uint8), y], 0)).save(
        cik / f'{a.ad}_ESKI_YENI_KESIT_1e1.png')
    d = np.abs(E.astype(np.int16) - Y.astype(np.int16)).max(-1)
    print('YANYANA', a.ad, json.dumps({'px': [W, H], 'kesit': {'x': [x0, x1], 'y': [y0, y1]},
                                       'fark_px_gt8': int((d > 8).sum())}), flush=True)


def renk_md5(a):
    kok = Path(a.kok); sonuc = {}
    for p in sorted(kok.rglob('*')):
        if not p.is_file():
            continue
        r = str(p.relative_to(kok))
        if p.suffix.lower() in ('.jpg', '.jpeg', '.png'):
            sonuc[r] = hashlib.md5(p.read_bytes()).hexdigest()
        elif p.suffix.lower() == '.pdf':
            import pikepdf
            with pikepdf.open(p) as pdf:
                for n, sf in enumerate(pdf.pages, 1):
                    for ad, raw in sf.images.items():
                        sonuc[f'{r}#s{n}{ad}'] = hashlib.md5(raw.read_raw_bytes()).hexdigest()
    Path(a.cik).write_text(json.dumps(sonuc, indent=1))
    print('RENK_MD5', a.kok, len(sonuc), flush=True)


def renk_karsilastir(a):
    satir, top = [], 0
    for r in a.renkler.split(','):
        e = json.loads(Path(a.kok, f'eski_{r}', f'MD5_eski_{r}.json').read_text())
        y = json.loads(Path(a.kok, f'yeni_{r}', f'MD5_yeni_{r}.json').read_text())
        ortak = sorted(set(e) & set(y)); fark = [k for k in ortak if e[k] != y[k]]
        eksik = sorted(set(e) ^ set(y))
        satir.append({'renk': r, 'goruntu': len(ortak), 'farkli': len(fark), 'eksik': len(eksik), 'ornek_fark': fark[:3]})
        top += len(fark) + len(eksik)
    print('RENK_TABLO', json.dumps(satir), flush=True)
    Path(a.cik).write_text('| renk | karsilastirilan goruntu | farkli | yalniz birinde |\n|---|---|---|---|\n' +
                           ''.join(f"| {s['renk']} | {s['goruntu']} | {s['farkli']} | {s['eksik']} |\n" for s in satir))
    return 0 if top == 0 and all(s['goruntu'] for s in satir) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('is_', choices=('yanyana', 'renk_md5', 'renk_karsilastir'))
    ap.add_argument('--eski'); ap.add_argument('--yeni'); ap.add_argument('--ad'); ap.add_argument('--kutu', default='')
    ap.add_argument('--kok'); ap.add_argument('--cik'); ap.add_argument('--renkler', default='')
    a = ap.parse_args()
    sys.exit({'yanyana': yanyana, 'renk_md5': renk_md5, 'renk_karsilastir': renk_karsilastir}[a.is_](a) or 0)


if __name__ == '__main__':
    main()
