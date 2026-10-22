#!/usr/bin/env python3
"""Bir POD ilaninin galerisine yeni kapak ekler: 1. siraya yukler, HICBIR gorsel silinmez (POD kapak v3, 27 Eyl 2026).

Korumalar:
  - Ilan state=active degilse DUR (dokunulmaz).
  - Galeri + 1 > 20 ise DUR (Etsy siniri).
  - Ayni kapak zaten 1. sirada ise (ayni alt metin + ayni boyut) yeniden yuklemez (tekrar kosuda cift olmaz).
  - Varsayilan KURU DENEME; yazma yalniz --apply --confirm KAPAK_EKLE ile.
Geri okuma (PASS/FAIL): 1. sira yeni gorsel mi; eski gorseller ayni id ve ayni sirayla 2..n+1'de mi;
varyasyon gorsel baglari ve videolar ayni mi; ilan hala active mi. Once/sonra yedekleri --out'a yazilir.

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: pod_kapak_ekle.py --listing-id ID --image JPG --alt "..." --out OUT [--apply --confirm KAPAK_EKLE]
"""
import argparse
import json
import os
import pathlib
import sys
from datetime import datetime, timezone

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_cover_from_video import (  # noqa: E402
    eventually, gallery, variation_images, variation_map, video_ids, videos,
)

ETSY_MAX = 20


def ozet(rows):
    return [{"rank": r.get("rank"), "listing_image_id": r.get("listing_image_id"),
             "alt_text": r.get("alt_text"), "w": r.get("full_width"), "h": r.get("full_height")} for r in rows]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--image", required=True)
    ap.add_argument("--alt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--quota-min", type=int, default=30)
    a = ap.parse_args()
    if a.apply and a.confirm != "KAPAK_EKLE":
        raise SystemExit("HATA: --apply icin --confirm KAPAK_EKLE gerekli. DUR.")
    if len(a.alt) > 500:
        raise SystemExit("HATA: alt metin 500 karakteri asiyor. DUR.")
    img = pathlib.Path(a.image)
    w, h = Image.open(img).size
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lid = str(a.listing_id)

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    ilan = api.get(f"/listings/{lid}") or {}
    once_g, once_v = gallery(api, lid), variation_images(api, shop, lid)
    once_vid = videos(api, lid)
    once = {"listing_id": int(lid), "state": ilan.get("state"), "gorseller": ozet(once_g),
            "varyasyon": variation_map(once_v), "videolar": video_ids(once_vid)}
    (out / f"{lid}_ONCE.json").write_text(json.dumps(once, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    log(f"ilan {lid}: state {ilan.get('state')} | galeri {len(once_g)} | varyasyon bagi {len(once_v)} | "
        f"video {len(once_vid)} | yuklenecek {img.name} {w}x{h} | kota {api.remaining}")

    if ilan.get("state") != "active":
        raise SystemExit(f"HATA: ilan active degil ({ilan.get('state')}); dokunulmadi. DUR.")
    ilk = once_g[0] if once_g else {}
    zaten = ilk.get("alt_text") == a.alt and (ilk.get("full_width"), ilk.get("full_height")) == (w, h)
    if zaten:
        log("ayni kapak zaten 1. sirada (alt metin + boyut eslesiyor); yukleme yapilmayacak")
    elif len(once_g) + 1 > ETSY_MAX:
        raise SystemExit(f"HATA: galeri {len(once_g)} + 1 > {ETSY_MAX}; Etsy siniri. DUR.")
    log(f"PLAN: 1. siraya ekle; mevcut {len(once_g)} gorsel 2..{len(once_g) + 1}'e kayar; silme yok")
    if not a.apply:
        log("KURU DENEME: yazma yok")
        return
    if zaten:
        yeni_id = ilk.get("listing_image_id")
        eski_ids = [r.get("listing_image_id") for r in once_g[1:]]
    else:
        if api.remaining is not None and int(api.remaining) < a.quota_min:
            raise SystemExit(f"HATA: kota {api.remaining} < {a.quota_min}; yazma yok. DUR.")
        eski_ids = [r.get("listing_image_id") for r in once_g]
        with img.open("rb") as fh:
            up = api.post_file(f"/shops/{shop}/listings/{lid}/images",
                               files={"image": (img.name, fh, "image/jpeg")},
                               data={"rank": "1", "alt_text": a.alt})
        yeni_id = up.get("listing_image_id")
        if not yeni_id:
            raise SystemExit("HATA: yeni gorsel id donmedi. DUR.")
        log(f"yuklendi: listing_image_id {yeni_id}")
        g = eventually(lambda: gallery(api, lid),
                       lambda rows: any(r.get("listing_image_id") == yeni_id for r in rows))
        if not g or g[0].get("listing_image_id") != yeni_id:
            log("yeni gorsel 1. sirada degil; sira tek cagriyla 1'e aliniyor")
            api.post_file(f"/shops/{shop}/listings/{lid}/images",
                          files={"listing_image_id": (None, str(yeni_id)), "rank": (None, "1")})

    sonra_g = eventually(lambda: gallery(api, lid),
                         lambda rows: bool(rows) and rows[0].get("listing_image_id") == yeni_id)
    sonra_v, sonra_vid = variation_images(api, shop, lid), videos(api, lid)
    sonra_state = (api.get(f"/listings/{lid}") or {}).get("state")
    sonra = {"listing_id": int(lid), "state": sonra_state, "gorseller": ozet(sonra_g),
             "varyasyon": variation_map(sonra_v), "videolar": video_ids(sonra_vid)}
    (out / f"{lid}_SONRA.json").write_text(json.dumps(sonra, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    ids = [r.get("listing_image_id") for r in sonra_g]
    kontroller = {
        "1. sira yeni kapak": bool(sonra_g) and ids[0] == yeni_id,
        "yeni kapak alt metni": bool(sonra_g) and sonra_g[0].get("alt_text") == a.alt,
        f"eski {len(eski_ids)} gorsel ayni id + sira (2..{len(eski_ids) + 1})": ids[1:] == eski_ids,
        "gorsel silinmedi": len(ids) == len(eski_ids) + 1,
        "varyasyon gorsel baglari ayni": variation_map(sonra_v) == variation_map(once_v),
        "videolar ayni": video_ids(sonra_vid) == video_ids(once_vid),
        "ilan active": sonra_state == "active",
    }
    ok = all(kontroller.values())
    satirlar = [f"# Kapak ekleme {lid} ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", "",
                f"- yeni kapak listing_image_id: {yeni_id} | galeri {len(once_g)} -> {len(sonra_g)} | kota {api.remaining}"]
    satirlar += [f"- {'PASS' if v else 'FAIL'} {k}" for k, v in kontroller.items()]
    satirlar.append(f"- SONUC: {'PASS' if ok else 'FAIL'}")
    (out / "report.md").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    for s_ in satirlar[2:]:
        log(s_)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
