#!/usr/bin/env python3
"""by_baski_ekle v2 yerel testi (sahte Etsy). Veri: canli 77 ilan yapisi (ARIES_LEO 4595363435 ONCE.json, 24 Eki;
fiyatlar 24 Eki sonrasi 3.90/4.90) + canli aciklama testdata_by_aciklama_77.txt + CL orijinali testdata_by_aciklama_cl.txt."""
import copy
import html
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import by_baski_ekle as E  # noqa: E402

D = Path(__file__).resolve().parent
A77 = html.unescape((D / "testdata_by_aciklama_77.txt").read_text(encoding="utf-8"))  # canli API metni (varlik kodlu) cozulmus
ACL = (D / "testdata_by_aciklama_cl.txt").read_text(encoding="utf-8")
STIL = [("Starlit", 138126211616, "STARLIT"), ("Timeless", 108763733183, "TIMELESS"), ("First Page", 176794359732, "FIRSTPAGE"),
        ("Layers", 108661364507, "LAYERS"), ("Botanical", 101440971797, "BOTANICAL")]
FMT = [("Digital card 5x7", 1523008985108, "CARD5X7", 390), ("Digital file 8x10", 1046101489652, "FILE8X10", 490)]
ESKI_HZ = 1512772362964


def urun(st, sid, kod, fm, fid, fkod, fiyat, hz=ESKI_HZ, sku=None):
    return {"sku": sku if sku is not None else f"BY-ARI_LEO-{kod}-{fkod}", "is_deleted": False,
            "offerings": [{"quantity": 999, "is_enabled": True, "is_deleted": False,
                           "price": {"amount": fiyat, "divisor": 100, "currency_code": "USD"}, "readiness_state_id": hz}],
            "property_values": [{"property_id": 513, "property_name": "Style", "value_ids": [sid], "values": [st]},
                                {"property_id": 514, "property_name": "Format", "value_ids": [fid], "values": [fm]}]}


def inv10():
    return {"products": [urun(st, sid, k, fm, fid, fk, f) for st, sid, k in STIL for fm, fid, fk, f in FMT],
            "price_on_property": [513, 514], "quantity_on_property": [], "sku_on_property": [513, 514],
            "readiness_state_on_property": []}


def inv_pilot():
    """Pilot 4595350971 bugunku hali: baski 29, SKU bos, hazirlik dijitalden kopya (v1 yazimi)."""
    pr = []
    for st, sid, k in STIL:
        pr += [urun(st, sid, k, fm, fid, fk, f) for fm, fid, fk, f in FMT]
        pr.append(urun(st, sid, k, "Shipped print 8x10", 7777, "PRINT8X10", 2900, sku=""))
    return {"products": pr, "price_on_property": [513, 514], "quantity_on_property": [], "sku_on_property": [513, 514],
            "readiness_state_on_property": []}


class Api:
    def __init__(self, desc, inv=None, profil=E.PROFIL, partner_tutmaz=False, vid_degis=False):
        self.inv, self.remaining, self.calls = inv or inv10(), 900, 0
        self.L = {"state": "active", "shop_id": 1, "shipping_profile_id": profil, "listing_type": "physical",
                  "title": "t", "tags": ["a"], "description": html.escape(desc, quote=True).replace("&#x27;", "&#39;"),
                  "materials": ["digital file"], "production_partners": [], "price": {"amount": 390, "divisor": 100},
                  "shop_section_id": E.BOLUM}
        self.v = [(513, sid, 900 + i) for i, (_, sid, _) in enumerate(STIL)]
        self.partner_tutmaz, self.vid_degis = partner_tutmaz, vid_degis
        self.puts, self.patches, self.posts = [], [], []

    def get(self, path, params=None, ok404=False):
        self.calls += 1; self.remaining -= 1
        if path.endswith("/inventory"):
            return copy.deepcopy(self.inv)
        if path.endswith("/variation-images"):
            return {"results": [{"property_id": p, "value_id": v, "image_id": i} for p, v, i in self.v]}
        return copy.deepcopy(self.L)

    def put_json(self, path, body):
        self.calls += 1; self.remaining -= 1; self.puts.append(copy.deepcopy(body))
        yeni = []
        for p in body["products"]:
            q = copy.deepcopy(p)
            for v in q["property_values"]:
                if not v.get("value_ids"):
                    v["value_ids"] = [5000 + len(yeni)]
                if self.vid_degis and v["property_id"] == 513:
                    v["value_ids"] = [v["value_ids"][0] + 1]
            q["is_deleted"] = False
            o = q["offerings"][0]
            o["price"] = {"amount": int(round(o["price"] * 100)), "divisor": 100}
            o["is_deleted"] = False
            yeni.append(q)
        self.inv = {**{k: body[k] for k in body if k != "products"}, "products": yeni}
        if self.vid_degis:
            self.v = []

    def patch(self, path, data):
        self.calls += 1; self.remaining -= 1; self.patches.append(dict(data))
        if "description" in data:
            self.L["description"] = html.escape(data["description"], quote=True).replace("&#x27;", "&#39;")
        if "materials" in data:
            self.L["materials"] = [m.strip() for m in data["materials"].split(",")]
        if "production_partner_ids" in data and not self.partner_tutmaz:
            self.L["production_partners"] = [{"production_partner_id": int(x)} for x in data["production_partner_ids"].split(",")]

    def post_json(self, path, body):
        self.calls += 1; self.remaining -= 1; self.posts.append(body)
        self.v = [(x["property_id"], x["value_id"], x["image_id"]) for x in body["variation_images"]]


def test():
    E.BEKLE_SN = 0
    out = Path(tempfile.mkdtemp())
    ok = 0
    # 1 canli 77 metni: YAZ; 4 parca tam 1 kez; ikinci kez TAMAM
    d0 = html.unescape(A77)
    durum, d1 = E.aciklama_plani(A77)
    assert durum == "YAZ" and d1 != d0
    for parca in (E.DEGIS[0][1], E.DEGIS[1][1], E.SATIR_TESLIM, E.SATIR_FORMAT):
        assert d1.count(parca) == 1, parca
    assert E.aciklama_plani(d1) == ("TAMAM", d1); ok += 1
    # 2 yeni metin = CL orijinali yapisi (DELIVERY/FORMATS satir sirasi)
    sl = d1.split("\n")
    assert sl[sl.index("- Digital card and digital file: sent in Etsy Messages as soon as you approve your preview.") + 1] == E.SATIR_TESLIM
    assert sl[sl.index("- Digital file 8x10: an 8x10 inch, 300 dpi JPG for your own printing. Nothing is shipped.") + 1] == E.SATIR_FORMAT
    assert E.aciklama_plani(ACL)[0] == "TAMAM"; ok += 1
    # 3 kismi metin -> Dur
    kismi = d0.replace(E.DEGIS[0][0], E.DEGIS[0][1])
    try:
        E.aciklama_plani(kismi); raise AssertionError("kismi gecti")
    except E.Dur:
        ok += 1
    # 4 yasak ifade (tam liste) -> Dur
    for y in ("printed by Printful", "308 gsm paper", "100% cotton", "museum quality", "OBA-free", "bright white",
              "12-colour", "lasts 100 to 200 years", "instant download", "a — b", "Hahnemühle"):
        try:
            E.aciklama_plani(d0 + "\n" + y); raise AssertionError(f"yasak gecti: {y}")
        except E.Dur:
            pass
    ok += 1
    # 5 yeni 77 ilan: yaz PASS; govde 15 urun, baski SKU/hazirlik/rd_on; materials + aciklama + ortak
    api = Api(A77)
    r = E.ilan(api, "1", "111", True, out)
    assert r["durum"] == "PASS", r
    b = api.puts[0]
    assert len(b["products"]) == 15 and b["readiness_state_on_property"] == [514] and b["sku_on_property"] == [513, 514]
    assert [E.anahtar(p)[1] for p in b["products"][:3]] == ["Digital card 5x7", "Digital file 8x10", "Shipped print 8x10"]
    bs = [p for p in b["products"] if E.anahtar(p)[1] == E.BASKI]
    assert {p["sku"] for p in bs} == {f"BY-ARI_LEO-{k}-PRINT8X10" for _, _, k in STIL}
    assert all(p["offerings"][0] == {"price": 29.0, "quantity": 999, "is_enabled": True, "readiness_state_id": E.HAZIRLIK_BASKI} for p in bs)
    dj = [p for p in b["products"] if E.anahtar(p)[1] != E.BASKI]
    assert all(p["offerings"][0]["readiness_state_id"] == ESKI_HZ and p["property_values"][1]["value_ids"] for p in dj)
    assert api.patches[0].keys() == {"description", "materials"} and api.patches[1] == {"production_partner_ids": "5817638"}
    assert r["yazildi"] == ["envanter", "ilan:description+materials", "uretim_ortagi"] and not api.posts; ok += 1
    # 6 tekrar kosu: ZATEN, yalniz 3 GET, yazma yok
    n = api.calls
    r2 = E.ilan(api, "1", "111", True, out)
    assert r2["durum"] == "ZATEN" and api.calls - n == 3 and len(api.puts) == 1; ok += 1
    # 7 pilot bugunku hali: aciklama TAMAM, envanter YAZ (SKU+hazirlik), materials + ortak
    api = Api(html.unescape(ACL).replace("\r\n", "\n"), inv=inv_pilot())
    r = E.ilan(api, "1", "222", True, out)
    assert r["durum"] == "PASS" and r["plan"]["aciklama"] == "TAMAM" and r["plan"]["envanter"] == "YAZ", r
    assert api.patches[0].keys() == {"materials"}
    assert all(p["property_values"][1]["value_ids"] == [7777] for p in api.puts[0]["products"] if E.anahtar(p)[1] == E.BASKI); ok += 1
    # 8 yanlis kargo profili -> Dur, yazma yok
    api = Api(A77, profil=318080539024)
    try:
        E.ilan(api, "1", "333", True, out); raise AssertionError("profil gecti")
    except E.Dur:
        assert not api.puts and not api.patches; ok += 1
    # 9 oku modu: PLAN_OK, yazma yok
    api = Api(A77)
    r = E.ilan(api, "1", "444", False, out)
    assert r["durum"] == "PLAN_OK" and not api.puts and not api.patches; ok += 1
    # 10 PUT stil value_id'lerini degistirir + baglar kaybolur: ada gore yeni id'lerle geri yazilir
    api = Api(A77, vid_degis=True)
    r = E.ilan(api, "1", "555", True, out)
    assert r["durum"] == "PASS" and r["onarim"] == "ada gore geri yazildi" and "value_id" in r.get("not", ""), r
    assert sorted(x["value_id"] for x in api.posts[0]["variation_images"]) == sorted(sid + 1 for _, sid, _ in STIL); ok += 1
    # 11 ortak tutmazsa geri okuma FAIL
    api = Api(A77, partner_tutmaz=True)
    r = E.ilan(api, "1", "666", True, out)
    assert r["durum"] == "FAIL" and any("uretim ortagi" in h for h in r["hatalar"]); ok += 1
    # 12 dijital fiyat beklenmedik -> Dur
    inv = inv10(); inv["products"][0]["offerings"][0]["price"]["amount"] = 500
    try:
        E.ilan(Api(A77, inv=inv), "1", "777", True, out); raise AssertionError("fiyat gecti")
    except E.Dur:
        ok += 1
    # 13 FILE8X10 SKU sablon disi -> Dur
    inv = inv10(); inv["products"][1]["sku"] = "X"
    try:
        E.ilan(Api(A77, inv=inv), "1", "888", True, out); raise AssertionError("sku gecti")
    except E.Dur:
        ok += 1
    # 14 kilitli sinif: izin disi yazma istek gondermeden durur
    import etsy_common

    class S:
        api_key_header = "x"; access_token = None
    izin = set()
    k = E.kilitli(S(), "1", izin)
    for f, a in ((k.put_json, ("/listings/9/inventory", {})), (k.patch, ("/shops/1/listings/9", {"description": "d"})),
                 (k.post_json, ("/shops/1/listings/9/variation-images", {})), (k.delete, ("/x",))):
        try:
            f(*a); raise AssertionError("kilit gecti")
        except SystemExit as e:
            assert "YASAK" in str(e)
    izin.add("9")
    try:
        k.patch("/shops/1/listings/9", {"title": "x"}); raise AssertionError("baslik gecti")
    except SystemExit as e:
        assert "YASAK" in str(e)
    assert etsy_common; ok += 1
    print(f"test_by_baski_ekle: {ok}/14 PASS")


if __name__ == "__main__":
    test()
