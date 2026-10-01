"""Dijital yol duzeltmeleri (1 Eki 2026, siparis 4188621967): leke kapisi KAYNAGA karsi; olcek ikinci denemesi
POD ile ayni. Sentetik goruntu, Drive / kisisel kod gerekmez."""
import io
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.medya_v1 import siparis_dosyasi as sd


def _jpg_bayt(a):
    b = io.BytesIO(); Image.fromarray(a).save(b, 'JPEG', quality=95, subsampling=0); return b.getvalue()


class LekeKaynak(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(7)
        H, W = 600, 480
        self.kaynak = np.zeros((H, W, 3), np.uint8)
        self.kaynak[rng.integers(0, H, 400), rng.integers(0, W, 400)] = 255     # yildizlar (cifte ozgu)
        self.kaynak[100:220, 150:330] = (200, 150, 60)                           # burc cizimi
        self.plate = np.zeros((H, W, 3), np.uint8)                              # medyan plate: yildizsiz duz
        self.maske = np.zeros((H, W), bool); self.maske[450:520, 60:420] = True  # degisen isim bandi
        self.ek = {'maske': self.maske}

    def _baski(self, leke=False):
        b = self.kaynak.copy()
        b[455:515, 80:400] = (240, 190, 70)                                       # yeni isimler (bant ici)
        if leke:
            b[300:360, 40:120] = (90, 90, 90)                                     # bant DISINDA gercek yama
        return Image.open(io.BytesIO(_jpg_bayt(b)))

    def test_kaynaga_karsi_temiz_gecer(self):
        r = sd.dijital_leke(self._baski(), _jpg_bayt(self.kaynak), self.ek)
        self.assertTrue(r['gecti'], r)

    def test_eski_plate_referansi_tasarimi_leke_sayardi(self):
        # Hata kaniti: ayni temiz baski plate'e karsi olculunce yildiz / cizim leke sayiliyor.
        r = sd.leke_kapisi(self._baski(), _jpg_bayt(self.plate), self.maske)
        self.assertFalse(r['gecti'], r)

    def test_gercek_leke_hala_yakalanir(self):
        r = sd.dijital_leke(self._baski(leke=True), _jpg_bayt(self.kaynak), self.ek)
        self.assertFalse(r['gecti'], r)


class OlcekIkinciDeneme(unittest.TestCase):
    def _ilk(self, gecti):
        return ('p1', {'olcek_kapisi': {'gecti': gecti, 'konum_fark_px': 1.3, 'kenar_fark_px': 0.8}}, {'e': 1},
                'b1', {'bpx': 1})

    def _calis(self, ed='modern', hedef_en=3300, ilk_gecti=False, ikinci_gecti=True, hata=False, yok=False):
        d = Path(tempfile.mkdtemp())
        hedef, gecici = d / 'sayfa.jpg', d / '_olcekli_sayfa.jpg'
        hedef.write_bytes(b'ilk')
        cagri = {'yeniden': 0, 'etkin': None}

        def yeniden():
            cagri['yeniden'] += 1
            cagri['etkin'] = sd.SATIR_OLCEKLI['etkin']
            if hata:
                raise RuntimeError('render')
            if yok:
                return None
            gecici.write_bytes(b'ikinci')
            return 'p2', {}, {'e': 2}, 'b2', {'bpx': 2}, gecici
        olc = lambda b, e, p, i: {'gecti': ikinci_gecti, 'konum_fark_px': 0.4, 'kenar_fark_px': 0.5}
        leke = lambda b, e: {'gecti': True, 'ref': 'kaynak'}
        try:
            r = sd.olcek_ikinci_deneme(ed, hedef_en, self._ilk(ilk_gecti), yeniden, olc, leke, hedef)
        except RuntimeError:
            r = 'HATA'
        return r, cagri, hedef, gecici

    def test_gecen_ilk_deneme_dokunulmaz(self):
        r, c, h, _ = self._calis(ilk_gecti=True)
        self.assertEqual(r[0], 'p1'); self.assertEqual(c['yeniden'], 0); self.assertEqual(h.read_bytes(), b'ilk')

    def test_blue_ve_2400_ikinci_deneme_yok(self):
        for ed, en in (('blue', 3300), ('modern', 2400)):
            r, c, _, _ = self._calis(ed=ed, hedef_en=en)
            self.assertEqual(r[0], 'p1'); self.assertEqual(c['yeniden'], 0)

    def test_ikinci_gecerse_kullanilir(self):
        r, c, h, g = self._calis()
        self.assertEqual(r[0], 'p2'); self.assertTrue(c['etkin'])
        self.assertEqual(h.read_bytes(), b'ikinci'); self.assertFalse(g.exists())
        self.assertEqual(r[1]['olcek_kapisi']['yerlesim'], 'olcekli (2400 x k)')
        self.assertEqual(r[1]['olcek_kapisi']['ilk_yerlesim']['konum_fark_px'], 1.3)
        self.assertEqual(r[1]['leke_kapisi']['ref'], 'kaynak')
        self.assertFalse(sd.SATIR_OLCEKLI['etkin'])

    def test_ikinci_kalirsa_ilk_kalir(self):
        r, _, h, g = self._calis(ikinci_gecti=False)
        self.assertEqual(r[0], 'p1'); self.assertEqual(h.read_bytes(), b'ilk'); self.assertFalse(g.exists())
        self.assertEqual(r[1]['olcek_kapisi']['olcekli_deneme']['konum_fark_px'], 0.4)

    def test_hata_bayragi_geri_alir(self):
        r, _, _, _ = self._calis(hata=True)
        self.assertEqual(r, 'HATA'); self.assertFalse(sd.SATIR_OLCEKLI['etkin'])
        r, _, _, _ = self._calis(yok=True)
        self.assertEqual(r[0], 'p1')


class MbHedefBayragi(unittest.TestCase):
    """MB hedef cozunurluk bayragi yalniz dijital MB isinde acik; POD ve diger renkler 2400 / kendi yolu."""

    def _is(self, renk, hata=False):
        from unittest.mock import patch
        gorulen = {}

        def sahte_render(ed, *a, **kw):
            gorulen['etkin'] = sd.MB_HEDEF['etkin']
            if hata:
                raise RuntimeError('render')
            return None, {'durum': 'ELLE KONTROL'}, None
        d = Path(tempfile.mkdtemp()); y = d / 'k.jpg'
        Image.new('RGB', (4800, 6000)).save(y)
        with patch.object(sd, 'pod_kaynak', lambda *a: y), patch.object(sd, 'render_et', sahte_render), \
                patch.object(sd, 'EdisyonPoster', lambda: None), patch.object(sd, 'BluePoster', lambda: None):
            sd._dijital_is((renk, '4x5', {'cift': 'CANCER_LEO', 'isim1': 'A', 'isim2': 'B', 'mesaj': 'm',
                                          'sayfa': 1}, d, d))
        return gorulen.get('etkin'), sd.MB_HEDEF['etkin']

    def test_yalniz_mb(self):
        self.assertEqual(self._is('MIDNIGHT_BLUE'), (True, False))
        for r in ('DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY', 'WARM_PARCHMENT'):
            self.assertEqual(self._is(r), (False, False), r)

    def test_hatada_kapanir(self):
        self.assertEqual(self._is('MIDNIGHT_BLUE', hata=True), (True, False))

    def test_pod_yolu_bayragi_acmaz(self):
        self.assertFalse(sd.MB_HEDEF['etkin'])
        import inspect
        self.assertNotIn('MB_HEDEF', inspect.getsource(sd.pod_uret))


if __name__ == '__main__':
    unittest.main()
