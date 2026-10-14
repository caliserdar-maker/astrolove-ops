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


# ---- KAPAK (01_Cover) yeni olcu (Takip 14 Eki, Serdar: "tablo cok daha buyuk, yazilar cok daha buyuk") ----
# Poster olcusu ve yazi puntolari gallery_layout.json slide 1'de (poster 70/50/54/90, 8x10 orani 54*3200 / 90*2400 = 0.8).
KAPAK = dict(sol_pct=4, poster_bosluk_px=80, sag_bosluk_pct=3, pair_max=280, sutun_yukseklik_pct=80,
             sira=["collection", "pair", "headline", "product", "personalization", "formats"])
BURCLAR = ["Aquarius", "Aries", "Cancer", "Capricorn", "Gemini", "Leo", "Libra", "Pisces", "Sagittarius", "Scorpio", "Taurus", "Virgo"]


def kapak_yerlesim(s):
    """Slide 1: poster + kagit/golge buyur; sol sutun yazilari buyur, pair HER ZAMAN iki satir (78 ciftte ayni punto),
    dikey dizilim esit aralikla yeniden hesaplanir ve sutun dikeyde ortalanir. Yeni kagit + golge temiz zemine cizilir."""
    W, H = 3200, 2400
    E = {e["id"]: e for e in s["elements"]}
    P = {k: E["hero_poster"][k] for k in ("center_x_pct", "center_y_pct", "width_pct", "height_pct")}
    kagit = next(b for b in s["background_layers"] if b.get("name") == "hero_poster_blank_paper")
    if any(abs(kagit[k] - v) > 1e-6 for k, v in P.items()):
        raise SystemExit("HATA: hero_poster ile hero_poster_blank_paper olculeri farkli")
    pl, pr = (P["center_x_pct"] - P["width_pct"] / 2) / 100 * W, (P["center_x_pct"] + P["width_pct"] / 2) / 100 * W
    pt, pb = (P["center_y_pct"] - P["height_pct"] / 2) / 100 * H, (P["center_y_pct"] + P["height_pct"] / 2) / 100 * H
    if W - pr < KAPAK["sag_bosluk_pct"] / 100 * W - 0.5:
        raise SystemExit(f"HATA: poster sag bosluk {W - pr:.0f} px < %{KAPAK['sag_bosluk_pct']}")
    x0 = KAPAK["sol_pct"] / 100 * W
    col = pl - KAPAK["poster_bosluk_px"] - x0
    # pair: iki satir "<A> &" / "<B>"; 12 burcun en genis satirinin sigdigi en buyuk punto (<= 280), 78 ciftte ayni
    p = E["pair"]
    fd = p["font"]

    def font(size):
        f = ImageFont.truetype(f"{ROOT}/galeri/{fd['file']}", size)
        f.set_variation_by_axes([fd["weight"]])
        return f
    size = KAPAK["pair_max"]
    while max(max(font(size).getlength(n + " &"), font(size).getlength(n)) for n in BURCLAR) > col:
        size -= 1
    p["content"] = f"{A} &\n{B}"
    fd["size_px"] = size
    p["line_height_em"] = 1.0
    for k in KAPAK["sira"] + ["brand"]:
        E[k]["center_x_pct"] = (x0 + col / 2) / W * 100
        E[k]["width_pct"] = col / W * 100

    def slot(e):                                   # by_galeri_render ile ayni satir yuvasi yuksekligi
        n = len(e["content"].split("\n"))
        sz = e["font"]["size_px"]
        return sz + (n - 1) * sz * e["line_height_em"]
    hs = [slot(E[k]) for k in KAPAK["sira"]]
    span = KAPAK["sutun_yukseklik_pct"] / 100 * H
    gap = (span - sum(hs)) / (len(hs) - 1)
    if gap < 40:
        raise SystemExit(f"HATA: sutun ogeleri sigmiyor (aralik {gap:.0f} px)")
    y = H / 2 - span / 2
    for k, h in zip(KAPAK["sira"], hs):
        E[k]["center_y_pct"] = (y + h / 2) / H * 100
        E[k]["height_pct"] = (h + 2) / H * 100
        y += h + gap
    # temiz zemine yeni kagit + golge (eskisi B'de pisirilmis; yeni poster onu tamamen ortuyor)
    sh = E["hero_poster"]["shadow"]
    bg = Image.open(f"{ROOT}/galeri/{s['clean_background_file']}").convert("RGB")
    box = (round(pl), round(pt), round(pr), round(pb))
    from PIL import ImageDraw, ImageFilter
    col_rgb = tuple(int(sh["color_hex"][i:i + 2], 16) for i in (1, 3, 5))
    for off, blur, op in (((sh["offset_x_px"], sh["offset_y_px"]), sh["softness_blur_px"], sh["opacity"]),
                          ((0, 0), sh["contact_shadow_blur_px"], sh["contact_shadow_opacity"])):
        m = Image.new("L", bg.size, 0)
        ImageDraw.Draw(m).rectangle((box[0] + off[0], box[1] + off[1], box[2] + off[0], box[3] + off[1]), fill=round(255 * op))
        m = m.filter(ImageFilter.GaussianBlur(blur))
        bg = Image.composite(Image.new("RGB", bg.size, col_rgb), bg, m)
    ImageDraw.Draw(bg).rectangle(box, fill=kagit["fill_hex"])
    bg.save(f"{WORK}/01_Cover_B_yeni.png")
    s["clean_background_file"] = "01_Cover_B_yeni.png"
    print("kapak", dict(pair_punto=size, sutun_px=[round(x0), round(x0 + col)], poster_px=box, aralik_px=round(gap)))


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
            kapak_yerlesim(s)
    json.dump(d, open(f"{WORK}/gallery_layout.json", "w"), ensure_ascii=False, indent=1)
    from pathlib import Path
    secili = [int(x) for x in os.environ.get("GALERI_SLAYT", "").split(",") if x.strip()] or None   # bos = 10 gorsel
    render(Path(WORK), Path(f"{SRC}/galeri"), secili)


if __name__ == "__main__":
    main()
