#!/usr/bin/env python3
"""BIZIM YILIMIZ: "Shipped print 8x10" ($29) secenegini ve aciklamadaki baski metnini GERI EKLER.
Serdar onayi 24 Eki 2026 (Genel Merkez): tedarikci Printful (ana) + Shortrun (ABD yedek); baski secenegi geri gelir.
by_baski_kaldir.py'nin (21 Eki karar 5) tersi. Metin, CANCER_LIBRA yedeginden (Drive TEMP/BY_BASKI_KALDIR_20261021/
CANCER_LIBRA/ONCE_ACIKLAMA.txt) birebir alinan satirlardir.

Ilan basina: listing GET (active degilse DOKUNMA) -> envanter GET (10 urun: 5 stil x kart+dosya bekler) -> aciklama plani
(beklenen her parca TAM 1 kez, yoksa yazmadan DUR) -> envanter PUT (mevcut 10 urun AYNEN + 5 stil x "Shipped print 8x10" 29.00)
-> updateListing PATCH yalniz {description} -> geri okuma: 15 urun, eski 10 urun ayni, baski 5 x 29.00, stil-gorsel baglari
ayni (bozulduysa ayni degerlerle geri yazilir), state/baslik/etiket/kargo profili ayni, aciklama plan ile ayni.
Modlar: oku (plan, yazma yok) | yaz (--confirm BASKI_EKLE; --hepsi icin BASKI_EKLE_HEPSI). Ilk FAIL'de DUR.
"""
import argparse
import html
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

P_STYLE, P_FORMAT = 513, 514
BASKI, FIYAT = "Shipped print 8x10", 29.00
BOLUM = 60895624
ONAY, ONAY_HEPSI = "BASKI_EKLE", "BASKI_EKLE_HEPSI"
ISTEK_TAHMIN = 10
OUT = Path("out")

SATIR_TESLIM = ("- Shipped print: made and shipped within 4 to 7 days after your approval, with free shipping to the US, UK "
                "and EU. Estimated delivery: US 3 to 8 days, UK and Australia 5 to 10 days, EU 5 to 12 days. For other "
                "countries, see the delivery estimate at checkout.")
SATIR_FORMAT = ("- Shipped print 8x10: printed on premium matte art paper with long-lasting inks and shipped to you by our "
                "production partner.")
DEGIS = [  # (simdiki, yeni): simdiki TAM 1 kez olmali
    ("As soon as you approve it, we prepare your file.", "As soon as you approve it, we prepare your file or your print."),
    ("Digital files can't be refunded once sent.",
     "Digital files can't be refunded once sent. If your print arrives damaged, send us a photo within 7 days and we'll "
     "replace it at no cost."),
]
SONRASINA = [  # (bu satirdan sonra, eklenecek satir); bu satir TAM 1 kez olmali
    ("- Digital card and digital file: sent in Etsy Messages as soon as you approve your preview.", SATIR_TESLIM),
    ("- Digital file 8x10: an 8x10 inch, 300 dpi JPG for your own printing. Nothing is shipped.", SATIR_FORMAT),
]
YASAK = [(re.compile("[–—]"), "uzun/orta tire"), (re.compile(r"hahnem|photo rag|gicl[eé]e|prodigi|printful|shortrun", re.I),
                                                          "yasak marka/kagit")]


class Dur(Exception):
    pass


def log(m):
    print(m, flush=True)


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else round(float(p), 2)


def yeni_aciklama(d0):
    t = d0.replace("\r\n", "\n")
    if "Shipped print" in t or "your print" in t:
        return None                                        # zaten baski metni var
    for eski, yeni in DEGIS:
        if t.count(eski) != 1:
            raise Dur(f"aciklamada beklenen parca {t.count(eski)} kez: {eski[:50]}")
        t = t.replace(eski, yeni)
    satirlar = t.split("\n")
    for once, ekle in SONRASINA:
        idx = [i for i, s in enumerate(satirlar) if s.strip() == once]
        if len(idx) != 1:
            raise Dur(f"aciklamada satir {len(idx)} kez: {once[:50]}")
        satirlar.insert(idx[0] + 1, ekle)
    t = "\n".join(satirlar)
    for rx, ad in YASAK:
        if rx.search(t):
            raise Dur(f"yeni aciklamada {ad}")
    return t


def imza(inv):
    s = {}
    for p in inv.get("products") or []:
        pv = {v["property_id"]: v for v in p.get("property_values") or []}
        o = (p.get("offerings") or [{}])[0]
        s[(pv[P_STYLE]["values"][0], pv[P_FORMAT]["values"][0])] = (
            p.get("sku") or "", para(o["price"]), o.get("quantity"), bool(o.get("is_enabled")), o.get("readiness_state_id"))
    return s


def govde(inv):
    """Mevcut urunler AYNEN; her stilin son urunundan sonra o stilin baski urunu eklenir."""
    urunler, stiller, rs = [], [], None
    for p in inv.get("products") or []:
        pv = {v["property_id"]: v for v in p.get("property_values") or []}
        st = pv[P_STYLE]["values"][0]
        if st not in stiller:
            stiller.append(st)
        o = (p.get("offerings") or [{}])[0]
        rs = rs or o.get("readiness_state_id")
        urunler.append(dict(sku=p.get("sku") or "",
                            property_values=[dict(property_id=v["property_id"], property_name=v.get("property_name"),
                                                  value_ids=v.get("value_ids"), values=v.get("values"))
                                             for v in p.get("property_values") or []],
                            offerings=[dict(price=para(o["price"]), quantity=o.get("quantity"), is_enabled=bool(o.get("is_enabled")),
                                            readiness_state_id=o.get("readiness_state_id"))]))
    son = []
    for st in stiller:
        grup = [u for u in urunler if u["property_values"][[v["property_id"] for v in u["property_values"]].index(P_STYLE)]["values"][0] == st]
        stil_pv = next(v for v in grup[0]["property_values"] if v["property_id"] == P_STYLE)
        son += grup + [dict(sku="", property_values=[dict(property_id=P_STYLE, property_name=stil_pv.get("property_name") or "Style",
                                                          value_ids=stil_pv.get("value_ids"), values=stil_pv.get("values")),
                                                     dict(property_id=P_FORMAT, property_name="Format", values=[BASKI])],
                                 offerings=[dict(price=FIYAT, quantity=999, is_enabled=True, readiness_state_id=rs)])]
    return dict(products=son, price_on_property=inv.get("price_on_property") or [],
                quantity_on_property=inv.get("quantity_on_property") or [], sku_on_property=inv.get("sku_on_property") or [],
                readiness_state_on_property=inv.get("readiness_state_on_property") or []), stiller, rs


def vimg(api, shop, lid):
    return sorted((v.get("property_id"), v.get("value_id"), v.get("image_id"))
                  for v in (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or [])


def bolum_ids(api, shop):
    ids, off = [], 0
    while True:
        d = api.get(f"/shops/{shop}/shop-sections/listings", params={"shop_section_ids": BOLUM, "limit": 100, "offset": off}) or {}
        r = d.get("results") or []
        ids += [str(x.get("listing_id")) for x in r if x.get("listing_id")]
        if len(r) < 100:
            break
        off += 100
    ids = list(dict.fromkeys(ids))
    if len(ids) != 78:
        raise SystemExit(f"DUR: bolum {BOLUM} ilan sayisi {len(ids)} (78 bekleniyordu)")
    return ids


def ilan(api, shop, lid, yaz, out):
    R = {"ilan": lid}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    i0 = imza(inv)
    if sum(1 for k in i0 if k[1] == BASKI) == 5 and len(i0) == 15:
        R["durum"] = "ZATEN"
        return R
    x = api.get(f"/listings/{lid}") or {}
    R["once"] = dict(state=x.get("state"), profil=x.get("shipping_profile_id"), tip=x.get("listing_type"))
    if x.get("state") != "active" or str(x.get("shop_id")) != str(shop):
        R["durum"] = "ATLANDI_STATE"
        return R
    if not x.get("shipping_profile_id"):
        raise Dur("kargo profili yok (fiziksel baski satilamaz)")
    if len(i0) != 10 or {k[1] for k in i0} != {"Digital card 5x7", "Digital file 8x10"} or len({k[0] for k in i0}) != 5:
        raise Dur(f"envanter beklenen yapida degil: {len(i0)} urun, formatlar {sorted({k[1] for k in i0})}")
    if {v[1] for v in i0.values()} != {3.90, 4.90}:
        raise Dur(f"dijital fiyatlar beklenen degil: {sorted({v[1] for v in i0.values()})}")
    d0 = html.unescape(x.get("description") or "").replace("\r\n", "\n")
    d1 = yeni_aciklama(d0)
    body, stiller, rs = govde(inv)
    v0 = vimg(api, shop, lid)
    d = out / lid
    d.mkdir(parents=True, exist_ok=True)
    (d / "ONCE.json").write_text(json.dumps({"listing": x, "inventory": inv, "vimg": v0}, ensure_ascii=False, indent=1), encoding="utf-8")
    (d / "PUT.json").write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    if d1:
        (d / "ACIKLAMA_PLAN.txt").write_text(d1, encoding="utf-8")
    R.update(stil=stiller, readiness=rs, aciklama_degisecek=bool(d1), urun_plan=len(body["products"]))
    if not yaz:
        R["durum"] = "PLAN_OK"
        return R
    if api.remaining is not None and int(api.remaining) < ISTEK_TAHMIN + 10:
        R["durum"] = f"DUR_KOTA kalan {api.remaining}"
        return R
    api.put_json(f"/listings/{lid}/inventory", body)
    if d1:
        api.patch(f"/shops/{shop}/listings/{lid}", {"description": d1})
    # geri okuma
    inv2 = api.get(f"/listings/{lid}/inventory") or {}
    x2 = api.get(f"/listings/{lid}") or {}
    v2 = vimg(api, shop, lid)
    i2 = imza(inv2)
    f = []
    if len(i2) != 15:
        f.append(f"urun {len(i2)} != 15")
    if {k: v for k, v in i2.items() if k[1] != BASKI} != i0:
        f.append("eski 10 urun degisti")
    bask = {k: v for k, v in i2.items() if k[1] == BASKI}
    if len(bask) != 5 or any(v[1] != FIYAT or not v[3] for v in bask.values()):
        f.append(f"baski urunleri hatali: {bask}")
    onarim = "gerekmedi"
    if v2 != v0:
        # stil value_id degismediyse ayni degerlerle geri yaz
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                      {"variation_images": [{"property_id": p, "value_id": v, "image_id": i} for p, v, i in v0]})
        v2 = vimg(api, shop, lid)
        onarim = "geri yazildi"
        if v2 != v0:
            f.append("stil-gorsel baglari geri yazilamadi")
    d2 = html.unescape(x2.get("description") or "").replace("\r\n", "\n")
    if d1 and d2 != d1:
        f.append("aciklama plan ile ayni degil")
    for k in ("state", "title", "tags", "shipping_profile_id", "listing_type"):
        if x2.get(k) != x.get(k):
            f.append(f"{k} degisti")
    R.update(hatalar=f, onarim=onarim, durum="PASS" if not f else "FAIL", kota=api.remaining)
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["oku", "yaz"])
    ap.add_argument("--ilanlar", default="")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    yaz = a.mod == "yaz"
    if yaz and a.confirm != (ONAY_HEPSI if a.hepsi else ONAY):
        raise SystemExit(f"DUR: yaz icin --confirm {ONAY_HEPSI if a.hepsi else ONAY}")
    from etsy_common import Etsy, TokenStore, mask
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]
    OUT.mkdir(exist_ok=True)
    tum = bolum_ids(api, shop)
    if a.hepsi:
        ids = tum
    else:
        ids = [x.strip() for x in a.ilanlar.split(",") if x.strip()]
        if not ids or [x for x in ids if x not in tum]:
            raise SystemExit("DUR: ilan listesi bos ya da yil donumu bolumu disinda")
    sonuc, t0 = [], time.time()
    for i, lid in enumerate(ids, 1):
        try:
            api.kota_kapisi(f"ilan {lid}")
            R = ilan(api, shop, lid, yaz, OUT)
        except (Dur, SystemExit) as e:
            R = {"ilan": lid, "durum": f"FAIL_DUR: {str(e)[:400]}"}
        sonuc.append(R)
        g = time.time() - t0
        log(f"[{i}/{len(ids)}] {100 * i // len(ids)}% gecen {g:.0f}s kalan ~{g / i * (len(ids) - i):.0f}s | {lid} {R['durum']} kota={api.remaining}")
        if R["durum"].startswith(("FAIL", "DUR")):
            break
    say = {}
    for r in sonuc:
        say[r["durum"].split(" ")[0].rstrip(":")] = say.get(r["durum"].split(" ")[0].rstrip(":"), 0) + 1
    tamam = len(sonuc) == len(ids) and not any(r["durum"].startswith(("FAIL", "DUR", "ATLANDI")) for r in sonuc)
    oz = {"mod": a.mod, "istenen": len(ids), "islenen": len(sonuc), "sayim": say, "kota_son": api.remaining,
          "durum": "PASS" if tamam else "FAIL", "ilanlar": sonuc}
    (OUT / f"BY_BASKI_EKLE_{a.mod.upper()}.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    log("OZET " + json.dumps({k: v for k, v in oz.items() if k != "ilanlar"}, ensure_ascii=False))
    sys.exit(0 if tamam else 1)


if __name__ == "__main__":
    main()
