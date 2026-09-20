#!/usr/bin/env python3
"""Buyuk boy adaylari (HPR Photo Rag) — SALT OKUMA, siparis yok.

Adaylar: 4:5 -> 20x25, 24x30 | A serisi -> A1, A0 | 11:14 -> 16x20.5, 22x28.
Her aday icin: GLOBAL-HPR SKU var mi, birim maliyet, ABD/Ingiltere en ucuz kargo,
baski alani px, usta dosyasindan gercek DPI, mevcut boylarin fiyat kuralindan
onerilen fiyat, Etsy ucretleri sonrasi kar ve Offsite Ads (%15) sonrasi kar.
Cikti: BUYUK_BOY.csv + FIYAT_KURALI.json -> gdrive:ASTROLOVE/TEMP/POD_5X7/
"""
import argparse
import csv
import json
import math
import pathlib
import subprocess
import sys
import time

import requests
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
from prodigi_pilot_quote import Api, load_key, process  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
DRV = "gdrive:ASTROLOVE/TEMP/POD_5X7"
USTA = "gdrive:ASTROLOVE/WALL_ART/POSTERS/ORIGINAL_HIGH_RES/MIDNIGHT_BLUE"
# aday: (etiket, oran grubu, usta orani, en_in, boy_in)
ADAYLAR = [("20x25", "4:5", "4X5", 20, 25), ("24x30", "4:5", "4X5", 24, 30),
           ("A1", "A", "A_SERIES", 23.4, 33.1), ("A0", "A", "A_SERIES", 33.1, 46.8),
           ("16x20.5", "11:14", "11X14", 16, 20.5), ("22x28", "11:14", "11X14", 22, 28)]
MEVCUT = ["8x10", "11x14", "12x16", "12x18", "16x20", "16x24", "18x24", "20x30", "24x36",
          "30x40", "A4", "A3", "A2"]
KARGO_SUT = ["kargo_budget", "kargo_standard", "kargo_standardplus", "kargo_express", "kargo_overnight"]
ISLEM, ODEME_YUZDE, ODEME_SABIT_TRY = 0.065, 0.065, 14.0
DUZENLEYICI, DOVIZ, ILAN, OFFSITE = 0.0167, 0.025, 0.20, 0.15
SUT = ["boy", "oran", "sku", "sku_var", "urun_adi", "boyut", "baski_alani_px", "usta_px",
       "gercek_dpi", "dpi_yeterli", "birim_usd", "kargo_us_en_ucuz", "kargo_us_yontem",
       "kargo_gb_en_ucuz", "kargo_gb_yontem", "lab_us", "lab_gb", "maliyet_us",
       "onerilen_fiyat", "etsy_ucret", "kar", "kar_yuzde", "kar_offsite", "notlar"]
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise RuntimeError(f"rclone {a[0]}: {r.stderr.strip()[-200:]}")
    return r


def sayi(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def kur_usdtry():
    for url in ("https://api.frankfurter.app/latest?from=USD&to=TRY",
                "https://open.er-api.com/v6/latest/USD"):
        try:
            return float(requests.get(url, timeout=20).json()["rates"]["TRY"]), url
        except Exception:  # noqa: BLE001
            continue
    return None, ""


def en_ucuz(row, sutunlar=KARGO_SUT):
    k = {s: sayi(row.get(s)) for s in sutunlar if sayi(row.get(s)) is not None}
    if not k:
        return None, ""
    ad, v = min(k.items(), key=lambda kv: kv[1])
    return v, ad.replace("kargo_", "")


def gb_teklif(api, sku, attrs):
    """Ingiltere teklifi: (en ucuz kargo, yontem, lab)."""
    q, err = api.quote(sku, attrs, dest="GB")
    if q is None:
        return None, "", f"GB teklif yok: {err[:80]}"
    en, ad, lab = None, "", []
    for qu in q.get("quotes") or []:
        s = sayi(((qu.get("costSummary") or {}).get("shipping") or {}).get("amount"))
        m = (qu.get("shipmentMethod") or "").lower()
        if s is not None and (en is None or s < en):
            en, ad = s, m
        for sh in qu.get("shipments") or []:
            fl = sh.get("fulfillmentLocation") or {}
            t = f"{fl.get('countryCode','')}/{fl.get('labCode','')}"
            if t not in lab:
                lab.append(t)
    return en, ad, ", ".join(lab)


def usta_px(isd, oran):
    """Usta dosyasinin piksel olcusu (cift: ARIES_LEO, edisyon MB)."""
    y = isd / f"usta_{oran}.jpg"
    if not y.exists():
        r = rclone("copyto", f"{USTA}/{oran}/ARIES_LEO.jpg", str(y), sert=False)
        if r.returncode != 0:
            return None
    with Image.open(y) as im:
        return im.size


def fiyat_kurali(api, ham, isd):
    """Mevcut 13 boydan olcum: fiyat / (birim + en ucuz ABD kargo) orani."""
    fiyatlar = {}
    yol = isd / "pod_prices.csv"
    if not yol.exists():
        yol = KOK.parent / "etsy" / "pod_prices.csv"
    for r in csv.DictReader(yol.open(encoding="utf-8")):
        fiyatlar[r["size"]] = float(r["price"])
    fiyatlar["8x10"] = 29.99            # 20 Eyl: 30.99 -> 29.99 (canli)
    oranlar, satir = [], []
    for i, boy in enumerate(MEVCUT, start=1):
        sku = f"GLOBAL-HPR-{boy}"
        row, durum = process(api, {"sinif": "poster", "sku": sku, "not": ""}, ham)
        birim = sayi(row.get("birim_fiyat"))
        kargo, yontem = en_ucuz(row)
        if durum != "ok" or birim is None or kargo is None:
            continue
        maliyet = birim + kargo
        oranlar.append(fiyatlar[boy] / maliyet)
        satir.append({"boy": boy, "birim": birim, "kargo": kargo, "maliyet": round(maliyet, 2),
                      "fiyat": fiyatlar[boy], "oran": round(fiyatlar[boy] / maliyet, 4)})
        log(f"kural {i}/{len(MEVCUT)} {boy}: maliyet {maliyet:.2f} fiyat {fiyatlar[boy]} "
            f"oran {fiyatlar[boy] / maliyet:.3f}")
    ort = sum(oranlar) / len(oranlar)
    return {"oran_ort": round(ort, 4), "oran_min": round(min(oranlar), 4),
            "oran_max": round(max(oranlar), 4), "satirlar": satir}


def x99(x):
    """En yakin ust .99 fiyat."""
    return math.floor(x) + 0.99 if x - math.floor(x) <= 0.99 else math.floor(x) + 1.99


def ucret(fiyat, kur):
    sabit = None if kur is None else ODEME_SABIT_TRY / kur
    t = fiyat * (ISLEM + ODEME_YUZDE + DUZENLEYICI + DOVIZ) + ILAN + (sabit or 0)
    return round(t, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is-dizin", default="_work/buyuk")
    ap.add_argument("--no-drive", action="store_true")
    a = ap.parse_args()
    isd = pathlib.Path(a.is_dizin)
    ham = isd / "ham"
    ham.mkdir(parents=True, exist_ok=True)
    api = Api(load_key())
    kur, kur_kaynak = kur_usdtry()
    log(f"USD/TRY {kur} ({kur_kaynak or 'yok'})")

    kural = fiyat_kurali(api, ham, isd)
    log(f"fiyat kurali: fiyat ~ {kural['oran_ort']} x (birim + ABD kargo) "
        f"[min {kural['oran_min']} max {kural['oran_max']}]")
    (isd / "FIYAT_KURALI.json").write_text(json.dumps(kural, ensure_ascii=False, indent=1),
                                           encoding="utf-8")

    ustalar = {}
    satirlar = []
    for i, (boy, oran, usta_oran, w_in, h_in) in enumerate(ADAYLAR, start=1):
        sku = f"GLOBAL-HPR-{boy}"
        row, durum = process(api, {"sinif": "poster", "sku": sku, "not": ""}, ham)
        s = {k: "" for k in SUT}
        s.update({"boy": boy, "oran": oran, "sku": sku, "sku_var": "EVET" if durum == "ok" else "HAYIR"})
        if usta_oran not in ustalar:
            ustalar[usta_oran] = usta_px(isd, usta_oran)
        up = ustalar.get(usta_oran)
        if up:
            s["usta_px"] = f"{up[0]}x{up[1]}"
            dpi = round(max(up) / max(w_in, h_in))
            s["gercek_dpi"] = dpi
            s["dpi_yeterli"] = "EVET" if dpi >= 300 else "HAYIR"
        if durum != "ok":
            s["notlar"] = (row.get("notlar") or "")[:120]
            satirlar.append(s)
            log(f"{i}/{len(ADAYLAR)} {boy}: SKU YOK ({s['notlar'][:60]})")
            continue
        birim = sayi(row.get("birim_fiyat"))
        us_kargo, us_yontem = en_ucuz(row)
        pa = None
        pj = ham / f"{sku}.product.json"
        if pj.exists():
            d = json.loads(pj.read_text())
            for v in d.get("variants") or []:
                p = (v.get("printAreaSizes") or {}).get("default") or {}
                if p.get("horizontalResolution"):
                    pa = (int(p["horizontalResolution"]), int(p["verticalResolution"]))
                    break
        attrs = {}
        if pj.exists():
            d = json.loads(pj.read_text())
            var = (d.get("variants") or [{}])[0]
            attrs = dict(var.get("attributes") or {})
        gb_kargo, gb_yontem, gb_lab = gb_teklif(api, sku, attrs)
        maliyet = (birim or 0) + (us_kargo or 0)
        fiyat = x99(kural["oran_ort"] * maliyet)
        u = ucret(fiyat, kur)
        kar = round(fiyat - u - maliyet, 2)
        s.update({"urun_adi": row.get("urun_adi", "")[:70], "boyut": row.get("boyut"),
                  "baski_alani_px": f"{pa[0]}x{pa[1]}" if pa else "",
                  "birim_usd": birim, "kargo_us_en_ucuz": us_kargo, "kargo_us_yontem": us_yontem,
                  "kargo_gb_en_ucuz": gb_kargo if gb_kargo is not None else "",
                  "kargo_gb_yontem": gb_yontem, "lab_us": row.get("uretim_ulkesi_lab"),
                  "lab_gb": gb_lab, "maliyet_us": round(maliyet, 2), "onerilen_fiyat": fiyat,
                  "etsy_ucret": u, "kar": kar, "kar_yuzde": round(100 * kar / fiyat, 1),
                  "kar_offsite": round(kar - fiyat * OFFSITE, 2),
                  "notlar": (row.get("notlar") or "")[:120]})
        satirlar.append(s)
        log(f"{i}/{len(ADAYLAR)} {boy}: birim {birim} US kargo {us_kargo} GB kargo {gb_kargo} "
            f"dpi {s['gercek_dpi']} fiyat {fiyat} kar {kar}")

    yol = isd / "BUYUK_BOY.csv"
    with yol.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUT, extrasaction="ignore")
        w.writeheader()
        w.writerows(satirlar)
    if not a.no_drive:
        rclone("copyto", str(yol), f"{DRV}/BUYUK_BOY.csv")
        rclone("copyto", str(isd / "FIYAT_KURALI.json"), f"{DRV}/FIYAT_KURALI.json")
    print(json.dumps({"kur": kur, "kural": kural["oran_ort"],
                      "adaylar": [{k: s[k] for k in ("boy", "sku_var", "birim_usd", "kargo_us_en_ucuz",
                                                     "kargo_gb_en_ucuz", "gercek_dpi", "onerilen_fiyat",
                                                     "kar", "kar_offsite")} for s in satirlar]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
