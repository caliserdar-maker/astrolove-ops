#!/usr/bin/env python3
"""KUPA ORCHARD 78 ilan: RU katmani (Etsy listing translation, language=ru). Serdar 19 Eki 2026.

Kaynak metin: kupa-orchard dali kupa_orchard/ilan/KUPA78_ORCHARD_METIN_RU.csv (a8cb552; ChatGPT cevirisi, Claude kontrolu).
Ilan listesi: Drive TEMP/KUPA_ORCHARD_TASLAK_20261019/KUPA_TASLAK_LISTE.csv (cift -> listing_id).

Kuru (varsayilan): her ilan icin salt okuma: state, bolum, mevcut RU. Yazilacak metnin kontrolu (baslik <= 140,
  13 tekrarsiz etiket <= 20, uzun/orta tire yok, yer tutucu yok). Etsy'ye YAZMAZ.
--apply: YALNIZ state == active ilana PUT /shops/{shop}/listings/{id}/translations/ru (baslik, aciklama, 13 etiket;
  etiketler virgullu TEK metin, B95 dersi). Taslak/baska state ilana YAZILMAZ (updateListing taslagi yayina alir dersi;
  translation PUT'un taslaktaki etkisi olculmedi). Yazim sonrasi geri okuma: baslik, aciklama (html.unescape),
  etiketler birebir + state hala active. Kota x-remaining-today < quota_min ise DUR. Ayni RU zaten birebir varsa ATLA.
Cikti: OUT/KUPA_RU.json, OUT/KUPA_RU.csv (cift, listing_id, state, bolum, ru_once, durum, not).
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

BOLUM_ID = 60980873  # "Zodiac Couple Mugs"
TIRE = re.compile("[–—]")


def metin_kontrol(r):
    tags = [t.strip() for t in r["etiketler"].split(",")]
    sorun = []
    if len(r["baslik"]) > 140:
        sorun.append(f"baslik {len(r['baslik'])} > 140")
    if len(tags) != 13 or len(set(tags)) != 13 or any(len(t) > 20 or not t for t in tags):
        sorun.append(f"etiket {tags}")
    tum = r["baslik"] + r["aciklama"] + " ".join(tags)
    if TIRE.search(tum):
        sorun.append("uzun/orta tire")
    if re.search(r"[{}]", tum):
        sorun.append("yer tutucu")
    if re.search(r"lena|serdar", tum, re.I):
        sorun.append("kisi adi")
    return tags, sorun


def norm(s):
    return html.unescape(s or "").replace("\r\n", "\n").strip()


def ayni(ru, r, tags):
    return (norm(ru.get("title")) == r["baslik"].strip() and norm(ru.get("description")) == r["aciklama"].strip()
            and [norm(t) for t in (ru.get("tags") or [])] == tags)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", required=True)
    ap.add_argument("--ru-csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--quota-min", type=int, default=10)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    ru = {r["kod"]: r for r in csv.DictReader(open(a.ru_csv, encoding="utf-8"))}
    ilan = [(r["cift"], int(r["listing_id"])) for r in csv.DictReader(open(a.liste, encoding="utf-8")) if r.get("listing_id")]
    if len(ru) != 78 or len(ilan) != 78 or sorted(c for c, _ in ilan) != sorted(ru):
        raise SystemExit(f"DUR: liste {len(ilan)} / RU {len(ru)} eslesmiyor")

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]

    satir, t0 = [], time.time()

    def kaydet():
        json.dump({"apply": a.apply, "kota": api.remaining, "cagri": api.calls, "satir": satir},
                  open(out / "KUPA_RU.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        with open(out / "KUPA_RU.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["cift", "listing_id", "state", "bolum", "ru_once", "durum", "not"])
            w.writeheader(); w.writerows(satir)

    for i, (cift, lid) in enumerate(sorted(ilan), 1):
        if api.remaining is not None and int(api.remaining) < a.quota_min:
            kaydet(); raise SystemExit(f"DUR: kota {api.remaining} < {a.quota_min}")
        r = ru[cift]
        tags, sorun = metin_kontrol(r)
        L = api.get(f"/listings/{lid}") or {}
        st, bolum = L.get("state"), L.get("shop_section_id")
        mevcut = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
        ru_once = "AYNI" if mevcut and ayni(mevcut, r, tags) else ("FARKLI" if norm(mevcut.get("title")) else "BOS")
        notu = []
        if bolum != BOLUM_ID:
            notu.append(f"bolum {bolum}")
        if sorun:
            durum = "FAIL"; notu += sorun
        elif st != "active":
            durum = "ATLA (aktif degil)"
        elif ru_once == "AYNI":
            durum = "TAMAM (zaten var)"
        elif not a.apply:
            durum = "HAZIR"
        else:
            back = api.put(f"/shops/{shop}/listings/{lid}/translations/ru",
                           {"title": r["baslik"], "description": r["aciklama"], "tags": ",".join(tags)})
            ok = False
            for d in range(3):  # yazim sonrasi tek okuma bayat olabilir (B68): 10 sn arayla 3 deneme
                if not (isinstance(back, dict) and back.get("description")) or d:
                    time.sleep(10 if d else 0)
                    back = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
                if ayni(back, r, tags):
                    ok = True; break
            st2 = (api.get(f"/listings/{lid}") or {}).get("state")
            if st2 != "active":
                notu.append(f"state {st2} oldu")
                ok = False
            durum = "PASS" if ok else "FAIL"
            if not ok and "geri okuma" not in " ".join(notu):
                notu.append("geri okuma farkli")
        satir.append({"cift": cift, "listing_id": lid, "state": st, "bolum": bolum, "ru_once": ru_once,
                      "durum": durum, "not": "; ".join(notu)})
        g = time.time() - t0
        log(f"[{i}/78 %{100 * i // 78}] {cift} {lid} {st} RU {ru_once} -> {durum} | kota {api.remaining} "
            f"(gecen {g:.0f}s, kalan ~{g / i * (78 - i):.0f}s)")
        kaydet()
        if durum == "FAIL" and a.apply and sum(x["durum"] == "FAIL" for x in satir[-2:]) == 2:
            raise SystemExit("DUR: ust uste 2 FAIL")

    say = {}
    for x in satir:
        say[x["durum"]] = say.get(x["durum"], 0) + 1
    st_say = {}
    for x in satir:
        st_say[x["state"]] = st_say.get(x["state"], 0) + 1
    log(f"OZET state {st_say} | durum {say} | bolum disi {sum(x['bolum'] != BOLUM_ID for x in satir)} | "
        f"kota {api.remaining} | cagri {api.calls}")
    sys.exit(1 if say.get("FAIL") else 0)


if __name__ == "__main__":
    main()
