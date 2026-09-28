#!/usr/bin/env python3
"""78 POD ilaninin 15 boy durumu — SALT OKUMA (gece denetimi, 21 Eyl 2026).

Her ilan icin olculur:
  - urun sayisi (hedef 75), boy sayisi (hedef 15), eksik boylar
  - boy etiketlerinde oran oneki ("4:5 · ") kalmis mi
  - menu sirasi hedefle ayni mi, fiyatlar tablo ile birebir mi
  - galeri sayisi, rank 7 gorseli var mi ve o kare POD_SIZE_GUIDE_15 kartiyla esleiyor mu
  - aciklamada "✦ 15 SIZES" / eski "✦ 13 SIZES" / duz "CHOOSE YOUR SIZE" hangisi var
Cikti: <is-dizin>/DURUM_15_GECE.csv -> Drive TEMP/POD_5X7/DURUM_15_GECE.csv
ETSY'YE YAZMA YOK: yalniz GET.
"""
import argparse
import csv
import io
import json
import os
import pathlib
import sys
import time

import numpy as np
import requests
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore  # noqa: E402
import pod_pilot_15 as P  # noqa: E402
import pod_boy_15 as B  # noqa: E402

DRV = "gdrive:ASTROLOVE/TEMP/POD_5X7"
SG15 = "gdrive:ASTROLOVE/TEMP/POD_SIZE_GUIDE_15"
ILAN_JSON = KOK.parent / "etsy" / "seo" / "pod_changes_v2.json"
SUT = ["ilan", "cift", "durum", "urun", "boy", "eksik_boy", "onekli_etiket", "sira_hedef",
       "fiyat_hedef", "fiyat_farki", "galeri", "sg_rank7", "sg_fark", "sg_edisyon",
       "aciklama_boy_blogu", "varyasyon_gorsel", "asama", "not"]
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def _kucult(b):
    im = Image.open(io.BytesIO(b)).convert("RGB").resize((240, 180), Image.LANCZOS)
    return np.asarray(im, dtype=np.int16)


def sg_karsilastir(imgs, cift, isd):
    """rank 7 karesini bu ciftin 15 boyluk kartlariyla karsilastirir -> (fark, edisyon)."""
    r7 = next((im for im in imgs if (im.get("rank") or 0) == 7), None)
    if not r7:
        return None, ""
    d = isd / "sg15" / cift
    d.mkdir(parents=True, exist_ok=True)
    if not any(d.glob("*.jpg")):
        P.rclone("copy", f"{SG15}/{cift}", str(d), "--include", "08_SIZES_*", "-q", sert=False)
    kartlar = {p.parent.name if p.parent.name != cift else p.stem: p for p in d.rglob("*.jpg")}
    if not kartlar:
        return None, "(kart yok)"
    try:
        a = _kucult(requests.get(r7.get("url_fullxfull") or r7.get("url_570xN"), timeout=60).content)
    except (requests.RequestException, OSError) as e:
        return None, f"({type(e).__name__})"
    en_iyi = min(((float(np.abs(a - _kucult(p.read_bytes())).mean()), ed)
                  for ed, p in kartlar.items()), default=(None, ""))
    return (round(en_iyi[0], 2) if en_iyi[0] is not None else None), en_iyi[1]


def aciklama_asamasi(metin):
    if "✦ 15 SIZES" in metin:
        return "15_SIZES"
    if "✦ 13 SIZES" in metin:
        return "13_SIZES"
    if "CHOOSE YOUR SIZE" in metin:
        return "DUZ_13"
    return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is-dizin", default="_work/durum15")
    ap.add_argument("--kota-alt", type=int, default=300)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sg-karsilastir", default="true")
    a = ap.parse_args()
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)
    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    kota0 = api.remaining
    log(f"kota (once): {kota0} | SALT OKUMA")
    if kota0 is not None and int(kota0) < a.kota_alt:
        raise SystemExit(f"DUR: kota {kota0} < {a.kota_alt}")

    katalog = json.loads(ILAN_JSON.read_text(encoding="utf-8"))
    if a.limit:
        katalog = katalog[:a.limit]
    hedef_etiket = [B.ETIKET[k] for k, _f in B.HEDEF]
    satirlar, t_bas, son = [], time.time(), 0.0
    for n, kayit in enumerate(katalog, 1):
        lid = str(kayit["id"])
        cift = "".join(ch if ch.isalnum() else "_" for ch in (kayit.get("pair") or "").upper())
        cift = "_".join(x for x in cift.split("_") if x)
        r = {c: "" for c in SUT}
        r["ilan"], r["cift"] = lid, cift
        try:
            L = api.get(f"/listings/{lid}") or {}
            inv = api.get(f"/listings/{lid}/inventory") or {}
            imgs = sorted(((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or []),
                          key=lambda x: x.get("rank") or 0)
            vimg = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get(
                "results") or []
        except SystemExit as e:
            r["not"] = f"okuma hatasi: {str(e)[:150]}"
            r["asama"] = "OKUNAMADI"
            satirlar.append(r)
            continue
        urunler = inv.get("products") or []
        sira = P.boy_sirasi(inv)
        anahtarlar = [B.anahtar_of(x) for x in sira]
        r["durum"] = L.get("state")
        r["urun"] = len(urunler)
        r["boy"] = len(sira)
        r["eksik_boy"] = ",".join(k for k, _f in B.HEDEF if k not in anahtarlar)
        r["onekli_etiket"] = sum(1 for x in sira if " · " in x)
        r["sira_hedef"] = sira == hedef_etiket
        h = P.fiyat_haritasi(inv)
        farklar = []
        for k, fiyat in B.HEDEF:
            ler = [v[0] for kk, v in h.items() if B.anahtar_of(kk[1]) == k]
            kotu = sorted({x for x in ler if abs(x - fiyat) > 1e-9})
            if kotu:
                farklar.append(f"{k}:{kotu[0]:.2f}!={fiyat:.2f}")
        r["fiyat_hedef"] = not farklar and not r["eksik_boy"]
        r["fiyat_farki"] = "; ".join(farklar)[:120]
        r["galeri"] = len(imgs)
        r["sg_rank7"] = any((im.get("rank") or 0) == 7 for im in imgs)
        r["varyasyon_gorsel"] = len(vimg)
        r["aciklama_boy_blogu"] = aciklama_asamasi(L.get("description") or "")
        if a.sg_karsilastir == "true":
            fark, ed = sg_karsilastir(imgs, cift, isd)
            r["sg_fark"], r["sg_edisyon"] = fark, ed
        # asama: nerede kalmis
        if r["urun"] == 75 and r["onekli_etiket"] == 0 and r["sira_hedef"] and r["fiyat_hedef"]:
            r["asama"] = "ETIKETSIZ_15"          # en son hedef (pilot gibi)
        elif r["urun"] == 75 and r["sira_hedef"] is False and r["onekli_etiket"] == 15:
            r["asama"] = "15_ONEKLI_SIRA_ESKI"
        elif r["urun"] == 75:
            r["asama"] = "15_ONEKLI" if r["onekli_etiket"] else "15_KARISIK"
        elif r["urun"] == 65:
            r["asama"] = "13_BOY"
        else:
            r["asama"] = f"BEKLENMEDIK_{r['urun']}"
        satirlar.append(r)
        gecen = time.time() - t_bas
        if time.time() - son >= 60 or n == len(katalog) or n == 1:
            son = time.time()
            log(f"{n}/{len(katalog)} (%{n / len(katalog) * 100:.0f}) {lid} {cift}: {r['asama']} | "
                f"urun {r['urun']} onek {r['onekli_etiket']} | gecen {gecen / 60:.1f} dk, "
                f"kalan ~{gecen / n * (len(katalog) - n) / 60:.1f} dk | kota {api.remaining}")

    p = isd / "DURUM_15_GECE.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUT)
        w.writeheader()
        w.writerows(satirlar)
    P.rclone("copyto", str(p), f"{DRV}/DURUM_15_GECE.csv")
    sayim = {}
    for r in satirlar:
        sayim[r["asama"]] = sayim.get(r["asama"], 0) + 1
    log(f"OZET asama: {sayim}")
    log(f"75 urun: {sum(1 for r in satirlar if r['urun'] == 75)}/{len(satirlar)} | "
        f"oneksiz etiket: {sum(1 for r in satirlar if r['onekli_etiket'] == 0)} | "
        f"sira hedef: {sum(1 for r in satirlar if r['sira_hedef'] is True)} | "
        f"fiyat hedef: {sum(1 for r in satirlar if r['fiyat_hedef'] is True)} | "
        f"aciklama 15: {sum(1 for r in satirlar if r['aciklama_boy_blogu'] == '15_SIZES')}")
    log(f"kota {kota0} -> {api.remaining} | sure {(time.time() - t_bas) / 60:.1f} dk | "
        f"{DRV}/DURUM_15_GECE.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
