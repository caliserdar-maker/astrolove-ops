#!/usr/bin/env python3
"""Guarded replacement of one POD listing's unlinked rank-1 cover."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
from datetime import datetime, timezone

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import (  # noqa: E402
    download,
    eventually,
    gallery,
    image_map,
    variation_images,
    variation_map,
    video_ids,
    videos,
)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pixel_sha256(path: pathlib.Path) -> str:
    with Image.open(path) as image:
        return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--cover-file", required=True)
    ap.add_argument("--expected-pixel-sha256", required=True)
    ap.add_argument("--expected-old-cover-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--quota-min", type=int, default=50)
    args = ap.parse_args()

    listing_id = str(args.listing_id)
    cover = pathlib.Path(args.cover_file)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not cover.is_file():
        raise SystemExit(f"HATA: kapak yok: {cover}")
    digest = sha256(cover)
    pixel_digest = pixel_sha256(cover)
    if pixel_digest != args.expected_pixel_sha256:
        raise SystemExit(f"HATA: piksel SHA256 uyusmadi: {pixel_digest}")
    with Image.open(cover) as image:
        cover_size = list(image.size)
        cover_mode = image.mode
    if cover_size != [2400, 3000] or cover_mode != "RGB":
        raise SystemExit(f"HATA: kapak ozellikleri: size={cover_size} mode={cover_mode}")

    store = TokenStore(
        os.environ["TOKEN_FILE"],
        os.environ.get("ETSY_API_KEY"),
        os.environ.get("ETSY_SHARED_SECRET"),
    )
    api = Etsy(store)
    shop_id = os.environ["ETSY_SHOP_ID"]
    listing = api.get(f"/listings/{listing_id}") or {}
    before_images = gallery(api, listing_id)
    before_videos = videos(api, listing_id)
    before_variations = variation_images(api, shop_id, listing_id)
    old_cover_id = str(before_images[0].get("listing_image_id")) if before_images else ""
    variation_image_ids = {str(row.get("image_id")) for row in before_variations}
    checks = {
        "target_title": "Aquarius and Gemini" in (listing.get("title") or ""),
        "active": listing.get("state") == "active",
        "image_count_13": len(before_images) == 13,
        "single_video": len(before_videos) == 1,
        "five_variation_links": len(before_variations) == 5,
        "rank1_exists": bool(before_images and int(before_images[0].get("rank") or 0) == 1),
        "expected_old_cover": old_cover_id == str(args.expected_old_cover_id),
        "rank1_not_variation_linked": old_cover_id not in variation_image_ids,
    }
    if not all(checks.values()):
        raise SystemExit(f"HATA: onkosul: {checks}; old_cover={old_cover_id}")

    old_url = before_images[0].get("url_fullxfull") or before_images[0].get("url_570xN")
    if not old_url:
        raise SystemExit("HATA: eski kapak URL yok")
    old_backup = out / f"old_cover_{old_cover_id}.jpg"
    download(old_url, old_backup)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = out / f"backup_{listing_id}_{stamp}.json"
    backup_path.write_text(
        json.dumps(
            {
                "utc": now(),
                "listing": listing,
                "images": before_images,
                "videos": before_videos,
                "variation_images": before_variations,
                "candidate": {
                    "path": str(cover),
                    "sha256": digest,
                    "pixel_sha256": pixel_digest,
                    "size": cover_size,
                    "mode": cover_mode,
                    "scope": "gold artwork only; background/crop/geometry unchanged",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = {
        "listing_id": listing_id,
        "apply": args.apply,
        "status": "DRY_RUN_PASS",
        "before_checks": checks,
        "old_cover_id": old_cover_id,
        "candidate_sha256": digest,
        "candidate_pixel_sha256": pixel_digest,
        "candidate_size": cover_size,
        "candidate_mode": cover_mode,
        "backup": backup_path.name,
        "old_cover_backup": old_backup.name,
        "quota_before": api.remaining,
    }
    if not args.apply:
        (out / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        log(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if api.remaining is not None and int(api.remaining) < args.quota_min:
        raise SystemExit(f"HATA: kota {api.remaining} < {args.quota_min}; yazma yok")

    with cover.open("rb") as handle:
        uploaded = api.post_file(
            f"/shops/{shop_id}/listings/{listing_id}/images",
            files={"image": (cover.name, handle, "image/png")},
            data={
                "rank": "1",
                "alt_text": "Aquarius and Gemini gold zodiac couple art in a midnight blue interior",
            },
        )
    new_cover_id = uploaded.get("listing_image_id")
    if not new_cover_id:
        raise SystemExit("HATA: yeni kapak image_id donmedi; eski kapak korunuyor")
    api.post_file(
        f"/shops/{shop_id}/listings/{listing_id}/images",
        files={
            "listing_image_id": (None, str(new_cover_id)),
            "rank": (None, "1"),
        },
    )
    mid_images = eventually(
        lambda: gallery(api, listing_id),
        lambda rows: len(rows) == 14
        and any(str(row.get("listing_image_id")) == str(new_cover_id) for row in rows)
        and any(str(row.get("listing_image_id")) == old_cover_id for row in rows),
    )
    new_rank = next(
        (
            int(row.get("rank") or 0)
            for row in mid_images
            if str(row.get("listing_image_id")) == str(new_cover_id)
        ),
        None,
    )
    if new_rank not in (1, 2):
        raise SystemExit(
            f"HATA: yeni kapak guvenli rank 1/2 konumunda degil: {new_rank}; eski kapak korunuyor"
        )
    mid_ids = {str(row.get("listing_image_id")) for row in mid_images}
    if not all(str(row.get("listing_image_id")) in mid_ids for row in before_images):
        raise SystemExit("HATA: yukleme sonrasi eski galeri tam degil; eski kapak korunuyor")

    untouched_before = [
        str(row.get("listing_image_id"))
        for row in before_images
        if str(row.get("listing_image_id")) != old_cover_id
    ]
    api.delete(f"/shops/{shop_id}/listings/{listing_id}/images/{old_cover_id}")
    after_images = eventually(
        lambda: gallery(api, listing_id),
        lambda rows: len(rows) == 13
        and str(rows[0].get("listing_image_id")) == str(new_cover_id),
    )
    after_videos = videos(api, listing_id)
    after_variations = variation_images(api, shop_id, listing_id)
    after_listing = api.get(f"/listings/{listing_id}") or {}
    untouched_after = [str(row.get("listing_image_id")) for row in after_images[1:]]
    new_metadata = next(
        (row for row in after_images if str(row.get("listing_image_id")) == str(new_cover_id)),
        {},
    )
    final_checks = {
        "new_cover_rank1": bool(
            after_images and str(after_images[0].get("listing_image_id")) == str(new_cover_id)
        ),
        "new_cover_2400x3000": [
            new_metadata.get("full_width"),
            new_metadata.get("full_height"),
        ] == [2400, 3000],
        "image_count_13": len(after_images) == 13,
        "other_12_images_unchanged": untouched_before == untouched_after,
        "video_unchanged": video_ids(before_videos) == video_ids(after_videos),
        "variation_images_unchanged": variation_map(before_variations)
        == variation_map(after_variations),
        "title_unchanged": listing.get("title") == after_listing.get("title"),
        "state_unchanged": listing.get("state") == after_listing.get("state") == "active",
    }
    result.update(
        {
            "status": "PASS" if all(final_checks.values()) else "FAIL",
            "new_cover_id": new_cover_id,
            "final_checks": final_checks,
            "gallery_after": image_map(after_images),
            "video_ids_after": video_ids(after_videos),
            "quota_after": api.remaining,
        }
    )
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise SystemExit("HATA: kapak geri-okuma kontrolleri gecmedi")


if __name__ == "__main__":
    main()
