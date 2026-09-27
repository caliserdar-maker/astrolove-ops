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
    "WH": ((243, 242, 238), (205, 203, 197)),
    "NA": ((201, 166, 118), (158, 121, 80)),
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


# Prodigi Classic frame (urun foyu, 27 Eyl 2026): yuz genisligi 20 mm, duvardan derinlik 22 mm,
# natural = mese efektli laminat. Olcek: 8x10 baski genisligi 203.2 mm.
YUZ_ORAN = 20.0 / 203.2


def _grain(w: int, h: int, base: tuple[int, int, int], seed: int = 7) -> Image.Image:
    """Mese efektli laminat: prosedurel ince damar (yalniz cerceve yuzeyi)."""
    rng = np.random.default_rng(seed)
    x = np.arange(w, dtype=np.float32)[None, :]
    y = np.arange(h, dtype=np.float32)[:, None]
    noise = rng.normal(0, 1, (h, 1)).astype(np.float32)
    noise = np.convolve(noise[:, 0], np.ones(9) / 9, mode="same")[:, None]
    wave = np.sin(y / 3.1 + 6 * noise + x / 400.0) * 7 + np.sin(y / 11.0 + x / 170.0) * 4
    arr = np.clip(np.array(base, dtype=np.float32)[None, None, :] + wave[..., None], 0, 255)
    return Image.fromarray(np.uint8(arr), "RGB")


def _face(w: int, h: int, code: str, horizontal: bool) -> Image.Image:
    outer, _ = FRAME_COLORS[code]
    if code == "NA":
        return _grain(w, h, outer) if horizontal else _grain(h, w, outer).rotate(90, expand=True)
    return Image.new("RGB", (w, h), outer)


def render_frame(design: Image.Image, code: str, paspartu: bool, box: tuple[int, int, int, int]) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """box = tasarimin (baskinin) yerlesecegi 4:5 alan. Cerceve bu alanin DISINA olcekli yuz genisligiyle cizilir."""
    if code not in FRAME_NAMES:
        raise ValueError(f"bilinmeyen cerceve: {code}")
    x0, y0, x1, y1 = box
    dw, dh = x1 - x0, y1 - y0
    if dw * 5 != dh * 4:
        raise ValueError(f"tasarim alani 4:5 degil: {dw}x{dh}")
    mat = round(dw * 0.12) if paspartu else 0
    f = max(8, round((dw + 2 * mat) * YUZ_ORAN))
    ox0, oy0, ox1, oy1 = x0 - mat - f, y0 - mat - f, x1 + mat + f, y1 + mat + f
    ow, oh = ox1 - ox0, oy1 - oy0
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    depth = max(6, round(f * 22 / 20 * 0.45))
    ImageDraw.Draw(shadow).rectangle((ox0 + depth // 2, oy0 + depth, ox1 + depth, oy1 + depth * 2), fill=(25, 20, 15, 105))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(depth * 1.6)))
    frame = Image.new("RGB", (ow, oh))
    top = _face(ow, f, code, True)
    side = _face(f, oh, code, False)
    frame.paste(side, (0, 0)); frame.paste(side.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (ow - f, 0))
    frame.paste(top, (0, 0)); frame.paste(top.transpose(Image.Transpose.FLIP_TOP_BOTTOM), (0, oh - f))
    d = ImageDraw.Draw(frame)
    # Gonye birlesimleri + isik: ust/sol acik, alt/sag koyu (tek isik kaynagi, sol ust)
    shade = Image.new("RGBA", (ow, oh), (0, 0, 0, 0)); sd = ImageDraw.Draw(shade)
    sd.polygon([(0, 0), (ow, 0), (ow - f, f), (f, f)], fill=(255, 255, 255, 26))
    sd.polygon([(0, 0), (f, f), (f, oh - f), (0, oh)], fill=(255, 255, 255, 12))
    sd.polygon([(0, oh), (f, oh - f), (ow - f, oh - f), (ow, oh)], fill=(0, 0, 0, 34))
    sd.polygon([(ow, 0), (ow, oh), (ow - f, oh - f), (ow - f, f)], fill=(0, 0, 0, 22))
    for pts in ([(0, 0), (f, f)], [(ow, 0), (ow - f, f)], [(0, oh), (f, oh - f)], [(ow, oh), (ow - f, oh - f)]):
        sd.line(pts, fill=(0, 0, 0, 40), width=2)
    sd.rectangle((0, 0, ow - 1, oh - 1), outline=(0, 0, 0, 60), width=2)
    sd.rectangle((f - 2, f - 2, ow - f + 1, oh - f + 1), outline=(0, 0, 0, 70), width=3)
    frame = Image.alpha_composite(frame.convert("RGBA"), shade)
    if paspartu:
        ImageDraw.Draw(frame).rectangle((f, f, ow - f - 1, oh - f - 1), fill=(246, 245, 241, 255))
    canvas.alpha_composite(frame, (ox0, oy0))
    canvas.paste(design.resize((dw, dh), RESAMPLE), (x0, y0))
    return canvas, (x0, y0, x1, y1)


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
    result, area = render_frame(design, code, paspartu, (480, 420, 1520, 1720))  # tasarim 1040x1300 (4:5)
    return result.convert("RGB"), [area]


def _unframed(design: Image.Image, size: tuple[int, int], center: tuple[int, int]) -> tuple[int, int, int, int]:
    """Cercevesiz baski: yalniz ince golge; tasarim olceklenir, kirpilmaz."""
    w, h = size
    x0, y0 = center[0] - w // 2, center[1] - h // 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((x0 + 10, y0 + 16, x0 + w + 14, y0 + h + 22), fill=(25, 20, 15, 70))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    canvas.paste(design.resize((w, h), RESAMPLE), (x0, y0))
    return (x0, y0, x0 + w, y0 + h)


def options_card(design: Image.Image, paspartu: bool) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
    """2x2: Print only, Black, White, Natural. Tum tasarim alanlari ayni boyutta."""
    global canvas
    canvas = wall().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    title_font, label_font, note_font = brand_font(84), brand_font(50), brand_font(40)
    draw.text((W // 2, 95), "Choose your format", font=title_font, fill=(45, 40, 35), anchor="ma")
    dw, dh = 600, 750
    cells = [(505, 330), (1495, 330), (505, 1360), (1495, 1360)]  # tasarim alani ust-orta
    boxes: list[tuple[int, int, int, int]] = []
    boxes.append(_unframed(design, (dw, dh), (cells[0][0], cells[0][1] + dh // 2)))
    for code, (cx, top) in zip(("BK", "WH", "NA"), cells[1:]):
        _, area = render_frame(design, code, paspartu, (cx - dw // 2, top, cx + dw // 2, top + dh))
        boxes.append(area)
    fh = dh + round(dw * YUZ_ORAN) + 25  # etiket cerceve altindan 55 px asagida
    draw = ImageDraw.Draw(canvas)
    for label, (cx, top) in zip(("Print only", "Black Frame", "White Frame", "Natural Frame"), cells):
        draw.text((cx, top + fh + 30), label, font=label_font, fill=(52, 47, 42), anchor="ma")
    draw.text((W // 2, 2400), "Also available as a Digital File", font=note_font, fill=(95, 88, 80), anchor="ma")
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
