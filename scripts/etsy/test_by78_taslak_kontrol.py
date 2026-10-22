"""by78_taslak_kontrol: sahte Etsy yanitlariyla 1 dogru (PASS) + 1 bozuk (FAIL) ilan. Ag erisimi yok."""
import copy
import csv
import importlib.util
import io
import os
import tempfile
import unittest

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("k", os.path.join(D, "by78_taslak_kontrol.py"))
k = importlib.util.module_from_spec(sp); sp.loader.exec_module(k)

METIN = """cift,grup,baslik,etiket_1,etiket_2,etiket_3,etiket_4,etiket_5,etiket_6,etiket_7,etiket_8,etiket_9,etiket_10,etiket_11,etiket_12,etiket_13,aciklama
CANCER_LIBRA,A,"1st Anniversary Gift for Husband, Personalized Cancer Libra Zodiac Couple Print",t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,t13,"A gift with ""your names"" and your date.
Second line."
LEO_LEO,B,"1 Year Anniversary Gift for Boyfriend, Personalized Leo Leo Zodiac Couple Print",u1,u2,u3,u4,u5,u6,u7,u8,u9,u10,u11,u12,u13,"Leo and Leo text."
"""


def ilan(lid, m, cift):
    a, b = (p.capitalize() for p in cift.split("_"))
    l1, l2 = ("Name on the left", "Name on the right") if a == b else (f"Name under {a}", f"Name under {b}")
    vid = {s: 1000 + i for i, s in enumerate(k.STYLES)}
    prods = [dict(property_values=[dict(property_id=513, values=[s], value_ids=[vid[s]]), dict(property_id=514, values=[f], value_ids=[1])],
                  offerings=[dict(price=dict(amount=int(p * 100), divisor=100), quantity=999, is_enabled=True)])
             for s in k.STYLES for f, p in k.FIYAT.items()]
    ims = [dict(rank=1, listing_image_id=1, full_width=2400, full_height=2400)] + \
          [dict(rank=r, listing_image_id=r, full_width=3200, full_height=2400) for r in range(2, 9)] + \
          [dict(rank=r, listing_image_id=r, full_width=2400, full_height=3000) for r in range(9, 14)]
    return {
        f"/listings/{lid}": dict(state="draft", title=m["baslik"], tags=[m[f"etiket_{i}"] for i in range(1, 14)],
                                 description=m["aciklama"].replace('"', "&quot;"), shop_section_id=k.SECTION, shipping_profile_id=k.SHIP,
                                 return_policy_id=k.RET, taxonomy_id=k.TAX, processing_min=4, processing_max=7,
                                 production_partners=[dict(production_partner_id=k.PARTNER)], who_made="i_did", when_made="made_to_order"),
        f"/listings/{lid}/images": dict(results=ims),
        f"/listings/{lid}/inventory": dict(products=prods),
        f"/listings/{lid}/videos": dict(results=[dict(video_id=int(lid))]),
        f"/shops/1/listings/{lid}/variation-images": dict(results=[dict(property_id=513, value_id=vid[s], value=s, image_id={"Starlit": 9, "Timeless": 10, "First Page": 11, "Layers": 13, "Botanical": 12}[s])
                                                                     for i, s in enumerate(k.STYLES)]),
        f"/listings/{lid}/personalization": dict(personalization_questions=[
            dict(question_text=t, required=r, max_allowed_characters=n) for t, r, n in
            [(l1, True, 11), (l2, True, 11), ("Your special date", True, 20), ("Heading", True, 20), ("Optional short line", False, 20)]]),
        f"/shops/1/listings/{lid}/properties": dict(results=[dict(property_name="Occasion")]),
    }


class SahteApi:
    calls, remaining = 0, 9999

    def __init__(self, y):
        self.y = y

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        return copy.deepcopy(self.y.get(path))


class Test(unittest.TestCase):
    def test_pass_fail(self):
        M = list(csv.DictReader(io.StringIO(METIN)))
        y = ilan("111", M[0], "CANCER_LIBRA")
        bozuk = ilan("222", M[1], "LEO_LEO")
        bozuk["/listings/222"]["state"] = "active"
        bozuk["/listings/222"]["description"] = "Leo and Leo text — changed."
        bozuk["/listings/222/images"]["results"][0].update(full_width=2400, full_height=3000)   # eski dikey kapak artik FAIL
        bozuk["/listings/222/videos"]["results"] = []
        bozuk["/listings/222/inventory"]["products"][2]["offerings"][0]["price"] = dict(amount=2500, divisor=100)
        bozuk["/listings/222/inventory"]["products"][4]["offerings"][0]["is_enabled"] = False
        bozuk["/shops/1/listings/222/variation-images"]["results"][1]["image_id"] = 9
        bozuk["/shops/1/listings/222/variation-images"]["results"][3]["image_id"] = 1   # Layers eski kapaga bagli
        bozuk["/listings/222/personalization"]["personalization_questions"][0]["question_text"] = "Name under Leo"
        bozuk["/shops/1/listings/222/properties"]["results"].append(dict(property_name="Holiday"))
        y.update(bozuk)
        taslak = [dict(cift="CANCER_LIBRA", listing_id="111"), dict(cift="LEO_LEO", listing_id="222")]
        with tempfile.TemporaryDirectory() as t:
            ok = k.calistir(SahteApi(y), "1", taslak, M, t)
            rows = list(csv.DictReader(open(os.path.join(t, "KONTROL.csv"))))
            print("\nKONTROL.csv:"); [print(" ", r["cift"], r["sonuc"], r["neden"][:400]) for r in rows]
        self.assertFalse(ok)                                    # 78 degil + 1 FAIL
        self.assertEqual(rows[0]["sonuc"], "PASS", rows[0]["neden"])
        self.assertEqual(rows[1]["sonuc"], "FAIL")
        for parca in ("state active", "aciklama farkli", "uzun/orta tire", "1. gorsel 2400x2400 (kare kapak) degil", "fiyat", "kapali urun 1",
                      "stil gorselleri ayni degil", "stil bag sirasi", "Layers=1", "video 0 (1 olmali)", "kisisellestirme", "Holiday"):
            self.assertIn(parca, rows[1]["neden"])


class TestHafif(unittest.TestCase):
    def test_hafif(self):
        tas = [dict(cift="CANCER_LIBRA", listing_id="111")] + [dict(cift=f"C{i}_X", listing_id=str(200 + i)) for i in range(77)]
        def il(lid, kapak=(2400, 2400), video=1, state="draft"):
            ims = [dict(rank=1, full_width=kapak[0], full_height=kapak[1])] + [dict(rank=r, full_width=3200, full_height=2400) for r in range(2, 9)] + \
                  [dict(rank=r, full_width=2400, full_height=3000) for r in range(9, 14)]
            return dict(listing_id=int(lid), state=state, images=ims, videos=[dict(video_id=1)] * video)
        res = {t["listing_id"]: il(t["listing_id"]) for t in tas}
        res["200"] = il("200", kapak=(2400, 3000))                      # eski dikey kapak
        res["201"] = il("201", video=0)                                 # video yok
        res["202"] = il("202", state="active")
        class Api:
            calls, remaining = 0, 600
            def get(self, path, params=None, ok404=False):
                self.calls += 1
                assert path == "/listings/batch" and params["includes"] == "images,videos"
                return dict(results=[res[i] for i in params["listing_ids"].split(",") if i in res])
        bag = [dict(cift=t["cift"], listing_id=t["listing_id"], sonuc="TAMAM", bag=k.BAG_METIN) for t in tas[1:]]
        bag[5]["bag"] = "Starlit=9 Timeless=10 First Page=11 Botanical=12 Layers=1"   # C5_X bag hatali
        cl = {"ilan": {"CANCER_LIBRA": {"listing_id": 111, "sonuc": "PASS", "bag_sonra": {
            "Starlit": [1, 9], "Timeless": [2, 10], "First Page": [3, 11], "Botanical": [4, 12], "Layers": [5, 13]}}}}
        api = Api()
        with tempfile.TemporaryDirectory() as t:
            ok, sonuc = k.hafif_calistir(api, tas, bag, cl, t)
        self.assertEqual(api.calls, 1)
        self.assertFalse(ok)
        fail = {x["cift"]: x["neden"] for x in sonuc if x["sonuc"] == "FAIL"}
        self.assertEqual(set(fail), {"C0_X", "C1_X", "C2_X", "C5_X"}, fail)
        self.assertIn("rank 1 2400x3000", fail["C0_X"]); self.assertIn("video 0", fail["C1_X"])
        self.assertIn("state active", fail["C2_X"]); self.assertIn("Layers=1", fail["C5_X"])
        self.assertEqual(sum(x["sonuc"] == "PASS" for x in sonuc), 74)


if __name__ == "__main__":
    unittest.main()
