#!/usr/bin/env python3
"""
Son N satisin kaynagi (SALT OKUMA) - Serdar, 26 Eyl 2026.

Etsy API siparis basina trafik kaynagi vermez. Olculebilen tek iz: odeme hesabi
defteri (getShopPaymentAccountLedgerEntries). Offsite Ads ile gelen satista Etsy
o fise bagli ayri bir "offsite ads" ucreti keser. Bu ucret varsa kaynak = OFFSITE ADS.
Yoksa kaynak = Etsy ici (organik arama/magaza ya da site ici Etsy Ads; site ici
reklam atfi API'de yok, yalniz Etsy Ads panelinde).

Cikti: out/SATIS_KAYNAK.md + out/SATIS_KAYNAK.json. Musteri adi/adresi okunmaz/yazilmaz;
fis numarasi yalniz son 4 hane. Etsy'ye YAZMA YOK.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

N = int(os.environ.get("ADET", "4"))
OUT = Path("out")


def son4(x):
    return "***" + str(x)[-4:]


def tarih(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def para(m):
    try:
        return round(int(m["amount"]) / int(m["divisor"]), 2), m.get("currency_code", "")
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None, ""


def main():
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]

    rc = api.get(f"/shops/{shop}/receipts",
                 {"limit": N, "sort_on": "created", "sort_order": "desc", "was_paid": "true"})
    fisler = rc.get("results") or []
    if not fisler:
        raise SystemExit("HATA: fis bulunamadi")
    en_eski = min(int(f["created_timestamp"]) for f in fisler)

    # Defter: en eski fisten 1 gun once -> simdi
    kayit, offset = [], 0
    while True:
        d = api.get(f"/shops/{shop}/payment-account/ledger-entries",
                    {"min_created": en_eski - 86400, "max_created": int(time.time()),
                     "limit": 100, "offset": offset})
        r = d.get("results") or []
        kayit += r
        if len(r) < 100 or offset > 2000:
            break
        offset += 100

    fis_ids = {str(f["receipt_id"]) for f in fisler}
    tx_to_fis = {}
    for f in fisler:
        for t in f.get("transactions") or []:
            tx_to_fis[str(t.get("transaction_id"))] = str(f["receipt_id"])

    def bagli_fis(e):
        ref = str(e.get("reference_id") or "")
        if ref in fis_ids:
            return ref
        if ref in tx_to_fis:
            return tx_to_fis[ref]
        for adj in e.get("payment_adjustments") or []:
            if str(adj.get("receipt_id") or "") in fis_ids:
                return str(adj["receipt_id"])
        return None

    turler, toplamlar, ham = {}, {}, []
    per_fis = {str(f["receipt_id"]): [] for f in fisler}
    for e in kayit:
        tur = str(e.get("ledger_type") or "")
        turler[tur] = turler.get(tur, 0) + 1
        tutar = round(int(e.get("amount") or 0) / 100, 2)
        toplamlar[tur] = round(toplamlar.get(tur, 0) + tutar, 2)
        ham.append({"tur": tur, "ref_tur": e.get("reference_type"), "tutar": tutar,
                    "para": e.get("currency"), "tarih": tarih(e.get("created_timestamp") or 0),
                    "fis_bagli": son4(bagli_fis(e)) if bagli_fis(e) else ""})
        rid = bagli_fis(e)
        if rid:
            per_fis[rid].append({"tur": tur, "ref_tur": e.get("reference_type"),
                                 "tutar": round(int(e.get("amount") or 0) / 100, 2),
                                 "aciklama": (e.get("description") or "")[:60]})

    satirlar, js = [], []
    for f in fisler:
        rid = str(f["receipt_id"])
        tx = f.get("transactions") or []
        urun = "; ".join((t.get("title") or "")[:45] for t in tx)
        dijital = all(t.get("is_digital") for t in tx) if tx else None
        toplam, cur = para(f.get("grandtotal") or {})
        e = per_fis[rid]
        offsite = [x for x in e if "offsite" in (x["tur"] + " " + x["aciklama"]).lower()]
        kaynak = "OFFSITE ADS" if offsite else "Etsy ici (organik ya da site ici Etsy Ads)"
        ulke = f.get("country_iso") or ""
        satirlar.append(f"| {son4(rid)} | {tarih(f['created_timestamp'])} | {ulke} | "
                        f"{'dijital' if dijital else 'fiziksel'} | {toplam} {cur} | {kaynak} | "
                        f"{', '.join(sorted({x['tur'] for x in e})) or '-'} |")
        js.append({"fis": son4(rid), "tarih": tarih(f["created_timestamp"]), "ulke": ulke,
                   "dijital": dijital, "toplam": toplam, "para": cur, "urun": urun,
                   "kaynak": kaynak, "defter": e})

    OUT.mkdir(exist_ok=True)
    md = ["# Son satislarin kaynagi (salt okuma, " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + ")", "",
          "| Fis | Tarih | Ulke | Tur | Toplam | Kaynak | Defter kayit turleri |",
          "|---|---|---|---|---|---|---|", *satirlar, "",
          "Defterdeki tum kayit turleri (donem): " + ", ".join(f"{k}={v}" for k, v in sorted(turler.items())),
          "", "Not: Etsy API site ici Etsy Ads atfini vermez; 'Etsy ici' = organik ya da Etsy Ads."]
    (OUT / "SATIS_KAYNAK.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "SATIS_KAYNAK.json").write_text(json.dumps({"satislar": js, "defter_turleri": turler,
                                                       "defter_toplam": toplamlar, "defter_ham": ham},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
    # Depo herkese acik olabilir: siparis satirlari loga YAZILMAZ, yalniz Drive'a.
    log(f"{len(js)} satis yazildi; OFFSITE ADS: {sum(1 for x in js if x['kaynak'] == 'OFFSITE ADS')}")
    log("Defter turleri: " + ", ".join(sorted(turler)))
    log(f"Etsy cagri: {api.calls}, kota kalan: {api.remaining}")


if __name__ == "__main__":
    main()
