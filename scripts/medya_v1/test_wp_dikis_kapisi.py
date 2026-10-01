#!/usr/bin/env python3
"""Siparis dikis kapisi (durdurucu): v2 YANYANA kesiti (yeni) + ayni yerin onayli WP kesiti. v2 dikisi FAIL
(x 1299 yanyana = baski 1563, sapma ~18); ayni seridin onarimi sonrasi PASS; onayli kendisiyle PASS."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_bakir as wb                                            # noqa: E402
import wp_dikis_kapisi as dk                                     # noqa: E402

V = Path(__file__).resolve().parent / 'test_veri'
OX, OY = 1100, 3900                                              # kesitin yanyana sol-ust koordinati


def _yukle():
    a = np.asarray(Image.open(V / 'v2_yanyana_kesit.png').convert('RGB')).astype(np.float32)
    b = np.asarray(Image.open(V / 'v2_onayli_kesit.png').convert('RGB')).astype(np.float32)
    return a, b, np.ones(a.shape[0], bool)


def test_v2_fail():
    a, b, sat = _yukle()
    r = dk.kapi(a, b, sat)
    assert not r['gecti'], r
    c = max(r['cizgi'], key=lambda z: z['sapma_yeni'])
    assert c['tur'] == 'koyu' and abs(c['x'] + OX - 1299.5) <= 2 and c['sapma_yeni'] >= 15, c


def test_onarim_pass():
    a, b, sat = _yukle()
    B, _ = wb.serit_onar(a, 1297 - OX, 1303 - OX, 3975 - OY, 4235 - OY)
    r = dk.kapi(B, b, sat)
    assert r['gecti'], r


def test_onayli_pass():
    _, b, sat = _yukle()
    assert dk.kapi(b, b, sat)['gecti']


if __name__ == '__main__':
    for f in (test_v2_fail, test_onarim_pass, test_onayli_pass):
        f(); print('PASS', f.__name__)
