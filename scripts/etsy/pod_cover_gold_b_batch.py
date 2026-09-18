#!/usr/bin/env python3
"""Guarded candidate-B cover replacement for the remaining 77 POD listings.

Dry-run reads every listing and locks its current cover ID, video ID, gallery,
variation-image map and deterministic candidate pixel hash.  Apply is refused
unless all 77 dry-runs passed.  During apply, every locked value is rechecked
before the candidate is uploaded, and the old cover is deleted only after the
new image and all protected media have been verified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import sys
from datetime import datetime, timezone

import numpy as np
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
from pod_cover_gold_b_transform import build_candidate, load_luts  # noqa: E402


PILOT_ID = "4570112095"
EXPECTED_CATALOG_SHA256 = "51386f4ad727f446deecf55dac4f154ac58934a4ce74d6a61704f68aaf383917"
EXPECTED_CATALOG_COUNT = 78
EXPECTED_TARGET_COUNT = 77
LEGACY_MASTER_MARKER = "astroLove master-locked POD cover".lower()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_state(path: pathlib.Path) -> dict:
    if not path.exists():
        return {
            "version": 1,
            "pilot_listing_id": PILOT_ID,
            "catalog_sha256": EXPECTED_CATALOG_SHA256,
            "rows": {},
        }
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("version") != 1:
        raise RuntimeError(f"state surumu: {state.get('version')}")
    if state.get("pilot_listing_id") != PILOT_ID:
        raise RuntimeError("state pilot listing id uyusmadi")
    if state.get("catalog_sha256") != EXPECTED_CATALOG_SHA256:
        raise RuntimeError("state katalog SHA uyusmadi")
    state.setdefault("rows", {})
    return state


def save_state(path: pathlib.Path, state: dict) -> None:
    state["updated_utc"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def as_strings(values) -> list[str]:
    return [str(value) for value in values]


def current_snapshot(api: Etsy, shop_id: str, listing_id: str) -> dict:
    listing = api.get(f"/listings/{listing_id}") or {}
    images = gallery(api, listing_id)
    listing_videos = videos(api, listing_id)
    variations = variation_images(api, shop_id, listing_id)
    return {
        "listing": listing,
        "images": images,
        "videos": listing_videos,
        "variations": variations,
    }


def snapshot_signature(snapshot: dict) -> dict:
    return {
        "title": snapshot["listing"].get("title"),
        "state": snapshot["listing"].get("state"),
        "images": [list(item) for item in image_map(snapshot["images"])],
        "video_ids": as_strings(video_ids(snapshot["videos"])),
        "variation_images": [list(item) for item in variation_map(snapshot["variations"])],
    }


def validate_snapshot(snapshot: dict, expected_title: str) -> tuple[dict, dict]:
    images = snapshot["images"]
    listing_videos = snapshot["videos"]
    variations = snapshot["variations"]
    source_cover_id = str(images[0].get("listing_image_id")) if images else ""
    variation_ids = {str(row.get("image_id")) for row in variations}
    marked_unlinked = [
        row for row in images
        if LEGACY_MASTER_MARKER in (row.get("alt_text") or "").lower()
        and str(row.get("listing_image_id")) not in variation_ids
    ]
    newest_image = max(
        images,
        key=lambda row: int(row.get("listing_image_id") or 0),
        default={},
    )
    newest_id = str(newest_image.get("listing_image_id") or "")
    newest_is_unlinked_2400 = bool(
        newest_id
        and newest_id not in variation_ids
        and [newest_image.get("full_width"), newest_image.get("full_height")]
        == [2400, 3000]
    )
    standard_13 = len(images) == 13 and source_cover_id not in variation_ids
    legacy_14_marked = len(images) == 14 and len(marked_unlinked) == 1
    legacy_14_newest = bool(
        len(images) == 14
        and source_cover_id in variation_ids
        and newest_is_unlinked_2400
    )
    legacy_14 = legacy_14_marked or legacy_14_newest
    delete_target_id = (
        source_cover_id if standard_13
        else str(marked_unlinked[0].get("listing_image_id")) if legacy_14_marked
        else newest_id if legacy_14_newest
        else ""
    )
    checks = {
        "expected_title": snapshot["listing"].get("title") == expected_title,
        "active": snapshot["listing"].get("state") == "active",
        "gallery_shape_supported": standard_13 or legacy_14,
        "standard_13": standard_13,
        "legacy_14_with_one_marked_unlinked_cover": legacy_14_marked,
        "legacy_14_with_newest_unlinked_2400_cover": legacy_14_newest,
        "single_video": len(listing_videos) == 1,
        "five_variation_links": len(variations) == 5,
        "rank1_exists": bool(images and int(images[0].get("rank") or 0) == 1),
        "delete_target_exists": bool(delete_target_id),
        "delete_target_not_variation_linked": bool(
            delete_target_id and delete_target_id not in variation_ids
        ),
    }
    required = (
        checks["expected_title"], checks["active"], checks["gallery_shape_supported"],
        checks["single_video"], checks["five_variation_links"], checks["rank1_exists"],
        checks["delete_target_exists"], checks["delete_target_not_variation_linked"],
    )
    if not all(required):
        raise RuntimeError(f"onkosul: {checks}")
    return checks, {
        "mode": "standard_13" if standard_13 else "legacy_14_recovery",
        "legacy_selector": (
            "none" if standard_13
            else "alt_text_marker" if legacy_14_marked
            else "newest_unlinked_2400"
        ),
        "source_cover_id": source_cover_id,
        "delete_target_id": delete_target_id,
        "image_count": len(images),
    }


def make_candidate(snapshot: dict, work: pathlib.Path, luts: list[np.ndarray]) -> tuple[pathlib.Path, dict]:
    images = snapshot["images"]
    listing_videos = snapshot["videos"]
    old_cover_id = images[0].get("listing_image_id")
    url = images[0].get("url_fullxfull") or images[0].get("url_570xN")
    if not url:
        raise RuntimeError("mevcut kapak URL yok")
    work.mkdir(parents=True, exist_ok=True)
    base_cover = work / "current_cover.jpg"
    candidate_path = work / "candidate_B.png"
    download(url, base_cover)
    with Image.open(base_cover) as image:
        base = np.asarray(image.convert("RGB"), dtype=np.uint8)
        base_size = list(image.size)
    if base_size != [2400, 3000]:
        raise RuntimeError(f"mevcut kapak boyutu {base_size} != [2400, 3000]")
    candidate, transform = build_candidate(base, luts)
    transform_checks = {
        "geometry_none": transform.get("geometry_operation") == "none",
        "mask_outside_zero": transform.get("changed_pixels_outside_mask") == 0,
        "changed_pixels_nonzero": int(transform.get("changed_pixels") or 0) > 1000,
        "mask_fraction_safe": 0.005 <= float(transform.get("mask_fraction") or 0) <= 0.04,
    }
    if not all(transform_checks.values()):
        raise RuntimeError(f"B donusum QA: {transform}; checks={transform_checks}")
    Image.fromarray(candidate, "RGB").save(candidate_path, format="PNG", compress_level=9, optimize=True)
    qa = {
        "source_cover_id": old_cover_id,
        "source_cover_size": base_size,
        "source_cover_sha256": sha256(base_cover),
        "source_video_id": listing_videos[0].get("video_id"),
        "cover_size": [2400, 3000],
        "base": "current live rank-1 cover",
        "geometry_unchanged": True,
        "background_pixels_changed": 0,
        "transform": transform,
        "transform_checks": transform_checks,
    }
    return candidate_path, qa


def quota_int(api: Etsy) -> int | None:
    try:
        return int(api.remaining) if api.remaining is not None else None
    except (TypeError, ValueError):
        return None


def require_apply_quota(api: Etsy, rows_left: int, floor: int) -> None:
    remaining = quota_int(api)
    if remaining is None:
        raise RuntimeError("Etsy kota basligi okunamadi; yazma yok")
    required = max(floor, 12 * rows_left + 100, 2 * rows_left + 60)
    if remaining < required:
        raise RuntimeError(f"kota {remaining} < gerekli {required}; yazma yok")


def backup_snapshot(path: pathlib.Path, row: dict, snapshot: dict, qa: dict) -> None:
    path.write_text(
        json.dumps(
            {"utc": now(), "catalog": row, "snapshot": snapshot, "candidate_qa": qa},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def apply_candidate(api: Etsy, shop_id: str, listing_id: str, pair: str,
                    candidate: pathlib.Path, before: dict, replacement_plan: dict,
                    backup_dir: pathlib.Path) -> dict:
    before_images = before["images"]
    before_videos = before["videos"]
    before_variations = before["variations"]
    source_cover_id = str(before_images[0].get("listing_image_id"))
    delete_target_id = str(replacement_plan["delete_target_id"])
    delete_target = next(
        (row for row in before_images
         if str(row.get("listing_image_id")) == delete_target_id),
        None,
    )
    if not delete_target:
        raise RuntimeError("silinecek eski baglantisiz kapak galeride yok")
    old_url = delete_target.get("url_fullxfull") or delete_target.get("url_570xN")
    if not old_url:
        raise RuntimeError("eski kapak URL yok")
    old_backup = backup_dir / f"deleted_cover_{listing_id}_{delete_target_id}.jpg"
    download(old_url, old_backup)

    with candidate.open("rb") as handle:
        uploaded = api.post_file(
            f"/shops/{shop_id}/listings/{listing_id}/images",
            files={"image": (candidate.name, handle, "image/png")},
            data={
                "rank": "1",
                "alt_text": f"{pair} gold zodiac couple art in a midnight blue interior",
            },
        )
    new_cover_id = uploaded.get("listing_image_id")
    if not new_cover_id:
        raise RuntimeError("yeni kapak image_id donmedi; eski kapak korunuyor")
    api.post_file(
        f"/shops/{shop_id}/listings/{listing_id}/images",
        files={"listing_image_id": (None, str(new_cover_id)), "rank": (None, "1")},
    )
    mid_images = eventually(
        lambda: gallery(api, listing_id),
        lambda rows: len(rows) == len(before_images) + 1
        and any(str(x.get("listing_image_id")) == str(new_cover_id) for x in rows)
        and any(str(x.get("listing_image_id")) == delete_target_id for x in rows),
    )
    mid_videos = videos(api, listing_id)
    mid_variations = variation_images(api, shop_id, listing_id)
    mid_ids = {str(x.get("listing_image_id")) for x in mid_images}
    new_rank = next(
        (int(x.get("rank") or 0) for x in mid_images
         if str(x.get("listing_image_id")) == str(new_cover_id)),
        None,
    )
    mid_checks = {
        "new_cover_safe_rank": new_rank in (1, 2),
        "image_count_plus_one": len(mid_images) == len(before_images) + 1,
        "old_gallery_preserved": all(
            str(x.get("listing_image_id")) in mid_ids for x in before_images
        ),
        "video_unchanged_before_delete": video_ids(before_videos) == video_ids(mid_videos),
        "variation_images_unchanged_before_delete": variation_map(before_variations)
        == variation_map(mid_variations),
    }
    if not all(mid_checks.values()):
        raise RuntimeError(f"yukleme geri-okuma: {mid_checks}; eski kapak korunuyor")

    untouched_before = [
        str(x.get("listing_image_id")) for x in before_images
        if str(x.get("listing_image_id")) != delete_target_id
    ]
    api.delete(f"/shops/{shop_id}/listings/{listing_id}/images/{delete_target_id}")
    after_images = eventually(
        lambda: gallery(api, listing_id),
        lambda rows: len(rows) == len(before_images)
        and str(rows[0].get("listing_image_id")) == str(new_cover_id),
    )
    after_videos = videos(api, listing_id)
    after_variations = variation_images(api, shop_id, listing_id)
    after_listing = api.get(f"/listings/{listing_id}") or {}
    new_metadata = next(
        (x for x in after_images if str(x.get("listing_image_id")) == str(new_cover_id)),
        {},
    )
    untouched_after = [str(x.get("listing_image_id")) for x in after_images[1:]]
    final_checks = {
        "new_cover_rank1": bool(
            after_images and str(after_images[0].get("listing_image_id")) == str(new_cover_id)
        ),
        "new_cover_2400x3000": [
            new_metadata.get("full_width"), new_metadata.get("full_height")
        ] == [2400, 3000],
        "image_count_preserved": len(after_images) == len(before_images),
        "other_images_unchanged": untouched_before == untouched_after,
        "video_unchanged": video_ids(before_videos) == video_ids(after_videos),
        "variation_images_unchanged": variation_map(before_variations)
        == variation_map(after_variations),
        "title_unchanged": before["listing"].get("title") == after_listing.get("title"),
        "state_unchanged": before["listing"].get("state")
        == after_listing.get("state") == "active",
    }
    if not all(final_checks.values()):
        raise RuntimeError(f"son geri-okuma: {final_checks}")
    return {
        "replacement_mode": replacement_plan["mode"],
        "legacy_selector": replacement_plan["legacy_selector"],
        "source_cover_id": source_cover_id,
        "deleted_image_id": delete_target_id,
        "new_cover_id": str(new_cover_id),
        "deleted_cover_backup": old_backup.name,
        "mid_checks": mid_checks,
        "final_checks": final_checks,
        "gallery_after": image_map(after_images),
        "video_ids_after": video_ids(after_videos),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--luts", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--quota-min", type=int, default=300)
    args = ap.parse_args()

    catalog_path = pathlib.Path(args.catalog)
    if sha256(catalog_path) != EXPECTED_CATALOG_SHA256:
        raise SystemExit("HATA: 78 POD katalog SHA degisti")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    ids = [str(row.get("id")) for row in catalog]
    if len(catalog) != EXPECTED_CATALOG_COUNT or len(set(ids)) != EXPECTED_CATALOG_COUNT:
        raise SystemExit(f"HATA: POD katalog sayisi/tekilligi: {len(catalog)}/{len(set(ids))}")
    if ids.count(PILOT_ID) != 1:
        raise SystemExit("HATA: pilot ilan katalogda tam bir kez bulunmuyor")
    targets = [row for row in catalog if str(row.get("id")) != PILOT_ID]
    if len(targets) != EXPECTED_TARGET_COUNT:
        raise SystemExit(f"HATA: hedef sayisi {len(targets)} != {EXPECTED_TARGET_COUNT}")

    out = pathlib.Path(args.out)
    work_root = out / "work"
    backup_dir = out / "backups"
    evidence_dir = out / "evidence"
    for path in (work_root, backup_dir, evidence_dir):
        path.mkdir(parents=True, exist_ok=True)
    state_path = pathlib.Path(args.state)
    try:
        state = load_state(state_path)
        luts = load_luts(pathlib.Path(args.luts))
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"HATA: {exc}") from exc

    store = TokenStore(
        os.environ["TOKEN_FILE"],
        os.environ.get("ETSY_API_KEY"),
        os.environ.get("ETSY_SHARED_SECRET"),
    )
    api = Etsy(store)
    shop_id = os.environ["ETSY_SHOP_ID"]

    if args.apply:
        missing = [
            str(row["id"]) for row in targets
            if state.get("rows", {}).get(str(row["id"]), {}).get("dry_run", {}).get("status")
            != "DRY_RUN_PASS"
        ]
        if not state.get("dry_run_complete") or missing:
            raise SystemExit(f"HATA: 77/77 kuru prova kilidi yok; eksik={missing[:10]}")
        api.get(f"/listings/{PILOT_ID}")
        remaining_apply = sum(
            1 for row in targets
            if state.get("rows", {}).get(str(row["id"]), {}).get("apply", {}).get("status") != "PASS"
        )
        try:
            require_apply_quota(api, remaining_apply, args.quota_min)
        except RuntimeError as exc:
            raise SystemExit(f"HATA: {exc}") from exc

    selected = [
        row for row in targets
        if not args.apply
        or state.get("rows", {}).get(str(row["id"]), {}).get("apply", {}).get("status") != "PASS"
    ]
    if args.limit:
        selected = selected[: args.limit]
    failures = 0
    processed = 0
    for index, row in enumerate(selected, 1):
        listing_id = str(row["id"])
        pair = str(row["pair"])
        row_state = state.setdefault("rows", {}).setdefault(
            listing_id, {"listing_id": listing_id, "pair": pair}
        )
        phase = "apply" if args.apply else "dry_run"
        row_state[phase] = {"status": "RUNNING", "started_utc": now()}
        save_state(state_path, state)
        work = work_root / listing_id
        if work.exists():
            shutil.rmtree(work)
        log(f"[{index}/{len(selected)}] {phase.upper()} {pair} {listing_id}")
        try:
            if args.apply:
                require_apply_quota(api, len(selected) - index + 1, args.quota_min)
            before = current_snapshot(api, shop_id, listing_id)
            checks, replacement_plan = validate_snapshot(before, str(row["title"]))
            candidate, qa = make_candidate(before, work, luts)
            current = {
                "source_cover_id": str(before["images"][0].get("listing_image_id")),
                "delete_target_id": replacement_plan["delete_target_id"],
                "replacement_mode": replacement_plan["mode"],
                "legacy_selector": replacement_plan["legacy_selector"],
                "image_count": replacement_plan["image_count"],
                "video_ids": as_strings(video_ids(before["videos"])),
                "snapshot_signature": snapshot_signature(before),
                "candidate_pixel_sha256": qa["transform"]["pixel_sha256"],
            }
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_json = backup_dir / f"backup_{listing_id}_{stamp}.json"
            backup_snapshot(backup_json, row, before, qa)
            evidence = {
                "listing_id": listing_id,
                "pair": pair,
                "phase": phase,
                "before_checks": checks,
                "replacement_plan": replacement_plan,
                "current": current,
                "qa": qa,
                "backup": backup_json.name,
            }
            if not args.apply:
                row_state[phase] = {
                    "status": "DRY_RUN_PASS",
                    "finished_utc": now(),
                    **current,
                    "before_checks": checks,
                    "qa": qa,
                    "backup": backup_json.name,
                    "quota": api.remaining,
                }
            else:
                locked = row_state.get("dry_run", {})
                lock_checks = {
                    "source_cover_id": locked.get("source_cover_id") == current["source_cover_id"],
                    "delete_target_id": locked.get("delete_target_id") == current["delete_target_id"],
                    "replacement_mode": locked.get("replacement_mode") == current["replacement_mode"],
                    "legacy_selector": locked.get("legacy_selector") == current["legacy_selector"],
                    "image_count": locked.get("image_count") == current["image_count"],
                    "video_ids": locked.get("video_ids") == current["video_ids"],
                    "snapshot_signature": locked.get("snapshot_signature")
                    == current["snapshot_signature"],
                    "candidate_pixel_sha256": locked.get("candidate_pixel_sha256")
                    == current["candidate_pixel_sha256"],
                }
                if not all(lock_checks.values()):
                    raise RuntimeError(f"kuru prova-canli kilidi: {lock_checks}")
                applied = apply_candidate(
                    api, shop_id, listing_id, pair, candidate, before,
                    replacement_plan, backup_dir
                )
                evidence["lock_checks"] = lock_checks
                evidence["applied"] = applied
                row_state[phase] = {
                    "status": "PASS",
                    "finished_utc": now(),
                    "lock_checks": lock_checks,
                    "candidate_pixel_sha256": current["candidate_pixel_sha256"],
                    **applied,
                    "quota": api.remaining,
                }
            (evidence_dir / f"{listing_id}_{phase}.json").write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            processed += 1
            log(f"  {row_state[phase]['status']} | kota={api.remaining}")
        except (SystemExit, Exception) as exc:
            failures += 1
            row_state[phase] = {
                "status": "FAIL",
                "finished_utc": now(),
                "error": str(exc),
                "quota": api.remaining,
            }
            log(f"  FAIL: {exc}")
            if args.apply:
                save_state(state_path, state)
                break
        finally:
            save_state(state_path, state)
            shutil.rmtree(work, ignore_errors=True)

    dry_pass = sum(
        1 for row in targets
        if state.get("rows", {}).get(str(row["id"]), {}).get("dry_run", {}).get("status")
        == "DRY_RUN_PASS"
    )
    apply_pass = sum(
        1 for row in targets
        if state.get("rows", {}).get(str(row["id"]), {}).get("apply", {}).get("status") == "PASS"
    )
    if not args.apply:
        state["dry_run_complete"] = dry_pass == EXPECTED_TARGET_COUNT and failures == 0
    state["apply_complete"] = apply_pass == EXPECTED_TARGET_COUNT
    save_state(state_path, state)
    summary = {
        "utc": now(),
        "apply": args.apply,
        "expected_targets": EXPECTED_TARGET_COUNT,
        "selected": len(selected),
        "processed": processed,
        "failures": failures,
        "dry_run_pass": dry_pass,
        "dry_run_complete": state.get("dry_run_complete", False),
        "apply_pass": apply_pass,
        "apply_complete": state.get("apply_complete", False),
        "quota": api.remaining,
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log(json.dumps(summary, ensure_ascii=False))
    if failures:
        raise SystemExit(f"HATA: {failures} ilan basarisiz")
    if not args.apply and not state.get("dry_run_complete") and not args.limit:
        raise SystemExit(f"HATA: kuru prova tam degil: {dry_pass}/{EXPECTED_TARGET_COUNT}")
    if args.apply and not state.get("apply_complete") and not args.limit:
        raise SystemExit(f"HATA: uygulama tam degil: {apply_pass}/{EXPECTED_TARGET_COUNT}")


if __name__ == "__main__":
    main()
