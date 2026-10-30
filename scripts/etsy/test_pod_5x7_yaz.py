#!/usr/bin/env python3
"""pod_5x7_yaz.py sahte Etsy testi (ag yok, gercek TOKEN_FILE yok). Plan, gercek kuru betigiyle (pod_5x7_kuru.main) sahte Etsy uzerinden
uretilir; ilan verisi depodaki testdata_pod_5x7_kuru_4570143815.json (canli ilan 28 Eki kuru okumasi), ikinci ilan ayni verinin
4570110121 kopyasi. Sahte Etsy: envanter PUT'ta 5x7 Size value_id uretir, fiyati {amount, divisor} doner, RU PUT'ta gercek
etsy_common.ru_yazim_kapisi'ni calistirir (gercek _call gibi).
Calistir: python3 scripts/etsy/test_pod_5x7_yaz.py"""
import copy
import csv
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402
import pod_5x7_kuru as K  # noqa: E402
import pod_5x7_yaz as Y  # noqa: E402
from beyan_marka_yaz import norm  # noqa: E402

Y.BEKLE_SN = 0
F = json.loads((KOK / "testdata_pod_5x7_kuru_4570143815.json").read_text(encoding="utf-8"))
A, B = "4570110121", "4570143815"     # A = pilot, B = fixture ilani (ikisi de data/pod/pod78_ids.csv'de)
sonuc = []


def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))


AU = {"shipping_profile_destination_id": 11, "shipping_profile_id": K.PROFIL, "origin_country_iso": "US", "destination_country_iso": "AU",
      "destination_region": "none", "min_delivery_days": 5, "max_delivery_days": 10, "shipping_carrier_id": 0, "mail_class": None,
      "primary_cost": {"amount": 0, "divisor": 100, "currency_code": "USD"}, "secondary_cost": {"amount": 0, "divisor": 100, "currency_code": "USD"}}
US = dict(copy.deepcopy(AU), shipping_profile_destination_id=12, destination_country_iso="US", min_delivery_days=3, max_delivery_days=8)


class Sahte:
    def __init__(s, ilanlar=(A, B), kalan=5000):
        s.L, s.inv, s.vi, s.ru = {}, {}, {}, {}
        for lid in ilanlar:
            s.L[lid] = dict(copy.deepcopy(F["listing"]), listing_id=int(lid))
            s.inv[lid] = copy.deepcopy({kk: v for kk, v in F["inventory"].items() if kk != "listing"})
            s.vi[lid] = copy.deepcopy(F["variation_images"])
            s.ru[lid] = copy.deepcopy(F["ru"])
        s.profil = {"title": "POD", "shipping_profile_destinations": [copy.deepcopy(AU), copy.deepcopy(US)]}
        s.remaining, s.calls, s.yaz, s.sira = kalan, 0, [], 10 ** 12
        s.vi_dusur = s.inv_boz = s.en_boz = s.sira_boz = s.post_hata = False
        s.esik = 10

    @staticmethod
    def lid(path):
        p = path.split("/")
        return p[p.index("listings") + 1]

    def _say(s):
        s.calls += 1; s.remaining -= 1
        if s.remaining < 10:
            raise SystemExit(f"DUR: kota sert tabani: kalan {s.remaining} < 10")

    def _call(s, *a, **kw):   # salt_okur sarar; sahte istekler buradan gecmez
        raise AssertionError("_call")

    def kota_kapisi(s, ne="is"):
        if s.remaining is not None and s.remaining < 10:
            raise SystemExit("DUR: kota esigi")

    def get(s, path, params=None, ok404=False):
        s._say()
        if "/shipping-profiles/" in path:
            return copy.deepcopy(s.profil)
        lid = s.lid(path)
        if path.endswith("/inventory"):
            return copy.deepcopy(s.inv[lid])
        if path.endswith("/variation-images"):
            return {"results": copy.deepcopy(s.vi[lid])}
        if path.endswith("/translations/ru"):
            return copy.deepcopy(s.ru[lid])
        return copy.deepcopy(s.L[lid])

    def put_json(s, path, body):
        s._say(); lid = s.lid(path); s.yaz.append(("PUT inv", lid))
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
            p["offerings"] = [dict(o, price={"amount": round(o["price"] * 100), "divisor": 100, "currency_code": "USD"},
                                   offering_id=n) for o in p["offerings"]]
            p["product_id"] = 9000 + n
            pr.append(p)
        if s.inv_boz:
            pr = pr[:-1]
        if s.sira_boz:          # tek sefer: Etsy urun sirasini degistirmis gibi (menu sirasi bozulur)
            pr, s.sira_boz = pr[::-1], False
        s.inv[lid] = {"products": pr, **{kk: body[kk] for kk in Y.ON_PROP}}
        if s.vi_dusur:
            s.vi[lid] = []

    def post_json(s, path, body):
        s._say(); lid = s.lid(path); s.yaz.append(("POST vi", lid))
        if s.post_hata:          # tek sefer 400
            s.post_hata = False
            raise SystemExit("HATA: POST variation-images -> 400")
        ad = {(v["property_id"], i): a for p in s.inv[lid]["products"] for v in p["property_values"]
              for i, a in zip(v.get("value_ids") or [], v.get("values") or [])}
        s.vi[lid] = [dict(x, value=ad[(x["property_id"], x["value_id"])]) for x in body["variation_images"]]

    def patch(s, path, data):
        s._say(); lid = s.lid(path); s.yaz.append(("PATCH", lid))
        s.L[lid]["description"] = data["description"] + (" x" if s.en_boz else "")

    def put(s, path, data):
        E.ru_yazim_kapisi("PUT", path, data)   # gercek Etsy._call ile ayni kapi
        s._say(); s.yaz.append(("PUT " + ("ru" if "translations" in path else "profil"), path.split("/")[-1]))
        if "/shipping-profiles/" in path:
            for d in s.profil["shipping_profile_destinations"]:
                if str(d["shipping_profile_destination_id"]) == path.split("/")[-1]:
                    d.update(min_delivery_days=data["min_delivery_days"], max_delivery_days=data["max_delivery_days"])
            return
        lid = s.lid(path)
        s.ru[lid] = dict(title=data["title"], description=data["description"], tags=data["tags"].split(","))


# ------------------------------------------------------------------ plan (gercek kuru betigi, sahte Etsy)
def plan_uret(kok, damga="777"):
    sh = Sahte()
    sh.get_eski = sh.get

    def get(path, params=None, ok404=False):
        if path.endswith("/listings/active") or path.endswith("/listings"):
            return {"count": 2, "results": [{"listing_id": int(A), "shipping_profile_id": K.PROFIL},
                                            {"listing_id": int(B), "shipping_profile_id": K.PROFIL}]}
        return sh.get_eski(path, params, ok404)
    sh.get = get

    class FS:
        def __init__(s2, *a):
            pass

        def needs_refresh(s2):
            return False
    e0, t0 = E.Etsy, E.TokenStore
    E.Etsy, E.TokenStore = (lambda store: sh), FS
    os.environ.update(TOKEN_FILE="/dev/null", ETSY_SHOP_ID="1")
    out = Path(kok) / f"KURU_{damga}"
    sys.argv = ["k", "--ids", f"{A},{B}", "--pilot", A, "--out", str(out)]
    try:
        rc = K.main()
    finally:
        E.Etsy, E.TokenStore = e0, t0
    E.RU_POSTER_IZIN.clear()
    return rc, out


W = Path(tempfile.mkdtemp(prefix="yaz5x7_"))
rc, PLAN = plan_uret(W)
k("P0 kuru plan (gercek betik) PASS, 2 ilan", rc == 0 and len(list(PLAN.glob("KURU_*.json"))) == 2, rc)
PK = {lid: json.loads((PLAN / f"KURU_{lid}.json").read_text(encoding="utf-8")) for lid in (A, B)}


def kos(mod, api, sadece="", haric="", plan=PLAN, damga="777", onay=None):
    out = Path(tempfile.mkdtemp(prefix="out_", dir=W))
    a = Y.argumanlar(["--mod", mod, "--plan", str(plan), "--plan-damga", damga, "--sadece", sadece, "--haric", haric,
                      "--onay", Y.ONAY.get(mod, "") if onay is None else onay, "--out", str(out)])
    E.RU_POSTER_IZIN.clear()
    rc = Y.calis(api, "1", a, out)
    s = json.loads((out / "SONUC.json").read_text(encoding="utf-8"))
    return rc, s, out


def durum(s):
    return {r["listing_id"]: r["sonuc"] for r in s["ilanlar"]}


# T1 pilot
api = Sahte()
rc, s, out = kos("yaz", api, sadece=A)
r = s["ilanlar"][0]
inv = api.inv[A]["products"]
yeni = [p for p in inv if Y.boy(p) == K.ETIKET_5X7]
k("T1 pilot TAMAM, rc 0, yalniz A", rc == 0 and durum(s) == {A: "TAMAM"} and {x[1] for x in api.yaz if x[0] != "PUT ru"} == {A}, (rc, durum(s)))
k("T1 envanter 140, ilk urun 5x7, 10 yeni (Print 19.90 x5, Digital 3.90 x5)",
  len(inv) == 140 and Y.boy(inv[0]) == K.ETIKET_5X7 and len(yeni) == 10
  and sorted(K.para(p["offerings"][0]["price"]) for p in yeni) == [3.9] * 5 + [19.9] * 5)
k("T1 mevcut 130 urun aynen (imza)", Y.imza({"products": [p for p in inv if Y.boy(p) != K.ETIKET_5X7]})[0]
  == Y.imza(PK[A]["envanter_ham_yedek"])[0])
k("T1 EN = plan en_yeni; '24 hours' onizleme cumlesi; yasak yok",
  norm(api.L[A]["description"]) == PK[A]["en_yeni"] and "We send a free preview via Etsy Messages within 24 hours. After you approve, "
  "your file is emailed to you within 24 hours. We check every personalization by hand before sending" in api.L[A]["description"]
  and not K.YASAK_EN.search(api.L[A]["description"]) and "14 sizes, from 5 x 7" in api.L[A]["description"])
k("T1 RU = plan ru_yeni, RU baslik + etiket aynen", api.ru[A]["description"] == PK[A]["ru_yeni"] and api.ru[A]["title"] == F["ru"]["title"]
  and api.ru[A]["tags"] == F["ru"]["tags"])
k("T1 B'ye dokunulmadi", api.inv[B] == {kk: v for kk, v in F["inventory"].items() if kk != "listing"}
  and api.L[B]["description"] == F["listing"]["description"] and api.ru[B] == F["ru"])
k("T1 istek 11 (kuru tahmini), YEDEK var, renk bagi ayni", r["istek"] == 11 and (out / f"YEDEK_{A}.json").is_file()
  and Y.renk_ad(api.inv[A], api.vi[A]) == Y.renk_ad(F["inventory"], F["variation_images"]), r.get("istek"))

# T2 tekrar: ZATEN
n0 = len(api.yaz)
rc, s, _ = kos("yaz", api, sadece=A)
k("T2 ikinci kosu ZATEN, yazma 0, istek 4", rc == 0 and durum(s) == {A: "ZATEN"} and len(api.yaz) == n0 and s["ilanlar"][0]["istek"] == 4,
  (durum(s), s["ilanlar"][0].get("istek")))

# T3 haric: plan 2 satir, haric A -> yalniz B; plan kilidi reddetmez
api = Sahte()
rc, s, out = kos("yaz", api, haric=A)
csvs = {x["listing_id"]: x["sonuc"] for x in csv.DictReader(open(out / "SONUC.csv", encoding="utf-8"))}
k("T3 haric A: B TAMAM, A HARIC (yazma yok)", rc == 0 and durum(s) == {B: "TAMAM"} and csvs == {B: "TAMAM", A: "HARIC"}
  and all(x[1] != A for x in api.yaz), csvs)

# T4 plan FAIL satiri: haricsiz DUR, haric ile gecer
P2 = W / "KURU_778"
shutil.copytree(PLAN, P2)
kb = json.loads((P2 / f"KURU_{A}.json").read_text(encoding="utf-8")); kb["PASS"] = False; kb["hata"] = ["x"]
(P2 / f"KURU_{A}.json").write_text(json.dumps(kb, ensure_ascii=False), encoding="utf-8")
api = Sahte()
try:
    kos("yaz", api, plan=P2, damga="778"); dur = None
except SystemExit as e:
    dur = str(e)
k("T4a plan FAIL satiri secili -> DUR, istek 0", dur and "plan FAIL" in dur and api.calls == 0, dur)
rc, s, _ = kos("yaz", api, plan=P2, damga="778", haric=A)
k("T4b ayni plan + haric A -> B TAMAM", rc == 0 and durum(s) == {B: "TAMAM"}, durum(s))

# T5 plan disi kimlik / onay / damga
api = Sahte()
for ad, f in (("sadece plan disi", lambda: kos("yaz", api, sadece="123")), ("haric plan disi", lambda: kos("yaz", api, haric="123")),
              ("onay yanlis", lambda: kos("yaz", api, sadece=A, onay="EVET")), ("damga klasorle uyusmuyor", lambda: kos("yaz", api, damga="999")),
              ("sadece+haric ayni", lambda: kos("yaz", api, sadece=A, haric=A))):
    try:
        f(); d = None
    except SystemExit as e:
        d = str(e)
    k(f"T5 {ad} -> DUR, istek 0", d and d.startswith("DUR") and api.calls == 0, d)

# T6 canli != plan (EN elle degismis) -> A ATLANDI_KAYMA, yazma yok, B yazilir, rc 1
api = Sahte()
api.L[A]["description"] += "\n\nEXTRA"
rc, s, _ = kos("yaz", api)
k("T6 EN kaymasi: A ATLANDI_KAYMA (yazma 0), B TAMAM, rc 1", rc == 1 and durum(s) == {A: "ATLANDI_KAYMA", B: "TAMAM"}
  and all(x[1] != A for x in api.yaz), durum(s))
# T6b envanter kaymasi (fiyat degismis), T6c renk bagi kaymasi, T6d RU kaymasi, T6e taslak
for ad, boz in (("envanter fiyat", lambda a: a.inv[A]["products"][3]["offerings"][0]["price"].update(amount=1)),
                ("renk bagi", lambda a: a.vi[A].pop()), ("RU etiket", lambda a: a.ru[A]["tags"].append("yeni")),
                ("state draft", lambda a: a.L[A].update(state="draft"))):
    api = Sahte(); boz(api)
    rc, s, _ = kos("yaz", api, sadece=A)
    k(f"T6 {ad} kaymasi -> ATLANDI_KAYMA, yazma 0", rc == 1 and durum(s) == {A: "ATLANDI_KAYMA"} and not api.yaz, s["ilanlar"][0].get("neden"))

# T7 envanter geri okuma bozuk -> FAIL, kosu durur (B YAPILMADI), EN/RU yazilmaz
api = Sahte(); api.inv_boz = True
rc, s, out = kos("yaz", api)
csvs = {x["listing_id"]: x["sonuc"] for x in csv.DictReader(open(out / "SONUC.csv", encoding="utf-8"))}
k("T7 envanter geri okuma FAIL -> dur; ikinci ilan YAPILMADI; EN/RU yazilmadi", rc == 1 and list(durum(s).values()) == ["FAIL"]
  and "YAPILMADI" in csvs.values() and [x[0] for x in api.yaz] == ["PUT inv"], (csvs, api.yaz))

# T8 renk bagi dustu -> POST ile yeniden kurulur, TAMAM, istek 13
api = Sahte(); api.vi_dusur = True
rc, s, _ = kos("yaz", api, sadece=A)
k("T8 renk bagi yeniden kuruldu (POST), TAMAM", rc == 0 and durum(s) == {A: "TAMAM"} and ("POST vi", A) in api.yaz
  and Y.renk_ad(api.inv[A], api.vi[A]) == Y.renk_ad(F["inventory"], F["variation_images"]), (durum(s), s["ilanlar"][0].get("istek")))

# T9 EN geri okuma tutmaz -> FAIL (3 deneme), RU yazilmaz
api = Sahte(); api.en_boz = True
rc, s, _ = kos("yaz", api, sadece=A)
k("T9 EN geri okuma FAIL, RU yazilmadi", rc == 1 and durum(s) == {A: "FAIL"} and not any(x[0] == "PUT ru" for x in api.yaz),
  s["ilanlar"][0].get("neden"))

# T10 kota: ilan esigi (19 + 10)
api = Sahte(kalan=28)
rc, s, _ = kos("yaz", api, sadece=A)
k("T10 kalan 28 < 19+10 -> KOTA, istek 0", rc == 1 and durum(s) == {A: "KOTA"} and api.calls == 0, s["ilanlar"][0].get("neden"))
api = Sahte(kalan=33)    # 33 >= 19+10: A okunur (29 kalir), yazim icin 15+10=25 yeter; A sonrasi 22 < 29 -> B KOTA
rc, s, _ = kos("yaz", api)
k("T10b kalan 33: A TAMAM (22 kalir), B ilan esiginde KOTA, kosu durur", durum(s) == {A: "TAMAM", B: "KOTA"} and rc == 1, durum(s))

# T11 plan butunlugu: plan dosyasinda en_yeni elle degismis -> DUR (istek yok)
P3 = W / "KURU_779"
shutil.copytree(PLAN, P3)
kb = json.loads((P3 / f"KURU_{A}.json").read_text(encoding="utf-8")); kb["en_yeni"] = kb["en_yeni"].replace("14 sizes", "15 sizes")
(P3 / f"KURU_{A}.json").write_text(json.dumps(kb, ensure_ascii=False), encoding="utf-8")
api = Sahte()
try:
    kos("yaz", api, plan=P3, damga="779", sadece=A); d = None
except SystemExit as e:
    d = str(e)
k("T11 plan en_yeni elle degismis -> DUR, istek 0", d and "aciklama plani" in d and api.calls == 0, d)

# T12 RU kapisi: izin olmadan RU PUT -> SystemExit (gercek ru_yazim_kapisi)
E.RU_POSTER_IZIN.clear()
try:
    Sahte().put(f"/shops/1/listings/{A}/translations/ru", {"title": "t", "description": PK[A]["ru_yeni"], "tags": "a"}); d = None
except SystemExit as e:
    d = str(e)
k("T12 izinsiz poster RU yazimi kapida durur", d and "ru_poster" in d, d)

# T13 kontrol modu: yazma yontemleri kapali, KONTROL_YAZILACAK; yazilmis ilanda KONTROL_ZATEN
api = Sahte()
rc, s, _ = kos("kontrol", api)
k("T13 kontrol: 2 ilan KONTROL_YAZILACAK, yazma 0, istek 8", rc == 0 and set(durum(s).values()) == {"KONTROL_YAZILACAK"} and not api.yaz
  and api.calls == 8, (durum(s), api.calls))

# T14 geri-al: yaz -> geri-al -> canli = plan ham (envanter imzasi, EN, RU); tekrar geri-al ZATEN
api = Sahte()
kos("yaz", api, sadece=A)
rc, s, _ = kos("geri-al", api, sadece=A)
k("T14 geri-al TAMAM: 130 urun imza = ham, EN = eski, RU = eski", rc == 0 and durum(s) == {A: "TAMAM"}
  and Y.imza(api.inv[A]) == Y.imza(F["inventory"]) and norm(api.L[A]["description"]) == norm(F["listing"]["description"])
  and api.ru[A]["description"] == F["ru"]["description"], durum(s))
rc, s, _ = kos("geri-al", api, sadece=A)
k("T14b ikinci geri-al ZATEN", rc == 0 and durum(s) == {A: "ZATEN"}, durum(s))
try:
    kos("geri-al", Sahte(), sadece=A, onay=Y.ONAY["yaz"]); d = None
except SystemExit as e:
    d = str(e)
k("T14c geri-al yaz onayiyla calismaz", d and "onay" in d, d)

# T15 profil: AU 5-10 -> 7-22, US aynen; tekrar ZATEN; geri-al; kayma
api = Sahte()
pp = json.loads((PLAN / "PROFIL_PLAN.json").read_text(encoding="utf-8"))
rc, s, _ = kos("profil", api)
hd = {d["destination_country_iso"]: (d["min_delivery_days"], d["max_delivery_days"]) for d in api.profil["shipping_profile_destinations"]}
k("T15 profil TAMAM: AU (7, 22), US (3, 8)", rc == 0 and s["sonuc"] == "TAMAM" and hd == {"AU": (7, 22), "US": (3, 8)}, (s, hd))
rc, s, _ = kos("profil", api)
k("T15b profil tekrar ZATEN", rc == 0 and s["sonuc"] == "ZATEN", s)
rc, s, _ = kos("profil-geri-al", api)
hd = {d["destination_country_iso"]: (d["min_delivery_days"], d["max_delivery_days"]) for d in api.profil["shipping_profile_destinations"]}
k("T15c profil-geri-al: AU (5, 10)", rc == 0 and s["sonuc"] == "TAMAM" and hd["AU"] == (5, 10), (s, hd))
api = Sahte(); api.profil["shipping_profile_destinations"][1]["max_delivery_days"] = 9
rc, s, _ = kos("profil", api)
k("T15d US hedefi plandan farkli -> ATLANDI_KAYMA, yazma 0", rc == 1 and s["sonuc"] == "ATLANDI_KAYMA" and not api.yaz, s)
k("T15e plan AU once (5, 10) -> sonra (7, 22)", (pp["au_once"][0]["min_delivery_days"], pp["au_once"][0]["max_delivery_days"]) == (5, 10)
  and pp["au_sonra"] == {"min_delivery_days": 7, "max_delivery_days": 22})

# T16 EN geri okuma farkli (gercekci yarim yazim): yaz tekrar -> ATLANDI_KAYMA (canli != plan); geri-al bilesen basina TAMAM
api = Sahte(); api.en_boz = True
kos("yaz", api, sadece=A)
api.en_boz = False
rc, s, _ = kos("yaz", api, sadece=A)
k("T16a yarim ilanda yeniden yaz -> ATLANDI_KAYMA (EN plandan farkli), yazma yok", rc == 1 and durum(s) == {A: "ATLANDI_KAYMA"}, s["ilanlar"][0].get("neden"))
n0 = len(api.yaz)
rc, s, _ = kos("geri-al", api, sadece=A)
r = s["ilanlar"][0]
k("T16b geri-al: envanter geri, EN plan disi farkli -> kayma (elle), RU atla, TAMAM_KISMI rc 1", rc == 1 and r["sonuc"] == "TAMAM_KISMI"
  and r["adim"]["envanter"] == "yaz" and r["adim"]["en"].startswith("kayma") and r["adim"]["ru"] == "atla"
  and Y.imza(api.inv[A]) == Y.imza(F["inventory"]) and ("PATCH", A) not in api.yaz[n0:], r.get("adim"))

# T17 Etsy urun sirasini bozarsa: yaz FAIL (menu sirasi), geri-al calisir (sirasiz imza)
api = Sahte(); api.sira_boz = True
rc, s, _ = kos("yaz", api, sadece=A)
k("T17a menu sirasi bozuk -> FAIL", rc == 1 and durum(s) == {A: "FAIL"} and "menusu" in s["ilanlar"][0]["neden"], s["ilanlar"][0].get("neden"))
rc, s, _ = kos("geri-al", api, sadece=A)
k("T17b geri-al TAMAM: 130 urun, menu ham sirada", rc == 0 and durum(s) == {A: "TAMAM"} and len(api.inv[A]["products"]) == 130
  and Y.menu(api.inv[A]) == Y.menu(F["inventory"]), durum(s))

api = Sahte(); api.sira_boz = True
kos("yaz", api, sadece=A)
n0 = len(api.yaz)
rc, s, _ = kos("yaz", api, sadece=A)
k("T17d menu bozuk + yeniden yaz -> ATLANDI_KAYMA, yazma 0", rc == 1 and durum(s) == {A: "ATLANDI_KAYMA"} and len(api.yaz) == n0
  and "menusu" in s["ilanlar"][0]["neden"], s["ilanlar"][0].get("neden"))
rc, s, _ = kos("kontrol", api, sadece=A)
k("T17e kontrol modu menu bozuk ilani gosterir (ATLANDI_KAYMA)", durum(s) == {A: "ATLANDI_KAYMA"}, durum(s))

# T23 yaz sonrasi EN'de elle duzeltme: geri-al EN'ye dokunmaz (kayma), envanter + RU geri, TAMAM_KISMI
api = Sahte()
kos("yaz", api, sadece=A)
api.L[A]["description"] = api.L[A]["description"].replace("- Nothing is shipped. For personal use only.", "- Nothing ships.")
rc, s, _ = kos("geri-al", api, sadece=A)
r = s["ilanlar"][0]
k("T23 elle EN duzeltmesi korunur: en kayma, envanter/RU geri, TAMAM_KISMI", rc == 1 and r["sonuc"] == "TAMAM_KISMI"
  and r["adim"]["en"].startswith("kayma") and "- Nothing ships." in api.L[A]["description"]
  and api.ru[A]["description"] == F["ru"]["description"] and len(api.inv[A]["products"]) == 130, r.get("adim"))

# T18 renk bagi dustu + POST 400: yaz FAIL; yeniden yaz -> envanter atla, renk onar, EN/RU yaz, TAMAM
api = Sahte(); api.vi_dusur = True; api.post_hata = True
rc, s, _ = kos("yaz", api, sadece=A)
k("T18a renk bagi POST 400 -> FAIL, EN yazilmadi", rc == 1 and durum(s) == {A: "FAIL"} and not any(x[0] == "PATCH" for x in api.yaz))
api.vi_dusur = False
rc, s, _ = kos("yaz", api, sadece=A)
r = s["ilanlar"][0]
k("T18b yeniden yaz: renk onar + TAMAM, bag plandaki gibi", rc == 0 and r["sonuc"] == "TAMAM" and r["adim"]["renk"] == "onar"
  and r["adim"]["envanter"] == "atla" and Y.renk_ad(api.inv[A], api.vi[A]) == Y.renk_ad(F["inventory"], F["variation_images"]), r.get("adim"))

# T19 kuru sonrasi satis: canli adet 997 -> kayma degil, 140 urun adet 997
api = Sahte()
for p in api.inv[A]["products"]:
    for o in p["offerings"]:
        o["quantity"] = 997
rc, s, _ = kos("yaz", api, sadece=A)
k("T19 adet 997 (satis): TAMAM, tum teklifler 997", rc == 0 and durum(s) == {A: "TAMAM"} and Y.adetler(api.inv[A]) == {997}, durum(s))
api = Sahte(); api.inv[A]["products"][0]["offerings"][0]["quantity"] = 5
rc, s, _ = kos("yaz", api, sadece=A)
k("T19b adet tek deger degil -> ATLANDI_KAYMA", rc == 1 and durum(s) == {A: "ATLANDI_KAYMA"} and not api.yaz, s["ilanlar"][0].get("neden"))

# T20 RU geri alinamaz (eski RU ru_poster'dan kurulamiyor) -> yaz ATLANDI_KAYMA
P4 = W / "KURU_780"
shutil.copytree(PLAN, P4)
kb = json.loads((P4 / f"KURU_{A}.json").read_text(encoding="utf-8")); kb["ru_simdi"] += " elle"
(P4 / f"KURU_{A}.json").write_text(json.dumps(kb, ensure_ascii=False), encoding="utf-8")
api = Sahte(); api.ru[A]["description"] += " elle"
rc, s, _ = kos("yaz", api, plan=P4, damga="780", sadece=A)
k("T20 RU geri alinamaz -> ATLANDI_KAYMA, yazma 0", rc == 1 and durum(s) == {A: "ATLANDI_KAYMA"} and "geri alinamaz" in s["ilanlar"][0]["neden"]
  and not api.yaz, s["ilanlar"][0].get("neden"))

# T21 profil: 78 disi kullanan / tasiyici tanimli -> DUR
for ad, boz in (("78 disi kullanan", lambda x: x.update(pod78_disi_kullanan=["1"])),
                ("tasiyici tanimli", lambda x: x["au_once"][0].update(shipping_carrier_id=5))):
    P5 = W / "KURU_781"
    shutil.rmtree(P5, ignore_errors=True); shutil.copytree(PLAN, P5)
    pp2 = json.loads((P5 / "PROFIL_PLAN.json").read_text(encoding="utf-8")); boz(pp2)
    (P5 / "PROFIL_PLAN.json").write_text(json.dumps(pp2), encoding="utf-8")
    api = Sahte()
    try:
        kos("profil", api, plan=P5, damga="781"); d = None
    except SystemExit as e:
        d = str(e)
    k(f"T21 profil {ad} -> DUR, istek 0", d and d.startswith("DUR") and api.calls == 0, d)

# T22 secim: tekrarli sadece tek sayilir; hepsi haric -> DUR
api = Sahte()
rc, s, _ = kos("yaz", api, sadece=f"{A},{A}")
k("T22a --sadece A,A -> tek ilan", rc == 0 and len(s["ilanlar"]) == 1, durum(s))
try:
    kos("yaz", Sahte(), haric=f"{A},{B}"); d = None
except SystemExit as e:
    d = str(e)
k("T22b hepsi haric -> DUR", d and "secilen ilan yok" in d, d)

shutil.rmtree(W, ignore_errors=True)
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
