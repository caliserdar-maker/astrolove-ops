#!/usr/bin/env python3
"""
DIJITAL 78 - POD V11 Gold B kapagina "INSTANT DOWNLOAD - 5 COLORS" etiketi (3 varyant).

Kaynak kapak OLDUGU GIBI kullanilir; yalniz uzerine etiket cizilir.

GUVENLI BANT (tahmin degil, olculmus):
  `pod_cover_gold_b_transform.artwork_mask` poster/isim/alt-marka bolgelerini
  y 650-2425 arasinda tanimlar -> etiket bu bandin disinda kalmali.
  Etsy arama kartinda ortadan KARE kirpim y 300-2700'u birakir.
  Kesisim -> kullanilabilir bantlar: y 300-650 (ust) ve y 2425-2700 (alt).
Etiket bu bantlarin disina TASMAZ; boylece hem posterin ustune gelmez hem de
arama kartinda kirpilmaz.

Cikti: 3 varyant (2400x3000) + KAPAK_ETIKET_KARSILASTIRMA.jpg (ust satir varyantlar,
alt satir 300 px ve 200 px arama karti simulasyonu) + notlar.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

KAPAK = (2400, 3000)
ARTWORK_BANT = (650, 2425)        # artwork_mask zones min/max y
KARE_KIRPIM = (300, 2700)         # ortadan kare kirpim (2400 px yukseklik)
UST_BANT = (KARE_KIRPIM[0], ARTWORK_BANT[0])      # 300-650
ALT_BANT = (ARTWORK_BANT[1], KARE_KIRPIM[1])      # 2425-2700
ETIKET = "INSTANT DOWNLOAD · 5 COLORS"
KREM = (236, 229, 214)
LACI = (28, 38, 62)
ALTIN = (186, 152, 92)


def font(fonts_dir, size, weight=500):
    p = Path(fonts_dir) / "Montserrat[wght].ttf"
    if not p.exists():
        sys.exit(f"HATA: font yok: {p}")
    f = ImageFont.truetype(str(p), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def tracked(d, xy, s, f, fill, tracking, anchor="l"):
    w = sum(d.textlength(c, font=f) for c in s) + tracking * (len(s) - 1)
    x, y = xy
    if anchor == "c":
        x -= w / 2
    for c in s:
        d.text((x, y), c, font=f, fill=fill)
        x += d.textlength(c, font=f) + tracking
    return w


def olc(d, s, f, tracking):
    return sum(d.textlength(c, font=f) for c in s) + tracking * (len(s) - 1)


def sar(d, metin, f, en):
    """Sutun genisligine gore kelime sarmasi."""
    satirlar, aktif = [], ""
    for kelime in metin.split():
        deneme = (aktif + " " + kelime).strip()
        if d.textlength(deneme, font=f) <= en or not aktif:
            aktif = deneme
        else:
            satirlar.append(aktif)
            aktif = kelime
    if aktif:
        satirlar.append(aktif)
    return satirlar


def v1_hap(base, fonts_dir):
    """Sol ust kosede yari saydam koyu hap."""
    im = base.copy().convert("RGBA")
    kat = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(kat)
    f = font(fonts_dir, 46, 500)
    tr = 7.0
    tw = olc(d, ETIKET, f, tr)
    ph, px = 104, 52
    x0, y0 = 120, (UST_BANT[0] + UST_BANT[1]) // 2 - ph // 2
    x1 = x0 + tw + px * 2
    d.rounded_rectangle([x0, y0, x1, y0 + ph], radius=ph // 2, fill=LACI + (205,),
                        outline=ALTIN + (150,), width=2)
    tracked(d, (x0 + px, y0 + ph // 2 - f.getbbox("H")[3] // 2 - 4), ETIKET, f, KREM + (255,), tr)
    return Image.alpha_composite(im, kat).convert("RGB"), (y0, y0 + ph)


def _bant(base, fonts_dir, y0, h):
    im = base.copy().convert("RGBA")
    kat = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(kat)
    f = font(fonts_dir, 44, 500)
    tr = 9.0
    d.rectangle([0, y0, im.width, y0 + h], fill=LACI + (198,))
    d.line([0, y0, im.width, y0], fill=ALTIN + (170,), width=3)
    d.line([0, y0 + h, im.width, y0 + h], fill=ALTIN + (170,), width=3)
    tracked(d, (im.width / 2, y0 + h // 2 - f.getbbox("H")[3] // 2 - 4), ETIKET, f, KREM + (255,),
            tr, anchor="c")
    return Image.alpha_composite(im, kat).convert("RGB"), (y0, y0 + h)


def v2_alt_bant(base, fonts_dir):
    h = 112
    return _bant(base, fonts_dir, ALT_BANT[1] - 90 - h, h)      # alt banda yakin, kirpim ici


def v3_ust_bant(base, fonts_dir):
    h = 112
    return _bant(base, fonts_dir, UST_BANT[0] + 60, h)          # ust banda yakin, kirpim ici


VARYANTLAR = [("V1_SOL_UST_HAP", v1_hap), ("V2_ALT_BANT", v2_alt_bant), ("V3_UST_BANT", v3_ust_bant)]


def arama_karti(im, px):
    """Etsy arama karti simulasyonu: ortadan kare kirpim -> px."""
    w, h = im.size
    k = min(w, h)
    ust = (h - k) // 2
    return im.crop((0, ust, w, ust + k)).resize((px, px), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kapak", required=True)
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hedef-bayt", type=int, default=1_000_000)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    base = Image.open(a.kapak).convert("RGB")
    if base.size != KAPAK:
        print(f"UYARI: kapak {base.size}, beklenen {KAPAK}; oranli olceklenecek", flush=True)
        base = base.resize(KAPAK, Image.LANCZOS)

    uretilen, notlar = [], []
    for ad, fn in VARYANTLAR:
        im, (ey0, ey1) = fn(base, a.fonts)
        p = out / f"KAPAK_{ad}.jpg"
        im.save(p, "JPEG", quality=94, optimize=True, subsampling=0)
        uretilen.append((ad, im, (ey0, ey1)))
        kirpimda = ey0 >= KARE_KIRPIM[0] and ey1 <= KARE_KIRPIM[1]
        posterde = not (ey1 <= ARTWORK_BANT[0] or ey0 >= ARTWORK_BANT[1])
        yuk_200 = (ey1 - ey0) * 200 / 2400.0          # kare kirpimda 200 px'e inen etiket yuksekligi
        notlar.append({
            "varyant": ad, "etiket_y": [ey0, ey1],
            "kare_kirpimda_kaliyor": kirpimda,
            "poster_uzerine_geliyor": posterde,
            "etiket_yuksekligi_200px_kartta": round(yuk_200, 1),
            "not": (f"{'Kirpimda kaliyor' if kirpimda else 'KIRPIMDA KAYBOLUYOR'}, "
                    f"postere {'DEGIYOR' if posterde else 'degmiyor'}. "
                    f"200 px kartta etiket {yuk_200:.1f} px: "
                    f"{'okunur' if yuk_200 >= 9 else 'sinirda, zor okunur'}."),
        })
        print(f"  {ad}: {notlar[-1]['not']}", flush=True)

    # --------------------------------------------------- karsilastirma sayfasi
    ust_h = 900
    ust_w = int(KAPAK[0] * ust_h / KAPAK[1])
    bosluk, kenar = 60, 70
    f_bas = font(a.fonts, 34, 600)
    f_not = font(a.fonts, 22, 400)
    sayfa_w = kenar * 2 + ust_w * 3 + bosluk * 2
    alt_h = 300 + 48 + 70
    sayfa_h = kenar + 60 + ust_h + 60 + alt_h + 30 + kenar
    sayfa = Image.new("RGB", (sayfa_w, sayfa_h), (250, 250, 248))
    d = ImageDraw.Draw(sayfa)
    tracked(d, (sayfa_w / 2, kenar), "ETIKETLI KAPAK  ·  3 VARYANT  ·  ARAMA KARTI SIMULASYONU",
            f_bas, (40, 40, 44), 6, anchor="c")
    y_ust = kenar + 60
    for i, (ad, im, _) in enumerate(uretilen):
        x = kenar + i * (ust_w + bosluk)
        sayfa.paste(im.resize((ust_w, ust_h), Image.LANCZOS), (x, y_ust))
        d.rectangle([x, y_ust, x + ust_w - 1, y_ust + ust_h - 1], outline=(215, 213, 208), width=2)
        tracked(d, (x + ust_w / 2, y_ust + ust_h + 16), ad.replace("_", " "), f_not, (70, 70, 74), 3,
                anchor="c")
    y_alt = y_ust + ust_h + 70
    for i, (ad, im, _) in enumerate(uretilen):
        x = kenar + i * (ust_w + bosluk)
        k300, k200 = arama_karti(im, 300), arama_karti(im, 200)
        sayfa.paste(k300, (x, y_alt))
        d.rectangle([x, y_alt, x + 299, y_alt + 299], outline=(215, 213, 208), width=2)
        sayfa.paste(k200, (x + 340, y_alt + 50))
        d.rectangle([x + 340, y_alt + 50, x + 539, y_alt + 249], outline=(215, 213, 208), width=2)
        d.text((x, y_alt + 310), "300 px", font=f_not, fill=(70, 70, 74))
        d.text((x + 340, y_alt + 310), "200 px", font=f_not, fill=(70, 70, 74))
        ny = y_alt + 348
        for satir in sar(d, notlar[i]["not"], f_not, ust_w - 10):
            d.text((x, ny), satir, font=f_not, fill=(95, 95, 100))
            ny += 30
    p = out / "KAPAK_ETIKET_KARSILASTIRMA.jpg"
    for q in (95, 92, 88, 84, 80, 76, 72):
        sayfa.save(p, "JPEG", quality=q, optimize=True, progressive=True)
        if p.stat().st_size <= a.hedef_bayt:
            break
    print(f"KAPAK_ETIKET_KARSILASTIRMA.jpg {sayfa.size} q{q} {p.stat().st_size/1e3:.0f} KB "
          f"({'TAMAM' if p.stat().st_size <= a.hedef_bayt else 'SINIR ASILDI'})", flush=True)
    (out / "KAPAK_ETIKET_NOT.json").write_text(json.dumps(notlar, ensure_ascii=False, indent=2),
                                               encoding="utf-8")
    if p.stat().st_size > a.hedef_bayt:
        raise SystemExit("HATA: karsilastirma sayfasi boyut sinirini asti")


if __name__ == "__main__":
    main()
