"""Bizim Yilimiz Etsy gallery (10 images, 3200x2400) for one pair.
Needs posters (by_poster.py) and the First Page card (by_kart.py) of the same pair with example names EMMA / JAMES.
Env: BY_ROOT, PAIR. Output: <ROOT>/cikti/<PAIR>/galeri/*.jpg
"""
import os, sys, json, shutil
import numpy as np, cv2
from PIL import Image, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import by_poster as bp                     # noqa: E402  (masks of PAIR)
from by_galeri_render import render        # noqa: E402

ROOT, PAIR = bp.ROOT, bp.PAIR
A, B = (s.capitalize() for s in PAIR.split("_"))
SRC = f"{ROOT}/cikti/{PAIR}"
WORK = f"{SRC}/galeri_kaynak"
POSTERS = {"Poster_Stil1_Starlit_EMMA_JAMES.jpg": "1_Starlit", "Poster_Stil2_Timeless_EMMA_JAMES.jpg": "2_Timeless",
           "Poster_Stil3_FirstPage_EMMA_JAMES.jpg": "3_FirstPage", "Poster_Stil4_Layers_EMMA_JAMES.jpg": "4_Layers",
           "Poster_Stil5_Botanical_EMMA_JAMES.jpg": "5_Botanical"}


def sym_png(mask, h, path):
    s = h / mask.shape[0]
    a = cv2.resize(mask, (round(mask.shape[1] * s), h), interpolation=cv2.INTER_AREA)
    rgba = np.zeros((h, a.shape[1], 4), np.uint8)
    rgba[..., :3] = (40, 30, 30)
    rgba[..., 3] = a
    Image.fromarray(rgba).save(path)


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(f"{WORK}/source_assets")
    for d in ("B_Clean_Backgrounds", "fonts"):
        os.symlink(f"{ROOT}/galeri/{d}", f"{WORK}/{d}")
    for name, style in POSTERS.items():
        shutil.copy(f"{SRC}/poster/{style}_8x10.jpg", f"{WORK}/source_assets/{name}")
    shutil.copy(f"{SRC}/kart/3_FirstPage_5x7.jpg", f"{WORK}/source_assets/Kart_Stil3_FirstPage_EMMA_JAMES.jpg")
    sym_png(bp.MASKS["hero"], 2800, f"{WORK}/source_assets/Sembol_Ortak_Cancer_Libra.png")
    sym_png(bp.MASKS["left"], 600, f"{WORK}/source_assets/Sembol_Cancer.png")
    sym_png(bp.MASKS["right"], 600, f"{WORK}/source_assets/Sembol_Libra.png")
    d = json.load(open(f"{ROOT}/galeri/gallery_layout.json"))
    for s in d["slides"]:
        for e in s["elements"]:
            if e["type"] != "text":
                continue
            c = e["content"]
            c = c.replace("Cancer & Libra", f"{A} & {B}").replace("EMMA (Cancer)", f"EMMA ({A})").replace("JAMES (Libra)", f"JAMES ({B})")
            if c == "Cancer":
                c = A
            if c == "Libra":
                c = B
            e["content"] = c
        if s["number"] == 1:
            E = {e["id"]: e for e in s["elements"]}
            p = E["pair"]
            f = ImageFont.truetype(f"{ROOT}/galeri/{p['font']['file']}", p["font"]["size_px"])
            f.set_variation_by_axes([p["font"]["weight"]])
            if f.getlength(p["content"]) > 1300:   # posterle arada boşluk kalsın (Takip 14 Eki)
                # long pair names: two lines, slightly smaller, rest of the column moves down
                p["content"] = f"{A} &\n{B}"
                size = p["font"]["size_px"]
                while max(f.getlength(x) for x in p["content"].split("\n")) > p["width_pct"] / 100 * 3200:
                    size -= 5
                    f = ImageFont.truetype(f"{ROOT}/galeri/{p['font']['file']}", size)
                    f.set_variation_by_axes([p["font"]["weight"]])
                p["font"]["size_px"] = min(size, 185)
                p["line_height_em"] = 1.0
                p.update(center_y_pct=27, height_pct=17)
                E["headline"]["center_y_pct"] = 47
                E["product"]["center_y_pct"] = 62
                E["personalization"]["center_y_pct"] = 73
                E["formats"]["center_y_pct"] = 80
    json.dump(d, open(f"{WORK}/gallery_layout.json", "w"), ensure_ascii=False, indent=1)
    from pathlib import Path
    render(Path(WORK), Path(f"{SRC}/galeri"))


if __name__ == "__main__":
    main()
