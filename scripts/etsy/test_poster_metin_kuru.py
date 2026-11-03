#!/usr/bin/env python3
"""poster_metin_kuru testi (sahte Etsy; ag yok). Canli metin ornegi: CANCER_LIBRA (scripts/etsy/testdata_poster_cancer_libra.json,
3 Kas 19:24 UTC canli okuma; musteri verisi yok). Kullanim: python3 scripts/etsy/test_poster_metin_kuru.py -> SONUC n/n PASS."""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
import poster_metin_kuru as P  # noqa: E402

D = json.loads((pathlib.Path(__file__).with_name("testdata_poster_cancer_libra.json")).read_text())
LID = "4570143815"
BOY = ["5×7″ (13×18cm)"] + list(P.K.BOYLAR)
sonuc = []


def k(ad, kosul, ayr=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + ("" if kosul else f"  [{ayr}]"))


class Sahte:
    def __init__(self, desc=None, boy=None, ru_batch=True):
        self.calls, self.remaining, self.yol = 0, 900, []
        self.desc, self.boy, self.ru_batch = desc or D["description"], boy or BOY, ru_batch

    def kota_kapisi(self, ne=""):
        pass

    def get(self, path, params=None, ok404=False):
        self.calls += 1; self.yol.append(path)
        ru = dict(language="ru", title=D["ru"]["title"], description=D["ru"]["description"], tags=D["ru"]["tags"])
        if path == "/listings/batch":
            x = dict(listing_id=int(LID), state="active", title=D["title"], description=self.desc, tags=D["tags"], images=[{"listing_image_id": 1, "rank": 1}])
            if self.ru_batch:
                x["translations"] = {"ru": ru}
            return {"results": [x]}
        if path.endswith("/inventory"):
            return {"products": [{"property_values": [{"property_id": 513, "values": [b]}], "offerings": [{"price": {"amount": 1990, "divisor": 100}}]} for b in self.boy]}
        if path.endswith("/translations/ru"):
            return ru
        raise AssertionError(path)


with tempfile.TemporaryDirectory() as d:
    out = pathlib.Path(d)
    a = Sahte(); P.calis(a, "1", [LID], {LID: "CANCER_LIBRA"}, out)
    p = json.loads((out / "ONCE_SONRA.json").read_text())[LID]
    k("canli metin: PASS, 2 EN + 2 RU satir degisir", not p["hata"] and len(p["en_fark"]) == 4 and len(p["ru_fark"]) == 4, p["hata"])
    k("EN sonra: premium / long-lasting / free preview yok, 300 dpi kalir", not any(x in p["en_sonra"].lower() for x in ("premium", "long-lasting", "free preview"))
      and "300 dpi" in p["en_sonra"] and "- Printed on matte art paper\n" in p["en_sonra"])
    k("Soru 11 cumlesi birebir", "We send a preview via Etsy Messages within 24 hours. After you approve, your file is emailed to you within 24 hours." in p["en_sonra"])
    k("RU sonra: premialnoy / stoykimi / besplatno maket yok", not any(x in p["ru_sonra"] for x in ("преми", "стойк", "бесплатно отправляем")))
    k("kapi uyari 0, HTML varligi yok", p["kapi_uyari"] == 0 and "&#39;" not in p["en_sonra"])
    k("istek: 1 batch + 1 envanter (RU batch'ten)", a.calls == 2 and a.yol == ["/listings/batch", f"/listings/{LID}/inventory"], a.yol)
    y = json.loads((out / "YEDEK.json").read_text())[LID]
    k("yedek: baslik, etiket, ru, gorsel, fiyat", y["title"] == D["title"] and y["ru"]["title"] and y["gorsel"] == [1] and y["fiyatlar"] == [19.9])
    k("boylar: 14 (5x7 dahil)", p["boylar"][0] == "5x7" and len(p["boylar"]) == 14, p["boylar"])
    b = Sahte(ru_batch=False); P.calis(b, "1", [LID], {LID: "X"}, out / "b")
    k("RU batch'te yoksa tekil GET", b.calls == 3)
    try:
        P.calis(Sahte(desc=D["description"].replace("- Printed on premium matte art paper with long-lasting inks", "- Printed on premium paper")), "1", [LID], {LID: "X"}, out / "c"); dur = False
    except SystemExit:
        dur = "eslesmesi 0" in (out / "c" / "FARK.csv").read_text()
    k("beklenmeyen canli metin: FAIL + DUR", dur)
    try:
        P.calis(Sahte(boy=BOY[:13]), "1", [LID], {LID: "X"}, out / "e"); dur = False
    except SystemExit:
        dur = True
    k("envanter boylari metinle uyusmazsa FAIL", dur)
    class Api:
        def _call(self, *a, **kw):
            return {}
    api = Api(); P.K.salt_okur(api)
    try:
        api._call("PATCH", "/x"); dur = False
    except SystemExit:
        dur = True
    k("salt okur: yazma cagrisi DUR", dur)
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
