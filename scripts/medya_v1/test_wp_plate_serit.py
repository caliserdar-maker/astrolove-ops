#!/usr/bin/env python3
"""24x36 plate seridi (Serdar 1 Eki ~15:50): aday kesiti (x 1837-2037, y 4276-4540) uzerinde onarim. Once kapi FAIL
(acik cizgi x 1937), sonra PASS; serit disi degisen piksel 0; seritteki sutunlar komsu ortalamasina iner."""
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_dikis_kapisi as dk                                     # noqa: E402
import wp_ornek as wo                                            # noqa: E402

V = Path(__file__).resolve().parent / 'test_veri'
OX, OY = 1837, 4276


def _yukle():
    a = np.asarray(Image.open(V / 'plate24x36_aday_kesit.png').convert('RGB')).astype(np.float32)
    b = np.asarray(Image.open(V / 'onayli24x36_aday_kesit.png').convert('RGB')).astype(np.float32)
    return a, b


def test_serit_uygula():
    a, b = _yukle()
    sat = np.ones(a.shape[0], bool)
    assert not dk.kapi(a, b, sat)['gecti']
    x0, x1, y0, y1 = wo.PLATE_SERITLER['24x36'][0]
    WP, P = a.copy(), a.copy()
    r = wo.serit_uygula(WP, P, np.zeros(a.shape[:2], np.float32), (x0 - OX, x1 - OX, y0 - OY, y1 - OY))
    assert r['serit_disi_degisen_px'] == 0 and r['degisen_px'] > 0, r
    k = dk.kapi(WP, b, sat)
    assert k['gecti'], k
    L = WP @ wo.wk.LUMA
    pr = L[y0 - OY:y1 - OY, x0 - OX - 8:x1 - OX + 8].mean(0)
    cev = np.r_[pr[:8], pr[-8:]]
    assert pr[8:-8].max() <= cev.max() + 1.0, pr                     # serit artik cevresinden acik degil


def test_plate_serit_onar_kanvas():
    """plate_serit_onar: kucuk kanvasta (kesit 150 px ofsetli) tablo ve kesit koordinatlariyla uctan uca."""
    a, b = _yukle()
    H, W = a.shape[0] + 300, a.shape[1] + 300
    K = np.full((H, W, 3), a.mean((0, 1)), np.float32); K[150:150 + a.shape[0], 150:150 + a.shape[1]] = a
    S = np.full((H, W, 3), b.mean((0, 1)), np.float32); S[150:150 + b.shape[0], 150:150 + b.shape[1]] = b
    x0, x1, y0, y1 = wo.PLATE_SERITLER['24x36'][0]
    d = (OX - 150, OY - 150)
    eski = dict(wo.PLATE_SERITLER), dict(wo.SERIT_KESIT)
    wo.PLATE_SERITLER['T'] = [(x0 - d[0], x1 - d[0], y0 - d[1], y1 - d[1])]
    wo.SERIT_KESIT['T'] = (150, 350, 150, 414)
    try:
        with tempfile.TemporaryDirectory() as t:
            WP, P = K.copy(), K.copy()
            _, _, r = wo.plate_serit_onar('X', 'T', S, WP, P, np.zeros((H, W), np.float32), {}, None, Path(t))
            assert (Path(t) / 'WP_X_T_SERIT_ONCE_1e1.png').exists() and (Path(t) / 'WP_X_T_SERIT_SONRA_1e1.png').exists()
    finally:
        wo.PLATE_SERITLER.clear(); wo.PLATE_SERITLER.update(eski[0])
        wo.SERIT_KESIT.clear(); wo.SERIT_KESIT.update(eski[1])
    s = r['seritler'][0]
    assert r['gecti'] and not s['kapi_once']['gecti'] and s['kapi_sonra']['gecti'], r
    assert np.abs(WP - K).max(-1)[np.abs(WP - K).max(-1) > 0].size == s['degisen_px']


if __name__ == '__main__':
    for f in (test_serit_uygula, test_plate_serit_onar_kanvas):
        f(); print('PASS', f.__name__)
