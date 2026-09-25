#!/usr/bin/env python3
"""Prodigi hesap ayari API'den okunabiliyor mu? (SALT OKUMA, 25 Eyl 2026 - canli guvenli test on kosulu)

Siparis vermeden once "Pause indefinitely" (Preferences) ayari ve hesap adresi API'de var mi diye aday uclar
YALNIZ GET ile denenir. Cikti: yol + HTTP kodu + (200 ise) ust duzey alan ADLARI; deger yazilmaz.
Kullanim: prodigi_hesap_oku.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ADAYLAR = ["/preferences", "/settings", "/account", "/accounts/me", "/me", "/merchant", "/merchants/me",
           "/user", "/profile", "/orders/settings", "/orders/preferences", "/branding", "/packaging"]


def main():
    from prodigi_pilot_quote import Api, load_key
    api = Api(load_key())
    bulunan = 0
    for yol in ADAYLAR:
        r = api._call("GET", yol)
        alanlar = ""
        if r.status_code == 200:
            try:
                d = r.json()
                alanlar = ",".join(sorted(d)[:20]) if isinstance(d, dict) else type(d).__name__
                bulunan += 1
            except ValueError:
                alanlar = "json degil"
        print(f"{yol}: HTTP {r.status_code}" + (f" alanlar={alanlar}" if alanlar else ""), flush=True)
    print(f"SONUC: hesap/ayar ucu {'VAR' if bulunan else 'YOK'} ({bulunan}/{len(ADAYLAR)} yol 200)", flush=True)


if __name__ == "__main__":
    main()
