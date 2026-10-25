#!/usr/bin/env python3
"""Printful poster maliyet + kargo (SALT OKUMA; siparis/urun OLUSTURMAZ). Serdar 25 Eki: fiyat tablosu gercek Printful
verisiyle hesaplanacak; kargo takip numarali olmali.
1) GET /products/{id} (varsayilan 1 = Enhanced Matte Paper Poster (in), 268 = (cm)): her varyant boy + fiyat.
2) POST /shipping/rates: her boy x ulke (US CA GB DE FR AU NO TR IL BR JP) tek adet; donen secenekler (ad, ucret, sure).
Cikti: <out>/PRINTFUL_POSTER.json (ham) + PRINTFUL_POSTER.csv (urun, boy, varyant, fiyat, ulke, kargo_adi, kargo, min-max gun).
Kullanim: poster_fiyat.py <out>  (env: PRINTFUL_TOKEN; URUNLER="1 268"; ULKELER="US CA ...")"""
import csv
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

API = "https://api.printful.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36 astrolove-ops"
URUNLER = os.environ.get("URUNLER", "1 268").split()
ULKELER = os.environ.get("ULKELER", "US CA GB DE FR AU NO TR IL BR JP").split()
ADETLER = [int(x) for x in (os.environ.get("ADET") or "1").split()]   # "1 2": ikinci urun kargosu = rate(2) - rate(1)
ADRES = {"US": {"state_code": "NY", "city": "New York", "zip": "10001"}, "CA": {"state_code": "ON", "city": "Toronto", "zip": "M5V 2T6"},
         "GB": {"city": "London", "zip": "SW1A 1AA"}, "DE": {"city": "Berlin", "zip": "10115"}, "FR": {"city": "Paris", "zip": "75001"},
         "AU": {"state_code": "NSW", "city": "Sydney", "zip": "2000"}, "NO": {"city": "Oslo", "zip": "0150"},
         "TR": {"city": "Istanbul", "zip": "34000"}, "IL": {"city": "Tel Aviv", "zip": "6100000"},
         "BR": {"state_code": "SP", "city": "Sao Paulo", "zip": "01000-000"}, "JP": {"city": "Tokyo", "zip": "100-0001"},
         "IT": {"city": "Rome", "zip": "00184"}, "ES": {"city": "Madrid", "zip": "28001"}, "NL": {"city": "Amsterdam", "zip": "1012 JS"},
         "PL": {"city": "Warsaw", "zip": "00-001"}, "IE": {"city": "Dublin", "zip": "D02 X285"}}


def istek(yol, token, veri=None):
    req = urllib.request.Request(API + yol, data=json.dumps(veri).encode() if veri is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                                          "User-Agent": UA, "Accept": "application/json"},
                                 method="POST" if veri is not None else "GET")
    for deneme in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            g = e.read().decode()[:2000]
            if e.code == 429 and deneme < 2:
                time.sleep(30)
                continue
            try:
                return e.code, json.loads(g)
            except ValueError:
                return e.code, {"ham": g}


def main():
    token = os.environ["PRINTFUL_TOKEN"]
    out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    ham, satir = {"urunler": {}, "kargo": []}, []
    for uid in URUNLER:
        st, d = istek(f"/products/{uid}", token)
        ham["urunler"][uid] = {"status": st, "yanit": d}
        if st != 200:
            print(f"urun {uid}: HTTP {st}", flush=True)
            continue
        urun = (d.get("result") or {}).get("product") or {}
        varyantlar = (d.get("result") or {}).get("variants") or []
        print(f"urun {uid} {urun.get('title')}: {len(varyantlar)} varyant", flush=True)
        for v in varyantlar:
            boy, fiyat, vid = v.get("size"), v.get("price"), v.get("id")
            for ulke in ULKELER:
              for adet in ADETLER:
                veri = {"recipient": {"country_code": ulke, **ADRES.get(ulke, {})},
                        "items": [{"variant_id": vid, "quantity": adet}], "currency": "USD"}
                s2, k = istek("/shipping/rates", token, veri)
                ham["kargo"].append({"urun": uid, "varyant": vid, "boy": boy, "ulke": ulke, "adet": adet, "status": s2, "yanit": k})
                secenekler = k.get("result") if isinstance(k, dict) and isinstance(k.get("result"), list) else []
                if not secenekler:
                    satir.append([uid, urun.get("title"), boy, vid, fiyat, ulke, adet, f"HATA {s2}", "", "", ""])
                for s in secenekler:
                    satir.append([uid, urun.get("title"), boy, vid, fiyat, ulke, adet, s.get("name") or s.get("id"), s.get("rate"),
                                  s.get("minDeliveryDays"), s.get("maxDeliveryDays")])
                time.sleep(0.6)
            print(f"  {boy} varyant {vid} fiyat {fiyat}: {len(ULKELER)} ulke", flush=True)
    (out / "PRINTFUL_POSTER.json").write_text(json.dumps(ham, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "PRINTFUL_POSTER.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["urun", "urun_adi", "boy", "varyant", "fiyat", "ulke", "adet", "kargo_adi", "kargo", "min_gun", "max_gun"])
        w.writerows(satir)
    print(f"SATIR {len(satir)}", flush=True)
    sys.exit(0 if satir else 1)


if __name__ == "__main__":
    main()
