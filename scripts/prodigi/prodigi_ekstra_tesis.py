#!/usr/bin/env python3
"""
Paket ekstralari (kartpostal + 2 sticker) - tesis ve fatura dogrulamasi (SALT OKUMA, 25 Eyl 2026, Serdar B + A).

 1) Canli Prodigi siparisleri: GET /orders (liste) + GET /orders/ord_14538276. Her siparis icin YALNIZ
    siparis id, tarih, durum, varis ulkesi, uretim tesisi (shipments[].fulfillmentLocation) ve fatura kalemleri
    (charges[].items: description / itemSku / cost). Alici adi, adres, e-posta, merchantReference YAZILMAZ.
 2) Ekstra fatura kalemi: aciklamasi/SKU'su kartpostal / sticker / insert / packaging gecen kalem.
    Tesis bazinda: ekstra faturalanmis siparis sayisi / toplam siparis.
 3) Kur: ECB gunluk referans kuru (eurofxref-daily.xml): GBP->USD = USD/EUR / GBP/EUR.
    Yayimlanan fiyat (Prodigi packaging inserts sayfasi): kartpostal 2.00 GBP + 2 x sticker 1.00 GBP = 4.00 GBP.

Cikti: out/PRODIGI_EKSTRA_TESIS.md + .json (Drive TEMP/PRODIGI/). POST yok, siparis/teklif acilmaz.
Kullanim: prodigi_ekstra_tesis.py [--out-dir out] [--self-test]
"""
import argparse
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ECB = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
EKSTRA_GBP = {"kartpostal": 2.00, "sticker": 1.00}      # Prodigi fiyat tablosu (standart); pakette 1 kartpostal + 2 sticker
PAKET_GBP = EKSTRA_GBP["kartpostal"] + 2 * EKSTRA_GBP["sticker"]
EKSTRA_DESEN = re.compile(r"post\s*card|sticker|insert|packag|branded", re.I)
REF_SIPARIS = "ord_14538276"


def kur_gbp_usd(get=requests.get):
    r = get(ECB, timeout=30)
    r.raise_for_status()
    kok = ET.fromstring(r.content)
    oran, tarih = {}, ""
    for c in kok.iter():
        if c.get("time"):
            tarih = c.get("time")
        if c.get("currency"):
            oran[c.get("currency")] = float(c.get("rate"))
    return round(oran["USD"] / oran["GBP"], 4), tarih


def para(c):
    try:
        return float((c or {}).get("amount")), (c or {}).get("currency", "")
    except (TypeError, ValueError):
        return None, (c or {}).get("currency", "")


def siparis_ozet(o):
    """Musteri verisi YOK: yalniz id / tarih / durum / varis ulkesi / tesis / fatura kalemleri."""
    labs = []
    for sh in o.get("shipments") or []:
        fl = sh.get("fulfillmentLocation") or {}
        if fl:
            labs.append(f"{fl.get('countryCode', '')}/{fl.get('labCode', '')}")
    kalemler, ekstra = [], []
    toplam = None
    for ch in o.get("charges") or []:
        t, cur = para(ch.get("totalCost"))
        toplam = (toplam or 0) + (t or 0)
        for it in ch.get("items") or []:
            tutar, c = para(it.get("cost"))
            d = {"aciklama": str(it.get("description") or "")[:80], "sku": str(it.get("itemSku") or "")[:60],
                 "tutar": tutar, "para": c or cur}
            kalemler.append(d)
            if EKSTRA_DESEN.search(f"{d['aciklama']} {d['sku']}"):
                ekstra.append(d)
    return {"id": o.get("id"), "tarih": str(o.get("created") or "")[:10],
            "durum": (o.get("status") or {}).get("stage"),
            "varis": ((o.get("recipient") or {}).get("address") or {}).get("countryCode", ""),
            "tesis": " ".join(dict.fromkeys(labs)) or "-", "kalemler": kalemler,
            "ekstra_kalem": ekstra, "ekstra_toplam": round(sum(x["tutar"] or 0 for x in ekstra), 2),
            "fatura_toplam": round(toplam, 2) if toplam is not None else None}


def siparisler(api, en_fazla=300):
    out, skip = [], 0
    while len(out) < en_fazla:
        r = api._call("GET", f"/orders?top=50&skip={skip}")
        if r.status_code != 200:
            break
        d = r.json()
        out += d.get("orders") or []
        if not d.get("hasMore"):
            break
        skip += 50
        time.sleep(0.3)
    if not any(o.get("id") == REF_SIPARIS for o in out):
        r = api._call("GET", f"/orders/{REF_SIPARIS}")
        if r.status_code == 200 and (r.json() or {}).get("order"):
            out.append(r.json()["order"])
    return out


def rapor(ozetler, kur, tarih, out):
    tesis = {}
    for s in ozetler:
        for lab in s["tesis"].split():
            t = tesis.setdefault(lab, {"siparis": 0, "ekstra_faturali": 0, "ekstra_usd": []})
            t["siparis"] += 1
            if s["ekstra_kalem"]:
                t["ekstra_faturali"] += 1
                t["ekstra_usd"].append(s["ekstra_toplam"])
    ref = next((s for s in ozetler if s["id"] == REF_SIPARIS), None)
    paket_usd = round(PAKET_GBP * kur, 2) if kur else None
    md = [f"# Paket ekstralari: tesis + fatura dogrulamasi (salt okuma, {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC)", "",
          f"- Yayimlanan fiyat: kartpostal {EKSTRA_GBP['kartpostal']:.2f} GBP + 2 x sticker {EKSTRA_GBP['sticker']:.2f} GBP "
          f"= {PAKET_GBP:.2f} GBP",
          f"- Kur (ECB {tarih}): 1 GBP = {kur} USD -> paket {paket_usd} USD", ""]
    if ref:
        md += [f"## {REF_SIPARIS} (ABD dogrulamasi)", "",
               f"- tarih {ref['tarih']}, durum {ref['durum']}, varis {ref['varis']}, tesis {ref['tesis']}, fatura toplam {ref['fatura_toplam']}",
               f"- ekstra kalem toplami: {ref['ekstra_toplam']} (yayimlanan fiyattan: {paket_usd})", "",
               "| aciklama | sku | tutar | para |", "|---|---|---|---|"]
        md += [f"| {k['aciklama']} | {k['sku']} | {k['tutar']} | {k['para']} |" for k in ref["kalemler"]]
        md.append("")
    else:
        md += [f"## {REF_SIPARIS}: OKUNAMADI", ""]
    md += ["## Tesis bazinda (canli siparis kayitlari)", "", "| tesis | siparis | ekstra faturali | ekstra tutarlari |", "|---|---|---|---|"]
    md += [f"| {lab} | {t['siparis']} | {t['ekstra_faturali']} | {', '.join(str(x) for x in t['ekstra_usd'][:8])} |"
           for lab, t in sorted(tesis.items())]
    md += ["", "## Siparisler (musteri verisi yok)", "", "| id | tarih | durum | varis | tesis | ekstra | fatura |", "|---|---|---|---|---|---|---|"]
    md += [f"| {s['id']} | {s['tarih']} | {s['durum']} | {s['varis']} | {s['tesis']} | {s['ekstra_toplam']} | {s['fatura_toplam']} |"
           for s in ozetler]
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "PRODIGI_EKSTRA_TESIS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (Path(out) / "PRODIGI_EKSTRA_TESIS.json").write_text(json.dumps(
        {"kur_gbp_usd": kur, "kur_tarih": tarih, "paket_gbp": PAKET_GBP, "paket_usd": paket_usd, "tesis": tesis,
         "ref": ref, "siparisler": ozetler}, indent=1, ensure_ascii=False), encoding="utf-8")
    return "\n".join(md)


def self_test():
    o = {"id": "ord_1", "created": "2026-09-10T10:00:00Z", "status": {"stage": "Complete"}, "merchantReference": "etsy-1000000001",
         "recipient": {"name": "Gizli Kisi", "email": "g@x.com", "address": {"line1": "1 Gizli St", "countryCode": "US"}},
         "shipments": [{"fulfillmentLocation": {"countryCode": "US", "labCode": "prodigi_us"}}],
         "charges": [{"totalCost": {"amount": "21.85", "currency": "USD"}, "items": [
             {"description": "GLOBAL-HPR-8x10", "itemSku": "GLOBAL-HPR-8x10", "cost": {"amount": "10.00", "currency": "USD"},
              "merchantItemReference": "etsy-1000000001-1"},
             {"description": "Branded postcard insert", "itemSku": "", "cost": {"amount": "2.50", "currency": "USD"}},
             {"description": "Packaging sticker", "itemSku": "", "cost": {"amount": "2.50", "currency": "USD"}},
             {"description": "Shipping", "itemSku": "", "cost": {"amount": "6.85", "currency": "USD"}}]}]}
    s = siparis_ozet(o)
    assert s["tesis"] == "US/prodigi_us" and s["ekstra_toplam"] == 5.0 and s["varis"] == "US", s
    import tempfile
    d = tempfile.mkdtemp()
    metin = rapor([dict(s, id=REF_SIPARIS)], 1.34, "2026-09-25", d) + Path(d, "PRODIGI_EKSTRA_TESIS.json").read_text()
    for gizli in ("Gizli", "g@x.com", "1000000001"):
        assert gizli not in metin, gizli
    assert "paket 5.36 USD" in metin, metin[:400]

    class R:
        status_code, content = 200, (b"<gesmes:Envelope xmlns:gesmes='g' xmlns='e'><Cube><Cube time='2026-09-25'>"
                                     b"<Cube currency='USD' rate='1.1700'/><Cube currency='GBP' rate='0.8700'/></Cube></Cube></gesmes:Envelope>")
        def raise_for_status(self): pass
    assert kur_gbp_usd(lambda *a, **k: R()) == (round(1.17 / 0.87, 4), "2026-09-25")
    print("self-test OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    from prodigi_pilot_quote import Api, leak_check, load_key
    try:
        kur, tarih = kur_gbp_usd()
    except Exception as e:                               # noqa: BLE001
        kur, tarih = None, f"OKUNAMADI ({type(e).__name__})"
    api = Api(load_key())
    ozetler = [siparis_ozet(o) for o in siparisler(api)]
    print(rapor(ozetler, kur, tarih, a.out_dir))
    leak_check(a.out_dir)


if __name__ == "__main__":
    main()
