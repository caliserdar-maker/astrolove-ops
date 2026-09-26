#!/usr/bin/env python3
"""
DIJITAL 78 - kapak uzerine MUZE ETIKETI PLAKASI (canli POD kapagindan).

Eski V1-V3 etiketleri reddedildi: postere biniyordu, gri ince yazi 200 px'te
okunmuyordu, tam genislik bantlar sahneyi kesiyordu. Bu surum:
  - Cercevenin ALT RAYI olculur (poster alt kenarindan asagi ilk sicak bant).
  - Plaka o rayin uzerine oturur: koyu lacivert zemin, ince altin kenar,
    altin metin, eski etiketin ~1.8 kati punto, tok agirlik, yumusak golge.
  - KAPI: plaka dikdortgeni ile poster ic alani kesisimi = 0 piksel
    (hem olculen poster alani hem de altin artwork maskesi ile).
Cikti: KAPAK_PLAKA.jpg (2400x3000) + KAPAK_V2.jpg (etiketsiz | plakali +
arama karti simulasyonu 300/200 px) + KAPAK_PLAKA_NOT.json
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

KAPAK = (2400, 3000)
KARE_KIRPIM = (300, 2700)                 # ortadan kare kirpim (arama karti)
ARTWORK_ZONES = [(650, 1735, 565, 1870), (1775, 2165, 630, 1810), (2260, 2425, 900, 1540)]
ETIKET = "INSTANT DOWNLOAD · 5 COLORS"
LACI = (20, 29, 52)
ALTIN = (203, 167, 98)
KREM = (238, 231, 217)


def poster_ve_cerceve(im):
    """Poster alt kenari ve cerceve alt rayini OLC (tahmin yok).
    Poster: soguk/koyu (b > r). Cerceve: sicak (r > b + esik)."""
    a = np.asarray(im.convert("RGB"), dtype=np.int16)
    serit = a[:, 1000:1400, :].mean(axis=1)                 # orta sutun seridi
    r, b = serit[:, 0], serit[:, 2]
    soguk = b > r + 6
    sicak = r > b + 14
    alt_artwork = max(z[1] for z in ARTWORK_ZONES)
    poster_alt = alt_artwork
    for y in range(alt_artwork, KAPAK[1] - 1):
        if not soguk[y] and not soguk[min(y + 1, KAPAK[1] - 1)]:
            poster_alt = y
            break
    ray_bas = ray_son = None
    for y in range(poster_alt, min(poster_alt + 420, KAPAK[1] - 20)):
        if sicak[y:y + 12].all():
            ray_bas = y
            break
    if ray_bas is not None:
        for y in range(ray_bas, min(ray_bas + 500, KAPAK[1] - 1)):
            if not sicak[y:y + 8].any():
                ray_son = y
                break
        ray_son = ray_son or min(ray_bas + 260, KAPAK[1] - 1)
    ray_x = None
    if ray_bas is not None and ray_son is not None:
        y = int((ray_bas + ray_son) / 2)
        satir = a[y]
        sicak_x = np.where(satir[:, 0] > satir[:, 2] + 14)[0]
        if sicak_x.size > 200:
            ray_x = (int(sicak_x.min()), int(sicak_x.max()))
    return poster_alt, ray_bas, ray_son, ray_x


def artwork_maskesi(im):
    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    zones = np.zeros(a.shape[:2], dtype=bool)
    for y0, y1, x0, x1 in ARTWORK_ZONES:
        zones[y0:y1, x0:x1] = True
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return zones & (r > 44) & (g > 29) & (r > b * 1.16) & (g > b * 1.04) & (r > g * 1.01)


def plaka_ciz(im, kutu, fonts, punto_kat=1.0):
    """kutu = (x0, y0, x1, y1). Koyu zemin + ince altin kenar + altin metin + golge."""
    from PIL import ImageFont
    x0, y0, x1, y1 = kutu
    w, h = x1 - x0, y1 - y0
    kat = im.copy().convert("RGBA")
    golge = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(golge).rounded_rectangle([x0 + 6, y0 + 14, x1 + 6, y1 + 16], radius=10,
                                            fill=(0, 0, 0, 120))
    golge = golge.filter(ImageFilter.GaussianBlur(14))
    kat.alpha_composite(golge)
    plaka = Image.new("RGBA", (w, h), LACI + (250,))
    d = ImageDraw.Draw(plaka)
    d.rectangle([0, 0, w - 1, h - 1], outline=ALTIN + (255,), width=3)
    d.rectangle([9, 9, w - 10, h - 10], outline=ALTIN + (120,), width=1)
    boy = int(h * 0.46 * punto_kat)
    f = ImageFont.truetype(str(Path(fonts) / "Montserrat[wght].ttf"), boy)
    try:
        f.set_variation_by_axes([700])
    except Exception:                                        # noqa: BLE001
        pass
    tr = max(3, int(boy * 0.10))
    genislik = sum(d.textlength(c, font=f) for c in ETIKET) + tr * (len(ETIKET) - 1)
    while genislik > w - 70 and boy > 10:
        boy -= 2
        f = ImageFont.truetype(str(Path(fonts) / "Montserrat[wght].ttf"), boy)
        try:
            f.set_variation_by_axes([700])
        except Exception:                                    # noqa: BLE001
            pass
        tr = max(3, int(boy * 0.10))
        genislik = sum(d.textlength(c, font=f) for c in ETIKET) + tr * (len(ETIKET) - 1)
    kb = f.getbbox("H")
    x = (w - genislik) / 2
    y = (h - (kb[3] - kb[1])) / 2 - kb[1]
    for ch in ETIKET:
        d.text((x, y), ch, font=f, fill=ALTIN)
        x += d.textlength(ch, font=f) + tr
    kat.alpha_composite(plaka, (x0, y0))
    return kat.convert("RGB"), (kb[3] - kb[1])


def arama_karti(im, px):
    y0, y1 = KARE_KIRPIM
    kare = im.crop(((im.width - (y1 - y0)) // 2, y0, (im.width + (y1 - y0)) // 2, y1))
    return kare.resize((px, px), Image.LANCZOS)


def kaydet_sinirli(im, yol, sinir):
    for q in (95, 92, 88, 84, 80, 74):
        im.save(yol, "JPEG", quality=q, optimize=True, subsampling=0 if q >= 88 else 1)
        if yol.stat().st_size <= sinir:
            return q
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kapak", required=True)
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plaka-genislik", type=float, default=0.46, help="kapak genisliginin orani")
    ap.add_argument("--plaka-yukseklik", type=int, default=190)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    im = Image.open(a.kapak).convert("RGB")
    if im.size != KAPAK:
        im = im.resize(KAPAK, Image.LANCZOS)

    poster_alt, ray_bas, ray_son, ray_x = poster_ve_cerceve(im)
    print(f"olcum: poster alt kenari y={poster_alt} | cerceve alt rayi "
          f"{ray_bas}-{ray_son} | cerceve x {ray_x}", flush=True)
    h = a.plaka_yukseklik
    if ray_bas is not None and ray_son is not None and ray_son - ray_bas > 40:
        merkez = (ray_bas + ray_son) / 2
    else:
        merkez = poster_alt + 120
        print("::warning::cerceve rayi olculemedi, poster altina 120 px yerlestirildi", flush=True)
    y0 = int(merkez - h / 2)
    y0 = max(y0, poster_alt + 12)                            # postere sifir temas
    y1 = min(y0 + h, KARE_KIRPIM[1] - 24)                    # kare kirpimda kalsin
    w = int(KAPAK[0] * a.plaka_genislik)
    if ray_x:
        w = min(w, int((ray_x[1] - ray_x[0]) * 0.82))        # plaka cerceveden dar kalsin
        merkez_x = (ray_x[0] + ray_x[1]) / 2
    else:
        merkez_x = KAPAK[0] / 2
    x0 = int(merkez_x - w / 2)
    kutu = (x0, y0, x0 + w, y1)

    maske = artwork_maskesi(im)
    kesisim_artwork = int(maske[y0:y1, x0:x0 + w].sum())
    kesisim_poster = max(0, poster_alt - y0) * w if y0 < poster_alt else 0
    plakali, cap = plaka_ciz(im, kutu, a.fonts)
    plakali.save(out / "KAPAK_PLAKA.jpg", "JPEG", quality=95, optimize=True, subsampling=0)

    kartlar = {}
    for px in (300, 200):
        kartlar[px] = (arama_karti(im, px), arama_karti(plakali, px))
    kapi = "GECTI" if kesisim_artwork == 0 and kesisim_poster == 0 else "KALDI"
    not_json = {
        "poster_alt_kenari": int(poster_alt), "cerceve_rayi": [ray_bas, ray_son],
        "cerceve_x": list(ray_x) if ray_x else None,
        "plaka_kutu": list(kutu), "plaka_yuksekligi_px": y1 - y0,
        "metin_cap_yuksekligi_px": int(cap),
        "kesisim_artwork_px": kesisim_artwork, "kesisim_poster_px": int(kesisim_poster),
        "kapi_poster_kesisimi": kapi,
        "plaka_yuksekligi_200px_kartta": round((y1 - y0) * 200 / (KARE_KIRPIM[1] - KARE_KIRPIM[0]), 1),
        "metin_cap_200px_kartta": round(cap * 200 / (KARE_KIRPIM[1] - KARE_KIRPIM[0]), 1),
        "kare_kirpimda_kaliyor": bool(y1 <= KARE_KIRPIM[1] and y0 >= KARE_KIRPIM[0]),
    }
    (out / "KAPAK_PLAKA_NOT.json").write_text(json.dumps(not_json, indent=2), encoding="utf-8")
    print(json.dumps(not_json, ensure_ascii=False), flush=True)

    # ------------------------------------------------------------ KAPAK_V2 sayfasi
    from PIL import ImageFont
    f_b = ImageFont.truetype(str(Path(a.fonts) / "Montserrat[wght].ttf"), 34)
    f_n = ImageFont.truetype(str(Path(a.fonts) / "Montserrat[wght].ttf"), 26)
    ust_h = 980
    ust_w = int(KAPAK[0] * ust_h / KAPAK[1])
    kenar, ara = 60, 70
    sayfa_w = kenar * 2 + ust_w * 2 + ara
    sayfa_h = kenar + 70 + ust_h + 60 + 300 + 150 + kenar
    sayfa = Image.new("RGB", (sayfa_w, sayfa_h), (250, 250, 248))
    d = ImageDraw.Draw(sayfa)
    d.text((kenar, 34), "KAPAK V2  ·  ETIKETSIZ vs PLAKA  ·  ARAMA KARTI SIMULASYONU",
           font=f_b, fill=(28, 38, 62))
    for i, (baslik, gorsel) in enumerate((("ETIKETSIZ (canli POD kapagi)", im),
                                          ("PLAKALI (yeni)", plakali))):
        x = kenar + i * (ust_w + ara)
        y = kenar + 70
        sayfa.paste(gorsel.resize((ust_w, ust_h), Image.LANCZOS), (x, y))
        d.rectangle([x, y, x + ust_w - 1, y + ust_h - 1], outline=(214, 212, 206), width=2)
        d.text((x, y + ust_h + 14), baslik, font=f_n, fill=(40, 44, 58))
        k300, k200 = kartlar[300][i], kartlar[200][i]
        ky = y + ust_h + 60
        sayfa.paste(k300, (x, ky))
        d.rectangle([x, ky, x + 299, ky + 299], outline=(214, 212, 206), width=2)
        sayfa.paste(k200, (x + 330, ky + 50))
        d.rectangle([x + 330, ky + 50, x + 529, ky + 249], outline=(214, 212, 206), width=2)
        d.text((x, ky + 310), "300 px", font=f_n, fill=(90, 92, 100))
        d.text((x + 330, ky + 310), "200 px", font=f_n, fill=(90, 92, 100))
    d.text((kenar, sayfa_h - kenar - 60),
           f"plaka {kutu[2]-kutu[0]}x{y1-y0} px · metin cap {int(cap)} px · "
           f"200 px kartta plaka {not_json['plaka_yuksekligi_200px_kartta']} px, "
           f"metin {not_json['metin_cap_200px_kartta']} px · "
           f"poster kesisimi {kesisim_artwork + int(kesisim_poster)} px ({kapi})",
           font=f_n, fill=(95, 95, 100))
    q = kaydet_sinirli(sayfa, out / "KAPAK_V2.jpg", 800_000)
    print(f"KAPAK_V2.jpg {sayfa.size} q{q} "
          f"{(out / 'KAPAK_V2.jpg').stat().st_size/1e3:.0f} KB | kapi {kapi}", flush=True)
    if kapi != "GECTI":
        raise SystemExit("HATA: plaka poster alanina giriyor")


if __name__ == "__main__":
    main()
