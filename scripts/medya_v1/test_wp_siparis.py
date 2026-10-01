#!/usr/bin/env python3
"""Siparis hatti: WARM_PARCHMENT siparisi kilitli bakir koda (wp_ornek.cift_boy siparis=True) gider; isim/mesaj
siparisten gecer, BASKI_<boy>.jpg hedef pikselde yazilir, kapilar d) haric bakir QC'den + durdurucu dikis kapisi (wp_dikis_kapisi). Drive/hat yok (sahte)."""
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402
import wp_dikis_kapisi as dk                                     # noqa: E402
import wp_ornek as wo                                            # noqa: E402

SIP = {'receipt': 'T', 'cift': 'CANCER_LIBRA', 'boy': '11x14', 'renk': 'WARM_PARCHMENT', 'sayfa': 7,
       'isim1': 'EMILY', 'isim2': 'JAMES', 'mesaj': 'It Began With a Kiss in the Rain', 'hedef_px': [40, 50]}


def _sahte(gecti_g=True, dikis=True):
    cagri = {}
    dk.siparis_kapisi = lambda WP, cift, boy, et: {'cizgi': [] if dikis else [{'x': 1563}], 'gecti': dikis}

    def cift_boy(cift, boy, P_ed, P_blue, no, cik, isim=None, mesaj=None, siparis=False):
        cagri.update(cift=cift, boy=boy, no=no, isim=isim, mesaj=mesaj, siparis=siparis)
        q = {a: {'gecti': True} for a in sd.WP_KAPILAR}
        q['g_kontrast']['gecti'] = gecti_g
        q['d_dikis'] = {'gecti': False}
        R = {'durum': 'URETILDI', 'qc': q, 'bantlar': {'isim': [10, 20]}, 'plate_gecti': True, 'zemin_birebir': {'gecti': True},
             'eski_iz': {'gecti': True}, 'siparis_duz_renk_kapilar': {'kapilar_gecti': True}}
        return R, np.full((50, 40, 3), 200.0, np.float32)
    return cagri, cift_boy


def test_yonlendirme():
    cagri, f = _sahte()
    eski, wo.cift_boy = wo.cift_boy, f
    try:
        with tempfile.TemporaryDirectory() as d:
            r = sd.wp_bakir_uret(dict(SIP), None, None, Path(d))
            assert (Path(d) / 'BASKI_11x14.jpg').exists()
    finally:
        wo.cift_boy = eski
    assert cagri == {'cift': 'CANCER_LIBRA', 'boy': '11x14', 'no': {'CANCER_LIBRA': 7}, 'isim': ('EMILY', 'JAMES'),
                     'mesaj': SIP['mesaj'], 'siparis': True}, cagri
    assert r['yontem'] == 'WP_BAKIR' and r['kapilar_gecti'] and r['baski_px'] == [40, 50], r
    assert 'd_dikis' not in r['kapilar'] and r['kapilar']['dikis'] is True


def test_kapi_dusurur():
    _, f = _sahte(gecti_g=False)
    eski, wo.cift_boy = wo.cift_boy, f
    try:
        with tempfile.TemporaryDirectory() as d:
            r = sd.wp_bakir_uret(dict(SIP), None, None, Path(d))
    finally:
        wo.cift_boy = eski
    assert r['kapilar_gecti'] is False and r['kapilar']['g_kontrast'] is False


def test_dikis_durdurur():
    _, f = _sahte(dikis=False)
    eski, wo.cift_boy = wo.cift_boy, f
    try:
        with tempfile.TemporaryDirectory() as d:
            r = sd.wp_bakir_uret(dict(SIP), None, None, Path(d))
    finally:
        wo.cift_boy = eski
    assert r['kapilar_gecti'] is False and r['kapilar']['dikis'] is False


if __name__ == '__main__':
    for f in (test_yonlendirme, test_kapi_dusurur, test_dikis_durdurur):
        f(); print('PASS', f.__name__)
