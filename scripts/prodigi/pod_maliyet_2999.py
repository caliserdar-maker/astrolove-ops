#!/usr/bin/env python3
"""POD 8x10 maliyet tablosu (SALT OKUMA; siparis verilmez).

Prodigi'den US/USD teklifi alinir (birim fiyat + kargo), 29.99 / 18.99 / 16.99
satis fiyatlari icin kar tablosu yazilir. Tahmin yok: yalniz API'den donen
degerler. Cikti: MALIYET.csv -> gdrive:ASTROLOVE/TEMP/POD_FIYAT_2999/
"""
import argparse
import csv
import json
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
from prodigi_pilot_quote import Api, load_key, process  # noqa: E402

DRV = "gdrive:ASTROLOVE/TEMP/POD_FIYAT_2999"
# en kucuk boyut adaylari + onayli 8x10 Enhanced Matte (EMA)
ADAYLAR = [{"sinif": "poster", "sku": "GLOBAL-FAP-5x7", "not": "EMA 5x7 adayi"},
           {"sinif": "poster", "sku": "GLOBAL-BLP-5x7", "not": "Budget 5x7 adayi"},
           {"sinif": "poster", "sku": "GLOBAL-FAP-8x10", "not": "EMA 8x10 (onayli)"},
           {"sinif": "poster", "sku": "GLOBAL-BLP-8x10", "not": "Budget 8x10"}]
SATIS = [29.99, 18.99, 16.99]
KARGO = ["kargo_budget", "kargo_standard", "kargo_standardplus", "kargo_express", "kargo_overnight"]
SUTUN = (["sku", "urun_adi", "boyut", "birim_fiyat", "para_birimi"] + KARGO
         + ["en_ucuz_kargo", "en_ucuz_kargo_toplam", "uretim_ulkesi_lab", "durum", "notlar"]
         + [f"kar_{s:.2f}" for s in SATIS] + [f"kar_{s:.2f}_etsy_sonrasi" for s in SATIS])


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="_work/maliyet")
    ap.add_argument("--no-drive", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out_dir)
    (out / "ham").mkdir(parents=True, exist_ok=True)
    api = Api(load_key())
    satirlar = []
    for cand in ADAYLAR:
        row, durum = process(api, cand, out / "ham")
        s = {k: row.get(k, "") for k in SUTUN if k in row}
        s.update({"sku": cand["sku"], "durum": durum})
        birim = f(row.get("birim_fiyat"))
        kargolar = {k: f(row.get(k)) for k in KARGO if f(row.get(k)) is not None}
        if kargolar:
            ad, en_ucuz = min(kargolar.items(), key=lambda kv: kv[1])
            s["en_ucuz_kargo"] = ad.replace("kargo_", "")
            s["en_ucuz_kargo_toplam"] = round((birim or 0) + en_ucuz, 2)
        for st in SATIS:
            if birim is not None and kargolar:
                toplam = (birim or 0) + min(kargolar.values())
                s[f"kar_{st:.2f}"] = round(st - toplam, 2)
                # Etsy: %6.5 islem + 0.20 listeleme (yayimlanmis oranlar, olcum degil)
                s[f"kar_{st:.2f}_etsy_sonrasi"] = round(st - toplam - st * 0.065 - 0.20, 2)
        satirlar.append(s)
        print(json.dumps({"sku": cand["sku"], "durum": durum,
                          "birim": row.get("birim_fiyat"),
                          "kargo": {k.replace('kargo_', ''): row.get(k) for k in KARGO if row.get(k)}},
                         ensure_ascii=False), flush=True)
    yol = out / "MALIYET.csv"
    with yol.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        for s in satirlar:
            w.writerow(s)
    if not a.no_drive:
        r = subprocess.run(["rclone", "copyto", str(yol), f"{DRV}/MALIYET.csv"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit("HATA: MALIYET.csv Drive'a yuklenemedi")
    print(f"MALIYET.csv yazildi: {yol}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
