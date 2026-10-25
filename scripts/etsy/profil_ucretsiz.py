#!/usr/bin/env python3
"""Wall art (78 poster) kargo profili 314711751541 "POD Prints - Free Shipping": TUM hedefler ucretsiz (Serdar 25 Eki 2026,
Genel Merkez: "kargo tum ulkelere ucretsiz olacak"). Teslim gunleri DEGISMEZ; yalniz primary/secondary cost 0.
KAPI: profili 78 poster ilani (data/pod/pod78_ids.csv) disinda kullanan ilan varsa (active/draft/inactive/expired/sold_out)
yazmadan DUR. Yedek: out/PROFIL_YEDEK.json; geri okuma tum hedefler 0 ve gunler ayni olmali.
Modlar: oku | yaz (--confirm PROFIL_WALLART_UCRETSIZ).  Cikti son satir ::notice::SONUC TAMAM|HATA"""
import argparse
import csv
import json
import os
import re
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
PROFIL = 314711751541
ONAY = "PROFIL_WALLART_UCRETSIZ"
IDS_YOL = Path(__file__).resolve().parents[2] / "data" / "pod" / "pod78_ids.csv"
OUT = Path("out")


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else round(float(p or 0), 2)


def hedefler(P):
    out = {}
    for x in P.get("shipping_profile_destinations") or []:
        cc = (x.get("destination_country_iso") or "").upper()
        rg = (x.get("destination_region") or "none").lower()
        k = cc or ("EVERYWHERE" if rg == "none" else rg.upper())
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
            kim += [(str(x.get("listing_id")), st) for x in r if int(x.get("shipping_profile_id") or 0) == PROFIL]
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
        from etsy_common import Etsy, TokenStore, mask
        k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
        mask(k_); mask(s_)
        store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
        if store.needs_refresh():
            store.refresh()
        api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]

        class Kilitli(type(api)):
            def put(self, path, data):
                if not re.fullmatch(rf"/shops/{shop}/shipping-profiles/{PROFIL}/destinations/\d+", path) or a.mod != "yaz":
                    raise SystemExit(f"YASAK: PUT {path}")
                return super().put(path, data)

            def post(self, *x, **y):
                raise SystemExit("YASAK: POST")

            def patch(self, *x, **y):
                raise SystemExit("YASAK: PATCH")

            def put_json(self, *x, **y):
                raise SystemExit("YASAK: PUT json")

            def post_json(self, *x, **y):
                raise SystemExit("YASAK: POST json")

            def delete(self, *x, **y):
                raise SystemExit("YASAK: DELETE")
        api.__class__ = Kilitli
        P0 = api.get(f"/shops/{shop}/shipping-profiles/{PROFIL}") or {}
        (OUT / "PROFIL_YEDEK.json").write_text(json.dumps(P0, ensure_ascii=False, indent=1), encoding="utf-8")
        h0 = hedefler(P0)
        R.update(baslik=P0.get("title"), once={k: (v["p"], v["s"], v["a"], v["b"]) for k, v in h0.items()})
        if not h0:
            raise SystemExit("DUR: profil hedefi yok")
        poster = {r["listing_id"].strip() for r in csv.DictReader(open(IDS_YOL, encoding="utf-8")) if r.get("listing_id")}
        kim = kullananlar(api, shop)
        R["kullanan_sayi"] = len(kim)
        disari = [x for x in kim if x[0] not in poster]
        R["disari"] = disari[:20]
        if disari:
            raise SystemExit(f"DUR: profili 78 poster disinda {len(disari)} ilan kullaniyor: {disari[:10]}")
        degis = [k for k, v in h0.items() if v["p"] != 0 or v["s"] != 0]
        R["degisecek"] = degis
        if a.mod == "yaz":
            for k in degis:
                v = h0[k]
                alan = {"destination_country_iso": v["cc"]} if v["cc"] else {"destination_region": v["rg"]}
                api.put(f"/shops/{shop}/shipping-profiles/{PROFIL}/destinations/{v['id']}",
                        {"primary_cost": 0, "secondary_cost": 0, "min_delivery_days": v["a"], "max_delivery_days": v["b"], **alan})
            h1 = hedefler(api.get(f"/shops/{shop}/shipping-profiles/{PROFIL}") or {})
            R["sonra"] = {k: (v["p"], v["s"], v["a"], v["b"]) for k, v in h1.items()}
            bek = {k: (0.0, 0.0, v["a"], v["b"]) for k, v in h0.items()}
            if R["sonra"] != bek:
                raise SystemExit(f"DUR: geri okuma beklenen degil: {R['sonra']}")
    except BaseException as e:  # noqa: BLE001
        hata = f"{type(e).__name__}: {str(e)[:500]}"
        R["hata"], R["iz"] = hata, traceback.format_exc()[-1500:]
    finally:
        (OUT / f"PROFIL_{a.mod.upper()}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print("PROFIL " + json.dumps({k: v for k, v in R.items() if k != "iz"}, ensure_ascii=False, default=str), flush=True)
        print(f"::notice::SONUC {'TAMAM' if hata is None else 'HATA'} {a.mod} degisecek {R.get('degisecek')} kullanan {R.get('kullanan_sayi')}",
              flush=True)
    sys.exit(0 if hata is None else 1)


if __name__ == "__main__":
    main()
