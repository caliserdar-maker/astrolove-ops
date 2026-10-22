#!/usr/bin/env python3
"""Serdar 1 Eki: v2 WP_CANCER_LIBRA_11x14_YANYANA.jpg (2864x4286) kesiti (x 1100-1500, y 3900-4286) uzerinde
yanyana dikis dedektoru. v2'de 'With' ile 'a' arasindaki dikey cizgi (x 1298-1301) FAIL vermeli; ayni seridin
(SERDAR_SERIT yanyana karsiligi) komsu sutun ortalamasiyla onarimi sonrasi PASS ve en koyu sutun <= 4 olmali."""
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_bakir as wb                                            # noqa: E402
import wp_ornek as wo                                            # noqa: E402

KESIT = Path(__file__).resolve().parent / 'test_veri' / 'v2_yanyana_kesit.png'
OFSET = (1100, 3900)
GEO = {'x0': 264, 'y0': 2608, 'olcek': 1.0, 'panel_y': [1880, 3093]}   # 1 Eki kosusu (c5e0289) yanyana yerlesimi
HPAN = 1163


def _profil(img):
    x0, x1, y0, y1 = wo.SERDAR_YAN
    return wo.sutun_profili(img, x0 - OFSET[0], x1 - OFSET[0], y0 - OFSET[1], y1 - OFSET[1])


def _onar(img):
    A = np.asarray(img.convert('RGB')).astype(np.float32)
    x0, x1, y0, y1 = wo.SERDAR_SERIT
    dx = GEO['x0'] + OFSET[0]; dy = GEO['y0'] - GEO['panel_y'][1] + OFSET[1]
    B, _ = wb.serit_onar(A, x0 - dx, x1 - dx, y0 - dy, y1 - dy)
    bio = io.BytesIO()
    Image.fromarray(np.clip(B + 0.5, 0, 255).astype(np.uint8)).save(bio, 'JPEG', quality=90)
    return Image.open(io.BytesIO(bio.getvalue())), np.abs(B - A).max(-1) > 0, (x0 - dx, x1 - dx, y0 - dy, y1 - dy)


def test_v2_fail():
    img = Image.open(KESIT)
    assert wo.koyu_sutun(_profil(img)) > 4
    r = wo.yanyana_dedektor(img, GEO, HPAN, ofset=OFSET)
    assert r['sonuc'].startswith('FAIL') and any(1298 <= c['x'] <= 1301 for c in r['cizgi']), r


def test_onarim_pass():
    j, deg, (a, b, c, d) = _onar(Image.open(KESIT))
    assert wo.koyu_sutun(_profil(j)) <= 4, _profil(j)
    disari = deg.copy(); disari[c:d, a:b] = False
    assert not disari.any()
    r = wo.yanyana_dedektor(j, GEO, HPAN, ofset=OFSET)
    assert r['sonuc'].startswith('PASS'), r


if __name__ == '__main__':
    import time
    t = time.time()
    for f in (test_v2_fail, test_onarim_pass):
        f(); print('PASS', f.__name__, f'{time.time() - t:.1f}s')
