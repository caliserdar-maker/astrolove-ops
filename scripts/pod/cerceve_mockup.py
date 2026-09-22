#!/usr/bin/env python3
"""CERCEVELI MOCKUP ORNEKLERI (22 Eyl 2026) — toplu uretim YOK, yalniz ornek.

Pilot cift, Midnight Blue, 4:5 poster. 3 cerceve rengi (black / white / natural) x 2 sahne:
  A) duz urun gorseli  — notr studyo zemini, gercekci cerceve profili + golge + cam yansimasi
  B) oda sahnesi       — mevcut koyu oda karemizin duvarina yerlestirme

KURAL: posterin pikselleri DEGISMEZ; yalnizca olceklenir (LANCZOS) ve yerlestirilir.
Cerceve, golge ve cam yansimasi posterin DISINA / USTUNE ayri katman olarak cizilir.
Cikti: <out>/CERCEVE_<RENK>_<SAHNE>.jpg, 2400x3000 (4:5), Etsy'ye YUKLEME YOK.
"""
import argparse
import pathlib
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

Image.MAX_IMAGE_PIXELS = None
W, H = 2400, 3000                    # cikti tuvali (4:5)
T0 = time.time()

# Cerceve profilleri: (dis kenar rengi, ic egim rengi, ic dudak rengi, ahsap damari?)
RENKLER = {
    "black":   {"ad": "Framed, Black",   "dis": (26, 26, 28),  "egim": (46, 46, 50),
                "dudak": (12, 12, 14),  "damar": False},
    "white":   {"ad": "Framed, White",   "dis": (246, 245, 242), "egim": (255, 255, 253),
                "dudak": (214, 212, 206), "damar": False},
    "natural": {"ad": "Framed, Natural", "dis": (196, 172, 138), "egim": (214, 193, 163),
                "dudak": (163, 138, 106), "damar": True},
}


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise SystemExit(f"HATA: rclone {a[0]}: {r.stderr.strip()[-200:]}")
    return r


def _streak(boy, eksen, tohum):
    """Tek yonlu (uzun) damar alani: eksen=0 yatay cizgiler, 1 dikey cizgiler."""
    tw, th = boy
    rng = np.random.default_rng(tohum)
    g = rng.normal(0, 1, (th, tw)).astype(np.float32)
    im = Image.fromarray(np.clip((g * 40 + 128), 0, 255).astype(np.uint8), "L")
    # anizotropik bulaniklik: uzunluk yonunde cok, en yonunde az
    if eksen == 0:
        im = im.filter(ImageFilter.GaussianBlur(1.6)).resize((max(tw // 48, 1), th), Image.BILINEAR)
        im = im.resize((tw, th), Image.BILINEAR)
    else:
        im = im.filter(ImageFilter.GaussianBlur(1.6)).resize((tw, max(th // 48, 1)), Image.BILINEAR)
        im = im.resize((tw, th), Image.BILINEAR)
    a = np.asarray(im, dtype=np.float32)
    a = (a - a.mean()) / (a.std() + 1e-9)
    return np.clip(a, -2.2, 2.2)


def ahsap_damari(boy, kalinlik, tohum=7):
    """Mese damari: ust/alt raylarda YATAY, sag/sol raylarda DIKEY akar (-1..1)."""
    tw, th = boy
    yatay, dikey = _streak(boy, 0, tohum), _streak(boy, 1, tohum + 1)
    yy, xx = np.mgrid[0:th, 0:tw]
    # hangi raydayiz: kenara olan yatay/dikey uzaklik karsilastirmasi (gonye mantigi)
    dx = np.minimum(xx, tw - 1 - xx)
    dy = np.minimum(yy, th - 1 - yy)
    ust_alt = (dy <= dx).astype(np.float32)
    g = yatay * ust_alt + dikey * (1 - ust_alt)
    return np.clip(g * 0.45, -1, 1)


def cerceve_ciz(poster, renk, kalinlik, lip=14):
    """Posteri cerceveler. Donus: (RGBA kare, poster_kutusu). Poster pikselleri degismez."""
    c = RENKLER[renk]
    pw, ph = poster.size
    tw, th = pw + 2 * (kalinlik + lip), ph + 2 * (kalinlik + lip)
    kare = Image.new("RGB", (tw, th), c["dis"])
    a = np.asarray(kare, dtype=np.float32)

    # dis profil: kenardan ice dogru hafif egim (isigi ust-soldan al)
    yy, xx = np.mgrid[0:th, 0:tw]
    d = np.minimum(np.minimum(xx, tw - 1 - xx), np.minimum(yy, th - 1 - yy)).astype(np.float32)
    egim = np.clip(d / max(kalinlik, 1), 0, 1)                   # 0 dis kenar -> 1 ic kenar
    ust_sol = ((xx / tw) * -1 + (yy / th) * -1 + 1)               # +0.5 ust-sol, -0.5 alt-sag
    k = np.array(c["dis"], dtype=np.float32)
    k2 = np.array(c["egim"], dtype=np.float32)
    a = k[None, None, :] + (k2 - k)[None, None, :] * egim[..., None]
    a *= (1.0 + 0.10 * ust_sol[..., None])                        # yonlu isik
    if c["damar"]:
        a *= (1.0 + 0.055 * ahsap_damari((tw, th), kalinlik)[..., None])
    a = np.clip(a, 0, 255)

    kare = Image.fromarray(a.astype(np.uint8), "RGB")
    d0 = ImageDraw.Draw(kare)
    # ic dudak (cerceve ile baski arasindaki koyu ince cizgi)
    x0, y0 = kalinlik, kalinlik
    x1, y1 = tw - kalinlik, th - kalinlik
    d0.rectangle([x0, y0, x1 - 1, y1 - 1], fill=c["dudak"])
    # baskinin kendisi: SADECE yerlestirilir
    px, py = kalinlik + lip, kalinlik + lip
    kare.paste(poster, (px, py))

    # cam: ust-soldan gelen genis, yumusak yansima + cok hafif genel parlaklik
    cam = Image.new("L", (tw, th), 0)
    dc = ImageDraw.Draw(cam)
    dc.polygon([(px, py), (px + pw * 0.58, py), (px, py + ph * 0.66)], fill=40)
    dc.polygon([(px + pw * 0.82, py), (px + pw, py), (px + pw, py + ph * 0.22)], fill=20)
    cam = cam.filter(ImageFilter.GaussianBlur(pw * 0.035))
    beyaz = Image.new("RGB", (tw, th), (255, 255, 255))
    kare = Image.composite(Image.blend(kare, beyaz, 0.30), kare, cam.point(lambda v: v * 2))
    return kare.convert("RGBA"), (px, py, pw, ph)


def golge(boyut, kutu, yaricap, kacis, siyahlik=150):
    """Yumusak dusen golge katmani (RGBA)."""
    g = Image.new("L", boyut, 0)
    ImageDraw.Draw(g).rectangle([kutu[0] + kacis[0], kutu[1] + kacis[1],
                                 kutu[2] + kacis[0], kutu[3] + kacis[1]], fill=siyahlik)
    g = g.filter(ImageFilter.GaussianBlur(yaricap))
    kat = Image.new("RGBA", boyut, (0, 0, 0, 0))
    kat.putalpha(g)
    return kat


def sahne_duz(kare, kutu_olcu):
    """A) Notr studyo zemini: yumusak dikey degrade + zemin golgesi."""
    zemin = np.zeros((H, W, 3), dtype=np.float32)
    ust, alt = np.array([238, 236, 232], np.float32), np.array([214, 210, 204], np.float32)
    t = np.linspace(0, 1, H)[:, None, None]
    zemin[:] = ust[None, None, :] * (1 - t) + alt[None, None, :] * t
    vig = np.linspace(-1, 1, W)[None, :, None] ** 2 + np.linspace(-1, 1, H)[:, None, None] ** 2
    zemin *= (1 - 0.06 * np.clip(vig, 0, 1))
    im = Image.fromarray(np.clip(zemin, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    fw, fh = kare.size
    olcek = min((W * 0.72) / fw, (H * 0.78) / fh)
    kare2 = kare.resize((round(fw * olcek), round(fh * olcek)), Image.LANCZOS)
    fx, fy = (W - kare2.width) // 2, (H - kare2.height) // 2
    kutu = (fx, fy, fx + kare2.width, fy + kare2.height)
    im.alpha_composite(golge(im.size, kutu, kare2.width * 0.035, (0, round(kare2.height * 0.02)), 120))
    im.alpha_composite(kare2, (fx, fy))
    return im.convert("RGB"), olcek


def duvar_kutusu(oda, oran, pay=0.42):
    """Oda karesinde cerceveyi koyacagimiz duvar kutusu: ust-orta bolge, oran korunur."""
    ow, oh = oda.size
    yh = oh * pay
    yw = yh / oran
    if yw > ow * 0.46:
        yw = ow * 0.46
        yh = yw * oran
    x = (ow - yw) / 2
    y = oh * 0.17
    return round(x), round(y), round(yw), round(yh)


def sahne_oda(kare, oda_yolu):
    """B) Mevcut koyu oda karesi: cerceveli is duvara yerlestirilir."""
    oda = Image.open(oda_yolu).convert("RGB")
    # 4:5 cikti icin oda karesinden merkezden kirp
    ow, oh = oda.size
    hedef = W / H
    if ow / oh > hedef:
        yeni_w = round(oh * hedef)
        oda = oda.crop(((ow - yeni_w) // 2, 0, (ow - yeni_w) // 2 + yeni_w, oh))
    else:
        yeni_h = round(ow / hedef)
        oda = oda.crop((0, 0, ow, yeni_h))
    oda = oda.resize((W, H), Image.LANCZOS).convert("RGBA")

    fw, fh = kare.size
    x, y, yw, yh = duvar_kutusu(oda, fh / fw)
    kare2 = kare.resize((yw, yh), Image.LANCZOS)
    oda.alpha_composite(golge(oda.size, (x, y, x + yw, y + yh), yw * 0.05,
                              (round(yw * 0.012), round(yh * 0.018)), 165))
    oda.alpha_composite(kare2, (x, y))
    return oda.convert("RGB"), (x, y, yw, yh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poster", required=True, help="4:5 poster dosyasi (yerel)")
    ap.add_argument("--oda", default="", help="koyu oda karesi (yerel); bos = B sahnesi atlanir")
    ap.add_argument("--out", default="_out/mockup")
    ap.add_argument("--renkler", default="black,white,natural")
    ap.add_argument("--kalinlik-oran", type=float, default=0.055,
                    help="cerceve kalinligi / poster genisligi (Prodigi Classic ~%5-6)")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    poster = Image.open(a.poster).convert("RGB")
    pw, ph = poster.size
    log(f"poster: {pw}x{ph} (oran {ph/pw:.4f}; 4:5 = 1.25)")
    if abs(ph / pw - 1.25) > 0.02:
        raise SystemExit(f"DUR: poster orani 4:5 degil ({ph/pw:.4f})")
    # posteri cikti olceginde bir kez olcekle (tek yeniden orneklemeyle)
    hedef_w = round(W * 0.60)
    poster = poster.resize((hedef_w, round(hedef_w * 1.25)), Image.LANCZOS)
    kalinlik = max(8, round(poster.width * a.kalinlik_oran))

    satir = []
    for renk in [r.strip() for r in a.renkler.split(",") if r.strip()]:
        kare, pkutu = cerceve_ciz(poster, renk, kalinlik)
        im, olcek = sahne_duz(kare, kare.size)
        p = out / f"CERCEVE_{renk}_DUZ.jpg"
        im.save(p, "JPEG", quality=92, optimize=True)
        satir.append((p.name, im.size, round(kalinlik * olcek)))
        log(f"{renk} DUZ: {p.name} {im.size} | cerceve {kalinlik}px -> {kalinlik*olcek:.0f}px")
        if a.oda:
            im2, kutu = sahne_oda(kare, a.oda)
            p2 = out / f"CERCEVE_{renk}_ODA.jpg"
            im2.save(p2, "JPEG", quality=92, optimize=True)
            satir.append((p2.name, im2.size, kutu))
            log(f"{renk} ODA: {p2.name} {im2.size} | duvar kutusu {kutu}")
    log(f"uretilen dosya: {len(satir)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
