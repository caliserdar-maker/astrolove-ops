#!/usr/bin/env python3
"""siparis-dijital plan: cift normalizasyonu + hizli kaynak denetimi (yerel, rclone yok: --ls-json)."""
import base64, json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
import surucu  # noqa: E402


def girdi_yaz(d, **k):
    g = {'receipt': '9000000002', 'cift': 'SAGITTARIUS_CAPRICORN', 'isim1': 'ALI', 'isim2': 'VELI',
         'mesaj_b64': base64.b64encode('Test'.encode()).decode(), 'isler': ''}
    g.update(k)
    p = Path(d) / 'g.json'; p.write_text(json.dumps({'inputs': g})); return p


def tam_liste(cift, r=('MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY'), w=surucu.DIJ_BOYLAR):
    k = surucu.kaynak_listesi(cift, r, w)
    return {'pod': k['pod'], 'plates': k['plates']}


def plan(gjson, ls):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(ls, f)
    env = {**os.environ, 'SIPARIS_GIRDI_JSON': str(gjson)}
    t = time.time()
    p = subprocess.run([sys.executable, str(D / 'plan.py'), '--ls-json', f.name], capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr, time.time() - t


class PlanTesti(unittest.TestCase):
    def test_normalize_ters_cift_ve_isimler(self):
        self.assertEqual(surucu.cift_normalize('SAGITTARIUS_CAPRICORN', 'ALI', 'VELI'),
                         ('CAPRICORN_SAGITTARIUS', 'VELI', 'ALI', True))

    def test_normalize_dogru_ve_ayni_burc(self):
        self.assertEqual(surucu.cift_normalize('CANCER_LEO', 'A', 'B'), ('CANCER_LEO', 'A', 'B', False))
        self.assertEqual(surucu.cift_normalize('LEO_LEO', 'A', 'B'), ('LEO_LEO', 'A', 'B', False))

    def test_girdi_normalize_eder(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ['SIPARIS_GIRDI_JSON'] = str(girdi_yaz(d))
            g = surucu.girdi()
        self.assertEqual((g['cift'], g['isim1'], g['isim2'], g['normalize'], g['cift_girdi']),
                         ('CAPRICORN_SAGITTARIUS', 'VELI', 'ALI', True, 'SAGITTARIUS_CAPRICORN'))

    def test_plan_kaynak_tamam(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out, err, sn = plan(girdi_yaz(d), tam_liste('CAPRICORN_SAGITTARIUS'))
        self.assertEqual(rc, 0, err)
        self.assertIn('cift=CAPRICORN_SAGITTARIUS', out); self.assertIn('normalize=evet', out)
        self.assertIn('wp=["16x20", "18x24", "24x36", "11x14", "A2"]', out)
        self.assertIn('KAYNAK TAMAM', err)

    def test_plan_eksik_kaynak_hizli_fail(self):
        ls = tam_liste('CAPRICORN_SAGITTARIUS')
        ls['pod'].remove('CAPRICORN_SAGITTARIUS/DEEP_BLACK/24x36.jpg'); ls['plates'].remove('VINTAGE_A2.png')
        with tempfile.TemporaryDirectory() as d:
            rc, out, err, sn = plan(girdi_yaz(d), ls)
        self.assertEqual(rc, 1)
        self.assertIn('POD_PRINT/CAPRICORN_SAGITTARIUS/DEEP_BLACK/24x36.jpg', err)
        self.assertIn('PLATES/VINTAGE_A2.png', err)
        self.assertNotIn('renk=', out)                         # matris cikmaz -> isler acilmaz
        self.assertLess(sn, 10)

    def test_plan_ters_girdi_dogru_klasoru_arar(self):
        # klasorler alfabetik: ters girdi normalize edilmeseydi SAGITTARIUS_CAPRICORN/* aranir, hepsi eksik cikardi
        with tempfile.TemporaryDirectory() as d:
            rc, _, err, _ = plan(girdi_yaz(d, cift='SAGITTARIUS_CAPRICORN'), tam_liste('CAPRICORN_SAGITTARIUS'))
        self.assertEqual(rc, 0, err)

    def test_plan_yalniz_paket(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out, err, _ = plan(girdi_yaz(d, isler='paket', cift='CANCER_LIBRA'), {'pod': [], 'plates': []})
        self.assertEqual(rc, 0, err); self.assertIn('renk=[]', out); self.assertIn('normalize=hayir', out)

    def test_plan_mb_referansi_gerekli(self):
        k = surucu.kaynak_listesi('CANCER_LEO', ['MIDNIGHT_BLUE'], [])
        self.assertIn('CANCER_LIBRA/MIDNIGHT_BLUE/24x36.jpg', k['pod'])
        self.assertIn('BLUE_A2.png', k['plates'])


if __name__ == '__main__':
    unittest.main()
