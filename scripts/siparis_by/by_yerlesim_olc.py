#!/usr/bin/env python3
"""1st Anniversary (YD / Bizim Yilimiz v3) 8x10 yerlesim olcumu (Merkez 31 Eki 1a ek: zeminler oran basina Canva'da hazirlanacak). ETSY YOK.
Tasarim kodu bizim-yilimiz-v3 kod/by_poster.py (KOD_REF) DEGISTIRILMEDEN ice aktarilir; oge maskesi ureten fonksiyonlar (place, hero_mask,
names_full, same_size_full, text_full, divider_mask) sarmalanir, her cagrinin dondurdugu maskenin gercek piksel kutusu kaydedilir. Yani olcu
Olculer.json'daki niyet degil, cizilen posterdeki yerdir (ornek: PAIR / NAME1 / NAME2 / DATE / HEADING / LINE). Sembol boyu cifte, isim
satiri genisligi isme gore degisir: bu degerler ornege aittir; kutu MERKEZI ve yazi YUKSEKLIGI Olculer.json'dan gelir (ciftten bagimsiz).
NOT: isimler arasi kucuk yildiz ve tarih cevresindeki ince cizgiler (ayrac_cizgi_yildiz) zemin degil, KODLA cizilir (divider_mask).
zarf_78: 78 ciftin hepsinde hero_mask gercek kutusu + 12 burc isareti (Canva'da birakilacak en buyuk alan) ve isim / satir sinirlari.
zemin_cizgi: zemin rasterinda cerceve cizgisi (Starlit, FirstPage) ve cember (Starlit, Timeless) olcumu.
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
        if ad == "divider_mask":         # yildiz + iki cizgi: ayri parcalar (inceleme 31 Eki: tek kutu isimleri / tarihi kapsiyordu)
            n, lab, stt, _ = cv2.connectedComponentsWithStats((np.asarray(m) > ESIK).astype(np.uint8), 8)
            for i in sorted(range(1, n), key=lambda i: (stt[i, 1], stt[i, 0])):
                b = np.where(lab == i, 255, 0).astype(np.uint8)
                tur = "ayrac_yildiz" if stt[i, 3] > 3 * max(1, stt[i, 2]) / 4 else "ayrac_cizgi"
                r = kutu(Image.fromarray(b), W, H, tur + " (KODLA cizilir, zemin degil)", "by_poster.divider_mask")
                r and oge.append(r)
            continue
        r = kutu(m, W, H, {"left": "burc_isareti_sol", "right": "burc_isareti_sag"}.get(isim, isim), f"by_poster.{ad}")
        r and oge.append(r)
    return oge


HERO78 = {}


def hero78(bp, root):
    """Her cift alfasi BIR kez yuklenir (8185 px), 5 stilin hero kutusu birlikte olculur."""
    W, H = bp.W, bp.H
    eski = (bp.PAIR, bp.MASKS["hero"], bp.INK_P)
    for st in STIL:
        HERO78[st] = []
    try:
        for f in sorted(Path(root, "kaynak", "ana").glob("*_alfa.png")):
            pr = f.name[:-len("_alfa.png")].upper()
            if pr not in bp.REF_W:
                continue
            bp.PAIR = pr
            bp.MASKS["hero"] = bp.load_src(str(f))
            bp.INK_P = float(bp.MASKS["hero"].astype(np.float64).sum())
            for st in STIL:
                k = kutu(bp.hero_mask(bp.els(st)["hero"]), W, H, pr, "hero_mask")
                k and HERO78[st].append((pr, k["kutu_px"]))
    finally:
        bp.PAIR, bp.MASKS["hero"], bp.INK_P = eski


def zarf(bp, stil, root):
    """78 ciftin hepsinde (kaynak/ana/*_alfa.png) by_poster.hero_mask'in GERCEK kutusu ve 12 burc isaretinin sol / sag kutusu: Canva'da
    birakilacak en buyuk alan (inceleme 31 Eki: ornek ciftin kutusu yetmez). Isim ve kisa satirlar icin kodun sinirlari (by_poster)."""
    W, H = bp.W, bp.H
    e = bp.els(stil)
    hk = HERO78[stil]
    U = [min(b[0] for _, b in hk), min(b[1] for _, b in hk), max(b[2] for _, b in hk), max(b[3] for _, b in hk)]
    gen = sorted(hk, key=lambda t: t[1][2] - t[1][0]); yuk = sorted(hk, key=lambda t: t[1][3] - t[1][1])
    sk = {}
    for yan, ad in (("left", "burc_isareti_sol"), ("right", "burc_isareti_sag")):
        s = (e["left"]["width"] / 100 * W / bp.GLYPH_REF["CANCER"] + e["right"]["width"] / 100 * W / bp.GLYPH_REF["LIBRA"]) / 2
        bb = [kutu(bp.place(bp.sign_mask(b), s, e[yan]), W, H, b, "place")["kutu_px"] for b in bp.KUCUK]
        sk[ad] = dict(birlesik_kutu_px=[min(b[0] for b in bb), min(b[1] for b in bb), max(b[2] for b in bb), max(b[3] for b in bb)],
                      burc_sayisi=len(bb))
    return dict(
        hero=dict(cift_sayisi=len(hk), birlesik_kutu_px=U,
                  birlesik_kenar_oran=dict(sol=round(U[0] / W, 4), ust=round(U[1] / H, 4), sag=round((W - U[2]) / W, 4), alt=round((H - U[3]) / H, 4)),
                  en_dar=dict(cift=gen[0][0], kutu_px=gen[0][1]), en_genis=dict(cift=gen[-1][0], kutu_px=gen[-1][1]),
                  en_basik=dict(cift=yuk[0][0], kutu_px=yuk[0][1]), en_uzun=dict(cift=yuk[-1][0], kutu_px=yuk[-1][1]),
                  kural="by_poster.hero_mask: olcek = min(canli goreli boy, CANCER_LIBRA murekkep alani, %90 kutu yuksekligi, %115 kutu genisligi)"),
        **sk,
        isimler=dict(kural="iki isim ayni punto, ayni taban cizgisi; her biri en fazla 0.30 x W = " + str(round(0.30 * W)) + " px genislik "
                     "(asarsa ikisi birlikte kuculur); merkezler tasarim_niyeti SERDAR / LENA center_x, center_y",
                     en_fazla_genislik_px=round(0.30 * W)),
        kisa_satir=dict(kural="LINE (YEAR ONE) 'YEAR ONE' boyunda, en fazla 0.70 x W (Layers 'Paper' / 'Anniversary' satiri 0.86 x W, Layers "
                        "LINE 0.32 x W); tarih GENISLIGE gore sigdirilir (yukseklik metne gore degisir)"),
        golge_notu="kutular murekkep maskesi (> 64 / 255); altin golge / kagit kesimi golgesi kutunun 6-9 px disina tasar (bagimsiz inceleme 31 Eki)")


def zemin_cizgi(png, stil):
    """Zemin rasterindaki duz cerceve cizgisi (kenar profili) ve cember / yay (yinelemeli en kucuk kareler; bagimsiz inceleme daire2 yontemi).
    Yalniz bu stillerde anlamli: Starlit / FirstPage cerceve, Starlit / Timeless cember."""
    g = np.asarray(Image.open(png).convert("L")).astype(np.float64)
    hp = g - cv2.GaussianBlur(g, (0, 0), 6)
    H, W = g.shape
    out = {}
    if stil in ("1_Starlit", "3_FirstPage"):
        px = hp[1000:2000].mean(0); py = hp[:, 800:1600].mean(1)
        ara = lambda p, a, b: a + int(np.argmax(np.abs(p[a:b])))
        x0, x1, y0, y1 = ara(px, 20, 300), ara(px, W - 300, W - 10), ara(py, 20, 300), ara(py, H - 300, H - 10)
        pay = dict(sol=x0, sag=W - 1 - x1, ust=y0, alt=H - 1 - y1)
        esit = max(pay.values()) - min(pay.values()) <= 6
        out["cerceve_cizgi_px"] = dict(sol=x0, sag=x1, ust=y0, alt=y1, kenar_payi_px=pay,
                                       not_=("dort kenarda esit px pay (kenara orani W ve H'de farkli)" if esit else
                                             "yan pay ile ust / alt pay farkli; baska oranda hangisinin korunacagi kural karari"))
    if stil in ("1_Starlit", "2_Timeless"):
        isaret, c0 = (1, (1185, 1236, 943)) if stil == "1_Starlit" else (-1, (1183, 1240, 952))
        ys, xs = np.nonzero(isaret * hp > 20); xs = xs.astype(float); ys = ys.astype(float)
        cx, cy, r = c0
        for _ in range(4):
            k = np.abs(np.hypot(xs - cx, ys - cy) - r) < 25
            A = np.c_[2 * xs[k], 2 * ys[k], np.ones(k.sum())]; c = np.linalg.lstsq(A, xs[k] ** 2 + ys[k] ** 2, rcond=None)[0]
            cx, cy, r = c[0], c[1], float(np.sqrt(c[2] + c[0] ** 2 + c[1] ** 2))
        res = np.abs(np.hypot(xs[k] - cx, ys[k] - cy) - r)
        ang = np.degrees(np.arctan2(ys[k] - cy, xs[k] - cx))
        bos = [a for a in range(-180, 180, 15) if ((ang >= a) & (ang < a + 15)).sum() < 50]
        out["cember"] = dict(merkez_px=[round(cx), round(cy)], yaricap_px=round(r), kalinti_medyan_px=round(float(np.median(res)), 1),
                             bos_aci_araliklari_derece=bos, not_="raster cizim; alt kisimda bosluk var (kapali degil); tepe yildizi ve isiltilar rasterde")
    return out


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
    hero78(bp, root)
    for st in STIL:
        d = next(x for x in meas["designs"] if x["name"] == st)
        R["stiller"][st] = dict(
            olcum=olc_stil(bp, st),
            tasarim_niyeti=dict(ogeler=d["elements"], **{k: v for k, v in d.items() if k not in ("name", "elements")}),
            zarf_78=zarf(bp, st, root),
            zemin_cizgi=zemin_cizgi(Path(root, "z", "Baski_2400x3000_Buyutulmus", f"{st}_8x10_300ppi.png"), st))
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
