#!/usr/bin/env python3
"""PRODIGI CANLI TEKLIF TARAMASI — SALT OKUMA (24 Eyl 2026).

16 HPR SKU x 7 ulke x tum kargo yontemleri icin POST /v4.0/quotes.
quote = fiyat sorgusu; SIPARIS DEGILDIR. Prodigi'ye ve Etsy'ye YAZMA YOK.

TAHMIN YOK: API bir alani dondurmezse hucreye "YOK" yazilir.
Cikti: <out>/PRODIGI_CANLI_TEKLIF.csv + <out>/PRODIGI_CANLI_TEKLIF.md
"""
import argparse
import csv
import json
import pathlib
import sys
import time

import requests

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
from order_router import Prodigi, load_prodigi_key  # noqa: E402

SKULAR = ["GLOBAL-HPR-8X10", "GLOBAL-HPR-11X14", "GLOBAL-HPR-12X16", "GLOBAL-HPR-12X18",
          "GLOBAL-HPR-16X20", "GLOBAL-HPR-16X24", "GLOBAL-HPR-18X24", "GLOBAL-HPR-20X30",
          "GLOBAL-HPR-24X30", "GLOBAL-HPR-24X32", "GLOBAL-HPR-24X36", "GLOBAL-HPR-30X40",
          "GLOBAL-HPR-A4", "GLOBAL-HPR-A3", "GLOBAL-HPR-A2", "GLOBAL-HPR-A1"]
ULKELER = ["US", "GB", "DE", "CA", "AU", "TR", "JP"]
YONTEMLER = ["Budget", "Standard", "Express", "Overnight"]
SUT = ["sku", "ulke", "kargo_yontemi", "urun_bedeli", "kargo_bedeli", "vergi", "toplam",
       "para_birimi", "uretim_ulkesi", "uretim_lab", "tasiyici", "tahmini_teslim",
       "en_ucuz", "sonuc", "hata"]
YOK = "YOK"
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def para(o):
    """{'amount': '15.00', 'currency': 'USD'} -> (float, para_birimi) ya da (None, None)."""
    if not isinstance(o, dict):
        return None, None
    try:
        return round(float(o.get("amount")), 2), o.get("currency")
    except (TypeError, ValueError):
        return None, o.get("currency")


def kur_cek():
    """USD/TRY kurunu bir kaynaktan ceker. Donus: (deger, kaynak, zaman) ya da (None, hata, '')."""
    kaynaklar = [
        ("open.er-api.com", "https://open.er-api.com/v6/latest/USD",
         lambda d: (d["rates"]["TRY"], d.get("time_last_update_utc") or d.get("time_last_update_unix"))),
        ("frankfurter.app", "https://api.frankfurter.app/latest?from=USD&to=TRY",
         lambda d: (d["rates"]["TRY"], d.get("date"))),
        ("exchangerate.host", "https://api.exchangerate.host/latest?base=USD&symbols=TRY",
         lambda d: (d["rates"]["TRY"], d.get("date"))),
    ]
    for ad, url, al in kaynaklar:
        try:
            r = requests.get(url, timeout=25)
            if r.status_code != 200:
                log(f"kur kaynagi {ad}: HTTP {r.status_code}")
                continue
            deger, zaman = al(r.json())
            return round(float(deger), 4), f"{ad} ({url})", str(zaman)
        except Exception as e:                                        # noqa: BLE001
            log(f"kur kaynagi {ad} hata: {type(e).__name__} {str(e)[:100]}")
    return None, "HICBIR KAYNAK CEVAP VERMEDI", ""


def teklif_cek(prod, sku, ulke, yontem):
    """Tek sorgu. Donus: (satirlar, ham_cevap, http_kodu)."""
    govde = {"shippingMethod": yontem, "destinationCountryCode": ulke, "currencyCode": "USD",
             "items": [{"sku": sku, "copies": 1, "assets": [{"printArea": "default"}]}]}
    st, d = prod.call("POST", "/quotes", govde)
    satirlar = []
    if st != 200:
        return [], d, st
    sonuc = d.get("outcome") or YOK
    for q in d.get("quotes") or []:
        cs = q.get("costSummary") or {}
        u_bedel, u_pb = para(cs.get("items"))
        k_bedel, k_pb = para(cs.get("shipping"))
        v_bedel, _ = para(cs.get("totalTax") or cs.get("tax"))
        t_bedel, t_pb = para(cs.get("totalCost"))
        if t_bedel is None and u_bedel is not None and k_bedel is not None:
            t_bedel = round(u_bedel + k_bedel + (v_bedel or 0), 2)
        gonderiler = q.get("shipments") or []
        uretim_ul = uretim_lab = tasiyici = teslim = YOK
        if gonderiler:
            g0 = gonderiler[0]
            fl = g0.get("fulfillmentLocation") or {}
            uretim_ul = fl.get("countryCode") or YOK
            uretim_lab = fl.get("labCode") or YOK
            car = g0.get("carrier") or {}
            tasiyici = " / ".join(x for x in (car.get("name"), car.get("service")) if x) or YOK
            teslim = (g0.get("deliveryEstimate") or g0.get("estimatedDeliveryDate")
                      or car.get("deliveryTime") or YOK)
            if isinstance(teslim, dict):
                teslim = json.dumps(teslim, ensure_ascii=False)
        satirlar.append({
            "sku": sku, "ulke": ulke,
            "kargo_yontemi": q.get("shipmentMethod") or yontem,
            "urun_bedeli": u_bedel if u_bedel is not None else YOK,
            "kargo_bedeli": k_bedel if k_bedel is not None else YOK,
            "vergi": v_bedel if v_bedel is not None else YOK,
            "toplam": t_bedel if t_bedel is not None else YOK,
            "para_birimi": t_pb or u_pb or k_pb or YOK,
            "uretim_ulkesi": uretim_ul, "uretim_lab": uretim_lab, "tasiyici": tasiyici,
            "tahmini_teslim": teslim, "en_ucuz": "", "sonuc": sonuc, "hata": ""})
    return satirlar, d, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="live")
    ap.add_argument("--out", default="_out/fiyat")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    prod = Prodigi(load_prodigi_key(a.env), a.env)

    bas_utc = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    kur, kur_kaynak, kur_zaman = kur_cek()
    log(f"USD/TRY = {kur} | kaynak {kur_kaynak} | kaynak zamani {kur_zaman}")

    satirlar, hatalar, ilk_ham = [], [], None
    toplam = len(SKULAR) * len(ULKELER) * len(YONTEMLER)
    n, son = 0, 0.0
    for sku in SKULAR:
        for ulke in ULKELER:
            for yontem in YONTEMLER:
                n += 1
                s, ham, st = teklif_cek(prod, sku, ulke, yontem)
                if ilk_ham is None and s:
                    ilk_ham = ham
                if s:
                    satirlar += s
                else:
                    mesaj = json.dumps(ham, ensure_ascii=False)[:400]
                    hatalar.append({"sku": sku, "ulke": ulke, "kargo_yontemi": yontem,
                                    "http": st, "ham_hata": mesaj})
                    satirlar.append({c: "" for c in SUT} | {
                        "sku": sku, "ulke": ulke, "kargo_yontemi": yontem,
                        "urun_bedeli": YOK, "kargo_bedeli": YOK, "vergi": YOK, "toplam": YOK,
                        "para_birimi": YOK, "uretim_ulkesi": YOK, "uretim_lab": YOK,
                        "tasiyici": YOK, "tahmini_teslim": YOK, "en_ucuz": "",
                        "sonuc": (ham.get("outcome") if isinstance(ham, dict) else YOK) or YOK,
                        "hata": mesaj})
                if time.time() - son >= 60 or n == toplam:
                    son = time.time()
                    gecen = time.time() - T0
                    log(f"{n}/{toplam} (%{n/toplam*100:.0f}) {sku} {ulke} {yontem} | "
                        f"satir {len(satirlar)} hata {len(hatalar)} | gecen {gecen/60:.1f} dk, "
                        f"kalan ~{(gecen/n*(toplam-n))/60:.1f} dk")

    # en ucuz isaretleme (SKU + ulke basina, gecerli toplami olanlar arasinda)
    grup = {}
    for i, r in enumerate(satirlar):
        if isinstance(r.get("toplam"), float):
            grup.setdefault((r["sku"], r["ulke"]), []).append((r["toplam"], i))
    for (sku, ulke), liste in grup.items():
        en = min(liste)[1]
        satirlar[en]["en_ucuz"] = "EN_UCUZ"

    p_csv = out / "PRODIGI_CANLI_TEKLIF.csv"
    with open(p_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUT, extrasaction="ignore")
        w.writeheader()
        w.writerows(satirlar)
    if ilk_ham is not None:
        (out / "ORNEK_HAM_CEVAP.json").write_text(json.dumps(ilk_ham, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")

    basarili = sum(1 for r in satirlar if isinstance(r.get("toplam"), float))
    eksik_sku = sorted({h["sku"] for h in hatalar})
    md = [f"# Prodigi canli teklif taramasi — {bas_utc}", "",
          "**SALT OKUMA.** Bunlar `POST /v4.0/quotes` fiyat sorgulari; siparis olusturulmadi, "
          "Etsy'ye ve Prodigi'ye hicbir sey yazilmadi.", "",
          f"- Sorgu baslangici: **{bas_utc}**, bitis: "
          f"**{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}**",
          f"- Sorgu sayisi: {toplam} ({len(SKULAR)} SKU x {len(ULKELER)} ulke x "
          f"{len(YONTEMLER)} kargo yontemi)",
          f"- Fiyatli satir: **{basarili}** | cevapsiz/hatali sorgu: **{len(hatalar)}**",
          f"- Ulkeler: {', '.join(ULKELER)}",
          f"- Kargo yontemleri sorgulandi: {', '.join(YONTEMLER)} (Prodigi hepsini her "
          "SKU/ulke icin sunmuyor; sunmadigi yerler hata listesinde)", "",
          "## USD/TRY kuru", "",
          f"- Deger: **{kur if kur is not None else 'YOK'}**",
          f"- Kaynak: {kur_kaynak}",
          f"- Kaynagin verdigi zaman: {kur_zaman or 'YOK'}",
          f"- Cekildigi an (bu kosu): {bas_utc}", "",
          "## Bos hucre kurali", "",
          "API bir degeri dondurmediyse hucreye `YOK` yazildi. Tahmin yok.", ""]
    if hatalar:
        md += ["## Hata veren SKU / ulke / yontem", "",
               f"Etkilenen SKU'lar: {', '.join(eksik_sku)}", "",
               "| sku | ulke | yontem | http | API'nin dondurdugu ham mesaj |", "|---|---|---|---|---|"]
        for h in hatalar[:200]:
            md.append(f"| {h['sku']} | {h['ulke']} | {h['kargo_yontemi']} | {h['http']} | "
                      f"`{h['ham_hata'][:300].replace('|', '/')}` |")
        if len(hatalar) > 200:
            md.append(f"\n... ve {len(hatalar) - 200} hata daha (tamami CSV'nin `hata` sutununda).")
    else:
        md += ["## Hata", "", "Yok."]
    md += ["", "## Dosyalar", "",
           "- `PRODIGI_CANLI_TEKLIF.csv` — her satir: sku, ulke, kargo yontemi, urun bedeli, "
           "kargo bedeli, vergi, toplam, para birimi, uretim ulkesi/lab, tasiyici, tahmini "
           "teslim, `en_ucuz` isareti, sonuc, hata",
           "- `ORNEK_HAM_CEVAP.json` — API'nin ilk basarili ham cevabi (alan adlarinin kaniti)", ""]
    p_md = out / "PRODIGI_CANLI_TEKLIF.md"
    p_md.write_text("\n".join(md), encoding="utf-8")
    log(f"CSV {p_csv} ({len(satirlar)} satir) | MD {p_md} | fiyatli {basarili} | hata {len(hatalar)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
