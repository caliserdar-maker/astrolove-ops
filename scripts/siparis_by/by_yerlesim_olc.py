#!/usr/bin/env python3
"""1st Anniversary (YD / Bizim Yilimiz v3) 8x10 yerlesim olcumu (Merkez 31 Eki 1a ek: zeminler oran basina Canva'da hazirlanacak). ETSY YOK.
Tasarim kodu bizim-yilimiz-v3 kod/by_poster.py (KOD_REF) DEGISTIRILMEDEN ice aktarilir; oge maskesi ureten fonksiyonlar (place, hero_mask,
names_full, same_size_full, text_full, divider_mask) sarmalanir, her cagrinin dondurdugu maskenin gercek piksel kutusu kaydedilir. Yani olcu
Olculer.json'daki niyet degil, cizilen posterdeki yerdir (ornek: PAIR / NAME1 / NAME2 / DATE / HEADING / LINE). Sembol boyu cifte, isim
satiri genisligi isme gore degisir: bu degerler ornege aittir; kutu MERKEZI ve yazi YUKSEKLIGI Olculer.json'dan gelir (ciftten bagimsiz).
NOT: isimler arasi kucuk yildiz ve tarih cevresindeki ince cizgiler (ayrac_cizgi_yildiz) zemin degil, KODLA cizilir (divider_mask).
Zemin ogeleri (cerceve, yay, yaprak, yildiz): zemin PNG'sinde yuksek frekans maskesi (by_boy2.maskeler ile ayni esik) -> her kenara en yakin
zemin ogesi uzakligi ve en buyuk bilesenlerin kutusu.
Kullanim: BY_ROOT=<bizim-yilimiz> by_yerlesim_olc.py --out <dir> [--pair CANCER_LIBRA --name1 EMILY --name2 JAMES]"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

STIL = ["1_Starlit", "2_Timeless", "3_FirstPage", "4_Layers", "5_Botanical"]
FN = {"1_Starlit": "starlit", "2_Timeless": "timeless", "3_FirstPage": "first_page", "4_Layers": "layers", "5_Botanical": "botanical"}
ESIK = 64          # maske > 64 / 255 (kenar yumusatmasinin yarisindan az kisim sayilmaz)


def kutu(m, W, H, ad, kaynak):
    a = np.asarray(m)
    ys, xs = np.nonzero(a > ESIK)
    if not len(xs):
        return None
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    return dict(oge=ad, kaynak=kaynak, kutu_px=[x0, y0, x1, y1], gen_px=x1 - x0, yuk_px=y1 - y0,
                merkez_yuzde=[round((x0 + x1) / 2 / W * 100, 2), round((y0 + y1) / 2 / H * 100, 2)],
                gen_yuzde_W=round((x1 - x0) / W * 100, 2), yuk_yuzde_H=round((y1 - y0) / H * 100, 2),
                kenar_px=dict(sol=x0, ust=y0, sag=W - x1, alt=H - y1),
                kenar_oran=dict(sol=round(x0 / W, 4), ust=round(y0 / H, 4), sag=round((W - x1) / W, 4), alt=round((H - y1) / H, 4)))


def modul(root):
    spec = importlib.util.spec_from_file_location("by_poster", Path(root, "kod", "by_poster.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def olc_stil(bp, stil):
    W, H = bp.W, bp.H
    kayit = []

    def sar(ad, adlandir):
        asil = getattr(bp, ad)

        def f(*a, **k):
            r = asil(*a, **k)
            kayit.append((ad, adlandir(a, k), r))
            return r
        setattr(bp, ad, f)
        return asil

    asillar = {
        "place": sar("place", lambda a, k: a[2]["element"]),
        "hero_mask": sar("hero_mask", lambda a, k: "hero"),
        "names_full": sar("names_full", lambda a, k: "isimler"),
        "same_size_full": sar("same_size_full", lambda a, k: f"{a[1]} ({a[0]})"),
        "text_full": sar("text_full", lambda a, k: a[3]["element"] + f" ({a[0]})"),
        "divider_mask": sar("divider_mask", lambda a, k: "ayrac_cizgi_yildiz"),
    }
    try:
        getattr(bp, FN[stil])()
    finally:
        for ad, f in asillar.items():
            setattr(bp, ad, f)
    oge, gor = [], set()
    for ad, isim, m in kayit:
        if ad == "place" and isim == "hero":
            continue                      # hero_mask icinde (ayni kutu)
        k = isim
        if k in gor:                      # same_size_full ic cagrisi text_full: ayni oge bir kez
            continue
        gor.add(k)
        if ad == "names_full":            # iki isim tek maskede: sol / sag yari
            a = np.asarray(m)
            for yan, sl in (("isim_sol (NAME1)", slice(0, W // 2)), ("isim_sag (NAME2)", slice(W // 2, W))):
                b = np.zeros_like(a); b[:, sl] = a[:, sl]
                r = kutu(Image.fromarray(b), W, H, yan, "by_poster.names_full")
                r and oge.append(r)
            continue
        r = kutu(m, W, H, {"left": "burc_isareti_sol", "right": "burc_isareti_sag"}.get(isim, isim), f"by_poster.{ad}")
        r and oge.append(r)
    return oge


def zemin_ogeleri(png):
    bg = np.asarray(Image.open(png).convert("RGB"))
    H, W = bg.shape[:2]
    g = cv2.cvtColor(bg, cv2.COLOR_RGB2GRAY).astype(np.float32)
    z = np.abs(g - cv2.GaussianBlur(g, (0, 0), max(8.0, W / 96))) > 18
    z = cv2.morphologyEx(z.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(z, 8)
    buyuk = sorted(range(1, n), key=lambda i: -st[i, 4])[:6]
    ys, xs = np.nonzero(z)
    yakin = dict(sol=int(xs.min()), ust=int(ys.min()), sag=int(W - 1 - xs.max()), alt=int(H - 1 - ys.max())) if len(xs) else None
    # her kenarin 0.5 % bandinda zemin ogesi pikseli (kenara degen oge var mi)
    b = max(3, round(0.005 * H))
    degen = dict(sol=int(z[:, :b].sum()), ust=int(z[:b].sum()), sag=int(z[:, W - b:].sum()), alt=int(z[H - b:].sum()))
    return dict(boyut=[W, H], esik="gri - GaussianBlur(sigma W/96) > 18, acma 2x2 (by_boy2.maskeler ile ayni)",
                kenara_en_yakin_oge_px=yakin, kenar_bandi_oge_px=dict(bant_px=b, **degen),
                en_buyuk_bilesenler=[dict(kutu_px=[int(st[i, 0]), int(st[i, 1]), int(st[i, 0] + st[i, 2]), int(st[i, 1] + st[i, 3])],
                                          alan_px=int(st[i, 4])) for i in buyuk])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pair", default="CANCER_LIBRA")
    ap.add_argument("--name1", default="EMILY")
    ap.add_argument("--name2", default="JAMES")
    a = ap.parse_args(argv)
    root = os.environ["BY_ROOT"]
    os.environ.update(PAIR=a.pair, NAME1=a.name1, NAME2=a.name2, DATE="12 JUNE 2025", HEADING="Paper Anniversary", LINE="",
                      SCALE="1", OUT=str(Path(a.out, "_cizim")))
    bp = modul(root)
    meas = json.loads(Path(root, "z", "Olculer.json").read_text())
    R = dict(aciklama=("8x10 = 2400x3000 px (300 dpi). olcum = cizilen posterde maskenin gercek kutusu (ornek: "
                       f"{a.pair}, {a.name1} / {a.name2}, 12 JUNE 2025, Paper Anniversary, YEAR ONE); kenar_oran = kenar_px / W (sol, sag) "
                       "ya da / H (ust, alt). Sembol boyu cifte, isim genisligi isme gore degisir; tasarim_niyeti = Olculer.json (yuzde, "
                       "ciftten bagimsiz merkez ve yukseklik)."),
             kaynak=dict(kod="bizim-yilimiz-v3 kod/by_poster.py (degistirilmedi)", olculer="z/Olculer.json",
                         zemin="z/Baski_2400x3000_Buyutulmus/<stil>_8x10_300ppi.png"),
             ornek=dict(pair=a.pair, name1=a.name1, name2=a.name2, date="12 JUNE 2025", heading="Paper Anniversary", line="YEAR ONE"),
             olculer_birim=meas.get("units"), stiller={})
    kontak = []
    for st in STIL:
        d = next(x for x in meas["designs"] if x["name"] == st)
        R["stiller"][st] = dict(
            olcum=olc_stil(bp, st),
            tasarim_niyeti=dict(ogeler=d["elements"], **{k: v for k, v in d.items() if k not in ("name", "elements")}),
            zemin_ogeleri=zemin_ogeleri(Path(root, "z", "Baski_2400x3000_Buyutulmus", f"{st}_8x10_300ppi.png")))
        print(st, len(R["stiller"][st]["olcum"]), "oge", flush=True)
        im = Image.open(Path(root, "z", "Baski_2400x3000_Buyutulmus", f"{st}_8x10_300ppi.png")).convert("RGB")
        from PIL import ImageDraw
        dr = ImageDraw.Draw(im)
        for o in R["stiller"][st]["olcum"]:
            dr.rectangle(o["kutu_px"], outline=(255, 0, 90), width=6)
            dr.text((o["kutu_px"][0] + 8, o["kutu_px"][1] + 4), o["oge"].split(" (")[0], fill=(255, 0, 90))
        kontak.append(im.resize((600, 750), Image.LANCZOS))
    Path(a.out).mkdir(parents=True, exist_ok=True)
    K = Image.new("RGB", (600 * 5 + 20 * 6, 790), (236, 236, 236))
    for i, im in enumerate(kontak):
        K.paste(im, (20 + i * 620, 20))
    K.save(Path(a.out, "KONTAK_YERLESIM.jpg"), quality=90)
    Path(a.out, "YERLESIM_8x10.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
