#!/usr/bin/env python3
"""Galeri v11 B1 yedek, KILITLI ETSY SALT OKUMA asamasi (Merkez 29 Eki, plan v2 adim 5c). ETSY'YE YAZMA YOK.
KILIT SURESI (Serdar 23 Eki): bu kosu yalniz Etsy okur ve JSON yazar; gorsel / video dosyalari kilitsiz ayri is akisinda
(galeri-v11-yedek-indir.yml, scripts/kapak78/galeri_v11_yedek_indir.py) CDN'den indirilir.
Ilan listesi --ciftler (data/pod/pod78_ids.csv: listing_id, cift). Ilan basina once api.kota_kapisi, sonra 3 GET:
  /listings/{id}/images (kimlik, rank, alt metin, url_fullxfull, boyut), /shops/{shop}/listings/{id}/variation-images (renk baglari),
  /listings/{id}/videos (video kimligi, video_url). Yazma yontemleri kapali (yd_envanter_oku.salt_okur: GET disi DUR).
Kontrol (yalniz rapor; okuma durmaz): 9 gorsel, rank 1..9 tekil, 5 renk bagi property 200 (5 ad, tekil, bagli gorsel galeride),
v10 baglari MB->1 DB->6 PW->7 CI->8 WP->9, video 1.
Cikti <out>/: <ilan>_<CIFT>/GALERI.json (gorseller, baglar, videolar; galeri_v10_liste.yedek_oku ile ayni anahtarlar),
OKUMA.csv (ilan basina), OKUMA.md (sayilar + toplam istek + kalan kota). Cikis 0 (kontrol sapmasi raporda), 1 okuma hatasi / kota."""
import argparse
import csv
import json
import os
import pathlib
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))

N = 9
RENK_PID = 200
RENKLER = ("Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment")
V10_SIRA = {"Midnight Blue": 1, "Deep Black": 6, "Pure White": 7, "Champagne Ivory": 8, "Warm Parchment": 9}
GORSEL_ALAN = ("rank", "listing_image_id", "alt_text", "url_fullxfull", "full_width", "full_height")
VIDEO_ALAN = ("video_id", "video_url", "thumbnail_url", "width", "height", "video_state")
ISTEK_ILAN = 3


def oku(api, shop, lid):
    img = sorted((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or [], key=lambda y: y.get("rank") or 0)
    vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    vid = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    return dict(gorseller=[{k: g.get(k) for k in GORSEL_ALAN} for g in img],
                baglar=[{k: b.get(k) for k in ("property_id", "value_id", "value", "image_id")} for b in vi],
                videolar=[{k: v.get(k) for k in VIDEO_ALAN} for v in vid])


def kontrol(y):
    g, b, v = y["gorseller"], y["baglar"], y["videolar"]
    ids = [x["listing_image_id"] for x in g]
    rk = {x["listing_image_id"]: x["rank"] for x in g}
    neden = []
    if len(g) != N or [x["rank"] for x in g] != list(range(1, N + 1)) or len(set(ids)) != len(ids):
        neden.append(f"galeri {len(g)} gorsel / rank {[x['rank'] for x in g]} ({N} ve 1..{N} beklenir)")
    adlar = [x["value"] for x in b]
    if len(b) != 5 or sorted(map(str, adlar)) != sorted(RENKLER) or len(set(adlar)) != len(adlar):
        neden.append(f"renk bagi {len(b)} kayit / adlar {sorted(set(map(str, adlar)))}")
    if any(x["property_id"] != RENK_PID for x in b):
        neden.append("renk bagi property 200 degil")
    if any(x["image_id"] not in ids for x in b):
        neden.append("bagli gorsel galeride yok")
    sira = {x["value"]: rk.get(x["image_id"]) for x in b}
    if not neden and sira != V10_SIRA:
        neden.append(f"baglar v10 sirasinda degil {sira}")
    if len(v) != 1:
        neden.append(f"video {len(v)} (1 beklenir)")
    return neden, sira


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ciftler", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--sadece", default="", help="virgullu listing_id (bos = 78)")
    a = ap.parse_args(argv)
    import etsy_common as E
    from yd_envanter_oku import salt_okur
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k_); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api = E.Etsy(store); salt_okur(api)
    return calistir(api, os.environ["ETSY_SHOP_ID"], a)


def calistir(api, shop, a):
    rows = [r for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig")) if r.get("listing_id", "").strip()]
    s = {x.strip() for x in a.sadece.split(",") if x.strip()}
    if s - {r["listing_id"] for r in rows} or any(not x.isdigit() for x in s):
        print(f"::error::sadece: 78 ilan listesinde olmayan / rakam olmayan {sorted(s)[:5]}"); return 1
    rows = [r for r in rows if not s or r["listing_id"] in s]
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    satir, hata = [], None
    for n, r in enumerate(rows, 1):
        lid, cift = r["listing_id"].strip(), r["cift"].strip()
        c0 = api.calls
        try:
            api.kota_kapisi(f"ilan {lid}")
            y = oku(api, shop, lid)
        except (SystemExit, Exception) as e:  # noqa: BLE001 kota tabani / ag: okuma durur, okunanlar yazilir
            hata = f"ilan {lid}: {str(getattr(e, 'code', None) or e)[:200]}"
            print(f"[{n}/{len(rows)}] {lid} {cift} DUR | {hata}", flush=True)
            break
        d = out / f"{lid}_{cift}"; d.mkdir(exist_ok=True)
        (d / "GALERI.json").write_text(json.dumps(dict(listing_id=lid, cift=cift, **y), ensure_ascii=False, indent=1), encoding="utf-8")
        neden, sira = kontrol(y)
        satir.append(dict(listing_id=lid, cift=cift, gorsel=len(y["gorseller"]), bag=len(y["baglar"]),
                          bag_sira=" ".join(f"{k}:{v}" for k, v in sorted(sira.items())), video=",".join(str(v["video_id"]) for v in y["videolar"]),
                          durum="UYGUN" if not neden else "SAPMA", neden="; ".join(neden), istek=api.calls - c0))
        print(f"[{n}/{len(rows)}] {lid} {cift} gorsel {len(y['gorseller'])} bag {len(y['baglar'])} video {len(y['videolar'])} "
              f"{satir[-1]['durum']} | istek {api.calls} kota {api.remaining}", flush=True)
    with open(out / "OKUMA.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["listing_id", "cift", "gorsel", "bag", "bag_sira", "video", "durum", "neden", "istek"])
        w.writeheader(); w.writerows(satir)
    uy = sum(1 for x in satir if x["durum"] == "UYGUN")
    ozet = (f"# Galeri v11 yedek: Etsy salt okuma\n\nilan okundu {len(satir)}/{len(rows)} | UYGUN {uy} | SAPMA {len(satir) - uy}\n"
            f"istek (api.calls, bu kosu) {api.calls} | ilan basina {ISTEK_ILAN} GET | kalan kota {api.remaining}\n"
            + (f"\nDUR: {hata}\n" if hata else "")
            + "".join(f"- {x['listing_id']} {x['cift']}: {x['neden']}\n" for x in satir if x["neden"]))
    (out / "OKUMA.md").write_text(ozet, encoding="utf-8")
    print(ozet, flush=True)
    return 1 if hata or len(satir) != len(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
