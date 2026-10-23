#!/usr/bin/env python3
"""sira=ters (Serdar 23 Eki, siparis basina sol/sag ters): girdi denetimi, isim takasi, yalniz SIPARIS baskisinda sembol
ogesi takasi (kimlik baskisi ve varsayilan degismez). Yerel, ag yok."""
import base64, json, os, sys, tempfile, types, unittest
from pathlib import Path

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
import surucu  # noqa: E402


def girdi(**k):
    g = {'receipt': '9000000002', 'cift': 'LIBRA_TAURUS', 'isim1': 'ALI', 'isim2': 'VELI',
         'mesaj_b64': base64.b64encode('Test'.encode()).decode(), 'isler': 'wp:11x14', 'tek_olcu': '11x14'}
    g.update(k)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump({'inputs': g}, f)
    os.environ['SIPARIS_GIRDI_JSON'] = f.name
    return surucu.girdi()


def sahte():
    """oran_kur: her cagrida YENI S (gercek oran_kur gibi); baski: render 2 kez (2400 + hedef) oran_kur cagirir."""
    eu = types.SimpleNamespace(kayit=[])

    def oran_kur(ed, oran, kilit, o):
        S = {'oge': {'sembol_sol': {'ad': 'LIBRA_GLIF', 'gorsel': (100, 50, 140, 90)},
                     'sembol_sag': {'ad': 'TAURUS_GLIF', 'gorsel': (300, 50, 340, 90)},
                     'sonsuz': {'ad': 'BIRLESIK'}}, 'temiz_a': 'TEMIZ'}
        eu.kayit.append(S)
        return {'s': 1}, S
    eu.oran_kur = oran_kur
    wo = types.SimpleNamespace()

    def baski(x, *q, **k):
        return [eu.oran_kur('modern', '4:5', None, None)[1] for _ in range(2)]
    wo.baski = baski
    return wo, eu


class Sira(unittest.TestCase):
    def test_varsayilan_bos(self):
        g = girdi()
        self.assertEqual(g['sira'], '')
        x = surucu.sira_isim({'isim1': 'ALI', 'isim2': 'VELI'}, g)
        self.assertEqual((x['isim1'], x['isim2']), ('ALI', 'VELI'))

    def test_ters_isim_takas(self):
        g = girdi(sira='ters')
        self.assertEqual((g['isim1'], g['isim2']), ('ALI', 'VELI'))          # girdi anlami degismez (1./2. burcun ismi)
        x = surucu.sira_isim({'isim1': g['isim1'], 'isim2': g['isim2']}, g)
        self.assertEqual((x['isim1'], x['isim2']), ('VELI', 'ALI'))          # sol = 2. burc (TAURUS) ismi

    def test_ters_alfabetik_normalize_ile(self):
        g = girdi(sira='ters', cift='TAURUS_LIBRA', isim1='VELI', isim2='ALI')   # ters girilen cift: once normalize
        self.assertEqual((g['cift'], g['isim1'], g['isim2']), ('LIBRA_TAURUS', 'ALI', 'VELI'))
        x = surucu.sira_isim({'isim1': g['isim1'], 'isim2': g['isim2']}, g)
        self.assertEqual((x['isim1'], x['isim2']), ('VELI', 'ALI'))

    def test_gecersiz_sira_ve_is(self):
        for k in ({'sira': 'TERSx'}, {'sira': 'ters', 'isler': 'renk:DEEP_BLACK'}, {'sira': 'ters', 'isler': ''},
                  {'sira': 'ters', 'isler': 'wp:11x14,renk:DEEP_BLACK'}):
            with self.assertRaises(SystemExit, msg=str(k)):
                girdi(**k)
        self.assertEqual(girdi(sira='TERS')['sira'], 'ters')

    def test_renk_sayfa_asamasi_ters_ret(self):
        g = {'sira': 'ters'}
        for f in (surucu.renk_asamasi, surucu.sayfa_asamasi):
            with self.assertRaises(SystemExit):
                f(types.SimpleNamespace(), g)

    def test_yalniz_siparis_baskisinda_takas(self):
        wo, eu = sahte()
        say = surucu.sira_ters_kur(wo, eu)
        kim = wo.baski({'receipt': 'WPK_LIBRA_TAURUS_11x14_CHAMPAGNE_IVORY_kimlik'})
        sip = wo.baski({'receipt': 'WPK_LIBRA_TAURUS_11x14_CHAMPAGNE_IVORY_siparis'})
        for S in kim:                                                       # kimlik: kaynakla birebir
            self.assertEqual((S['oge']['sembol_sol']['ad'], S['oge']['sembol_sag']['ad']), ('LIBRA_GLIF', 'TAURUS_GLIF'))
        for S in sip:                                                       # siparis: sol = TAURUS glifi (kendi gorsel kutusuyla)
            self.assertEqual((S['oge']['sembol_sol']['ad'], S['oge']['sembol_sag']['ad']), ('TAURUS_GLIF', 'LIBRA_GLIF'))
            self.assertEqual(S['oge']['sembol_sol']['gorsel'], (300, 50, 340, 90))
            self.assertEqual(S['oge']['sonsuz']['ad'], 'BIRLESIK')            # birlesik sembol ayni oge (aynalama yok)
            self.assertEqual(S['temiz_a'], 'TEMIZ')
        for S in eu.kayit:                                                  # oran_kur sonucu yerinde degismedi
            self.assertEqual(S['oge']['sembol_sol']['ad'], 'LIBRA_GLIF')
        self.assertEqual((say['takas'], say['takassiz']), (2, 2))
        self.assertFalse(say['etkin'])
        wo.baski({'receipt': 'X_kimlik'})                                    # siparisten sonra yine takassiz
        self.assertEqual((say['takas'], say['takassiz']), (2, 4))

    def test_hata_sonrasi_bayrak_iner(self):
        _, eu = sahte()
        def patla(*q, **k):
            raise RuntimeError('render hatasi')
        wo = types.SimpleNamespace(baski=patla)
        say = surucu.sira_ters_kur(wo, eu)
        with self.assertRaises(RuntimeError):
            wo.baski({'receipt': 'Y_siparis'})
        self.assertFalse(say['etkin'])

if __name__ == '__main__':
    unittest.main(verbosity=1)
