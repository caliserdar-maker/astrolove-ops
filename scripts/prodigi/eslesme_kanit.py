#!/usr/bin/env python3
"""KANIT: 20 Eyl fiyat kosusu Etsy product/offering kimliklerini yeniledi mi?

Salt okuma. YEDEK (yazma oncesi envanter, POD_FIYAT_2999/YEDEK/<lid>.json) ile CANLI envanteri
karsilastirir: product_id ve offering_id kumeleri, SKU -> product_id haritasi. Ayrica Prodigi
API'den son siparisleri listeler (eslesme sorunlu olanlar isaretlenir).

Cikti: Drive TEMP/POD_5X7/ESLESME_KANIT.csv + ESLESME_KANIT.json
Ortam: ETSY_API_KEY/ETSY_SHOP_ID/TOKEN_FILE, rclone (Drive), Prodigi anahtari.
"""
import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore  # noqa: E402
from order_router import Prodigi, load_prodigi_key  # noqa: E402

DRV = "gdrive:ASTROLOVE/TEMP/POD_5X7"
YEDEK = "gdrive:ASTROLOVE/TEMP/POD_FIYAT_2999/YEDEK"
SUT = ["listing_id", "urun_once", "urun_simdi", "product_id_ayni", "product_id_degisen",
       "offering_id_ayni", "offering_id_degisen", "sku_ayni", "sku_pid_degisen", "not"]
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise SystemExit(f"HATA: rclone {a[0]}: {r.stderr.strip()[-200:]}")
    return r


def kimlikler(inv):
    """(product_id kumesi, offering_id kumesi, sku -> product_id)."""
    pid, oid, sku = set(), set(), {}
    for pr in inv.get("products") or []:
        p = pr.get("product_id")
        if p is not None:
            pid.add(p)
            if pr.get("sku"):
                sku[pr["sku"]] = p
        for o in pr.get("offerings") or []:
            if o.get("offering_id") is not None:
                oid.add(o["offering_id"])
    return pid, oid, sku


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is-dizin", default="_work/kanit")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--kota-alt", type=int, default=150)
    ap.add_argument("--siparis-adet", type=int, default=20)
    a = ap.parse_args()
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)

    yd = isd / "yedek"
    yd.mkdir(exist_ok=True)
    rclone("copy", YEDEK, str(yd), "--include", "*.json", "-q")
    dosyalar = sorted(yd.glob("*.json"))
    if a.limit:
        dosyalar = dosyalar[:a.limit]
    log(f"yedek envanter dosyasi: {len(dosyalar)}")

    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    shop = os.environ["ETSY_SHOP_ID"]
    api.get(f"/shops/{shop}", ok404=True)
    kota0 = api.remaining
    log(f"kota (once): {kota0}")

    satirlar, ozet = [], {"ilan": 0, "pid_hepsi_degisti": 0, "pid_kismen": 0, "pid_ayni": 0,
                          "oid_hepsi_degisti": 0, "sku_korundu": 0}
    for i, p in enumerate(dosyalar, 1):
        lid = p.stem
        try:
            eski = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            satirlar.append({"listing_id": lid, "not": "yedek okunamadi"})
            continue
        eski_inv = eski.get("inventory") or eski.get("envanter") or eski
        simdi = api.get(f"/listings/{lid}/inventory") or {}
        e_pid, e_oid, e_sku = kimlikler(eski_inv)
        s_pid, s_oid, s_sku = kimlikler(simdi)
        ortak_sku = set(e_sku) & set(s_sku)
        sku_pid_degisen = sum(1 for k in ortak_sku if e_sku[k] != s_sku[k])
        satir = {"listing_id": lid, "urun_once": len(e_pid), "urun_simdi": len(s_pid),
                 "product_id_ayni": len(e_pid & s_pid), "product_id_degisen": len(e_pid - s_pid),
                 "offering_id_ayni": len(e_oid & s_oid), "offering_id_degisen": len(e_oid - s_oid),
                 "sku_ayni": len(ortak_sku), "sku_pid_degisen": sku_pid_degisen, "not": ""}
        satirlar.append(satir)
        ozet["ilan"] += 1
        if e_pid and not (e_pid & s_pid):
            ozet["pid_hepsi_degisti"] += 1
        elif e_pid & s_pid and (e_pid - s_pid):
            ozet["pid_kismen"] += 1
        elif e_pid and e_pid == s_pid:
            ozet["pid_ayni"] += 1
        if e_oid and not (e_oid & s_oid):
            ozet["oid_hepsi_degisti"] += 1
        if ortak_sku and len(ortak_sku) == len(e_sku):
            ozet["sku_korundu"] += 1
        if i % 10 == 0 or i == len(dosyalar):
            gec = time.time() - T0
            log(f"{i}/{len(dosyalar)} (%{100 * i / len(dosyalar):.0f}) kota {api.remaining} | "
                f"gecen {gec:.0f}sn | kalan ~{gec / i * (len(dosyalar) - i):.0f}sn")
        if api.remaining is not None and int(api.remaining) < a.kota_alt:
            log(f"DUR: kota {api.remaining} < {a.kota_alt}")
            break

    # ---------------------------------------------------------- Prodigi son siparisler
    prod = Prodigi(load_prodigi_key("live"), "live")
    stt, d = prod.call("GET", f"/orders?top={a.siparis_adet}")
    siparisler = []
    if stt == 200:
        for o in (d.get("orders") or []):
            durum = o.get("status") or {}
            kalemler = o.get("items") or []
            siparisler.append({
                "id": o.get("id"), "created": o.get("created"),
                "merchantReference": o.get("merchantReference"),
                "stage": durum.get("stage"), "issues": durum.get("issues"),
                "details": durum.get("details"),
                "kalem": [{"sku": k.get("sku"), "merchantReference": k.get("merchantReference"),
                           "assets": [{"printArea": x.get("printArea"), "status": x.get("status"),
                                       "url_var": bool(x.get("url"))} for x in (k.get("assets") or [])]}
                          for k in kalemler]})
        log(f"Prodigi son {len(siparisler)} siparis okundu")
    else:
        log(f"Prodigi siparis listesi HTTP {stt}: {json.dumps(d)[:200]}")

    sorunlu = [s for s in siparisler if s.get("issues")]
    eksik_asset = [s for s in siparisler
                   if any(not x["url_var"] for k in s["kalem"] for x in k["assets"])]
    log(f"ozet: {ozet} | sorunlu siparis {len(sorunlu)}/{len(siparisler)} | "
        f"asset'i eksik {len(eksik_asset)}")

    c = isd / "ESLESME_KANIT.csv"
    with c.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUT, extrasaction="ignore")
        w.writeheader()
        w.writerows(satirlar)
    j = isd / "ESLESME_KANIT.json"
    j.write_text(json.dumps({"ozet": ozet, "kota_once": kota0, "kota_sonra": api.remaining,
                             "siparisler": siparisler, "zaman_utc": time.strftime(
                                 "%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                            ensure_ascii=False, indent=1), encoding="utf-8")
    rclone("copyto", str(c), f"{DRV}/ESLESME_KANIT.csv")
    rclone("copyto", str(j), f"{DRV}/ESLESME_KANIT.json")
    log(f"yazildi: {DRV}/ESLESME_KANIT.csv + .json | kota (sonra) {api.remaining}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
