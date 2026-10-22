#!/usr/bin/env python3
"""Dikis duzeltmesi (ornek dal): bayrak kapali -> eski kuyruk_duzlestir ile ayni; acik -> MB profili uc satirlar atilir.
KISISEL_YOL=<kisisel-v1>/scripts/kisisel ve PROFIL_YOL=<cancer_name_gold.png klasoru> gerekir (yoksa atlanir)."""
import os, sys, unittest
from pathlib import Path
import numpy as np
KY, PY = os.environ.get('KISISEL_YOL', ''), os.environ.get('PROFIL_YOL', '')
if KY:
    sys.path.insert(0, KY)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import pilot12, pilot7, mesaj_kapisi as mk
    HAZIR = bool(PY) and (Path(PY) / 'cancer_name_gold.png').exists()
except Exception:                                                 # noqa: BLE001
    HAZIR = False


@unittest.skipUnless(HAZIR, 'kisisel modulleri / profil yok')
class DikisDuzeltTesti(unittest.TestCase):
    def setUp(self):
        self.prof = pilot12.profil_yukle(Path(PY))['sol']

    def test_kapali_eskiyle_ayni(self):
        mk.DIKIS['etkin'] = False
        mk.duzeltme_uygula(pilot12)
        a, i = pilot12.kuyruk_duzlestir(self.prof)
        b, j = pilot7.kuyruk_duzlestir(self.prof)
        self.assertEqual(i, j); self.assertTrue(np.array_equal(a, b))

    def test_acik_mb_profili(self):
        q, (i0, i1) = mk.profil_kenar_kirp(self.prof)
        self.assertEqual((i0, i1), (29, 354))
        d = np.abs(np.diff(q @ mk.LUMA))
        self.assertLessEqual(float(d[:20].max()), 6.0)
        mk.DIKIS['etkin'] = True
        try:
            mk.duzeltme_uygula(pilot12)
            r, k = pilot12.kuyruk_duzlestir(self.prof)
            self.assertTrue(np.array_equal(r, q)); self.assertEqual(k, len(q) - 1)
        finally:
            mk.DIKIS['etkin'] = False

    def test_kisa_profil(self):
        p = np.linspace([250, 200, 80], [150, 110, 40], 8).astype(np.float32)
        q, ar = mk.profil_kenar_kirp(p)
        self.assertTrue(np.array_equal(q, p))


if __name__ == '__main__':
    unittest.main()
