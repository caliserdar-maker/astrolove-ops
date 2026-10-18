#!/usr/bin/env python3
"""KUPA: CANCER_LIBRA kupa ilani TASLAK (Serdar 18 Eki 2026). YAYIN YOK, Etsy Ads YOK.

--mod oku  : SALT OKUMA (Etsy'ye yazma yok; kilitli istemci her yazmayi durdurur).
             kupa kategorisi (taxonomy) adaylari + secilen dugumun nitelikleri (zorunlu/istege bagli, olasi degerler),
             Bizim Yilimiz CANCER_LIBRA ilaninin hazirlik ayari (readiness_state_id, processing, kargo profili),
             iade politikalari, uretim ortaklari, bolumler, kargo profilleri, ayni baslikli taslak var mi,
             Etsy OAS (statik): ilgili uclarin istek alanlari (production partner olusturma ucu var mi dahil).
             Cikti: OUT/KUPA_OKU.json + OUT/KUPA_OKU.md
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, BY_CSV (BY78_TASLAKLAR.csv), OUT
Kota tabani 10 (Serdar 15 Eki): x-remaining-today < 10 ise DUR.
"""
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

PAIR = "CANCER_LIBRA"
KOTA_MIN = 10
OAS = "https://www.etsy.com/openapi/generated/oas/3.0.0.json"
OAS_OP = ["createDraftListing", "createShopReturnPolicy", "createShopShippingProfile", "createShopShippingProfileDestination",
          "createShopSection", "getShopProductionPartners", "uploadListingVideo", "updateVariationImages",
          "updateListingPersonalization", "updateListingProperty", "updateListingInventory", "uploadListingImage",
          "getListingPersonalization", "getShopReadinessStateDefinitions", "createShopReadinessStateDefinition"]
KUPA_ADLARI = ("mug", "mugs")


class SaltOkur(Etsy):
    """Her yazma cagrisi programi durdurur; her cevaptan sonra kota tabani kontrol edilir."""

    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        r = super()._call(method, path, **kw)
        try:
            if self.remaining is not None and int(self.remaining) < KOTA_MIN:
                raise SystemExit(f"DUR: kota {self.remaining} < {KOTA_MIN}")
        except ValueError:
            pass
        return r

    def post(self, *a, **k):
        raise SystemExit("YASAK: POST")

    def put(self, *a, **k):
        raise SystemExit("YASAK: PUT")

    def patch(self, *a, **k):
        raise SystemExit("YASAK: PATCH")

    def delete(self, *a, **k):
        raise SystemExit("YASAK: DELETE")

    def post_json(self, *a, **k):
        raise SystemExit("YASAK: POST json")

    def put_json(self, *a, **k):
        raise SystemExit("YASAK: PUT json")

    def post_file(self, *a, **k):
        raise SystemExit("YASAK: POST file")


def para(p):
    if isinstance(p, dict) and p.get("divisor"):
        return round(p["amount"] / p["divisor"], 2)
    return p


def agac_duz(dugumler, yol=(), out=None):
    out = [] if out is None else out
    for n in dugumler or []:
        p = yol + (n.get("name"),)
        out.append((n.get("id"), p, bool(n.get("children"))))
        agac_duz(n.get("children"), p, out)
    return out


def oas_ozet():
    d = requests.get(OAS, timeout=120).json()
    S = d.get("components", {}).get("schemas", {})

    def coz(x, n=0):
        if n > 4 or not isinstance(x, dict):
            return x
        if "$ref" in x:
            return coz(S.get(x["$ref"].split("/")[-1], {}), n + 1)
        if "allOf" in x:
            return coz(x["allOf"][0], n + 1)
        return x

    R = {"surum": d.get("info", {}).get("version"), "uclar": {}, "production_partner_yollari": {}}
    for path, ops in d.get("paths", {}).items():
        for m, op in ops.items():
            if not isinstance(op, dict):
                continue
            if "production-partner" in path:
                R["production_partner_yollari"][f"{m.upper()} {path}"] = op.get("operationId")
            if op.get("operationId") not in OAS_OP:
                continue
            alan = {}
            for ct, c in ((op.get("requestBody") or {}).get("content") or {}).items():
                sc = coz(c.get("schema") or {})
                for k, v in (sc.get("properties") or {}).items():
                    v = coz(v)
                    it = coz(v.get("items") or {}) if v.get("type") == "array" else {}
                    alan[k] = dict(tip=v.get("type"), enum=v.get("enum") or it.get("enum"), zorunlu=k in (sc.get("required") or []),
                                   min=v.get("minimum", v.get("minLength")), max=v.get("maximum", v.get("maxLength")),
                                   oge=sorted((it.get("properties") or {}).keys()) if it else None,
                                   aciklama=(v.get("description") or "")[:400])
            R["uclar"][op["operationId"]] = dict(yol=f"{m.upper()} {path}", ozet=(op.get("summary") or "")[:200],
                                                 aciklama=(op.get("description") or "")[:900], alanlar=alan,
                                                 parametreler=[(p.get("in"), p.get("name"), p.get("required")) for p in op.get("parameters") or []])
    pq = S.get("ListingPersonalizationQuestion") or next((S[k] for k in S if k.endswith("PersonalizationQuestion")), None)
    if pq:
        R["kisisellestirme_soru_semasi"] = {k: (coz(v).get("type"), coz(v).get("enum"), (coz(v).get("description") or "")[:300])
                                            for k, v in (pq.get("properties") or {}).items()}
    return R


def oku(api, shop, out):
    R = {"kota_bas": None}
    api.get(f"/shops/{shop}")
    R["kota_bas"] = api.remaining

    # 1) kupa kategorisi
    duz = agac_duz((api.get("/seller-taxonomy/nodes") or {}).get("results"))
    aday = [(i, " > ".join(p), c) for i, p, c in duz if (p[-1] or "").strip().lower() in KUPA_ADLARI]
    R["kategori_adaylari"] = aday
    yaprak = [a for a in aday if not a[2]]
    tercih = [a for a in yaprak if "drinkware" in a[1].lower()] or yaprak
    R["kategori"] = dict(id=tercih[0][0], yol=tercih[0][1]) if tercih else None
    if R["kategori"]:
        props = (api.get(f"/seller-taxonomy/nodes/{R['kategori']['id']}/properties") or {}).get("results") or []
        R["nitelikler"] = [dict(property_id=p.get("property_id"), ad=p.get("name"), gorunen=p.get("display_name"),
                                zorunlu=p.get("is_required"), varyasyon=p.get("supports_variations"),
                                coklu=p.get("is_multivalued"), max_deger=p.get("max_values_allowed"),
                                attribute=p.get("supports_attributes"),
                                olcekler=[(s.get("scale_id"), s.get("display_name")) for s in p.get("scales") or []],
                                degerler=[(v.get("value_id"), v.get("name"), v.get("scale_id")) for v in p.get("possible_values") or []])
                           for p in props]

    # 2) Bizim Yilimiz CANCER_LIBRA ilani (hazirlik ayari)
    by = next((r for r in csv.DictReader(open(os.environ["BY_CSV"], encoding="utf-8")) if r.get("cift") == PAIR), None)
    R["by_csv_satir"] = by
    lid = int(by["listing_id"]) if by and by.get("listing_id") else None
    if lid:
        L = api.get(f"/listings/{lid}") or {}
        inv = api.get(f"/listings/{lid}/inventory") or {}
        rs = sorted({o.get("readiness_state_id") for p in inv.get("products") or [] for o in p.get("offerings") or []
                     if o.get("readiness_state_id")})
        sp = api.get(f"/shops/{shop}/shipping-profiles/{L.get('shipping_profile_id')}", ok404=True) or {}
        R["by_ilan"] = dict(listing_id=lid, state=L.get("state"), processing=(L.get("processing_min"), L.get("processing_max")),
                            readiness_state_ids=rs, shipping_profile_id=L.get("shipping_profile_id"),
                            return_policy_id=L.get("return_policy_id"), who_made=L.get("who_made"), when_made=L.get("when_made"),
                            production_partners=L.get("production_partners"), shop_section_id=L.get("shop_section_id"),
                            personalization=(L.get("is_personalizable"), L.get("personalization_is_required"),
                                             L.get("personalization_char_count_max")))
        R["by_kargo_profili"] = dict(
            id=sp.get("shipping_profile_id"), ad=sp.get("title"), cikis=(sp.get("origin_country_iso"), sp.get("origin_postal_code")),
            islem=(sp.get("min_processing_days"), sp.get("max_processing_days"), sp.get("processing_days_display_label")),
            hedefler=[(d.get("destination_country_iso") or d.get("destination_region"), para(d.get("primary_cost")),
                       para(d.get("secondary_cost")), d.get("min_delivery_days"), d.get("max_delivery_days"))
                      for d in sp.get("shipping_profile_destinations") or []],
            ham_anahtarlar=sorted(sp.keys()))
    rsd = (api.get(f"/shops/{shop}/readiness-state-definitions") or {}).get("results") or []
    R["hazirlik_tanimlari"] = [dict(id=x.get("readiness_state_id"), durum=x.get("readiness_state"), min=x.get("min_processing_days"),
                                    max=x.get("max_processing_days"), etiket=x.get("processing_days_display_label")) for x in rsd]

    # 3) iade, ortak, bolum, kargo profilleri, ayni baslikli taslak
    rp = (api.get(f"/shops/{shop}/policies/return") or {}).get("results") or []
    R["iade_politikalari"] = [dict(id=x.get("return_policy_id"), iade=x.get("accepts_returns"), degisim=x.get("accepts_exchanges"),
                                   sure=x.get("return_deadline")) for x in rp]
    pp = (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []
    R["uretim_ortaklari"] = [dict(id=x.get("production_partner_id"), ad=x.get("partner_name"), konum=x.get("location")) for x in pp]
    secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    R["bolumler"] = [dict(id=x.get("shop_section_id"), ad=x.get("title"), aktif_ilan=x.get("active_listing_count")) for x in secs]
    sps = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    R["kargo_profilleri"] = [dict(id=x.get("shipping_profile_id"), ad=x.get("title")) for x in sps]
    if os.environ.get("KUPA_CSV"):
        row = next(r for r in csv.DictReader(open(os.environ["KUPA_CSV"], encoding="utf-8")) if r["kod"] == PAIR)
        drafts = (api.get(f"/shops/{shop}/listings", params={"state": "draft", "limit": 100}) or {}).get("results") or []
        R["ayni_baslikli_taslak"] = [x.get("listing_id") for x in drafts if x.get("title") == row["baslik"]]
    R["kota_son"] = api.remaining
    R["cagri"] = api.calls

    # 4) OAS (statik dosya, kota harcamaz)
    try:
        R["oas"] = oas_ozet()
    except Exception as e:  # noqa: BLE001
        R["oas"] = dict(hata=str(e)[:300])

    json.dump(R, open(out / "KUPA_OKU.json", "w"), indent=1, ensure_ascii=False, default=str)
    md = [f"# KUPA OKU ({PAIR})", f"kota bas {R['kota_bas']} son {R['kota_son']} cagri {R['cagri']}",
          f"kategori: {R.get('kategori')}", f"kategori adaylari: {R['kategori_adaylari']}", "", "## Nitelikler"]
    for p in R.get("nitelikler") or []:
        md.append(f"- {p['property_id']} {p['ad']} zorunlu={p['zorunlu']} varyasyon={p['varyasyon']} coklu={p['coklu']} "
                  f"olcek={p['olcekler']} degerler({len(p['degerler'])})={[d[1] for d in p['degerler']][:40]}")
    md += ["", f"BY ilan: {R.get('by_ilan')}", f"BY kargo: {R.get('by_kargo_profili')}", f"hazirlik: {R['hazirlik_tanimlari']}",
           f"iade: {R['iade_politikalari']}", f"ortak: {R['uretim_ortaklari']}", f"bolum: {R['bolumler']}",
           f"kargo profilleri: {R['kargo_profilleri']}", f"ayni baslikli taslak: {R.get('ayni_baslikli_taslak')}",
           f"OAS production partner yollari: {(R['oas'] or {}).get('production_partner_yollari')}"]
    (out / "KUPA_OKU.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    print(f"::warning::OKU kategori {R.get('kategori')} | nitelik {len(R.get('nitelikler') or [])} | BY readiness "
          f"{(R.get('by_ilan') or {}).get('readiness_state_ids')} | iade {len(rp)} ortak {len(pp)} bolum {len(secs)} | "
          f"kota {R['kota_bas']} -> {R['kota_son']} | OAS partner {(R['oas'] or {}).get('production_partner_yollari')}")
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["oku"])
    a = ap.parse_args()
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    shop = os.environ["ETSY_SHOP_ID"]
    if a.mod == "oku":
        oku(SaltOkur(store), shop, out)


if __name__ == "__main__":
    main()
