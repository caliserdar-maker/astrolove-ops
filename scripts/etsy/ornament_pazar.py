#!/usr/bin/env python3
"""ORNAMENT PAZAR (Merkez gorevi 2 Kas 2026, Serdar onayli). SALT OKUMA, Etsy'ye yazma YOK. Yalniz API anahtari (APIKeyStore,
OAuth token kullanmaz / yenilemez). Yalniz GET.

Akis (en fazla BUTCE=80 Etsy API istegi; sayac etsy_common.Etsy.calls, 5xx tekrarlari dahil):
  1. GET /openapi-ping -> x-remaining-today. Kosul: kalan - BUTCE >= ALT (500). Degilse baska istek yok, cikis 2.
  2. findAllListingsActive x 6 ifade (keywords, sort_on=score, limit=100) -> tekillestirme (listing_id).
  3. Favoriye (num_favorers) gore ilk 40: getListingsByListingIds (1 istek, includes=Images,Shop) -> ana gorsel adresi.
  4. Ilk 40'in magazalari: getShop (tekil shop_id) -> transaction_sold_count, review_count, review_average, shop_name.
  5. Siralama: favori azalan, sonra magaza toplam satis azalan. Ilk 20 icin getReviewsByListing (limit=1, 'count').
  6. Ilk 20'nin ana gorseli (etsystatic CDN, API kotasi disi) indirilir; TEMAS.jpg (yalniz ic inceleme).
Bilinmeyen alan bos kalir; rakam uydurulmaz. Etsy ilan basina satis adedi VERMEZ: 'magaza_toplam_satis' magazanin toplamidir.

Kullanim: ornament_pazar.py --out KLASOR   (ortam: ETSY_API_KEY, ETSY_SHARED_SECRET)
Cikti: ILANLAR.csv (tum tekil ilanlar), ILK20.csv, TEMAS.jpg, OZET.json, RAPOR_TASLAK.md
"""
import argparse
import csv
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402

IFADELER = ["personalized couple ornament", "zodiac ornament", "first christmas ornament couple",
            "astrology ornament", "constellation ornament", "custom name date ornament"]
BUTCE = 80          # Merkez: en fazla 80 istek
ALT = 500           # Merkez: kalan - 80 en az 500
ILK_DUKKAN = 40     # favoriye gore ilk 40 ilanin magazasi
ILK = 20
TEKRAR_PAYI = 3     # Etsy._call tek cagrida en fazla 3 gonderim yapar (5xx); butce asilmasin diye cagri oncesi pay


class Butce(SystemExit):
    pass


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Okuyucu:
    def __init__(self, api, butce=BUTCE):
        self.api, self.butce, self.atlanan = api, butce, []

    def get(self, path, params=None, hata_bos=False):
        """Butce kapisi + GET. hata_bos=True: 4xx (403/400 gibi) -> None ve not (kota DUR / 429 yine durdurur)."""
        if self.api.calls + TEKRAR_PAYI > self.butce:
            raise Butce(f"DUR: istek butcesi: {self.api.calls} kullanildi, {path} icin pay yok (butce {self.butce})")
        try:
            return self.api.get(path, params=params, ok404=hata_bos)
        except SystemExit as e:
            m = str(e)
            if hata_bos and m.startswith("HATA: GET") and "-> 429" not in m:
                self.atlanan.append(m[:200])
                E.log(f"  atlandi (alan bos kalir): {m[:160]}")
                return None
            raise


def fiyat(p):
    try:
        return round(int(p["amount"]) / int(p["divisor"]), 2), p.get("currency_code") or ""
    except (TypeError, KeyError, ValueError, ZeroDivisionError):
        return "", ""


def tarih(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def ana_gorsel(L):
    ims = L.get("images") or []
    if not ims:
        return ""
    im = sorted(ims, key=lambda x: (x.get("rank") or 99))[0]
    return im.get("url_570xN") or im.get("url_fullxfull") or ""


def tam(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def sirala_anahtar(s):
    f, t = tam(s.get("favori")), tam(s.get("magaza_toplam_satis"))
    return (-(f if f is not None else -1), -(t if t is not None else -1), int(s["listing_id"]))


SUTUN = ["sira", "listing_id", "url", "baslik", "fiyat", "para_birimi", "magaza_id", "magaza_adi", "favori", "goruntulenme",
         "magaza_toplam_satis", "magaza_yorum", "magaza_puan", "ilan_yorum", "kisisellestirilebilir", "malzeme", "etiketler",
         "ilan_olusturma", "aramalar", "ana_gorsel_url", "tasarim_tarzi"]


def calis(out, api, indir=None):  # noqa: C901
    out.mkdir(parents=True, exist_ok=True)
    ok = Okuyucu(api)
    ozet = {"baslangic_utc": simdi(), "butce": BUTCE, "alt": ALT, "ifadeler": {}, "kaynak": "Etsy Open API v3 (yalniz GET, API anahtari)"}

    # 1. kota
    ok.get("/openapi-ping")
    kalan = tam(api.remaining)
    ozet["kota_baslangic"] = kalan
    E.log(f"kota baslangic: kalan {kalan} (x-remaining-today) | kosul kalan - {BUTCE} >= {ALT}")
    if kalan is None or kalan - BUTCE < ALT:
        ozet["durum"] = "BASLAMADI"
        ozet["neden"] = f"kalan {kalan}: kalan - {BUTCE} < {ALT} (ya da baslik okunamadi)"
        (out / "OZET.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
        E.log(f"BASLAMADI: {ozet['neden']}; baska Etsy istegi yok")
        return 2

    # 2. aramalar
    ilanlar, t0 = {}, time.monotonic()
    for i, q in enumerate(IFADELER, 1):
        j = ok.get("/listings/active", {"keywords": q, "sort_on": "score", "limit": 100}) or {}
        res = j.get("results") or []
        ozet["ifadeler"][q] = {"donen": len(res), "toplam_eslesen": j.get("count")}
        for r, L in enumerate(res, 1):
            lid = str(L.get("listing_id"))
            if lid == "None":
                continue
            s = ilanlar.setdefault(lid, {"_L": L, "aramalar": []})
            s["aramalar"].append(f"{q}#{r}")
        g = time.monotonic() - t0
        E.log(f"[{i}/{len(IFADELER)}] '{q}': {len(res)} ilan (eslesen {j.get('count')}) | tekil {len(ilanlar)} | "
              f"gecen {g:.0f}s kalan ~{g / i * (len(IFADELER) - i):.0f}s | istek {api.calls} | kota {api.remaining}")

    satirlar = []
    for lid, s in ilanlar.items():
        L = s["_L"]
        fy, pb = fiyat(L.get("price"))
        satirlar.append({
            "listing_id": lid, "url": L.get("url") or f"https://www.etsy.com/listing/{lid}", "baslik": L.get("title") or "",
            "fiyat": fy, "para_birimi": pb, "magaza_id": L.get("shop_id") or "", "magaza_adi": "",
            "favori": L.get("num_favorers") if L.get("num_favorers") is not None else "",
            "goruntulenme": L.get("views") if L.get("views") is not None else "",
            "magaza_toplam_satis": "", "magaza_yorum": "", "magaza_puan": "", "ilan_yorum": "",
            "kisisellestirilebilir": L.get("is_personalizable") if L.get("is_personalizable") is not None else "",
            "malzeme": "; ".join(L.get("materials") or []), "etiketler": "; ".join(L.get("tags") or []),
            "ilan_olusturma": tarih(L.get("original_creation_timestamp") or L.get("created_timestamp")),
            "aramalar": " | ".join(s["aramalar"]), "ana_gorsel_url": "", "tasarim_tarzi": ""})
    satirlar.sort(key=sirala_anahtar)
    ust = satirlar[:ILK_DUKKAN]

    # 3. ilk 40: gorsel (+ magaza adi, include veriyorsa)
    if ust:
        j = ok.get("/listings/batch", {"listing_ids": ",".join(s["listing_id"] for s in ust), "includes": "Images,Shop"},
                   hata_bos=True) or {}
        by = {str(L.get("listing_id")): L for L in (j.get("results") or [])}
        for s in ust:
            L = by.get(s["listing_id"]) or {}
            s["ana_gorsel_url"] = ana_gorsel(L)
            sh = L.get("shop") or {}
            if sh.get("shop_name"):
                s["magaza_adi"] = sh["shop_name"]
        E.log(f"batch: {len(by)}/{len(ust)} ilan, gorselli {sum(1 for s in ust if s['ana_gorsel_url'])} | istek {api.calls}")

    # 4. getShop
    dukkan = {}
    shop_idler = list(dict.fromkeys(str(s["magaza_id"]) for s in ust if s["magaza_id"]))
    for i, sid in enumerate(shop_idler, 1):
        dukkan[sid] = ok.get(f"/shops/{sid}", hata_bos=True) or {}
        if i % 10 == 0 or i == len(shop_idler):
            E.log(f"getShop {i}/{len(shop_idler)} | istek {api.calls} | kota {api.remaining}")
    for s in ust:
        d = dukkan.get(str(s["magaza_id"])) or {}
        if d.get("shop_name"):
            s["magaza_adi"] = d["shop_name"]
        for a, b in (("magaza_toplam_satis", "transaction_sold_count"), ("magaza_yorum", "review_count"),
                     ("magaza_puan", "review_average")):
            if d.get(b) is not None:
                s[a] = d[b]

    # 5. siralama (favori, sonra magaza toplam satis) + ilk 20 ilan yorum sayisi
    ust.sort(key=sirala_anahtar)
    satirlar = ust + satirlar[ILK_DUKKAN:]
    for n, s in enumerate(satirlar, 1):
        s["sira"] = n
    ilk = ust[:ILK]
    for i, s in enumerate(ilk, 1):
        j = ok.get(f"/listings/{s['listing_id']}/reviews", {"limit": 1}, hata_bos=True)
        if isinstance(j, dict) and j.get("count") is not None:
            s["ilan_yorum"] = j["count"]
        if i % 5 == 0 or i == len(ilk):
            E.log(f"yorum {i}/{len(ilk)} | istek {api.calls} | kota {api.remaining}")
    ozet["etsy_istek"] = api.calls
    ozet["kota_bitis"] = tam(api.remaining)
    ozet["tekil_ilan"] = len(satirlar)
    ozet["getShop"] = len(shop_idler)
    ozet["atlanan"] = ok.atlanan
    E.log(f"ETSY OKUMA BITTI: istek {api.calls}/{BUTCE} | kota {kalan} -> {api.remaining}")

    # 6. gorseller + temas sayfasi (Etsy API disi; CDN)
    indir = indir or (lambda u: requests.get(u, timeout=60).content)
    resimler = []
    for s in ilk:
        b = None
        if s["ana_gorsel_url"]:
            try:
                b = indir(s["ana_gorsel_url"])
            except Exception as e:  # noqa: BLE001
                ozet.setdefault("gorsel_hata", []).append(f"{s['listing_id']}: {type(e).__name__}")
        resimler.append((s, b))
    ozet["gorsel_indirilen"] = sum(1 for _, b in resimler if b)
    temas(resimler, out / "TEMAS.jpg")

    yaz_csv(out / "ILANLAR.csv", satirlar)
    yaz_csv(out / "ILK20.csv", ilk)
    ozet["bitis_utc"] = simdi()
    ozet["durum"] = "TAMAM"
    (out / "OZET.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "RAPOR_TASLAK.md").write_text(rapor_taslak(ilk, ozet), encoding="utf-8")
    E.log(f"cikti: {out} | tekil ilan {len(satirlar)} | ilk {len(ilk)} | gorsel {ozet['gorsel_indirilen']}/{len(ilk)}")
    return 0


def yaz_csv(yol, satirlar):
    with open(yol, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        w.writerows(satirlar)


def temas(resimler, yol, kol=5, gen=300):
    from PIL import Image, ImageDraw, ImageFont
    try:
        F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except OSError:
        F = ImageFont.load_default()
    yuk, et = gen, 40
    sat = max(1, (len(resimler) + kol - 1) // kol)
    sayfa = Image.new("RGB", (kol * gen, sat * (yuk + et)), "white")
    d = ImageDraw.Draw(sayfa)
    for i, (s, b) in enumerate(resimler):
        x, y = (i % kol) * gen, (i // kol) * (yuk + et)
        if b:
            try:
                im = Image.open(io.BytesIO(b)).convert("RGB")
                im.thumbnail((gen - 4, yuk - 4))
                sayfa.paste(im, (x + (gen - im.width) // 2, y + (yuk - im.height) // 2))
            except Exception:  # noqa: BLE001
                d.text((x + 8, y + yuk // 2), "gorsel acilamadi", fill="red", font=F)
        else:
            d.text((x + 8, y + yuk // 2), "gorsel yok", fill="red", font=F)
        d.text((x + 6, y + yuk + 4), f"#{s['sira']} fav {s['favori']} | {s['listing_id']}", fill="black", font=F)
        d.text((x + 6, y + yuk + 21), str(s.get("magaza_adi") or "")[:34], fill="black", font=F)
    sayfa.save(yol, "JPEG", quality=85)


def rapor_taslak(ilk, ozet):
    k = "Etsy API, kesin"
    y = [f"# Ornament pazar taslak (otomatik; tasarim sutunu elle doldurulur)\n",
         f"Okuma: {ozet['baslangic_utc']} - {ozet.get('bitis_utc', '')} UTC | Etsy istek {ozet.get('etsy_istek')}/{BUTCE} | "
         f"kota {ozet.get('kota_baslangic')} -> {ozet.get('kota_bitis')} ({k})\n",
         "Uyari: Etsy ilan basina satis adedi vermez. 'Magaza satis' magazanin TOPLAM satisidir, ilanin kendi satisi degildir.\n",
         "| # | Ilan | Baslik | Magaza | Fiyat | Favori | Goruntulenme | Magaza satis | Ilan yorum |",
         "|---|---|---|---|---|---|---|---|---|"]
    for s in ilk:
        b = str(s["baslik"]).replace("|", "/")[:70]
        y.append(f"| {s['sira']} | [{s['listing_id']}]({s['url']}) | {b} | {s['magaza_adi']} | {s['fiyat']} {s['para_birimi']} | "
                 f"{s['favori']} | {s['goruntulenme']} | {s['magaza_toplam_satis']} | {s['ilan_yorum']} |")
    y.append(f"\nKaynak: tum rakamlar {k} (findAllListingsActive, getListingsByListingIds, getShop, getReviewsByListing). "
             "Bos hucre = API vermedi.")
    return "\n".join(y) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    api = E.Etsy(E.APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")))
    return calis(Path(a.out), api)


if __name__ == "__main__":
    sys.exit(main())
