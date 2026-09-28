"""sembol_kapisi: kutudan yana tasan sembol parcasi (Terazi alt cubugu) sayilir (28 Eyl, Serdar onayi).
Eski kapi yalniz bolgeye TAMAMEN sigan bilesenleri sayiyordu: kaynakta kutudan tasan cubuk hic denetlenmiyordu."""
import sys
import types
import unittest

import numpy as np
from PIL import Image

sys.modules.setdefault('pilot6', types.SimpleNamespace(LUMA=np.array([0.299, 0.587, 0.114], np.float32), MUREKKEP=60))
import a1_poster as A  # noqa: E402

H, W = 400, 1000
ZEMIN, ALTIN = (2, 6, 30), (240, 180, 60)


def sayfa(cubuk_dx=0, cubuk=True):
    a = np.zeros((H, W, 3), np.uint8); a[:] = ZEMIN
    for x0 in (200, 650):                                   # iki sembol: halka (bant ici) + alt cubuk (kutudan genis)
        a[120:200, x0:x0 + 150] = ALTIN; a[135:185, x0 + 15:x0 + 135] = ZEMIN
        if cubuk and x0 == 650:
            a[215:225, x0 - 40 + cubuk_dx:x0 + 190 + cubuk_dx] = ALTIN
        elif x0 == 200:
            a[215:225, x0:x0 + 150] = ALTIN
    a[300:340, 150:450] = ALTIN; a[300:340, 600:900] = ALTIN  # isim bandi
    return a


def kapi(poster):
    ref = sayfa()
    S = {'ref': Image.fromarray(ref),
         'oge': {'sembol_sol': {'gorsel': [200, 120, 350, 200], 'w': 150}, 'sembol_sag': {'gorsel': [650, 120, 800, 200], 'w': 150}}}
    s = {'sembol_bant': [120, 200], 'isim_bant': [300, 340]}
    m_src = (ref.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)) > 60
    return A.sembol_kapisi(Image.fromarray(poster), S, s, {'sol': 275, 'sag': 725}, m_src, A.SEMBOL_ESIK)[0]


class KayikParca(unittest.TestCase):
    def test_ayni_poster_gecer(self):
        k = kapi(sayfa())
        self.assertTrue(k['gecti'], k)

    def test_tasan_cubuk_kayarsa_kalir(self):
        k = kapi(sayfa(cubuk_dx=90))                          # cubuk 90 px saga (AQUARIUS_LIBRA tipi)
        self.assertFalse(k['sag']['gecti'], k['sag'])
        self.assertTrue(k['sol']['gecti'], k['sol'])

    def test_tasan_cubuk_yoksa_kalir(self):
        k = kapi(sayfa(cubuk=False))
        self.assertFalse(k['sag']['gecti'], k['sag'])


if __name__ == '__main__':
    unittest.main()
