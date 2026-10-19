"""kupa_eski_sil: sahte Etsy ile kapilar (state/baslik/koru) ve tek silme. Ag erisimi yok."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kupa_eski_sil as s  # noqa: E402

SHOP = "39729443"


class Sahte(s.Kilit):
    def __init__(self, ilanlar, sil_kod=204):
        self.ilanlar, self.sil_kod, self.silinen = ilanlar, sil_kod, []
        self.calls, self.remaining = 0, "4000"

    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        if method != "GET":
            raise SystemExit(f"YASAK yazma: {method} {path}")
        self.calls += 1
        return self.ilanlar.get(int(path.rsplit("/", 1)[1]))

    def sil(self, lid):
        if lid != s.SIL:
            raise SystemExit("YASAK")
        self.silinen.append(lid)
        if self.sil_kod in (200, 204):
            self.ilanlar.pop(lid, None)
        return self.sil_kod, ""


def ilanlar(state="draft", baslik=s.BASLIK, koru="draft"):
    return {s.SIL: dict(listing_id=s.SIL, shop_id=int(SHOP), state=state, title=baslik),
            s.KORU: dict(listing_id=s.KORU, shop_id=int(SHOP), state=koru, title=s.BASLIK)}


class Test(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())

    def test_pass(self):
        api = Sahte(ilanlar())
        R = s.calistir(api, SHOP, self.out, bekle=0)
        self.assertEqual(R["sonuc"], "PASS")
        self.assertEqual(api.silinen, [s.SIL])
        self.assertIn(s.KORU, api.ilanlar)

    def test_kapilar_silmez(self):
        for kw in (dict(state="active"), dict(baslik="Baska baslik"), dict(koru="active")):
            api = Sahte(ilanlar(**kw))
            with self.assertRaises(SystemExit):
                s.calistir(api, SHOP, self.out, bekle=0)
            self.assertEqual(api.silinen, [], kw)

    def test_yok_ise_silmez(self):
        api = Sahte({s.KORU: ilanlar()[s.KORU]})
        with self.assertRaises(SystemExit):
            s.calistir(api, SHOP, self.out, bekle=0)
        self.assertEqual(api.silinen, [])

    def test_baska_ilan_ve_yazma_yasak(self):
        api = Sahte(ilanlar())
        for f in (lambda: s.Kilit.sil(api, s.KORU), lambda: api.delete(f"/listings/{s.KORU}"),
                  lambda: api.patch(f"/shops/1/listings/{s.KORU}", {"state": "active"})):
            with self.assertRaises(SystemExit):
                f()

    def test_silinemezse_fail(self):
        api = Sahte(ilanlar(), sil_kod=403)
        with self.assertRaises(SystemExit):
            s.calistir(api, SHOP, self.out, bekle=0)
        self.assertIn(s.SIL, api.ilanlar)


if __name__ == "__main__":
    unittest.main()
