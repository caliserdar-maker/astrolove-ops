"""Bizim Yilimiz 5x7 card (production, 78 pairs). Env: BY_ROOT, PAIR, NAME1, NAME2, DATE, LINE, OUT.
Bizim Yilimiz 5x7 card (1500x2100, 300 dpi).
Backgrounds + layout: ChatGPT card package (B_Bos_Zeminler, Olculer_5x7.json).
Symbols, materials and fonts: same as the 8x10 posters (render_v3.py), so card and poster match.
Usage: NAME1=EMMA NAME2=JAMES DATE="14 JUNE 2025" LINE="YEAR ONE" OUT=dir python3 render_card.py
"""
import os
import sys
import json
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import by_poster as rv  # noqa: E402

CW, CH = 1500, 2100
rv.W, rv.H = CW, CH                     # all material/text helpers use these globals
PK = f"{rv.ROOT}/kart"
OUT = os.environ.get("OUT", f"{rv.ROOT}/cikti/{rv.PAIR}/kart")
N1, N2 = os.environ.get("NAME1", "EMMA"), os.environ.get("NAME2", "JAMES")
DATE = os.environ.get("DATE", "14 JUNE 2025")
LINE = os.environ.get("LINE", "YEAR ONE").strip() or "YEAR ONE"   # bos LINE posterdeki gibi "YEAR ONE" (14 Eki, Serdar)
MEAS = {d["name"]: d for d in json.load(open(f"{PK}/Olculer_5x7.json"))["designs"]}
fs = rv.fs


def E(name):
    return {e["element"]: e for e in MEAS[name]["elements"]}


def bg(name):
    return Image.open(f"{PK}/B_Bos_Zeminler/B_{name}_5x7.png").convert("RGB")


def fit_size(s, factory, track_pct, target_w):
    size = 120
    for _ in range(5):
        m = rv.text_mask(s, factory(size), track_pct / 100 * CW)
        size = max(8, round(size * target_w / m.width))
    return size


def at(s, factory, size, track_pct, el):
    m = rv.text_mask(s, factory(size), track_pct / 100 * CW)
    return rv.full_mask(m, el["center_x"] / 100 * CW, el["center_y"] / 100 * CH)


def heading(e, factory, track=0):
    """'Happy First' / 'Anniversary' share one size (fitted on the wider JSON line)"""
    s1 = fit_size("Happy First", factory, track, e["Happy First"]["width"] / 100 * CW)
    s2 = fit_size("Anniversary", factory, track, e["Anniversary"]["width"] / 100 * CW)
    s = min(s1, s2)
    return rv.union(at("Happy First", factory, s, track, e["Happy First"]),
                    at("Anniversary", factory, s, track, e["Anniversary"]))


def small_line(text, factory, track, el, ref, max_w_pct=None):
    """date / short line: size from the sample text width, shrink only if a long custom line overflows"""
    size = fit_size(ref, factory, track, el["width"] / 100 * CW)
    m = rv.text_mask(text, factory(size), track / 100 * CW)
    lim = (max_w_pct if max_w_pct is not None else el.get("max_width", 70)) / 100 * CW
    if m.width > lim:
        size = int(size * lim / m.width)
    return at(text, factory, size, track, el)


def names(e, factory, track):
    return rv.names_full(N1, N2, factory, track, e["EMMA"], e["JAMES"],
                         target_h=e["EMMA"]["visible_height"] / 100 * CH, max_w=0.28)


def strong(mask):
    """small card text (date, short line) prints at only ~3 mm cap height: solid, slightly bolder ink so it does not look faint"""
    return mask.point(lambda v: min(255, int(v * 1.3)))


def scaled(el, k):
    """same element, k times wider target (only the card date/line, which ChatGPT measured very small)"""
    d = dict(el)
    d["width"] = el["width"] * k
    return d


def symbols(e):
    return rv.hero_mask(e["hero"]), rv.signs_mask(e["left"], e["right"])


def gold_card(name, tex, k, shadow, shadow_op, glow, bevel):
    e = E(name)
    b = bg(name)
    gold = rv.gold_layer(tex, k)
    hero, small = symbols(e)
    sym = rv.union(hero, small)
    txt = rv.union(
        names(e, fs("Cinzel", 500), 0.35),
        heading(e, fs("EBGaramondItalic")),
        small_line(DATE, fs("Cinzel", 500), 0.55, e["14 JUNE 2025"], "14 JUNE 2025"),
        small_line(LINE, fs("Cinzel", 500), 0.75, e["YEAR ONE"], "YEAR ONE"),
        rv.divider_mask(MEAS[name]["removed_dividers"]),
    )
    b = rv.apply_gold(b, sym, gold, shadow, shadow_op, glow, bevel=bevel)
    b = rv.apply_gold(b, txt, gold, shadow, shadow_op * 0.7, glow, bevel=bevel * 0.55)
    return b


def starlit():
    return gold_card("1_Starlit", f"{rv.Z}/Altin_1024x1024/1_Starlit_Altin_1024.png", 1.0,
                     "#00040F", 0.55, ("#E0A64A", 0.16, 14), 18)


def timeless():
    return gold_card("2_Timeless", f"{rv.Z}/Altin_1024x1024/2_Timeless_Altin_1024.png", (0.80, 0.73, 0.68),
                     "#5A4220", 0.30, None, 11)


def ink_card(name, c_sym, c_txt, c_sub, head_f, name_f):
    e = E(name)
    b = bg(name)
    hero, small = symbols(e)
    b = rv.apply_ink(b, hero, c_sym)
    b = rv.apply_ink(b, small, c_sym)
    b = rv.apply_ink(b, rv.union(heading(e, head_f, -0.03), names(e, name_f, 0.25)), c_txt)
    sub = rv.union(small_line(DATE, fs("Cinzel", 500), 0.55, scaled(e["14 JUNE 2025"], 1.1), "14 JUNE 2025"),
                   small_line(LINE, fs("Cinzel", 500), 0.75, e["YEAR ONE"], "YEAR ONE"))
    return rv.apply_ink(b, strong(sub), c_sub, press=False, density=1.0)


def first_page():
    return ink_card("3_FirstPage", "#702431", "#6C1F2C", "#6C1F2C",
                    fs("Cormorant", 600, "italic"), fs("Cormorant", 700))


def botanical():
    return ink_card("5_Botanical", "#1F3B2D", "#1B372A", "#1F3B2D",
                    fs("Cormorant", 600), fs("Cormorant", 700))


def layers():
    name = "4_Layers"
    e = E(name)
    b = bg(name)
    hero, small = symbols(e)
    b = rv.apply_papercut(b, hero, "#A84A2C", lift=6)
    b = rv.apply_ink(b, small, "#6E3A24")
    b = rv.apply_papercut(b, heading(e, fs("DMSerif"), -0.10), "#A34729", lift=4)
    ms = fs("Montserrat", 600)
    b = rv.apply_ink(b, names(e, ms, 0.35), "#592319")
    sub = rv.union(small_line(LINE, ms, 0.65, e["YEAR ONE"], "YEAR ONE", max_w_pct=37),  # ic kemerin ust genisligi ~%41 (olculdu)
                   small_line(DATE, ms, 0.40, scaled(e["14 JUNE 2025"], 1.15), "14 JUNE 2025"))
    return rv.apply_ink(b, strong(sub), "#592319", press=False, density=1.0)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    ims = []
    # STYLE (14 Eki 2026, siparis yolu): by_poster.select_styles ile ayni; kart basligi HER ZAMAN "Happy First Anniversary" (HEADING kullanilmaz)
    for n, fn in rv.select_styles([("1_Starlit", starlit), ("2_Timeless", timeless), ("3_FirstPage", first_page),
                                   ("4_Layers", layers), ("5_Botanical", botanical)]):
        im = fn()
        im.save(f"{OUT}/{n}_5x7.jpg", quality=97, subsampling=0, dpi=(300, 300))
        ims.append(im)
        print(n)
    if len(ims) < 5:
        raise SystemExit(0)                                    # tek stil (siparis): yan yana sayfa yok
    th = [i.resize((500, 700), Image.LANCZOS) for i in ims]
    sheet = Image.new("RGB", (5 * 500 + 6 * 15, 730), (236, 236, 236))
    for k, t in enumerate(th):
        sheet.paste(t, (15 + k * 515, 15))
    sheet.save(f"{OUT}/KART5_YANYANA.jpg", quality=90)
