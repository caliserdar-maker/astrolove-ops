#!/usr/bin/env python3
"""PDF sayfalarini TAM (1:1, yeniden kodlama yok) JPEG olarak cikarir: goz kontrolu (Serdar 3 Eki, Test 6 WP 5 boy).
Sayfa goruntusu PDF'te DCT (JPEG) akisiyla gomulu: ham bayt aynen yazilir. Boy, piksel olcusunden.
Kullanim: pdf_sayfa.py PDF CIKTI_KLASOR ONEK"""
import sys
from pathlib import Path

import pikepdf

BOY = {(4800, 6000): '16x20', (5400, 7200): '18x24', (7200, 10800): '24x36', (3307, 4200): '11x14', (4960, 7015): 'A2'}


def main(pdf, cik, onek):
    cik = Path(cik); cik.mkdir(parents=True, exist_ok=True)
    n = 0
    with pikepdf.open(pdf) as p:
        for i, pg in enumerate(p.pages):
            for _, x in pg.images.items():
                boy = BOY.get((int(x.Width), int(x.Height)), f'sayfa{i + 1}')
                if x.get('/Filter') != '/DCTDecode':
                    raise SystemExit(f'sayfa {i + 1}: JPEG degil ({x.get("/Filter")})')
                (cik / f'{onek}_{boy}.jpg').write_bytes(x.read_raw_bytes())
                n += 1
                print('SAYFA', i + 1, boy, int(x.Width), int(x.Height), flush=True)
    if n == 0:
        raise SystemExit('goruntu yok')
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:4]))
