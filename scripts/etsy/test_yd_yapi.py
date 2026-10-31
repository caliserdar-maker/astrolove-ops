#!/usr/bin/env python3
"""yd_yapi_kuru.py + yd_yapi_yaz.py sahte Etsy testi (ag yok, token yok, Etsy yok). YD ilani depodaki canli okuma
scripts/kapak78/test_veri/HAM_4595350971.json (CANCER_LIBRA, 15 urun, 5 Style bagi); ikinci ilan ayni verinin AQUARIUS_AQUARIUS kopyasi.
Poster fiyat referansi scripts/etsy/testdata_pod_5x7_kuru_4570143815.json (wall art canli envanteri, 28 Eki).
Sahte Etsy: envanter PUT yalniz ?max_variations_supported=3 ile (yoksa 409), yeni deger kimligi uretir, fiyati {amount, divisor} doner;
variation-images POST; kargo hedefi PUT; magaza ilan taramasi. Hata enjeksiyonu (inceleme 30 Eki): envanter PUT uygulanip 5xx atar
(put_hata="sonra") ya da uygulanmadan atar ("once"); kargo PUT hata atar (dest_hata). Poster ref'e 5x7 urunleri eklenir (30 Eki yazimi
sonrasi canli poster 14 boy). Calistir: python3 scripts/etsy/test_yd_yapi.py"""
import copy
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import yd_yapi_kuru as K  # noqa: E402
import yd_yapi_yaz as Y  # noqa: E402

Y.BEKLE_SN = 0
HAM = json.loads((KOK.parent / "kapak78/test_veri/HAM_4595350971.json").read_text(encoding="utf-8"))
POSTER = json.loads((KOK / "testdata_pod_5x7_kuru_4570143815.json").read_text(encoding="utf-8"))
A, B, PREF, PROF, TID, BOY = "4595350971", "4595373190", "4570110121", 318080539024, 121, 777001
SHOP = "39729443"
sonuc = []


def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""), flush=True)


def hedef(i, cc, rg, ucret, a, b):
    return {"shipping_profile_destination_id": i, "shipping_profile_id": PROF, "origin_country_iso": "US", "destination_country_iso": cc,
            "destination_region": rg, "primary_cost": {"amount": ucret * 100, "divisor": 100, "currency_code": "USD"},
            "secondary_cost": {"amount": ucret * 100, "divisor": 100, "currency_code": "USD"}, "min_delivery_days": a, "max_delivery_days": b,
            "shipping_carrier_id": 0, "mail_class": None}


class Sahte:
    def __init__(s, kalan=5000, ucret_her_yer=0, disari=False, poster_5x7=True):
        s.L, s.inv, s.vi = {}, {}, {}
        for lid, cift in ((A, "CAN_LIB"), (B, "AQU_AQU")):
            s.L[lid] = dict(copy.deepcopy(HAM["listing"]), listing_id=int(lid))
            inv = copy.deepcopy({kk: v for kk, v in HAM["inventory"].items() if kk != "listing"})
            for p in inv["products"]:
                p["sku"] = p["sku"].replace("CAN_LIB", cift)
            s.inv[lid] = inv
            s.vi[lid] = copy.deepcopy(HAM["variation_images"])
        s.poster = copy.deepcopy({kk: v for kk, v in POSTER["inventory"].items() if kk != "listing"})
        if poster_5x7:          # 28 Eki verisinde 5x7 yok; 30 Eki yazimi sonrasi canli posterde 5x7 Digital 3.90 / Print 19.90
            ek = []
            for p in s.poster["products"]:
                if K.deger(p, 513) == "8×10″ (20×25cm)":
                    q = copy.deepcopy(p); K.pv(q, 513)["values"] = [K.K.ETIKET_5X7]; K.pv(q, 513).pop("value_ids", None)
                    q["sku"] = q["sku"].replace("8x10", "5x7")
                    for o in q["offerings"]:
                        o["price"] = {"amount": 390 if K.deger(q, 514) == "Digital File" else 1990, "divisor": 100}
                    ek.append(q)
            s.poster["products"] = ek + s.poster["products"]
        s.tax = [{"property_id": 513, "name": "Custom 1", "display_name": "Custom 1", "supports_variations": True, "scales": [], "possible_values": []},
                 {"property_id": 514, "name": "Custom 2", "display_name": "Custom 2", "supports_variations": True, "scales": [], "possible_values": []},
                 {"property_id": BOY, "name": "Size", "display_name": "Size", "supports_variations": True, "scales": [], "possible_values": []},
                 {"property_id": 777002, "name": "Width", "display_name": "Width", "supports_variations": True,
                  "scales": [{"scale_id": 5, "display_name": "Inches"}], "possible_values": []}]
        s.profil = {"shipping_profile_id": PROF, "title": "BY Print Worldwide", "shipping_profile_destinations": [
            hedef(1, "US", "none", 0, 3, 8), hedef(2, "", "eu", 0, 5, 12), hedef(3, "", "none", ucret_her_yer, 7, 21)]}
        s.magaza = [{"listing_id": int(A), "shipping_profile_id": PROF}, {"listing_id": int(B), "shipping_profile_id": PROF}] \
            + ([{"listing_id": 4570110121, "shipping_profile_id": PROF}] if disari else [])
        s.remaining, s.calls, s.yaz, s.sira = kalan, 0, [], 10 ** 12
        s.vi_dusur = s.inv_boz = False
        s.put_hata = None          # "sonra": PUT uygulanir sonra 503 (zaman asimi gibi); "once": uygulanmadan 503 (tek sefer)
        s.dest_hata, s.dest_govde = False, []

    @staticmethod
    def lid(path):
        p = path.split("?")[0].split("/")
        return p[p.index("listings") + 1]

    def _say(s):
        s.calls += 1; s.remaining -= 1
        if s.remaining < 10:
            raise SystemExit(f"DUR: kota sert tabani: kalan {s.remaining} < 10")

    def _call(s, *a, **kw):
        raise AssertionError("_call")

    def kota_kapisi(s, ne="is"):
        if s.remaining is not None and s.remaining < 10:
            raise SystemExit("DUR: kota esigi")

    def get(s, path, params=None, ok404=False):
        s._say()
        if "/seller-taxonomy/nodes/" in path:
            return {"results": copy.deepcopy(s.tax)}
        if "/shipping-profiles/" in path:
            return copy.deepcopy(s.profil)
        if path.endswith(f"/shops/{SHOP}/listings"):
            st = (params or {}).get("state")
            return {"results": copy.deepcopy(s.magaza) if st == "active" else []}
        lid = s.lid(path)
        if path.endswith("/inventory"):
            return copy.deepcopy(s.poster if lid == PREF else s.inv[lid])
        if path.endswith("/variation-images"):
            return {"results": copy.deepcopy(s.vi[lid])}
        return copy.deepcopy(s.L[lid])

    def put_json(s, path, body):
        s._say(); lid = s.lid(path); s.yaz.append(("PUT inv", lid, path))
        if not path.endswith("/inventory?max_variations_supported=3"):
            raise SystemExit("HATA: PUT inventory -> 409: maximum number of supported variations is 2")
        if s.put_hata == "once":
            s.put_hata = None
            raise SystemExit("HATA: PUT inventory -> 503 (uygulanmadi)")
        eski = {(v["property_id"], a): i for p in s.inv[lid]["products"] for v in p["property_values"]
                for i, a in zip(v.get("value_ids") or [], v.get("values") or [])}
        pr = []
        for n, p in enumerate(copy.deepcopy(body["products"])):
            for v in p["property_values"]:
                if not v.get("value_ids"):
                    key = (v["property_id"], v["values"][0])
                    if key not in eski:
                        s.sira += 1; eski[key] = s.sira
                    v["value_ids"] = [eski[key]]
                v.setdefault("scale_id", None)
            p["offerings"] = [dict(o, price={"amount": round(o["price"] * 100), "divisor": 100, "currency_code": "USD"}, offering_id=n)
                              for o in p["offerings"]]
            p["product_id"] = 9000 + n
            pr.append(p)
        if s.inv_boz:            # tek sefer: Etsy bir urunu dusurmus gibi (geri okuma FAIL -> otomatik geri alma)
            pr, s.inv_boz = pr[:-1], False
        s.inv[lid] = {"products": pr, **{kk: body[kk] for kk in Y.ON_PROP}}
        if s.vi_dusur:
            s.vi[lid] = []
        if s.put_hata == "sonra":   # Etsy degisikligi uyguladi ama yanit 5xx / zaman asimi
            s.put_hata = None
            raise SystemExit("HATA: PUT inventory -> 503 (Etsy uyguladi)")

    def post_json(s, path, body):
        s._say(); lid = s.lid(path); s.yaz.append(("POST vi", lid, path))
        ad = {(v["property_id"], i): a for p in s.inv[lid]["products"] for v in p["property_values"]
              for i, a in zip(v.get("value_ids") or [], v.get("values") or [])}
        s.vi[lid] = [dict(x, value=ad[(x["property_id"], x["value_id"])]) for x in body["variation_images"]]

    def put(s, path, data):
        s._say(); s.yaz.append(("PUT dest", path)); s.dest_govde.append(dict(data))
        if s.dest_hata:
            raise SystemExit("HATA: PUT destination -> 500")
        i = int(path.rsplit("/", 1)[1])
        for d in s.profil["shipping_profile_destinations"]:
            if d["shipping_profile_destination_id"] == i:
                d["primary_cost"] = {"amount": round(data["primary_cost"] * 100), "divisor": 100, "currency_code": "USD"}
                d["secondary_cost"] = {"amount": round(data["secondary_cost"] * 100), "divisor": 100, "currency_code": "USD"}

    def patch(s, *a, **kw):
        raise AssertionError("PATCH (updateListing) cagrilmamali")


def liste(d):
    p = d / "yd.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "a", "b"])
        w.writerows([[A, "CANCER_LIBRA", "Cancer", "Libra"], [B, "AQUARIUS_AQUARIUS", "Aquarius", "Aquarius"]])
    return p


def kuru(api, d, damga="123", boy=BOY, scale=None, sadece=""):
    out = d / f"KURU_{damga}"
    if out.exists():
        shutil.rmtree(out)
    a = SimpleNamespace(liste=str(liste(d)), sadece=sadece, pilot=A, poster_ref=PREF, boy_pid=boy, boy_scale_id=scale, out=str(out))
    return K.calistir(api, SHOP, a, out), out


def ac(api):
    """Ayni sahte magazada ayri kosu: onceki salt okuma kosusunun (salt_okur) ornege yazdigi kilitleri kaldirir (gercekte her kosu ayri surec)."""
    for ad in ("put", "patch", "post", "put_json", "post_json", "post_file", "delete", "_call"):
        api.__dict__.pop(ad, None)
    return api


def yaz(api, plan, mod, d, sadece="", haric="", damga="123", tum=True):
    ac(api)
    out = d / f"o_{mod}_{len(list(d.glob('o_*')))}"
    argv = ["--mod", mod, "--plan", str(plan), "--plan-damga", damga, "--sadece", sadece, "--haric", haric, "--out", str(out),
            "--liste", str(liste(d))]
    if mod != "kontrol":
        argv += ["--onay", Y.ONAY[mod]]
    if mod == "yaz" and not sadece and tum:
        argv += ["--tum"]
    a = Y.argumanlar(argv)
    out.mkdir(parents=True, exist_ok=True)
    rc = Y.calis(api, SHOP, a, out)
    return rc, json.loads((out / "SONUC.json").read_text())


def kuru_testleri(d):
    api = Sahte()
    rc, out = kuru(api, d)
    ka = json.loads((out / f"KURU_{A}.json").read_text())
    yuk = ka["envanter_yuk"]
    pr = yuk["products"]
    k("kuru: cikis 0, iki ilan PLAN", rc == 0 and ka["durum"] == "PLAN" and json.loads((out / f"KURU_{B}.json").read_text())["durum"] == "PLAN")
    k("kuru: 140 urun (5 stil x 2 format x 14 boy), menu sirasi stil > format > boy",
      len(pr) == 140 and K.menu(yuk, BOY) == [list(K.STILLER), ["Digital File", "Print"], [e for e, _ in K.BOYLAR]])
    fy = {(K.deger(p, 514), K.deger(p, BOY)): p["offerings"][0]["price"] for p in pr}
    k("kuru: fiyat Digital File her boy 3.90; Print 5x7 19.90, 8x10 24.90, 24x36 64.90, A2 42.90",
      {v for (f, _), v in fy.items() if f == "Digital File"} == {3.90} and fy[("Print", K.K.ETIKET_5X7)] == 19.90
      and fy[("Print", "8×10″ (20×25cm)")] == 24.90 and fy[("Print", "24×36″ (61×91cm)")] == 64.90 and fy[("Print", "A2 (42×59.4cm)")] == 42.90)
    k("kuru: SKU poster kalibi, adet 999, readiness dijital / baski canlidan, on_property",
      pr[0]["sku"] == "BY-CAN_LIB-ST-5x7-DIGITAL" and pr[14]["sku"] == "BY-CAN_LIB-ST-5x7"
      and {o["quantity"] for p in pr for o in p["offerings"]} == {999}
      and {p["offerings"][0]["readiness_state_id"] for p in pr if K.deger(p, 514) == "Digital File"} == {1512772362964}
      and {p["offerings"][0]["readiness_state_id"] for p in pr if K.deger(p, 514) == "Print"} == {1517641240112}
      and yuk["price_on_property"] == [514, BOY] and yuk["sku_on_property"] == [513, 514, BOY] and yuk["readiness_state_on_property"] == [514])
    k("kuru: Style value_id canlidan, Format / Size kimliksiz (Etsy uretir)",
      K.pv(pr[0], 513)["value_ids"] == [138126211616] and "value_ids" not in K.pv(pr[0], 514) and "value_ids" not in K.pv(pr[0], BOY))
    k("kuru: istek = 2 ilan x 3 + poster 1 + taksonomi 1 + profil 1 + tarama 5", api.calls == 14, api.calls)
    t = json.loads((out / "ISTEK_TAHMINI.json").read_text())
    k("kuru: ISTEK_TAHMINI yazim 7 / 23 ilan basina", t["yazim"]["ilan_basina_tipik"] == 7 and t["yazim"]["ilan_basina_en_kotu"] == 23
      and t["yazim"]["toplam_tipik"] == 14)
    pp = json.loads((out / "PROFIL_PLAN.json").read_text())
    k("kuru: profil UCRETSIZ, takip notu", pp["durum"] == "UCRETSIZ" and "takip" in pp and not pp["yazim"])
    k("kuru: aciklamada eski format satiri raporlanir (metin degismez)", isinstance(ka["metin_celiski"], list))
    try:
        api.put_json(f"/listings/{A}/inventory?max_variations_supported=3", yuk); ok = False
    except SystemExit:
        ok = True
    k("kuru: salt okuma (yazma yontemi DUR)", ok)
    rc2, out2 = kuru(Sahte(), d, damga="124", boy=None)
    k("kuru: boy ozelligi secilmedi -> BLOK, cikis 1", rc2 == 1 and json.loads((out2 / f"KURU_{A}.json").read_text())["durum"] == "BLOK")
    rc2, out2 = kuru(Sahte(), d, damga="125", boy=777002)
    k("kuru: olcekli boy ozelligi --boy-scale-id yok -> BLOK", rc2 == 1 and "olcekli" in " ".join(json.loads((out2 / f"KURU_{A}.json").read_text())["hata"]))
    s = Sahte(); s.L[B]["state"] = "draft"
    rc2, out2 = kuru(s, d, damga="126")
    kb = json.loads((out2 / f"KURU_{B}.json").read_text())
    k("kuru: taslak ilan BLOK (updateListing taslagi yayina alir kurali)", rc2 == 1 and kb["durum"] == "BLOK" and "state draft" in kb["hata"][0])
    s = Sahte()
    for p in s.poster["products"]:
        if K.deger(p, 514) == "Print" and K.deger(p, 513) == "8×10″ (20×25cm)":
            p["offerings"][0]["price"] = {"amount": 2590, "divisor": 100}
    rc2, out2 = kuru(s, d, damga="127")
    k("kuru: poster canli fiyati tablodan farkli -> tum ilanlar BLOK", rc2 == 1 and "poster Print 8x10" in json.loads((out2 / f"KURU_{A}.json").read_text())["hata"][0])
    # inceleme 30 Eki madde 2: bos / eksik boy / tanimsiz etiket / 5x7 fiyati sessiz gecmez
    for ad, boz, bek in (("posterde 5x7 yok (13/14)", lambda s: None, "Print 13/14"),
                         ("poster envanteri bos", lambda s: s.poster.update(products=[]), "Print 0/14"),
                         ("poster 5x7 Print 24.90", lambda s: [p["offerings"][0].update(price={"amount": 2490, "divisor": 100})
                                                              for p in s.poster["products"] if K.deger(p, 513) == K.K.ETIKET_5X7
                                                              and K.deger(p, 514) == "Print"], "poster Print 5x7 canli [24.9]"),
                         ("poster boy etiketi degismis", lambda s: [K.pv(p, 513).update(values=["8x10 in"]) for p in s.poster["products"]
                                                                    if K.deger(p, 513) == "8×10″ (20×25cm)"], "tanimsiz boy etiketi")):
        s = Sahte(poster_5x7=ad != "posterde 5x7 yok (13/14)"); boz(s)
        rc2, out2 = kuru(s, d, damga="127")
        h = " ".join(json.loads((out2 / f"KURU_{A}.json").read_text())["hata"])
        k(f"kuru: {ad} -> BLOK ({bek})", rc2 == 1 and bek in h, h[:160])
    s = Sahte(); s.inv[A]["products"][0]["property_values"][1]["values"] = ["Digital card 4x6"]
    rc2, out2 = kuru(s, d, damga="128")
    k("kuru: bilinmeyen eski format -> BLOK", "bilinmeyen urun" in " ".join(json.loads((out2 / f"KURU_{A}.json").read_text())["hata"]))
    rc2, out2 = kuru(Sahte(ucret_her_yer=12, disari=True), d, damga="129")
    pp = json.loads((out2 / "PROFIL_PLAN.json").read_text())
    k("kuru: profil ucretli + YD disi kullanan -> profil BLOK", rc2 == 1 and pp["durum"] == "BLOK" and pp["yd78_disi_kullanan"] == ["4570110121"])
    rc2, out2 = kuru(Sahte(ucret_her_yer=12), d, damga="130")
    pp = json.loads((out2 / "PROFIL_PLAN.json").read_text())
    k("kuru: profil ucretli, yalniz YD kullaniyor -> YAZILACAK (EVERYWHERE 0, gunler ayni)",
      rc2 == 0 and pp["durum"] == "YAZILACAK" and [(y["hedef"], y["govde"]["primary_cost"], y["govde"]["min_delivery_days"]) for y in pp["yazim"]] == [("EVERYWHERE", 0, 7)])
    return out


def yaz_testleri(d, plan):
    try:
        Y.argumanlar(["--mod", "yaz", "--plan", str(plan), "--plan-damga", "123", "--out", str(d / "x")]); ok = False
    except SystemExit as e:
        ok = "onay" in str(e)
    k("yaz: onay sozcugu yok -> DUR", ok)
    try:
        Y.argumanlar(["--mod", "kontrol", "--plan", str(plan), "--plan-damga", "999", "--out", str(d / "x")]); ok = False
    except SystemExit as e:
        ok = "KURU_999" in str(e)
    k("yaz: plan klasoru plan_damga ile ayni degil -> DUR", ok)
    try:
        Y.plan_yukle(plan, ["4570000000"], []); ok = False
    except SystemExit as e:
        ok = "plan disi" in str(e)
    k("yaz: --sadece plan disi ilan -> DUR", ok)
    try:
        Y.argumanlar(["--mod", "yaz", "--plan", str(plan), "--plan-damga", "123", "--onay", Y.ONAY["yaz"], "--out", str(d / "x")]); ok = False
    except SystemExit as e:
        ok = "--tum" in str(e)
    k("yaz: --sadece (pilot) ve --tum yok -> DUR (madde 7)", ok)
    bozuk = d / "KURU_555"; shutil.copytree(plan, bozuk)
    kb = json.loads((bozuk / f"KURU_{A}.json").read_text()); kb["envanter_yuk"]["products"][20]["offerings"][0]["price"] = 9.90
    (bozuk / f"KURU_{A}.json").write_text(json.dumps(kb))
    try:
        Y.plan_yukle(bozuk, [A], []); ok = False
    except SystemExit as e:
        ok = "yeniden kurulamadi" in str(e)
    k("yaz: elle degistirilmis plan (fiyat) -> DUR, Etsy istegi yok", ok)
    shutil.rmtree(bozuk)

    api = Sahte()
    rc, s = yaz(api, plan, "kontrol", d)
    k("kontrol: 2 ilan KONTROL_YAZILACAK, 6 GET, yazim yok", rc == 0 and [r["sonuc"] for r in s["ilanlar"]] == ["KONTROL_YAZILACAK"] * 2
      and api.calls == 6 and not api.yaz)
    rc, s = yaz(api, plan, "yaz", d, sadece=A)
    r = s["ilanlar"][0]
    k("yaz pilot: TAMAM, 7 istek, PUT ?max_variations_supported=3, B'ye dokunulmadi",
      rc == 0 and r["sonuc"] == "TAMAM" and r["istek"] == 7 and api.yaz == [("PUT inv", A, f"/listings/{A}/inventory?max_variations_supported=3")]
      and len(api.inv[B]["products"]) == 15, r)
    k("yaz pilot: canli 140 urun, Style baglari ayni (ad + gorsel)", len(api.inv[A]["products"]) == 140
      and K.baglar(api.inv[A], api.vi[A])[0] == K.baglar(HAM["inventory"], HAM["variation_images"])[0])
    k("yaz: YEDEK_<lid>.json yazimdan once", any((p / f"YEDEK_{A}.json").exists() for p in d.glob("o_yaz_*")))
    rc, s = yaz(api, plan, "yaz", d, sadece=A)
    k("yaz tekrar: ZATEN, yazim yok", rc == 0 and s["ilanlar"][0]["sonuc"] == "ZATEN" and len(api.yaz) == 1)
    api.vi_dusur = True
    rc, s = yaz(api, plan, "yaz", d, sadece=B)
    r = s["ilanlar"][0]
    k("yaz: PUT sonrasi baglar dustu -> ada gore POST, TAMAM, 9 istek", rc == 0 and r["sonuc"] == "TAMAM" and r["yazilan"] == ["envanter", "bag"]
      and r["istek"] == 9 and K.baglar(api.inv[B], api.vi[B])[0] == [tuple(x) for x in json.loads((plan / f"KURU_{B}.json").read_text())["bag_ad"]], r)
    api.vi_dusur = False
    # geri-al: ham yedege
    rc, s = yaz(api, plan, "geri-al", d)
    k("geri-al: iki ilan 15 urune, eski format; baglar ada gore", rc == 0 and [r["sonuc"] for r in s["ilanlar"]] == ["TAMAM"] * 2
      and all(Y.imza(api.inv[x]) == Y.imza(json.loads((plan / f"KURU_{x}.json").read_text())["envanter_ham_yedek"]) for x in (A, B))
      and all(K.baglar(api.inv[x], api.vi[x])[0] == K.baglar(HAM["inventory"], HAM["variation_images"])[0] for x in (A,)))
    # kayma: kuru sonrasi fiyat degismis
    api2 = Sahte(); api2.inv[A]["products"][2]["offerings"][0]["price"] = {"amount": 2990, "divisor": 100}
    rc, s = yaz(api2, plan, "yaz", d)
    k("yaz: canli plandan farkli -> ATLANDI_KAYMA, o ilana yazim yok, sonraki ilan yazilir", rc == 1
      and [r["sonuc"] for r in s["ilanlar"]] == ["ATLANDI_KAYMA", "TAMAM"] and all(x[1] == B for x in api2.yaz))
    api3 = Sahte(); api3.L[A]["state"] = "draft"
    rc, s = yaz(api3, plan, "yaz", d, sadece=A)
    k("yaz: yazim aninda taslak -> ATLANDI_KAYMA, yazim yok", rc == 1 and s["ilanlar"][0]["sonuc"] == "ATLANDI_KAYMA" and not api3.yaz)
    api4 = Sahte(); api4.inv_boz = True
    rc, s = yaz(api4, plan, "yaz", d)
    r = s["ilanlar"][0]
    k("yaz: geri okuma FAIL -> otomatik geri alma TAMAM, ham envanter, kosu durdu (B yapilmadi)",
      rc == 1 and r["sonuc"] == "FAIL" and r.get("geri_alma") == "TAMAM" and s["ozet"]["yapilmadi"] == [B]
      and Y.imza(api4.inv[A]) == Y.imza(json.loads((plan / f"KURU_{A}.json").read_text())["envanter_ham_yedek"])
      and r["istek"] <= Y.ILAN_UST, r)
    # inceleme 30 Eki madde 1: PUT Etsy'de uygulandi ama 5xx / zaman asimi -> otomatik geri alma (yazilan PUT'tan once)
    hamA = json.loads((plan / f"KURU_{A}.json").read_text())["envanter_ham_yedek"]
    api4b = Sahte(); api4b.put_hata = "sonra"
    rc, s = yaz(api4b, plan, "yaz", d)
    r = s["ilanlar"][0]
    k("yaz: PUT uygulandi + 503 -> FAIL, otomatik geri alma TAMAM, canli ham (15 urun), Style baglari ayni, B yapilmadi",
      rc == 1 and r["sonuc"] == "FAIL" and r.get("geri_alma") == "TAMAM" and Y.imza(api4b.inv[A]) == Y.imza(hamA)
      and len(api4b.inv[A]["products"]) == 15 and K.baglar(api4b.inv[A], api4b.vi[A])[0] == K.baglar(hamA, HAM["variation_images"])[0]
      and s["ozet"]["yapilmadi"] == [B] and r["istek"] <= Y.ILAN_UST, r)
    api4c = Sahte(); api4c.put_hata = "once"
    rc, s = yaz(api4c, plan, "yaz", d)
    r = s["ilanlar"][0]
    k("yaz: PUT uygulanmadan 503 -> FAIL, canli okundu (ham), ikinci PUT yok, geri alma TAMAM (envanter PUT yok)",
      rc == 1 and r["sonuc"] == "FAIL" and str(r.get("geri_alma", "")).startswith("TAMAM (canli envanter ham")
      and [x[0] for x in api4c.yaz] == ["PUT inv"] and Y.imza(api4c.inv[A]) == Y.imza(hamA), r)
    api5 = Sahte(kalan=Y.ILAN_UST + 10 + 3)
    rc, s = yaz(api5, plan, "yaz", d)
    k("yaz: kota esigi (ILAN_UST + 10) -> ilk ilan yazilir, ikincisi KOTA, yarim ilan yok",
      [r["sonuc"] for r in s["ilanlar"]] == ["TAMAM", "KOTA"] and len(api5.inv[B]["products"]) == 15 and rc == 1)
    api6 = Sahte(kalan=30)
    rc, s = yaz(api6, plan, "yaz", d)
    k("yaz: kalan < ILAN_UST + 10 -> KOTA, istek yok", s["ilanlar"][0]["sonuc"] == "KOTA" and api6.calls == 0)
    # yazim sonrasi kuru: ZATEN -> yaz PLAN_ZATEN
    api7 = Sahte(); yaz(api7, plan, "yaz", d, sadece=A)
    rc, out = kuru(api7, d, damga="200")
    k("kuru (yazim sonrasi): hedef yapidaki ilan ZATEN", json.loads((out / f"KURU_{A}.json").read_text())["durum"] == "ZATEN")
    rc, s = yaz(api7, out, "yaz", d, damga="200")
    k("yaz: plan ZATEN ilan -> PLAN_ZATEN (yazim yok), diger ilan TAMAM", [r["sonuc"] for r in s["ilanlar"]] == ["PLAN_ZATEN", "TAMAM"] and rc == 0)
    # profil
    api8 = Sahte(ucret_her_yer=12)
    rc, out = kuru(api8, d, damga="300")
    n0 = len(api8.yaz)
    rc, s = yaz(api8, out, "profil", d, damga="300")
    ev = [x for x in api8.profil["shipping_profile_destinations"] if x["shipping_profile_destination_id"] == 3][0]
    k("profil: EVERYWHERE ucret 12 -> 0, gunler ayni, 1 PUT", rc == 0 and s["sonuc"] == "TAMAM" and len(api8.yaz) - n0 == 1
      and ev["primary_cost"]["amount"] == 0 and (ev["min_delivery_days"], ev["max_delivery_days"]) == (7, 21))
    rc, s = yaz(api8, out, "profil", d, damga="300")
    k("profil tekrar: ZATEN", rc == 0 and s["sonuc"] == "ZATEN")
    rc, s = yaz(api8, out, "profil-geri-al", d, damga="300")
    k("profil-geri-al: EVERYWHERE 12'ye", rc == 0 and s["sonuc"] == "TAMAM" and ev is not None
      and [x for x in api8.profil["shipping_profile_destinations"] if x["shipping_profile_destination_id"] == 3][0]["primary_cost"]["amount"] == 1200)
    k("profil: PUT govdesi canli hedeften (ucret disi alanlar canliyla ayni)",
      api8.dest_govde[0] == Y.hedef_govde(hedef(3, "", "none", 12, 7, 21), 0, 0))
    rc2, out2 = kuru(Sahte(ucret_her_yer=12, disari=True), d, damga="301")
    a9 = Sahte(ucret_her_yer=12, disari=True)
    rc, s = yaz(a9, out2, "profil", d, damga="301")
    k("profil: YD disi kullanan varken (plan BLOK) yazim yok, SONUC.json HATA, cikis 1",
      rc == 1 and s["sonuc"] == "HATA" and "PROFIL_PLAN yazilamaz" in s["neden"] and not a9.yaz)
    # inceleme 30 Eki madde 4: tasiyici / mail_class korunur; yazim aninda yeniden tarama; PUT hatasi SONUC.json'a
    a10 = Sahte(ucret_her_yer=12)
    for x in a10.profil["shipping_profile_destinations"]:
        x.update(shipping_carrier_id=27, mail_class="tracked_intl")
    rc, out = kuru(a10, d, damga="302")
    rc, s = yaz(a10, out, "profil", d, damga="302")
    g = a10.dest_govde[0] if a10.dest_govde else {}
    k("profil: PUT govdesinde canli shipping_carrier_id / mail_class / teslim gunleri korunur, yalniz ucret 0",
      rc == 0 and s["sonuc"] == "TAMAM" and g.get("shipping_carrier_id") == 27 and g.get("mail_class") == "tracked_intl"
      and (g.get("min_delivery_days"), g.get("max_delivery_days")) == (7, 21) and (g.get("primary_cost"), g.get("secondary_cost")) == (0, 0)
      and g.get("destination_region") == "none", g)
    a11 = Sahte(ucret_her_yer=12)
    rc, out = kuru(a11, d, damga="303")
    a11.magaza.append({"listing_id": 4570110121, "shipping_profile_id": PROF})   # kuru sonrasi profile YD disi ilan eklendi
    rc, s = yaz(a11, out, "profil", d, damga="303")
    k("profil: yazim aninda yeniden tarama, YD disi kullanan -> DUR, PUT yok", rc == 1 and s["sonuc"] == "DUR"
      and s.get("yd_disi_kullanan") == ["4570110121"] and not [x for x in a11.yaz if x[0] == "PUT dest"], s)
    a12 = Sahte(ucret_her_yer=12)
    rc, out = kuru(a12, d, damga="304")
    a12.dest_hata = True
    try:
        rc, s = yaz(a12, out, "profil", d, damga="304"); ok = rc == 1 and s["sonuc"] == "HATA" and "500" in s["neden"]
    except BaseException as e:   # noqa: BLE001  (duzeltme oncesi istisna disari tasar, SONUC.json yazilmaz)
        ok, s = False, repr(e)
    k("profil: PUT hatasi -> SONUC.json HATA (istisna yakalanir), cikis 1", ok, s)


def is_akisi():
    import kilit_bekle
    wf = KOK.parents[1] / ".github/workflows"
    kume = kilit_bekle.kilit_kumesi(str(KOK.parents[1]))
    for ad, betik in (("yd-yapi-kuru.yml", "yd_yapi_kuru.py"), ("yd-yapi-yaz.yml", "yd_yapi_yaz.py")):
        t = (wf / ad).read_text(encoding="utf-8")
        k(f"is akisi {ad}: Etsy kilidinde, kilit token indirmeden once, actions: read, concurrency yok, token geri yaz + sir_koru",
          f".github/workflows/{ad}" in kume and t.index("kilit_bekle.py") < t.index("ETSY_TOKEN.json") and "actions: read" in t
          and "concurrency:" not in t and "token_geri_yaz.sh" in t and "sir_koru.py" in t and betik in t and "schedule" not in t)
    t = (wf / "yd-yapi-yaz.yml").read_text(encoding="utf-8")
    k("is akisi yd-yapi-yaz: varsayilan mod kontrol, onay girdisi, plan TEMP/YD_YAPI/KURU_<damga>",
      'default: "kontrol"' in t and '--onay "$ONAY"' in t and "TEMP/YD_YAPI/KURU_$PD" in t)
    k("is akisi yd-yapi-yaz: yaz modunda sadece (pilot) bos ise tum=evet zorunlu, betige --tum",
      'tum: {description' in t and '[ "$MOD" = yaz ] && [ -z "$S" ] && [ "$TUM" != evet ]' in t and "--tum" in t)


def boy_516():
    """Serdar 31 Eki 5a: canli taksonomi 121 kaydi (kupa-yd-oku 41180774733 YD_BOY.json) 516 Custom3 -> menu adi Size, hata yok."""
    tax = [{"property_id": 516, "name": "Custom3", "display_name": "Custom Property", "supports_variations": True, "scales": [],
            "possible_values": []}]
    sab, h = K.boy_ozellik(tax, K.BOY_PID)
    k("boy: varsayilan BOY_PID 516, menu adi Size (Custom Property degil), hata yok",
      K.BOY_PID == 516 and sab == {"property_id": 516, "property_name": "Size"} and not h, (sab, h))
    pv = lambda ad3, ids=(513, 514, 516): {"products": [{"sku": "x", "property_values": [
        {"property_id": i, "property_name": a} for i, a in zip(ids, ("Style", "Format", ad3))]}]}
    k("boy_kabul: 513 + 514 + 516 Size -> PASS; ad 'Custom Property' -> FAIL; 516 yok -> FAIL (Serdar 31 Eki 4a pilot adimi)",
      Y.boy_kabul(pv("Size"), 516) == [] and Y.boy_kabul(pv("Custom Property"), 516) and Y.boy_kabul(pv("Size", (513, 514, 515)), 516))
    k("boy: --boy-pid varsayilani 516, 0 = secilmedi", K.argumanlar(["--out", "x"]).boy_pid == 516
      and K.boy_ozellik(tax, 0)[0] is None)


def sku_siniri(d):
    """Serdar 31 Eki 1a: kisa stil kodu; 140 SKU <= 32 (kapi PASS). Kapi hala calisir: uzun SKU -> hata."""
    rc, out = kuru(Sahte(), d, damga="s32")
    ka = json.loads((out / f"KURU_{A}.json").read_text())
    sk = [p["sku"] for p in ka["envanter_yuk"]["products"]]
    k("SKU kisa kod: 140 SKU <= 32, en uzun 27, kapi hatasi yok", rc == 0 and len(sk) == 140 and max(map(len, sk)) == 27
      and not any("karakteri asiyor" in h for h in ka["hata"]), (rc, max(map(len, sk)), ka["hata"][:2]))
    k("SKU kodlari ST/TL/FP/LY/BO, eski uzun kod yok", {x.split("-")[2] for x in sk} == {"ST", "TL", "FP", "LY", "BO"})
    uzun = copy.deepcopy(ka["envanter_yuk"]); uzun["products"][0]["sku"] = "BY-CAN_LIB-FIRSTPAGE-12x18-DIGITAL"
    k("kapi: 34 karakterlik SKU -> hata", any("32 karakteri asiyor" in h for h in K.hedef_kapisi(uzun, BOY)))


def main():
    d = Path(tempfile.mkdtemp(prefix="ydyapi_"))
    try:
        boy_516()
        sku_siniri(d)
        plan = kuru_testleri(d)
        yaz_testleri(d, plan)
        is_akisi()
    finally:
        shutil.rmtree(d, ignore_errors=True)
    bad = sonuc.count(False)
    print(f"\nyd_yapi testleri: {len(sonuc) - bad}/{len(sonuc)} PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
