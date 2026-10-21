#!/usr/bin/env python3
"""BIZIM YILIMIZ: "Shipped print 8x10" secenegini ve metnini kaldirir (Serdar 21 Eki karar 5). ETSY'YE YAZAR, TEK ILAN.
Baski yolu tedarikci kararindan sonra yeniden acilir. Toplu kullanim YOK: --cift tek cift alir.
Ilan basina: listing GET (state active degilse DUR: updateListing taslagi yayina alir) -> aciklama planlanir (beklenen parcalar
yoksa yazmadan DUR) -> envanter GET (15 urun) -> envanter PUT (Shipped print 8x10 urunleri cikar; kalan 10 urunun fiyat/stok/
SKU/readiness/deger id'leri AYNI) -> updateListing PATCH yalniz {description} -> geri okuma: state, baslik, etiket, kargo profili,
stil-gorsel baglari degismemis; aciklamada baski vaadi (VAAT) 0; envanter 10 urun.
Yedek: OUT/ONCE_ENVANTER.json, ONCE_ACIKLAMA.txt (geri donus bunlardan). Kota < 10 DUR. Sir loga yazilmaz.
Ortam: ETSY_*, TOKEN_FILE, TASLAK_CSV. Cikti: OUT/BY_BASKI_KALDIR.json."""
import argparse
import csv
import html
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

KOTA_MIN = 10  # Serdar 15 Eki: Etsy kota tabani 10
P_STYLE, P_FORMAT = 513, 514
BASKI = "Shipped print 8x10"
DEGIS = [  # (eski, yeni) her biri aciklamada TAM 1 kez olmali
    ("As soon as you approve it, we prepare your file or your print.", "As soon as you approve it, we prepare your file."),
    (" If your print arrives damaged, send us a photo within 7 days and we'll replace it at no cost.", ""),
]
SATIR_SIL = re.compile(r"^- Shipped print[^\n]*\n?", re.M)  # DELIVERY + FORMATS satirlari (2 beklenir)
VAAT = re.compile(r"shipped print|shipped to you|made and shipped|free shipping|arrives damaged|your print", re.I)  # "Nothing is shipped" mesru
YASAK = [(VAAT, "baski vaadi"), (re.compile("[–—]"), "uzun/orta tire")]


class Dur(Exception):
    pass


def yeni_aciklama(d0):
    t = d0.replace("\r\n", "\n")
    for eski, yeni in DEGIS:
        if t.count(eski) != 1:
            raise Dur(f"aciklamada beklenen parca {t.count(eski)} kez: {eski[:50]}")
        t = t.replace(eski, yeni)
    n = len(SATIR_SIL.findall(t))
    if n != 2:
        raise Dur(f"'- Shipped print' satiri {n} kez (2 beklenir)")
    t = SATIR_SIL.sub("", t)
    for rx, ad in YASAK:
        if rx.search(t):
            raise Dur(f"yeni aciklamada kalan: {ad}")
    return t


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else float(p)


def imza(inv):
    s = {}
    for p in inv.get("products") or []:
        pv = {v["property_id"]: v for v in p.get("property_values") or []}
        o = (p.get("offerings") or [{}])[0]
        s[(pv[P_STYLE]["values"][0], pv[P_FORMAT]["values"][0])] = (
            p.get("sku"), para(o["price"]), o.get("quantity"), o.get("is_enabled"), o.get("readiness_state_id"),
            tuple(pv[P_STYLE].get("value_ids") or []), tuple(pv[P_FORMAT].get("value_ids") or []))
    return s


def kur(store, lid, shop):
    from etsy_common import Etsy

    class Kilitli(Etsy):
        def put_json(self, path, body):
            if path != f"/listings/{lid}/inventory":
                raise SystemExit(f"YASAK: PUT {path}")
            return super().put_json(path, body)

        def patch(self, path, data):
            if path != f"/shops/{shop}/listings/{lid}" or set(data) != {"description"}:
                raise SystemExit(f"YASAK: PATCH {path} {sorted(data)}")
            return super().patch(path, data)

        def post(self, *a, **k):
            raise SystemExit("YASAK: POST")

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


def calis(api, shop, lid, out, R):
    x = api.get(f"/listings/{lid}", params={"includes": "Images"}) or {}
    kota(api)
    R["once"] = dict(state=x.get("state"), baslik=x.get("title"), etiket=x.get("tags"), profil=x.get("shipping_profile_id"))
    if x.get("state") != "active" or str(x.get("shop_id")) != str(shop):
        raise Dur(f"state {x.get('state')} / shop uyusmuyor: yazma yok (taslak yayina alinmaz)")
    d0 = html.unescape(x.get("description") or "").replace("\r\n", "\n")
    (out / "ONCE_ACIKLAMA.txt").write_text(d0, encoding="utf-8")
    d1 = yeni_aciklama(d0)
    (out / "SONRA_ACIKLAMA_PLAN.txt").write_text(d1, encoding="utf-8")
    R["bilgi"] = dict(baslikta_print=bool(re.search(r"print", x.get("title") or "", re.I)),
                      etikette_print=[t for t in x.get("tags") or [] if re.search(r"print", t, re.I)],
                      alt_metin_print_ship=sum(1 for i in x.get("images") or [] if re.search(r"print|ship", i.get("alt_text") or "", re.I)))
    inv = api.get(f"/listings/{lid}/inventory") or {}
    (out / "ONCE_ENVANTER.json").write_text(json.dumps(inv, indent=1, ensure_ascii=False), encoding="utf-8")
    i0 = imza(inv)
    if len(i0) != 15 or sum(1 for k in i0 if k[1] == BASKI) != 5:
        raise Dur(f"envanter {len(i0)} urun, baski {sum(1 for k in i0 if k[1] == BASKI)} (15/5 beklenir)")
    vi0 = sorted((v.get("property_id"), v.get("value_id"), v.get("image_id"))
                 for v in (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or [])
    kota(api)
    prods = []
    for p in inv.get("products") or []:
        pv = {v["property_id"]: v for v in p.get("property_values") or []}
        if pv[P_FORMAT]["values"][0] == BASKI:
            continue
        o = (p.get("offerings") or [{}])[0]
        prods.append(dict(sku=p.get("sku") or "",
                          property_values=[dict(property_id=v["property_id"], property_name=v.get("property_name"),
                                                value_ids=v.get("value_ids"), values=v.get("values")) for v in p.get("property_values") or []],
                          offerings=[dict(price=para(o["price"]), quantity=o.get("quantity"), is_enabled=o.get("is_enabled"),
                                          readiness_state_id=o.get("readiness_state_id"))]))
    govde = dict(products=prods, price_on_property=inv.get("price_on_property") or [],
                 quantity_on_property=inv.get("quantity_on_property") or [], sku_on_property=inv.get("sku_on_property") or [],
                 readiness_state_on_property=inv.get("readiness_state_on_property") or [])
    inv2 = api.put_json(f"/listings/{lid}/inventory", govde) or {}
    kota(api)
    i1 = imza(inv2)
    bek = {k: v for k, v in i0.items() if k[1] != BASKI}
    R["envanter"] = dict(once=len(i0), sonra=len(i1), ayni=i1 == bek)
    if i1 != bek:
        raise Dur("envanter: kalan 10 urun degisti ya da baski urunu kaldi")
    y = api.patch(f"/shops/{shop}/listings/{lid}", {"description": d1}) or {}
    kota(api)
    son = api.get(f"/listings/{lid}") or {}
    vi1 = sorted((v.get("property_id"), v.get("value_id"), v.get("image_id"))
                 for v in (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or [])
    d2 = html.unescape(son.get("description") or "").replace("\r\n", "\n")
    (out / "SONRA_ACIKLAMA.txt").write_text(d2, encoding="utf-8")
    R["sonra"] = dict(state=son.get("state"), baslik_ayni=son.get("title") == x.get("title"), etiket_ayni=son.get("tags") == x.get("tags"),
                      profil=son.get("shipping_profile_id"), aciklama_plan_ile_ayni=d2 == d1, baski_vaadi_kalan=len(VAAT.findall(d2)),
                      stil_gorsel_bag=dict(once=len(vi0), sonra=len(vi1), ayni=vi0 == vi1), patch_state=y.get("state"))
    s = R["sonra"]
    ok = (s["state"] == "active" and s["baslik_ayni"] and s["etiket_ayni"] and str(s["profil"]) == str(R["once"]["profil"])
          and s["aciklama_plan_ile_ayni"] and s["baski_vaadi_kalan"] == 0 and s["stil_gorsel_bag"]["ayni"])
    R["sonuc"] = "PASS" if ok else "FAIL"
    if not ok:
        raise Dur(f"geri okuma FAIL: {s}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cift", required=True)
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = {r["cift"]: r for r in csv.DictReader(open(os.environ["TASLAK_CSV"])) if r.get("listing_id")}
    if a.cift not in rows or len(a.cift.split()) != 1:
        raise SystemExit(f"HATA: tek cift gerekli, listede yok: {a.cift}")
    lid, shop = str(rows[a.cift]["listing_id"]), os.environ["ETSY_SHOP_ID"]
    from etsy_common import TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = kur(store, lid, shop)
    R = {"cift": a.cift, "listing_id": lid, "link": f"https://www.etsy.com/listing/{lid}"}
    try:
        calis(api, shop, lid, out, R)
    except Dur as e:
        R["dur"] = str(e)
        print(f"::error::DURDU: {e}")
        raise SystemExit(4)
    finally:
        R["istek"], R["kota_son"] = api.calls, api.remaining
        (out / "BY_BASKI_KALDIR.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"::warning::{a.cift} {lid} PASS | envanter 15->10 | baski vaadi 0 | istek {api.calls} | kota {api.remaining} | bilgi {R['bilgi']}")


if __name__ == "__main__":
    main()
