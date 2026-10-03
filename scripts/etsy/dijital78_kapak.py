#!/usr/bin/env python3
"""
DIJITAL 78 - ADIM 7: KAPAK ORNEGI (yalniz ornek, Etsy'ye yukleme YOK).

Bir ciftin 5 edisyon posterini yan yana gosteren iki duzen alternatifi uretir:
  A) DUZ SIRA  - 5 poster ayni taban cizgisinde, ust uste binmeden
  B) KADEMELI  - 5 poster ust uste binerek kademeli inis/cikis

Her alternatif Etsy kapak orani 4:5, 2400x3000. Cikti:
  KAPAK_A_DUZ.jpg, KAPAK_B_KADEMELI.jpg (2400x3000, etiketsiz)
  KAPAK_ORNEK.jpg (4800x3000, iki alternatif yan yana, kose etiketli, <= 1 MB)

Girdi: ZIP'lerden cikarilan 4:5 posterler (--zip-dizin) veya dogrudan --gorsel.
"""
import argparse
import io
import re
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None

EDISYON_SIRA = ["Champagne_Ivory", "Pure_White", "Warm_Parchment", "Midnight_Blue", "Deep_Black"]
KAPAK = (2400, 3000)
ZEMIN = (242, 240, 236)
ZEMIN_ALT = (232, 229, 223)
GOLGE = (0, 0, 0)
HEDEF_BAYT = 1_000_000


def poster_bul(zip_dizin, cift):
    """Ciftin 5 edisyon ZIP'inden 4:5 JPG'leri sirayla cikarir."""
    d = Path(zip_dizin)
    out = []
    for ed in EDISYON_SIRA:
        adaylar = [p for p in d.glob("*.zip")
                   if re.search(rf"_{ed}_", p.name) and cift_uyar(p.name, cift)]
        if not adaylar:
            continue
        with zipfile.ZipFile(adaylar[0]) as z:
            secili = None
            for zi in z.infolist():
                n = zi.filename.lower()
                if n.endswith((".jpg", ".jpeg")) and re.search(r"4[x_]5", n):
                    secili = zi
                    break
            if secili is None:  # 4:5 yoksa oranca en yakini
                en_iyi, fark = None, 9.0
                for zi in z.infolist():
                    if not zi.filename.lower().endswith((".jpg", ".jpeg")):
                        continue
                    with z.open(zi) as fh:
                        im = Image.open(io.BytesIO(fh.read()))
                        w, h = im.size
                    f = abs((w / h) - 0.8) / 0.8
                    if f < fark:
                        en_iyi, fark = zi, f
                secili = en_iyi
            if secili is None:
                continue
            with z.open(secili) as fh:
                im = Image.open(io.BytesIO(fh.read())).convert("RGB")
        out.append((ed.replace("_", " "), im))
    return out


def cift_uyar(ad, cift):
    a, b = cift.split("_")
    return re.match(rf"AstroLove_({a}_{b}|{b}_{a})_", ad, re.I) is not None


def zemin(boyut):
    im = Image.new("RGB", boyut, ZEMIN)
    d = ImageDraw.Draw(im)
    for y in range(boyut[1]):
        t = y / boyut[1]
        c = tuple(int(ZEMIN[i] + (ZEMIN_ALT[i] - ZEMIN[i]) * (t ** 1.6)) for i in range(3))
        d.line([(0, y), (boyut[0], y)], fill=c)
    return im


def yerlestir(tuval, im, x, y, w, h):
    """Poster + ince kenarlik + yumusak golge."""
    p = im.resize((w, h), Image.LANCZOS)
    golge = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    ImageDraw.Draw(golge).rectangle([30, 34, w + 29, h + 33], fill=(0, 0, 0, 70))
    from PIL import ImageFilter
    golge = golge.filter(ImageFilter.GaussianBlur(18))
    tuval.paste(Image.alpha_composite(
        tuval.crop((x - 30, y - 30, x + w + 30, y + h + 30)).convert("RGBA"), golge
    ).convert("RGB"), (x - 30, y - 30))
    tuval.paste(p, (x, y))
    ImageDraw.Draw(tuval).rectangle([x, y, x + w - 1, y + h - 1], outline=(206, 202, 194), width=2)


def duzen_a(posterler):
    """DUZ SIRA: 5 poster ayni taban cizgisinde, ust uste binmeden."""
    t = zemin(KAPAK)
    n = len(posterler)
    kenar, bosluk = 44, 24
    w = (KAPAK[0] - 2 * kenar - (n - 1) * bosluk) // n
    h = int(round(w * 5 / 4))
    y = (KAPAK[1] - h) // 2 - 40
    x = (KAPAK[0] - (n * w + (n - 1) * bosluk)) // 2
    for _, im in posterler:
        yerlestir(t, im, x, y, w, h)
        x += w + bosluk
    return t


def duzen_b(posterler):
    """KADEMELI: buyuk posterler ust uste binerek kademeli yerlesir."""
    t = zemin(KAPAK)
    n = len(posterler)
    w = 980
    h = int(round(w * 5 / 4))
    adim = (KAPAK[0] - 2 * 90 - w) // max(1, n - 1)
    kademe = 96
    y0 = (KAPAK[1] - h - (n - 1) * kademe) // 2
    for i, (_, im) in enumerate(posterler):
        yerlestir(t, im, 90 + i * adim, y0 + i * kademe, w, h)
    return t


def yazi(d, xy, metin, punto, renk=(90, 86, 80)):
    for yol in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(yol).exists():
            d.text(xy, metin, font=ImageFont.truetype(yol, punto), fill=renk)
            return
    d.text(xy, metin, fill=renk)


def kaydet(im, yol, hedef=None):
    for q in (95, 92, 88, 84, 80, 76, 72, 68):
        im.save(yol, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0)
        if hedef is None or Path(yol).stat().st_size <= hedef:
            return q, Path(yol).stat().st_size
    return q, Path(yol).stat().st_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip-dizin", required=True)
    ap.add_argument("--cift", default="Aries_Leo")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    posterler = poster_bul(a.zip_dizin, a.cift)
    print(f"poster: {len(posterler)} / 5 -> {[p[0] for p in posterler]}", flush=True)
    if len(posterler) < 2:
        raise SystemExit(f"HATA: {a.cift} icin yeterli poster bulunamadi ({len(posterler)})")

    A, B = duzen_a(posterler), duzen_b(posterler)
    qa, sa = kaydet(A, out / "KAPAK_A_DUZ.jpg")
    qb, sb = kaydet(B, out / "KAPAK_B_KADEMELI.jpg")
    print(f"A: {A.size} q{qa} {sa/1e6:.2f} MB | B: {B.size} q{qb} {sb/1e6:.2f} MB", flush=True)

    birlesik = Image.new("RGB", (KAPAK[0] * 2 + 16, KAPAK[1]), (255, 255, 255))
    birlesik.paste(A, (0, 0))
    birlesik.paste(B, (KAPAK[0] + 16, 0))
    d = ImageDraw.Draw(birlesik)
    yazi(d, (60, 56), f"A  DUZ SIRA   {a.cift.replace('_', ' + ')}   5 renk", 54)
    yazi(d, (KAPAK[0] + 76, 56), f"B  KADEMELI   {a.cift.replace('_', ' + ')}   5 renk", 54)
    q, s = kaydet(birlesik, out / "KAPAK_ORNEK.jpg", HEDEF_BAYT)
    print(f"KAPAK_ORNEK.jpg {birlesik.size} q{q} {s/1e6:.3f} MB "
          f"({'TAMAM' if s <= HEDEF_BAYT else 'SINIR ASILDI'})", flush=True)
    if s > HEDEF_BAYT:
        raise SystemExit("HATA: KAPAK_ORNEK.jpg 1 MB siniri asildi")


if __name__ == "__main__":
    main()
