#!/usr/bin/env python3
"""
Kisisellestirme pilotu v3 (Mo, 21 Eyl 2026) - asamalar ayri surecte.

Karar: font aramasi bitti. Isim = Cinzel wght 500, tagline = EB Garamond
Italic 700. Altin doku yontemi aynen (stil testi gecti: maks kanal farki 2/8).

v2'de 'uret' asamasi 28+ dk takildi ve ne SIGALRM asama siniri ne job
timeout'u tetiklendi -> is, Python'a donmeyen tek bir C cagrisindaydi (dev
bilesenlerin PIL ile cozulmesi/olceklenmesi). Bu surumde:
  1) Yeni 'hazirla' asamasi her bileseni hedef kutusuna kuculterek HAZIR/
     altina yazar; uret ve yakin YALNIZ bu kucuk kopyalarla calisir.
  2) Her asama AYRI SUREC olarak timeout=480 ile kosar; C cagrisinda takilsa
     bile oldurulur (surec ici sinyal yetmiyordu).
  3) Her cikti uretildigi anda Drive'a yazilir.

Kullanim:
  python pilot3.py             -> tum asamalari sirayla, her biri ayri surecte
  python pilot3.py --adim ADI  -> tek asamayi bu surecte kosar (orkestratorun
                                  cagirdigi bicim)
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from kisisel_pilot import (BOX, DEST, FOLDERS, FONT_DIR, NEW_LEFT, NEW_RIGHT,
                           ORIG_TAGLINE, TAGLINES, bbox_of, cap_icin_boyut,
                           ciz_metin, fetch, font_yukle, ink_mask, iou, lsf, rc,
                           tracking_icin)

Image.MAX_IMAGE_PIXELS = None          # bilincli: bilesenler 60-120 Mpx

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
REF = OUT / "ref"
HAZIR = OUT / "hazir"
DURUM = OUT / "durum.json"

OLCEK = 0.6
TUVAL = (2400, 3000)
IOU_H = 200
TR_TEST = "ğıİöüşçŞÇÜÖ"

ISIM_FONT, ISIM_W = "Cinzel.ttf", 500
TAG_FONT, TAG_W = "EBGaramond-Italic.ttf", 700

B = {k: tuple(v * OLCEK for v in box) for k, box in BOX.items()}     # top,left,w,h

# hazirla: hangi referans hangi kutunun boyutuna kuculecek
BILESEN = [
    ("parts/midnight_blue_bg.jpg", "bg", "bg.png"),
    ("parts/circle.png", "ring", "ring.png"),
    ("main/*", "main", "main.png"),
    ("small/cancer*", "sym_left", "sym_left.png"),
    ("small/libra*", "sym_right", "sym_right.png"),
    ("parts/logo.png", "infinity", "infinity.png"),
    ("names/cancer_name_gold.png", "name_left", "orij_name_left.png"),
    ("names/libra_name_gold.png", "name_right", "orij_name_right.png"),
    ("parts/tagline.png", "tagline", "orij_tagline.png"),
]

T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def gonder(ad, alt=""):
    p = OUT / ad
    if not p.exists():
        log(f"gonderilemedi (yok): {ad}")
        return
    try:
        rc("copy", str(p), DEST + (f"/{alt}" if alt else ""))
        log(f"Drive <- {alt + '/' if alt else ''}{ad} ({p.stat().st_size / 1e3:.0f} KB)")
    except Exception as e:
        log(f"Drive yazilamadi {ad}: {str(e)[:140]}")


def durum_oku():
    return json.loads(DURUM.read_text()) if DURUM.exists() else {}


def durum_yaz(d):
    DURUM.write_text(json.dumps(d, ensure_ascii=False))


def ref_yol(desen):
    k, ad = desen.split("/", 1)
    d = REF / k
    if ad.endswith("*"):
        return sorted(d.glob(ad))[0]
    if "*" in ad:
        return sorted(d.glob(ad))[0]
    return d / ad


# ------------------------------------------------------------------ asamalar


def a_indir(d):
    import re
    klas = {k: lsf(v) for k, v in FOLDERS.items()}

    def bul(k, kalip):
        for f in klas[k]:
            if re.fullmatch(kalip, f, re.I):
                return f
        raise FileNotFoundError(f"{k}: {kalip} yok -> {klas[k][:10]}")

    istek = [("names", "cancer_name_gold.png"), ("names", "libra_name_gold.png"),
             ("parts", "tagline.png"), ("parts", "logo.png"), ("parts", "circle.png"),
             ("parts", "midnight_blue_bg.jpg"),
             ("main", bul("main", r"(cancer_libra|libra_cancer)_gold\.png")),
             ("small", bul("small", r"cancer[^/]*\.png")),
             ("small", bul("small", r"libra[^/]*\.png"))]
    satir = []
    for i, (k, f) in enumerate(istek, 1):
        t = time.time()
        p = fetch(FOLDERS[k], f, REF / k)
        with Image.open(p) as im:
            bo = im.size
        satir.append(f"{k}/{f}  {p.stat().st_size / 1e6:.2f} MB  {bo[0]}x{bo[1]}")
        log(f"indi {i}/{len(istek)} ({time.time() - t:.1f}s): {satir[-1]}")
    (OUT / "INDIRILEN.txt").write_text("\n".join(satir) + "\n")
    gonder("INDIRILEN.txt")
    d["indirilen"] = satir
    return d


def a_hazirla(d):
    """Her bileseni hedef kutusuna kuculterek HAZIR/ altina yazar.

    JPEG: draft ile acarken kucultulur. PNG: once tamsayi reduce, sonra resize.
    Tam cozunurlukteki nesne asla tutulmaz; her bilesenden sonra serbest birakilir.
    """
    HAZIR.mkdir(parents=True, exist_ok=True)
    olcum = []
    for desen, kutu_ad, cikti in BILESEN:
        t = time.time()
        kaynak = ref_yol(desen)
        hw = max(int(round(B[kutu_ad][2])), 1)
        hh = max(int(round(B[kutu_ad][3])), 1)
        im = Image.open(kaynak)
        tam = im.size
        if im.format == "JPEG":
            im.draft("RGB", (hw, hh))                       # cozerken kucult
            ara = im.size
        else:
            k = max(min(im.width // max(hw, 1), im.height // max(hh, 1)), 1)
            if k > 1:
                im = im.reduce(k)                           # hizli tamsayi indirgeme
            ara = im.size
        im = im.convert("RGBA").resize((hw, hh), Image.LANCZOS, reducing_gap=3.0)
        hedef = HAZIR / cikti
        im.save(hedef)
        im.close()
        del im
        olcum.append(f"{cikti:22s} {tam[0]}x{tam[1]} -> ara {ara[0]}x{ara[1]} -> "
                     f"{hw}x{hh}  {time.time() - t:.1f}s  {hedef.stat().st_size / 1e3:.0f} KB")
        log(f"hazir: {olcum[-1]}")
    (OUT / "HAZIR.txt").write_text("\n".join(olcum) + "\n")
    gonder("HAZIR.txt")
    for _, _, cikti in BILESEN:
        p = HAZIR / cikti
        try:
            rc("copy", str(p), f"{DEST}/HAZIR")
        except Exception as e:
            log(f"HAZIR gonderilemedi {cikti}: {str(e)[:100]}")
    log(f"HAZIR/ Drive'a yazildi ({len(BILESEN)} bilesen)")
    d["hazir"] = olcum
    return d


def zemin_kur():
    """HAZIR kopyalarindan yazisiz poster tuvali."""
    t = Image.new("RGBA", TUVAL, (0, 0, 0, 255))
    for cikti, kutu_ad in (("bg.png", "bg"), ("ring.png", "ring"), ("main.png", "main"),
                           ("sym_left.png", "sym_left"), ("sym_right.png", "sym_right"),
                           ("infinity.png", "infinity")):
        im = Image.open(HAZIR / cikti).convert("RGBA")
        top, left = B[kutu_ad][0], B[kutu_ad][1]
        x, y = int(round(left)), int(round(top))
        kx, ky = max(-x, 0), max(-y, 0)
        if kx or ky:
            im = im.crop((kx, ky, im.width, im.height))
            x, y = x + kx, y + ky
        im = im.crop((0, 0, min(im.width, TUVAL[0] - x), min(im.height, TUVAL[1] - y)))
        t.alpha_composite(im, (x, y))
    return t


def a_zemin(d):
    t = time.time()
    z = zemin_kur()
    z.save(OUT / "zemin.png")
    log(f"zemin.png kuruldu ({time.time() - t:.1f}s)")
    o = z.copy()
    for cikti, kutu_ad in (("orij_name_left.png", "name_left"),
                           ("orij_name_right.png", "name_right"),
                           ("orij_tagline.png", "tagline")):
        im = Image.open(HAZIR / cikti).convert("RGBA")
        o.alpha_composite(im, (int(round(B[kutu_ad][1])), int(round(B[kutu_ad][0]))))
    o.save(OUT / "orij.png")
    log("orij.png (orijinal yazilarla) kuruldu")
    return d


def met_al(path):
    """Referans plakadan: png boyutu, cam kutusu, altin satir profili."""
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im)
    m = ink_mask(a)
    x0, y0, x1, y1 = bbox_of(m)
    prof = []
    for y in range(y0, y1):
        mr = m[y, x0:x1]
        prof.append(np.median(a[y, x0:x1][mr][:, :3], axis=0).tolist() if mr.sum() >= 3
                    else (prof[-1] if prof else [200., 170., 110.]))
    al = a[..., 3]
    return {"png": list(im.size), "bb": [x0, y0, x1, y1], "prof": prof,
            "yumusak": bool(((al > 8) & (al < 120)).sum() / max((al > 8).sum(), 1) > 0.45),
            "rgb": [float(v) for v in np.median(a[..., :3][m], axis=0)],
            "maske_kucuk": kucuk_maske(m, (x0, y0, x1, y1))}


def kucuk_maske(m, bb):
    x0, y0, x1, y1 = bb
    im = Image.fromarray((m[y0:y1, x0:x1] * 255).astype(np.uint8), "L")
    o = IOU_H / im.height
    return [max(int(im.width * o), 1), IOU_H]


def ref_maske(path, met):
    im = Image.open(path).convert("RGBA")
    m = ink_mask(np.asarray(im))
    x0, y0, x1, y1 = met["bb"]
    k = Image.fromarray((m[y0:y1, x0:x1] * 255).astype(np.uint8), "L")
    return k.resize(tuple(met["maske_kucuk"]), Image.LANCZOS)


def hedef(kutu, met):
    top, left, w, h = kutu
    pw, ph = met["png"]
    x0, y0, x1, y1 = met["bb"]
    oy = h / ph
    return left + w / 2, top + ((y0 + y1) / 2) * oy, (y1 - y0) * oy


def altin(mask_img, met):
    m = np.asarray(mask_img).astype(np.float32) / 255.0
    h, w = m.shape
    prof = np.asarray(met["prof"], np.float32)
    idx = np.linspace(0, len(prof) - 1, h)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(prof) - 1)
    t = (idx - lo)[:, None]
    g = prof[lo] * (1 - t) + prof[hi] * t
    o = np.zeros((h, w, 4), np.uint8)
    o[..., :3] = np.clip(np.repeat(g[:, None, :], w, axis=1), 0, 255).astype(np.uint8)
    o[..., 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    pl = Image.fromarray(o, "RGBA")
    if met["yumusak"]:
        from PIL import ImageFilter
        hale = Image.fromarray((m * 255).astype(np.uint8), "L").filter(
            ImageFilter.GaussianBlur(max(h * 0.05, 1)))
        arr = np.asarray(pl).copy()
        arr[..., 3] = np.clip(np.maximum(arr[..., 3].astype(np.float32),
                                         np.asarray(hale).astype(np.float32) * 0.35),
                              0, 255).astype(np.uint8)
        pl = Image.fromarray(arr, "RGBA")
    return pl


def a_olc(d):
    """Referans olcumleri + stil testi. Font sabit, arama yok."""
    fp = FONT_DIR / ISIM_FONT
    yollar = {"cancer": REF / "names" / "cancer_name_gold.png",
              "libra": REF / "names" / "libra_name_gold.png",
              "tagline": REF / "parts" / "tagline.png"}
    d["met"] = {}
    for k, p in yollar.items():
        t = time.time()
        d["met"][k] = met_al(p)
        log(f"olcum {k}: bb={d['met'][k]['bb']} ({time.time() - t:.1f}s)")

    d["stil"] = {}
    tr = []
    kiyas = []
    for ad, k in (("CANCER", "cancer"), ("LIBRA", "libra")):
        met = d["met"][k]
        orij = ref_maske(yollar[k], met)
        size = cap_icin_boyut(fp, ad, IOU_H, ISIM_W)
        ft = font_yukle(fp, size, ISIM_W)
        t_ = tracking_icin(ft, ad, orij.width)
        cr, _ = ciz_metin(ft, ad, t_)
        skor = iou(np.asarray(orij), np.asarray(cr.resize(orij.size, Image.LANCZOS)))
        pl = altin(cr, met)
        a = np.asarray(pl)
        yrgb = np.median(a[..., :3][a[..., 3] > 40], axis=0)
        tr.append(t_ / size)
        d["stil"][ad] = {"iou": round(skor, 4), "tr_orani": round(t_ / size, 4),
                         "orij_rgb": [int(v) for v in met["rgb"]],
                         "yeni_rgb": [int(v) for v in yrgb],
                         "rgb_fark": round(float(np.abs(np.array(met["rgb"]) - yrgb).max()), 1)}
        log(f"STIL {ad}: {json.dumps(d['stil'][ad])}")
        kiyas.append((orij, pl))
    d["isim_tr"] = sum(tr) / len(tr)

    tmet = d["met"]["tagline"]
    tfp = FONT_DIR / TAG_FONT
    torij = ref_maske(yollar["tagline"], tmet)
    tsize = cap_icin_boyut(tfp, ORIG_TAGLINE, IOU_H, TAG_W)
    d["tag_tr"] = tracking_icin(font_yukle(tfp, tsize, TAG_W), ORIG_TAGLINE,
                                torij.width) / tsize
    _, _, tag_h = hedef(B["tagline"], tmet)
    d["tag_punto"] = cap_icin_boyut(tfp, ORIG_TAGLINE, tag_h, TAG_W)
    d["tag_maks_w"] = B["tagline"][2]
    log(f"isim tr={d['isim_tr']:.4f} | tagline tr={d['tag_tr']:.4f} "
        f"punto={d['tag_punto']} maks_w={d['tag_maks_w']:.0f}")

    h = 120
    w = max(max(o.width, p.width) for o, p in kiyas) + 20
    kn = Image.new("RGB", (w, len(kiyas) * 280), (10, 12, 26))
    for i, (o, p) in enumerate(kiyas):
        kn.paste(Image.merge("RGB", [o.resize((int(o.width * h / o.height), h))] * 3),
                 (10, i * 280 + 10))
        pr = p.resize((int(p.width * h / p.height), h), Image.LANCZOS)
        kn.paste(pr.convert("RGB"), (10, i * 280 + 150), pr)
    kaydet_jpg(kn, OUT / "STIL_KIYAS.jpg", 400_000)
    gonder("STIL_KIYAS.jpg")

    from fontTools.ttLib import TTFont
    def eksik(p):
        cm = set()
        for tb in TTFont(str(p))["cmap"].tables:
            cm |= set(tb.cmap.keys())
        return [c for c in TR_TEST if ord(c) not in cm]
    d["tr_eksik"] = {"isim": eksik(fp), "tagline": eksik(tfp)}
    log(f"TURKCE eksik glif: {json.dumps(d['tr_eksik'])}")
    return d


def kaydet_jpg(im, path, maks):
    im = im.convert("RGB")
    for q in (95, 92, 88, 84, 80, 76, 72, 66, 60, 54, 48):
        im.save(path, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0)
        if path.stat().st_size <= maks:
            return q
    return q


def yaz_metin(tuval, metin, fp, wght, met, kutu, tr_orani, maks_w=None, punto=None,
              taban=0.70):
    mx, my, cam_h = hedef(kutu, met)
    tam = punto or cap_icin_boyut(fp, metin, cam_h, wght)
    size, olcek = tam, 1.0
    cr, _ = ciz_metin(font_yukle(fp, size, wght), metin, size * tr_orani)
    for _ in range(5):
        if not maks_w or cr.width <= maks_w or olcek <= taban + 1e-9:
            break
        olcek = max(olcek * min(maks_w / cr.width, 0.99), taban)
        size = max(int(round(tam * olcek)), 4)
        cr, _ = ciz_metin(font_yukle(fp, size, wght), metin, size * tr_orani)
    pl = altin(cr, met)
    tuval.alpha_composite(pl, (int(round(mx - pl.width / 2)), int(round(my - pl.height / 2))))
    return {"metin": metin, "punto": size, "olcek": round(olcek, 3), "genislik": pl.width,
            "sigdi": not (maks_w and cr.width > maks_w),
            "tabana_dayandi": bool(maks_w and olcek <= taban + 1e-9 and cr.width > maks_w)}


def a_uret(d, kod):
    z = Image.open(OUT / "zemin.png").convert("RGBA")
    ifp, tfp = FONT_DIR / ISIM_FONT, FONT_DIR / TAG_FONT
    sol = yaz_metin(z, NEW_LEFT, ifp, ISIM_W, d["met"]["cancer"], B["name_left"], d["isim_tr"])
    sag = yaz_metin(z, NEW_RIGHT, ifp, ISIM_W, d["met"]["libra"], B["name_right"], d["isim_tr"])
    tg = yaz_metin(z, TAGLINES[kod], tfp, TAG_W, d["met"]["tagline"], B["tagline"],
                   d["tag_tr"], maks_w=d["tag_maks_w"], punto=d["tag_punto"])
    z.save(OUT / f"poster_{kod}.png")
    q = kaydet_jpg(z, OUT / f"PILOT_{kod}.jpg", 1_500_000)
    boyut = (OUT / f"PILOT_{kod}.jpg").stat().st_size
    log(f"PILOT_{kod}.jpg q={q} {boyut / 1e6:.2f} MB | {json.dumps(tg, ensure_ascii=False)}")
    gonder(f"PILOT_{kod}.jpg")                       # uretilir uretilmez gonder
    d.setdefault("yerlesim", {})[kod] = {"sol": sol, "sag": sag, "tagline": tg}
    return d


def a_yakin(d):
    orij = Image.open(OUT / "orij.png").convert("RGBA")
    pa = Image.open(OUT / "poster_A.png").convert("RGBA")
    bant = (int(B["sym_left"][1] - 70), int(B["name_left"][0] - 55),
            int(B["name_right"][1] + B["name_right"][2] + 70),
            int(B["name_left"][0] + B["name_left"][3] + 55))
    u, a = orij.crop(bant), pa.crop(bant)
    yi = Image.new("RGB", (u.width, u.height * 2 + 16), (10, 12, 26))
    yi.paste(u.convert("RGB"), (0, 0))
    yi.paste(a.convert("RGB"), (0, u.height + 16))
    yi = yi.resize((1500, int(yi.height * 1500 / yi.width)), Image.LANCZOS)
    log(f"YAKIN_ISIMLER q={kaydet_jpg(yi, OUT / 'YAKIN_ISIMLER.jpg', 400_000)}")
    gonder("YAKIN_ISIMLER.jpg")

    tb = (int(B["tagline"][1] - 90), int(B["tagline"][0] - 45),
          int(B["tagline"][1] + B["tagline"][2] + 90),
          int(B["tagline"][0] + B["tagline"][3] + 45))
    ser = [orij.crop(tb)] + [Image.open(OUT / f"poster_{k}.png").convert("RGBA").crop(tb)
                             for k in ("A", "B", "C")]
    yt = Image.new("RGB", (ser[0].width, sum(s.height for s in ser) + 48), (10, 12, 26))
    y = 0
    for s in ser:
        yt.paste(s.convert("RGB"), (0, y))
        y += s.height + 16
    yt = yt.resize((1500, int(yt.height * 1500 / yt.width)), Image.LANCZOS)
    log(f"YAKIN_TAGLINE q={kaydet_jpg(yt, OUT / 'YAKIN_TAGLINE.jpg', 400_000)}")
    gonder("YAKIN_TAGLINE.jpg")
    return d


def rapor_yaz(d, sureler):
    m = ["# Kisisellestirme stil testi (pilot v3)", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}, "
         f"tuval {TUVAL[0]}x{TUVAL[1]} (Canva 4000x5000 kutulari x{OLCEK}).",
         "Font aramasi kapali (Mo karari): isim Cinzel wght 500, tagline "
         "EB Garamond Italic 700; ikisi de SIL OFL 1.1, ticari kullanim serbest.", "",
         "## Asama sureleri", "", "| asama | saniye |", "| --- | --- |"]
    m += [f"| {k} | {v} |" for k, v in sureler.items()]
    if d.get("stil"):
        m += ["", "## Stil fark skoru", "",
              "| plaka | maske IoU | altin RGB orijinal | altin RGB yeni | maks kanal farki |",
              "| --- | --- | --- | --- | --- |"]
        m += [f"| {k} | {v['iou']} | {tuple(v['orij_rgb'])} | {tuple(v['yeni_rgb'])} "
              f"| {v['rgb_fark']} |" for k, v in d["stil"].items()]
    if d.get("tr_eksik") is not None:
        m += ["", "## Turkce karakter", "", f"Test dizisi: `{TR_TEST}`", "",
              f"- isim fontu eksik glif: {d['tr_eksik']['isim'] or 'YOK'}",
              f"- tagline fontu eksik glif: {d['tr_eksik']['tagline'] or 'YOK'}"]
    if d.get("yerlesim"):
        m += ["", "## Uzun metin kurali", "",
              f"Tagline kutusu {d['tag_maks_w']:.0f} px, ortak punto {d['tag_punto']}, taban %70.", ""]
        for k, v in d["yerlesim"].items():
            t = v["tagline"]
            m.append(f"- {k}: punto {t['punto']} (%{t['olcek'] * 100:.0f}), "
                     f"genislik {t['genislik']} px, "
                     f"{'sigdi' if t['sigdi'] else 'TABANA DAYANDI (kutuyu asiyor)'}")
        day = [k for k, v in d["yerlesim"].items() if v["tagline"].get("tabana_dayandi")]
        if day:
            m += ["", f"**UYARI:** {', '.join(day)} varyantinda %70 tabani asildi."]
    if d.get("hazir"):
        m += ["", "## Bilesen kucultme (hazirla)", ""] + [f"- {s}" for s in d["hazir"]]
    if d.get("indirilen"):
        m += ["", "## Indirilen referanslar", ""] + [f"- {s}" for s in d["indirilen"]]
    (OUT / "STIL_TEST.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    gonder("STIL_TEST.md")


ADIMLAR = ["indir", "hazirla", "zemin", "olc", "uret_A", "uret_B", "uret_C", "yakin"]


def adim_kos(ad):
    d = durum_oku()
    if ad == "indir":
        d = a_indir(d)
    elif ad == "hazirla":
        d = a_hazirla(d)
    elif ad == "zemin":
        d = a_zemin(d)
    elif ad == "olc":
        d = a_olc(d)
    elif ad.startswith("uret_"):
        d = a_uret(d, ad.split("_")[1])
    elif ad == "yakin":
        d = a_yakin(d)
    else:
        raise SystemExit(f"bilinmeyen adim: {ad}")
    durum_yaz(d)


def orkestra(sinir):
    OUT.mkdir(parents=True, exist_ok=True)
    REF.mkdir(parents=True, exist_ok=True)
    if DURUM.exists():
        DURUM.unlink()
    sureler = {}
    log(f"pilot3 basladi | {len(ADIMLAR)} asama, her biri ayri surecte, timeout {sinir}s")
    for ad in ADIMLAR:
        t = time.time()
        log(f"=== ASAMA BASLADI: {ad}")
        try:
            r = subprocess.run([sys.executable, __file__, "--adim", ad],
                               timeout=sinir, stdin=subprocess.DEVNULL)
            kod = r.returncode
        except subprocess.TimeoutExpired:
            sureler[ad] = f"{time.time() - t:.1f} (TIMEOUT {sinir}s, surec oldurulda)"
            log(f"!!! ASAMA ZAMAN ASIMI: {ad} ({sinir}s) - surec oldurulda")
            rapor_yaz(durum_oku(), sureler)
            sys.exit(1)
        s = round(time.time() - t, 1)
        sureler[ad] = s
        if kod != 0:
            log(f"!!! ASAMA HATASI: {ad} (cikis {kod}, {s}s)")
            rapor_yaz(durum_oku(), sureler)
            sys.exit(1)
        log(f"=== ASAMA BITTI: {ad} ({s}s)")
    rapor_yaz(durum_oku(), sureler)
    log(f"TOPLAM {time.time() - T0:.1f}s | {json.dumps(sureler)}")
    log("pilot3 bitti")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adim", default="")
    ap.add_argument("--sinir", type=int, default=480)
    a = ap.parse_args()
    if a.adim:
        adim_kos(a.adim)
    else:
        orkestra(a.sinir)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
