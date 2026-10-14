"""Bizim Yilimiz 8x10 poster (production, 78 pairs). Env: BY_ROOT, PAIR (e.g. CANCER_LIBRA), NAME1 (left = first sign), NAME2, DATE, OUT.
Bizim Yilimiz v3: v2 + full-resolution sources.
- Symbols from the ORIGINAL high-res sources (main 8185 px alpha, sign glyph sheets), area-downscaled.
- Gold texture tiled at native resolution (no 3x stretch); sparkle/dividers supersampled.
- JPEG 4:4:4, q97. All pixel parameters scale with SCALE.
- Gold styles: symbols AND all text in gold foil (texture + bevel + shadow/glow).
- Ink styles: ink takes the paper texture (grain shows through) + light letterpress.
- Fonts harmonised: classic serif families only (Cinzel, EB Garamond, Cormorant),
  sans only in Layers (as in the concept). Kerning via raqm.
Backgrounds + positions: ChatGPT (Olculer.json). Symbols: ORIGINAL masks.
"""
import glob
import json
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

Image.MAX_IMAGE_PIXELS = None  # main symbol sources are up to ~12000 px (our own files)

SCALE = int(os.environ.get("SCALE", "1"))
W, H = 2400 * SCALE, 3000 * SCALE
ROOT = os.environ.get("BY_ROOT", "/home/claude/by78")
KAY = f"{ROOT}/kaynak"
PAIR = os.environ.get("PAIR", "CANCER_LIBRA").upper()
N1 = os.environ.get("NAME1", "SERDAR")
N2 = os.environ.get("NAME2", "LENA")
DATE = os.environ.get("DATE", "12 JUNE 2025")
# Siparis yolu (14 Eki 2026): HEADING = ust satir ("Paper Anniversary" varsayilan / "Our First Year"); yazi boyu HER ZAMAN
# "Paper Anniversary" icin olculen boy (kisa baslik genislige gore BUYUMEZ). LINE = kisa satir (varsayilan "YEAR ONE"; boyu
# "YEAR ONE" ornek genisliginden, yalniz tasarsa kuculur; by_kart.small_line ile ayni kural). STYLE = tek stil (1..5 ya da ad).
HEADING = os.environ.get("HEADING", "Paper Anniversary").strip()
if HEADING not in ("Paper Anniversary", "Our First Year"):
    raise SystemExit(f"HATA: HEADING yalniz 'Paper Anniversary' ya da 'Our First Year' olabilir: {HEADING!r}")
LINE = os.environ.get("LINE", "YEAR ONE").strip() or "YEAR ONE"
STYLE = os.environ.get("STYLE", "").strip()
Z = f"{ROOT}/z"
F = f"{ROOT}/fonts"
OUT = os.environ.get("OUT", f"{ROOT}/cikti/{PAIR}/poster")
MEAS = {d["name"]: d for d in json.load(open(f"{Z}/Olculer.json"))["designs"]}
CINZEL = f"{F}/Cinzel.ttf"
EBG_I = f"{F}/EBGaramond-Italic.ttf"


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def fs(family, weight=400, style="normal"):
    """Return a font factory: size -> ImageFont."""
    if family == "Cinzel":
        def f(size):
            ft = ImageFont.truetype(CINZEL, size, layout_engine=ImageFont.Layout.RAQM)
            ft.set_variation_by_axes([weight])
            return ft
        return f
    if family == "EBGaramondItalic":
        return lambda size: ImageFont.truetype(EBG_I, size, layout_engine=ImageFont.Layout.RAQM)
    fam = {"Cormorant": "cormorant-garamond", "Montserrat": "montserrat",
           "DMSerif": "dm-serif-display"}[family]
    path = f"{F}/{fam}-latin-{weight}-{style}.woff"
    return lambda size: ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)


def load_src(path, box=None):
    m = Image.open(path).convert("L")
    if box:
        m = m.crop(box)
    a = np.array(m)
    ys, xs = np.where(a > 8)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


# small sign glyphs: same sheets and boxes as the live motor (motor_gpt/olustur_alfa_sablon.py KUCUK)
KUCUK = {"AQUARIUS": ("KUCUK_1", [1095, 219, 2010, 600]), "ARIES": ("KUCUK_1", [2257, 102, 2917, 717]),
         "CANCER": ("KUCUK_1", [175, 933, 859, 1527]), "CAPRICORN": ("KUCUK_1", [1200, 880, 1905, 1580]),
         "GEMINI": ("KUCUK_1", [2285, 923, 2889, 1537]), "LEO": ("KUCUK_1", [254, 1743, 781, 2357]),
         "LIBRA": ("KUCUK_2", [1001, 94, 1822, 709]), "PISCES": ("KUCUK_2", [2023, 95, 2682, 708]),
         "SAGITTARIUS": ("KUCUK_2", [217, 875, 723, 1533]), "SCORPIO": ("KUCUK_2", [1038, 897, 1784, 1512]),
         "TAURUS": ("KUCUK_2", [2045, 898, 2659, 1510]), "VIRGO": ("KUCUK_2", [130, 1666, 811, 2349])}
S1, S2 = PAIR.split("_")


def sign_mask(sign):
    sheet, box = KUCUK[sign]
    return load_src(f"{KAY}/{sheet}.png", tuple(box))


MASKS = {"hero": load_src(f"{KAY}/ana/{PAIR.lower()}_alfa.png"), "left": sign_mask(S1), "right": sign_mask(S2)}


def P(v):
    """pixel parameter at the current scale"""
    return v * SCALE


# ---------------- text mask ----------------
def text_mask(s, font, tracking):
    pad = 60
    if tracking == 0:
        bb = font.getbbox(s)
        m = Image.new("L", (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), 0)
        ImageDraw.Draw(m).text((pad - bb[0], pad - bb[1]), s, font=font, fill=255)
    else:
        widths = [font.getlength(c) for c in s]
        total = sum(widths) + tracking * (len(s) - 1)
        asc, desc = font.getmetrics()
        m = Image.new("L", (int(total) + 2 * pad, asc + desc + 2 * pad), 0)
        d = ImageDraw.Draw(m)
        x = pad
        for c, w in zip(s, widths):
            d.text((x, pad), c, font=font, fill=255)
            x += w + tracking
    return m.crop(m.getbbox())


def fit_text(s, factory, tracking_pct, target, by):
    track = tracking_pct / 100 * W
    size = 200
    for _ in range(4):
        m = text_mask(s, factory(size), track)
        cur = m.height if by == "h" else m.width
        size = max(8, round(size * target / cur))
    return text_mask(s, factory(size), track)


# ---------------- materials ----------------
def full_mask(m, cx, cy):
    """Place a small mask onto a full-canvas L image centred at (cx, cy)."""
    canvas = Image.new("L", (W, H), 0)
    canvas.paste(m, (round(cx - m.width / 2), round(cy - m.height / 2)))
    return canvas


def gold_layer(tex, k=1.0):
    t = np.array(Image.open(tex).convert("RGB"))
    if SCALE > 1:
        t = cv2.resize(t, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)
    tile = np.concatenate([np.concatenate([t, t[:, ::-1]], 1), np.concatenate([t[::-1], t[::-1, ::-1]], 1)], 0)
    reps = (H // tile.shape[0] + 1, W // tile.shape[1] + 1, 1)
    a = np.tile(tile, reps)[:H, :W].astype(np.float32)
    # keep the fine metal grain crisp, even out large bright/dark patches so every element has the same gold
    low = cv2.GaussianBlur(a, (0, 0), P(60)) + 1e-3
    mean = a.reshape(-1, 3).mean(0)
    a = np.clip(a / low, 0.6, 1.6) * (0.75 * mean + 0.25 * low) * np.array(k if isinstance(k, tuple) else (k, k, k), np.float32)
    return np.clip(a, 0, 255)


def apply_gold(bg, mask, gold, shadow_col, shadow_op, glow=None, bevel=18):
    a = np.array(mask).astype(np.float32) / 255
    if a.max() == 0:
        return bg
    # drop shadow
    sh = cv2.GaussianBlur(np.roll(np.roll(a, P(5), 0), P(4), 1), (0, 0), P(7)) * shadow_op
    base = np.array(bg).astype(np.float32)
    sc = np.array(hexrgb(shadow_col), np.float32)
    base = base * (1 - sh[..., None]) + sc * sh[..., None]
    if glow:
        gcol, gop, grad = glow
        g = cv2.GaussianBlur(a, (0, 0), P(grad)) * gop
        base = base * (1 - g[..., None]) + np.array(hexrgb(gcol), np.float32) * g[..., None]
    # bevel lighting on the gold
    blur = cv2.GaussianBlur(a, (0, 0), P(2.2))
    gy, gx = np.gradient(blur)
    light = np.clip(-(gx + gy) * bevel * SCALE, -0.45, 0.45)
    spec = np.clip(light, 0, None) ** 1.5 * 0.9
    g = gold * (1 + light[..., None]) + 255 * spec[..., None] * 0.35
    g = np.clip(g, 0, 255)
    out = base * (1 - a[..., None]) + g * a[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def apply_ink(bg, mask, color, press=True, density=0.93):
    a = np.array(mask).astype(np.float32) / 255
    base = np.array(bg).astype(np.float32)
    lum = base.mean(axis=2)
    local = cv2.GaussianBlur(lum, (0, 0), P(25)) + 1e-3
    grain = np.clip(lum / local, 0.75, 1.25)          # paper grain
    col = np.array(hexrgb(color), np.float32)
    ink = col[None, None, :] * (grain[..., None] ** 1.6)
    # uneven absorption
    rng = np.random.default_rng(11)
    n = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), P(3))
    alpha = a * np.clip(density + n * 0.05, 0.80, 1.0)
    if press:
        # letterpress: light rim below-right, slightly darker ink edge top-left
        rim = cv2.GaussianBlur(np.roll(np.roll(a, P(3), 0), P(2), 1), (0, 0), P(2.0)) * (1 - a)
        base = base + rim[..., None] * 18
        edge = cv2.GaussianBlur(np.roll(np.roll(a, -P(2), 0), -P(2), 1), (0, 0), P(1.5))
        ink = ink * (1 - 0.10 * (a - edge).clip(0, 1)[..., None])
    out = base * (1 - alpha[..., None]) + ink * alpha[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def apply_papercut(bg, mask, color, lift=7):
    a = np.array(mask).astype(np.float32) / 255
    base = np.array(bg).astype(np.float32)
    sh = cv2.GaussianBlur(np.roll(np.roll(a, P(lift), 0), P(lift - 2), 1), (0, 0), P(6)) * 0.38
    base = base * (1 - sh[..., None]) + np.array([90, 40, 25], np.float32) * sh[..., None]
    lum = np.array(bg).astype(np.float32).mean(axis=2)
    grain = np.clip(lum / (cv2.GaussianBlur(lum, (0, 0), P(25)) + 1e-3), 0.85, 1.15)
    col = np.array(hexrgb(color), np.float32)[None, None, :] * grain[..., None] ** 1.2
    blur = cv2.GaussianBlur(a, (0, 0), P(1.6))
    gy, gx = np.gradient(blur)
    light = np.clip(-(gx + gy) * 10 * SCALE, -0.25, 0.25)
    col = np.clip(col * (1 + light[..., None]), 0, 255)
    out = base * (1 - a[..., None]) + col * a[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


YER = json.load(open(f"{KAY}/yerlesim78.json"))
REF_W = {k: v["u1"] - v["u0"] for k, v in YER.items()}
GLYPH_REF = {"CANCER": load_src(f"{KAY}/KUCUK_1.png", tuple(KUCUK["CANCER"][1])).shape[1],
             "LIBRA": load_src(f"{KAY}/KUCUK_2.png", tuple(KUCUK["LIBRA"][1])).shape[1]}


def place(mask, s, el):
    m = Image.fromarray(cv2.resize(mask, (max(1, round(mask.shape[1] * s)), max(1, round(mask.shape[0] * s))),
                                   interpolation=cv2.INTER_AREA))
    return full_mask(m, el["center_x"] / 100 * W, el["center_y"] / 100 * H)


def hero_mask(el):
    """Layout boxes were measured on CANCER_LIBRA. Other pairs keep the relative size of the
    78 live posters (yerlesim78.json ana box width), clamped so tall/wide symbols stay in the design."""
    mask = MASKS["hero"]
    tw = el["width"] / 100 * W * REF_W[PAIR] / REF_W["CANCER_LIBRA"]
    s = tw / mask.shape[1]
    s = min(s, el["visible_height"] / 100 * H * 1.10 / mask.shape[0], el["width"] / 100 * W * 1.3 / mask.shape[1])
    return place(mask, s, el)


def signs_mask(el_l, el_r):
    """small glyphs share ONE pixel scale (as in the motor), taken from the measured Cancer/Libra widths"""
    s = (el_l["width"] / 100 * W / GLYPH_REF["CANCER"] + el_r["width"] / 100 * W / GLYPH_REF["LIBRA"]) / 2
    return union(place(MASKS["left"], s, el_l), place(MASKS["right"], s, el_r))


def symbol_mask(el):
    raise RuntimeError("use hero_mask / signs_mask")


def fit_size(s, factory, tracking_pct, target, by):
    """fit_text ile ayni dongu; yalniz puntoyu dondurur"""
    track = tracking_pct / 100 * W
    size = 200
    for _ in range(4):
        m = text_mask(s, factory(size), track)
        cur = m.height if by == "h" else m.width
        size = max(8, round(size * target / cur))
    return size


def same_size_full(s, ref, factory, tracking_pct, el, by, target=None, max_w=None):
    """s metnini, ref metninin el kutusunda alacagi puntoyla ciz (kisa metin BUYUMEZ); ust cizgisi ref ile ayni.
    s == ref ise text_full ile birebir ayni sonuc. max_w: tasarsa yalniz kuculur (piksel)."""
    if s == ref:
        return text_full(ref, factory, tracking_pct, el, by, target)
    if target is None:
        target = (el["visible_height"] / 100 * H) if by == "h" else (el["width"] / 100 * W)
    size = fit_size(ref, factory, tracking_pct, target, by)
    track = tracking_pct / 100 * W
    mr = text_mask(ref, factory(size), track)
    m = text_mask(s, factory(size), track)
    lim = max_w if max_w is not None else target
    if by == "w" and m.width > lim:
        size = int(size * lim / m.width)
        m = text_mask(s, factory(size), track)
    cx, cy = el["center_x"] / 100 * W, el["center_y"] / 100 * H
    top = cy - mr.height / 2                                   # ref'in ust cizgisi (buyuk harf tepesi) korunur
    return full_mask(m, cx, top + m.height / 2)


def text_full(s, factory, tracking_pct, el, by, target=None):
    if target is None:
        target = (el["visible_height"] / 100 * H) if by == "h" else (el["width"] / 100 * W)
    m = fit_text(s, factory, tracking_pct, target, by)
    return full_mask(m, el["center_x"] / 100 * W, el["center_y"] / 100 * H)


def line_mask(s, font, track):
    """text drawn on a baseline; returns (mask, baseline_y_in_mask)"""
    pad = 80
    asc, desc = font.getmetrics()
    widths = [font.getlength(c) for c in s] if track else [font.getlength(s)]
    total = (sum(widths) + track * (len(s) - 1)) if track else widths[0]
    m = Image.new("L", (int(total) + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(m)
    base = pad + asc
    if track:
        x = pad
        for c, w in zip(s, widths):
            d.text((x, base), c, font=font, fill=255, anchor="ls")
            x += w + track
    else:
        d.text((pad, base), s, font=font, fill=255, anchor="ls")
    bb = m.getbbox()
    return m.crop((bb[0], 0, bb[2], m.height)), base


def names_full(n1, n2, factory, tracking_pct, e1, e2, target_h=None, max_w=0.30):
    """both names: SAME font size from cap height (descenders like J ignored), SAME baseline;
    shrink both together if one is too wide"""
    track = tracking_pct / 100 * W
    th = target_h if target_h is not None else max(e1["visible_height"], e2["visible_height"]) / 100 * H
    size = 200
    for _ in range(4):
        cap = text_mask("HEMN", factory(size), 0).height
        size = max(8, round(size * th / cap))
    for _ in range(6):
        wmax = max(line_mask(n, factory(size), track)[0].width for n in (n1, n2))
        if wmax <= max_w * W:
            break
        size = max(8, int(size * max_w * W / wmax))
    cap = text_mask("HEMN", factory(size), 0).height
    cy = (e1["center_y"] + e2["center_y"]) / 2 / 100 * H
    baseline = cy + cap / 2
    out = Image.new("L", (W, H), 0)
    for n, e in ((n1, e1), (n2, e2)):
        m, b = line_mask(n, factory(size), track)
        out.paste(m, (round(e["center_x"] / 100 * W - m.width / 2), round(baseline - b)))
    return out


SS = 4


def sparkle_mask(cx, cy, w, h):
    """drawn 4x larger in a local box, area-downscaled (crisp, antialiased)"""
    bw, bh = int(w) + 8, int(h) + 8
    m = Image.new("L", (bw * SS, bh * SS), 0)
    d = ImageDraw.Draw(m)
    k = 0.11
    X, Y = bw * SS / 2, bh * SS / 2
    w, h = w * SS, h * SS
    d.polygon([(X, Y - h / 2), (X + w * k, Y), (X, Y + h / 2), (X - w * k, Y)], fill=255)
    d.polygon([(X - w / 2, Y), (X, Y - h * k * 0.7), (X + w / 2, Y), (X, Y + h * k * 0.7)], fill=255)
    m = m.resize((bw, bh), Image.BOX)
    return full_mask(m, cx, cy)


def divider_mask(dv):
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    y = dv["rule_center_y"] / 100 * H
    t = max(P(3), dv["rule_thickness_percent_height"] / 100 * H)
    for x0, x1 in dv["rule_x_ranges"]:
        # same straight rule as the concept, drawn 4x and downscaled (crisp edges)
        L = (x1 - x0) / 100 * W
        big = Image.new("L", (int(L * SS) + 8, int(t * SS) + 8), 0)
        bd = ImageDraw.Draw(big)
        cy_ = big.height / 2
        bd.rectangle([4, cy_ - t * SS / 2, L * SS + 4, cy_ + t * SS / 2], fill=255)
        sm = big.resize((max(1, big.width // SS), max(1, big.height // SS)), Image.BOX)
        m.paste(sm, (round(x0 / 100 * W), round(y - sm.height / 2)))
    m = ImageChops.lighter(m, sparkle_mask(dv["star_center_x"] / 100 * W, dv["star_center_y"] / 100 * H,
                                           dv["star_width"] / 100 * W, dv["star_height"] / 100 * H * 0.55))
    return m


def union(*ms):
    out = ms[0]
    for m in ms[1:]:
        out = ImageChops.lighter(out, m)
    return out


# ---------------- styles ----------------
def select_styles(all_styles):
    """STYLE bos = 5 stil; '3', '3_FirstPage', 'FirstPage' ya da 'first page' = tek stil"""
    if not STYLE:
        return all_styles
    k = STYLE.lower().replace(" ", "").replace("_", "")
    sel = [(n, f) for n, f in all_styles if k in (n[0], n.lower().replace("_", ""), n.split("_", 1)[1].lower())]
    if len(sel) != 1:
        raise SystemExit(f"HATA: STYLE taninmadi: {STYLE!r} (1..5, 1_Starlit, Starlit ...)")
    return sel



def els(name):
    return {e["element"]: e for e in MEAS[name]["elements"]}


def bgimg(name):
    im = Image.open(f"{Z}/Baski_2400x3000_Buyutulmus/{name}_8x10_300ppi.png").convert("RGB")
    return im if SCALE == 1 else im.resize((W, H), Image.LANCZOS)


def gold_style(name, tex, k, shadow, shadow_op, glow, names_font, title_font, small_font,
               t_names=3.4, t_title_w=None, t_date_w=None, t_year_w=None, bevel=18):
    e = els(name)
    bg = bgimg(name)
    gold = gold_layer(tex, k)
    sym = union(hero_mask(e["hero"]), signs_mask(e["left"], e["right"]))
    txt = union(
        names_full(N1, N2, names_font, 0.35, e["SERDAR"], e["LENA"], t_names / 100 * H),
        same_size_full(HEADING, "Paper Anniversary", title_font, 0, e["Paper Anniversary"], "w", t_title_w),
        text_full(DATE, small_font, 0.55, e["12 JUNE 2025"], "w", t_date_w),
        same_size_full(LINE, "YEAR ONE", small_font, 0.75, e["YEAR ONE"], "w", t_year_w, max_w=0.70 * W),
        divider_mask(MEAS[name]["removed_dividers"]),
    )
    bg = apply_gold(bg, sym, gold, shadow, shadow_op, glow, bevel=bevel)
    bg = apply_gold(bg, txt, gold, shadow, shadow_op * 0.7, glow, bevel=bevel * 0.55)
    return bg


def starlit():
    return gold_style("1_Starlit", f"{Z}/Altin_1024x1024/1_Starlit_Altin_1024.png", 1.0,
                      "#00040F", 0.55, ("#E0A64A", 0.16, 14),
                      fs("Cinzel", 500), fs("EBGaramondItalic"), fs("Cinzel", 500),
                      t_names=3.3, t_title_w=0.40 * W, t_date_w=0.27 * W, t_year_w=0.17 * W)


def timeless():
    return gold_style("2_Timeless", f"{Z}/Altin_1024x1024/2_Timeless_Altin_1024.png", (0.80, 0.73, 0.68),
                      "#5A4220", 0.30, None,
                      fs("Cinzel", 500), fs("EBGaramondItalic"), fs("Cinzel", 500),
                      t_names=3.2, t_title_w=0.42 * W, t_date_w=0.27 * W, t_year_w=0.17 * W, bevel=11)


def ink_style(name, color_sym, color_small, color_txt, color_sub, title_f, names_f, small_f,
              title_by="w", extra=None):
    e = els(name)
    bg = bgimg(name)
    bg = apply_ink(bg, hero_mask(e["hero"]), color_sym)
    bg = apply_ink(bg, signs_mask(e["left"], e["right"]), color_small)
    t = same_size_full(HEADING, "Paper Anniversary", title_f, -0.03, e["Paper Anniversary"], title_by)
    n = names_full(N1, N2, names_f, 0.25, e["SERDAR"], e["LENA"])
    bg = apply_ink(bg, union(t, n), color_txt)
    sub = union(text_full(DATE, small_f, 0.55, e["12 JUNE 2025"], "w", 0.30 * W),
                same_size_full(LINE, "YEAR ONE", small_f, 0.75, e["YEAR ONE"], "w", 0.20 * W, max_w=0.70 * W))
    bg = apply_ink(bg, sub, color_sub, press=False)
    return bg


def first_page():
    return ink_style("3_FirstPage", "#702431", "#702431", "#6C1F2C", "#6C1F2C",
                     fs("Cormorant", 600, "italic"), fs("Cormorant", 700), fs("Cinzel", 500))


def botanical():
    return ink_style("5_Botanical", "#1F3B2D", "#1F3B2D", "#1B372A", "#1F3B2D",
                     fs("Cormorant", 600), fs("Cormorant", 700), fs("Cinzel", 500))


def layers():
    name = "4_Layers"
    e = els(name)
    bg = bgimg(name)
    bg = apply_papercut(bg, hero_mask(e["hero"]), "#A84A2C", lift=7)
    bg = apply_ink(bg, signs_mask(e["left"], e["right"]), "#6E3A24")
    # iki satir: 1. kelime "Paper" kutusunda, kalan kelimeler "Anniversary" kutusunda; puntolar Paper/Anniversary ile ayni
    w1, w2 = (HEADING.split(" ", 1) + [""])[:2] if HEADING != "Paper Anniversary" else ("Paper", "Anniversary")
    title = union(same_size_full(w1, "Paper", fs("DMSerif"), -0.10, e["Paper"], "w", max_w=0.86 * W),
                  same_size_full(w2, "Anniversary", fs("DMSerif"), -0.15, e["Anniversary"], "w", max_w=0.86 * W))
    bg = apply_papercut(bg, title, "#A34729", lift=5)
    names = names_full(N1, N2, fs("Montserrat", 600), 0.35, e["SERDAR"], e["LENA"])
    sub = union(same_size_full(LINE, "YEAR ONE", fs("Montserrat", 600), 0.65, e["YEAR ONE"], "w", max_w=0.46 * W),  # kemerin ici dar
                text_full(DATE, fs("Montserrat", 600), 0.40, e["12 JUNE 2025"], "w"))
    bg = apply_ink(bg, union(names, sub), "#592319")
    return bg


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    ims = []
    for n, fn in select_styles([("1_Starlit", starlit), ("2_Timeless", timeless), ("3_FirstPage", first_page),
                                ("4_Layers", layers), ("5_Botanical", botanical)]):
        im = fn()
        im.save(f"{OUT}/{n}_8x10.jpg", quality=97, subsampling=0, dpi=(300, 300))
        ims.append(im)
        print(n)
    if len(ims) < 5:
        raise SystemExit(0)                                    # tek stil (siparis): yan yana sayfa yok
    small = [i.resize((720, 900), Image.LANCZOS) for i in ims]
    sheet = Image.new("RGB", (720 * 5 + 20 * 6, 940), (236, 236, 236))
    for k, i in enumerate(small):
        sheet.paste(i, (20 + k * 740, 20))
    sheet.save(f"{OUT}/STIL5_v3_YANYANA.jpg", quality=90)
