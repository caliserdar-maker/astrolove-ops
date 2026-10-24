#!/usr/bin/env python3
"""BY78 YAYINDAKI 78 ILAN AYAR DENETIMI (15 Eki 2026, Serdar). SALT OKUR: Etsy API'ye yalniz GET; yazma metodu YOK.
Istek (~7): 1 toplu getListingsByListingIds (includes=images,videos,personalization) + 2 ornek envanter
  + kargo profili + iade politikasi + hazirlik durumlari + uretim ortaklari. Kota tabani 500 (altindaysa baslamaz).
Cikti: <OUT>/DENETIM.csv (ilan basina), <OUT>/DENETIM.json (genel + ornek), <OUT>/DENETIM.md (sorun listesi).
Kullanim: by78_denetim.py --taslak BY78_TASLAKLAR.csv --out DIR"""
import argparse
import csv
import html
import json
import os
import re
import sys
from pathlib import Path

SECTION, SHIP, RET, TAX, PARTNER = 60895624, 314711751541, 1513990287785, 121, 5817638
WHO, WHEN = "i_did", "made_to_order"
MATERIALS = ["matte paper", "ink"]
FIYAT = {"Digital card 5x7": 5.0, "Digital file 8x10": 9.0, "Shipped print 8x10": 29.0}
STYLES = ["Starlit", "Timeless", "First Page", "Layers", "Botanical"]
P_STYLE, P_FORMAT = 513, 514
KOTA_MIN = 10  # Serdar 15 Eki: Etsy kota tabani 10
ORNEK = ["CANCER_LIBRA", "LEO_LEO"]
TIRE = re.compile("[–—]")


def kutular_beklenen(cift):
    a, b = (p.capitalize() for p in cift.split("_", 1))
    l1, l2 = ("Name on the left", "Name on the right") if a == b else (f"Name under {a}", f"Name under {b}")
    return [(l1, True, 11), (l2, True, 11), ("Your special date", True, 20), ("Heading", True, 20), ("Optional short line", False, 20)]


def para(m):
    if isinstance(m, dict) and m.get("divisor"):
        return round(m["amount"] / m["divisor"], 2)
    return m


def ilan_denetle(cift, x):
    n = []
    if x.get("state") != "active":
        n.append(f"state {x.get('state')}")
    t = html.unescape(x.get("title") or "")
    if len(t) > 140:
        n.append(f"baslik {len(t)} karakter")
    if TIRE.search(t):
        n.append("baslikta uzun tire")
    tags = x.get("tags") or []
    if len(tags) != 13:
        n.append(f"etiket {len(tags)}")
    if (x.get("materials") or []) != MATERIALS:
        n.append(f"materials {x.get('materials')}")
    for ad, bek in (("taxonomy_id", TAX), ("shop_section_id", SECTION), ("who_made", WHO), ("when_made", WHEN),
                    ("shipping_profile_id", SHIP), ("return_policy_id", RET)):
        if x.get(ad) != bek:
            n.append(f"{ad} {x.get(ad)} (beklenen {bek})")
    if x.get("is_supply") is not False:
        n.append(f"is_supply {x.get('is_supply')}")
    if (x.get("processing_min"), x.get("processing_max")) != (4, 7):
        n.append(f"islem {x.get('processing_min')}-{x.get('processing_max')}")
    pp = [p.get("production_partner_id") for p in x.get("production_partners") or []]
    if pp != [PARTNER]:
        n.append(f"production partner {pp}")
    if not x.get("is_personalizable"):
        n.append("kisisellestirme kapali")
    per = ((x.get("personalization") or {}).get("personalization_questions")) or x.get("personalization_questions") or []
    kut = [(q.get("question_text"), bool(q.get("required")), q.get("max_allowed_characters")) for q in per]
    if kut != kutular_beklenen(cift):
        n.append(f"kisisellestirme {kut}")
    ims = sorted(x.get("images") or [], key=lambda y: y.get("rank") or 0)
    if len(ims) != 13:
        n.append(f"gorsel {len(ims)}")
    if ims and (ims[0].get("full_width"), ims[0].get("full_height")) != (2400, 2400):
        n.append(f"rank 1 {ims[0].get('full_width')}x{ims[0].get('full_height')}")
    vids = x.get("videos") or []
    if len(vids) != 1:
        n.append(f"video {len(vids)}")
    d = html.unescape(x.get("description") or "")
    if TIRE.search(d):
        n.append("aciklamada uzun tire")
    return n, dict(baslik_uzunluk=len(t), etiket=len(tags), gorsel=len(ims), video=len(vids), kutu=len(per),
                   about=("ABOUT OUR DESIGNS" in d), free_shipping=bool(re.search(r"free shipping", d, re.I)),
                   aciklama_uzunluk=len(d))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taslak", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    taslak = list(csv.DictReader(open(a.taslak, encoding="utf-8-sig")))
    ids = [r["listing_id"].strip() for r in taslak]

    # 1) toplu okuma
    L = {}
    for i in range(0, len(ids), 100):
        d = api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100]), "includes": "images,videos,personalization"}) or {}
        for x in d.get("results") or []:
            L[str(x.get("listing_id"))] = x
    kota_bas = int(api.remaining or 0)
    print(f"toplu okuma: {len(L)}/{len(ids)} ilan | kota {kota_bas}", flush=True)
    if kota_bas < KOTA_MIN:
        raise SystemExit(f"HATA: kota {kota_bas} < {KOTA_MIN}; diger okumalar yapilmadi")

    satir, sorunlu = [], []
    for r in taslak:
        c, lid = r["cift"].strip(), r["listing_id"].strip()
        x = L.get(lid)
        if not x:
            n, ay = ["toplu okumada yok"], {}
        else:
            n, ay = ilan_denetle(c, x)
        satir.append(dict(cift=c, listing_id=lid, sonuc="FAIL" if n else "PASS", neden="; ".join(n), **ay))
        if n:
            sorunlu.append((c, lid, n))

    G = {"kota_bas": kota_bas, "ilan": len(L)}
    # 2) ornek envanter
    G["ornek_envanter"] = {}
    rs_ids = set()
    for c in ORNEK:
        lid = next(r["listing_id"] for r in taslak if r["cift"] == c)
        inv = api.get(f"/listings/{lid}/inventory") or {}
        tab, hata = [], []
        for p in inv.get("products") or []:
            pv = {v.get("property_id"): (v.get("values") or [None])[0] for v in p.get("property_values") or []}
            o = (p.get("offerings") or [{}])[0]
            rs_ids.add(o.get("readiness_state_id"))
            tab.append(dict(stil=pv.get(P_STYLE), format=pv.get(P_FORMAT), fiyat=para(o.get("price")), stok=o.get("quantity"),
                            acik=o.get("is_enabled"), sku=p.get("sku"), readiness=o.get("readiness_state_id")))
            if FIYAT.get(pv.get(P_FORMAT)) != para(o.get("price")):
                hata.append(f"{pv.get(P_STYLE)}/{pv.get(P_FORMAT)} fiyat {para(o.get('price'))}")
            if not o.get("is_enabled") or (o.get("quantity") or 0) <= 0:
                hata.append(f"{pv.get(P_STYLE)}/{pv.get(P_FORMAT)} kapali/stok {o.get('quantity')}")
        kombi = {(t["stil"], t["format"]) for t in tab}
        if kombi != {(s_, f_) for s_ in STYLES for f_ in FIYAT}:
            hata.append(f"kombinasyon {len(kombi)} (15 olmali)")
        G["ornek_envanter"][c] = dict(listing_id=lid, urun=len(tab), price_on_property=inv.get("price_on_property"),
                                      sku_on_property=inv.get("sku_on_property"), hata=hata, tablo=tab)
    # 3) kargo, iade, hazirlik, uretim ortagi
    sp = api.get(f"/shops/{shop}/shipping-profiles/{SHIP}", ok404=True) or {}
    G["kargo"] = dict(baslik=sp.get("title"), cikis=sp.get("origin_country_iso"), origin_zip=sp.get("origin_postal_code"),
                      islem=(sp.get("min_processing_days"), sp.get("max_processing_days")), profil_tipi=sp.get("profile_type"),
                      hedefler=[dict(ulke=d.get("destination_country_iso"), bolge=d.get("destination_region"),
                                     ilk=para(d.get("primary_cost")), ek=para(d.get("secondary_cost")),
                                     teslim=(d.get("min_delivery_days"), d.get("max_delivery_days")),
                                     tasiyici=d.get("shipping_carrier_id"), servis=d.get("mail_class"))
                                for d in sp.get("shipping_profile_destinations") or []],
                      ust_secenek=[dict(ad=u.get("upgrade_name"), tip=u.get("type"), fiyat=para(u.get("price")))
                                   for u in sp.get("shipping_profile_upgrades") or []])
    rp = api.get(f"/shops/{shop}/policies/return/{RET}", ok404=True) or {}
    G["iade"] = {k_: rp.get(k_) for k_ in ("return_policy_id", "accepts_returns", "accepts_exchanges", "return_deadline")}
    rsd = (api.get(f"/shops/{shop}/readiness-state-definitions") or {}).get("results") or []
    G["hazirlik"] = [dict(id=r_.get("readiness_state_id"), durum=r_.get("readiness_state"), min=r_.get("min_processing_days"),
                          max=r_.get("max_processing_days"), kullanilan=r_.get("readiness_state_id") in rs_ids) for r_ in rsd]
    ppd = (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []
    G["uretim_ortagi"] = [dict(id=p.get("production_partner_id"), ad=p.get("partner_name"), yer=p.get("location")) for p in ppd]
    G["kota_son"] = api.remaining
    G["istek"] = api.calls
    G["about_sayisi"] = sum(1 for x in satir if x.get("about"))
    G["free_shipping_sayisi"] = sum(1 for x in satir if x.get("free_shipping"))

    alan = ["cift", "listing_id", "sonuc", "neden", "baslik_uzunluk", "etiket", "gorsel", "video", "kutu", "about", "free_shipping", "aciklama_uzunluk"]
    with open(out / "DENETIM.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan, extrasaction="ignore", lineterminator="\n"); w.writeheader(); w.writerows(satir)
    json.dump(G, open(out / "DENETIM.json", "w"), indent=1, ensure_ascii=False, default=str)
    n_pass = sum(x["sonuc"] == "PASS" for x in satir)
    md = ["# BY78 yayindaki 78 ilan denetimi (salt okuma)", "", f"- PASS {n_pass}/{len(satir)} | istek {api.calls} | kota {kota_bas} -> {api.remaining}",
          f"- ABOUT OUR DESIGNS {G['about_sayisi']}/78 | aciklamada 'free shipping' {G['free_shipping_sayisi']}/78",
          f"- kargo: {json.dumps(G['kargo'], ensure_ascii=False)}", f"- iade: {G['iade']}", f"- hazirlik: {G['hazirlik']}",
          f"- uretim ortagi: {G['uretim_ortagi']}",
          *[f"- ornek {c}: urun {v['urun']} hata {v['hata']} | price_on {v['price_on_property']} sku_on {v['sku_on_property']} | "
            f"skular {sorted({t['sku'] for t in v['tablo']})} | fiyat/stok {sorted({(t['format'], t['fiyat'], t['stok'], t['acik']) for t in v['tablo']})}"
            for c, v in G["ornek_envanter"].items()],
          "", "## SORUNLU"] + ([f"- {c} {lid}: {'; '.join(n)}" for c, lid, n in sorunlu] or ["- yok"])
    (out / "DENETIM.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"::warning::DENETIM PASS {n_pass}/{len(satir)} | istek {api.calls} | kota {kota_bas}->{api.remaining} | "
          f"ABOUT {G['about_sayisi']}/78 free_shipping {G['free_shipping_sayisi']}/78 | sorunlu {[(c, '; '.join(n)[:80]) for c, _, n in sorunlu][:5]}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
    except Exception as e:
        import traceback
        print(f"::error::{type(e).__name__}: {str(e)[:500]} | {traceback.format_exc()[-700:]}".replace("\n", " / "))
        raise SystemExit(1)
