#!/usr/bin/env python3
"""BIZIM YILIMIZ: ayri kargo profili + SKU + aciklama (Serdar onayi 15 Eki 2026, A-D plani). ETSY'YE YAZAR (adim adim).
--adim profil : YENI kargo profili "BY Print 8x10 Worldwide" (ayni adla varsa olusturmaz, eksik hedefleri ekler):
                US 0 (3-8 gun), eu 0 (5-12), GB 0 (5-10), AU 5 (5-10), everywhere else 12 (7-21; 6 Eyl Mo kurali).
                Cikis US 28216. Eski poster profili 314711751541'e DOKUNULMAZ. Istek ~7.
--adim ilan --ciftler "CANCER_LIBRA ..." | HEPSI --profil ID :
                ilan basina: envanter GET -> stil-gorsel baglari GET (once) -> envanter PUT (SKU, sku_on_property [513,514];
                fiyat/stok/readiness/deger id'leri AYNI; price_on_property da [513,514] olur, fiyatlar ayni) -> updateListing PATCH yalniz {description, shipping_profile_id}
                -> stil-gorsel baglari GET (sonra, once ile ayni olmali). Yanitlarla dogrulama; ilk hatada DUR.
Tekrar kosu: aciklamasi ve profili zaten yeni olan ilan ATLANIR. Stil-gorsel bag okumasi ilk ilanda ve her 10. ilanda
(digerlerinde PUT yaniti deger id esitligi yeterli; CL 15 Eki: PUT baglari bozmadi). ETA satiri her ilanda.
Aciklama: ABOUT OUR DESIGNS bolumu silinir; FORMATS Shipped print satiri ve DELIVERY Shipped satiri degisir; RETURNS eklenir.
  Denetim: 'frame' YOK, uzun/orta tire YOK, tedarikci adi YOK; degisiklik disinda metin ayni.
--adim eski_kargo : eski 78 poster profili 314711751541'e CA 0, everywhere else 12, TR 18, IL 18, NO 14 (Serdar 15 Eki).
                KAPI: BY 78'in hicbiri o profilde degilse; once yedek, sonra mevcut hedefler birebir ayni kalmali. Istek ~8.
Guvenlik: yalniz listelenen uclar (Kilitli); ilan active degilse DUR; kota < 500 DUR.
Cikti: OUT/BY_KSA_<adim>.json (+ ONCE/SONRA aciklama .txt). Ortam: ETSY_*, TOKEN_FILE, TASLAK_CSV.
"""
import argparse
import csv
import html
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

KOTA_MIN = 500
ESKI_PROFIL = 314711751541
PROFIL_AD = "BY Print 8x10 Worldwide"
ORIGIN_ZIP = "28216"
# (anahtar, tur, kod, ucret, min gun, max gun)
HEDEF = [("US", "country", "US", 0, 3, 8), ("EU", "region", "eu", 0, 5, 12), ("GB", "country", "GB", 0, 5, 10),
         ("AU", "country", "AU", 5, 5, 10), ("EVERYWHERE", "region", "none", 12, 7, 21)]
P_STYLE, P_FORMAT = 513, 514
STIL_KOD = {"Starlit": "STARLIT", "Timeless": "TIMELESS", "First Page": "FIRSTPAGE", "Layers": "LAYERS", "Botanical": "BOTANICAL"}
FORMAT_KOD = {"Digital card 5x7": "CARD5X7", "Digital file 8x10": "FILE8X10", "Shipped print 8x10": "PRINT8X10"}

ESKI_SHIP_FMT = ("- Shipped print 8x10: printed on matte paper and shipped to you by our production partner. "
                 "Unframed; it fits standard frames.")
YENI_SHIP_FMT = ("- Shipped print 8x10: printed on premium matte art paper with long-lasting inks and shipped to you by "
                 "our production partner.")
ESKI_DELIV = ("- Shipped print: made and shipped within 4 to 7 days after your approval, with free shipping. "
              "Estimated delivery: US 3 to 8 days, UK and Australia 5 to 10 days, EU 5 to 12 days.")
YENI_DELIV = ("- Shipped print: made and shipped within 4 to 7 days after your approval, with free shipping to the US, UK "
              "and EU. Estimated delivery: US 3 to 8 days, UK and Australia 5 to 10 days, EU 5 to 12 days. For other "
              "countries, see the delivery estimate at checkout.")
RETURNS = ("RETURNS\nEvery item is personalized, so we can't accept returns or exchanges. Digital files can't be refunded "
           "once sent. If your print arrives damaged, send us a photo within 7 days and we'll replace it at no cost.")
YASAK = [(re.compile(r"frame", re.I), "frame"), (re.compile("[–—]"), "uzun/orta tire"),
         (re.compile(r"prodigi|printful|gelato|printify|shortrun|hahnem", re.I), "tedarikci adi")]


class Dur(Exception):
    pass


def kisa(cift):
    a, b = cift.split("_", 1)
    return f"{a[:3]}_{b[:3]}"


def sku(cift, stil, fmt):
    s = f"BY-{kisa(cift)}-{STIL_KOD[stil]}-{FORMAT_KOD[fmt]}"
    assert len(s) <= 32, s
    return s


def yeni_aciklama(d):
    """Canli aciklama (html unescape edilmis) -> yeni metin. Beklenen parcalar yoksa Dur."""
    t = d.replace("\r\n", "\n")
    for eski, yeni in ((ESKI_SHIP_FMT, YENI_SHIP_FMT), (ESKI_DELIV, YENI_DELIV)):
        if t.count(eski) != 1:
            raise Dur(f"aciklamada beklenen satir {t.count(eski)} kez: {eski[:50]}")
        t = t.replace(eski, yeni)
    m = re.search(r"\n\s*ABOUT OUR DESIGNS\n.*\Z", t, re.S)
    if not m:
        raise Dur("ABOUT OUR DESIGNS bolumu sonda bulunamadi")
    t = t[:m.start()].rstrip() + "\n\n" + RETURNS
    if "RETURNS" in d:
        raise Dur("aciklamada zaten RETURNS var")
    for rx, ad in YASAK:
        if rx.search(t):
            raise Dur(f"yeni aciklamada yasak: {ad}")
    return t


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else float(p)


def kur(store):
    from etsy_common import Etsy

    class Kilitli(Etsy):
        izin = []

        def _kontrol(self, method, path):
            if not any(m == method and re.match(p, path) for m, p in self.izin):
                raise SystemExit(f"YASAK: {method} {path}")

        def post(self, path, data):
            self._kontrol("POST", path); return super().post(path, data)

        def put_json(self, path, body):
            self._kontrol("PUT", path); return super().put_json(path, body)

        def patch(self, path, data):
            self._kontrol("PATCH", path)
            if set(data) - {"description", "shipping_profile_id"} or not data:
                raise SystemExit(f"YASAK PATCH alani: {sorted(data)}")
            return super().patch(path, data)

        def put(self, *a, **k):
            raise SystemExit("YASAK: PUT form")

        def post_json(self, *a, **k):
            raise SystemExit("YASAK: POST json")

        def post_file(self, *a, **k):
            raise SystemExit("YASAK: POST file")

        def delete(self, *a, **k):
            raise SystemExit("YASAK: DELETE")
    return Kilitli(store)


def kota(api):
    try:
        r = int(api.remaining)
    except (TypeError, ValueError):
        return
    if r < KOTA_MIN:
        raise Dur(f"KOTA {r} < {KOTA_MIN}")


def profil_adimi(api, shop, R):
    api.izin = [("POST", rf"^/shops/{shop}/shipping-profiles$"), ("POST", rf"^/shops/{shop}/shipping-profiles/\d+/destinations$")]
    lst = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    kota(api)
    var = [p for p in lst if p.get("title") == PROFIL_AD]
    if len(var) > 1:
        raise Dur(f"ayni adla {len(var)} profil var")
    if var:
        pid = var[0]["shipping_profile_id"]
        prof = var[0]
        R["olaylar"].append(f"profil zaten var {pid}")
    else:
        _, _, kod, ucret, dmin, dmax = HEDEF[0]
        body = {"title": PROFIL_AD, "origin_country_iso": "US", "origin_postal_code": ORIGIN_ZIP, "primary_cost": ucret,
                "secondary_cost": ucret, "min_processing_time": 4, "max_processing_time": 7, "processing_time_unit": "business_days",
                "destination_country_iso": kod, "min_delivery_days": dmin, "max_delivery_days": dmax}
        prof = api.post(f"/shops/{shop}/shipping-profiles", body) or {}
        pid = prof.get("shipping_profile_id")
        if not pid:
            raise Dur(f"profil olusmadi: {str(prof)[:200]}")
        R["olaylar"].append(f"profil olusturuldu {pid}")
    R["profil_id"] = pid

    def anahtar(x):
        cc = (x.get("destination_country_iso") or "").upper()
        rg = (x.get("destination_region") or "none").lower()
        return cc if cc else ("EVERYWHERE" if rg == "none" else rg.upper())
    have = {anahtar(x) for x in prof.get("shipping_profile_destinations") or []}
    for key, tur, kod, ucret, dmin, dmax in HEDEF:
        if key in have:
            continue
        body = {"primary_cost": ucret, "secondary_cost": ucret, "min_delivery_days": dmin, "max_delivery_days": dmax}
        body["destination_country_iso" if tur == "country" else "destination_region"] = kod
        api.post(f"/shops/{shop}/shipping-profiles/{pid}/destinations", body)
        R["olaylar"].append(f"hedef eklendi {key} {ucret} USD {dmin}-{dmax}")
        kota(api)
    son = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
    dest = {anahtar(x): (para(x.get("primary_cost")), para(x.get("secondary_cost")), x.get("min_delivery_days"), x.get("max_delivery_days"))
            for x in son.get("shipping_profile_destinations") or []}
    R["profil"] = dict(id=pid, baslik=son.get("title"), cikis=(son.get("origin_country_iso"), son.get("origin_postal_code")), hedefler=dest)
    bek = {k: (float(u), float(u), a, b) for k, _, _, u, a, b in HEDEF}
    if dest != bek:
        raise Dur(f"profil hedefleri beklenen degil: {dest} != {bek}")
    return pid


# Eski 78 poster profili dunya kargosu (Serdar karari 15 Eki): CA 0, everywhere else 12, TR 18, IL 18, NO 14 (AU 0 zaten var).
# Teslim: CA 5-10 (6 Eyl Mo kurali), digerleri 7-21 (6 Eyl Mo kurali, everywhere else).
ESKI_EK = [("CA", "country", "CA", 0, 5, 10), ("EVERYWHERE", "region", "none", 12, 7, 21), ("TR", "country", "TR", 18, 7, 21),
           ("IL", "country", "IL", 18, 7, 21), ("NO", "country", "NO", 14, 7, 21)]


def eski_kargo_adimi(api, shop, taslak, R, out):
    """KAPI: BY 78 ilanin HICBIRI eski profilde olmamali (once BY 77 tasinir). Yedek -> eksik hedefleri ekle -> geri okuma:
    mevcut hedefler birebir ayni, yeni hedefler beklenen."""
    api.izin = [("POST", rf"^/shops/{shop}/shipping-profiles/{ESKI_PROFIL}/destinations$")]
    ids = [r["listing_id"] for r in csv.DictReader(open(taslak)) if r.get("listing_id")]
    by = []
    for i in range(0, len(ids), 100):
        by += (api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100])}) or {}).get("results") or []
    kota(api)
    eskide = [x["listing_id"] for x in by if x.get("shipping_profile_id") == ESKI_PROFIL]
    R["by_eski_profilde"] = eskide
    if len(by) != len(ids) or eskide:
        raise Dur(f"KAPI: BY ilan okundu {len(by)}/{len(ids)}; eski profilde kalan {len(eskide)}")

    def anahtar(x):
        cc = (x.get("destination_country_iso") or "").upper()
        rg = (x.get("destination_region") or "none").lower()
        return cc if cc else ("EVERYWHERE" if rg == "none" else rg.upper())

    def imza(P):
        return {anahtar(x): (para(x.get("primary_cost")), para(x.get("secondary_cost")), x.get("min_delivery_days"), x.get("max_delivery_days"))
                for x in P.get("shipping_profile_destinations") or []}
    P0 = api.get(f"/shops/{shop}/shipping-profiles/{ESKI_PROFIL}") or {}
    (out / "ESKI_PROFIL_YEDEK.json").write_text(json.dumps(P0, indent=1, ensure_ascii=False), encoding="utf-8")
    i0 = imza(P0)
    R["once"] = i0
    for key, tur, kod, ucret, dmin, dmax in ESKI_EK:
        if key in i0:
            continue
        body = {"primary_cost": ucret, "secondary_cost": ucret, "min_delivery_days": dmin, "max_delivery_days": dmax}
        body["destination_country_iso" if tur == "country" else "destination_region"] = kod
        api.post(f"/shops/{shop}/shipping-profiles/{ESKI_PROFIL}/destinations", body)
        R["olaylar"].append(f"eski profile hedef eklendi {key} {ucret} USD {dmin}-{dmax}")
        kota(api)
    i1 = imza(api.get(f"/shops/{shop}/shipping-profiles/{ESKI_PROFIL}") or {})
    R["sonra"] = i1
    bek = dict(i0)
    bek.update({k: (float(u), float(u), a, b) for k, _, _, u, a, b in ESKI_EK if k not in i0})
    if i1 != bek:
        raise Dur(f"eski profil beklenen degil: {i1} != {bek}")
    print(f"::warning::ESKI PROFIL PASS {ESKI_PROFIL} | {i1}")


def kontrol_adimi(api, shop, pid, taslak, R, out):
    """SALT OKUMA: 78/78 toplu (1 istek) + yeni profil + eski profil + 3 ornek envanter SKU. ~6 istek."""
    api.izin = []
    rows = [r for r in csv.DictReader(open(taslak)) if r.get("listing_id")]
    L = {}
    ids = [str(r["listing_id"]) for r in rows]
    for i in range(0, len(ids), 100):
        for x in (api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100])}) or {}).get("results") or []:
            L[str(x["listing_id"])] = x
    sorun = {}
    for r in rows:
        x = L.get(str(r["listing_id"])) or {}
        d = html.unescape(x.get("description") or "")
        n = []
        if x.get("state") != "active":
            n.append(f"state {x.get('state')}")
        if str(x.get("shipping_profile_id")) != str(pid):
            n.append(f"profil {x.get('shipping_profile_id')}")
        if "ABOUT OUR DESIGNS" in d or "RETURNS" not in d or YENI_SHIP_FMT not in d or YENI_DELIV not in d:
            n.append("aciklama")
        for rx, ad in YASAK:
            if rx.search(d):
                n.append(ad)
        if n:
            sorun[r["cift"]] = n
    R["toplu"] = dict(okunan=len(L), toplam=len(rows), sorunlu=sorun)
    profiller = {}
    for p_ in (pid, ESKI_PROFIL):
        P = api.get(f"/shops/{shop}/shipping-profiles/{p_}") or {}
        profiller[str(p_)] = {((x.get("destination_country_iso") or "") or (x.get("destination_region") or "")): (
            para(x.get("primary_cost")), x.get("min_delivery_days"), x.get("max_delivery_days")) for x in P.get("shipping_profile_destinations") or []}
    R["profiller"] = profiller
    orn = {}
    for c in ("CANCER_LIBRA", "LEO_LEO", "SAGITTARIUS_SCORPIO"):
        r = next((r for r in rows if r["cift"] == c), None)
        if not r:
            continue
        inv = api.get(f"/listings/{r['listing_id']}/inventory") or {}
        sk = [p.get("sku") for p in inv.get("products") or []]
        orn[c] = dict(urun=len(sk), sku_dolu=sum(1 for s_ in sk if s_), dogru=sum(1 for p in inv.get("products") or []
                      if p.get("sku") == sku(c, *[{v["property_id"]: v["values"][0] for v in p.get("property_values") or []}[k] for k in (P_STYLE, P_FORMAT)])),
                      sku_on=inv.get("sku_on_property"))
    R["ornek_envanter"] = orn
    ok = not sorun and len(L) == len(rows) and all(v["dogru"] == 15 for v in orn.values())
    print(f"::warning::KONTROL {'PASS' if ok else 'FAIL'} | {len(rows) - len(sorun)}/{len(rows)} temiz | sorunlu {list(sorun)[:10]} | "
          f"ornek SKU {[(k, v['dogru']) for k, v in orn.items()]} | profiller {profiller}")
    if not ok:
        raise Dur("toplu kontrol FAIL")


def ilan_adimi(api, shop, ciftler, pid, taslak, R, out):
    if not pid:
        raise Dur("--profil gerekli")
    if int(pid) == ESKI_PROFIL:
        raise Dur("eski poster profili BY icin kullanilamaz")
    rows = {r["cift"]: r for r in csv.DictReader(open(taslak)) if r.get("listing_id")}
    if ciftler == ["HEPSI"]:
        ciftler = sorted(rows)
    eksik = [c for c in ciftler if c not in rows]
    if eksik:
        raise Dur(f"taslak listesinde yok: {eksik}")
    ids = [str(rows[c]["listing_id"]) for c in ciftler]
    api.izin = [("PUT", rf"^/listings/({'|'.join(ids)})/inventory$"), ("PATCH", rf"^/shops/{shop}/listings/({'|'.join(ids)})$")]
    L = {}
    for i in range(0, len(ids), 100):
        for x in (api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100])}) or {}).get("results") or []:
            L[str(x["listing_id"])] = x
    kota(api)
    import time
    t0, n_is = time.time(), 0
    for i, c in enumerate(ciftler, 1):
        lid = str(rows[c]["listing_id"])
        x = L.get(lid) or {}
        K = R["ilan"][c] = {"listing_id": lid, "link": f"https://www.etsy.com/listing/{lid}"}
        if x.get("state") != "active" or str(x.get("shop_id")) != str(shop):
            raise Dur(f"{c}: state {x.get('state')} shop {x.get('shop_id')}")
        d0 = html.unescape(x.get("description") or "")
        if "RETURNS" in d0 and str(x.get("shipping_profile_id")) == str(pid) and "ABOUT OUR DESIGNS" not in d0:
            K["sonuc"] = "ATLANDI_ZATEN_YAPILDI"       # tekrar kosuda yazilmaz (CL 15 Eki)
            continue
        d1 = yeni_aciklama(d0)
        n_is += 1
        bag_kontrol = n_is == 1 or n_is % 10 == 0 or len(ciftler) == 1   # hafif: ilk + her 10.; digerlerinde deger id esitligi
        (out / f"{c}_ACIKLAMA_ONCE.txt").write_text(d0, encoding="utf-8")
        (out / f"{c}_ACIKLAMA_SONRA.txt").write_text(d1, encoding="utf-8")

        inv = api.get(f"/listings/{lid}/inventory") or {}
        vi0 = ((api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []) if bag_kontrol else []
        bag0 = sorted((v.get("property_id"), v.get("value_id"), v.get("image_id")) for v in vi0)
        prods, once = [], {}
        for p in inv.get("products") or []:
            pv = {v["property_id"]: v for v in p.get("property_values") or []}
            st, fm = pv[P_STYLE]["values"][0], pv[P_FORMAT]["values"][0]
            o = (p.get("offerings") or [{}])[0]
            once[(st, fm)] = (para(o["price"]), o.get("quantity"), o.get("is_enabled"), o.get("readiness_state_id"),
                              pv[P_STYLE].get("value_ids"), pv[P_FORMAT].get("value_ids"))
            prods.append(dict(sku=sku(c, st, fm),
                              property_values=[dict(property_id=v["property_id"], property_name=v.get("property_name"),
                                                    value_ids=v.get("value_ids"), values=v.get("values"))
                                               for v in p.get("property_values") or []],
                              offerings=[dict(price=para(o["price"]), quantity=o.get("quantity"), is_enabled=o.get("is_enabled"),
                                              readiness_state_id=o.get("readiness_state_id"))]))
        if len(prods) != 15:
            raise Dur(f"{c}: urun {len(prods)} (15 beklenir)")
        govde = dict(products=prods, price_on_property=[P_STYLE, P_FORMAT],   # Etsy: sku_on 2 ozellikse price_on 0 ya da 2 (15 Eki 400)
                     quantity_on_property=inv.get("quantity_on_property") or [], sku_on_property=[P_STYLE, P_FORMAT],
                     readiness_state_on_property=inv.get("readiness_state_on_property") or [])
        inv2 = api.put_json(f"/listings/{lid}/inventory", govde) or {}
        kota(api)
        sonra, skular = {}, {}
        for p in inv2.get("products") or []:
            pv = {v["property_id"]: v for v in p.get("property_values") or []}
            st, fm = pv[P_STYLE]["values"][0], pv[P_FORMAT]["values"][0]
            o = (p.get("offerings") or [{}])[0]
            sonra[(st, fm)] = (para(o["price"]), o.get("quantity"), o.get("is_enabled"), o.get("readiness_state_id"),
                               pv[P_STYLE].get("value_ids"), pv[P_FORMAT].get("value_ids"))
            skular[(st, fm)] = p.get("sku")
        K["envanter"] = dict(urun=len(sonra), sku_on=inv2.get("sku_on_property"), sku=sorted(skular.values()))
        if sonra != once:
            raise Dur(f"{c}: envanter (fiyat/stok/readiness/deger id) degisti")
        if any(skular[k_] != sku(c, *k_) for k_ in skular) or sorted(inv2.get("sku_on_property") or []) != [P_STYLE, P_FORMAT]:
            raise Dur(f"{c}: SKU yazilmadi {skular}")

        y = api.patch(f"/shops/{shop}/listings/{lid}", {"description": d1, "shipping_profile_id": int(pid)}) or {}
        kota(api)
        K["patch"] = dict(state=y.get("state"), profil=y.get("shipping_profile_id"))
        if y.get("state") != "active":
            raise Dur(f"{c}: PATCH sonrasi state {y.get('state')}")
        if str(y.get("shipping_profile_id")) != str(pid):
            raise Dur(f"{c}: profil {y.get('shipping_profile_id')}")
        if html.unescape(y.get("description") or "").replace("\r\n", "\n") != d1:
            raise Dur(f"{c}: aciklama yanitla eslesmiyor")
        if (y.get("title"), y.get("tags")) != (x.get("title"), x.get("tags")):
            raise Dur(f"{c}: baslik/etiket degisti")
        if bag_kontrol:
            vi1 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
            bag1 = sorted((v.get("property_id"), v.get("value_id"), v.get("image_id")) for v in vi1)
            K["stil_gorsel_bag"] = dict(once=len(bag0), sonra=len(bag1), ayni=bag0 == bag1)
            if bag0 != bag1 or len(bag1) != 5:
                raise Dur(f"{c}: stil-gorsel baglari degisti/eksik {bag0} -> {bag1}")
        K["sonuc"] = "PASS"
        g = time.time() - t0
        print(f"[{i}/{len(ciftler)}] {c} {lid} PASS | SKU {len(skular)} | bag {'5 ayni' if bag_kontrol else 'deger id ayni'} | "
              f"gecen {g:.0f}s | kalan ~{g / i * (len(ciftler) - i):.0f}s | %{i / len(ciftler) * 100:.0f} | kota {api.remaining}", flush=True)
    n_pass = sum(1 for v in R["ilan"].values() if v.get("sonuc") == "PASS")
    n_atla = sum(1 for v in R["ilan"].values() if v.get("sonuc") == "ATLANDI_ZATEN_YAPILDI")
    print(f"::warning::ILAN PASS {n_pass} | atlandi {n_atla} | toplam {len(ciftler)} | profil {pid}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adim", required=True, choices=["profil", "ilan", "eski_kargo", "kontrol"])
    ap.add_argument("--ciftler", default="")
    ap.add_argument("--profil", default="")
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    from etsy_common import TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = kur(store)
    shop = os.environ["ETSY_SHOP_ID"]
    R = {"adim": a.adim, "olaylar": [], "ilan": {}}
    try:
        if a.adim == "profil":
            profil_adimi(api, shop, R)
            print(f"::warning::PROFIL PASS {R['profil_id']} | {R['profil']['hedefler']}")
        elif a.adim == "kontrol":
            kontrol_adimi(api, shop, a.profil, os.environ["TASLAK_CSV"], R, out)
        elif a.adim == "eski_kargo":
            eski_kargo_adimi(api, shop, os.environ["TASLAK_CSV"], R, out)
        else:
            ilan_adimi(api, shop, a.ciftler.split(), a.profil, os.environ["TASLAK_CSV"], R, out)
    except Dur as e:
        R["dur"] = str(e)
        print(f"::error::DURDU: {e}")
        raise SystemExit(4)
    finally:
        R["istek"], R["kota_son"] = api.calls, api.remaining
        (out / f"BY_KSA_{a.adim}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"::warning::BITTI {a.adim} | istek {api.calls} | kota {api.remaining}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
    except Exception as e:                                        # noqa: BLE001
        import traceback
        print(f"::error::{type(e).__name__}: {str(e)[:500]} | {traceback.format_exc()[-700:]}".replace("\n", " / "))
        raise SystemExit(1)
