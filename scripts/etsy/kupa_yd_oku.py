#!/usr/bin/env python3
"""SALT OKUMA (Etsy'ye yazma YOK; Serdar 31 Eki karar 3b + 5a). Iki kucuk okuma, kosu basina sabit istek:
  kupa : 78 kupa ilaninin canli EN aciklamasi + RU cevirisi (GET /listings/batch?includes=Translations, 100'luk parca: 1 istek).
         Kupa RU kurucusu (ru_kupa.py) girdisi. Cikti KUPA_CANLI.json (listing_id, cift, state, title, description, ru).
  kisisel: ayni burclu 12 kupa ilaninin kisisellestirme sorusu + ilan talimati (Serdar 31 Eki 7a; 1 batch + 12 GET = 13 istek).
  yd   : 1st Anniversary boy (Size) ozelligi. Pilot ilan: GET /listings/{id} (taxonomy_id), /listings/{id}/inventory (canli
         varyasyon ozellikleri), /shops/{shop}/listings/{id}/properties (ilan nitelikleri), /seller-taxonomy/nodes/{tid}/properties
         (taksonomi ozellikleri) = 4 istek. Cikti YD_BOY.json: canli ozellikler, ilan nitelikleri, taksonomide supports_variations
         ozellikler, ad/gorunen ad 'size' / 'dimension' iceren adaylar (yd_yapi_kuru.boy_ozellik kapisiyla sinanir).
Yazma yontemleri kapali (yd_envanter_oku.salt_okur). Kota: her istekten once etsy_common sert taban (KOTA_SINIRI 10).
Istek sayisi ISTEK.json (api.calls; token yenileme dahil degil)."""
import argparse
import csv
import json
import os
import pathlib
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402
from yd_envanter_oku import salt_okur  # noqa: E402

ADAY = ("size", "dimension")


def kupa(api, liste, out):
    rows = [r for r in csv.DictReader(open(liste, encoding="utf-8-sig")) if (r.get("listing_id") or "").strip()]
    cift = {r["listing_id"].strip(): r["cift"].strip() for r in rows}
    ids, sonuc = list(cift), []
    for k in range(0, len(ids), 100):
        api.kota_kapisi(f"kupa batch {k}")
        r = api.get("/listings/batch", {"listing_ids": ",".join(ids[k:k + 100]), "includes": "Translations"}) or {}
        sonuc += r.get("results") or []
    kayit = []
    for L in sonuc:
        tr = L.get("translations") or []
        if isinstance(tr, dict):
            tr = list(tr.values())
        ru = next((t for t in tr if isinstance(t, dict) and t.get("language") == "ru"), None) or {}
        kayit.append(dict(listing_id=str(L.get("listing_id")), cift=cift.get(str(L.get("listing_id")), ""), state=L.get("state"),
                          title=L.get("title"), description=L.get("description"), last_modified=L.get("last_modified_timestamp"),
                          ru=dict(title=ru.get("title"), description=ru.get("description"), tags=ru.get("tags"))))
    kayit.sort(key=lambda x: x["cift"])
    (out / "KUPA_CANLI.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    eksik = sorted(set(cift) - {x["listing_id"] for x in kayit})
    print(f"kupa: liste {len(cift)} okunan {len(kayit)} eksik {len(eksik)} {eksik[:5]} | istek {api.calls} kota {api.remaining}")
    return 0 if len(kayit) == len(cift) == 78 and not eksik else 1


def kisisel(api, liste, out):
    """Serdar 31 Eki karar 7a: ayni burclu 12 kupa ilaninin canli kisisellestirme sorusu (GET /listings/{id}/personalization, ilan
    basina 1 istek) + ilan alanlari (personalization_instructions vb.; /listings/batch 1 istek). Cikti KUPA_KISISEL_AYNI12.json."""
    rows = [r for r in csv.DictReader(open(liste, encoding="utf-8-sig")) if (r.get("listing_id") or "").strip()]
    ayni = {r["listing_id"].strip(): r["cift"].strip() for r in rows if r["cift"].split("_")[0] == r["cift"].split("_")[-1]}
    if len(ayni) != 12:
        raise SystemExit(f"DUR: ayni burclu kupa {len(ayni)} (12 beklenir)")
    api.kota_kapisi("kupa ayni12 batch")
    L = {str(x.get("listing_id")): x for x in (api.get("/listings/batch", {"listing_ids": ",".join(ayni)}) or {}).get("results") or []}
    kayit = []
    for lid, c in sorted(ayni.items(), key=lambda x: x[1]):
        api.kota_kapisi(f"kisisel {lid}")
        q = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []
        x = L.get(lid) or {}
        kayit.append(dict(listing_id=lid, cift=c, state=x.get("state"), is_personalizable=x.get("is_personalizable"),
                          personalization_instructions=x.get("personalization_instructions"),
                          personalization_char_count_max=x.get("personalization_char_count_max"), sorular=q))
    (out / "KUPA_KISISEL_AYNI12.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"kisisel: 12 ilan, soru sayilari {[len(k['sorular']) for k in kayit]} | istek {api.calls} kota {api.remaining}")
    return 0 if len(kayit) == 12 and all(k["state"] for k in kayit) else 1


def yd(api, shop, pilot, out):
    api.kota_kapisi("yd pilot")
    L = api.get(f"/listings/{pilot}") or {}
    inv = api.get(f"/listings/{pilot}/inventory") or {}
    nit = (api.get(f"/shops/{shop}/listings/{pilot}/properties", ok404=True) or {}).get("results") or []
    tid = L.get("taxonomy_id")
    tax = (api.get(f"/seller-taxonomy/nodes/{tid}/properties", ok404=True) or {}).get("results") or [] if tid else []
    canli = {}
    for p in inv.get("products") or []:
        for v in p.get("property_values") or []:
            o = canli.setdefault(v.get("property_id"), dict(ad=v.get("property_name"), degerler=[]))
            for d in v.get("values") or []:
                if d not in o["degerler"]:
                    o["degerler"].append(d)
    ozet = [dict(property_id=p.get("property_id"), name=p.get("name"), display_name=p.get("display_name"),
                 supports_variations=p.get("supports_variations"), is_multivalued=p.get("is_multivalued"),
                 scales=[dict(scale_id=s.get("scale_id"), display_name=s.get("display_name")) for s in p.get("scales") or []],
                 possible_values_say=len(p.get("possible_values") or []),
                 possible_values_ornek=[v.get("name") for v in (p.get("possible_values") or [])[:15]]) for p in tax]
    aday = [o for o in ozet if any(a in f"{o['name']} {o['display_name']}".lower() for a in ADAY)]
    kayit = dict(pilot=pilot, state=L.get("state"), title=L.get("title"), taxonomy_id=tid,
                 canli_varyasyon={str(k): v for k, v in canli.items()},
                 price_on_property=inv.get("price_on_property"), sku_on_property=inv.get("sku_on_property"),
                 ilan_nitelikleri=[{k: n.get(k) for k in ("property_id", "property_name", "scale_id", "scale_name", "value_ids", "values")}
                                   for n in nit],
                 taksonomi_ozellik_say=len(ozet), varyasyon_destekli=[o for o in ozet if o["supports_variations"]], boy_adaylari=aday)
    (out / "YD_BOY.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"yd: pilot {pilot} {L.get('state')} taksonomi {tid} canli varyasyon {sorted(canli, key=str)} "
          f"taksonomi ozellik {len(ozet)} varyasyon destekli {len(kayit['varyasyon_destekli'])} boy adayi "
          f"{[(o['property_id'], o['name'], o['supports_variations']) for o in aday]} | istek {api.calls} kota {api.remaining}")
    return 0 if tid and ozet else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["kupa", "yd", "ikisi", "kisisel"], default="ikisi")
    ap.add_argument("--kupa-liste", default="")
    ap.add_argument("--pilot", default="4595350971")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k_); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api, shop = E.Etsy(store), os.environ["ETSY_SHOP_ID"]
    salt_okur(api)
    rc, istek = 0, {}
    if a.mod in ("kupa", "ikisi"):
        rc |= kupa(api, a.kupa_liste, out); istek["kupa"] = api.calls
    if a.mod == "kisisel":
        rc |= kisisel(api, a.kupa_liste, out); istek["kisisel"] = api.calls
    if a.mod in ("yd", "ikisi"):
        c0 = api.calls
        rc |= yd(api, shop, a.pilot, out); istek["yd"] = api.calls - c0
    (out / "ISTEK.json").write_text(json.dumps(dict(istek, toplam=api.calls, kota_son=api.remaining), indent=1), encoding="utf-8")
    print(f"ISTEK {istek} toplam {api.calls} kota {api.remaining}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
