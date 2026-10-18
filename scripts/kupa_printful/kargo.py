#!/usr/bin/env python3
"""Printful kargo ucretleri (salt okuma): POST /shipping/rates. Siparis/urun olusturmaz.
Varsayilan ulkeler US, GB, DE; her ulkede ayri ayri varyant 1320 (11 oz) x1 ve 4830 (15 oz) x1.
Once yalniz ulke kodu denenir; API adres alani isterse ornek adresle tekrar denenir ve raporda yazilir
(US: NY 10001; GB: London SW1A 1AA; DE: Berlin 10115; CA: ON M5V 2T6; AU: NSW 2000; digerleri baskent posta kodu).
Kullanim: python kargo.py <cikti_klasoru>   (env: PRINTFUL_TOKEN)
Istege bagli ortam: KARGO_ULKELER="FR IT ..." (varsayilan "US GB DE"), KARGO_AD=KARGO_EK (cikti dosya adi,
varsayilan KARGO), KARGO_YALNIZ="Flat Rate" (yalniz adi bununla baslayan secenekler tabloya yazilir; ham yanit tam).
Cikti: <KARGO_AD>.json (ham yanitlar dahil) + <KARGO_AD>.txt (tablo)."""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

API = "https://api.printful.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36 astrolove-ops")
ULKELER = os.environ.get("KARGO_ULKELER", "US GB DE").split()
AD = os.environ.get("KARGO_AD", "KARGO")
YALNIZ = os.environ.get("KARGO_YALNIZ", "").strip()
VARYANTLAR = [(1320, "11 oz"), (4830, "15 oz")]
ORNEK_ADRES = {
    "US": {"state_code": "NY", "city": "New York", "zip": "10001"},
    "GB": {"city": "London", "zip": "SW1A 1AA"},
    "DE": {"city": "Berlin", "zip": "10115"},
    "FR": {"city": "Paris", "zip": "75001"},
    "IT": {"city": "Roma", "zip": "00118"},
    "ES": {"city": "Madrid", "zip": "28001"},
    "NL": {"city": "Amsterdam", "zip": "1012 JS"},
    "PL": {"city": "Warszawa", "zip": "00-001"},
    "AU": {"state_code": "NSW", "city": "Sydney", "zip": "2000"},
    "CA": {"state_code": "ON", "city": "Toronto", "zip": "M5V 2T6"},
}
VERGI_ANAHTAR = ("tax", "vat", "vergi", "duty", "incl")


def post(yol, token, veri):
    req = urllib.request.Request(
        API + yol, data=json.dumps(veri).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": UA, "Accept": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        govde = e.read().decode()[:3000]
        try:
            return e.code, json.loads(govde)
        except ValueError:
            return e.code, {"ham": govde}


def vergi_alanlari(d, yol=""):
    """Yanittaki vergi/KDV ile ilgili tum alanlar (anahtar adina gore)."""
    bulunan = {}
    if isinstance(d, dict):
        for k, v in d.items():
            y = f"{yol}.{k}" if yol else k
            if any(a in k.lower() for a in VERGI_ANAHTAR):
                bulunan[y] = v
            bulunan.update(vergi_alanlari(v, y))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            bulunan.update(vergi_alanlari(v, f"{yol}[{i}]"))
    return bulunan


def main():
    token = os.environ["PRINTFUL_TOKEN"]
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    kayitlar = []
    toplam = len(ULKELER) * len(VARYANTLAR)
    n = 0
    for ulke in ULKELER:
        for vid, boy in VARYANTLAR:
            n += 1
            alici = {"country_code": ulke}
            govde = {"recipient": alici, "items": [{"variant_id": vid, "quantity": 1}]}
            kod, yanit = post("/shipping/rates", token, govde)
            ornek = False
            if kod != 200:
                print(f"OZET ilk_deneme {ulke} {boy} HTTP {kod} {json.dumps(yanit)[:400]}")
                alici = {"country_code": ulke, **ORNEK_ADRES[ulke]}
                govde = {"recipient": alici, "items": [{"variant_id": vid, "quantity": 1}]}
                kod, yanit = post("/shipping/rates", token, govde)
                ornek = True
            secenekler = []
            if kod == 200:
                for s in yanit.get("result", []):
                    if YALNIZ and not str(s.get("name") or "").startswith(YALNIZ):
                        continue
                    secenekler.append({k: s.get(k) for k in ("id", "name", "rate", "currency",
                                                             "minDeliveryDays", "maxDeliveryDays",
                                                             "minDeliveryDate", "maxDeliveryDate")})
            kayit = {"ulke": ulke, "boy": boy, "varyant": vid, "alici": alici, "ornek_adres": ornek,
                     "http": kod, "secenekler": secenekler, "vergi_alanlari": vergi_alanlari(yanit),
                     "ham": yanit}
            kayitlar.append(kayit)
            print(f"[{n}/{toplam} %{100 * n // toplam}] OZET kargo {ulke} {boy} v{vid} HTTP {kod} "
                  f"ornek_adres={ornek} {[(s['name'], s['rate'], s['currency']) for s in secenekler]} "
                  f"vergi={kayit['vergi_alanlari'] or 'yok'}", flush=True)

    (out / f"{AD}.json").write_text(json.dumps(kayitlar, indent=2, ensure_ascii=False))
    sat = ["ulke | boy | varyant | kargo secenegi | ucret | para birimi | teslim (gun) | adres | vergi/KDV (API)"]
    for k in kayitlar:
        adres = "ornek: " + ", ".join(f"{a}={b}" for a, b in k["alici"].items() if a != "country_code") \
            if k["ornek_adres"] else "yalniz ulke kodu"
        vergi = json.dumps(k["vergi_alanlari"], ensure_ascii=False) if k["vergi_alanlari"] else "API vermedi"
        if not k["secenekler"]:
            sat.append(f"{k['ulke']} | {k['boy']} | {k['varyant']} | {'HATA HTTP ' + str(k['http']) if k['http'] != 200 else 'secenek yok (' + (YALNIZ or '-') + ')'} | - | - | - | {adres} | -")
        for s in k["secenekler"]:
            sat.append(f"{k['ulke']} | {k['boy']} | {k['varyant']} | {s['name']} | {s['rate']} | {s['currency']} | "
                       f"{s['minDeliveryDays']}-{s['maxDeliveryDays']} | {adres} | {vergi}")
    (out / f"{AD}.txt").write_text("\n".join(sat) + "\n")
    print("\n".join(sat))
    hata = [k for k in kayitlar if k["http"] != 200]
    if hata:
        print("OZET HATA kargo", [(k["ulke"], k["boy"], k["http"]) for k in hata])
        sys.exit(1)


if __name__ == "__main__":
    main()
