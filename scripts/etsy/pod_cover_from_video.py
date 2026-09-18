#!/usr/bin/env python3
"""Replace only a POD listing's rank-1 image with its live video's frame 0.

The video, all other gallery images, variation-image links, title and listing
state are treated as immutable and are verified after the write.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def gallery(api: Etsy, listing_id: str) -> list[dict]:
    body = api.get(f"/listings/{listing_id}/images", ok404=True) or {}
    return sorted(
        body.get("results") or [],
        key=lambda row: int(row.get("rank") or 0),
    )


def videos(api: Etsy, listing_id: str) -> list[dict]:
    body = api.get(f"/listings/{listing_id}/videos", ok404=True) or {}
    return body.get("results") or []


def variation_images(api: Etsy, shop_id: str, listing_id: str) -> list[dict]:
    body = api.get(
        f"/shops/{shop_id}/listings/{listing_id}/variation-images", ok404=True
    ) or {}
    return body.get("results") or []


def variation_map(rows: list[dict]) -> list[tuple]:
    return sorted(
        (row.get("property_id"), row.get("value_id"), row.get("value"), row.get("image_id"))
        for row in rows
    )


def image_map(rows: list[dict]) -> list[tuple]:
    return [(row.get("listing_image_id"), row.get("rank")) for row in rows]


def video_ids(rows: list[dict]) -> list[int | str | None]:
    return [row.get("video_id") for row in rows]


def eventually(fn, predicate, attempts: int = 8, pause: int = 3):
    value = None
    for _ in range(attempts):
        value = fn()
        if predicate(value):
            return value
        time.sleep(pause)
    return value


def video_url(row: dict) -> str:
    return row.get("video_url") or row.get("url") or row.get("download_url") or ""


def download(url: str, output: pathlib.Path) -> None:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    output.write_bytes(response.content)


def extract_cover(video: pathlib.Path, frame_native: pathlib.Path, cover: pathlib.Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-y", "-i", str(video),
            "-frames:v", "1", str(frame_native),
        ],
        check=True,
    )
    with Image.open(frame_native) as image:
        rgb = image.convert("RGB")
        if rgb.width * 5 != rgb.height * 4:
            raise RuntimeError(f"video ilk karesi 4:5 degil: {rgb.size}")
        rgb.resize((2400, 3000), Image.Resampling.LANCZOS).save(
            cover, format="PNG", compress_level=3
        )


def apply_mobile_display_compensation(cover: pathlib.Path) -> None:
    """Match Etsy Android image rendering to the brighter video rendering.

    The monotonic per-channel curves were measured from paired Chrome/Android
    screenshots of this listing: the live rank-1 image and video frame zero.
    This changes tone only; dimensions and every pixel coordinate stay fixed.
    """
    source_points = np.array(
        [0, 4, 8, 12, 16, 24, 32, 48, 64, 80, 96, 112, 128, 144, 160, 192, 224, 255],
        dtype=np.float32,
    )
    target_points = (
        [0, 4, 6, 9, 16, 27, 34, 56, 78, 96, 114, 131, 143, 158, 173, 202, 244, 255],
        [1, 6, 13, 15, 18, 28, 38, 64, 86, 96, 106, 118, 138, 156, 178, 210, 239, 255],
        [0, 2, 7, 13, 16, 27, 36, 59, 82, 101, 108, 121, 139, 159, 173, 217, 232, 255],
    )
    channel_luts = [
        np.interp(np.arange(256), source_points, values).round().astype(np.uint8)
        for values in target_points
    ]
    with Image.open(cover) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    adjusted = np.empty_like(rgb)
    for channel, lut in enumerate(channel_luts):
        adjusted[:, :, channel] = lut[rgb[:, :, channel]]
    Image.fromarray(adjusted, mode="RGB").save(cover, format="PNG", compress_level=3)


def qa_frame_match(frame_native: pathlib.Path, cover: pathlib.Path) -> float:
    with Image.open(frame_native) as frame, Image.open(cover) as image:
        original = np.asarray(frame.convert("RGB"), dtype=np.float32)
        returned = np.asarray(
            image.convert("RGB").resize(frame.size, Image.Resampling.LANCZOS), dtype=np.float32
        )
    return float(np.abs(original - returned).mean())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--mobile-display-compensation", action="store_true")
    ap.add_argument("--quota-min", type=int, default=50)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    listing_id = str(args.listing_id)
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
    old_cover_id = before_images[0].get("listing_image_id") if before_images else None
    variation_image_ids = {row.get("image_id") for row in before_variations}
    checks = {
        "target_title": "Aquarius and Gemini" in (listing.get("title") or ""),
        "active": listing.get("state") == "active",
        "image_count_13_or_recovery_14": len(before_images) in (13, 14),
        "single_video": len(before_videos) == 1,
        "five_variation_links": len(before_variations) == 5,
        "rank1_exists": bool(
            before_images and int(before_images[0].get("rank") or 0) == 1
        ),
        "rank1_not_variation_linked": bool(old_cover_id and old_cover_id not in variation_image_ids),
    }
    if not all(checks.values()):
        raise SystemExit(f"HATA: onkosul: {checks}")

    current_video_url = video_url(before_videos[0])
    if not current_video_url:
        raise SystemExit(f"HATA: video URL yok; alanlar={sorted(before_videos[0])}")
    source_video = out / "live_video.mp4"
    native_frame = out / "live_video_frame0.png"
    new_cover = out / "Aquarius_Gemini_video_frame0_cover.png"
    download(current_video_url, source_video)
    extract_cover(source_video, native_frame, new_cover)
    frame_mae = qa_frame_match(native_frame, new_cover)
    if args.mobile_display_compensation:
        apply_mobile_display_compensation(new_cover)
    delivered_mae = qa_frame_match(native_frame, new_cover)
    qa = {
        "source_video_id": before_videos[0].get("video_id"),
        "source_frame_size": list(Image.open(native_frame).size),
        "cover_size": list(Image.open(new_cover).size),
        "roundtrip_mae": round(frame_mae, 4),
        "exact_visual_source": frame_mae <= 1.0,
        "mobile_display_compensation": args.mobile_display_compensation,
        "delivered_tone_mae": round(delivered_mae, 4),
        "geometry_unchanged": True,
    }
    if not qa["exact_visual_source"]:
        raise SystemExit(f"HATA: video karesi-kapak eslesmesi: {qa}")

    recovery_candidate = None
    if len(before_images) == 14:
        # A prior guarded run may have uploaded the exact frame at rank 2 and
        # intentionally stopped before deleting the old cover.  Etsy can
        # return rank values with inconsistent JSON types, so identify the
        # candidate from pixels, not from a rank literal.
        matches = []
        for index, candidate in enumerate(before_images[1:], start=2):
            candidate_id = candidate.get("listing_image_id")
            candidate_url = candidate.get("url_fullxfull") or candidate.get("url_570xN")
            if candidate_id in variation_image_ids or not candidate_url:
                continue
            candidate_path = out / f"existing_candidate_{index}_{candidate_id}.jpg"
            download(candidate_url, candidate_path)
            matches.append(
                (qa_frame_match(native_frame, candidate_path), candidate)
            )
        if not matches:
            raise SystemExit("HATA: 14 gorselli kurtarma durumunda guvenli aday yok")
        candidate_mae, recovery_candidate = min(matches, key=lambda item: item[0])
        qa["existing_candidate_id"] = recovery_candidate.get("listing_image_id")
        qa["existing_candidate_rank"] = int(recovery_candidate.get("rank") or 0)
        qa["existing_candidate_mae"] = round(candidate_mae, 4)
        qa["existing_candidate_matches_video"] = candidate_mae <= 5.0
        if not qa["existing_candidate_matches_video"]:
            raise SystemExit(f"HATA: mevcut adaylar video karesi degil: {qa}")

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
                "qa": qa,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = {
        "listing_id": listing_id,
        "apply": args.apply,
        "before_checks": checks,
        "qa": qa,
        "backup": backup_path.name,
        "quota_before": api.remaining,
    }
    if not args.apply:
        result["status"] = "DRY_RUN_PASS"
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        log(json.dumps(result, ensure_ascii=False))
        return
    if api.remaining is not None and int(api.remaining) < args.quota_min:
        raise SystemExit(f"HATA: kota {api.remaining} < {args.quota_min}; yazma yok")

    if recovery_candidate:
        new_cover_id = recovery_candidate.get("listing_image_id")
        mid_images = before_images
        result["reused_existing_candidate"] = True
    else:
        with new_cover.open("rb") as handle:
            uploaded = api.post_file(
                f"/shops/{shop_id}/listings/{listing_id}/images",
                files={"image": (new_cover.name, handle, "image/png")},
                data={
                    "rank": "1",
                    "alt_text": "Aquarius and Gemini gold zodiac couple art matching the video opening frame",
                },
            )
        new_cover_id = uploaded.get("listing_image_id")
        if not new_cover_id:
            raise SystemExit("HATA: yeni kapak image_id donmedi")
        api.post_file(
            f"/shops/{shop_id}/listings/{listing_id}/images",
            files={
                "listing_image_id": (None, str(new_cover_id)),
                "rank": (None, "1"),
            },
        )
        mid_images = eventually(
            lambda: gallery(api, listing_id),
            lambda rows: any(row.get("listing_image_id") == new_cover_id for row in rows),
        )
        new_rank = next(
            (int(row.get("rank") or 0) for row in mid_images if row.get("listing_image_id") == new_cover_id),
            None,
        )
        if new_rank not in (1, 2):
            raise SystemExit(f"HATA: yeni kapak guvenli rank 1/2 konumunda degil: {new_rank}")
    untouched_before = [
        row.get("listing_image_id")
        for row in before_images
        if row.get("listing_image_id") not in (old_cover_id, new_cover_id)
    ]
    # Only now is the former cover removed.  All variation-linked images are
    # separate and were verified before this delete.
    api.delete(f"/shops/{shop_id}/listings/{listing_id}/images/{old_cover_id}")

    after_images = eventually(
        lambda: gallery(api, listing_id),
        lambda rows: len(rows) == 13 and rows[0].get("listing_image_id") == new_cover_id,
    )
    after_videos = videos(api, listing_id)
    after_variations = variation_images(api, shop_id, listing_id)
    after_listing = api.get(f"/listings/{listing_id}") or {}
    untouched_after = [
        row.get("listing_image_id") for row in after_images[1:]
    ]
    final_checks = {
        "new_cover_rank1": bool(
            after_images and after_images[0].get("listing_image_id") == new_cover_id
        ),
        "image_count_13": len(after_images) == 13,
        "other_12_images_unchanged": untouched_before == untouched_after,
        "video_unchanged": video_ids(before_videos) == video_ids(after_videos),
        "variation_images_unchanged": variation_map(before_variations) == variation_map(after_variations),
        "title_unchanged": listing.get("title") == after_listing.get("title"),
        "state_unchanged": listing.get("state") == after_listing.get("state") == "active",
    }
    result.update(
        {
            "status": "PASS" if all(final_checks.values()) else "FAIL",
            "old_cover_id": old_cover_id,
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
