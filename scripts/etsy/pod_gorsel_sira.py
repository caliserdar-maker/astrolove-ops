#!/usr/bin/env python3
"""Mevcut bir ilan gorselini yeniden siralar + alt metnini yazar (Serdar onayi, 27 Eyl 2026).

uploadListingImage, listing_image_id ile cagrilir: YENI DOSYA YUKLENMEZ, hicbir gorsel silinmez.
Varsayilan KURU DENEME; yazma yalniz --apply --confirm SIRA_ATA ile.
Geri okuma (PASS/FAIL): hedef gorsel istenen sirada, siralar 1..n tekil, alt metin dolu ve istenenle ayni,
gorsel id kumesi ayni (silme/ekleme yok), varyasyon gorsel baglari ayni, videolar ayni, state active.
Etsy siralari gec yansitabilir: geri okuma birkac kez denenir.

--sil (Serdar onayi 27 Eyl, yalniz adi verilen gorsel): once yedek (dosya + alt metin + rank + boyut) --out'a,
varyasyon gorseline bagliysa DUR; sonra deleteListingImage; geri okuma: gorsel yok, sayi bir eksik,
--rank1-id 1. sirada tek, siralar 1..n tekil, rank1 alt metni dolu, kalan id'ler/alt metinler ayni,
varyasyon baglari, video ve state ayni. Yazma yalniz --apply --confirm GORSEL_SIL ile.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import (eventually, gallery, variation_images, variation_map,  # noqa: E402
                                  video_ids, videos)


def durum(api, shop, lid):
    g = gallery(api, lid)
    return {"state": (api.get(f"/listings/{lid}") or {}).get("state"),
            "gorseller": [{"id": int(x["listing_image_id"]), "rank": int(x.get("rank") or 0),
                           "alt": x.get("alt_text") or ""} for x in g],
            "varyasyon": variation_map(variation_images(api, shop, lid)),
            "video": video_ids(videos(api, lid))}


def kontroller(once, sonra, hedef, rank, alt):
    ranks = sorted(x["rank"] for x in sonra["gorseller"])
    h = next((x for x in sonra["gorseller"] if x["id"] == hedef), {})
    return {
        f"hedef {hedef} {rank}. sirada": h.get("rank") == rank,
        f"{rank}. sirada tek gorsel": sum(1 for x in sonra["gorseller"] if x["rank"] == rank) == 1,
        "siralar 1..n tekil": ranks == list(range(1, len(ranks) + 1)),
        "alt metin dolu ve ayni": bool(h.get("alt")) and h.get("alt") == alt,
        "gorsel id kumesi ayni (silme/ekleme yok)": {x["id"] for x in once["gorseller"]} == {x["id"] for x in sonra["gorseller"]},
        "varyasyon gorsel baglari ayni": once["varyasyon"] == sonra["varyasyon"],
        "videolar ayni": once["video"] == sonra["video"],
        "ilan active": sonra["state"] == "active",
    }


def sil_kontroller(once, sonra, sil_id, rank1_id):
    ranks = sorted(x["rank"] for x in sonra["gorseller"])
    r1 = [x for x in sonra["gorseller"] if x["rank"] == 1]
    kalan_once = {x["id"]: x["alt"] for x in once["gorseller"] if x["id"] != sil_id}
    kalan_sonra = {x["id"]: x["alt"] for x in sonra["gorseller"]}
    return {
        f"{sil_id} silindi": sil_id not in kalan_sonra,
        f"gorsel sayisi {len(once['gorseller'])} -> {len(once['gorseller']) - 1}": len(sonra["gorseller"]) == len(once["gorseller"]) - 1,
        f"1. sirada tek gorsel = {rank1_id}": [x["id"] for x in r1] == [rank1_id],
        "siralar 1..n tekil": ranks == list(range(1, len(ranks) + 1)),
        "1. sira alt metni dolu": bool(r1 and r1[0]["alt"]),
        "kalan gorseller ve alt metinleri ayni": kalan_once == kalan_sonra,
        "varyasyon gorsel baglari ayni": once["varyasyon"] == sonra["varyasyon"],
        "videolar ayni": once["video"] == sonra["video"],
        "ilan active": sonra["state"] == "active",
    }


def sil(a, api, shop, lid, out):
    sid, r1 = a.sil_image_id, a.rank1_id
    ham = gallery(api, lid)
    once = durum(api, shop, lid)
    (out / f"{lid}_SIL_ONCE.json").write_text(json.dumps({"galeri_ham": ham, **once}, ensure_ascii=False, indent=1))
    hedef = next((x for x in ham if int(x["listing_image_id"]) == sid), None)
    log(f"ilan {lid}: state {once['state']} | galeri {len(ham)} | 1. sirada {[x['id'] for x in once['gorseller'] if x['rank'] == 1]} | kota {api.remaining}")
    if once["state"] != "active":
        raise SystemExit("HATA: ilan active degil. DUR.")
    if hedef is None:
        raise SystemExit(f"HATA: {sid} galeride yok. DUR.")
    if r1 not in {x["id"] for x in once["gorseller"]} or r1 == sid:
        raise SystemExit(f"HATA: --rank1-id {r1} galeride yok ya da silinecek gorselle ayni. DUR.")
    if any(str(sid) == str(v[3]) for v in once["varyasyon"]):
        raise SystemExit(f"HATA: {sid} bir varyasyon gorseline bagli; silinmez. DUR.")
    yedek = out / f"{lid}_SIL_{sid}.jpg"
    urllib.request.urlretrieve(hedef["url_fullxfull"], yedek)
    meta = {"listing_image_id": sid, "rank": hedef.get("rank"), "alt_text": hedef.get("alt_text"),
            "boyut": [hedef.get("full_width"), hedef.get("full_height")], "bayt": yedek.stat().st_size,
            "url_fullxfull": hedef["url_fullxfull"]}
    (out / f"{lid}_SIL_{sid}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    log(f"yedek: {yedek.name} {meta['bayt']} bayt {meta['boyut']} rank {meta['rank']} alt={bool(meta['alt_text'])}")
    if yedek.stat().st_size < 10000:
        raise SystemExit("HATA: yedek dosyasi kucuk/bozuk; silinmedi. DUR.")
    log(f"PLAN: yalniz {sid} silinir; {r1} 1. sirada kalir")
    if not a.apply:
        log("KURU DENEME: Etsy'ye yazilmadi"); return
    api.delete(f"/shops/{shop}/listings/{lid}/images/{sid}")
    sonra = eventually(lambda: durum(api, shop, lid),
                       lambda st: all(sil_kontroller(once, st, sid, r1).values()), attempts=10, pause=6)
    (out / f"{lid}_SIL_SONRA.json").write_text(json.dumps(sonra, ensure_ascii=False, indent=1))
    k = sil_kontroller(once, sonra, sid, r1)
    satir = [f"- {'PASS' if v else 'FAIL'} {ad}" for ad, v in k.items()]
    satir.append(f"- siralar: {[(x['rank'], x['id']) for x in sorted(sonra['gorseller'], key=lambda x: x['rank'])]}")
    satir.append(f"- kota {api.remaining} | SONUC: {'PASS' if all(k.values()) else 'FAIL'}")
    (out / "report.md").write_text("\n".join(satir) + "\n")
    print("\n".join(satir), flush=True)
    if not all(k.values()):
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing-id", required=True); ap.add_argument("--image-id", type=int)
    ap.add_argument("--rank", type=int, default=1); ap.add_argument("--alt", default="")
    ap.add_argument("--sil-image-id", type=int, help="yalniz bu gorseli sil (yedekli)")
    ap.add_argument("--rank1-id", type=int, help="--sil: silme sonrasi 1. sirada beklenen gorsel")
    ap.add_argument("--out", default="_out"); ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    if a.sil_image_id:
        if a.apply and a.confirm != "GORSEL_SIL":
            raise SystemExit("HATA: silme icin --confirm GORSEL_SIL gerekir. DUR.")
        if not a.rank1_id:
            raise SystemExit("HATA: --sil icin --rank1-id gerekir. DUR.")
        out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
        store = TokenStore(os.environ["TOKEN_FILE"], os.environ["ETSY_API_KEY"], os.environ["ETSY_SHARED_SECRET"])
        if store.needs_refresh():
            store.refresh()
        return sil(a, Etsy(store), os.environ["ETSY_SHOP_ID"], a.listing_id, out)
    if not a.image_id:
        raise SystemExit("HATA: --image-id gerekir. DUR.")
    if a.apply and a.confirm != "SIRA_ATA":
        raise SystemExit("HATA: yazma icin --confirm SIRA_ATA gerekir. DUR.")
    if not a.alt.strip() or len(a.alt) > 500:
        raise SystemExit("HATA: alt metin bos olamaz ve 500 karakteri asamaz (OAS). DUR.")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    store = TokenStore(os.environ["TOKEN_FILE"], os.environ["ETSY_API_KEY"], os.environ["ETSY_SHARED_SECRET"])
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store); shop = os.environ["ETSY_SHOP_ID"]; lid = a.listing_id

    once = durum(api, shop, lid)
    (out / f"{lid}_SIRA_ONCE.json").write_text(json.dumps(once, ensure_ascii=False, indent=1))
    log(f"ilan {lid}: state {once['state']} | galeri {len(once['gorseller'])} | "
        f"{a.rank}. sirada: {[x['id'] for x in once['gorseller'] if x['rank'] == a.rank]} | kota {api.remaining}")
    if once["state"] != "active":
        raise SystemExit("HATA: ilan active degil. DUR.")
    if a.image_id not in {x["id"] for x in once["gorseller"]}:
        raise SystemExit(f"HATA: {a.image_id} galeride yok. DUR.")
    on = kontroller(once, once, a.image_id, a.rank, a.alt)
    if all(on.values()):
        log("zaten istenen durumda; yazma yok")
        return
    log(f"PLAN: {a.image_id} -> {a.rank}. sira + alt metin (yeni yukleme yok, silme yok)")
    if not a.apply:
        log("KURU DENEME: Etsy'ye yazilmadi"); return

    api.post_file(f"/shops/{shop}/listings/{lid}/images",
                  files={"listing_image_id": (None, str(a.image_id)), "rank": (None, str(a.rank)),
                         "alt_text": (None, a.alt)})
    sonra = eventually(lambda: durum(api, shop, lid),
                       lambda s: all(kontroller(once, s, a.image_id, a.rank, a.alt).values()),
                       attempts=10, pause=6)
    (out / f"{lid}_SIRA_SONRA.json").write_text(json.dumps(sonra, ensure_ascii=False, indent=1))
    k = kontroller(once, sonra, a.image_id, a.rank, a.alt)
    satir = [f"- {'PASS' if v else 'FAIL'} {ad}" for ad, v in k.items()]
    satir.append(f"- siralar: {[(x['rank'], x['id']) for x in sorted(sonra['gorseller'], key=lambda x: x['rank'])]}")
    satir.append(f"- kota {api.remaining} | SONUC: {'PASS' if all(k.values()) else 'FAIL'}")
    (out / "report.md").write_text("\n".join(satir) + "\n")
    print("\n".join(satir), flush=True)
    if not all(k.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
