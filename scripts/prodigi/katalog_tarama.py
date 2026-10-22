#!/usr/bin/env python3
"""GOREV 0040 - Prodigi katalog taramasi (SALT OKUMA; siparis yok, Etsy yok).
1) Kesif: aday SKU onekleri (kagit + cerceve) once 3 boyda GET /products; var olan onek 16 boyumuzda taranir.
   Kayit: aciklama, attribute degerleri (paperType, substrateWeight, color, glaze, mount...), US'e gonderim, olcu.
2) Teklif: var olan her urun icin US teklif (tum yontemler; karar Standard). Cerceve: black/white/natural ayri.
3) Fiyat TASLAGI: maliyet = urun + Standard kargo + vergi + 5 paket; Etsy kesinti 0.698 + 0.2062 x fiyat;
   hedef net baski >= 10, cerceve >= 20; onerilen fiyat x.99; rakip bandi Print 35-70, Framed 65-180.
Cikti out/: KATALOG_URUN.csv, KATALOG_TEKLIF_US.csv, FIYAT_TASLAK.csv, KATALOG_OZET.md"""
import csv
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prodigi_maliyet_api import ayikla  # noqa: E402

BOYLAR = ["8x10", "A4", "11x14", "12x16", "A3", "12x18", "16x20", "16x24", "A2", "18x24", "20x30", "24x30", "24x32", "A1", "24x36", "30x40"]
KAGIT = ["HPR", "FAP", "EMA", "HGE", "BAP", "HBA", "SAP", "CPWP", "CPP", "LPP", "GPP", "PAP", "MFA", "BLP", "POS", "PHO", "SMG", "PHR"]
CERCEVE = ["CFP", "CFPM", "CFB", "CFBM", "BOX", "BOXM", "SPF", "SPFM", "SWF", "SWFM", "FSPF", "CLF", "CLFM", "FRA", "LFP", "FAPM"]
RENKLER = ["black", "white", "natural"]
PAKET, SABIT, ORAN = 5.0, 0.698, 0.2062
OUT = Path("out")


def eta(i, n, t0, ek=""):
    g = time.time() - t0
    print(f"[{i}/{n}] {100 * i // max(n, 1)}% gecen {g:.0f}s kalan ~{g / max(i, 1) * (n - i):.0f}s {ek}", flush=True)


def urun(api, sku):
    r = api._call("GET", f"/products/{sku}")
    if r.status_code != 200:
        return None
    return (r.json() or {}).get("product")


def kayit(p, onek, boy):
    at = p.get("attributes") or {}
    us = any("US" in (v.get("shipsTo") or []) for v in p.get("variants") or [])
    d = p.get("productDimensions") or {}
    return {"onek": onek, "boy": boy, "sku": p.get("sku"), "tur": "cerceve" if onek in CERCEVE else "kagit",
            "aciklama": p.get("description", ""), "us_gonderim": us,
            "olcu": f"{d.get('width')}x{d.get('height')}{d.get('units', '')}",
            **{f"attr_{k}": "|".join(map(str, v)) for k, v in at.items()}}


def teklif(api, sku, attrs, renk):
    sec = {k: (renk if k == "color" else v[0]) for k, v in attrs.items() if len(v) > 1}
    if "color" in attrs and renk not in attrs["color"]:
        return None
    body = {"destinationCountryCode": "US", "currencyCode": "USD",
            "items": [{"sku": sku, "copies": 1, "assets": [{"printArea": "default"}], **({"attributes": sec} if sec else {})}]}
    r = api._call("POST", "/quotes", body)
    return ayikla(r.json()) if r.status_code == 200 else {"hata": {"urun": None, "lab": f"HTTP {r.status_code}"}}


def fiyat(maliyet, hedef):
    p = (maliyet + SABIT + hedef) / (1 - ORAN)
    p = math.floor(p) + 0.99 if p <= math.floor(p) + 0.99 else math.floor(p) + 1.99
    return round(p, 2), round(p - SABIT - ORAN * p - maliyet, 2)


def yaz(ad, rows):
    alan = list(dict.fromkeys(k for r in rows for k in r))
    with open(OUT / ad, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=alan); w.writeheader(); w.writerows(rows)


def main():
    from prodigi_pilot_quote import Api, load_key
    api, t0 = Api(load_key()), time.time()
    OUT.mkdir(exist_ok=True)
    onekler = KAGIT + CERCEVE
    var = []
    for i, o in enumerate(onekler, 1):
        if any(urun(api, f"GLOBAL-{o}-{b}") for b in ("8x10", "16x20", "A3")):
            var.append(o)
        eta(i, len(onekler), t0, f"kesif {o} -> {'VAR' if o in var else 'yok'}")
    urunler, t1 = [], time.time()
    isler = [(o, b) for o in var for b in BOYLAR]
    for i, (o, b) in enumerate(isler, 1):
        p = urun(api, f"GLOBAL-{o}-{b}")
        urunler.append(kayit(p, o, b) if p else {"onek": o, "boy": b, "sku": f"GLOBAL-{o}-{b}", "tur": "", "aciklama": "YOK"})
        urunler[-1]["_attrs"] = (p or {}).get("attributes") or {}
        eta(i, len(isler), t1, f"urun GLOBAL-{o}-{b} {'ok' if p else 'yok'}")
    teklifler, t2 = [], time.time()
    hedefler = [u for u in urunler if u["aciklama"] != "YOK" and u.get("us_gonderim")]
    for i, u in enumerate(hedefler, 1):
        for renk in (RENKLER if "color" in u["_attrs"] else [""]):
            q = teklif(api, u["sku"], u["_attrs"], renk)
            for yontem, v in (q or {}).items():
                teklifler.append({"sku": u["sku"], "onek": u["onek"], "boy": u["boy"], "tur": u["tur"], "renk": renk, "yontem": yontem,
                                  "urun": v.get("urun"), "kargo": v.get("kargo"), "vergi": v.get("vergi"), "toplam": v.get("toplam"),
                                  "lab": v.get("lab"), "vergi_faturada": v.get("faturada")})
        eta(i, len(hedefler), t2, f"teklif {u['sku']}")
    taslak = []
    for t in teklifler:
        if t["yontem"] != "standard" or t["urun"] is None or t["kargo"] is None:
            continue
        maliyet = round(t["urun"] + t["kargo"] + (t["vergi"] or 0) + PAKET, 2)
        hedef, band = (20, (65, 180)) if t["tur"] == "cerceve" else (10, (35, 70))
        p, net = fiyat(maliyet, hedef)
        taslak.append({"format": t["onek"], "renk": t["renk"], "boy": t["boy"], "sku": t["sku"], "lab": t["lab"], "urun": t["urun"],
                       "standard_kargo": t["kargo"], "vergi": t["vergi"], "paket": PAKET, "maliyet": maliyet, "onerilen_fiyat": p,
                       "net": net, "hedef_net": hedef, "rakip_band": f"{band[0]}-{band[1]}",
                       "band_durum": "ICINDE" if band[0] <= p <= band[1] else ("ALTINDA" if p < band[0] else "USTUNDE")})
    for u in urunler:
        u.pop("_attrs", None)
    yaz("KATALOG_URUN.csv", urunler); yaz("KATALOG_TEKLIF_US.csv", teklifler); yaz("FIYAT_TASLAK.csv", taslak)
    ozet = [f"# KATALOG_OZET (GOREV 0040) {time.strftime('%Y-%m-%d %H:%M')} UTC", "",
            f"- aday onek {len(onekler)}, var olan: {', '.join(var)}",
            f"- urun satiri {len(urunler)} (var {sum(u['aciklama'] != 'YOK' for u in urunler)}), US teklif satiri {len(teklifler)}, taslak {len(taslak)}", ""]
    for o in var:
        ornek = next((u for u in urunler if u["onek"] == o and u["aciklama"] != "YOK"), {})
        boylar = [u["boy"] for u in urunler if u["onek"] == o and u["aciklama"] != "YOK"]
        ozet.append(f"- {o}: {ornek.get('aciklama', '')} | boy {len(boylar)}/16: {' '.join(boylar)} | "
                    + " | ".join(f"{k[5:]}={v}" for k, v in ornek.items() if k.startswith("attr_")))
    (OUT / "KATALOG_OZET.md").write_text("\n".join(ozet) + "\n", encoding="utf-8")
    print("\n".join(ozet[:4]), flush=True)


if __name__ == "__main__":
    main()
