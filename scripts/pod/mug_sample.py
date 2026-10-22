#!/usr/bin/env python3
"""11oz Prodigi kupa ornek gorseli: wrap (2670x1110) + 2 silindirik mockup (2000x2000).

Sembol ASLA yeniden cizilmez/sadelestirilmez/aynalanmaz: yalniz olceklenir ve yerlestirilir.
Kaynak sembol seffaf RGBA PNG olmalidir (--symbol).

Kullanim:
  python scripts/pod/mug_sample.py --symbol ari_leo.png --out _out \
      --title "Aries ∞ Leo" --tagline "Two Souls · One Bond."
"""
import argparse, math, pathlib, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 2670, 1110                 # Prodigi 11oz wrap sablonu, 300 dpi
NAVY, GOLD = (26, 26, 46), (201, 162, 39)     # #1A1A2E / #C9A227
SYM_CX, SYM_CY, SYM_H = 580, 555, 500         # sol yuz: sembol
TXT_CX = 2000                                 # sag yuz: metin
TITLE_PX, TAG_PX, TAG_GAP = 70, 40, 30
HANDLE_X = (1140, 1440)           # kulpun karsisi - bos kalacak
EDGE = 150                        # x<150 ve x>W-150 kulp bolgesi - bos
MARGIN_Y = 60                     # ust/alt guvenli bosluk

SERIF = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
         "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"]


def font(px):
    for p in SERIF:
        if pathlib.Path(p).exists():
            return ImageFont.truetype(p, px), pathlib.Path(p).name
    raise SystemExit("HATA: serif font bulunamadi")


def wrap_uret(sym_path, baslik, slogan, doku=None):
    im = Image.new("RGB", (W, H), NAVY)
    if doku:
        t = Image.open(doku).convert("RGB").resize((W, H), Image.LANCZOS)
        im = Image.blend(im, t, 0.35)
    # --- sembol: yalniz olcekleme ---
    s = Image.open(sym_path).convert("RGBA")
    bb = s.getbbox()
    if bb:
        s = s.crop(bb)
    k = SYM_H / s.height
    s = s.resize((max(1, round(s.width * k)), SYM_H), Image.LANCZOS)
    im.paste(s, (SYM_CX - s.width // 2, SYM_CY - s.height // 2), s)
    # --- metin ---
    d = ImageDraw.Draw(im)
    fb, ad = font(TITLE_PX)
    fs, _ = font(TAG_PX)
    bx = d.textbbox((0, 0), baslik, font=fb)
    sx = d.textbbox((0, 0), slogan, font=fs)
    by = SYM_CY - (bx[3] - bx[1]) // 2 - bx[1]
    d.text((TXT_CX - (bx[2] + bx[0]) // 2, by), baslik, font=fb, fill=GOLD)
    d.text((TXT_CX - (sx[2] + sx[0]) // 2, by + (bx[3] - bx[1]) + TAG_GAP - sx[1]),
           slogan, font=fs, fill=GOLD)
    return im, ad


def guvenli_bolge(im):
    """Zeminden farkli piksel yasak bolgelere tasmis mi? (bos liste = temiz)"""
    a = np.asarray(im).astype(np.int16)
    fark = np.abs(a - np.array(NAVY, np.int16)).max(2) > 18
    hata = []
    if fark[:MARGIN_Y].any() or fark[-MARGIN_Y:].any():
        hata.append("ust/alt 60 px")
    if fark[:, :EDGE].any() or fark[:, -EDGE:].any():
        hata.append("kulp kenari (x<150 / x>%d)" % (W - EDGE))
    if fark[:, HANDLE_X[0]:HANDLE_X[1]].any():
        hata.append("kulp karsisi (x=1140-1440)")
    return hata


def mockup(wrap, on_x, kulp_sag, boy=2000):
    """Silindirik izdusum: 2670 px = 360 derece. on_x = one bakan wrap sutunu."""
    im = Image.new("RGB", (boy, boy), (247, 247, 249))
    mm = 1000 / 95.0                       # kupa yuksekligi 95 mm -> 1000 px
    R = 82.0 / 2 * mm                      # cap 82 mm
    Hm = 95.0 * mm
    cx, top = boy // 2, int((boy - Hm) / 2)
    rim = R * 0.30                         # agiz elipsinin dikey yari ekseni
    wr = np.asarray(wrap.convert("RGB")).astype(np.float32)

    body = np.zeros((int(Hm), int(2 * R), 3), np.float32)
    xs = np.arange(int(2 * R)) - R + 0.5
    t = np.clip(xs / R, -1, 1)
    theta = np.arcsin(t)                                   # -pi/2..pi/2 gorunur yuz
    col = ((on_x + theta / (2 * math.pi) * W) % W).astype(int)
    if not kulp_sag:                                       # kulp solda: 180 derece donus
        col = ((on_x + theta / (2 * math.pi) * W) % W).astype(int)
    isik = 0.55 + 0.45 * np.cos(theta - 0.35)              # silindir golgelemesi
    for i, c in enumerate(col):
        body[:, i, :] = np.asarray(Image.fromarray(wr[:, c].astype(np.uint8)[:, None, :]
                                                   ).resize((1, int(Hm)), Image.LANCZOS))[:, 0, :]
    body *= isik[None, :, None]
    bimg = Image.fromarray(np.clip(body, 0, 255).astype(np.uint8))

    # kulp (beyaz seramik halka); govde sonra ustune yapistirilir
    d = ImageDraw.Draw(im)
    hy = top + Hm * 0.46
    yon = 1 if kulp_sag else -1
    hx = cx + yon * R * 0.90
    kr = R * 0.60
    kutu = sorted([hx - yon * kr * 0.15, hx + yon * kr * 1.15])
    for w, c in ((int(kr * 0.42), (206, 206, 214)), (int(kr * 0.22), (250, 250, 252))):
        d.ellipse([kutu[0], hy - kr, kutu[1], hy + kr], outline=c, width=w)
    # govde maskesi: dikdortgen + alt elips + ust elips
    mask = Image.new("L", (boy, boy), 0)
    md = ImageDraw.Draw(mask)
    md.rectangle([cx - R, top, cx + R, top + Hm], fill=255)
    md.ellipse([cx - R, top + Hm - rim, cx + R, top + Hm + rim], fill=255)
    md.ellipse([cx - R, top - rim, cx + R, top + rim], fill=255)
    kap = Image.new("RGB", (boy, boy), NAVY)
    kap.paste(bimg, (int(cx - R), top))
    # ust elips: beyaz ic + koyu ic golge
    im.paste(kap, (0, 0), mask)
    d.ellipse([cx - R, top - rim, cx + R, top + rim], fill=(250, 250, 252), outline=(208, 208, 214), width=5)
    d.ellipse([cx - R * 0.90, top - rim * 0.86, cx + R * 0.90, top + rim * 0.86],
              fill=(232, 232, 238))
    # zemin golgesi
    gl = Image.new("L", (boy, boy), 0)
    ImageDraw.Draw(gl).ellipse([cx - R * 1.05, top + Hm - rim * 0.5, cx + R * 1.05,
                                top + Hm + rim * 1.25], fill=90)
    gl = gl.filter(ImageFilter.GaussianBlur(28))
    im = Image.composite(Image.new("RGB", (boy, boy), (206, 206, 212)), im, gl)
    im.paste(kap, (0, 0), mask)
    d = ImageDraw.Draw(im)
    d.ellipse([cx - R, top - rim, cx + R, top + rim], fill=(250, 250, 252), outline=(208, 208, 214), width=5)
    d.ellipse([cx - R * 0.90, top - rim * 0.86, cx + R * 0.90, top + rim * 0.86], fill=(233, 233, 239))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--texture", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Aries ∞ Leo")
    ap.add_argument("--tagline", default="Two Souls · One Bond.")
    ap.add_argument("--prefix", default="ARI_LEO_MB_11oz")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)

    wrap, fontad = wrap_uret(a.symbol, a.title, a.tagline, a.texture)
    hata = guvenli_bolge(wrap)
    print(f"font: {fontad} | guvenli bolge: {'TEMIZ' if not hata else 'IHLAL ' + str(hata)}")
    if hata:
        sys.exit(f"HATA: yasak bolgeye tasma: {hata}")
    wp = out / f"{a.prefix}_wrap.jpg"
    wrap.save(wp, quality=95, subsampling=0, icc_profile=None)
    mockup(wrap, SYM_CX, True).save(out / f"{a.prefix}_mockup_A.jpg", quality=93)
    mockup(wrap, TXT_CX, False).save(out / f"{a.prefix}_mockup_B.jpg", quality=93)
    for p in sorted(out.glob(f"{a.prefix}_*")):
        print(p, p.stat().st_size, Image.open(p).size)


if __name__ == "__main__":
    main()
