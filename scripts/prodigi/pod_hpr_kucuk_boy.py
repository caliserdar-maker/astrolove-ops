#!/usr/bin/env python3
"""HPR (Hahnemuhle Photo Rag 308gsm) kucuk boy karari — SALT OKUMA.

1) Prodigi: mevcut 13 boy + adaylar (4x6, 5x7, 6x8) icin urun dogrulama,
   birim fiyat, en ucuz ABD kargo, baski alani pikselleri.
2) Etsy ucret modeliyle kar tablosu (MALIYET_HPR.csv).
3) Aries+Leo MB ustalarindan 3 aday boy onizlemesi (ORNEK_KUCUK.jpg) ve
   dosya eslemesi/kirpma hesabi (PLAN_KUCUK.json).
Etsy'ye hicbir cagri yapilmaz. Cikti: gdrive:ASTROLOVE/TEMP/POD_5X7/
"""
import argparse
import csv
import json
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone

import requests
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
from prodigi_pilot_quote import Api, load_key, process  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
DRV = "gdrive:ASTROLOVE/TEMP/POD_5X7"
USTA_KOK = ["gdrive:ASTROLOVE/WALL_ART/POSTERS/ORIGINAL_HIGH_RES",
            "gdrive:ASTROLOVE/POSTERS/ORIGINAL_HIGH_RES",
            "gdrive:ASTROLOVE/WALL_ART/ORIGINAL_HIGH_RES"]
MEVCUT = ["8x10", "11x14", "12x16", "12x18", "16x20", "16x24", "18x24",
          "20x30", "24x36", "30x40", "A4", "A3", "A2"]
ADAY = ["4x6", "5x7", "6x8"]
# aday -> (kullanilacak usta orani, hedef en/boy)
ADAY_USTA = {"4x6": ("2X3", 4, 6), "5x7": ("A_SERIES", 5, 7), "6x8": ("3X4", 6, 8)}
FIYAT = {"4x6": [16.99, 17.99, 18.99], "5x7": [18.99, 19.99, 21.99],
         "6x8": [23.99, 24.99, 25.99], "8x10": [29.99, 30.99]}
# Etsy ucretleri (Mo 20 Eyl 2026 tanimi)
ISLEM, ODEME_YUZDE, ODEME_SABIT_TRY = 0.065, 0.065, 14.0
DUZENLEYICI, DOVIZ, ILAN, OFFSITE = 0.0167, 0.025, 0.20, 0.15
KARGO_SUT = ["kargo_budget", "kargo_standard", "kargo_standardplus", "kargo_express", "kargo_overnight"]
T0 = time.time()


def ilerle(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def rclone(*a):
    return subprocess.run(["rclone", *a], capture_output=True, text=True)


def yukle(yerel, uzak):
    if rclone("copyto", str(yerel), f"{DRV}/{uzak}").returncode != 0:
        raise SystemExit(f"HATA: Drive'a yuklenemedi: {uzak}")


def sayi(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def kur_usdtry():
    """USD/TRY kuru (olculen; alinamazsa None)."""
    for url, yol in (("https://api.frankfurter.app/latest?from=USD&to=TRY", ("rates", "TRY")),
                     ("https://open.er-api.com/v6/latest/USD", ("rates", "TRY"))):
        try:
            d = requests.get(url, timeout=20).json()
            v = d
            for k in yol:
                v = v[k]
            if v:
                return float(v), url
        except Exception as e:  # noqa: BLE001
            ilerle(f"  kur alinamadi ({url}): {type(e).__name__}")
    return None, ""


def ucretler(fiyat, kur):
    """Etsy ucret kalemleri (USD). kur None ise odeme sabiti None kalir."""
    sabit = None if kur is None else ODEME_SABIT_TRY / kur
    kalem = {"islem": round(fiyat * ISLEM, 2),
             "odeme_yuzde": round(fiyat * ODEME_YUZDE, 2),
             "odeme_sabit": None if sabit is None else round(sabit, 2),
             "duzenleyici": round(fiyat * DUZENLEYICI, 2),
             "doviz": round(fiyat * DOVIZ, 2),
             "ilan": ILAN}
    toplam = sum(v for v in kalem.values() if v is not None)
    kalem["toplam"] = round(toplam, 2)
    return kalem


def prodigi_tablo(api, ham):
    """SKU -> process() satiri; 13 mevcut + 3 aday."""
    satirlar = {}
    skular = [f"GLOBAL-HPR-{s}" for s in MEVCUT + ADAY]
    for i, sku in enumerate(skular, start=1):
        row, durum = process(api, {"sinif": "poster", "sku": sku, "not": ""}, ham)
        if durum != "ok":
            row2, durum2 = process(api, {"sinif": "poster", "sku": sku.upper(), "not": ""}, ham)
            if durum2 == "ok":
                row, durum = row2, durum2
        row["durum"] = durum
        satirlar[sku] = row
        ilerle(f"{i}/{len(skular)} (%{100 * i / len(skular):.0f}) {sku} {durum} "
               f"birim {row.get('birim_fiyat')} kargo_b {row.get('kargo_budget')}")
    return satirlar


def en_ucuz_kargo(row):
    k = {s: sayi(row.get(s)) for s in KARGO_SUT if sayi(row.get(s)) is not None}
    if not k:
        return None, None
    ad, v = min(k.items(), key=lambda kv: kv[1])
    return ad.replace("kargo_", ""), v


def baski_alani(ham, sku):
    """Urun JSON'undan default baski alani (w_px, h_px)."""
    y = ham / f"{sku}.product.json"
    if not y.exists():
        return None
    d = json.loads(y.read_text())
    for v in d.get("variants") or []:
        pas = (v.get("printAreaSizes") or {}).get("default") or {}
        if pas.get("horizontalResolution"):
            return int(pas["horizontalResolution"]), int(pas["verticalResolution"])
    return None


def usta_kok_bul():
    for kok in USTA_KOK:
        r = rclone("lsjson", f"{kok}/MIDNIGHT_BLUE", "--dirs-only")
        if r.returncode == 0 and r.stdout.strip() not in ("", "[]"):
            return kok
    return None


def onizleme(isd, kok, hedefler):
    """Aries+Leo MB: 3 aday boy yan yana, gercek fiziksel oran (100 px/inc)."""
    olcek, bosluk, kenar = 100, 60, 40
    paneller, bilgi = [], {}
    for boy in ADAY:
        oran, w_in, h_in = ADAY_USTA[boy]
        yerel = isd / f"usta_{oran}.jpg"
        if not yerel.exists():
            r = rclone("copyto", f"{kok}/MIDNIGHT_BLUE/{oran}/ARIES_LEO.jpg", str(yerel))
            if r.returncode != 0:
                raise SystemExit(f"HATA: usta inmedi: {oran} ({r.stderr.strip()[-160:]})")
        im = Image.open(yerel).convert("RGB")
        sw, sh = im.size
        hedef_oran = w_in / h_in
        if sw / sh > hedef_oran:
            nw = round(sh * hedef_oran); x0 = (sw - nw) // 2
            kirp = im.crop((x0, 0, x0 + nw, sh)); kirpma = f"yatayda {sw - nw} px (her kenar {(sw - nw) // 2})"
        else:
            nh = round(sw / hedef_oran); y0 = (sh - nh) // 2
            kirp = im.crop((0, y0, sw, y0 + nh)); kirpma = f"dikeyde {sh - nh} px (her kenar {(sh - nh) // 2})"
        bilgi[boy] = {"usta_orani": oran, "usta_px": [sw, sh],
                      "usta_oran_degeri": round(sw / sh, 4), "hedef_oran": round(hedef_oran, 4),
                      "oran_farki_yuzde": round(abs((sw / sh) / hedef_oran - 1) * 100, 2),
                      "kirpma": kirpma, "kirp_sonrasi_px": list(kirp.size)}
        paneller.append((boy, kirp.resize((w_in * olcek, h_in * olcek), Image.LANCZOS)))
        hedefler.setdefault(boy, {})["usta"] = bilgi[boy]
    gen = kenar * 2 + sum(p.size[0] for _, p in paneller) + bosluk * (len(paneller) - 1)
    yuk = kenar * 2 + max(p.size[1] for _, p in paneller) + 46
    tuval = Image.new("RGB", (gen, yuk), (245, 244, 241))
    x = kenar
    from PIL import ImageDraw
    ciz = ImageDraw.Draw(tuval)
    for boy, p in paneller:
        y = kenar + (max(q.size[1] for _, q in paneller) - p.size[1])
        tuval.paste(p, (x, y))
        ciz.rectangle([x, y, x + p.size[0] - 1, y + p.size[1] - 1], outline=(120, 120, 120))
        ciz.text((x, kenar + max(q.size[1] for _, q in paneller) + 14),
                 f'{boy} in  ({ADAY_USTA[boy][0]} ustasi)', fill=(30, 30, 30))
        x += p.size[0] + bosluk
    yol = isd / "ORNEK_KUCUK.jpg"
    for q in (88, 82, 74, 66):
        tuval.save(yol, "JPEG", quality=q, optimize=True)
        if yol.stat().st_size <= 1_000_000:
            break
    ilerle(f"ORNEK_KUCUK.jpg {tuval.size[0]}x{tuval.size[1]} {yol.stat().st_size / 1024:.0f} KB")
    return yol, bilgi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is-dizin", default="_work/hpr")
    ap.add_argument("--no-drive", action="store_true")
    a = ap.parse_args()
    isd = pathlib.Path(a.is_dizin)
    ham = isd / "ham"
    ham.mkdir(parents=True, exist_ok=True)

    api = Api(load_key())
    ilerle("Prodigi urun + teklif okumasi basladi (16 SKU)")
    satirlar = prodigi_tablo(api, ham)
    kur, kur_kaynak = kur_usdtry()
    ilerle(f"USD/TRY {kur} ({kur_kaynak or 'yok'})")

    # --- SKU teyit tablosu
    teyit = isd / "SKU_TEYIT.csv"
    with teyit.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sku", "durum", "boyut", "baski_alani_px", "dpi", "birim_fiyat",
                    "en_ucuz_kargo", "en_ucuz_kargo_usd", "lab", "notlar"])
        for sku, row in satirlar.items():
            ad, v = en_ucuz_kargo(row)
            pa = baski_alani(ham, sku)
            w.writerow([sku, row.get("durum"), row.get("boyut"),
                        f"{pa[0]}x{pa[1]}" if pa else "", row.get("dpi"),
                        row.get("birim_fiyat"), ad or "", v if v is not None else "",
                        row.get("uretim_ulkesi_lab"), (row.get("notlar") or "")[:120]])

    # --- kar tablosu
    maliyet = isd / "MALIYET_HPR.csv"
    sut = ["boy", "sku", "prodigi_birim", "prodigi_kargo", "prodigi_toplam", "fiyat",
           "etsy_islem", "etsy_odeme_yuzde", "etsy_odeme_sabit", "etsy_duzenleyici",
           "etsy_doviz", "etsy_ilan", "etsy_ucret_toplam", "kar", "kar_yuzde",
           "kar_offsite_ads", "kar_offsite_yuzde", "kur_usdtry", "kur_kaynak"]
    ozet = []
    with maliyet.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sut, extrasaction="ignore")
        w.writeheader()
        for boy in ADAY + ["8x10"]:
            sku = f"GLOBAL-HPR-{boy}"
            row = satirlar.get(sku, {})
            birim = sayi(row.get("birim_fiyat"))
            _, kargo = en_ucuz_kargo(row)
            if birim is None or kargo is None:
                w.writerow({"boy": boy, "sku": sku, "fiyat": "", "kar": "VERI YOK"})
                continue
            toplam = round(birim + kargo, 2)
            for fiyat in FIYAT[boy]:
                u = ucretler(fiyat, kur)
                kar = None if u["odeme_sabit"] is None else round(fiyat - u["toplam"] - toplam, 2)
                kar_ads = None if kar is None else round(kar - fiyat * OFFSITE, 2)
                s = {"boy": boy, "sku": sku, "prodigi_birim": birim, "prodigi_kargo": kargo,
                     "prodigi_toplam": toplam, "fiyat": fiyat, "etsy_islem": u["islem"],
                     "etsy_odeme_yuzde": u["odeme_yuzde"], "etsy_odeme_sabit": u["odeme_sabit"],
                     "etsy_duzenleyici": u["duzenleyici"], "etsy_doviz": u["doviz"],
                     "etsy_ilan": u["ilan"], "etsy_ucret_toplam": u["toplam"], "kar": kar,
                     "kar_yuzde": None if kar is None else round(100 * kar / fiyat, 1),
                     "kar_offsite_ads": kar_ads,
                     "kar_offsite_yuzde": None if kar_ads is None else round(100 * kar_ads / fiyat, 1),
                     "kur_usdtry": kur, "kur_kaynak": kur_kaynak}
                w.writerow(s)
                ozet.append(s)

    # --- onizleme + dosya eslemesi
    hedefler = {}
    kok = usta_kok_bul()
    if kok is None:
        raise SystemExit("HATA: ORIGINAL_HIGH_RES kokü bulunamadi")
    ilerle(f"usta kok: {kok}")
    onizleme_yol, bilgi = onizleme(isd, kok, hedefler)

    plan = {"zaman_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "kur_usdtry": kur, "kur_kaynak": kur_kaynak, "usta_kok": kok, "adaylar": {}}
    for boy in ADAY:
        sku = f"GLOBAL-HPR-{boy}"
        pa = baski_alani(ham, sku)
        b = dict(bilgi[boy])
        b["sku"] = sku
        b["prodigi_baski_alani_px"] = list(pa) if pa else None
        if pa:
            kw, kh = b["kirp_sonrasi_px"]
            b["yeterli_cozunurluk"] = bool(kw >= pa[0] and kh >= pa[1])
            b["eksik_px"] = [max(0, pa[0] - kw), max(0, pa[1] - kh)]
            b["kirp_sonrasi_dpi"] = [round(kw / ADAY_USTA[boy][1]), round(kh / ADAY_USTA[boy][2])]
        plan["adaylar"][boy] = b
    plan_yol = isd / "PLAN_KUCUK.json"
    plan_yol.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

    if not a.no_drive:
        yukle(teyit, "SKU_TEYIT.csv")
        yukle(maliyet, "MALIYET_HPR.csv")
        yukle(onizleme_yol, "ORNEK_KUCUK.jpg")
        yukle(plan_yol, "PLAN_KUCUK.json")
        r = rclone("lsjson", f"{DRV}/ORNEK_KUCUK.jpg")
        if r.returncode == 0:
            try:
                ilerle("ORNEK_KUCUK.jpg ID: " + json.loads(r.stdout)[0].get("ID", ""))
            except Exception:  # noqa: BLE001
                pass
    print(json.dumps({"sku_ok": sum(1 for r in satirlar.values() if r.get("durum") == "ok"),
                      "sku_toplam": len(satirlar), "kur": kur,
                      "kar_ozet": [{k: s[k] for k in ("boy", "fiyat", "kar", "kar_offsite_ads")}
                                   for s in ozet],
                      "plan": {b: {k: plan["adaylar"][b].get(k) for k in
                                   ("usta_orani", "usta_px", "oran_farki_yuzde", "kirpma",
                                    "prodigi_baski_alani_px", "yeterli_cozunurluk", "kirp_sonrasi_dpi")}
                               for b in ADAY}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
