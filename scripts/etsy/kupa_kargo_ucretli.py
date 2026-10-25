#!/usr/bin/env python3
"""Kupa kargo profili 318301958420: HICBIR YERE ucretsiz kargo yok (Serdar 25 Eki 2026 aksam, Genel Merkez).
Fiyat 11 oz 12.90 / 15 oz 16.90 (kupa_fiyat.py); fark kargoya tasindi. Ucret = Printful 15 oz Flat Rate (API, kosu 40221341323)
bir ust .90 + 4.00. Teslim gunleri DEGISMEZ (mevcut degerler korunur).
Hedef (ilk kupa / ek kupa, USD):
  US 11.90/4.90  CA 12.90/5.90  GB 10.90/1.90  EU 10.90/2.90  AU 13.90/4.90  JP 10.90/2.90  diger tum ulkeler 17.90/7.90
Kabul edilen mevcut durum: onceki tur (US/CA/GB/EU/AU/JP 0, diger 14.90/14.90) ya da hedefin kendisi (tekrar kosu: ZATEN).
KAPI: profili kupa bolumu 60980873 disinda kullanan ilan varsa DUR. Yalniz PUT /shipping-profiles/{p}/destinations/{id}.
Modlar: oku | yaz (--confirm KUPA_KARGO_UCRETLI). Son satir ::notice::SONUC TAMAM|KOTA|HATA"""
import argparse
import json
import os
import re
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
PROFIL, BOLUM = 318301958420, 60980873
ONAY = "KUPA_KARGO_UCRETLI"
HEDEF = {"US": (11.90, 4.90), "CA": (12.90, 5.90), "GB": (10.90, 1.90), "EU": (10.90, 2.90), "AU": (13.90, 4.90),
         "JP": (10.90, 2.90), "EVERYWHERE": (17.90, 7.90)}
ONCEKI = {"US": (0.0, 0.0), "CA": (0.0, 0.0), "GB": (0.0, 0.0), "EU": (0.0, 0.0), "AU": (0.0, 0.0), "JP": (0.0, 0.0),
          "EVERYWHERE": (14.90, 14.90)}
OUT = Path("out")


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else round(float(p or 0), 2)


def hedefler(P):
    out = {}
    for x in P.get("shipping_profile_destinations") or []:
        cc = (x.get("destination_country_iso") or "").upper()
        rg = (x.get("destination_region") or "none").lower()
        k = cc or ("EVERYWHERE" if rg == "none" else rg.upper())
        if k in out:
            raise SystemExit(f"DUR: ayni hedef iki kez: {k}")
        out[k] = dict(id=x.get("shipping_profile_destination_id"), cc=cc, rg=rg, p=para(x.get("primary_cost")),
                      s=para(x.get("secondary_cost")), a=x.get("min_delivery_days"), b=x.get("max_delivery_days"))
    return out


def kullananlar(api, shop):
    kim = []
    for st in ("active", "draft", "inactive", "expired", "sold_out"):
        off = 0
        while True:
            d = api.get(f"/shops/{shop}/listings", params={"state": st, "limit": 100, "offset": off}) or {}
            r = d.get("results") or []
            kim += [(str(x.get("listing_id")), st, x.get("shop_section_id")) for x in r if int(x.get("shipping_profile_id") or 0) == PROFIL]
            off += len(r)
            if len(r) < 100:
                break
    return kim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["oku", "yaz"])
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    R, hata = {"profil": PROFIL, "mod": a.mod}, None
    try:
        if a.mod == "yaz" and a.confirm != ONAY:
            raise SystemExit(f"DUR: yaz icin --confirm {ONAY}")
        from etsy_common import Etsy, TokenStore, mask, KOTA_SINIRI
        k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
        mask(k_); mask(s_)
        store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
        if store.needs_refresh():
            store.refresh()
        api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]

        class Kilitli(type(api)):
            def put(self, path, data):
                anah = set(data)
                if a.mod != "yaz" or not re.fullmatch(rf"/shops/{shop}/shipping-profiles/{PROFIL}/destinations/\d+", path) \
                        or not {"primary_cost", "secondary_cost", "min_delivery_days", "max_delivery_days"} <= anah \
                        or not anah <= {"primary_cost", "secondary_cost", "min_delivery_days", "max_delivery_days",
                                        "destination_country_iso", "destination_region"} \
                        or ("destination_country_iso" in anah) == ("destination_region" in anah) \
                        or (round(float(data["primary_cost"]), 2), round(float(data["secondary_cost"]), 2)) not in HEDEF.values():
                    raise SystemExit(f"YASAK: PUT {path} {sorted(anah)}")
                return super().put(path, data)

            def post(self, *x, **y):
                raise SystemExit("YASAK: POST")

            def patch(self, *x, **y):
                raise SystemExit("YASAK: PATCH")

            def put_json(self, *x, **y):
                raise SystemExit("YASAK: PUT json")

            def post_json(self, *x, **y):
                raise SystemExit("YASAK: POST json")

            def post_file(self, *x, **y):
                raise SystemExit("YASAK: POST file")

            def delete(self, *x, **y):
                raise SystemExit("YASAK: DELETE")
        api.__class__ = Kilitli
        P0 = api.get(f"/shops/{shop}/shipping-profiles/{PROFIL}") or {}
        (OUT / "KUPA_KARGO_YEDEK.json").write_text(json.dumps(P0, ensure_ascii=False, indent=1), encoding="utf-8")
        h0 = hedefler(P0)
        R.update(baslik=P0.get("title"), once={k: (v["p"], v["s"], v["a"], v["b"]) for k, v in h0.items()})
        if set(h0) != set(HEDEF):
            raise SystemExit(f"DUR: profil hedefleri beklenmedik: {sorted(h0)} (beklenen {sorted(HEDEF)})")
        for k, v in h0.items():
            if (v["p"], v["s"]) not in (ONCEKI[k], HEDEF[k]):
                raise SystemExit(f"DUR: {k} ucret {v['p']}/{v['s']} (beklenen onceki {ONCEKI[k]} ya da hedef {HEDEF[k]})")
        kim = kullananlar(api, shop)
        R["kullanan_sayi"] = len(kim)
        disari = [x for x in kim if x[2] != BOLUM]
        R["disari"] = disari[:20]
        if disari:
            raise SystemExit(f"DUR: profili kupa bolumu disinda {len(disari)} ilan kullaniyor: {disari[:10]}")
        degis = [k for k, v in h0.items() if (v["p"], v["s"]) != HEDEF[k]]
        R["degisecek"] = degis
        if a.mod == "yaz" and degis:
            if api.remaining is not None and int(api.remaining) < len(degis) + 2 + KOTA_SINIRI:
                raise SystemExit(f"DUR: kota esigi: kalan {api.remaining} < {len(degis) + 2} + {KOTA_SINIRI} (yazma yok)")
            for k in degis:
                v = h0[k]
                alan = {"destination_country_iso": v["cc"]} if v["cc"] else {"destination_region": v["rg"]}
                api.put(f"/shops/{shop}/shipping-profiles/{PROFIL}/destinations/{v['id']}",
                        {"primary_cost": HEDEF[k][0], "secondary_cost": HEDEF[k][1], "min_delivery_days": v["a"],
                         "max_delivery_days": v["b"], **alan})
                R.setdefault("yazildi", []).append(k)
            h1 = hedefler(api.get(f"/shops/{shop}/shipping-profiles/{PROFIL}") or {})
            R["sonra"] = {k: (v["p"], v["s"], v["a"], v["b"]) for k, v in h1.items()}
            bek = {k: (HEDEF[k][0], HEDEF[k][1], v["a"], v["b"]) for k, v in h0.items()}
            if R["sonra"] != bek:
                raise SystemExit(f"DUR: geri okuma beklenen degil: {R['sonra']} != {bek}")
    except BaseException as e:  # noqa: BLE001
        hata = f"{type(e).__name__}: {str(e)[:500]}"
        R["hata"], R["iz"] = hata, traceback.format_exc()[-1500:]
    finally:
        (OUT / f"KUPA_KARGO_{a.mod.upper()}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print("KUPA_KARGO " + json.dumps({k: v for k, v in R.items() if k != "iz"}, ensure_ascii=False, default=str), flush=True)
        kota = hata is not None and ("kota esigi: kalan" in hata or "kota sert tabani: kalan" in hata) and not R.get("yazildi")
        et = "TAMAM" if hata is None else ("KOTA" if kota else "HATA")
        print(f"::notice::SONUC {et} {a.mod} degisecek {R.get('degisecek')} kullanan {R.get('kullanan_sayi')}", flush=True)
    sys.exit(0 if (hata is None or et == "KOTA") else 1)


if __name__ == "__main__":
    main()
