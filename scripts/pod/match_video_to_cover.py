#!/usr/bin/env python3
"""Shift a 4:5 listing video to match a vertically repositioned cover.

The first 0.4 seconds are the exact cover (scaled to the video canvas).  The
remaining motion is moved down by the same cover-space offset and composited
over that cover, so the Etsy-generated video thumbnail and the listing cover
share one composition.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess

import numpy as np
from PIL import Image


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def probe(path: pathlib.Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,duration",
            "-show_entries", "format=duration,size", "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def extract_frame(video: pathlib.Path, output: pathlib.Path, seconds: float) -> None:
    run([
        "ffmpeg", "-loglevel", "error", "-y", "-ss", str(seconds),
        "-i", str(video), "-frames:v", "1", str(output),
    ])


def mae(left: pathlib.Path, right: pathlib.Path) -> float:
    with Image.open(left) as a, Image.open(right) as b:
        aa = np.asarray(a.convert("RGB"), dtype=np.float32)
        bb = np.asarray(b.convert("RGB").resize(a.size, Image.Resampling.LANCZOS), dtype=np.float32)
    return float(np.abs(aa - bb).mean())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cover", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shift-cover-px", type=int, default=200)
    ap.add_argument("--cover-height", type=int, default=3000)
    ap.add_argument("--still", type=float, default=0.6)
    ap.add_argument("--fade", type=float, default=0.2)
    ap.add_argument("--motion-start", type=float, default=0.4)
    args = ap.parse_args()

    cover = pathlib.Path(args.cover)
    source = pathlib.Path(args.video)
    output = pathlib.Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    meta = probe(source)
    stream = meta["streams"][0]
    width, height = int(stream["width"]), int(stream["height"])
    duration = float(meta["format"]["duration"])
    if width * 5 != height * 4:
        raise SystemExit(f"HATA: video 4:5 degil: {width}x{height}")
    with Image.open(cover) as image:
        if image.width * 5 != image.height * 4:
            raise SystemExit(f"HATA: kapak 4:5 degil: {image.size}")

    shift = round(args.shift_cover_px * height / args.cover_height)
    # yuv420p requires even plane boundaries; keep the geometric shift within
    # one pixel while ensuring both stacked sections have even heights.
    if shift % 2:
        shift += 1
    fade_offset = args.still - args.fade
    body_height = height - shift
    # Extend only the source video's own top wall.  Mirroring a narrow strip
    # keeps the join continuous without introducing a visible horizontal band.
    top_sample = max(8, min(32, shift))
    filter_graph = (
        f"[0:v]scale={width}:{height}:flags=lanczos,fps=30[still0];"
        f"[still0]trim=duration={args.still},setpts=PTS-STARTPTS[still];"
        f"[1:v]fps=30,setpts=PTS-STARTPTS,split=2[motion0][top0];"
        f"[top0]crop={width}:{top_sample}:0:0,vflip,scale={width}:{shift}:flags=lanczos[top];"
        f"[motion0]crop={width}:{body_height}:0:0[body];"
        f"[top][body]vstack=inputs=2[shifted];"
        f"[shifted]trim=start={args.motion_start},setpts=PTS-STARTPTS[motion];"
        f"[still][motion]xfade=transition=fade:duration={args.fade}:offset={fade_offset}[out]"
    )
    run([
        "ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", str(cover),
        "-i", str(source), "-filter_complex", filter_graph, "-map", "[out]", "-an",
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ])

    qa_dir = output.parent / f"{output.stem}_qa"
    qa_dir.mkdir(exist_ok=True)
    first = qa_dir / "video_first_frame.png"
    reference = qa_dir / "cover_scaled.png"
    extract_frame(output, first, 0)
    with Image.open(cover) as image:
        image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS).save(reference)
    first_mae = mae(first, reference)
    result = {
        "output": str(output),
        "width": width,
        "height": height,
        "duration": duration,
        "shift_px": shift,
        "first_frame_cover_mae": round(first_mae, 4),
        "first_frame_visual_match": first_mae <= 3.0,
        "still_seconds": args.still,
        "fade_seconds": args.fade,
    }
    (qa_dir / "qa.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["first_frame_visual_match"]:
        raise SystemExit("HATA: video ilk karesi kapakla eslesmedi")


if __name__ == "__main__":
    main()
