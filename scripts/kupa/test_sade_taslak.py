#!/usr/bin/env python3
"""sade_taslak.py sahte Etsy testleri (ag yok). Kosu: python3 scripts/kupa/test_sade_taslak.py <kupa_orchard/ilan klasoru>
Klasorde SADE12_SEO_ONERI.csv ve SADE12_METIN.csv olmali (kupa-orchard 0cc17aa5)."""
import copy
import hashlib
import json
import os
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sade_taslak as st  # noqa: E402

ILAN = Path(sys.argv[1])
SHOP = "39729443"
SONUC = []


def ok(ad, kosul, bilgi=""):
    SONUC.append((ad, bool(kosul)))
    print(("PASS " if kosul else "FAIL ") + ad + (f" | {bilgi}" if bilgi and not kosul else ""))


SABLON_L = dict(listing_id=st.SABLON, state="draft", title="eski cift kupa", description="x", taxonomy_id=1062,
                shipping_profile_id=318301958420, return_policy_id=1513990287785, who_made="i_did", when_made="made_to_order",
                is_supply=False, should_auto_renew=True, is_taxable=True, is_customizable=True, materials=["Ceramic"],
                production_partners=[dict(production_partner_id=5817638)], shop_section_id=60980873, language="en-US",
                processing_min=4, processing_max=7, item_weight=None, styles=[])
SABLON_INV = dict(products=[dict(sku="KUPA-X", property_values=[dict(property_id=513, property_name="Style", values=["Orange Blossom"]),
                                                                  dict(property_id=514, property_name="Size", values=["11 oz"])],
                                 offerings=[dict(price=dict(amount=2400, divisor=100), quantity=999, readiness_state_id=1517641240112)])])
SABLON_PROPS = [dict(property_id=200, property_name="Primary color", value_ids=[10], values=["White"]),
                dict(property_id=46803063641, property_name="Occasion", value_ids=[32], values=["Birthday"])]


class Sim:
    def __init__(self, kota=500, bolum_var=False, aktif_adim=None, olustur_kod=201):
        self.kota, self.n, self.yazma = kota, 0, []
        self.secs = [dict(shop_section_id=60980873, title="Zodiac Couple Mugs")]
        if bolum_var:
            self.secs.append(dict(shop_section_id=777, title=st.BOLUM_AD))
        self.L, self.inv, self.ims, self.vids, self.vis, self.per, self.props = None, None, [], [], [], [], {}
        self.aktif_adim, self.olustur_kod, self.drafts = aktif_adim, olustur_kod, []
        self.patchler, self.alt_bozuk, self.dil_farkli, self.yayin_gorsel_sil = [], False, False, False

    def say(self):
        self.n += 1; self.kota -= 1
        return str(self.kota)

    def call(self, api, method, path, params=None, data=None, ok404=False, json_body=None):
        api._istek_oncesi()
        api.calls += 1
        api.remaining = self.say()
        if method != "GET":
            self.yazma.append((method, path))
        s, lid = SHOP, api.lid
        if method == "GET":
            if path == f"/shops/{s}":
                return {}
            if path == f"/listings/{st.SABLON}":
                inc = (params or {}).get("includes", "")
                if any(x.strip().lower() not in ("images", "shop", "user", "translations", "videos", "personalization", "buyerprice")
                       for x in inc.split(",") if x.strip()):   # gercek Etsy 1 Kas: 400 Invalid value (inventory)
                    raise SystemExit(f"HATA: GET {path} -> 400: includes {inc}")
                return copy.deepcopy(SABLON_L)
            if path == f"/listings/{st.SABLON}/inventory":
                return copy.deepcopy(SABLON_INV)
            if path == f"/shops/{s}/listings/{st.SABLON}/properties":
                return dict(results=copy.deepcopy(SABLON_PROPS))
            if path == f"/listings/{st.SABLON}/personalization":
                return dict(personalization_questions=[])
            if path == f"/shops/{s}/sections":
                return dict(results=self.secs)
            if path == f"/shops/{s}/listings":
                st_ = (params or {}).get("state")
                r = [x for x in self.drafts if x.get("state", "draft") == st_]
                if self.L and self.L.get("state") == st_:
                    r.append(dict(listing_id=self.L["listing_id"], title=self.L["title"], state=st_))
                return dict(results=r)
            if path == f"/listings/{lid}":
                return copy.deepcopy(self.L)
            if path == f"/listings/{lid}/inventory":
                return self.inv or dict(products=[])
            if path == f"/listings/{lid}/images":
                return dict(results=self.ims)
            if path == f"/listings/{lid}/videos":
                return dict(results=self.vids)
            if path == f"/listings/{lid}/personalization":
                return dict(personalization_questions=self.per)
            if path == f"/shops/{s}/listings/{lid}/properties":
                return dict(results=list(self.props.values()))
            if path == f"/shops/{s}/listings/{lid}/variation-images":
                return dict(results=self.vis)
            raise AssertionError(f"sim GET {path}")
        if method == "PATCH" and path == f"/shops/{s}/listings/{lid}":
            self.patchler.append(data)
            self.L["state"] = data["state"]
            if self.yayin_gorsel_sil:
                self.ims = self.ims[:-1]
            return copy.deepcopy(self.L)
        if path == f"/shops/{s}/sections":
            self.secs.append(dict(shop_section_id=888, title=data["title"]))
            return self.secs[-1]
        if path == f"/listings/{lid}/inventory":
            stil, urun = {}, []
            for p in json_body["products"]:
                pv = []
                for v in p["property_values"]:
                    vid = stil.setdefault(v["values"][0], 5000 + len(stil)) if v["property_id"] == 513 else 6000
                    pv.append(dict(v, value_ids=[vid]))
                o = p["offerings"][0]
                urun.append(dict(sku=p["sku"], property_values=pv, offerings=[dict(o, price=dict(amount=round(o["price"] * 100), divisor=100))]))
            self.inv = dict(products=urun)
            self._aktif("2")
            return self.inv
        if path.endswith("/variation-images"):
            self.vis = json_body["variation_images"]; return dict(results=self.vis)
        if path.endswith("/personalization"):
            self.per = json_body["personalization_questions"]; return json_body
        if "/properties/" in path:
            pid = int(path.rsplit("/", 1)[1])
            self.props[pid] = dict(property_id=pid, property_name={46803063641: "Occasion"}.get(pid, "x"), value_ids=[int(x) for x in data["value_ids"].split(",")],
                                   values=data["values"].split(","))
            return self.props[pid]
        raise AssertionError(f"sim {method} {path}")

    def _aktif(self, adim):
        if self.aktif_adim == adim:
            self.L["state"] = "active"

    def post_file(self, api, path, files, data=None, tekrar=1):
        st.ai_beyan_kapisi("POST", path, data)
        api._istek_oncesi()
        api.calls += 1; api.remaining = self.say(); self.yazma.append(("POST", path))
        if path.endswith("/images"):
            rk = int(data["rank"])
            self.ims.append(dict(rank=rk, listing_image_id=800000 + rk, full_width=2000, full_height=2000, alt_text=data["alt_text"] + (" x" if self.alt_bozuk and rk == 3 else "")))
            return self.ims[-1]
        self.vids.append(dict(video_id=900001, video_state="active"))
        return self.vids[-1]

    def olustur(self, api, shop, body):
        api._izin("POST", f"/shops/{shop}/listings")
        st.ai_beyan_kapisi("POST", f"/shops/{shop}/listings", data=body)
        api._istek_oncesi()
        api.calls += 1; api.remaining = self.say(); self.yazma.append(("POST", "create"))
        if self.olustur_kod != 201:
            return self.olustur_kod, None, "hata"
        self.L = dict(listing_id=4700000001, state="draft", title=body["title"], description=body["description"],
                      tags=body["tags"].split(","), who_made=body["who_made"], when_made=body["when_made"], taxonomy_id=body["taxonomy_id"],
                      materials=body["materials"].split(","), shipping_profile_id=body["shipping_profile_id"],
                      return_policy_id=body["return_policy_id"], shop_section_id=body["shop_section_id"],
                      production_partners=[dict(production_partner_id=int(body["production_partner_ids"]))],
                      is_supply=False, should_auto_renew=True, is_taxable=True, is_customizable=True, language="en-US",
                      processing_min=4, processing_max=7, item_weight=None, styles=[])
        if self.dil_farkli:
            self.L["language"] = "de"
        self.body = body
        return 201, dict(listing_id=4700000001), ""


def api_kur(sim):
    a = st.Kilitli.__new__(st.Kilitli)
    st.Etsy.__init__.__globals__  # noqa: B018
    a.store = type("S", (), dict(api_key_header="k", access_token="t", needs_refresh=lambda self, *x: False))()
    a.calls, a.remaining, a.lid = 0, None, None
    a._kilit, a._yenile_kilit, a._yerel = threading.Lock(), threading.Lock(), threading.local()
    a._son = a._sira = a._kabul = a._yanit = 0
    a.esik, a.sert_taban = st.KOTA_SINIRI, st.KOTA_SINIRI
    a._kapi_bakildi, a.pace, a.verbose_quota = False, 0, False
    a._bel_hazir()
    st.Etsy._call = lambda self, m, p, params=None, data=None, ok404=False, json_body=None: sim.call(self, m, p, params, data, ok404, json_body)
    st.Etsy.post_file = lambda self, p, files, data=None, tekrar=3: sim.post_file(self, p, files, data, tekrar)
    a.taslak_olustur = lambda shop, body: sim.olustur(a, shop, body)
    return a


def ortam(td, bozuk=False):
    img = Path(td) / "img" / "ARIES"; img.mkdir(parents=True)
    gl, vid = st.dosyalar("ARIES")
    man = []
    for i, ad in enumerate(gl + [vid]):
        (img / ad).write_bytes(f"veri {i} {ad}".encode())
        h = hashlib.sha256((img / ad).read_bytes()).hexdigest()
        if "_K0" not in ad:                               # kartlar manifestte yok (gercek durum)
            man.append(f"{'0' * 64 if bozuk and i == 7 else h}\tARIES/{ad}")
    (Path(td) / "MAN.tsv").write_text("\n".join(man) + "\n")
    os.environ.update(SEO_CSV=str(ILAN / "SADE12_SEO_ONERI.csv"), METIN_CSV=str(ILAN / "SADE12_METIN.csv"),
                      IMG_ROOT=str(Path(td) / "img"), MANIFEST=str(Path(td) / "MAN.tsv"))
    out = Path(td) / "out"; out.mkdir()
    return out


def kos(sim, out, burclar=("ARIES",), yayinla=False):
    a = api_kur(sim)
    try:
        return st.kos(a, SHOP, out, list(burclar), yayinla=yayinla), a, None
    except SystemExit as e:
        return None, a, e


# T1 tam akis
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim()
    rc, a, e = kos(sim, out)
    R = json.load(open(out / "SADE_TASLAK_ARIES.json"))
    ok("T1 rc 0", rc == 0, str(e))
    ok("T1 tum kontroller PASS", all(R["kontrol"].values()), [k for k, v in R["kontrol"].items() if not v])
    ok("T1 PATCH/DELETE yok", not [y for y in sim.yazma if y[0] in ("PATCH", "DELETE")])
    ok("T1 sablona yazma yok", not [y for y in sim.yazma if str(st.SABLON) in y[1]])
    ok("T1 bolum olusturuldu (yoktu)", ("POST", f"/shops/{SHOP}/sections") in sim.yazma and R["kontrol"][f"bolum {st.BOLUM_AD}"])
    ok("T1 sablon yedegi yazildi", (out / f"SABLON_{st.SABLON}.json").exists())
    ok("T1 fiyat 12.90 ilk govde, processing yok", sim.body["price"] == 12.90 and "processing_min" not in sim.body)
    ok("T1 SKU bos", all(p["sku"] == "" for p in sim.inv["products"]))
    ok("T1 istek <= PAY", sim.n <= st.PAY, f"istek {sim.n}")
    print(f"     istek {sim.n} | yazma {len(sim.yazma)} | elle {R['serdar_elle_girecek']}")
    ok("T1 elle girilecek: styles / language farki yok", R["serdar_elle_girecek"] == {})
    # T2 ikinci kosu ikinci ilan acmaz
    sim.yazma.clear()
    D = json.load(open(out / "DURUM.json")); ok("T2 DURUM tamam", "ARIES" in D["tamam"])
    rc2, *_ = kos(sim, out)
    ok("T2 ikinci kosuda yazma yok (tamam atlanir)", rc2 == 0 and [y for y in sim.yazma if y[1] == "create"] == [])

# T3 state active -> DUR, PATCH yok
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim(aktif_adim="2")
    rc, a, e = kos(sim, out)
    ok("T3 active -> SystemExit(2)", e is not None and e.code == 2, str(e))
    ok("T3 sonra gorsel yuklenmedi, PATCH yok", not sim.ims and not [y for y in sim.yazma if y[0] == "PATCH"])

# T4 kota payi
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim(kota=st.PAY + st.KOTA_SINIRI + 2)
    rc, a, e = kos(sim, out)
    ok("T4 pay yetmez -> rc 4, create yok", rc == 4 and not [y for y in sim.yazma if y[1] == "create"], f"rc {rc} e {e}")

# T5 sha manifest farkli -> DUR, create yok
with tempfile.TemporaryDirectory() as td:
    out = ortam(td, bozuk=True); sim = Sim()
    rc, a, e = kos(sim, out)
    ok("T5 sha FARKLI -> DUR", e is not None and "sha" in str(e) and not [y for y in sim.yazma if y[1] == "create"], str(e))

# T6 izin: PATCH, DELETE, sablon, baska bolum
a = api_kur(Sim()); a.lid = 4700000001
for ad, f in (("PATCH", lambda: a.patch(f"/shops/{SHOP}/listings/4700000001", {"state": "inactive"})),
              ("DELETE", lambda: a.delete(f"/listings/4700000001/images/1")),
              ("sablon PUT", lambda: a._izin("PUT", f"/listings/{st.SABLON}/inventory")),
              ("baska bolum", lambda: a._izin("POST", f"/shops/{SHOP}/sections", {"title": "Baska"})),
              ("updateListing PATCH yolu", lambda: a._izin("PATCH", f"/shops/{SHOP}/listings/4700000001"))):
    try:
        f(); ok(f"T6 {ad} engellendi", False)
    except SystemExit as e:
        ok(f"T6 {ad} engellendi", "YASAK" in str(e), str(e))

# T7 bolum varsa olusturulmaz; create 400 -> DUR ve ikinci deneme yok
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim(bolum_var=True, olustur_kod=400)
    rc, a, e = kos(sim, out)
    ok("T7 bolum varken POST sections yok", ("POST", f"/shops/{SHOP}/sections") not in sim.yazma)
    ok("T7 create 400 -> DUR, tek create", e is not None and len([y for y in sim.yazma if y[1] == "create"]) == 1, str(e))

# T9 salt okuma: hic yazma yok, bolum olusturulmaz, OKU.json
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim()
    a9 = api_kur(sim)
    a9._izin = lambda m, p, d=None: (_ for _ in ()).throw(SystemExit(f"YASAK (salt okuma): {m} {p}"))
    rc9 = st.kos(a9, SHOP, out, ["ARIES"], salt_oku=True)
    O = json.load(open(out / "OKU.json"))
    ok("T9 salt okuma rc 0, yazma 0", rc9 == 0 and sim.yazma == [], f"rc {rc9} yazma {sim.yazma}")
    ok("T9 OKU: bolum YOK, P_STYLE 513, readiness", O["bolum"][1] == "YOK" and O["P_STYLE"] == 513 and O["readiness"] == 1517641240112)
    print(f"     T9 istek {sim.n}")

# T10 video bayt farki + KARE_JSON yok -> DUR, create yok
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim()
    v = Path(td) / "img" / "ARIES" / "SADE_VIDEO_ARIES.mp4"; v.write_bytes(b"yeniden kodlanmis")
    os.environ.pop("KARE_JSON", None)
    rc, a, e = kos(sim, out)
    ok("T10 video bayt farki, kare ozeti yok -> DUR", e is not None and "kare ozeti FAIL" in str(e)
       and not [y for y in sim.yazma if y[1] == "create"], str(e))

# T11 sablon Occasion Wedding -> DUR, create yok
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim()
    eski = copy.deepcopy(SABLON_PROPS); SABLON_PROPS[1]["values"] = ["Wedding"]
    rc, a, e = kos(sim, out)
    SABLON_PROPS[:] = eski
    ok("T11 Occasion Wedding -> DUR", e is not None and "Occasion" in str(e) and not [y for y in sim.yazma if y[1] == "create"], str(e))

# T12 eski kopya 4607523667: GET dahil engel
a12 = api_kur(Sim())
try:
    st.Kilitli._call(a12, "GET", f"/listings/{st.ESKI_KOPYA}"); ok("T12 eski kopya GET engellendi", False)
except SystemExit as e:
    ok("T12 eski kopya GET engellendi", "YASAK" in str(e), str(e))

# T13 yayin: 14/14 PASS -> tek PATCH {"state": "active"}, yayin sonrasi geri okuma PASS
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim()
    rc, a, e = kos(sim, out, yayinla=True)
    R = json.load(open(out / "SADE_TASLAK_ARIES.json"))
    ok("T13 yayin rc 0, tek PATCH state=active", rc == 0 and sim.patchler == [{"state": "active"}], f"{e} {sim.patchler}")
    ok("T13 yayin sonrasi kontrol PASS", all(R["yayin"]["kontrol"].values()), R.get("yayin"))
    ok("T13 PATCH izni kapandi", a.yayin_izni is None)
    print(f"     T13 istek {sim.n}")

# T14 kontrol FAIL (alt metin) -> PATCH yok, draft kalir
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim(); sim.alt_bozuk = True
    rc, a, e = kos(sim, out, yayinla=True)
    ok("T14 kontrol FAIL -> PATCH yok, draft", e is not None and sim.patchler == [] and sim.L["state"] == "draft", f"{e} {sim.patchler}")

# T15 yayin izni yokken PATCH engelli (izinli govde olsa bile)
a15 = api_kur(Sim()); a15.lid = 4700000001
try:
    a15.patch(f"/shops/{SHOP}/listings/4700000001", {"state": "active"}); ok("T15 izinsiz PATCH engellendi", False)
except SystemExit as e:
    ok("T15 izinsiz PATCH engellendi", "YASAK" in str(e), str(e))
a15.yayin_izni = 4700000001
try:
    a15.patch(f"/shops/{SHOP}/listings/4700000001", {"state": "active", "title": "x"}); ok("T15 baska alanli PATCH engellendi", False)
except SystemExit as e:
    ok("T15 baska alanli PATCH engellendi", "YASAK" in str(e), str(e))

# T16 yayindan sonra DURUM kaybolursa: ikinci kosu yeni ilan ACMAZ, ikinci PATCH yok (inceleme madde 1)
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim()
    rc, a, e = kos(sim, out, yayinla=True)
    ok("T16a ilk kosu yayin", rc == 0 and sim.L["state"] == "active")
    (out / "DURUM.json").unlink()
    n_create = len([y for y in sim.yazma if y[1] == "create"])
    rc2, a2, e2 = kos(sim, out, yayinla=True)
    ok("T16b DURUM yok: yeni create yok, ikinci PATCH yok, DUR", len([y for y in sim.yazma if y[1] == "create"]) == n_create
       and sim.patchler == [{"state": "active"}] and e2 is not None, f"{e2} {sim.patchler}")

# T17 sablonla farkli alan (elle) varsa yayin yok (inceleme madde 2)
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim(); sim.dil_farkli = True
    rc, a, e = kos(sim, out, yayinla=True)
    ok("T17 elle alan -> PATCH yok, draft", e is not None and "elle" in str(e) and sim.patchler == [] and sim.L["state"] == "draft", str(e))

# T18 yayin sonrasi FAIL: tamam'a girmez, DURUM'da FAIL; ikinci kosu DUR (inceleme madde 3)
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim(); sim.yayin_gorsel_sil = True
    rc, a, e = kos(sim, out, yayinla=True)
    D = json.load(open(out / "DURUM.json"))
    ok("T18a yayin sonrasi FAIL kaydi", e is not None and "ARIES" not in D["tamam"] and str(D["yayin"]["ARIES"]).startswith("FAIL"), f"{e} {D}")
    rc2, a2, e2 = kos(sim, out, yayinla=True)
    ok("T18b ikinci kosu DUR, yeni yazim yok", e2 is not None and "FAIL" in str(e2) and len(sim.patchler) == 1, str(e2))

# T19 yarim kalan ilan (envanter sonrasi kesinti) sonraki kosuda ayni ilanla surer, ikinci create yok
with tempfile.TemporaryDirectory() as td:
    out = ortam(td); sim = Sim(aktif_adim="yok")
    a19 = api_kur(sim)
    gercek = st.Kilitli.post_file if hasattr(st.Kilitli, "post_file") else None
    sayac = {"n": 0}
    eski_pf = st.Etsy.post_file
    def kesik(self, p, files, data=None, tekrar=3):
        sayac["n"] += 1
        if sayac["n"] == 5:
            raise SystemExit("HATA: POST(file) -> 500 (sahte kesinti)")
        return sim.post_file(self, p, files, data, tekrar)
    st.Etsy.post_file = kesik
    try:
        st.kos(a19, SHOP, out, ["ARIES"], yayinla=True); ok("T19a kesinti", False)
    except SystemExit as e:
        ok("T19a kesinti DUR", "sahte kesinti" in str(e), str(e))
    rc2, a2, e2 = kos(sim, out, yayinla=True)
    ok("T19b devam: tek create, 14 gorsel, yayin", rc2 == 0 and len([y for y in sim.yazma if y[1] == "create"]) == 1
       and len(sim.ims) == 14 and sim.patchler == [{"state": "active"}], f"{e2} create {len([y for y in sim.yazma if y[1] == 'create'])} ims {len(sim.ims)}")

# T8 beyansiz aciklama -> metin kapisi DUR (gercek CSV degistirilmeden)
r = st.metin("ARIES"); r2 = dict(r)
ok("T8 ARIES metin hatasiz", r["hata"] == [], r["hata"])

n_ok = sum(v for _, v in SONUC)
print(f"\n{n_ok}/{len(SONUC)} PASS")
sys.exit(0 if n_ok == len(SONUC) else 1)
