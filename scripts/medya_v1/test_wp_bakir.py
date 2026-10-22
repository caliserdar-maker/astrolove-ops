#!/usr/bin/env python3
"""wp_bakir sentetik testi (1 Eki, 2. iterasyon). Kurgu: bakir daireli dokulu plate (onayli kagitta OLMAYAN
dikey dikis var), onayli WP yazisi gri-kahve + kabartmali (ust kenar isik, alt kenar golge), duz renk baskisi
kabartmasiz isim/mesaj + golgeli sembol. Beklenen: a-g PASS; dikis dedektoru onarimsiz ciktida dikisi yakalar."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_wp_katman as T                                       # noqa: E402
import wp_bakir as wb                                            # noqa: E402

W, H = T.W, T.H
BAKIR_ESKI = np.array([164, 98, 34], np.float32)
ET = {'buyuk_sembol': (262, 414), 'isim': (776, 838), 'mesaj': (934, 976)}
DIKIS = (slice(850, 1110), slice(600, 602))
SAT = np.isin(np.arange(H), np.r_[766:848, 924:986])


def daire_alfa():
    from PIL import Image, ImageDraw
    im = Image.new('L', (W * 2, H * 2), 0)
    ImageDraw.Draw(im).ellipse((2 * 120, 2 * 120, 2 * 780, 2 * 780), outline=255, width=8)
    return np.asarray(im.resize((W, H), Image.LANCZOS)).astype(np.float32)[..., None] / 255.0


def kabartmali(zemin, a, renk, k=0.9, sigma=1.5):
    gy, _ = wb._yukseklik_egim(a[..., 0], sigma)
    return zemin * (1 - a) + (renk[None, None] * np.clip(1 + k * gy, 0.5, 1.6)[..., None]) * a


def kur(dikisli=True):
    a_d = daire_alfa()
    doku = T.doku()
    S_kagit = T.bas(doku, a_d, BAKIR_ESKI)
    P_wp = S_kagit.copy()                                                        # plate: daire bakir
    if dikisli:
        P_wp[DIKIS] -= 12.0                                                      # plate dikisi (onaylida yok)
    a_eski = T.alfa(T.SEMBOL + T.ISIM + T.MESAJ, {})
    S_wp = kabartmali(S_kagit, a_eski, T.WP_M)                                  # onayli: gri-kahve, kabartmali
    P_c = T.bas(T.CI_Z, a_d, T.CI_M)
    S_c = T.bas(P_c, a_eski, T.CI_M)
    a_yeni = T.alfa(T.SEMBOL + T.YENI_ISIM + T.YENI_MESAJ, {})
    golge = np.ones((H, W, 1), np.float32)
    golge[:ET['isim'][0] - 20] = 1.0 + 0.25 * np.sin(np.arange(W)[None, :] / 9.0)[..., None]   # sembol golgeli
    B = T.bas(P_c, a_yeni, np.clip(T.CI_M * golge, 0, 255))                     # isim/mesaj duz (hat)
    B = B + np.random.default_rng(3).normal(0, 1.2, B.shape)
    daire_c = wb.daire_maskesi(P_c)
    P_ck, _ = wb.kagit_tabani(P_c, daire_c)
    return P_wp, S_wp, B - P_ck, S_c - P_ck, daire_c, float(np.median(P_c @ wb.LUMA))


def test_bakir_hatti():
    P_wp, S_wp, D_cu, D_src, daire, Lp = kur()
    out, P_k, r = wb.bakir_hatti(D_cu, D_src, P_wp, S_wp, daire, ET, Lp, 1.0, plate_iz={'gecti': True})
    q = r['qc']
    for k_ in ('a_renk', 'b_tasma', 'd_dikis', 'e_kagit', 'f_kabartma', 'g_kontrast'):
        assert q[k_]['gecti'], (k_, q[k_])
    assert r['plate_dikis']['onarildi'] and r['onarimsiz_d'], r['plate_dikis']   # dedektor gercek dikisi yakalar
    assert any(abs(c['x'] - 600) <= 2 for c in r['onarimsiz_d']), r['onarimsiz_d']
    assert abs(r['kabartma_onayli']['a'] - 0.9) < 0.3, r['kabartma_onayli']
    return out, S_wp, r


def test_kabartmasiz_kalir():
    """Kabartma uygulanmazsa f) FAIL."""
    P_wp, S_wp, D_cu, D_src, daire, Lp = kur(False)
    kb = wb.kabartma_olc(wb.alfa(D_src), S_wp, P_wp, SAT, 1.0)
    P_k, _ = wb.kagit_tabani(P_wp, daire)
    out, bb = wb.bakir_bas(D_cu, P_k, wb.BAKIR_KOYU, Lp, ET)                      # kabartmasiz
    f = wb.kabartma_kontrol(out, bb['te'], SAT, kb['sigma'], kb)
    assert not f['gecti'], f


def test_kontrast_dusuk_yakalanir():
    """Silik bakir onayli kontrastin altinda: g) yakalar."""
    P_wp, S_wp, D_cu, D_src, daire, Lp = kur(False)
    out, P_k, r = wb.bakir_hatti(D_cu, D_src, P_wp, S_wp, daire, ET, Lp, 1.0, {'gecti': True},
                                 hedef0=(200, 150, 90), tur=1)
    assert not r['qc']['g_kontrast']['gecti'], r['qc']['g_kontrast']['yeni']


if __name__ == '__main__':
    import time
    t = time.time()
    for f in (test_bakir_hatti, test_kabartmasiz_kalir, test_kontrast_dusuk_yakalanir):
        f(); print('PASS', f.__name__, f'{time.time() - t:.1f}s')
