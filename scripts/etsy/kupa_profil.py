#!/usr/bin/env python3
"""Kupa kargo profili 318301958420 "Kupa Free US UK EU" (Serdar 25 Eki 2026, Genel Merkez): ABD, Kanada, UK, AB, Avustralya
ve Japonya UCRETSIZ; diger tum ulkeler $14.90. Su an profilde yalniz US/CA/GB/EU/AU (hepsi 0) var: diger ulkeler hic
satin alamiyor. Eklenecek hedefler (POST destinations):
  JP: 0, teslim 5-12 gun (Printful JP 11 oz 2-4, 15 oz 8-11 gun tahmini, API 25 Eki)
  diger tum ulkeler (destination_region none): 14.90 / ek urun 14.90, teslim 7-21 gun (Printful TR/IL/BR/NO 5-11 gun)
Mevcut 5 hedefe dokunulmaz. KAPI: profili kupa bolumu 60980873 disinda kullanan ilan varsa DUR.
Modlar: oku | yaz (--confirm KUPA_PROFIL). Son satir ::notice::SONUC TAMAM|KOTA|HATA"""
import argparse
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
PROFIL, BOLUM = 318301958420, 60980873
ONAY = "KUPA_PROFIL"
MEVCUT = {"US": 0.0, "CA": 0.0, "GB": 0.0, "EU": 0.0, "AU": 0.0}
EKLE = {"JP": dict(destination_country_iso="JP", primary_cost=0, secondary_cost=0, min_delivery_days=5, max_delivery_days=12),
        "EVERYWHERE": dict(destination_region="none", primary_cost=14.90, secondary_cost=14.90, min_delivery_days=7, max_delivery_days=21)}
OUT = Path("out")


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else round(float(p or 0), 2)


def hedefler(P):
    out = {}
    for x in P.get("shipping_profile_destinations") or []:
        cc = (x.get("destination_country_iso") or "").upper()
        rg = (x.get("destination_region") or "none").lower()
        k = cc or ("EVERYWHERE" if rg == "none" else rg.upper())
        out[k] = (para(x.get("primary_cost")), para(x.get("secondary_cost")), x.get("min_delivery_days"), x.get("max_delivery_days"))
    return out


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
        izinli = [{k: v for k, v in d.items()} for d in EKLE.values()]

        class Kilitli(type(api)):
            def post(self, path, data):
                if a.mod != "yaz" or path != f"/shops/{shop}/shipping-profiles/{PROFIL}/destinations" or data not in izinli:
                    raise SystemExit(f"YASAK: POST {path} {data}")
                return super().post(path, data)

            def put(self, *x, **y):
                raise SystemExit("YASAK: PUT")

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
        (OUT / "KUPA_PROFIL_YEDEK.json").write_text(json.dumps(P0, ensure_ascii=False, indent=1), encoding="utf-8")
        h0 = hedefler(P0)
        R.update(baslik=P0.get("title"), once=h0)
        for k, c in MEVCUT.items():
            if k not in h0 or h0[k][0] != c or h0[k][1] != c:
                raise SystemExit(f"DUR: mevcut hedef {k} beklenmedik: {h0.get(k)}")
        fazla = set(h0) - set(MEVCUT) - set(EKLE)
        if fazla:
            raise SystemExit(f"DUR: beklenmeyen hedef: {sorted(fazla)}")
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
        R["kullanan_sayi"] = len(kim)
        disari = [x for x in kim if x[2] != BOLUM]
        R["disari"] = disari[:20]
        if disari:
            raise SystemExit(f"DUR: profili kupa bolumu disinda {len(disari)} ilan kullaniyor: {disari[:10]}")
        eksik = [k for k in EKLE if k not in h0]
        R["eklenecek"] = eksik
        for k in EKLE:
            if k in h0:
                e = EKLE[k]
                if h0[k] != (float(e["primary_cost"]), float(e["secondary_cost"]), e["min_delivery_days"], e["max_delivery_days"]):
                    raise SystemExit(f"DUR: {k} var ama hedeften farkli: {h0[k]}")
        if a.mod == "yaz" and eksik:
            if api.remaining is not None and int(api.remaining) < len(eksik) + 2 + KOTA_SINIRI:
                raise SystemExit(f"DUR: kota esigi: kalan {api.remaining} < {len(eksik) + 2} + {KOTA_SINIRI} (yazma yok)")
            for k in eksik:
                api.post(f"/shops/{shop}/shipping-profiles/{PROFIL}/destinations", dict(EKLE[k]))
            h1 = hedefler(api.get(f"/shops/{shop}/shipping-profiles/{PROFIL}") or {})
            R["sonra"] = h1
            bek = dict(h0)
            bek.update({k: (float(e["primary_cost"]), float(e["secondary_cost"]), e["min_delivery_days"], e["max_delivery_days"])
                        for k, e in EKLE.items()})
            if h1 != bek:
                raise SystemExit(f"DUR: geri okuma beklenen degil: {h1} != {bek}")
    except BaseException as e:  # noqa: BLE001
        hata = f"{type(e).__name__}: {str(e)[:500]}"
        R["hata"], R["iz"] = hata, traceback.format_exc()[-1500:]
    finally:
        (OUT / f"KUPA_PROFIL_{a.mod.upper()}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print("KUPA_PROFIL " + json.dumps({k: v for k, v in R.items() if k != "iz"}, ensure_ascii=False, default=str), flush=True)
        et = "TAMAM" if hata is None else ("KOTA" if "kota esigi: kalan" in hata or "kota sert tabani: kalan" in hata else "HATA")
        print(f"::notice::SONUC {et} {a.mod} eklenecek {R.get('eklenecek')} kullanan {R.get('kullanan_sayi')}", flush=True)
    sys.exit(0 if (hata is None or et == "KOTA") else 1)


if __name__ == "__main__":
    main()
