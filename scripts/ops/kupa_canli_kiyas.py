"""SALT OKUMA (Serdar 23 Eki, kupa isi madde 6): canli ilan gorselleri (Etsy herkese acik CDN, API/kota yok) ile Drive galeri
kaynagi kiyasi. Her canli gorsel icin en yakin galeri dosyasi (256 px gri, ortalama mutlak fark) ve istenen gorsellerden
kucuk JPEG kirpim. Kullanim: kupa_canli_kiyas.py <canli_klasor> <galeri_klasor> <cikti_klasor> <kirpim_rank,...>"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def kucuk(p):
    return np.asarray(Image.open(p).convert('L').resize((256, 256), Image.LANCZOS), float)


canli, galeri, cikti = (Path(x) for x in sys.argv[1:4])
istenen = {int(x) for x in sys.argv[4].split(',') if x}
cikti.mkdir(parents=True, exist_ok=True)
g = {p.name: kucuk(p) for p in sorted(galeri.glob('[01][0-9]_*.jpg'))}
assert g, 'galeri bos'
satirlar = []
for p in sorted(canli.glob('rank*.jpg'), key=lambda x: int(x.stem[4:])):
    r = int(p.stem[4:])
    c = kucuk(p)
    fark = sorted((float(np.abs(c - v).mean()), k) for k, v in g.items())
    satirlar.append(f'rank {r:2d} {Image.open(p).size} -> {fark[0][1]} MAE {fark[0][0]:.2f} (ikinci {fark[1][1]} {fark[1][0]:.2f})')
    if r in istenen:
        im = Image.open(p).convert('RGB')
        im.resize((900, round(900 * im.height / im.width)), Image.LANCZOS).save(cikti / f'CANLI_rank{r}_900.jpg', quality=72)
(cikti / 'KIYAS.txt').write_text('\n'.join(satirlar) + '\n')
print('\n'.join(satirlar))
