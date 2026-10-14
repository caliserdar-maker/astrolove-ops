"""Bizim Yilimiz Etsy gallery (13 images, order SIRA below; 01_Cover = Layers 8x10 poster copy 2400x3000, others 3200x2400) for one pair.
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
KAPAK = dict(sol_pct=4, poster_bosluk_px=160, sag_bosluk_pct=3, pair_max=280, sutun_yukseklik_pct=80,
             sira=["collection", "pair", "headline", "product", "personalization", "formats"])
BURCLAR = ["Aquarius", "Aries", "Cancer", "Capricorn", "Gemini", "Leo", "Libra", "Pisces", "Sagittarius", "Scorpio", "Taurus", "Virgo"]
# ---- GALERI SIRASI (Takip 14 Eki, ChatGPT degerlendirmesi, Serdar onayi): 13 gorsel; eski 05 ve 06 URETILMEZ ----
# (eski slayt no, yeni no, dosya adi). Yeni adlarda "_A" yok: eski 10'lu galeri dosyalariyla karismaz.
SIRA = [(1, 1, "01_Cover"), (2, 2, "02_Shared_Symbol"), (8, 3, "03_Formats"), (3, 4, "04_Five_Styles"),
        (7, 5, "05_Layers_Material"), (4, 6, "06_Personalization"), (9, 7, "07_Size_Gift_Scene"), (10, 8, "08_Free_Preview"),
        (11, 9, "09_Style_Starlit"), (12, 10, "10_Style_Timeless"), (13, 11, "11_Style_FirstPage"), (14, 12, "12_Style_Layers"),
        (15, 13, "13_Style_Botanical")]
# eski slayt 9 (olcek) dipnotu: ~1,6 kat punto, ince yazilarla ayni renk (scale_label), okunur yerde
DIPNOT = dict(kat=1.6)
# ---- STIL GORSELLERI 11-15 (Takip 14 Eki, Serdar: "style secilince ilgili poster gorunsun"): kapakla ayni duzen ----
STILLER = [  # (no, ad, poster dosyasi, headline)
    (11, "Starlit", "Poster_Stil1_Starlit_EMMA_JAMES.jpg", "Navy and gold,\nunder the stars."),
    (12, "Timeless", "Poster_Stil2_Timeless_EMMA_JAMES.jpg", "Cream and gold,\nsoft and classic."),
    (13, "First Page", "Poster_Stil3_FirstPage_EMMA_JAMES.jpg", "Cream and burgundy,\nlike a love letter."),
    (14, "Layers", "Poster_Stil4_Layers_EMMA_JAMES.jpg", "Peach and terracotta,\na layered paper look."),
    (15, "Botanical", "Poster_Stil5_Botanical_EMMA_JAMES.jpg", "Cream and green,\nwith botanicals.")]


def _sigdir(e, metinler, col, font):
    """e'nin puntosunu, verilen tum metinlerin (78 ciftte / 5 stilde ayni) her satiri sutuna sigana kadar kucultur."""
    fd = e["font"]
    tr = e.get("letter_spacing_px") or 0
    def gen(size, line):
        f = font(fd, size)
        return f.getlength(line) if not tr else sum(f.getlength(c) for c in line) + tr * size / fd["size_px"] * max(0, len(line) - 1)
    size = fd["size_px"]
    while max(gen(size, ln) for m in metinler for ln in m.split("\n")) > col:
        size -= 1
    if size != fd["size_px"]:
        if tr:
            e["letter_spacing_px"] = round(tr * size / fd["size_px"], 2)
        fd["size_px"] = size
    return size


def _font(fd, size):
    f = ImageFont.truetype(f"{ROOT}/galeri/{fd['file']}", size)
    f.set_variation_by_axes([fd["weight"]])
    return f


def kapak_yerlesim(s, stil=None):
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
    olcu = {}
    if stil:                                       # stil gorseli: buyuk ad tek satir, kapaktaki pair puntosuyla
        no, ad, dosya, baslik = stil
        if max(font(size).getlength(x[1]) for x in STILLER) > col:
            raise SystemExit("HATA: stil adi sutuna sigmiyor")
        p["content"] = ad
        E["collection"]["content"] = f"STYLE {no - 10} OF 5"
        E["headline"]["content"] = baslik
        E["product"]["content"] = f"{A} & {B}\nanniversary art"
        E["personalization"]["content"] = "Your names. Your date."
        E["hero_poster"]["content"]["source_file"] = f"source_assets/{dosya}"
        E["hero_poster"]["content"]["style"] = ad
        ciftler = [f"{a} & {b}" for i, a in enumerate(BURCLAR) for b in BURCLAR[i:]]      # 78 cift: alfabetik sira
        olcu = dict(headline=_sigdir(E["headline"], [x[3] for x in STILLER], col, _font),
                    product=_sigdir(E["product"], [c + "\nanniversary art" for c in ciftler], col, _font),
                    collection=_sigdir(E["collection"], [f"STYLE {i} OF 5" for i in range(1, 6)], col, _font),
                    formats=_sigdir(E["formats"], [E["formats"]["content"]], col, _font))
        s["preview_file"] = f"A_Previews/{no}_Style_{ad.replace(' ', '')}.jpg"
        s["number"] = no
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
    print("stil " + str(stil[0]) if stil else "kapak", dict(pair_punto=size, sutun_px=[round(x0), round(x0 + col)], poster_px=box,
                                                         aralik_px=round(gap), **{k + "_punto": v for k, v in olcu.items()}))


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
    import copy
    s1 = next(s for s in d["slides"] if s["number"] == 1)
    yeni = [copy.deepcopy(s1) for _ in STILLER]       # kapak metinleri cifte gore degistirilmeden once kopyalanir
    for s in d["slides"]:
        if s["number"] == 1:
            kapak_yerlesim(s)
    for s, st in zip(yeni, STILLER):
        kapak_yerlesim(s, st)
    d["slides"] += yeni
    # eski slayt 4: ornek posterde sagdaki kisa satir gercekten basili (LINE ile uretilen First Page posteri)
    s4 = next(s for s in d["slides"] if s["number"] == 4)
    E4 = {e["id"]: e for e in s4["elements"]}
    satir = E4["shortline_example"]["content"]
    import subprocess
    env = dict(os.environ, STYLE="3", LINE=satir, OUT=f"{WORK}/poster_line")
    r = subprocess.run([sys.executable, f"{os.path.dirname(os.path.abspath(__file__))}/by_poster.py"], env=env, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"HATA: LINE posteri uretilemedi\n{r.stderr[-1500:]}")
    shutil.copy(f"{WORK}/poster_line/3_FirstPage_8x10.jpg", f"{WORK}/source_assets/Poster_Stil3_FirstPage_EMMA_JAMES_LINE.jpg")
    E4["sample_poster"]["content"]["source_file"] = "source_assets/Poster_Stil3_FirstPage_EMMA_JAMES_LINE.jpg"
    print("slayt 4 ornek poster LINE:", repr(satir))
    # eski slayt 9: dipnot
    s9 = next(s for s in d["slides"] if s["number"] == 9)
    E9 = {e["id"]: e for e in s9["elements"]}
    n9 = E9["card_digital_note"]
    eski = (n9["font"]["size_px"], n9["color_hex"], n9["center_y_pct"])
    n9["font"]["size_px"] = round(n9["font"]["size_px"] * DIPNOT["kat"])
    n9["color_hex"] = E9["scale_label"]["color_hex"]
    for k, v in DIPNOT.items():
        if k != "kat":
            n9[k] = v
    n9["height_pct"] = max(n9["height_pct"], (n9["font"]["size_px"] + 4) / 24)
    print("slayt 9 dipnot:", eski, "->", (n9["font"]["size_px"], n9["color_hex"], n9["center_y_pct"]))
    # yeni sira + numara + dosya adi; eski 05 ve 06 cikarilir
    m = {a: (b, n) for a, b, n in SIRA}
    d["slides"] = sorted([s for s in d["slides"] if s["number"] in m], key=lambda s: m[s["number"]][0])
    for s in d["slides"]:
        b, n = m[s["number"]]
        s["number"], s["preview_file"] = b, f"A_Previews/{n}.jpg"
    json.dump(d, open(f"{WORK}/gallery_layout.json", "w"), ensure_ascii=False, indent=1)
    from pathlib import Path
    secili = [int(x) for x in os.environ.get("GALERI_SLAYT", "").split(",") if x.strip()] or None   # bos = 13 gorsel (YENI numaralar)
    # KAPAK = YALNIZ POSTER (Serdar 14 Eki 20:00: Etsy kare/dikey kirpma kapak yazilarini kesiyor):
    # 01_Cover.jpg = o ciftin poster/4_Layers_8x10.jpg dosyasinin birebir kopyasi (2400x3000, yeniden boyutlandirma yok).
    digerleri = [n for n in (secili or [s["number"] for s in d["slides"]]) if n != 1]
    if digerleri:
        render(Path(WORK), Path(f"{SRC}/galeri"), digerleri)
    if secili is None or 1 in secili:
        os.makedirs(f"{SRC}/galeri", exist_ok=True)
        shutil.copyfile(f"{SRC}/poster/4_Layers_8x10.jpg", f"{SRC}/galeri/01_Cover.jpg")
        print("01_Cover.jpg = poster/4_Layers_8x10.jpg (kopya)")


if __name__ == "__main__":
    main()
