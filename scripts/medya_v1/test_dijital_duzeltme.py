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

    def test_kutle_yerlesimi_ikinci_sans(self):
        d = Path(tempfile.mkdtemp()); hedef = d / 's.jpg'; hedef.write_bytes(b'ilk')
        gorulen = []

        def yeniden():
            gorulen.append(sd.SATIR_OLCEKLI.get('kutle'))
            g = d / f'_g{len(gorulen)}.jpg'; g.write_bytes(b'k%d' % len(gorulen))
            return 'p%d' % (len(gorulen) + 1), {}, {}, 'b', {}, g
        olc = lambda b, e, p, i: {'gecti': p == 'p3', 'konum_fark_px': 0.5 if p == 'p3' else 1.2, 'kenar_fark_px': 0.4}
        r = sd.olcek_ikinci_deneme('black', 7200, self._ilk(False), yeniden, olc, lambda b, e: {'gecti': True}, hedef)
        self.assertEqual(gorulen, [False, True])
        self.assertEqual(r[0], 'p3'); self.assertEqual(hedef.read_bytes(), b'k2')
        self.assertEqual(r[1]['olcek_kapisi']['yerlesim'], 'olcekli kutle (2400 x k)')
        self.assertFalse(sd.SATIR_OLCEKLI.get('kutle')); self.assertFalse(sd.SATIR_OLCEKLI['etkin'])
        # POD'un kendi ikinci denemesi bu bayragi hic acmaz
        import inspect
        self.assertNotIn("'kutle'", inspect.getsource(sd.pod_uret))

    def test_profil_ucuncu_deneme(self):
        d = Path(tempfile.mkdtemp()); hedef = d / 's.jpg'; hedef.write_bytes(b'ilk')
        gorulen = []

        def yeniden():
            gorulen.append((sd.SATIR_OLCEKLI.get('kutle'), sd.SATIR_OLCEKLI.get('profil_2400')))
            g = d / f'_g{len(gorulen)}.jpg'; g.write_bytes(b'k%d' % len(gorulen))
            return 'p%d' % (len(gorulen) + 1), {}, {}, 'b', {}, g
        olc = lambda b, e, p, i: {'gecti': p == 'p4', 'konum_fark_px': 0.5 if p == 'p4' else 1.5, 'kenar_fark_px': 0.4}
        r = sd.olcek_ikinci_deneme('black', 5400, self._ilk(False), yeniden, olc, lambda b, e: {'gecti': True}, hedef)
        self.assertEqual(gorulen, [(False, False), (True, False), (False, True)])
        self.assertEqual(r[0], 'p4'); self.assertEqual(hedef.read_bytes(), b'k3')
        self.assertEqual(r[1]['olcek_kapisi']['yerlesim'], 'olcekli profil 2400 (2400 x k)')
        self.assertFalse(sd.SATIR_OLCEKLI.get('profil_2400'))
        import inspect
        self.assertIn("if POD_EK_DENEME['etkin']", inspect.getsource(sd.pod_uret))   # POD'da yalniz WP bayragiyla

    def test_pod_ek_deneme_varsayilan_kapali(self):
        self.assertEqual(sd.POD_EK_DENEME, {'etkin': False})
        import inspect
        kaynak = inspect.getsource(sd.pod_uret)
        self.assertIn("POD_EK_DENEME['etkin']", kaynak)               # yalniz bayrak acikken

    def test_profil_kaydi_ve_kullanimi(self):
        """_kaydet profil_2400 iken 2400 profilini kopyalar; _olcekli o profille plaka ister."""
        istenen = []

        class P16:
            NORM_W = 2400
            def d_olcek(self, *a): return 1.0
            def plaka(self, metin, prof, cap, olcek):
                istenen.append(prof)
                from PIL import Image
                return Image.new('RGBA', (10, 10)), 30, 30.0
        Y = sd._SatirYerlesim(P16(), {})
        S = {'prof': {'sol': np.array([1.0, 2.0]), 'sag': np.array([3.0])}}
        Y.asil = lambda s, S_, i, t: (None, {}, {'sol': 5, 'sag': 6}, {'sol': 1, 'sag': 2, 'inf': 3}, None)
        S['oge'] = {'sonsuz': {'gorsel': (0, 0)}}
        sd.SATIR_OLCEKLI['profil_2400'] = True
        try:
            Y._kaydet({}, S, {'sol': 'A', 'sag': 'B'}, '')
        finally:
            sd.SATIR_OLCEKLI['profil_2400'] = False
        self.assertEqual(list(Y.kayit['prof']['sol']), [1.0, 2.0])
        S['prof']['sol'][0] = 9.0                                    # kopya: sonradan degisim etkilemez
        self.assertEqual(Y.kayit['prof']['sol'][0], 1.0)

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



class HizaOnbellek(unittest.TestCase):
    """_HizaBG: ince_hiza'nin tekrar eden plate resize'i bir kez; sonuc piksel piksel ayni (1 Eki hiz)."""

    def test_resize_ayni_ve_tekrar_yok(self):
        from PIL import Image
        rng = np.random.default_rng(1)
        im = Image.fromarray(rng.integers(0, 255, (300, 200, 3), dtype=np.uint8))
        bg = sd._HizaBG(im)
        self.assertIs(bg.convert('RGB'), bg); self.assertEqual((bg.width, bg.height), im.size)
        a = bg.convert('RGB').resize((120, 180), Image.LANCZOS)
        b = bg.convert('RGB').resize((120, 180), Image.LANCZOS)
        self.assertIs(a, b)                                           # ikinci cagri onbellekten
        self.assertEqual(np.asarray(a).tobytes(), np.asarray(im.convert('RGB').resize((120, 180), Image.LANCZOS)).tobytes())
        c = bg.convert('RGB').resize((121, 181), Image.LANCZOS)
        self.assertIsNot(a, c)

    def test_sarma_bir_kez(self):
        import types
        m = types.SimpleNamespace(ince_hiza=lambda ref, bg, kaba, alt=4: (type(bg).__name__, alt))
        sd._hiza_onbellek_kur(m); f = m.ince_hiza; sd._hiza_onbellek_kur(m)
        self.assertIs(m.ince_hiza, f)
        self.assertEqual(m.ince_hiza(None, __import__('PIL.Image').Image.new('RGB', (4, 4)), {}), ('_HizaBG', 4))


if __name__ == '__main__':
    unittest.main()
