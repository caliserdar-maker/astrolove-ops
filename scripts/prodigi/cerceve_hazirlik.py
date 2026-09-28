#!/usr/bin/env python3
"""CERCEVE PILOTU hazirligi — SALT OKUMA (22 Eyl 2026, Serdar onayi: yapi secenegi C).

Madde 1: GLOBAL-CFP (paspartusuz) ve GLOBAL-CFPM (paspartulu) urun kayitlari ham haliyle
         alinir; baski alani olculeri ve oranlari karsilastirilir (dosyalarimiz kirpmasiz
         sigiyor mu).
Madde 2: 15 boy x 3 cerceve rengi icin ABD ve Ingiltere'ye EN UCUZ kargo teklifi; mevcut
         ucret modelimiz + Offsite Ads %15 ile net kar; esik altinda kalanlar isaretlenir.
         -> CERCEVE_FIYAT.csv
Madde 5: ayni tekliflerin icinde 3 renk x 2 boy kuru teklif zaten var.

quote = fiyat sorgusu; SIPARIS DEGILDIR. Prodigi'ye ve Etsy'ye yazma YOK.
"""
import argparse
import csv
import json
import math
import pathlib
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
from order_router import Prodigi, load_prodigi_key, KARGO_SECENEK  # noqa: E402
from cerceve_sonda import teklif  # noqa: E402

BOYLAR = ["5x7", "8x10", "A4", "11x14", "12x16", "A3", "12x18", "16x20", "16x24", "A2",
          "18x24", "20x30", "A1", "24x36", "30x40"]
# Cercevesiz (mevcut) Etsy fiyatlarimiz — karsilastirma ve tavan kurali icin
CERCEVESIZ = {"5x7": 19.99, "8x10": 29.99, "A4": 32.99, "11x14": 36.99, "12x16": 39.99,
              "A3": 42.99, "12x18": 43.99, "16x20": 47.99, "16x24": 49.99, "A2": 49.99,
              "18x24": 56.99, "20x30": 79.99, "A1": 89.99, "24x36": 99.99, "30x40": 124.99}
# Bizim dosya oranlarimiz (poster kaynaklari): boy -> oran adi
ORAN = {"5x7": "5:7", "8x10": "4:5", "16x20": "4:5", "12x16": "3:4", "18x24": "3:4",
        "30x40": "3:4", "12x18": "2:3", "16x24": "2:3", "20x30": "2:3", "24x36": "2:3",
        "11x14": "11:14", "A4": "A", "A3": "A", "A2": "A", "A1": "A"}
RENKLER = ["black", "white", "natural"]
# Etsy ucret modeli (7 Eyl olcumu) + Offsite Ads
UCRET_ORAN = 0.065 + 0.065 + 0.0167 + 0.025      # %17.17
UCRET_SABIT = 0.20 + 14 / 48.785                 # ilan + odeme sabiti, USD
ADS_ORAN = 0.15
EKLER = 5.00                                     # postcard + 2 sticker (olculen)
HEDEF_NET = 0.20                                 # onerilen fiyatin hedef net marji
ESIK_NET = 0.15                                  # bunun altinda "cerceveli sunulmasin"
TAVAN_KAT = 2.5                                  # cercevesiz fiyatin kaç kati tavan (ONAY GEREKIR)
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def net(P, maliyet, ads=True):
    oran = UCRET_ORAN + (ADS_ORAN if ads else 0.0)
    return P - maliyet - (P * oran + UCRET_SABIT)


def hedef_fiyat(maliyet, hedef=HEDEF_NET, ads=True):
    """Net marj 'hedef' olacak fiyat; bir ust .99'a yuvarlanir."""
    oran = UCRET_ORAN + (ADS_ORAN if ads else 0.0)
    ham = (maliyet + UCRET_SABIT) / (1 - oran - hedef)
    return math.ceil(ham) - 0.01 if ham > math.floor(ham) else ham - 0.01


def cm(o):
    """productDimensions -> (genislik_cm, yukseklik_cm). Sozluk degilse None."""
    if not isinstance(o, dict):
        return None
    w, h = float(o.get("width") or 0), float(o.get("height") or 0)
    if (o.get("units") or "").lower().startswith("in"):
        w, h = w * 2.54, h * 2.54
    return round(w, 2), round(h, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="live")
    ap.add_argument("--out", default="_out/cerceve2")
    ap.add_argument("--cfpm-boy", default="8x10,16x20,18x24", help="CFPM fark teklifi boylari")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    prod = Prodigi(load_prodigi_key(a.env), a.env)

    # ---------------------------------------------------------------- 1) urun kayitlari
    ham = {}
    for aile in ("GLOBAL-CFP", "GLOBAL-CFPM", "GLOBAL-HPR"):
        ham[aile] = {}
        for b in BOYLAR:
            st, d = prod.call("GET", f"/products/{aile}-{b}")
            if st == 200:
                ham[aile][b] = (d.get("product") or d)
        log(f"{aile}: {len(ham[aile])}/{len(BOYLAR)} urun kaydi alindi")
    (out / "URUN_KAYITLARI.json").write_text(json.dumps(ham, ensure_ascii=False, indent=1),
                                             encoding="utf-8")

    # baski alani karsilastirmasi
    alan_satir = []
    for b in BOYLAR:
        satir = {"boy": b, "oran_dosya": ORAN[b]}
        for aile, kisa in (("GLOBAL-CFP", "cfp"), ("GLOBAL-CFPM", "cfpm"), ("GLOBAL-HPR", "hpr")):
            u = ham[aile].get(b) or {}
            pa = (u.get("printAreas") or {}).get("default") or {}
            # Prodigi v4: printAreas.default.required BOOL; olcu urun duzeyinde geliyor.
            olc = cm(pa.get("productDimensions")) or cm(u.get("productDimensions"))
            satir[f"{kisa}_ham_printarea"] = json.dumps(pa, ensure_ascii=False)[:80]
            satir[f"{kisa}_alan_cm"] = f"{olc[0]}x{olc[1]}" if olc else ""
            satir[f"{kisa}_oran"] = round(olc[1] / olc[0], 4) if olc and olc[0] else ""
        alan_satir.append(satir)
        log(f"  {b}: CFP {satir['cfp_alan_cm']} (oran {satir['cfp_oran']}) | "
            f"CFPM {satir['cfpm_alan_cm']} (oran {satir['cfpm_oran']}) | HPR {satir['hpr_alan_cm']}")
    with open(out / "BASKI_ALANI.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(alan_satir[0]), extrasaction="ignore")
        w.writeheader()
        w.writerows(alan_satir)

    # ---------------------------------------------------------------- 2) fiyat tablosu
    satirlar = []
    toplam = len(BOYLAR) * len(RENKLER)
    n = 0
    for b in BOYLAR:
        for renk in RENKLER:
            n += 1
            sku = f"GLOBAL-CFP-{b}"
            us, us_hata = teklif(prod, sku, "US", {"color": renk})
            gb, gb_hata = teklif(prod, sku, "GB", {"color": renk})
            r = {"boy": b, "oran": ORAN[b], "renk": renk, "prodigi_sku": sku,
                 "cercevesiz_fiyat": CERCEVESIZ[b]}
            if us:
                m_us = round(us["birim"] + us["kargo"] + EKLER, 2)
                r.update({"us_birim": us["birim"], "us_kargo": us["kargo"],
                          "us_yontem": us["yontem"], "us_toplam_maliyet": m_us})
            else:
                m_us = None
                r["us_hata"] = us_hata[:120]
            if gb:
                r.update({"gb_birim": gb["birim"], "gb_kargo": gb["kargo"],
                          "gb_yontem": gb["yontem"],
                          "gb_toplam_maliyet": round(gb["birim"] + gb["kargo"] + EKLER, 2)})
            else:
                r["gb_hata"] = gb_hata[:120]
            if m_us:
                # (a) mevcut yontemimiz: Offsite Ads'siz %20 net hedefi
                P20 = hedef_fiyat(m_us, HEDEF_NET, ads=False)
                # (b) Offsite Ads %15 gelse bile %15 net birakan fiyat (baglayici kisit)
                P15 = hedef_fiyat(m_us, ESIK_NET, ads=True)
                r["fiyat_20_reklamsiz"] = round(P20, 2)
                r["net_ads_us_at20"] = round(net(P20, m_us), 2)
                r["net_ads_us_at20_yuzde"] = round(net(P20, m_us) / P20 * 100, 1)
                r["fiyat_15_ads"] = round(P15, 2)
                r["net_ads_us_at15"] = round(net(P15, m_us), 2)
                r["net_reklamsiz_us_at15"] = round(net(P15, m_us, ads=False), 2)
                if r.get("gb_toplam_maliyet"):
                    r["net_ads_gb_at15"] = round(net(P15, r["gb_toplam_maliyet"]), 2)
                r["kat_cercevesiz"] = round(P15 / CERCEVESIZ[b], 2)
                if r["kat_cercevesiz"] > TAVAN_KAT:
                    r["karar"] = "KAPALI"
                    r["neden"] = (f"Offsite Ads'i kaldiran fiyat cercevesizin {r['kat_cercevesiz']} "
                                  f"kati > {TAVAN_KAT} (tavan kurali, ONAY GEREKIR)")
                else:
                    r["karar"], r["neden"] = "ACIK", ""
            else:
                r["karar"], r["neden"] = "KAPALI", "Prodigi teklifi alinamadi (US)"
            satirlar.append(r)
            log(f"{n}/{toplam} ({n/toplam*100:.0f}%) {b}/{renk}: "
                f"US {r.get('us_toplam_maliyet')} | %20 reklamsiz {r.get('fiyat_20_reklamsiz')} "
                f"(ads net %{r.get('net_ads_us_at20_yuzde')}) | ads-guvenli {r.get('fiyat_15_ads')} "
                f"({r.get('kat_cercevesiz')}x) | {r['karar']} {r['neden'][:50]}")

    sut = ["boy", "oran", "renk", "prodigi_sku", "cercevesiz_fiyat", "us_birim", "us_kargo",
           "us_yontem", "us_toplam_maliyet", "gb_birim", "gb_kargo", "gb_yontem",
           "gb_toplam_maliyet", "fiyat_20_reklamsiz", "net_ads_us_at20",
           "net_ads_us_at20_yuzde", "fiyat_15_ads", "net_ads_us_at15",
           "net_reklamsiz_us_at15", "net_ads_gb_at15", "kat_cercevesiz", "karar", "neden",
           "us_hata", "gb_hata"]
    with open(out / "CERCEVE_FIYAT.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sut, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    acik = sum(1 for r in satirlar if r["karar"] == "ACIK")
    log(f"CERCEVE_FIYAT.csv: {len(satirlar)} satir | ACIK {acik} | KAPALI {len(satirlar)-acik}")

    # ---------------------------------------------------------------- 1b) CFPM fark
    fark = {}
    for b in [x.strip() for x in a.cfpm_boy.split(",") if x.strip()]:
        s_cfp, _ = teklif(prod, f"GLOBAL-CFP-{b}", "US", {"color": "black"})
        s_cfpm, _ = teklif(prod, f"GLOBAL-CFPM-{b}", "US", {"color": "black"})
        if s_cfp and s_cfpm:
            fark[b] = {"cfp_birim": s_cfp["birim"], "cfpm_birim": s_cfpm["birim"],
                       "fark_birim": round(s_cfpm["birim"] - s_cfp["birim"], 2),
                       "cfp_toplam": round(s_cfp["toplam"], 2),
                       "cfpm_toplam": round(s_cfpm["toplam"], 2)}
            log(f"CFPM farki {b}: birim +{fark[b]['fark_birim']:.2f} USD "
                f"({s_cfp['birim']:.2f} -> {s_cfpm['birim']:.2f})")
    (out / "CFPM_FARK.json").write_text(json.dumps(fark, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    log(f"bitti | kargo secenekleri: {KARGO_SECENEK}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
