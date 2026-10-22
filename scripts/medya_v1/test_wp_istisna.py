#!/usr/bin/env python3
"""KARAR A (Serdar 2 Eki) iki yonlu test: 7 istisna hucresi olculen degerleriyle PASS; listede olmayan hucre p99 3.2
(sentetik) FAIL; genel esikler degismez."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_ornek as wo                                            # noqa: E402

# kosu 37052384573 (uretimin qc() e_kagit'i, plate B2/B3): ort, p99
OLCULEN = {'GEMINI_SCORPIO': (0.195, 3.24), 'PISCES_PISCES': (0.194, 3.24), 'VIRGO_VIRGO': (0.196, 3.26),
           'LEO_LEO': (0.194, 3.23), 'PISCES_TAURUS': (0.193, 3.23), 'SAGITTARIUS_TAURUS': (0.193, 3.24),
           'SCORPIO_VIRGO': (0.195, 3.28)}                       # SCORPIO_VIRGO: uretim kosusu 37055961309


def q(ort, p99):
    g = ort <= 0.5 and p99 <= 3.0
    return {'e_kagit': {'ort': ort, 'p99': p99, 'esik_ort': 0.5, 'esik_p99': 3.0, 'gecti': g},
            'a_renk': {'gecti': True}, 'gecti': g}


def test_istisna():
    assert set(OLCULEN) == set(wo.E_KAGIT_ISTISNA['11x14']) and list(wo.E_KAGIT_ISTISNA) == ['11x14']
    for c, (o, p) in OLCULEN.items():                            # 7 hucre PASS
        r = wo.e_kagit_istisna(c, '11x14', q(o, p))
        assert r['e_kagit']['gecti'] and r['gecti'] and r['e_kagit']['istisna']['sinir_p99'] <= 3.36, (c, r)
    for c, b, o, p in (('PISCES_SCORPIO', '11x14', 0.1, 3.2),      # listede olmayan cift: sentetik p99 3.2 FAIL
                       ('AQUARIUS_AQUARIUS', '11x14', 0.1, 3.2),
                       ('SCORPIO_VIRGO', '16x20', 0.1, 3.2),        # listedeki cift, baska boy: FAIL
                       ('SCORPIO_VIRGO', '11x14', 0.1, 3.5),        # liste siniri ustu: FAIL
                       ('SCORPIO_VIRGO', '11x14', 0.6, 3.1)):       # ort genel esigi asiyor: FAIL
        r = wo.e_kagit_istisna(c, b, q(o, p))
        assert not r['e_kagit']['gecti'] and not r['gecti'] and 'istisna' not in r['e_kagit'], (c, b, r)
    r = wo.e_kagit_istisna('PISCES_SCORPIO', '11x14', q(0.1, 2.9))  # genel kural degismedi
    assert r['e_kagit']['gecti'] and 'istisna' not in r['e_kagit']


if __name__ == '__main__':
    test_istisna(); print('PASS test_istisna (7 hucre PASS; listede olmayan p99 3.2 FAIL)')
