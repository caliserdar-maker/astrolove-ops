#!/usr/bin/env python3
"""Mevcut bir ilan gorselini yeniden siralar + alt metnini yazar (Serdar onayi, 27 Eyl 2026).

uploadListingImage, listing_image_id ile cagrilir: YENI DOSYA YUKLENMEZ, hicbir gorsel silinmez.
Varsayilan KURU DENEME; yazma yalniz --apply --confirm SIRA_ATA ile.
Geri okuma (PASS/FAIL): hedef gorsel istenen sirada, siralar 1..n tekil, alt metin dolu ve istenenle ayni,
gorsel id kumesi ayni (silme/ekleme yok), varyasyon gorsel baglari ayni, videolar ayni, state active.
Etsy siralari gec yansitabilir: geri okuma birkac kez denenir.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing-id", required=True); ap.add_argument("--image-id", required=True, type=int)
    ap.add_argument("--rank", type=int, default=1); ap.add_argument("--alt", required=True)
    ap.add_argument("--out", default="_out"); ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
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
