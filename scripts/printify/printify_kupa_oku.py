#!/usr/bin/env python3
"""Printify KAZIMALI KUPA katalog okuma (15 Eki 2026, Serdar onayi). YALNIZ GET, yalniz /catalog uclari.
Urun / taslak / siparis / yukleme YOK. Izinli uclar asagidaki IZIN listesinde regex ile kilitli; disinda istek atilmaz.

Okunan: blueprint 10669 (Speckled Wayland Ceramic Mug, 13oz (Engraving)), saglayicilari, varyantlar (yerlesim alanlari),
kargo (v1 + v2 yontemleri), saglayici bilgisi; tum blueprint listesinden benzer kazimali/lazer kupalar.
Not: Printify katalog API'si urun maliyetini vermez (maliyet urun olusturunca gorunur; bu is urun olusturmaz).

Kullanim: PRINTIFY_API_KEY=... printify_kupa_oku.py <cikis_dizini>
Cikti: <cikis>/raw/*.json (ham yanitlar), <cikis>/RAPOR.md, <cikis>/BENZER.csv. Anahtar hicbir dosyaya ya da loga yazilmaz.
"""
import csv
import html
import json
import os
import re
import sys
import time

import requests

API = "https://api.printify.com"
HEDEF_BP = 10669
BEKLE = 0.4
IZIN = [
    r"/v1/catalog/blueprints\.json",
    r"/v1/catalog/blueprints/\d+\.json",
    r"/v1/catalog/blueprints/\d+/print_providers\.json",
    r"/v1/catalog/blueprints/\d+/print_providers/\d+/(variants|shipping)\.json",
    r"/v1/catalog/print_providers/\d+\.json",
    r"/v2/catalog/blueprints/\d+/print_providers/\d+/shipping\.json",
    r"/v2/catalog/blueprints/\d+/print_providers/\d+/shipping/[a-z_]+\.json",
]
SAYAC = {"istek": 0}


def oturum():
    k = os.environ.get("PRINTIFY_API_KEY", "").strip().lstrip("﻿")
    if not k:
        sys.exit("HATA anahtar yok")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {k}", "User-Agent": "AstroLoveArt-katalog-okuma"})
    return s


def get(s, yol, params=None):
    if not any(re.fullmatch(p, yol) for p in IZIN):
        raise SystemExit(f"IZINSIZ UC (istek atilmadi): GET {yol}")
    for deneme in range(4):
        time.sleep(BEKLE)
        r = s.get(API + yol, params=params, timeout=60)
        SAYAC["istek"] += 1
        if r.status_code == 429:
            time.sleep(5 * (deneme + 1))
            continue
        if r.status_code >= 400:
            return {"_hata": r.status_code, "_metin": r.text[:300]}
        return r.json()
    return {"_hata": 429, "_metin": "hiz limiti"}


def kaydet(cikis, ad, veri):
    with open(os.path.join(cikis, "raw", ad), "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)


def duz(h):
    t = re.sub(r"<br\s*/?>|</p>|</li>", "\n", h or "", flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"[ \t]+", " ", html.unescape(t)).strip()


def kargo_ozet(v1):
    satir = []
    for p in (v1 or {}).get("profiles", []) if isinstance(v1, dict) else []:
        ulkeler = p.get("countries", [])
        ilk = p.get("first_item", {})
        ek = p.get("additional_items", {})
        satir.append((",".join(ulkeler[:12]) + (" ..." if len(ulkeler) > 12 else ""),
                      f"{ilk.get('cost', '?') / 100 if isinstance(ilk.get('cost'), int) else '?'} {ilk.get('currency', '')}",
                      f"{ek.get('cost', '?') / 100 if isinstance(ek.get('cost'), int) else '?'} {ek.get('currency', '')}",
                      len(p.get("variant_ids", []))))
    return satir


def main():
    cikis = sys.argv[1]
    os.makedirs(os.path.join(cikis, "raw"), exist_ok=True)
    s = oturum()
    R = []

    bp = get(s, f"/v1/catalog/blueprints/{HEDEF_BP}.json")
    kaydet(cikis, f"bp_{HEDEF_BP}.json", bp)
    R.append(f"# Printify kazimali kupa: blueprint {HEDEF_BP}\n")
    R.append(f"Kaynak uclar ve ham yanitlar: raw/. Okuma: yalniz GET katalog. Istek sayisi sonda.\n")
    R.append(f"## Blueprint\n- Ad: {bp.get('title', 'bulunamadi')}  [GET /v1/catalog/blueprints/{HEDEF_BP}.json]")
    R.append(f"- Marka / model: {bp.get('brand', '?')} / {bp.get('model', '?')}")
    aciklama = duz(bp.get("description", ""))
    R.append(f"- Katalog aciklamasi (tam metin):\n\n```\n{aciklama or 'bulunamadi'}\n```")
    bakim = [l for l in aciklama.splitlines() if re.search(r"dishwasher|microwave|hand wash|oven|freezer", l, re.I)]
    R.append("- Bakim satirlari (aciklamadan): " + ("; ".join(bakim) if bakim else "aciklamada bulunamadi"))

    pps = get(s, f"/v1/catalog/blueprints/{HEDEF_BP}/print_providers.json")
    kaydet(cikis, f"bp_{HEDEF_BP}_print_providers.json", pps)
    R.append(f"\n## Saglayicilar  [GET /v1/catalog/blueprints/{HEDEF_BP}/print_providers.json]")
    if not isinstance(pps, list):
        R.append(f"- HATA: {pps}")
        pps = []
    for pp in pps:
        R.append(f"- id {pp.get('id')}: {pp.get('title')}")

    for pp in pps:
        pid = pp.get("id")
        R.append(f"\n## Saglayici {pid}: {pp.get('title')}")
        info = get(s, f"/v1/catalog/print_providers/{pid}.json")
        kaydet(cikis, f"pp_{pid}.json", info)
        loc = info.get("location") if isinstance(info, dict) else None
        R.append(f"- Konum: {json.dumps(loc, ensure_ascii=False) if loc else 'bulunamadi'}  [GET /v1/catalog/print_providers/{pid}.json]")

        var = get(s, f"/v1/catalog/blueprints/{HEDEF_BP}/print_providers/{pid}/variants.json", {"show-out-of-stock": 1})
        kaydet(cikis, f"bp_{HEDEF_BP}_pp_{pid}_variants.json", var)
        R.append(f"\n### Varyantlar  [GET /v1/catalog/blueprints/{HEDEF_BP}/print_providers/{pid}/variants.json]")
        vl = var.get("variants", []) if isinstance(var, dict) else []
        if not vl:
            R.append(f"- bulunamadi ({var if isinstance(var, dict) and '_hata' in var else 'bos'})")
        for v in vl:
            yer = "; ".join(f"{p.get('position')}: {p.get('width')}x{p.get('height')} px"
                            + (f" ({','.join(p.get('decoration_methods', []))})" if p.get('decoration_methods') else "")
                            for p in v.get("placeholders", []))
            R.append(f"- {v.get('id')} | {v.get('title')} | secenek {json.dumps(v.get('options', {}), ensure_ascii=False)} | "
                     f"stok {v.get('is_available', '?')} | alan: {yer or 'bulunamadi'}")
        R.append("- Fiyat (ucretsiz plan / Premium): katalog API'si maliyet vermez; urun olusturmadan okunamaz -> bulunamadi.")

        v1 = get(s, f"/v1/catalog/blueprints/{HEDEF_BP}/print_providers/{pid}/shipping.json")
        kaydet(cikis, f"bp_{HEDEF_BP}_pp_{pid}_shipping_v1.json", v1)
        R.append(f"\n### Kargo v1  [GET /v1/catalog/blueprints/{HEDEF_BP}/print_providers/{pid}/shipping.json]")
        if isinstance(v1, dict) and "handling_time" in v1:
            R.append(f"- Hazirlama (handling) suresi: {json.dumps(v1.get('handling_time'), ensure_ascii=False)}")
        for ulke, ilk, ek, n in kargo_ozet(v1):
            R.append(f"- {ulke} | ilk {ilk} | ek {ek} | varyant {n}")
        if not kargo_ozet(v1):
            R.append(f"- bulunamadi ({v1 if isinstance(v1, dict) and '_hata' in v1 else 'bos'})")

        v2 = get(s, f"/v2/catalog/blueprints/{HEDEF_BP}/print_providers/{pid}/shipping.json")
        kaydet(cikis, f"bp_{HEDEF_BP}_pp_{pid}_shipping_v2.json", v2)
        R.append(f"\n### Kargo v2 yontemleri  [GET /v2/catalog/blueprints/{HEDEF_BP}/print_providers/{pid}/shipping.json]")
        yontemler = []
        if isinstance(v2, dict):
            for d in v2.get("data", []) or []:
                ad = (d.get("attributes") or {}).get("name") or d.get("id")
                if isinstance(ad, str):
                    yontemler.append(ad)
        R.append("- " + (", ".join(yontemler) if yontemler else f"bulunamadi ({v2 if isinstance(v2, dict) and '_hata' in v2 else 'bos'})"))
        for y in yontemler:
            yk = re.sub(r"[^a-z_]", "", y.lower())
            if not yk:
                continue
            d = get(s, f"/v2/catalog/blueprints/{HEDEF_BP}/print_providers/{pid}/shipping/{yk}.json")
            kaydet(cikis, f"bp_{HEDEF_BP}_pp_{pid}_shipping_v2_{yk}.json", d)
            R.append(f"\n#### {y}  [GET /v2/catalog/blueprints/{HEDEF_BP}/print_providers/{pid}/shipping/{yk}.json]")
            gor = set()
            for x in (d.get("data", []) if isinstance(d, dict) else []):
                a = x.get("attributes") or {}
                anahtar = (a.get("country", {}).get("code") if isinstance(a.get("country"), dict) else a.get("country"))
                h = a.get("handlingTime") or a.get("handling_time")
                ilk = a.get("shippingCost") or a.get("firstItem") or {}
                ek = a.get("shippingCostAdditional") or a.get("additionalItems") or {}
                st = f"{anahtar} | ilk {json.dumps(ilk, ensure_ascii=False)} | ek {json.dumps(ek, ensure_ascii=False)} | sure {json.dumps(h, ensure_ascii=False)}"
                if anahtar in ("US", "GB", "CA", "AU", "DE", "FR", "REST_OF_THE_WORLD") and st not in gor:
                    gor.add(st)
                    R.append(f"- {st}")
            if not gor:
                R.append("- secili ulkeler (US, GB, CA, AU, DE, FR) icin satir bulunamadi; ham JSON'a bak")

    # benzer kazimali / lazer kupalar
    tum = get(s, "/v1/catalog/blueprints.json")
    kaydet(cikis, "blueprints_all.json", tum)
    aday = []
    for b in tum if isinstance(tum, list) else []:
        t = (b.get("title") or "")
        if re.search(r"engrav|laser|etched", t, re.I) and re.search(r"mug|cup|tumbler", t, re.I):
            aday.append(b)
    R.append(f"\n## Benzer kazimali/lazer kupa ve bardaklar  [GET /v1/catalog/blueprints.json, baslikta engrav/laser/etched + mug/cup/tumbler]")
    R.append(f"- Aday sayisi: {len(aday)}")
    with open(os.path.join(cikis, "BENZER.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["blueprint_id", "baslik", "marka", "saglayici_id", "saglayici", "ABD_ilk_kargo", "ABD_ek_kargo", "kaynak"])
        for b in aday:
            bid = b.get("id")
            pl = get(s, f"/v1/catalog/blueprints/{bid}/print_providers.json")
            kaydet(cikis, f"bp_{bid}_print_providers.json", pl)
            for pp in pl if isinstance(pl, list) else []:
                pid = pp.get("id")
                sh = get(s, f"/v1/catalog/blueprints/{bid}/print_providers/{pid}/shipping.json")
                us_ilk = us_ek = "bulunamadi"
                for p in (sh.get("profiles", []) if isinstance(sh, dict) else []):
                    if "US" in p.get("countries", []):
                        us_ilk = p.get("first_item", {}).get("cost")
                        us_ek = p.get("additional_items", {}).get("cost")
                        us_ilk = us_ilk / 100 if isinstance(us_ilk, int) else us_ilk
                        us_ek = us_ek / 100 if isinstance(us_ek, int) else us_ek
                        break
                w.writerow([bid, b.get("title"), b.get("brand"), pid, pp.get("title"), us_ilk, us_ek,
                            f"GET /v1/catalog/blueprints/{bid}/print_providers/{pid}/shipping.json"])
                R.append(f"- {bid} | {b.get('title')} | saglayici {pid} {pp.get('title')} | ABD ilk {us_ilk} / ek {us_ek} USD")

    R.append(f"\n---\nToplam istek: {SAYAC['istek']} (yalniz GET, yalniz /catalog). Urun/taslak/siparis/yukleme: 0.")
    with open(os.path.join(cikis, "RAPOR.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(R) + "\n")
    print(f"BITTI istek {SAYAC['istek']} | saglayici {len(pps)} | benzer {len(aday)}")


if __name__ == "__main__":
    main()
