#!/usr/bin/env python3
"""Magaza bolumu (section) adi arastirmasi (14 Eki 2026). SALT OKUR, yalniz API anahtari (OAuth yok, Etsy'ye yazma yok).
1) Etsy OAS (statik, kota harcamaz): createShopSection / ShopSection 'title' alani sinirlari.
2) GET /listings/active?keywords=<ifade>: aday ifadelerin aktif ilan sayisi (rekabet; arama HACMI DEGILDIR).
3) "paper anniversary gift" ve "1st anniversary gift" aramasinda ilk siralardaki magazalar (sort_on=score, Etsy
   alaka siralamasina en yakin API siralamasi) -> GET /shops/{id} + /shops/{id}/sections: bolum adlari.
Cikti: BOLUM_ARASTIRMA.json + BOLUM_ARASTIRMA.md. Kullanim: bolum_arastir.py --oas oas.json --out _out"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import APIKeyStore, Etsy, log  # noqa: E402

ADAYLAR = ["paper anniversary gift", "1st anniversary gift", "first anniversary gift", "one year anniversary gift",
           "paper anniversary", "1st anniversary", "anniversary gifts", "personalized anniversary gift",
           "zodiac anniversary gift", "anniversary gift for him", "anniversary gift for her", "couple anniversary gift"]
SORGULAR = ["paper anniversary gift", "1st anniversary gift"]


def oas_bul(oas):
    d = json.load(open(oas))
    out = {}
    for yol, ops in d.get("paths", {}).items():
        if "/sections" not in yol:
            continue
        for yontem, op in ops.items():
            if not isinstance(op, dict):
                continue
            govde = (((op.get("requestBody") or {}).get("content") or {}))
            for ct, c in govde.items():
                props = ((c.get("schema") or {}).get("properties") or {})
                if "title" in props:
                    out[f"{yontem.upper()} {yol} ({op.get('operationId')})"] = {k: v for k, v in props["title"].items()}
    S = d.get("components", {}).get("schemas", {})
    for ad, s in S.items():
        if ad.endswith("ShopSection") and "title" in (s.get("properties") or {}):
            out[f"schema {ad}.title"] = s["properties"]["title"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oas", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--magaza", type=int, default=12)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    api = Etsy(APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")))
    rapor = {"oas_section_title": oas_bul(a.oas) if os.path.exists(a.oas) else "OAS indirilemedi"}
    rapor["aday_ilan_sayisi"] = {}
    for k in ADAYLAR:
        y = api.get("/listings/active", params={"keywords": k, "limit": 1}) or {}
        rapor["aday_ilan_sayisi"][k] = y.get("count")
    rapor["magazalar"] = {}
    for q in SORGULAR:
        sira, goruldu = [], set()
        for offset in (0, 100):
            y = api.get("/listings/active", params={"keywords": q, "limit": 100, "offset": offset,
                                                     "sort_on": "score"}) or {}
            for l in y.get("results") or []:
                sid = l.get("shop_id")
                if sid and sid not in goruldu:
                    goruldu.add(sid); sira.append((sid, l.get("listing_id"), l.get("title", "")[:90]))
            if len(sira) >= a.magaza:
                break
        liste = []
        for sid, lid, baslik in sira[:a.magaza]:
            s = api.get(f"/shops/{sid}", ok404=True) or {}
            sec = api.get(f"/shops/{sid}/sections", ok404=True) or {}
            liste.append({"shop_id": sid, "shop_name": s.get("shop_name"), "url": f"https://www.etsy.com/shop/{s.get('shop_name')}",
                          "ornek_ilan": f"https://www.etsy.com/listing/{lid}", "ornek_baslik": baslik,
                          "satis": s.get("transaction_sold_count"),
                          "bolumler": [{"title": x.get("title"), "aktif_ilan": x.get("active_listing_count")}
                                       for x in (sec.get("results") or [])]})
        rapor["magazalar"][q] = liste
    json.dump(rapor, open(out / "BOLUM_ARASTIRMA.json", "w"), ensure_ascii=False, indent=1)
    md = ["# Etsy bolum adi arastirmasi (API, salt okur)", "", "## OAS section title", "```",
          json.dumps(rapor["oas_section_title"], ensure_ascii=False, indent=1)[:3000], "```", "",
          "## Aday ifadeler: aktif ilan sayisi (rekabet, arama hacmi DEGIL)"]
    md += [f"- {k}: {v}" for k, v in rapor["aday_ilan_sayisi"].items()]
    for q, liste in rapor["magazalar"].items():
        md += ["", f"## '{q}' aramasinda ilk magazalar (sort_on=score)"]
        for m in liste:
            b = "; ".join(f"{x['title']} ({x['aktif_ilan']})" for x in m["bolumler"]) or "(bolum yok)"
            md.append(f"- {m['shop_name']} {m['url']} | satis {m['satis']} | ornek {m['ornek_ilan']} | bolumler: {b}")
    (out / "BOLUM_ARASTIRMA.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    log(f"Etsy GET cagrisi {api.calls}; kalan gunluk kota {api.remaining}; Etsy yazma cagrisi 0")


if __name__ == "__main__":
    main()
