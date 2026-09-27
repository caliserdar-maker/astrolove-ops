# Kart 02: sagdaki cerceve cevresindeki notr acik haleyi siler. Baska piksel degismez.
import sys, numpy as np
from PIL import Image
from scipy import ndimage
GIR, CIK = sys.argv[1], sys.argv[2]
a = np.asarray(Image.open(GIR).convert('RGB')).astype(np.int16)
X0, X1, Y0, Y1 = 2190, 2829, 495, 1294          # hale dis kutusu (olculdu)
kutu = np.zeros(a.shape[:2], bool); kutu[Y0:Y1+1, X0:X1+1] = True
sp = a.max(2) - a.min(2); v = a.mean(2)
hale = kutu & (sp <= 16) & (v >= 150)             # notr, acik: hale; altin (sp>40) ve koyu poster haric
# poster ici notr acik piksel olmasin: cercevenin ic tarafini disla
ic = np.zeros_like(kutu); ic[Y0+30:Y1-30, X0+30:X1-30] = True
hale &= ~ic
# her hale pikselini kutu disindaki en yakin pikselle doldur (golge/zemin devami)
_, (iy, ix) = ndimage.distance_transform_edt(kutu, return_indices=True)
b = a.copy(); b[hale] = a[iy[hale], ix[hale]]
Image.fromarray(b.astype(np.uint8)).save(CIK, quality=95, subsampling=0)
# QC
c = np.asarray(Image.open(CIK).convert('RGB')).astype(np.int16)
kalan = kutu & ~ic & ((c.max(2)-c.min(2)) <= 3) & (c.mean(2) >= 225)
dis = ~kutu
fark = np.abs(c - a).max(2)
print(f'boyut {c.shape[1]}x{c.shape[0]} | silinen hale px {hale.sum()} | kalan notr acik px {kalan.sum()} | '
      f'kutu disi ort fark {fark[dis].mean():.2f} maks {fark[dis].max()}')
print('PASS' if kalan.sum() < 50 and fark[dis].mean() < 1.0 else 'FAIL')
