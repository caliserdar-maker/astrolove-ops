#!/usr/bin/env python3
"""SALT OKUMA: bir ilanin satis kayitlari (getShopReceiptTransactionsByListing; transactions_r). Etsy'ye yazma yok.
Yazilan: islem tarihi (UTC), adet, fiyat, secilen varyasyonlar, receipt (OPAK KOD, IP adim 0 c 17 Kas), gonderim durumu.
Alici adi/adres/e-posta YAZILMAZ. Depo HERKESE ACIK: her satir receipt_desen.ROUTER ile maskelenir (10-12 haneli her sayi -> S-<kod>,
order_router.receipt_kod ile ayni algoritma; ilan id de maskelenir: supheli = maskele).
Kullanim: ilan_satis_oku.py --cift CANCER_LEO [--ids data/pod/pod78_ids.csv]"""
import argparse
import csv
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "guvenlik"))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402
import receipt_desen  # noqa: E402


def receipt_kod(rid):
    """order_router.receipt_kod ile ayni algoritma (HMAC-SHA256, ilk 8 hex); anahtar bu is akisinda ETSY_SHARED_SECRET
    (siparis kod anahtari yalniz siparis betiklerinde, test_siparis_kod_anahtari)."""
    import hashlib
    import hmac
    anahtar = os.environ.get("ETSY_SHARED_SECRET")
    if not anahtar:
        return "S-gizli"                 # anahtarsiz opak kod yok: kapali hata (CEO karari 3)
    return "S-" + hmac.new(anahtar.encode(), str(rid).encode(), hashlib.sha256).hexdigest()[:8]


# Varyasyon DEGERI yalniz urun secenegi ise yazilir (beden, renk, stil, cerceve, bicim, malzeme, dijital/baski secimi);
# diger her ozellik (Personalization vb.: alici metni, isim, tarih) gizlenir (CEO karari 2; bilinmeyen ozellik = gizli).
SECENEK = re.compile(r"\b(size|colou?r|style|frame|framed|format|material|digital file|print)\b", re.I)
SATIR_SONU = re.compile(r"[\r\n\x0b\x0c\x1c-\x1e\x85\u2028\u2029]")


def tek_satir(x):
    """Alan icindeki her satir sonu bosluk olur: degerden yeni '::add-mask::' / '::warning::' satiri dogamaz (\\r dahil)."""
    return SATIR_SONU.sub(" ", str(x))


def varyasyon(x):
    ad = tek_satir(x.get("formatted_name"))
    if x.get("property_id") == 54 or not SECENEK.search(ad):
        return f"{ad}=***"
    return f"{ad}={tek_satir(x.get('formatted_value'))}"


def maskele(s):
    return receipt_desen.satir_satir(s, lambda x: receipt_desen.ROUTER.sub(lambda m: receipt_kod(m.group(0)), x))


def satis_satiri(t):
    """Tek islem satiri (loga / annotation'a gider): receipt ve 10-12 haneli her sayi opak kod."""
    ts = datetime.fromtimestamp(t.get("created_timestamp") or 0, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    v = "; ".join(varyasyon(x) for x in t.get("variations") or [])
    p = t.get("price") or {}
    fiyat = round(p.get("amount", 0) / (p.get("divisor") or 1), 2)
    return maskele(f"::warning::SATIS {ts} | adet {tek_satir(t.get('quantity'))} | {fiyat} {tek_satir(p.get('currency_code'))} | {v} | "
                   f"receipt {tek_satir(t.get('receipt_id'))} | sku {tek_satir(t.get('sku'))} | "
                   f"gonderim {t.get('shipped_timestamp') and 'var' or 'yok'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cift", required=True); ap.add_argument("--ids", default="data/pod/pod78_ids.csv")
    a = ap.parse_args()
    lid = next(r["listing_id"].strip() for r in csv.DictReader(open(a.ids)) if r["cift"] == a.cift)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store); shop = os.environ["ETSY_SHOP_ID"]
    r = api.get(f"/shops/{shop}/listings/{lid}/transactions", params={"limit": 100}) or {}
    tr = sorted(r.get("results") or [], key=lambda t: t.get("created_timestamp") or 0, reverse=True)
    print(maskele(f"::warning::SATIS {a.cift} {lid}: toplam {r.get('count')} islem"))
    for t in tr[:8]:
        print(satis_satiri(t))
    print(f"::warning::BITTI | istek {api.calls} | kota {api.remaining}")


if __name__ == "__main__":
    main()
