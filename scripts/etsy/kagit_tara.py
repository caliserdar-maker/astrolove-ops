#!/usr/bin/env python3
"""Kagit / tedarikci ifadesi taramasi (Serdar 23 Eki; SALT OKUMA, Etsy'ye yazma YOK).
Aranan: Hahnemuhle, Photo Rag, 308, giclee, Prodigi, cotton/pamuk/хлопок, museum/музей, "fine art paper".
  1) Magaza duzeyi: GET /shops/{id} tum metin alanlari (duyuru, satis/tesekkur mesajlari, politika alanlari) + bolum adlari.
     About ve SSS icin v3 API'de okuma ucu yok (/shops/{id}/about denenir, 404 ise "uc yok" yazilir).
  2) 234 aktif ilanin gorselleri: alt metin + baslik/etiket/materials/EN aciklama (batch) + gorsel OCR (tesseract, 570 px CDN
     kopyasi, kota harcamaz) + Drive'daki eski "Fine Art Paper" kartlarina benzerlik (64x64 gri MAE).
Cikti: <out>/KAGIT_TARAMA.csv (bulgu basina satir), GORSEL_BENZERLIK.csv, KAGIT_OZET.json/md."""
import argparse
import concurrent.futures as cf
import csv
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import beyan_marka_yaz as B  # noqa: E402

DESEN = re.compile(r"hahnem[uü]hle|photo\s*rag|\b308\b|gicl[eé]e|жикле|prodigi|cotton|pamuk|хлоп\w*|museum|музе\w*|"
                   r"fine\s*art\s*paper|ISO\s*9706", re.I)


def bul(metin):
    return sorted({m.group(0).lower() for m in DESEN.finditer(metin or "")})


def metinler(o, yol=""):
    """Sozluk/listedeki tum metin alanlari: (yol, metin)."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from metinler(v, f"{yol}.{k}" if yol else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from metinler(v, f"{yol}[{i}]")
    elif isinstance(o, str):
        yield yol, o


def gri64(b):
    from PIL import Image
    import numpy as np
    return np.asarray(Image.open(io.BytesIO(b)).convert("L").resize((64, 64)), float)


def ocr(b):
    r = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "11", "-l", "eng"], input=b, capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", "ignore")


def gorsel_isle(lid, aile, im, refler):
    url = im.get("url_570xN")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
        b = r.read()
    g = gri64(b)
    mae = {ad: round(float(abs(g - v).mean()), 2) for ad, v in refler.items()}
    return dict(listing_id=lid, aile=aile, rank=im.get("rank"), image_id=im.get("listing_image_id"),
                ocr_bulgu=" ".join(bul(ocr(b))), **{f"mae_{k}": v for k, v in mae.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", nargs="*", default=[], help="eski kart dosyalari (Drive'dan indirilmis)")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    refler = {pathlib.Path(p).stem: gri64(open(p, "rb").read()) for p in a.ref}
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    B.mask(k); B.mask(s)
    store = B.TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = B.Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    bulgu = []
    try:
        dukkan = api.get(f"/shops/{shop}") or {}
        B.kota(api)
        for yol, m in metinler(dukkan):
            for t in bul(m):
                bulgu.append(dict(kaynak="magaza", listing_id="", alan=yol, terim=t, ornek=m[:160].replace("\n", " ")))
        alanlar = sorted(y for y, _ in metinler(dukkan))
        try:
            about = api.get(f"/shops/{shop}/about", ok404=True)
        except Exception:   # noqa: BLE001  v3'te uc yoksa 4xx: tarama durmaz
            about = None
        bolum = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
        for sb in bolum:
            for t in bul(sb.get("title")):
                bulgu.append(dict(kaynak="magaza", listing_id="", alan="section", terim=t, ornek=sb.get("title")))
        ids = B.aktif_idler(api, shop)
        ilan = []
        for i in range(0, len(ids), 100):
            ilan += (api.get("/listings/batch", {"listing_ids": ",".join(ids[i:i + 100])}) or {}).get("results") or []
            B.kota(api)
        isler = []
        bol = {str(x["shop_section_id"]): x.get("title") for x in bolum}
        for n, L in enumerate(sorted(ilan, key=lambda x: int(x["listing_id"])), 1):
            lid = str(L["listing_id"]); aile = B.BOLUM_AILE.get(bol.get(str(L.get("shop_section_id"))), "?")
            api.kota_kapisi(f"ilan {lid}")
            for alan in ("title", "description", "tags", "materials"):
                v = L.get(alan)
                for t in bul(" ".join(v) if isinstance(v, list) else v):
                    bulgu.append(dict(kaynak="ilan", listing_id=lid, alan=alan, terim=t, ornek=""))
            imgs = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
            B.kota(api)
            for im in imgs:
                for t in bul(im.get("alt_text")):
                    bulgu.append(dict(kaynak="alt_metin", listing_id=lid, alan=f"rank {im.get('rank')}", terim=t,
                                      ornek=(im.get("alt_text") or "")[:160]))
                isler.append((lid, aile, im))
            if n % 50 == 0:
                print(f"[{n}/{len(ilan)}] kota {api.remaining}", flush=True)
    except B.Dur as e:
        print(f"DUR: {e} | istek {api.calls} | kota {api.remaining}", flush=True); sys.exit(3)
    print(f"ETSY: {len(ilan)} ilan, {len(isler)} gorsel | istek {api.calls} | kota {api.remaining}", flush=True)
    gor, hata = [], 0
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for f in cf.as_completed([ex.submit(gorsel_isle, *x, refler) for x in isler]):
            try:
                gor.append(f.result())
            except Exception:   # noqa: BLE001  tek gorsel indirilemezse sayilir
                hata += 1
    for g in gor:
        for t in g["ocr_bulgu"].split():
            bulgu.append(dict(kaynak="gorsel_ocr", listing_id=g["listing_id"], alan=f"rank {g['rank']}", terim=t, ornek=str(g["image_id"])))
    with open(out / "KAGIT_TARAMA.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["kaynak", "listing_id", "alan", "terim", "ornek"]); w.writeheader(); w.writerows(bulgu)
    if gor:
        with open(out / "GORSEL_BENZERLIK.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(gor[0].keys())); w.writeheader()
            w.writerows(sorted(gor, key=lambda x: (x["listing_id"], x["rank"] or 0)))
    oz = dict(magaza_alanlari=alanlar, about_ucu="var" if about else "yok (404)", ilan=len(ilan), gorsel=len(isler), gorsel_hata=hata,
              bulgu_kaynak={}, bulgu_terim={}, ilan_sayisi_kaynak={}, istek=api.calls, kota=api.remaining)
    for b in bulgu:
        oz["bulgu_kaynak"][b["kaynak"]] = oz["bulgu_kaynak"].get(b["kaynak"], 0) + 1
        oz["bulgu_terim"][b["terim"]] = oz["bulgu_terim"].get(b["terim"], 0) + 1
    for kay in ("ilan", "alt_metin", "gorsel_ocr"):
        oz["ilan_sayisi_kaynak"][kay] = len({b["listing_id"] for b in bulgu if b["kaynak"] == kay})
    for ad in refler:
        en = sorted(gor, key=lambda x: x[f"mae_{ad}"])[:5]
        oz[f"en_yakin_{ad}"] = [(x["listing_id"], x["rank"], x[f"mae_{ad}"]) for x in en]
    (out / "KAGIT_OZET.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1), encoding="utf-8")
    print("KAGIT_OZET", json.dumps({k: v for k, v in oz.items() if k != "magaza_alanlari"}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
