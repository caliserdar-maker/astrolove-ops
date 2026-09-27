import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from scripts.medya_v1 import siparis_dosyasi as sd

TEST_DPI = 10          # gercek olcu 300 dpi; test hizli olsun diye ayni oranda kucuk


class _Havuz:
    def __init__(self, **_):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def map(self, fn, isler, chunksize=1):
        return [fn(x) for x in isler]


class _Baglam:
    Pool = _Havuz


def _sahte_is(arg):
    renk, oran, _, klas, _ = arg
    oran = sd.dijital_oran(oran)
    boy = sd.DIJITAL_BOY[oran]
    px = (round(sd.BOY[boy][1] * TEST_DPI), round(sd.BOY[boy][2] * TEST_DPI))
    Image.linear_gradient('L').resize(px).convert('RGB').save(klas / f'ARIES_LEO_{renk}_{oran}_{boy}.jpg', quality=95)
    return renk, oran, {'durum': 'URETILDI', 'kapilar_gecti': True}, None


class DijitalPaketTesti(unittest.TestCase):
    def setUp(self):
        self.sip = {'receipt': 'TEST_E_DIJITAL_ARIES_LEO', 'cift': 'ARIES_LEO',
                    'renk': 'MIDNIGHT_BLUE', 'isim1': 'EMILY', 'isim2': 'JAMES',
                    'mesaj': 'Written in the stars'}

    def _uret(self, kok, islev=_sahte_is, sip=None):
        with patch.object(sd, '_dijital_is', side_effect=islev), \
             patch('multiprocessing.get_context', return_value=_Baglam()), \
             patch.object(sd, 'bant_dogrulama', return_value={'gecti': True}), \
             patch.object(sd, 'DPI', TEST_DPI):
            return sd.dijital_uret(sip or self.sip, None, None, Path(kok))

    def test_bes_renk_bes_oran_ve_test_e_tamam(self):
        with tempfile.TemporaryDirectory() as kok:
            sonuc = self._uret(kok)
            self.assertEqual('URETILDI', sonuc['durum'])
            self.assertEqual(5, sonuc['toplam_pdf'])
            for renk in sd.RENKLER:
                klas = Path(kok) / renk
                self.assertEqual(5, len(list(klas.glob('*.jpg'))))
                self.assertFalse(list(klas.glob('*.zip')))
                rk = sonuc['renkler'][renk]
                self.assertTrue((klas / rk['pdf']).is_file())
                self.assertTrue(rk['pdf_kapisi']['gecti'], rk['pdf_kapisi'])
                self.assertEqual(5, rk['pdf_kapisi']['sayfa_sayisi'])
                self.assertEqual(['16x20', '18x24', '24x36', '11x14', 'A2'],
                                 [x['boy'] for x in rk['pdf_kapisi']['sayfalar']])
                self.assertTrue(all(x['ayni_bayt'] for x in rk['pdf_kapisi']['sayfalar']))
                self.assertIn('a_series', rk['oranlar'])
            self.assertEqual('AstroLove_Aries_Leo_Midnight_Blue.pdf',
                             sonuc['renkler']['MIDNIGHT_BLUE']['pdf'])

    def test_pdf_kapisi_yanlis_dpi_fail(self):
        with tempfile.TemporaryDirectory() as kok:
            sonuc = self._uret(kok, sip={**self.sip, 'yalniz_renk': True})
            rk = sonuc['renkler']['MIDNIGHT_BLUE']
            pdf = Path(kok) / 'MIDNIGHT_BLUE' / rk['pdf']
            sayfalar = [(Path(kok) / 'MIDNIGHT_BLUE' / x.split(' -> ')[0], x.split(' -> ')[1])
                        for x in rk['pdf_icerik']]
            self.assertFalse(sd.pdf_kapisi(pdf, sayfalar, dpi=300)['gecti'])

    def test_eksik_renk_silinir_ve_sonuc_eksik(self):
        def eksik(arg):
            renk, oran, _, klas, _ = arg
            if renk == 'DEEP_BLACK' and oran == '2x3':
                return renk, oran, {'durum': 'HATA', 'hata': 'sahte hata'}, None
            return _sahte_is(arg)

        with tempfile.TemporaryDirectory() as kok:
            sonuc = self._uret(kok, eksik)
            self.assertEqual('EKSIK', sonuc['durum'])
            self.assertFalse((Path(kok) / 'DEEP_BLACK').exists())
            self.assertEqual('sahte hata',
                             sonuc['renkler']['DEEP_BLACK']['oranlar']['2x3']['hata'])

    def test_eski_a_a_series_olur(self):
        with patch.object(sd, 'log') as kayit:
            self.assertEqual('a_series', sd.dijital_oran('A'))
        kayit.assert_called_once()

    def test_tek_renk(self):
        with tempfile.TemporaryDirectory() as kok:
            sip = {**self.sip, 'yalniz_renk': True}
            sonuc = self._uret(kok, sip=sip)
            self.assertEqual(['MIDNIGHT_BLUE'], list(sonuc['renkler']))
            self.assertEqual(5, len(list((Path(kok) / 'MIDNIGHT_BLUE').glob('*.jpg'))))


if __name__ == '__main__':
    unittest.main()
