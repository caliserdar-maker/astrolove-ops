#!/usr/bin/env python3
"""wp_bakir sentetik testi: bakir daireli dokulu plate, kabartmali duz renk baskisi (+ hibrit bant dikisi ve
kenar gurultusu). Beklenen: tum ogeler hedef bakir, dikis/hale kagida tasinmaz; dedektor kasitli dikisi yakalar."""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_wp_katman as T                                       # noqa: E402
import wp_bakir as wb                                            # noqa: E402

W, H = T.W, T.H
BAKIR = np.array([169, 109, 47], np.float32)


def daire_alfa():
    from PIL import Image, ImageDraw
    im = Image.new('L', (W * 2, H * 2), 0)
    ImageDraw.Draw(im).ellipse((2 * 120, 2 * 120, 2 * 780, 2 * 780), outline=255, width=8)
    return np.asarray(im.resize((W, H), Image.LANCZOS)).astype(np.float32)[..., None] / 255.0


def kur(dikisli=True):
    a_d = daire_alfa()
    doku = T.doku()
    P_wp = T.bas(doku, a_d, BAKIR)
    P_c = T.bas(T.CI_Z, a_d, T.CI_M)
    og = T.SEMBOL + T.YENI_ISIM + T.YENI_MESAJ
    a = T.alfa(og, {})
    golge = 1.0 + 0.25 * np.sin(np.arange(W)[None, :] / 9.0)[..., None]       # kabartma isigi/golgesi
    B = T.bas(P_c, a, np.clip(T.CI_M * golge, 0, 255))
    rng = np.random.default_rng(3)
    B = B + rng.normal(0, 1.2, B.shape)                                          # JPEG / plate gurultusu
    if dikisli:
        B[860:1120, 600:602] -= 4.0                                              # hibrit bant dikisi (D = 4)
    S_wp = T.bas(P_wp, T.alfa(T.SEMBOL + T.ISIM + T.MESAJ, {}), T.WP_M)          # onayli: gri-kahve
    et = {'buyuk_sembol': (262, 414), 'isim': (776, 838), 'mesaj': (934, 976)}
    return P_wp, P_c, B, S_wp, et, a_d[..., 0] > 0.5


def test_bakir_qc():
    P_wp, P_c, B, S_wp, et, _ = kur()
    daire = wb.daire_maskesi(P_c)
    assert daire.sum() > 1000, daire.sum()
    hedef = wb.bakir_hedef(P_wp, daire)
    assert wb._dE(hedef['rgb'], BAKIR) < 3, hedef
    out, b = wb.bakir_bas(B - P_c, P_wp, hedef['rgb'], float(np.median(P_c @ wb.LUMA)))
    q = wb.qc(out, P_wp, S_wp, b, et, daire, hedef, {'gecti': True})
    for k in ('a_renk', 'b_tasma', 'd_dikis', 'e_kagit'):
        assert q[k]['gecti'], (k, q[k])
    # maske disi birebir plate (dikis ve gurultu tasinmadi)
    assert np.abs(out - P_wp)[~b['M']].max() < 1e-3
    return out, P_wp, S_wp, b, et, daire, hedef


def test_dikis_dedektoru():
    out, P_wp, S_wp, b, et, daire, hedef = test_bakir_qc()
    kotu = out.copy()
    kotu[860:1120, 600:602] -= 12.0                                              # Serdar'in gordugu: 196 -> 184
    q = wb.qc(kotu, P_wp, S_wp, b, et, daire, hedef, {'gecti': True})
    assert not q['d_dikis']['gecti'] and q['d_dikis']['yeni'][0]['x'] in (600, 601), q['d_dikis']


def test_guclu_dikis_maskede():
    """Duz renk baskisinda guclu dikis (D = 20) cizgi maskesine girer: QC d) yakalar."""
    P_wp, P_c, B, S_wp, et, _ = kur()
    B[860:1120, 600:602] -= 20.0
    daire = wb.daire_maskesi(P_c); hedef = wb.bakir_hedef(P_wp, daire)
    out, b = wb.bakir_bas(B - P_c, P_wp, hedef['rgb'], float(np.median(P_c @ wb.LUMA)))
    q = wb.qc(out, P_wp, S_wp, b, et, daire, hedef, {'gecti': True})
    assert not q['d_dikis']['gecti'] and q['d_dikis']['maskede_ince_bilesen'], q['d_dikis']


def test_kahverengi_yakalanir():
    out, P_wp, S_wp, b, et, daire, hedef = test_bakir_qc()
    kotu = out.copy()
    m = np.zeros(out.shape[:2], bool); y0, y1 = et['buyuk_sembol']; m[y0:y1] = b['ce'][y0:y1]
    kotu[m] = T.WP_M                                                             # buyuk sembol gri-kahve kalmis
    q = wb.qc(kotu, P_wp, S_wp, b, et, daire, hedef, {'gecti': True})
    assert not q['a_renk']['gecti'], q['a_renk']


if __name__ == '__main__':
    import time
    t = time.time()
    for f in (test_bakir_qc, test_dikis_dedektoru, test_guclu_dikis_maskede, test_kahverengi_yakalanir):
        f(); print('PASS', f.__name__, f'{time.time() - t:.1f}s')
