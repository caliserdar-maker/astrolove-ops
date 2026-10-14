"""by78_yayinla: sahte Etsy ile (ag yok). 1 zaten active -> atla, 1 draft -> active, canli listeden ID -> FAIL (istek yok),
yayin sonrasi baslik degisirse FAIL + DUR, PATCH hatasinda yeniden deneme yok + DUR."""
import csv
import importlib.util
import os
import tempfile
import unittest

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("y", os.path.join(D, "by78_yayinla.py"))
y = importlib.util.module_from_spec(sp); sp.loader.exec_module(y)

SHOP = "39729443"


class SahteEtsy:
    def __init__(self, n=78, active=()):
        self.calls, self.remaining = 0, "9000"
        self.L = {}
        for i in range(n):
            lid = str(4600000000 + i)
            self.L[lid] = dict(state="active" if i in active else "draft", shop_id=int(SHOP), title=f"T{i}", tags=[f"a{i}", "b"],
                               url="")
        self.patchler = []
        self.bozuk_baslik = None

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        lid = path.split("/")[2]
        if path.endswith("/inventory"):
            return dict(products=[dict(property_values=[dict(values=["Starlit"]), dict(values=["Digital card 5x7"])],
                                       offerings=[dict(price=dict(amount=500, divisor=100))])])
        return dict(self.L[lid])

    def yayinla(self, lid):
        self.patchler.append(lid)
        self.L[lid]["state"] = "active"
        self.L[lid]["url"] = f"https://www.etsy.com/listing/{lid}/x"
        if lid == self.bozuk_baslik:
            self.L[lid]["title"] = "DEGISTI"


def taslak(api):
    return [dict(cift=f"C{i}", listing_id=lid) for i, lid in enumerate(api.L)]


def oku(t):
    return list(csv.DictReader(open(os.path.join(t, "YAYIN.csv"), encoding="utf-8")))


class Test(unittest.TestCase):
    def test_adet1_atla_ve_yayinla(self):
        api = SahteEtsy(active={0})
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), set(), t, 1, api.yayinla)
            r = oku(t)
        print("\nadet=1:", [(x["cift"], x["once"], x["sonra"], x["sonuc"]) for x in r[:3]], "...", len(r), "satir")
        self.assertEqual(kod, 0)
        self.assertEqual(r[0]["sonuc"], "ATLANDI_ZATEN_ACTIVE")
        self.assertEqual((r[1]["once"], r[1]["sonra"], r[1]["sonuc"]), ("draft", "active", "YAYINLANDI"))
        self.assertTrue(r[1]["url"])
        self.assertEqual(api.patchler, [r[1]["listing_id"]])            # tek yazma
        self.assertTrue(all(x["sonuc"] == "BEKLIYOR" for x in r[2:]))

    def test_adet0_tekrar_kosu(self):
        api = SahteEtsy(active={0, 1})                                   # onceki kosuda 1 yayinlanmis gibi
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), set(), t, 0, api.yayinla)
            r = oku(t)
        print("adet=0 tekrar:", {s: sum(x["sonuc"] == s for x in r) for s in {x["sonuc"] for x in r}}, "PATCH", len(api.patchler))
        self.assertEqual(kod, 0)
        self.assertEqual(len(api.patchler), 76)
        self.assertEqual(sum(x["sonuc"] == "ATLANDI_ZATEN_ACTIVE" for x in r), 2)

    def test_canli_id_hedefte_fail(self):
        api = SahteEtsy()
        kara = {list(api.L)[5]}                                          # canli 78 ilandan biri hedefte
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), kara, t, 0, api.yayinla)
        print("canli ID hedefte: kod", kod, "| Etsy cagrisi", api.calls, "| PATCH", len(api.patchler))
        self.assertEqual(kod, 3)
        self.assertEqual((api.calls, api.patchler), (0, []))

    def test_degisirse_dur(self):
        api = SahteEtsy()
        api.bozuk_baslik = list(api.L)[1]
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), set(), t, 0, api.yayinla)
            r = oku(t)
        print("baslik degisti:", r[-1]["sonuc"], r[-1]["not"], "| PATCH", len(api.patchler))
        self.assertEqual(kod, 4)
        self.assertEqual(len(api.patchler), 2)                           # ikincide durdu
        self.assertEqual(r[-1]["sonuc"], "FAIL")

    def test_patch_hatasi_yeniden_deneme_yok(self):
        api = SahteEtsy()
        n = []

        def hata(lid):
            n.append(lid); raise RuntimeError("PATCH 500")
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), set(), t, 0, hata)
            r = oku(t)
        print("PATCH hatasi:", r[-1]["sonuc"], r[-1]["not"], "| deneme", len(n))
        self.assertEqual((kod, len(n), r[-1]["sonuc"]), (4, 1, "HATA"))


if __name__ == "__main__":
    unittest.main()
