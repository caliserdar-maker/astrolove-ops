#!/usr/bin/env python3
"""Apply the measured candidate-B correction only to gold poster artwork."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage


LUT_HEX = (
    "000305080b0d101315181b1d202325282b2d303336383b3e404346484b4e505356585b5e606366686b6e707376787b7e808386888b8e919396999b9ea1a3a6a9abaeb1b3b6b9bbbec1c3c6c9cbced1d3d6d9dbdee1e3e6e9eceeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeefefeff0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f1f1f1f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f3f3f4f5f6f6f6f6f6f6f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f8f9fafafafafafafbfbfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfdfdfdfdfefefefefeffffff",
    "000306080b0e111316191c1f2124272a2c2f3235383a3d404345484b4e505356595c5e616467696c6f7275777a7d808285888b8e909396999b9ea1a4a7a9acacacacacacacacacacacacacacacacacacacacacacacacacacacacacacacacacacacacacacacaeb0b2b4b7babdc0c0c0c0c0c0c0c0c0c0c0c0c0c0c1c1c2c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c4c4c5c6c6c7c7c7c7c7c8c9c9cacacacacacbcccdcdcdcdcdcdcdcdcdcdcfd1d3d5d6d7d8d8d8d8d8d8d8d8d8d9d9d9dadadadadadadbdbdcdcdedfe1e2e3e3e3e3e3e3e3e3e3e3e4e5e6e7e8e9ebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff",
    "00020406080a0c0e10121416181a1c1e20222426292b2d2e2e2f2f2f30303135393d404040404040404040404040404041414141414141414141414141424242434344454546474848494a4b4d4e5054585d616363646565656565656565656565656565656565666667676767676868696a6a6a6a6a6a6a6a6a6a6a6a6a6a6a6a6a6a6b6b6c6d7174787c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7d80838687878787898a8b8c8e8f90929394959798999a9c9d9ea0a1a2a3a5a6a7a8aaabacaeafb0b1b3b4b5b6b8b9babcbdbebfc1c2c3c4c6c7c8cacbcccdcfd0d1d2d4d5d6d8d9dadbdddedfe0e2e3e4e6e7e8e9ebecedeef0f1f2f4f5f6f7f9fafbfcfeff",
)


def artwork_mask(base: np.ndarray) -> np.ndarray:
    zones = np.zeros(base.shape[:2], dtype=bool)
    zones[650:1735, 565:1870] = True
    zones[1775:2165, 630:1810] = True
    zones[2260:2425, 900:1540] = True
    a = base.astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    raw = zones & (r > 44) & (g > 29) & (r > b * 1.16) & (g > b * 1.04) & (r > g * 1.01)
    labels, _ = ndimage.label(raw, structure=np.ones((3, 3), dtype=np.uint8))
    sizes = np.bincount(labels.ravel())
    keep = sizes >= 45
    keep[0] = False
    return ndimage.binary_dilation(keep[labels], iterations=2)


def load_luts(path: pathlib.Path) -> list[np.ndarray]:
    lut_data = json.loads(path.read_text(encoding="utf-8"))
    luts = [np.frombuffer(bytes.fromhex(lut_data[channel]), dtype=np.uint8) for channel in "RGB"]
    if any(len(lut) != 256 for lut in luts):
        raise ValueError("LUT uzunlugu")
    return luts


def build_candidate(base: np.ndarray, luts: list[np.ndarray]) -> tuple[np.ndarray, dict]:
    """Return candidate B plus deterministic, geometry-free QA metrics."""
    if list(base.shape) != [3000, 2400, 3] or base.dtype != np.uint8:
        raise ValueError(f"taban ozellikleri: shape={base.shape} dtype={base.dtype}")
    mask = artwork_mask(base)
    corrected = np.empty_like(base)
    for channel, lut in enumerate(luts):
        corrected[..., channel] = lut[base[..., channel]]
    alpha = np.asarray(
        Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)),
        dtype=np.float32,
    ) / 255.0
    alpha *= mask.astype(np.float32)
    alpha = alpha[..., None]
    candidate = np.rint(base * (1.0 - alpha) + corrected * alpha).clip(0, 255).astype(np.uint8)
    changed = np.any(candidate != base, axis=2)
    pixel_digest = hashlib.sha256(candidate.tobytes()).hexdigest()
    qa = {
        "dimensions": [2400, 3000],
        "mode": "RGB",
        "geometry_operation": "none",
        "changed_pixels": int(changed.sum()),
        "changed_pixels_outside_mask": int(changed[~mask].sum()),
        "mask_fraction": round(float(mask.mean()), 6),
        "pixel_sha256": pixel_digest,
    }
    return candidate, qa


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--qa", required=True)
    ap.add_argument("--luts", required=True)
    ap.add_argument("--expected-pixel-sha256", required=True)
    args = ap.parse_args()
    source = pathlib.Path(args.input)
    output = pathlib.Path(args.output)
    qa_path = pathlib.Path(args.qa)

    with Image.open(source) as image:
        base = np.asarray(image.convert("RGB"), dtype=np.uint8)
    if list(base.shape) != [3000, 2400, 3]:
        raise SystemExit(f"HATA: taban boyutu {base.shape}")
    try:
        luts = load_luts(pathlib.Path(args.luts))
        candidate, qa = build_candidate(base, luts)
    except ValueError as exc:
        raise SystemExit(f"HATA: {exc}") from exc
    pixel_digest = qa["pixel_sha256"]
    if qa["changed_pixels_outside_mask"] != 0:
        raise SystemExit(f"HATA: maske disi degisim: {qa}")
    if pixel_digest != args.expected_pixel_sha256:
        raise SystemExit(f"HATA: piksel SHA256: {qa}")
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(candidate, "RGB").save(output, format="PNG", compress_level=9, optimize=True)
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
