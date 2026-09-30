#!/usr/bin/env python3
"""wp_katman sentetik testi: duz CI zemini + dokulu WP zemini, bant bazinda kaymis yerlesim,
farkli murekkep renkleri. Kimlik farki kucuk olmali; kirli plate ve eski iz yakalanmali."""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_katman as wk                                           # noqa: E402

W, H = 900, 1200
FONT = None
for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
          '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
    if Path(f).exists():
        FONT = f; break


def font(n):
    return ImageFont.truetype(FONT, n) if FONT else ImageFont.load_default()


def alfa(ogeler, kayma):
    """ogeler: [(bant_adi, xy, metin, punto)] -> 0..1 alfa; kayma: bant_adi -> (dx, dy)."""
    im = Image.new('L', (W * 2, H * 2), 0)
    d = ImageDraw.Draw(im)
    for ad, (x, y), t, n in ogeler:
        dx, dy = kayma.get(ad, (0, 0))
        d.text(((x + dx) * 2, (y + dy) * 2), t, font=font(n * 2), fill=255, anchor='mm')
    return np.asarray(im.resize((W, H), Image.LANCZOS)).astype(np.float32)[..., None] / 255.0


def doku(tohum=1):
    rng = np.random.default_rng(tohum)
    n = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 3) * 60
    g = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 40) * 400
    base = np.array([214, 178, 128], np.float32)
    return np.clip(base + (n + g)[..., None] * np.array([1.0, 0.9, 0.7]), 0, 255)


SEMBOL = [('buyuk', (450, 350), 'XO', 200)]
ISIM = [('isim', (250, 800), 'AQUARIUS', 44), ('isim', (650, 800), 'CANCER', 44)]
MESAJ = [('mesaj', (450, 950), 'Two Souls One Bond', 34)]
YENI_ISIM = [('isim', (250, 800), 'EMILY', 44), ('isim', (650, 800), 'JAMES', 44)]
YENI_MESAJ = [('mesaj', (450, 950), 'It Began With a Kiss', 34)]
KAYMA_WP = {'buyuk': (6, -9), 'isim': (-4, 7), 'mesaj': (3, 5)}
CI_Z = np.full((H, W, 3), [238, 226, 208], np.float32)
CI_M = np.array([92, 60, 38], np.float32)
WP_M = np.array([120, 84, 36], np.float32)


def bas(zemin, a, renk):
    return zemin * (1 - a) + renk * a


def kur():
    P_wp = doku()
    a_ci = alfa(SEMBOL + ISIM + MESAJ, {})
    a_wp = alfa(SEMBOL + ISIM + MESAJ, KAYMA_WP)
    S_ci = bas(CI_Z, a_ci, CI_M)
    S_wp = bas(P_wp, a_wp, WP_M)
    return P_wp, S_ci, S_wp


def ogren(P_wp, S_ci, S_wp):
    D_ci, D_wp = S_ci - CI_Z, S_wp - P_wp
    bl = wk.bantlar(wk.murekkep_maskesi(D_wp))
    hiz = wk.hizala(D_ci, D_wp, bl)
    Dw = wk.katman_tasi(D_ci, hiz, (W, H))
    return hiz, wk.renk_ogren(Dw, P_wp, S_wp)


def test_kimlik():
    P_wp, S_ci, S_wp = kur()
    hiz, model = ogren(P_wp, S_ci, S_wp)
    assert len(hiz) == 3, hiz
    for s, k in zip(hiz, ('buyuk', 'isim', 'mesaj')):
        dx, dy = KAYMA_WP[k]
        assert abs(s['dx'] + dx) < 0.6 and abs(s['dy'] + dy) < 0.6, (k, s['dx'], s['dy'])
    out, _ = wk.katman_bas(S_ci, CI_Z, P_wp, hiz, model)
    r = wk.fark_tablosu(out, S_wp, P_wp, {})
    assert r['murekkep']['ort'] < 2.0 and r['murekkep']['p99'] < 15, r
    assert r['tum']['ort'] < 0.3, r


def test_siparis_zemin_birebir():
    """Yeni isimde murekkep olmayan her piksel WP plate'inin kendisi (silme/leke yok)."""
    P_wp, S_ci, S_wp = kur()
    hiz, model = ogren(P_wp, S_ci, S_wp)
    B = bas(CI_Z, alfa(SEMBOL + YENI_ISIM + YENI_MESAJ, {}), CI_M)
    out, D = wk.katman_bas(B, CI_Z, P_wp, hiz, model)
    bos = np.abs(D).max(-1) <= wk.RAMPA[0]
    assert np.abs(out - P_wp)[bos].max() < 1e-3
    yeni = alfa(SEMBOL + YENI_ISIM + YENI_MESAJ, {})[..., 0] > 0.03
    iz = wk.eski_iz(S_ci - CI_Z, B - CI_Z, yeni, np.ones((H, W), bool))
    assert iz['gecti'], iz


def test_eski_iz_yakalanir():
    P_wp, S_ci, S_wp = kur()
    a_eski = alfa(ISIM, {})
    B = bas(CI_Z, alfa(SEMBOL + YENI_ISIM + YENI_MESAJ, {}), CI_M)
    B = bas(B, a_eski * 0.3, CI_M)                        # eski ismin %30 hayaleti
    yeni = alfa(SEMBOL + YENI_ISIM + YENI_MESAJ, {})[..., 0] > 0.03
    iz = wk.eski_iz(S_ci - CI_Z, B - CI_Z, yeni, np.ones((H, W), bool))
    assert not iz['gecti'], iz


def test_plate_temizlik():
    P_wp, S_ci, S_wp = kur()
    bl = {'isim': (760, 840), 'mesaj': (925, 975)}
    iyi = wk.plate_temizlik(P_wp, S_wp, bl)
    assert iyi['gecti'], iyi
    kirli = bas(P_wp, alfa(MESAJ, KAYMA_WP) * 0.35, WP_M)   # soluk eski slogan izi
    k = wk.plate_temizlik(kirli, S_wp, bl)
    assert not k['mesaj']['gecti'], k
    assert k['isim']['gecti'], k


if __name__ == '__main__':
    import time
    t = time.time()
    for f in (test_kimlik, test_siparis_zemin_birebir, test_eski_iz_yakalanir, test_plate_temizlik):
        f(); print('PASS', f.__name__, f'{time.time() - t:.1f}s')
