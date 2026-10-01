#!/usr/bin/env python3
"""Siparis dikis kapisi (durdurucu): v2 YANYANA kesiti (yeni) + ayni yerin onayli WP kesiti. v2 dikisi FAIL
(x 1299 yanyana = baski 1563, sapma ~18); ayni seridin onarimi sonrasi PASS; onayli kendisiyle PASS.
AS 11x14 (e4f65cd, isim/sembol bandi x 2262): Scorpio sapi kenari kabartma halesi; eski yazi maskesiyle yanlis alarm
(sapma 62 / onayli 33), hale maskesiyle yok. Yazidan uzak acik kil cizgi hala yakalanir."""
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


def _as():
    a = np.asarray(Image.open(V / 'as11x14_yeni_kesit.png').convert('RGB')).astype(np.float32)
    b = np.asarray(Image.open(V / 'as11x14_onayli_kesit.png').convert('RGB')).astype(np.float32)
    return a, b


def test_as_hale():
    import wp_ornek as wo
    a, b = _as()
    c = {'yon': 'dikey', 'tur': 'acik', 'x': 150, 'y': [80, 184]}
    La, Lb = a @ wb.LUMA, b @ wb.LUMA
    eski = dk.olc(c, La, Lb, wo._yazi_maskesi(a, ince=True), wo._yazi_maskesi(b, ince=True))
    assert eski and eski['sapma_yeni'] > 40, eski                  # 1 Eki taramasindaki yanlis alarm yeniden uretilir
    assert dk.olc(c, La, Lb, dk.hale_maskesi(a), dk.hale_maskesi(b)) is None
    assert dk.kapi(a, b, np.ones(a.shape[0], bool))['gecti']


def test_acik_cizgi_yakalanir():
    """Yazidan uzak +15 luma acik dikey kil cizgi (24x36 plate adayi gibi) FAIL."""
    a, b, sat = _yukle()
    a = a.copy(); a[20:200, 60:63] += 15.0
    r = dk.kapi(np.clip(a, 0, 255), b, sat)
    assert not r['gecti'] and any(c['tur'] == 'acik' and abs(c['x'] - 61) <= 2 for c in r['cizgi']), r


def test_24x36_aday():
    """24x36 plate adayi (x 1937, y 4376-4440, acik, sapma ~12): parsomen benekleri hale almaz, aday gorunur kalir."""
    a = np.asarray(Image.open(V / 'plate24x36_aday_kesit.png').convert('RGB')).astype(np.float32)
    b = np.asarray(Image.open(V / 'onayli24x36_aday_kesit.png').convert('RGB')).astype(np.float32)
    r = dk.kapi(a, b, np.ones(a.shape[0], bool))
    assert not r['gecti'] and any(c['tur'] == 'acik' and abs(c['x'] - 100) <= 2 for c in r['cizgi']), r


def test_onayli_pass():
    _, b, sat = _yukle()
    assert dk.kapi(b, b, sat)['gecti']


if __name__ == '__main__':
    for f in (test_v2_fail, test_onarim_pass, test_onayli_pass, test_as_hale, test_acik_cizgi_yakalanir,
              test_24x36_aday):
        f(); print('PASS', f.__name__)
