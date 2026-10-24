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
    def __init__(self, desc, inv=None, profil=E.PROFIL_DIJITAL, partner_tutmaz=False, vid_degis=False, patch_hata=False):
        self.inv, self.remaining, self.calls = inv or inv10(), 900, 0
        self.L = {"state": "active", "shop_id": 1, "shipping_profile_id": profil, "listing_type": "physical",
                  "title": "t", "tags": ["a"], "description": html.escape(desc, quote=True).replace("&#x27;", "&#39;"),
                  "materials": ["digital file"], "production_partners": [], "price": {"amount": 390, "divisor": 100},
                  "shop_section_id": E.BOLUM}
        self.v = [(513, sid, 900 + i) for i, (_, sid, _) in enumerate(STIL)]
        self.partner_tutmaz, self.vid_degis, self.patch_hata = partner_tutmaz, vid_degis, patch_hata
        self.sira = []
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
        self.calls += 1; self.remaining -= 1
        if self.patch_hata:
            raise RuntimeError("500 sahte")
        self.patches.append(dict(data)); self.sira.append("patch")
        if "shipping_profile_id" in data:
            self.L["shipping_profile_id"] = data["shipping_profile_id"]
        if "description" in data:
            self.L["description"] = html.escape(data["description"], quote=True).replace("&#x27;", "&#39;")
        if "materials" in data:
            self.L["materials"] = [m.strip() for m in data["materials"].split(",")]
        if "production_partner_ids" in data and not self.partner_tutmaz:
            self.L["production_partners"] = [{"production_partner_id": int(x)} for x in data["production_partner_ids"].split(",")]

    def post_json(self, path, body):
        self.calls += 1; self.remaining -= 1; self.posts.append(body); self.sira.append("post")
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
    assert E.aciklama_plani(ACL)[0] == "YAZ"; ok += 1   # CL/pilot eski teslim satirli: yalniz satir guncellenir
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
    assert len(b["products"]) == 15 and b["readiness_state_on_property"] == [513, 514] and b["sku_on_property"] == [513, 514]
    assert [E.anahtar(p)[1] for p in b["products"][:3]] == ["Digital card 5x7", "Digital file 8x10", "Shipped print 8x10"]
    bs = [p for p in b["products"] if E.anahtar(p)[1] == E.BASKI]
    assert {p["sku"] for p in bs} == {f"BY-ARI_LEO-{k}-PRINT8X10" for _, _, k in STIL}
    assert all(p["offerings"][0] == {"price": 29.0, "quantity": 999, "is_enabled": True, "readiness_state_id": E.HAZIRLIK_BASKI} for p in bs)
    dj = [p for p in b["products"] if E.anahtar(p)[1] != E.BASKI]
    assert all(p["offerings"][0]["readiness_state_id"] == ESKI_HZ and p["property_values"][1]["value_ids"] for p in dj)
    assert api.patches[0].keys() == {"description", "materials", "shipping_profile_id"} and api.patches[1] == {"production_partner_ids": "5817638"}
    assert api.patches[0]["shipping_profile_id"] == E.PROFIL_BASKI == E.PROFIL
    assert r["yazildi"] == ["envanter", "ilan:description+materials+shipping_profile_id", "uretim_ortagi"] and not api.posts; ok += 1
    # 6 tekrar kosu: ZATEN, yalniz 3 GET, yazma yok
    n = api.calls
    r2 = E.ilan(api, "1", "111", True, out)
    assert r2["durum"] == "ZATEN" and api.calls - n == 3 and len(api.puts) == 1; ok += 1
    # 7 pilot bugunku hali: aciklama TAMAM, envanter YAZ (SKU+hazirlik), materials + ortak
    api = Api(html.unescape(ACL).replace("\r\n", "\n"), inv=inv_pilot())
    r = E.ilan(api, "1", "222", True, out)
    assert r["durum"] == "PASS" and r["plan"]["aciklama"] == "YAZ" and r["plan"]["envanter"] == "YAZ", r
    assert api.patches[0].keys() == {"description", "materials", "shipping_profile_id"}
    assert E.SATIR_TESLIM in api.patches[0]["description"] and E.SATIR_TESLIM_ESKI not in api.patches[0]["description"]
    assert all(p["property_values"][1]["value_ids"] == [7777] for p in api.puts[0]["products"] if E.anahtar(p)[1] == E.BASKI); ok += 1
    # 8 yanlis kargo profili -> Dur, yazma yok
    api = Api(A77, profil=318000000000)
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
    assert sorted(x["value_id"] for x in api.posts[0]["variation_images"]) == sorted(sid + 1 for _, sid, _ in STIL)
    assert api.sira[0] == "post", api.sira   # bag onarimi PUT'un hemen ardindan, PATCH'lerden once
    ok += 1
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
    # 15 kota: tahmini istek + 10 alti -> KOTA_BEKLE, yazma yok
    api = Api(A77); api.remaining = 28
    r = E.ilan(api, "1", "901", True, out)
    assert r["durum"].startswith("KOTA_BEKLE") and not api.puts and not api.patches, r; ok += 1
    # 16 PUT sonrasi PATCH istisnasi: disaridan verilen R'de yazilan adim kalir
    api = Api(A77, patch_hata=True)
    R = {"ilan": "902", "yazildi": []}
    try:
        E.ilan(api, "1", "902", True, out, R); raise AssertionError("istisna yok")
    except RuntimeError:
        assert R["yazildi"] == ["envanter"], R; ok += 1
    # 17 hedef profil baski profili ise shipping_profile_id yazilir ve geri okunur
    eski = E.PROFIL
    try:
        E.PROFIL = E.PROFIL_BASKI
        api = Api(A77)
        r = E.ilan(api, "1", "903", True, out)
        assert r["durum"] == "PASS" and api.patches[0]["shipping_profile_id"] == E.PROFIL_BASKI, r
        r = E.ilan(api, "1", "903", True, out)
        assert r["durum"] == "ZATEN"; ok += 1
    finally:
        E.PROFIL = eski
    # 18 yasak: frame ve yalniz AstroLove
    for y in ("fits standard frames", "by AstroLove team"):
        try:
            E.aciklama_plani(html.unescape(A77) + "\n" + y); raise AssertionError(y)
        except E.Dur:
            pass
    assert E.aciklama_plani(A77)[0] == "YAZ"; ok += 1
    # 19 profil adimi: AU ve diger ulkeler 0'a; teslim gunleri ayni; disari kullanan varsa DUR
    class PApi:
        def __init__(self, kullanan_bolum=E.BOLUM):
            self.dest = [{"shipping_profile_destination_id": 10 + i, "destination_country_iso": c, "destination_region": r,
                          "primary_cost": {"amount": u * 100, "divisor": 100}, "secondary_cost": {"amount": u * 100, "divisor": 100},
                          "min_delivery_days": a, "max_delivery_days": b}
                         for i, (c, r, u, a, b) in enumerate([("US", "none", 0, 3, 8), ("", "eu", 0, 5, 12), ("GB", "none", 0, 5, 10),
                                                               ("AU", "none", 5, 5, 10), ("", "none", 12, 7, 21)])]
            self.kb, self.puts = kullanan_bolum, []

        def get(self, path, params=None, ok404=False):
            if path.endswith("/listings"):
                return {"results": [{"listing_id": 5, "shipping_profile_id": E.PROFIL_BASKI, "shop_section_id": self.kb}]
                        if params["state"] == "active" else []}
            return {"title": "BY Print 8x10 Worldwide", "shipping_profile_destinations": copy.deepcopy(self.dest)}

        def put(self, path, data):
            self.puts.append((path, data))
            did = int(path.rsplit("/", 1)[1])
            for x in self.dest:
                if x["shipping_profile_destination_id"] == did:
                    x["primary_cost"] = x["secondary_cost"] = {"amount": data["primary_cost"] * 100, "divisor": 100}
    pa = PApi()
    r = E.profil_adimi(pa, "1", True, out)
    assert sorted(r["degisecek"]) == ["AU", "EVERYWHERE"] and len(pa.puts) == 2
    govdeler = {path.rsplit("/", 1)[1]: d for path, d in pa.puts}
    assert govdeler["13"] == {"primary_cost": 0, "secondary_cost": 0, "min_delivery_days": 5, "max_delivery_days": 10,
                              "destination_country_iso": "AU"}, govdeler
    assert govdeler["14"] == {"primary_cost": 0, "secondary_cost": 0, "min_delivery_days": 7, "max_delivery_days": 21,
                              "destination_region": "none"}, govdeler
    assert all(v[0] == 0 for v in r["sonra"].values()) and r["sonra"]["EVERYWHERE"][2:] == (7, 21)
    E.profil_ucretsiz_mi(pa, "1")
    assert E.profil_adimi(pa, "1", True, out)["degisecek"] == []
    try:
        E.profil_adimi(PApi(kullanan_bolum=123), "1", True, out); raise AssertionError("disari kullanan gecti")
    except SystemExit as e:
        assert "disinda" in str(e)
    try:
        E.profil_ucretsiz_mi(PApi(), "1"); raise AssertionError("ucretli gecti")
    except SystemExit:
        pass
    ok += 1
    # 20 SONUC etiketi: kota -> KOTA, kota disi -> HATA, hepsi iyi -> TAMAM
    se = E.sonuc_etiketi
    assert se([{"durum": "PASS"}], None, True) == "TAMAM"
    assert se([{"durum": "PASS"}, {"durum": "KOTA_BEKLE kalan 12 < 16 + 10 (yazma yok)"}], None, False) == "KOTA"
    assert se([{"durum": "DUR: DUR: kota sert tabani: kalan 9 < 10"}], None, False) == "KOTA"
    assert se([], "SystemExit: DUR: kota esigi: kalan 4 < 10 (kosu baslamadi)", False) == "KOTA"
    assert se([{"durum": "FAIL_DUR: kargo profili 1"}], None, False) == "HATA"
    assert se([{"durum": "DUR: Etsy 400 kotasiz"}], None, False) == "HATA"
    assert se([], "SystemExit: invalid_grant", False) == "HATA"
    assert se([], "SystemExit: HATA: 429 kota. retry-after=7020", False) == "KOTA"
    assert se([], "SystemExit: DUR: kota esigi aktif ama x-remaining-today basligi okunamadi", False) == "HATA"
    assert se([{"durum": "FAIL"}], None, False) == "HATA"
    ok += 1
    # 21 kilit: profil PUT'u yalniz izinle, ulke/bolgeden tam biri
    izin = {"PROFIL"}
    k = E.kilitli(S(), "1", izin)
    yol = f"/shops/1/shipping-profiles/{E.PROFIL_BASKI}/destinations/5"
    taban = {"primary_cost": 0, "secondary_cost": 0, "min_delivery_days": 5, "max_delivery_days": 10}
    for d in (taban, {**taban, "destination_country_iso": "AU", "destination_region": "none"}, {**taban, "title": "x"}):
        try:
            k.put(yol, d); raise AssertionError(f"kilit gecti {d}")
        except SystemExit as e:
            assert "YASAK" in str(e)
    try:
        E.kilitli(S(), "1", set()).put(yol, {**taban, "destination_country_iso": "AU"}); raise AssertionError("izinsiz gecti")
    except SystemExit as e:
        assert "YASAK" in str(e)
    ok += 1
    # 22 teslim satiri guncellemesi: eski satirli tam metin (pilot/CL) -> YAZ, yalniz o satir; sonra TAMAM; yeni metinde eski yok
    eski_metin = d1.replace(E.SATIR_TESLIM, E.SATIR_TESLIM_ESKI)
    assert html.unescape(ACL).replace("\r\n", "\n").count(E.SATIR_TESLIM_ESKI) == 1   # CL orijinalinde eski satir var
    durum, g = E.aciklama_plani(eski_metin)
    assert durum == "YAZ" and g == d1 and E.SATIR_TESLIM_ESKI not in g
    assert E.aciklama_plani(html.unescape(ACL))[0] == "YAZ"
    assert E.aciklama_plani(g) == ("TAMAM", g)
    assert "worldwide" in d1 and "other countries 7 to 21 days" in d1 and "\u2014" not in E.SATIR_TESLIM and "\u2013" not in E.SATIR_TESLIM
    try:
        E.aciklama_plani(eski_metin + "\n" + E.SATIR_TESLIM); raise AssertionError("eski+yeni gecti")
    except E.Dur:
        pass
    ok += 1
    print(f"test_by_baski_ekle: {ok}/22 PASS")


if __name__ == "__main__":
    test()
