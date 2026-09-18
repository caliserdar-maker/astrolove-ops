#!/usr/bin/env python3
"""Aries-Pisces referans sahnesini kilitleyip POD kapak/video medyasini toplu uygular.

Sahne, cerceve, masa ve poster konumu master gorselden gelir. Kaynak videodan
yalniz lacivert poster yuzeyi alinir. Yeni kapak rank=1 olarak EKLENIR; mevcut
gorseller ve variation-images baglantilari silinmez/degistirilmez. Mevcut video
yedeklendikten sonra tek yeni video ile degistirilir.
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


OUT_W, OUT_H = 1080, 1350
MARKER = "AstroLove master-locked POD cover"
DEFAULT_SKIP = {
    "4570138967",  # Aries-Pisces referans
    "4570166282",  # Gemini-Gemini duzeltildi
    "4570110121",  # Aquarius-Aquarius duzeltildi
    "4570031205",  # Aries-Leo duzeltildi
    "4570205899",  # Pisces-Taurus duzeltildi
    "4570204681",  # Pisces-Sagittarius duzeltildi
}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def longest_run(values: np.ndarray) -> tuple[int, int]:
    indices = np.flatnonzero(values)
    if not len(indices):
        raise RuntimeError("lacivert poster yuzeyi bulunamadi")
    runs: list[tuple[int, int]] = []
    start = prev = int(indices[0])
    for raw in indices[1:]:
        value = int(raw)
        if value != prev + 1:
            runs.append((start, prev))
            start = value
        prev = value
    runs.append((start, prev))
    return max(runs, key=lambda run: run[1] - run[0])


def navy_rect(path: pathlib.Path) -> tuple[int, int, int, int]:
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    red, green, blue = arr[..., 0], arr[..., 1], arr[..., 2]
    mask = (blue > red + 8) & (blue > green + 3) & ((red + green + blue) < 230)
    x0, x1 = longest_run(mask.mean(axis=0) > 0.30)
    y0, y1 = longest_run(mask.mean(axis=1) > 0.30)
    return x0, y0, x1 - x0 + 1, y1 - y0 + 1


def frame0(video: pathlib.Path, output: pathlib.Path) -> None:
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-frames:v", "1", str(output)],
        check=True,
    )


def build_media(master: pathlib.Path, source: pathlib.Path, cover: pathlib.Path,
                video: pathlib.Path, work: pathlib.Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    source_frame = work / "source_frame0.png"
    frame0(source, source_frame)
    sx, sy, sw, sh = navy_rect(source_frame)
    mx, my, mw, mh = navy_rect(master)
    with Image.open(master) as im:
        master_w, master_h = im.size
    tx = round(mx * OUT_W / master_w)
    ty = round(my * OUT_H / master_h)
    tw = round(mw * OUT_W / master_w)
    th = round(mh * OUT_H / master_h)
    # Aries-Pisces onayli geometrisine toleransli kilit. Fark buyukse yazma yok.
    expected = (168, 98, 766, 994)
    actual = (tx, ty, tw, th)
    if any(abs(a - b) > 3 for a, b in zip(actual, expected)):
        raise RuntimeError(f"master geometrisi degisti: {actual}, beklenen~{expected}")
    filt = (
        f"[0:v]scale={OUT_W}:{OUT_H}:flags=lanczos,fps=30[room];"
        f"[1:v]crop={sw}:{sh}:{sx}:{sy},scale={tw}:{th}:flags=lanczos[art];"
        f"[room][art]overlay={tx}:{ty}:shortest=1[out]"
    )
    subprocess.run([
        "ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", str(master),
        "-i", str(source), "-filter_complex", filt, "-map", "[out]", "-an", "-t", "4.6",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(video),
    ], check=True)
    subprocess.run([
        "ffmpeg", "-loglevel", "error", "-y", "-i", str(video),
        "-vf", "select='eq(n,0)',scale=2400:3000:flags=lanczos,unsharp=5:5:0.2:3:3:0",
        "-frames:v", "1", "-q:v", "2", str(cover),
    ], check=True)
    with Image.open(cover) as im:
        if im.size != (2400, 3000):
            raise RuntimeError(f"kapak boyutu hatali: {im.size}")
    return {"source_rect": [sx, sy, sw, sh], "target_rect": list(actual)}


def gallery(api: Etsy, lid: str) -> list[dict]:
    body = api.get(f"/listings/{lid}/images", ok404=True) or {}
    return sorted(body.get("results") or [], key=lambda x: x.get("rank") or 0)


def videos(api: Etsy, lid: str) -> list[dict]:
    return (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []


def variation_images(api: Etsy, shop: str, lid: str) -> list[dict]:
    return (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []


def variation_map(items: list[dict]) -> list[tuple]:
    return sorted((x.get("property_id"), x.get("value_id"), x.get("value"), x.get("image_id"))
                  for x in items)


def eventually(fn, predicate, attempts: int = 8, pause: int = 3):
    value = None
    for _ in range(attempts):
        value = fn()
        if predicate(value):
            return value
        time.sleep(pause)
    return value


def compact_images(items: list[dict]) -> list[dict]:
    return [{"id": x.get("listing_image_id"), "rank": x.get("rank"),
             "alt_text": x.get("alt_text"), "url": x.get("url_fullxfull")} for x in items]


def marked_cover(items: list[dict]) -> dict | None:
    """Galerinin herhangi bir sirasindaki master-locked kapagi bul."""
    marker = MARKER.lower()
    return next((item for item in items if marker in (item.get("alt_text") or "").lower()), None)


def remaining_below(api: Etsy, minimum: int) -> bool:
    if api.remaining is None:
        return False
    try:
        return int(api.remaining) < minimum
    except (TypeError, ValueError):
        return False


def set_image_rank(api: Etsy, shop: str, lid: str, image_id: int | str, rank: int) -> None:
    """Etsy'nin upload sirasinda yok sayabildigi rank'i ikinci ve acik bir cagriyla yaz."""
    api.post_file(
        f"/shops/{shop}/listings/{lid}/images",
        files={
            "listing_image_id": (None, str(image_id)),
            "rank": (None, str(rank)),
        },
    )


def download(url: str, path: pathlib.Path) -> None:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    path.write_bytes(response.content)


def load_state(path: pathlib.Path) -> dict:
    if not path.exists():
        return {"updated_utc": now(), "rows": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: pathlib.Path, state: dict) -> None:
    state["updated_utc"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def pair_code(text: str) -> str:
    return "_".join(part.strip().upper() for part in text.split("+"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--master-listing", default="4570138967")
    ap.add_argument("--master-image", default="")
    ap.add_argument("--skip", default=",".join(sorted(DEFAULT_SKIP)))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--quota-min", type=int, default=900)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    media_dir = out / "media"
    backup_dir = out / "backups"
    media_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    source_dir = pathlib.Path(args.source_dir)
    state_path = pathlib.Path(args.state)
    state = load_state(state_path)
    skip = {x.strip() for x in args.skip.split(",") if x.strip()}

    store = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                       os.environ.get("ETSY_SHARED_SECRET"))
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]

    master = pathlib.Path(args.master_image) if args.master_image else out / "master_aries_pisces.jpg"
    if not args.master_image:
        master_images = gallery(api, args.master_listing)
        if not master_images or not master_images[0].get("url_fullxfull"):
            raise SystemExit("HATA: Aries-Pisces master kapagi okunamadi")
        download(master_images[0]["url_fullxfull"], master)
    if not master.exists():
        raise SystemExit(f"HATA: master yok: {master}")

    catalog = json.loads(pathlib.Path(args.catalog).read_text(encoding="utf-8"))
    targets = []
    for row in catalog:
        lid = str(row.get("id") or row.get("listing_id") or "")
        if not lid or lid in skip or state.get("rows", {}).get(lid, {}).get("status") == "PASS":
            continue
        targets.append((lid, pair_code(row.get("pair") or row.get("zodiac_pair") or ""), row))
    if args.limit:
        targets = targets[:args.limit]
    log(f"HEDEF: {len(targets)} | atlanan/onceden tamamlanan: {len(catalog) - len(targets)}")

    failures = 0
    for index, (lid, pair, catalog_row) in enumerate(targets, 1):
        # Bu kontrol ilanla ilgili dort geri-okumadan ONCE yapilir. Esik altinda
        # tek bir GET dahi atilmaz; state sonraki kosuda kaldigi yerden devam eder.
        if remaining_below(api, args.quota_min):
            log(f"KOTA DUR: {api.remaining} < {args.quota_min}; {lid} ve sonrasi islenmedi")
            break
        row_state = {"listing_id": lid, "pair": pair, "started_utc": now(), "status": "RUNNING"}
        state.setdefault("rows", {})[lid] = row_state
        save_state(state_path, state)
        log(f"[{index}/{len(targets)}] {pair} {lid}")
        stop_after_row = False
        try:
            source = source_dir / f"{pair}.mp4"
            if not source.exists() or source.stat().st_size < 10000:
                raise RuntimeError(f"kaynak video yok/kucuk: {source}")
            pair_dir = media_dir / pair
            pair_dir.mkdir(parents=True, exist_ok=True)
            cover = pair_dir / f"AstroLove_{pair}_POD_MasterLocked.jpg"
            video = pair_dir / f"AstroLove_{pair}_POD_MasterLocked_Autoplay.mp4"
            qa = build_media(master, source, cover, video, pair_dir / "work")

            listing = api.get(f"/listings/{lid}") or {}
            before_images = gallery(api, lid)
            before_videos = videos(api, lid)
            before_var = variation_images(api, shop, lid)
            backup = {
                "utc": now(), "catalog": catalog_row, "listing": listing,
                "images": before_images, "videos": before_videos,
                "variation_images": before_var, "qa": qa,
            }
            backup_path = backup_dir / f"backup_{lid}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            backup_path.write_text(json.dumps(backup, ensure_ascii=False, indent=1), encoding="utf-8")
            checks = {
                "active": listing.get("state") == "active",
                "gallery_capacity": len(before_images) < 20,
                # Sifir video, onceki kosunun silme-yukleme arasinda kesilmis olabilecegini gosterir;
                # guvenle yeni video yuklenerek iyilestirilebilir. Birden fazla video ise durulur.
                "source_video_at_most_one": len(before_videos) <= 1,
                "variation_images_present": len(before_var) >= 5,
            }
            if not all(checks.values()):
                raise RuntimeError(f"onkosul: {checks}")
            if not args.apply:
                row_state.update(status="DRY_RUN_PASS", qa=qa, backup=backup_path.name,
                                 image_count=len(before_images), video_count=len(before_videos))
                save_state(state_path, state)
                continue
            existing_cover = marked_cover(before_images)
            already_cover = existing_cover is not None
            if existing_cover:
                new_image_id = existing_cover.get("listing_image_id")
                log(f"  mevcut master-locked kapak bulundu: {new_image_id} rank={existing_cover.get('rank')}")
            else:
                with cover.open("rb") as fh:
                    uploaded = api.post_file(
                        f"/shops/{shop}/listings/{lid}/images",
                        files={"image": (cover.name, fh, "image/jpeg")},
                        data={"rank": "1", "alt_text": f"{MARKER}: {pair.replace('_', ' + ').title()}"},
                    )
                new_image_id = uploaded.get("listing_image_id")
                if not new_image_id:
                    raise RuntimeError("yeni kapak image_id donmedi")
                log(f"  kapak eklendi: {new_image_id} rank=1")

            # Etsy bazen multipart upload icindeki rank=1 alanini kabul edip
            # gorseli listenin sonuna ekliyor. Ayrı rank yazimi deterministiktir
            # ve mevcut variation-image baglantilarini degistirmez.
            current_rank = existing_cover.get("rank") if existing_cover else uploaded.get("rank")
            if str(current_rank) != "1":
                set_image_rank(api, shop, lid, new_image_id, 1)
                log(f"  kapak rank duzeltme: {new_image_id} -> 1")

            mid_images = eventually(lambda: gallery(api, lid),
                                    lambda rows: bool(rows and rows[0].get("listing_image_id") == new_image_id))
            mid_var = variation_images(api, shop, lid)
            old_ids = {x.get("listing_image_id") for x in before_images}
            mid_ids = {x.get("listing_image_id") for x in mid_images}
            image_checks = {
                "new_cover_rank1": bool(mid_images and mid_images[0].get("listing_image_id") == new_image_id),
                "old_images_preserved": old_ids <= mid_ids,
                "variation_images_unchanged": variation_map(before_var) == variation_map(mid_var),
                "image_count": len(mid_images) == len(before_images) + (0 if already_cover else 1),
            }
            if not all(image_checks.values()):
                raise RuntimeError(f"kapak geri-okuma: {image_checks}")

            for old_video in before_videos:
                api.delete(f"/shops/{shop}/listings/{lid}/videos/{old_video.get('video_id')}")
            with video.open("rb") as fh:
                uploaded_video = api.post_file(
                    f"/shops/{shop}/listings/{lid}/videos",
                    files={"video": (video.name, fh, "video/mp4")},
                    data={"name": video.name},
                )
            after_videos = eventually(lambda: videos(api, lid), lambda rows: len(rows) == 1)
            after_images = eventually(lambda: gallery(api, lid),
                                      lambda rows: bool(rows and rows[0].get("listing_image_id") == new_image_id))
            after_var = variation_images(api, shop, lid)
            after_listing = api.get(f"/listings/{lid}") or {}
            final_checks = {
                **image_checks,
                "single_video": len(after_videos) == 1,
                "video_uploaded": bool(uploaded_video.get("video_id")),
                "cover_still_rank1": bool(after_images and after_images[0].get("listing_image_id") == new_image_id),
                "variation_images_still_unchanged": variation_map(before_var) == variation_map(after_var),
                "title_unchanged": listing.get("title") == after_listing.get("title"),
                "state_unchanged": listing.get("state") == after_listing.get("state") == "active",
            }
            if not all(final_checks.values()):
                raise RuntimeError(f"son geri-okuma: {final_checks}")
            row_state.update(status="PASS", finished_utc=now(), qa=qa, checks=final_checks,
                             backup=backup_path.name, new_image_id=new_image_id,
                             new_video_id=uploaded_video.get("video_id"), quota=api.remaining)
            log("  PASS")
        except SystemExit as exc:
            # Etsy istemcisi 429'da SystemExit uretir. Bunu yakalayip state ve
            # summary'yi kaydet; sonraki ilanlara gecerek kotayi tuketme.
            message = str(exc)
            if "429" in message or "kota" in message.lower():
                row_state.update(status="STOPPED_QUOTA", finished_utc=now(),
                                 error=message, quota=api.remaining)
                log(f"  KOTA DUR: {message}")
                stop_after_row = True
            else:
                failures += 1
                row_state.update(status="FAIL", finished_utc=now(), error=message, quota=api.remaining)
                log(f"  FAIL: {message}")
        except Exception as exc:  # tek ilan hatasi digerlerini durdurmaz; state'e yazilir
            failures += 1
            row_state.update(status="FAIL", finished_utc=now(), error=str(exc), quota=api.remaining)
            log(f"  FAIL: {exc}")
        finally:
            save_state(state_path, state)
        if stop_after_row:
            break

    summary = {
        "utc": now(), "apply": args.apply, "targets": len(targets), "failures": failures,
        "pass": sum(1 for r in state.get("rows", {}).values() if r.get("status") == "PASS"),
        "dry_run_pass": sum(1 for r in state.get("rows", {}).values() if r.get("status") == "DRY_RUN_PASS"),
        "quota": api.remaining,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(json.dumps(summary, ensure_ascii=False))
    if failures:
        raise SystemExit(f"HATA: {failures} ilan basarisiz; state dosyasina bakiniz")


if __name__ == "__main__":
    main()
