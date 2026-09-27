#!/usr/bin/env python3
"""Duz 4:5 baskiyi prosedurel cerceve mockup'larina yerlestirir."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 2000, 2500
FRAME_NAMES = {"BK": "Black Frame", "WH": "White Frame", "NA": "Natural Frame"}
FRAME_COLORS = {
    "BK": ((31, 30, 29), (70, 67, 63)),
    "WH": ((235, 233, 226), (199, 197, 190)),
    "NA": ((177, 128, 78), (116, 78, 45)),
}
RESAMPLE = Image.Resampling.LANCZOS


def open_design(path: Path) -> Image.Image:
    with Image.open(path) as im:
        rgb = ImageOps.exif_transpose(im).convert("RGB")
    if rgb.width * 5 != rgb.height * 4:
        raise ValueError(f"girdi 4:5 olmali, kirpma yasak: {rgb.size}")
    return rgb


def wall() -> Image.Image:
    """Hafif sicak, dikey gradyanli duvar."""
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    top = np.array([244, 241, 235], dtype=np.float32)[None, None, :]
    bottom = np.array([225, 220, 211], dtype=np.float32)[None, None, :]
    a = np.broadcast_to(top * (1 - y) + bottom * y, (H, W, 3))
    return Image.fromarray(np.uint8(np.rint(a)), "RGB")


def _frame_layer(size: tuple[int, int], code: str, paspartu: bool) -> tuple[Image.Image, tuple[int, int, int, int]]:
    fw, fh = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    outer, inner = FRAME_COLORS[code]
    profile = max(12, round(fw * 0.055))
    mat = round(fw * 0.075) if paspartu else 0
    d.rectangle((0, 0, fw - 1, fh - 1), fill=outer)
    d.rectangle((profile // 3, profile // 3, fw - profile // 3 - 1, fh - profile // 3 - 1), outline=inner, width=max(3, profile // 5))
    opening = (profile, profile, fw - profile, fh - profile)
    d.rectangle(opening, fill=(247, 245, 239, 255))
    if paspartu:
        opening = tuple(v + (mat if i < 2 else -mat) for i, v in enumerate(opening))
    d.rectangle(opening, fill=(0, 0, 0, 0))
    d.rectangle(opening, outline=inner, width=max(3, profile // 9))
    return layer, opening


def render_frame(design: Image.Image, code: str, paspartu: bool, box: tuple[int, int, int, int]) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Bir cerceveyi verilen dis kutuya cizer; tasarim kutusunu da dondurur."""
    if code not in FRAME_NAMES:
        raise ValueError(f"bilinmeyen cerceve: {code}")
    x0, y0, x1, y1 = box
    layer, local = _frame_layer((x1 - x0, y1 - y0), code, paspartu)
    design_box = (x0 + local[0], y0 + local[1], x0 + local[2], y0 + local[3])
    dw, dh = design_box[2] - design_box[0], design_box[3] - design_box[1]
    if dw * 5 != dh * 4:
        # Kutuyu merkezden tam 4:5'e daralt; hicbir zaman girdi kirpilmaz.
        target_w = min(dw, dh * 4 // 5)
        target_h = target_w * 5 // 4
        cx, cy = (design_box[0] + design_box[2]) // 2, (design_box[1] + design_box[3]) // 2
        design_box = (cx - target_w // 2, cy - target_h // 2, cx - target_w // 2 + target_w, cy - target_h // 2 + target_h)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x0 + 20, y0 + 28, x1 + 30, y1 + 40), 12, fill=(25, 20, 15, 95))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(30)))
    canvas.alpha_composite(layer, (x0, y0))
    resized = design.resize((design_box[2] - design_box[0], design_box[3] - design_box[1]), RESAMPLE)
    canvas.paste(resized, design_box[:2])
    return canvas, design_box


def mean_absolute_difference(design: Image.Image, rendered: Image.Image, box: tuple[int, int, int, int]) -> float:
    expected = design.resize((box[2] - box[0], box[3] - box[1]), RESAMPLE)
    actual = rendered.crop(box).convert("RGB")
    return float(np.abs(np.asarray(expected, dtype=np.int16) - np.asarray(actual, dtype=np.int16)).mean())


def quality_gate(design: Image.Image, rendered: Image.Image, boxes: list[tuple[int, int, int, int]]) -> tuple[bool, str]:
    errors = [mean_absolute_difference(design, rendered, b) for b in boxes]
    same = len({(b[2] - b[0], b[3] - b[1]) for b in boxes}) == 1
    passed = rendered.size == (W, H) and same and all(e <= 3 for e in errors)
    return passed, f"boyut={rendered.size} alanlar_esit={same} MAD={','.join(f'{e:.3f}' for e in errors)}"


def brand_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = (Path("fonts/Montserrat[wght].ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise FileNotFoundError("Montserrat veya DejaVu Sans fontu bulunamadi")


def single_card(design: Image.Image, code: str, paspartu: bool) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
    global canvas
    canvas = wall().convert("RGBA")
    result, area = render_frame(design, code, paspartu, (360, 280, 1640, 2020))
    return result.convert("RGB"), [area]


def options_card(design: Image.Image, paspartu: bool) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
    global canvas
    canvas = wall().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    title_font, label_font = brand_font(82), brand_font(44)
    draw.text((W // 2, 115), "Framed options", font=title_font, fill=(45, 40, 35), anchor="ma")
    boxes: list[tuple[int, int, int, int]] = []
    for code, x in zip(("BK", "WH", "NA"), (90, 730, 1370)):
        _, area = render_frame(design, code, paspartu, (x, 450, x + 540, 1110))
        boxes.append(area)
        draw = ImageDraw.Draw(canvas)
        draw.text((x + 270, 1390), FRAME_NAMES[code], font=label_font, fill=(52, 47, 42), anchor="ma")
    return canvas.convert("RGB"), boxes


def save_checked(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    image.save(path, "JPEG", quality=92, subsampling=0, icc_profile=profile)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("girdi", type=Path)
    ap.add_argument("cikti", type=Path, help="cikti dizini")
    ap.add_argument("--cerceve", default="BK", help="BK, WH, NA veya virgul ayrimli liste")
    ap.add_argument("--paspartu", choices=("0", "1"), default="0")
    args = ap.parse_args()
    design = open_design(args.girdi)
    codes = [c.strip().upper() for c in args.cerceve.split(",") if c.strip()]
    if not codes or any(c not in FRAME_NAMES for c in codes):
        ap.error("--cerceve yalniz BK,WH,NA degerlerini kabul eder")
    paspartu = args.paspartu == "1"
    products = [(f"cerceve_{code}.jpg", *single_card(design, code, paspartu)) for code in codes]
    products.append(("framed_options.jpg", *options_card(design, paspartu)))
    for name, image, boxes in products:
        output = args.cikti / name
        save_checked(image, output)
        with Image.open(output) as saved:
            checked = saved.convert("RGB")
        passed, detail = quality_gate(design, checked, boxes)
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")
        if not passed:
            output.unlink(missing_ok=True)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
