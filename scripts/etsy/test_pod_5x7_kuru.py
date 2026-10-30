"""pod_5x7_kuru.py Serdar 30 Eki degisiklikleri (ag yok; sahte Etsy, canli ilan 4570143815'in 28 Eki kuru okumasi:
scripts/etsy/testdata_pod_5x7_kuru_4570143815.json = KURU_4570143815.json aciklama_ham / envanter / renk bagi / RU).
K1 EN: 9 degisiklik, PACKAGING paragrafi (baslik dahil) yok, kalan metin PASS
K2 RU: ru_poster.kur PASS, UPAKOVKA / tubus / konvert paragrafi yok
K3 YASAK_EN 'Printful' yakalar (EN'de Printful -> FAIL)
K4 CELISKI'de ambalaj yok; AU_YENI (7, 22)
K5 uctan uca kuru kosu (sahte Etsy, yazma cagrisi SystemExit): PASS, PROFIL_PLAN AU govdesi 7-22, OZET.md degisiklik satiri,
   KURU json en_satir ambalaj kaldirma, PLAN.csv en_degisiklik 9; Etsy'ye yazma 0
Calistir: python3 scripts/etsy/test_pod_5x7_kuru.py"""
import csv, json, os, sys, tempfile
from pathlib import Path
KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import pod_5x7_kuru as P  # noqa: E402
import etsy_common as E  # noqa: E402

F = json.loads((KOK / "testdata_pod_5x7_kuru_4570143815.json").read_text(encoding="utf-8"))
LID = str(F["listing"]["listing_id"])
sonuc = []


def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))


boylar = [P.BOYLAR[b] for b in dict.fromkeys(P.pv(p, 513).get("values", [None])[0] for p in F["inventory"]["products"]) if b in P.BOYLAR]
en0, en, ru, kr, satir, celiski, hata = P.aciklama_plani(F["listing"]["description"], boylar)
k("K1 EN 9 degisiklik, hata yok", len(satir) == 9 and not hata, (len(satir), hata))
k("K1 EN once PACKAGING var, sonra yok", "PACKAGING" in en0 and "PACKAGING" not in en and "rolled in tissue" not in en
  and "\n\n\n" not in en and "\n\nCHANGES\n" in en)
k("K1 kaldirilan satir: PACKAGING paragrafi, yeni bos",
  any(s["eski"].startswith("PACKAGING\nPrints are rolled") and s["yeni"] == "" for s in satir))
k("K2 RU kur PASS, ambalaj paragrafi yok", kr.get("pass_") and not any(w in ru for w in ("УПАКОВКА", "тубус", "конверт")),
  kr.get("hata"))
k("K2 RU paragraf sayisi EN ile ayni", kr.get("paragraf_en") == kr.get("paragraf_ru"), (kr.get("paragraf_en"), kr.get("paragraf_ru")))
_, _, _, _, _, _, h3 = P.aciklama_plani(F["listing"]["description"].replace("long-lasting inks", "long-lasting inks by Printful"), boylar)
k("K3 YASAK_EN 'Printful' -> FAIL", any("Printful" in h for h in h3) and P.YASAK_EN.search("printed by printful"), h3)
k("K4 CELISKI ambalaj yok, AU_YENI (7, 22)", not any("tissue" in c for c, _ in P.CELISKI) and P.AU_YENI == (7, 22))

# K5 uctan uca (sahte Etsy)
yazma = []
AU = {"shipping_profile_destination_id": 11, "destination_country_iso": "AU", "min_delivery_days": 7, "max_delivery_days": 21,
      "primary_cost": {"amount": 0, "divisor": 100, "currency_code": "USD"}, "secondary_cost": {"amount": 0, "divisor": 100, "currency_code": "USD"}}
US = dict(AU, shipping_profile_destination_id=12, destination_country_iso="US", min_delivery_days=3, max_delivery_days=8)


class FE:
    remaining = 5000
    calls = 0

    def __init__(s, store):
        pass

    def kota_kapisi(s, *a, **k):
        pass

    def _call(s, method, path, *a, **k):
        if method != "GET":
            yazma.append((method, path))
        return {}

    def get(s, path, params=None, ok404=False):
        s.calls += 1
        if path == f"/listings/{LID}":
            return F["listing"]
        if path.endswith("/inventory"):
            return F["inventory"]
        if path.endswith("/variation-images"):
            return {"results": F["variation_images"]}
        if path.endswith("/translations/ru"):
            return F["ru"]
        if "/shipping-profiles/" in path:
            return {"title": "sahte", "shipping_profile_destinations": [AU, US]}
        if path.endswith("/listings/active"):
            return {"count": 1, "results": [{"listing_id": int(LID), "shipping_profile_id": P.PROFIL}]}
        return {"results": []}


class FS:
    def __init__(s, *a):
        pass

    def needs_refresh(s):
        return False


E.Etsy, E.TokenStore = FE, FS
os.environ.update(TOKEN_FILE="/dev/null", ETSY_SHOP_ID="1")
W = Path(tempfile.mkdtemp(prefix="kuru5x7_"))
sys.argv = ["k", "--ids", LID, "--pilot", LID, "--out", str(W)]
rc = P.main()
pp = json.loads((W / "PROFIL_PLAN.json").read_text(encoding="utf-8"))
oz = (W / "OZET.md").read_text(encoding="utf-8")
kj = json.loads((W / f"KURU_{LID}.json").read_text(encoding="utf-8"))
pl = list(csv.DictReader(open(W / "PLAN.csv", encoding="utf-8")))
k("K5 kuru kosu PASS (rc 0)", rc == 0 and kj["PASS"], kj.get("hata"))
k("K5 PROFIL_PLAN AU govdesi 7-22, yalniz AU hedefi",
  [x["govde"]["min_delivery_days"] for x in pp["yazim_istegi"]] == [7] and [x["govde"]["max_delivery_days"] for x in pp["yazim_istegi"]] == [22]
  and len(pp["yazim_istegi"]) == 1 and pp["yazim_istegi"][0]["yol"].endswith("/destinations/11"), pp["yazim_istegi"])
k("K5 OZET: AU -> (7, 22) + 30 Eki satiri + uyari", "-> (7, 22)" in oz and "Serdar 30 Eki degisiklikleri" in oz and "20-22 gun" in oz)
k("K5 OZET ilan satiri: ambalaj kaldirilir", "EN eski: PACKAGING" in oz and "(satir kaldirilir)" in oz)
k("K5 PLAN.csv en_degisiklik 9", pl and pl[0]["en_degisiklik"] == "9", pl[0] if pl else None)
k("K5 KURU json RU ambalajsiz", "УПАКОВКА" not in kj["ru_yeni"] and "УПАКОВКА" in kj["ru_simdi"])
k("K5 Etsy'ye yazma cagrisi 0", not yazma, yazma)
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
