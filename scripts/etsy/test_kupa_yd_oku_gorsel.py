#!/usr/bin/env python3
"""kupa_yd_oku.py gorsel modu testi (Serdar madde 113). Ag bastan kapali (TEST AGI kurali); Etsy sahte nesneyle taklit edilir.
Bilinen PASS: 78 ilan, her birinde gorsel -> rc 0, CSV satir sayisi = gorsel toplami, rank 1 ilk satir, alanlar dogru sutunda,
tek istek, kota kapisi cagrildi; main(--mod gorsel) CSV yazar. Rank boslugu / None ve SKU sorunu: rc 0, CSV yazilir, OZET'te listelenir.
Bilinen FAIL: Drive listesi depodan farkli (eksik id ya da ayni id farkli cift) ya da tekrarli, depo 78 degil (Etsy istegi yok),
0 gorselli ilan, yanitta olmayan ilan, bos URL (570xN ya da fullxfull) -> rc 1 / DUR. Dosya adi tarihi TR (UTC+3)."""
import csv
import json
import os
import socket
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket = _ag_yok
socket.create_connection = _ag_yok
urllib.request.urlopen = _ag_yok

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kupa_yd_oku as K  # noqa: E402

DEPO = K.DEPO_LISTE


def depo():
    with open(DEPO, encoding="utf-8") as f:
        return {r["listing_id"]: r["pair"] for r in csv.DictReader(f)}


class SahteApi:
    def __init__(self, sonuc):
        self.sonuc, self.calls, self.remaining, self.istekler, self.kapi = sonuc, 0, None, [], 0

    def kota_kapisi(self, ne=""):
        self.kapi += 1

    def _call(self, method, path, params=None, **k):
        self.calls += 1
        self.remaining = "5000"
        self.istekler.append((method, path, dict(params or {})))
        ids = params["listing_ids"].split(",")
        return {"results": [self.sonuc[i] for i in ids if i in self.sonuc]}

    def get(self, path, params=None, ok404=False):
        return self._call("GET", path, params=params)


def ilan(lid, pair, n=3, state="active"):
    on = K.sku_ailesi(pair)[:-1]
    return {"listing_id": int(lid), "state": state, "skus": [f"{on}01-15", f"{on}01-11"],
            "images": [{"rank": r, "url_fullxfull": f"https://i.etsystatic.com/x/il_fullxfull.{lid}{r}.jpg",
                        "url_570xN": f"https://i.etsystatic.com/x/il_570xN.{lid}{r}.jpg", "alt_text": f"alt {r}"}
                       for r in range(n, 0, -1)]}


def hepsi():
    return {k: ilan(k, v) for k, v in depo().items()}


class Test(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.drive = self.d / "drive.csv"
        self.yaz_drive(list(depo().items()))

    def yaz_drive(self, satirlar):
        with open(self.drive, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["cift", "listing_id"])
            for k, v in satirlar:
                w.writerow([v, k])

    def kos(self, sonuc):
        api = SahteApi(sonuc)
        rc = K.gorsel(api, self.drive, self.d, tarih="20261116")
        return rc, api

    def ozet(self):
        return json.loads((self.d / "KUPA78_IMAGE_OZET.json").read_text())

    def test_depo_listesi(self):
        m = depo()
        self.assertEqual((len(m), len(set(m.values()))), (78, 78))

    def test_pass(self):
        rc, api = self.kos(hepsi())
        self.assertEqual(rc, 0)
        self.assertEqual((api.calls, api.kapi), (1, 1))
        self.assertEqual(api.istekler[0][1], "/listings/batch")
        self.assertEqual(api.istekler[0][2]["includes"], "Images")
        with open(self.d / "KUPA78_IMAGE_URLS_20261116.csv", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(list(rows[0]), K.GORSEL_SUTUN)
        self.assertEqual(len(rows), 78 * 3)
        r0 = rows[0]
        self.assertEqual((r0["listing_id"], r0["pair"], r0["image_rank"]), ("4598542826", "AQUARIUS_AQUARIUS", "1"))
        self.assertEqual(r0["url_fullxfull"], "https://i.etsystatic.com/x/il_fullxfull.45985428261.jpg")
        self.assertEqual(r0["url_570xN"], "https://i.etsystatic.com/x/il_570xN.45985428261.jpg")
        self.assertEqual(r0["alt_text"], "alt 1")
        self.assertEqual(r0["sku"], "KUPA-AQUARIUS_AQUARIUS-01-11;KUPA-AQUARIUS_AQUARIUS-01-15")
        self.assertEqual([r["image_rank"] for r in rows[:3]], ["1", "2", "3"])
        oz = self.ozet()
        self.assertEqual((oz["farkli_ilan_csv"], oz["gorsel_toplam"]), (78, 234))

    def test_main_gorsel(self):
        sahte = SahteApi(hepsi())

        class Store:
            def __init__(self, *a):
                pass

            def needs_refresh(self):
                return False

        eski = (K.E.TokenStore, K.E.Etsy)
        K.E.TokenStore, K.E.Etsy = Store, lambda store: sahte
        os.environ.update(TOKEN_FILE="x", ETSY_SHOP_ID="1", ETSY_API_KEY="k", ETSY_SHARED_SECRET="s")
        try:
            rc = K.main(["--mod", "gorsel", "--kupa-liste", str(self.drive), "--out", str(self.d)])
        finally:
            K.E.TokenStore, K.E.Etsy = eski
        self.assertEqual(rc, 0)
        self.assertTrue(list(self.d.glob("KUPA78_IMAGE_URLS_*.csv")))
        self.assertEqual(json.loads((self.d / "ISTEK.json").read_text())["toplam"], 1)
        with self.assertRaises(SystemExit):
            sahte.post("/x", {})

    def test_sku_uzun_cift(self):
        self.assertEqual(K.sku_ailesi("SAGITTARIUS_SAGITTARIUS"), "KUPA-SAG_SAG-*")

    def test_drive_farkli_istek_yok(self):
        m = list(depo().items())[1:]
        self.yaz_drive(m)
        api = SahteApi({})
        with self.assertRaises(SystemExit):
            K.gorsel(api, self.drive, self.d, tarih="20261116")
        self.assertEqual(api.calls, 0)

    def test_drive_tekrar_istek_yok(self):
        m = list(depo().items())
        self.yaz_drive(m + m[:1])
        api = SahteApi({})
        with self.assertRaises(SystemExit):
            K.gorsel(api, self.drive, self.d, tarih="20261116")
        self.assertEqual(api.calls, 0)

    def ilk_bozuk(self, f):
        s = hepsi()
        k0 = next(iter(s))
        f(s, k0)
        return self.kos(s)[0], k0

    def test_sifir_gorsel_fail(self):
        rc, k0 = self.ilk_bozuk(lambda s, k: s[k].update(images=[]))
        self.assertEqual(rc, 1)
        self.assertEqual(self.ozet()["sifir_gorsel"], [k0])

    def test_eksik_ilan_fail(self):
        rc, _ = self.ilk_bozuk(lambda s, k: s.pop(k))
        self.assertEqual(rc, 1)

    def test_bos_url_fail(self):
        rc, _ = self.ilk_bozuk(lambda s, k: s[k]["images"][0].update(url_570xN=""))
        self.assertEqual(rc, 1)

    def satirlar(self, lid):
        with open(self.d / "KUPA78_IMAGE_URLS_20261116.csv", encoding="utf-8") as f:
            return [r for r in csv.DictReader(f) if r["listing_id"] == lid]

    def test_rank_bosluk_listelenir(self):
        # images[0] rank 3 -> 7: ranklar [7, 2, 1]
        rc, k0 = self.ilk_bozuk(lambda s, k: s[k]["images"][0].update(rank=7))
        self.assertEqual(rc, 0)
        self.assertEqual(self.ozet()["rank_hata"], [[k0, [7, 2, 1]]])
        self.assertEqual([r["image_rank"] for r in self.satirlar(k0)], ["1", "2", "7"])
        self.assertEqual(self.ozet()["gorsel_toplam"], 234)

    def test_rank_none_listelenir(self):
        rc, k0 = self.ilk_bozuk(lambda s, k: s[k]["images"][0].update(rank=None))
        self.assertEqual(rc, 0)
        self.assertEqual(self.ozet()["rank_hata"], [[k0, [None, 2, 1]]])
        self.assertEqual([r["image_rank"] for r in self.satirlar(k0)], ["1", "2", ""])

    def test_sku_yok_listelenir(self):
        rc, k0 = self.ilk_bozuk(lambda s, k: s[k].update(skus=[]))
        self.assertEqual(rc, 0)
        self.assertEqual(self.ozet()["sku_hata"], [[k0, []]])
        self.assertEqual({r["sku"] for r in self.satirlar(k0)}, {""})

    def test_sku_onek_listelenir(self):
        rc, k0 = self.ilk_bozuk(lambda s, k: s[k].update(skus=["KUPA-ARIES_LEO-01-11"]))
        self.assertEqual(rc, 0)
        self.assertEqual(self.ozet()["sku_hata"], [[k0, ["KUPA-ARIES_LEO-01-11"]]])
        self.assertEqual(len(self.satirlar(k0)), 3)

    def test_pass_ozet_bos(self):
        rc, _ = self.kos(hepsi())
        self.assertEqual(rc, 0)
        oz = self.ozet()
        self.assertEqual((oz["rank_hata"], oz["sku_hata"], oz["sifir_gorsel"], oz["yanitta_yok"], oz["bos_url"]), ([], [], [], [], 0))

    def test_bos_url_full_fail(self):
        rc, _ = self.ilk_bozuk(lambda s, k: s[k]["images"][1].update(url_fullxfull=""))
        self.assertEqual(rc, 1)
        self.assertEqual(self.ozet()["bos_url"], 1)

    def test_drive_ayni_id_farkli_cift_istek_yok(self):
        m = list(depo().items())
        m[0], m[1] = (m[0][0], m[1][1]), (m[1][0], m[0][1])
        self.yaz_drive(m)
        api = SahteApi({})
        with self.assertRaises(SystemExit):
            K.gorsel(api, self.drive, self.d, tarih="20261116")
        self.assertEqual(api.calls, 0)

    def test_depo_78_degil_istek_yok(self):
        m = list(depo().items())[1:]
        dp = self.d / "depo77.csv"
        with open(dp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["listing_id", "pair"])
            w.writerows(m)
        self.yaz_drive(m)
        api = SahteApi({})
        with self.assertRaises(SystemExit):
            K.gorsel(api, self.drive, self.d, depo=dp, tarih="20261116")
        self.assertEqual(api.calls, 0)

    def test_tr_tarih(self):
        utc = K.datetime.timezone.utc
        self.assertEqual(K.tr_tarih(K.datetime.datetime(2026, 11, 16, 22, 30, tzinfo=utc)), "20261117")
        self.assertEqual(K.tr_tarih(K.datetime.datetime(2026, 11, 16, 20, 59, tzinfo=utc)), "20261116")

    def test_aktif_degil_listelenir(self):
        rc, k0 = self.ilk_bozuk(lambda s, k: s[k].update(state="inactive"))
        self.assertEqual(rc, 0)
        self.assertEqual(self.ozet()["aktif_degil"], [[k0, "inactive"]])


if __name__ == "__main__":
    unittest.main()
