#!/usr/bin/env python3
"""Serdar 3 Eki (Test 5 WP tagline cift baski) testleri.
1) hizala: WP kaynaginda karsiligi olmayan sahte ince bant (doku lekesi) guvenilmez sayilir, en yakin guvenilir bandin
   donusumu gecer; tasinan katmanda o bolgeye baska yerin murekkebi gelmez.
2) ikinci metin kapisi (iki yonlu): mesajin kaymis kesik kopyasi olan cikti FAIL, temiz cikti PASS.
3) kapi beklenen katmani tasinmis haliyle olcer: CI'ya gore 40 px kaymis oge (duzen farki) yabanci sayilmaz."""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_katman as wk                                           # noqa: E402
import wp_bakir as wb                                            # noqa: E402

W, H = 1200, 1400
KAGIT = np.array([228.0, 205.0, 161.0], np.float32)


def kagit(tohum=0):
    r = np.random.default_rng(tohum)
    return np.clip(KAGIT + r.normal(0, 1.5, (H, W, 1)), 0, 255).astype(np.float32)


def yaz(img, metin, y, x=120, renk=(70, 50, 35), olcek=2.2):
    u = np.clip(img, 0, 255).astype(np.uint8)
    cv2.putText(u, metin, (x, y), cv2.FONT_HERSHEY_TRIPLEX, olcek, renk, 4, cv2.LINE_AA)
    img[:] = u.astype(np.float32)
    return img


def sayfa(P, kayma=0):
    A = P.copy()
    yaz(A, 'MAXWELL  &  QUINN', 300 + kayma)
    yaz(A, 'Written in the Stars, Always Yours', 1000 + kayma, x=80, olcek=1.6)
    return A


def test_sahte_bant():
    P = kagit(1)
    S_ci = sayfa(P)
    S_wp = sayfa(P).copy()
    r = np.random.default_rng(5)                                  # isim-mesaj arasinda doku lekeleri (sahte bant)
    for _ in range(40):
        x, y = int(r.integers(100, 1100)), int(r.integers(640, 660))
        S_wp[y - 5:y + 5, x - 5:x + 5] = (205, 182, 140)
    D_ci, D_wp = S_ci - P, S_wp - P
    bl = wk.bantlar(wk.murekkep_maskesi(D_wp, kenar=0))
    assert len(bl) == 3, bl
    hiz = wk.hizala(D_ci, D_wp, bl)
    sahte = [s for s in hiz if s['bant'][0] >= 600 and s['bant'][1] <= 700]
    assert len(sahte) == 1 and not sahte[0]['guvenilir'] and 'yedek' in sahte[0], sahte
    assert all(s['guvenilir'] for s in hiz if s not in sahte), hiz
    Dw = wk.katman_tasi(D_ci, hiz, (W, H))
    a, b = sahte[0]['bolge']
    assert np.abs(Dw[a:b] - D_ci[a:b]).max() < 1.0             # sahte bolge = birim esleme (CI orada bos)
    assert np.abs(Dw[a:b]).max() < 1.0, 'sahte bolgeye murekkep tasindi'


def test_ikinci_metin_iki_yon():
    P = kagit(2)
    B_ci = sayfa(P)                                                # siparisin duz renk baskisi
    temiz = sayfa(P, kayma=2)                                     # WP cikti: ayni metin, 2 px hizalama farki
    r = wb.ikinci_metin(temiz, P, B_ci - P, W / 2400.0)
    assert r['gecti'] and r['bilesen'] == 0, r
    hayalet = temiz.copy()                                         # Test 5: mesajin saga kaymis, alti kesik kopyasi
    kop = sayfa(P)[930:1010, 0:W - 300]
    bolge = hayalet[880:920, 300:W]
    bolge[:] = np.where((kop[40:80] - P[930:970, 0:W - 300]).__abs__().max(-1, keepdims=True) > 30,
                        kop[40:80], bolge)
    r2 = wb.ikinci_metin(hayalet, P, B_ci - P, W / 2400.0)
    assert not r2['gecti'] and r2['bilesen'] >= 1 and 880 <= r2['kutu'][1] <= 920, r2
    return r, r2


def test_duzen_farki():
    P = kagit(3)
    B_ci = sayfa(P)
    wp = sayfa(P, kayma=40)                                        # WP duzeninde ogeler 40 px asagida
    D_tasinmis = wp - P                                            # hizala + katman_tasi sonucu (guvenilir bant)
    assert not wb.ikinci_metin(wp, P, B_ci - P, W / 2400.0)['gecti']   # birim esleme: yanlis alarm
    assert wb.ikinci_metin(wp, P, D_tasinmis, W / 2400.0)['gecti']     # tasinmis katman: PASS


if __name__ == '__main__':
    test_sahte_bant(); print('PASS test_sahte_bant')
    r, r2 = test_ikinci_metin_iki_yon()
    test_duzen_farki(); print('PASS test_duzen_farki')
    print('PASS test_ikinci_metin_iki_yon', 'temiz en_buyuk', r['en_buyuk'], '| hayalet en_buyuk', r2['en_buyuk'],
          'esik', r2['esik_alan'])
