"""by78_yayinla (az istekli surum, 15 Eki): sahte Etsy ile (ag yok).
1 zaten active -> atla, 1 draft -> active; istek sayisi (adet=1: 3, 76 yayin: 1 + 76 + 8 = 85); canli listeden ID -> FAIL (istek yok);
PATCH yanitinda baslik degisirse -> inactive + geri_alindi + DUR; toplu dogrulamada url yoksa -> geri_alindi + DUR;
PATCH hatasinda yeniden deneme yok + DUR; baska magaza -> yazmadan DUR; kota < 500 -> DUR."""
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
            self.L[lid] = dict(listing_id=int(lid), state="active" if i in active else "draft", shop_id=int(SHOP), title=f"T{i}",
                               tags=[f"a{i}", "b"], url=f"https://www.etsy.com/listing/{lid}/x" if i in active else "")
        self.patchler = []
        self.gets = []
        self.bozuk_baslik = None
        self.url_yok = None
        self.kota_dus = None

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        self.gets.append(path)
        assert path == "/listings/batch", path                     # tek okuma yolu: toplu
        ids = params["listing_ids"].split(",")
        assert len(ids) <= 100
        return dict(results=[dict(self.L[i]) for i in ids if i in self.L])

    def durum(self, lid, state):
        self.calls += 1
        self.patchler.append((lid, state))
        self.L[lid]["state"] = state
        if state == "active":
            self.L[lid]["url"] = "" if lid == self.url_yok else f"https://www.etsy.com/listing/{lid}/x"
            if lid == self.bozuk_baslik:
                self.L[lid]["title"] = "DEGISTI"
        if self.kota_dus is not None and len(self.patchler) >= self.kota_dus:
            self.remaining = "9"
        return dict(self.L[lid])                                   # PATCH yaniti = guncel ilan


def taslak(api):
    return [dict(cift=f"C{i}", listing_id=lid) for i, lid in enumerate(api.L)]


def oku(t):
    return list(csv.DictReader(open(os.path.join(t, "YAYIN.csv"), encoding="utf-8")))


class Test(unittest.TestCase):
    def test_adet1_atla_ve_yayinla_3_istek(self):
        api = SahteEtsy(active={0})
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), set(), t, 1, api.durum)
            r = oku(t)
        print("\nadet=1:", [(x["cift"], x["once"], x["sonra"], x["sonuc"]) for x in r[:3]], "...", len(r), "satir | istek", api.calls)
        self.assertEqual(kod, 0)
        self.assertEqual(r[0]["sonuc"], "ATLANDI_ZATEN_ACTIVE")
        self.assertEqual((r[1]["once"], r[1]["sonra"], r[1]["sonuc"]), ("draft", "active", "YAYINLANDI"))
        self.assertTrue(r[1]["url"])
        self.assertEqual(api.patchler, [(r[1]["listing_id"], "active")])   # tek yazma
        self.assertTrue(all(x["sonuc"] == "BEKLIYOR" for x in r[2:]))
        self.assertEqual((api.calls, len(api.gets)), (3, 2))                # 1 toplu + 1 PATCH + 1 toplu dogrulama

    def test_adet0_tekrar_kosu_istek_sayisi(self):
        api = SahteEtsy(active={0, 1})                                   # onceki kosuda 1 yayinlanmis gibi
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), set(), t, 0, api.durum)
            r = oku(t)
        print("adet=0 tekrar:", {s: sum(x["sonuc"] == s for x in r) for s in {x["sonuc"] for x in r}},
              "PATCH", len(api.patchler), "GET", len(api.gets), "istek", api.calls)
        self.assertEqual(kod, 0)
        self.assertEqual(len(api.patchler), 76)
        self.assertEqual(sum(x["sonuc"] == "ATLANDI_ZATEN_ACTIVE" for x in r), 2)
        self.assertEqual(len(api.gets), 1 + 8)                           # 1 toplu + ceil(76/10) dogrulama
        self.assertEqual(api.calls, 85)

    def test_canli_id_hedefte_fail(self):
        api = SahteEtsy()
        kara = {list(api.L)[5]}                                          # canli 78 ilandan biri hedefte
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), kara, t, 0, api.durum)
        print("canli ID hedefte: kod", kod, "| Etsy cagrisi", api.calls, "| PATCH", len(api.patchler))
        self.assertEqual(kod, 3)
        self.assertEqual((api.calls, api.patchler), (0, []))

    def test_patch_yaniti_degisirse_dur(self):
        api = SahteEtsy()
        api.bozuk_baslik = list(api.L)[1]
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), set(), t, 0, api.durum)
            r = oku(t)
        lid = list(api.L)[1]
        print("baslik degisti:", [(x["cift"], x["once"], x["sonra"], x["sonuc"]) for x in r[-2:]], "| PATCH", api.patchler[-2:])
        self.assertEqual(kod, 4)
        self.assertEqual(api.patchler, [(list(api.L)[0], "active"), (lid, "active"), (lid, "inactive")])   # ikincide geri alip durdu
        self.assertEqual((r[-2]["sonuc"], r[-1]["sonuc"], r[-1]["sonra"]), ("FAIL", "geri_alindi", "inactive"))
        self.assertEqual(api.L[lid]["state"], "inactive")
        self.assertEqual(len(r), 3)                                      # sonraki ilanlara gecilmedi
        self.assertEqual(len(api.gets), 1)                               # PATCH yaniti ile yakalandi, ek okuma yok

    def test_toplu_dogrulamada_url_yoksa_geri_al(self):
        api = SahteEtsy()
        lid = api.url_yok = list(api.L)[3]
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), set(), t, 0, api.durum)
            r = oku(t)
        print("URL yok:", [(x["cift"], x["sonra"], x["sonuc"], x["not"]) for x in r[-2:]], "| PATCH", len(api.patchler))
        self.assertEqual((kod, r[-1]["sonuc"], api.L[lid]["state"]), (4, "geri_alindi", "inactive"))
        self.assertEqual(api.patchler[-1], (lid, "inactive"))
        self.assertEqual(len([p for p in api.patchler if p[1] == "active"]), 10)   # 10'luk grup dogrulamasinda yakalandi
        self.assertEqual(len(api.gets), 2)

    def test_patch_hatasi_yeniden_deneme_yok(self):
        api = SahteEtsy()
        n = []

        def hata(lid, state):
            n.append((lid, state)); raise RuntimeError("PATCH 500")
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), set(), t, 0, hata)
            r = oku(t)
        print("PATCH hatasi:", r[-1]["sonuc"], r[-1]["not"], "| deneme", len(n))
        self.assertEqual((kod, len(n), r[-1]["sonuc"]), (4, 1, "HATA"))

    def test_baska_magaza_yazmadan_dur(self):
        api = SahteEtsy()
        api.L[list(api.L)[7]]["shop_id"] = 1
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), set(), t, 0, api.durum)
        self.assertEqual((kod, api.patchler, len(api.gets)), (4, [], 1))

    def test_kota_tabani(self):
        api = SahteEtsy()
        api.kota_dus = 5                                                 # 5. PATCH'ten sonra kota 9 (taban 10)
        with tempfile.TemporaryDirectory() as t:
            kod = y.calistir(api, SHOP, taslak(api), set(), t, 0, api.durum)
        print("kota tabani: PATCH", len(api.patchler), "kod", kod)
        self.assertEqual((kod, len(api.patchler)), (4, 5))


if __name__ == "__main__":
    unittest.main()
