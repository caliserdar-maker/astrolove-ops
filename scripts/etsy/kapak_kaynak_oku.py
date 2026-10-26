#!/usr/bin/env python3
"""Kapak uretimi icin kaynak gorsel listesi (Merkez 26 Eki GOREV 2; Serdar onayi). SALT OKUMA, ETSY'YE YAZMA YOK.

Kapsam: 78 poster (--poster, data/pod/pod78_ids.csv) + 78 1st Anniversary (--yd, Drive BY78_TASLAKLAR.csv).
Ilan basina 2 GET (images, variation-images) + ilan basina kota kapisi; yazma yontemleri kapali (yd_envanter_oku.salt_okur).
Kaynak gorsel: poster = 'Midnight Blue' secenegine bagli gorsel; yd = 'Botanical' secenegine bagli gorsel.
Cikti <out>/: POSTER_GORSEL.json, YD_GORSEL.json, KAPAK_KAYNAK.csv (ilan basina tek satir), EKSIK.csv (okunamayan / bagsiz).
Kota ya da hata ile yarida kalirsa okunanlar yine yazilir, okunamayanlar EKSIK.csv'de; cikis 1."""
import argparse
import csv
import json
import os
import pathlib
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402
from yd_envanter_oku import salt_okur  # noqa: E402

KAYNAK = {"poster": "Midnight Blue", "yd": "Botanical"}
ALAN = ("rank", "listing_image_id", "full_width", "full_height", "url_fullxfull", "alt_text")


def liste(yol):
    return [(r["listing_id"].strip(), r.get("cift", "").strip())
            for r in csv.DictReader(open(yol, encoding="utf-8-sig")) if r.get("listing_id", "").strip()]


def oku(api, shop, lid):
    img = sorted((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or [], key=lambda y: y.get("rank") or 0)
    vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    return img, vi


def kayit(tur, lid, cift, img, vi):
    gor = [{k: g.get(k) for k in ALAN} for g in img]
    bag = [{k: b.get(k) for k in ("property_id", "value_id", "value", "image_id")} for b in vi]
    gid = {g["listing_image_id"]: g for g in gor}
    for b in bag:
        g = gid.get(b["image_id"])
        b["rank"] = g["rank"] if g else None                  # None = bagli gorsel galeride yok
    kb = next((b for b in bag if b["value"] == KAYNAK[tur]), None)
    kg = gid.get(kb["image_id"]) if kb else None
    return dict(listing_id=lid, cift=cift, tur=tur, gorsel_sayisi=len(gor), gorseller=gor, baglar=bag,
                kaynak_secenek=KAYNAK[tur], kaynak_image_id=kb["image_id"] if kb else None,
                kaynak_rank=kg["rank"] if kg else None, kaynak_url=kg["url_fullxfull"] if kg else None,
                kaynak_boyut=f"{kg['full_width']}x{kg['full_height']}" if kg else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poster", required=True)
    ap.add_argument("--yd", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k_); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api, shop = E.Etsy(store), os.environ["ETSY_SHOP_ID"]
    salt_okur(api)
    is_ = [("poster", l, c) for l, c in liste(a.poster)] + [("yd", l, c) for l, c in liste(a.yd)]
    sonuc, eksik, durdu = {"poster": [], "yd": []}, [], None
    for n, (tur, lid, cift) in enumerate(is_, 1):
        if durdu:
            eksik.append([lid, cift, tur, f"okunmadi ({durdu})"]); continue
        try:
            api.kota_kapisi(f"ilan {lid}")
            img, vi = oku(api, shop, lid)
        except SystemExit as e:                               # kota tabani / yazma kapisi: kalanlar okunmaz
            durdu = str(e); eksik.append([lid, cift, tur, f"okunmadi ({durdu})"]); continue
        except Exception as e:  # noqa: BLE001
            eksik.append([lid, cift, tur, f"hata {type(e).__name__}: {str(e)[:120]}"]); continue
        k = kayit(tur, lid, cift, img, vi)
        sonuc[tur].append(k)
        if not img:
            eksik.append([lid, cift, tur, "gorsel yok"])
        elif not k["kaynak_image_id"]:
            eksik.append([lid, cift, tur, f"{KAYNAK[tur]} bagi yok (bag {len(k['baglar'])})"])
        elif not k["kaynak_url"]:
            eksik.append([lid, cift, tur, f"{KAYNAK[tur]} bagli gorsel {k['kaynak_image_id']} galeride yok"])
        print(f"[{n}/{len(is_)}] {tur} {lid} gorsel {k['gorsel_sayisi']} bag {len(k['baglar'])} kaynak {k['kaynak_image_id']} "
              f"r{k['kaynak_rank']} {k['kaynak_boyut']} | istek {api.calls} kota {api.remaining}", flush=True)
    meta = dict(kaynak="Etsy API GET (kapak-kaynak-oku)", kosu=os.environ.get("GITHUB_RUN_ID"), istek=api.calls, kota_son=api.remaining)
    (out / "POSTER_GORSEL.json").write_text(json.dumps(dict(meta=meta, ilanlar=sonuc["poster"]), ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "YD_GORSEL.json").write_text(json.dumps(dict(meta=meta, ilanlar=sonuc["yd"]), ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "KAPAK_KAYNAK.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["listing_id", "cift", "tur", "kaynak_image_id", "kaynak_url", "kaynak_boyut"])
        for tur in ("poster", "yd"):
            w.writerows([k["listing_id"], k["cift"], tur, k["kaynak_image_id"] or "", k["kaynak_url"] or "", k["kaynak_boyut"] or ""]
                        for k in sonuc[tur])
    with open(out / "EKSIK.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "tur", "neden"]); w.writerows(eksik)
    satir = len(sonuc["poster"]) + len(sonuc["yd"])
    print(f"OZET: ilan {len(is_)} | CSV satir {satir} (poster {len(sonuc['poster'])}, yd {len(sonuc['yd'])}) | EKSIK {len(eksik)} | "
          f"istek {api.calls} | kota {api.remaining}")
    return 1 if durdu or satir != len(is_) else 0


if __name__ == "__main__":
    sys.exit(main())
