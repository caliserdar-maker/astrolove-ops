#!/usr/bin/env python3
"""
Kisisellestirme pilotu v5 (Mo karari, 21 Eyl 2026).

Yeni yontem: sabit ogeleri YENIDEN URETME.
  Zemin = REFERANS_CANCER_LIBRA.jpg (orijinal Canva posteri). Logo, halka,
  kucuk semboller, sonsuzluk ve yildizlar ondan aynen gelir; hicbirine
  dokunulmaz, renk duzeltmesi yapilmaz. (v4'te kanal duzeltmesi ortalama rengi
  tutturdu ama kabartmayi/parlak kenari/golgeyi tutturamadi.)

  Eski CANCER/LIBRA ve tagline dikdortgenleri HAZIR/bg.png'nin AYNI
  koordinatlarindan doldurulur. Olcum: bg.png referansla yazisiz bolgelerde
  medyan 0.00 fark veriyor, yani dolgu kaynagi birebir.

  Uzerine: isimler onayli yontemle (Cinzel 500 + onayli altin profil),
  tagline AYNI doku hattiyla (ayri renk duzeltmesi yok).
  Tagline agirligi olcumle secildi: EB Garamond Italic 400 -> cizgi kalinligi
  7.0 px = referansin 7.0 px'i (500 -> 10, 600 -> 12).
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from kisisel_pilot import (BOX, DEST, FOLDERS, FONT_DIR, NEW_LEFT, NEW_RIGHT,
                           ORIG_TAGLINE, TAGLINES, bbox_of, cap_icin_boyut,
                           ciz_metin, fetch, font_yukle, ink_mask, rc, tracking_icin)

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
REF = OUT / "ref"
HAZIR = OUT / "hazir"
OLCEK, TUVAL = 0.6, (2400, 3000)
B = {k: tuple(v * OLCEK for v in box) for k, box in BOX.items()}
BG_OFS = BOX["bg"][0] * OLCEK                 # bg.png'nin tuvaldeki ust ofseti (-100.86)
ISIM_FONT, ISIM_W = "Cinzel.ttf", 500
TAG_FONT = "EBGaramond-Italic.ttf"
TAG_ADAY = (400, 500, 600)
MUREKKEP = 70
REFERANS = "REFERANS_CANCER_LIBRA.jpg"
T0 = time.time()
LUMA = np.array([0.299, 0.587, 0.114])


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def gonder(ad):
    p = OUT / ad
    if not p.exists():
        return log(f"gonderilemedi (yok): {ad}")
    try:
        rc("copy", str(p), DEST)
        log(f"Drive <- {ad} ({p.stat().st_size / 1e3:.0f} KB)")
    except Exception as e:
        log(f"Drive yazilamadi {ad}: {str(e)[:130]}")


# ------------------------------------------------------------------ olcum


def kumeler(L, y0, y1, esik=MUREKKEP, bosluk=60):
    """Satirdaki tum bitisik murekkep kumeleri (soldan saga)."""
    s = L[y0:y1] > esik
    xs = np.nonzero(s.sum(axis=0) >= 2)[0]
    if len(xs) == 0:
        return []
    out, a, p = [], xs[0], xs[0]
    for x in xs[1:]:
        if x - p > bosluk:
            out.append((int(a), int(p) + 1))
            a = x
        p = x
    out.append((int(a), int(p) + 1))
    return [k for k in out if k[1] - k[0] > 25]


def blok_bul(L, y0, y1, esik=MUREKKEP, bosluk=60):
    """Satir araligindaki en genis bitisik murekkep kumesi (yildizlari eler)."""
    s = L[y0:y1] > esik
    c = s.sum(axis=0)
    xs = np.nonzero(c >= 2)[0]
    if len(xs) == 0:
        return None
    kume, a, p = [], xs[0], xs[0]
    for x in xs[1:]:
        if x - p > bosluk:
            kume.append((a, p))
            a = x
        p = x
    kume.append((a, p))
    a, b = max(kume, key=lambda k: k[1] - k[0])
    return int(a), int(b) + 1


def satir_bloklari(L, y_bas=1900, y_son=2900):
    sat = (L > MUREKKEP).sum(axis=1)
    out, y = [], y_bas
    while y < y_son:
        if sat[y] > 5:
            y0 = y
            while y < y_son and sat[y] > 5:
                y += 1
            if y - y0 > 20:
                out.append((y0, y))
        y += 1
    return out


def doku_olc(im, kutu):
    """Bolgedeki murekkep pikselleri: RGB, parlaklik, kabartma kontrasti, dikey profil."""
    x0, y0, x1, y1 = kutu
    a = np.asarray(im.convert("RGB")).astype(np.float32)[y0:y1, x0:x1]
    L = a @ LUMA
    m = L > MUREKKEP
    if m.sum() < 50:
        return None
    prof = [float(L[i][m[i]].mean()) if m[i].sum() > 2 else None for i in range(L.shape[0])]
    prof = [p for p in prof if p is not None]
    idx = np.linspace(0, len(prof) - 1, 8).astype(int)
    kal = []
    for i in range(m.shape[0]):
        r = m[i]
        if not r.any():
            continue
        d = np.diff(np.concatenate(([0], r.view(np.int8), [0])))
        kal += list(np.nonzero(d == -1)[0] - np.nonzero(d == 1)[0])
    return {"rgb": [round(float(v), 1) for v in np.median(a[m], axis=0)],
            "parlaklik": round(float(L[m].mean()), 1),
            "kabartma_std": round(float(L[m].std()), 1),
            "kalinlik": round(float(np.median(kal)), 1),
            "profil": [round(float(prof[i]), 1) for i in idx]}


def doku_fark(a, b):
    if not a or not b:
        return None
    return {"rgb": round(float(np.abs(np.array(a["rgb"]) - np.array(b["rgb"])).max()), 1),
            "parlaklik": round(abs(a["parlaklik"] - b["parlaklik"]), 1),
            "kabartma_std": round(abs(a["kabartma_std"] - b["kabartma_std"]), 1),
            "profil": round(float(np.abs(np.array(a["profil"]) - np.array(b["profil"])).max()), 1),
            "kalinlik": round(abs(a["kalinlik"] - b["kalinlik"]), 1)}


# ------------------------------------------------------------------ zemin


def temizle(ref, bg, kutular, tuy=6):
    """Verilen dikdortgenleri bg.png'nin ayni koordinatlarindan, yumusak gecisli
    maske ile doldurur (ek izi birakmamak icin)."""
    t = ref.convert("RGB").copy()
    for (x0, y0, x1, y1) in kutular:
        by0, by1 = int(round(y0 - BG_OFS)), int(round(y1 - BG_OFS))
        yama = bg.crop((x0, by0, x1, by1)).convert("RGB")
        m = Image.new("L", (x1 - x0, y1 - y0), 0)
        m.paste(255, (tuy, tuy, x1 - x0 - tuy, y1 - y0 - tuy))
        t.paste(yama, (x0, y0), m.filter(ImageFilter.GaussianBlur(tuy / 2)))
    return t


def ek_izi(temiz, ref, kutu, bant=3, pay=8):
    """Dolgu sinirinda iz olcumu: sinirin ic ve dis bandi arasindaki fark,
    ayni olcum referansta da yapilip kiyaslanir."""
    x0, y0, x1, y1 = kutu
    out = []
    for im in (temiz, ref):
        a = np.asarray(im.convert("RGB")).astype(np.float32)
        ic = np.concatenate([a[y0:y0 + bant, x0:x1].reshape(-1, 3),
                             a[y1 - bant:y1, x0:x1].reshape(-1, 3)])
        dis = np.concatenate([a[y0 - pay:y0 - pay + bant, x0:x1].reshape(-1, 3),
                              a[y1 + pay - bant:y1 + pay, x0:x1].reshape(-1, 3)])
        out.append(float(np.abs(ic.mean(axis=0) - dis.mean(axis=0)).max()))
    return {"temiz": round(out[0], 2), "referans": round(out[1], 2),
            "fark": round(abs(out[0] - out[1]), 2)}


def cap_punto(fp, wght, hedef_cap, lo=10, hi=400):
    """Buyuk harf yuksekligi hedef_cap olan punto ("T" ile olculur)."""
    for _ in range(22):
        mid = (lo + hi) / 2
        _, ust, taban = ciz_cap(fp, wght, max(int(round(mid)), 4), "T")
        if ust is None:
            lo = mid
            continue
        if (taban - ust) < hedef_cap:
            lo = mid
        else:
            hi = mid
        if hi - lo < 0.5:
            break
    return max(int(round((lo + hi) / 2)), 4)


def prof_al(path):
    a = np.asarray(Image.open(path).convert("RGBA"))
    m = ink_mask(a)
    x0, y0, x1, y1 = bbox_of(m)
    p = []
    for y in range(y0, y1):
        r = m[y, x0:x1]
        p.append(np.median(a[y, x0:x1][r][:, :3], axis=0) if r.sum() >= 3
                 else (p[-1] if p else np.array([200., 170., 110.])))
    return np.asarray(p, np.float32), (x0, y0, x1, y1), (a.shape[1], a.shape[0]), a


def ciz_cap(fp, wght, punto, metin):
    """Metni cizer ve kirpilmis maskede CAP BANDINI (cap ustu, taban cizgisi) doner.

    Gradyan tum cam kutusuna degil cap bandina oturmali: inen harfli bir metinde
    (g, p, gh, u) cam kutusu uzar ve ayni profil gerilince renk kayar. Bant
    ayni punto ile cizilen "T"den olculur.
    """
    from PIL import ImageDraw
    ft = font_yukle(fp, punto, wght)
    pad = 200

    def ciz(t):
        g = int(sum(ft.getlength(c) for c in t)) + 2 * pad
        im = Image.new("L", (max(g, 10), int(punto * 2.8) + 2 * pad), 0)
        dd = ImageDraw.Draw(im)
        x = float(pad)
        for c in t:
            dd.text((x, pad), c, fill=255, font=ft)
            x += ft.getlength(c)
        return im

    t_im = np.asarray(ciz("T")) > 40
    tb = bbox_of(t_im)
    s_im = ciz(metin)
    sb = bbox_of(np.asarray(s_im) > 40)
    if sb is None or tb is None:
        return None, None, None
    kirp = s_im.crop(sb)
    return kirp, tb[1] - sb[1], tb[3] - sb[1]        # cap ustu, taban cizgisi (yerel)


def altin(mask, prof, yumusak, bant=None):
    """Onayli altin doku hatti - isim ve tagline icin AYNI."""
    m = np.asarray(mask).astype(np.float32) / 255.0
    h, w = m.shape
    if bant:
        ust, taban = bant
        u = np.clip((np.arange(h) - ust) / max(taban - ust, 1), 0, 1)
        idx = u * (len(prof) - 1)
    else:
        idx = np.linspace(0, len(prof) - 1, h)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(prof) - 1)
    t = (idx - lo)[:, None]
    g = prof[lo] * (1 - t) + prof[hi] * t
    o = np.zeros((h, w, 4), np.uint8)
    o[..., :3] = np.clip(np.repeat(g[:, None, :], w, axis=1), 0, 255).astype(np.uint8)
    o[..., 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    pl = Image.fromarray(o, "RGBA")
    if yumusak:
        hale = Image.fromarray((m * 255).astype(np.uint8), "L").filter(
            ImageFilter.GaussianBlur(max(h * 0.05, 1)))
        arr = np.asarray(pl).copy()
        arr[..., 3] = np.clip(np.maximum(arr[..., 3].astype(np.float32),
                                         np.asarray(hale).astype(np.float32) * 0.35),
                              0, 255).astype(np.uint8)
        pl = Image.fromarray(arr, "RGBA")
    return pl


def yerlestir(tuval, pl, merkez_x, merkez_y):
    tuval.alpha_composite(pl, (int(round(merkez_x - pl.width / 2)),
                               int(round(merkez_y - pl.height / 2))))


def kaydet(im, path, maks=1_500_000):
    im = im.convert("RGB")
    for q in (95, 92, 88, 84, 80, 76, 72, 66, 60, 54, 48):
        im.save(path, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0)
        if path.stat().st_size <= maks:
            return q
    return q


# ------------------------------------------------------------------ ana akis


def hazirlik(indir):
    if indir:
        rc("copy", f"{DEST}/{REFERANS}", str(OUT))
        HAZIR.mkdir(parents=True, exist_ok=True)
        rc("copy", f"{DEST}/HAZIR/bg.png", str(HAZIR))
        for f in ("cancer_name_gold.png", "libra_name_gold.png"):
            fetch(FOLDERS["names"], f, REF / "names")
        log("referans + bg.png + isim plakalari indi")
    ref = Image.open(OUT / REFERANS).convert("RGB")
    if ref.size != TUVAL:
        ref = ref.resize(TUVAL, Image.LANCZOS)
    return ref, Image.open(HAZIR / "bg.png")


def kos(indir=True):
    OUT.mkdir(parents=True, exist_ok=True)
    d = {}
    ref, bg = hazirlik(indir)
    L = np.asarray(ref).astype(np.float32) @ LUMA

    # --- referanstaki eski yazi satirlarini bul
    bloklar = satir_bloklari(L)
    log(f"alt bolge murekkep bloklari: {bloklar}")
    isim_y = next(b for b in bloklar if 2150 < b[0] < 2350)
    tag_y = next(b for b in bloklar if 2450 < b[0] < 2750)
    isim_x = blok_bul(L, *isim_y, bosluk=400)          # CANCER..LIBRA tek kume
    tag_x = blok_bul(L, *tag_y)
    d["ref_isim_kutu"] = [isim_x[0], isim_y[0], isim_x[1], isim_y[1]]
    d["ref_tag_kutu"] = [tag_x[0], tag_y[0], tag_x[1], tag_y[1]]
    d["ref_tag_cap"] = tag_y[1] - tag_y[0]
    log(f"referans isim satiri {d['ref_isim_kutu']} | tagline {d['ref_tag_kutu']} "
        f"cap={d['ref_tag_cap']} px")
    d["ref_tag_doku"] = doku_olc(ref, d["ref_tag_kutu"])
    d["ref_isim_doku"] = doku_olc(ref, d["ref_isim_kutu"])
    log(f"REFERANS tagline dokusu: {json.dumps(d['ref_tag_doku'])}")

    # --- temizlik
    pay = 16
    # Isim satirinda uc kume var: CANCER, sonsuzluk, LIBRA. Sonsuzluk sabit bir
    # ogedir ve referanstan AYNEN kalmali; yalniz iki isim kutusu temizlenir.
    km = kumeler(L, *isim_y)
    d["isim_kumeleri"] = km
    log(f"isim satiri kumeleri: {km} (ortadaki sonsuzluk korunuyor)")
    if len(km) >= 3:
        isim_kut = [[max(km[0][0] - pay, 0), isim_y[0] - pay,
                     min((km[0][1] + km[1][0]) // 2, TUVAL[0]), isim_y[1] + pay],
                    [max((km[-2][1] + km[-1][0]) // 2, 0), isim_y[0] - pay,
                     min(km[-1][1] + pay, TUVAL[0]), isim_y[1] + pay]]
        d["sonsuzluk_kutu"] = [km[1][0], isim_y[0], km[1][1], isim_y[1]]
    else:
        log("UYARI: isim satirinda 3 kume bulunamadi, tum satir temizleniyor")
        isim_kut = [[max(d["ref_isim_kutu"][0] - pay, 0), d["ref_isim_kutu"][1] - pay,
                     min(d["ref_isim_kutu"][2] + pay, TUVAL[0]), d["ref_isim_kutu"][3] + pay]]
    kut = isim_kut + [[max(d["ref_tag_kutu"][0] - pay, 0), d["ref_tag_kutu"][1] - pay,
                       min(d["ref_tag_kutu"][2] + pay, TUVAL[0]), d["ref_tag_kutu"][3] + pay]]
    temiz = temizle(ref, bg, [tuple(k) for k in kut])
    d["ek_izi"] = {f"isim_{i + 1}": ek_izi(temiz, ref, tuple(k))
                   for i, k in enumerate(kut[:-1])}
    d["ek_izi"]["tagline"] = ek_izi(temiz, ref, tuple(kut[-1]))
    log(f"ek izi: {json.dumps(d['ek_izi'])}")
    kalan = {f"kutu_{i + 1}": doku_olc(temiz, tuple(k)) for i, k in enumerate(kut)}
    d["temizlik_kalinti"] = {k: (v["parlaklik"] if v else None) for k, v in kalan.items()}
    log(f"temizlik sonrasi kutularda kalan murekkep: {d['temizlik_kalinti']}")
    kaydet(temiz, OUT / "TEMIZ_ZEMIN.jpg")
    gonder("TEMIZ_ZEMIN.jpg")

    # --- altin profil (onayli) + isim yerlesimi
    prof_c, bb_c, png_c, arr_c = prof_al(REF / "names" / "cancer_name_gold.png")
    prof_l, bb_l, png_l, arr_l = prof_al(REF / "names" / "libra_name_gold.png")
    yum_c = bool(((arr_c[..., 3] > 8) & (arr_c[..., 3] < 120)).sum()
                 / max((arr_c[..., 3] > 8).sum(), 1) > 0.45)

    def isim_yaz(t, metin, prof, bb, png, kutu):
        top, left, w, h = kutu
        oy = h / png[1]
        cam_h = (bb[3] - bb[1]) * oy
        s = cap_icin_boyut(FONT_DIR / ISIM_FONT, metin, cam_h, ISIM_W)
        ft = font_yukle(FONT_DIR / ISIM_FONT, s, ISIM_W)
        tr = tracking_icin(font_yukle(FONT_DIR / ISIM_FONT, 200, ISIM_W),
                           "CANCER", int((bb[2] - bb[0]) * 200 / (bb[3] - bb[1]))) / 200
        cr, _ = ciz_metin(ft, metin, s * tr)
        yerlestir(t, altin(cr, prof, yum_c), left + w / 2,
                  top + ((bb[1] + bb[3]) / 2) * oy)
        return {"punto": s, "genislik": cr.width}

    # --- tagline agirligi: cizgi kalinligi referansa en yakin olan
    hedef_kal = d["ref_tag_doku"]["kalinlik"]
    adaylar = []
    for w in TAG_ADAY:
        s = cap_punto(FONT_DIR / TAG_FONT, w, d["ref_tag_cap"])
        cr, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, w, s, ORIG_TAGLINE)
        pl = altin(cr, prof_c, yum_c, (cu, ct))
        t = temiz.convert("RGBA").copy()
        yerlestir(t, pl, TUVAL[0] / 2, (d["ref_tag_kutu"][1] + d["ref_tag_kutu"][3]) / 2)
        o = doku_olc(t, d["ref_tag_kutu"])
        adaylar.append({"wght": w, "punto": s, "genislik": cr.width, "doku": o,
                        "fark": doku_fark(o, d["ref_tag_doku"])})
        log(f"aday EBG-It {w}: punto {s} genislik {cr.width} fark {json.dumps(adaylar[-1]['fark'])}")
    d["tag_adaylar"] = adaylar
    sec = min(adaylar, key=lambda a: abs(a["doku"]["kalinlik"] - hedef_kal))
    d["tag_secim"] = {"wght": sec["wght"], "punto": sec["punto"]}
    log(f"SECILEN tagline agirligi: {sec['wght']} (punto {sec['punto']}, "
        f"kalinlik {sec['doku']['kalinlik']} / referans {hedef_kal})")
    d["tag_maks_w"] = round(B["ring"][2], 1)

    # --- posterler
    d["yerlesim"] = {}
    for kod in ("A", "B", "C"):
        t = temiz.convert("RGBA").copy()
        sol = isim_yaz(t, NEW_LEFT, prof_c, bb_c, png_c, B["name_left"])
        sag = isim_yaz(t, NEW_RIGHT, prof_l, bb_l, png_l, B["name_right"])
        s = sec["punto"]                       # TEK punto: cap yuksekligi sabit kalir
        cr, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, sec["wght"], s, TAGLINES[kod])
        pl = altin(cr, prof_c, yum_c, (cu, ct))
        yerlestir(t, pl, TUVAL[0] / 2, (d["ref_tag_kutu"][1] + d["ref_tag_kutu"][3]) / 2)
        d["yerlesim"][kod] = {"sol": sol, "sag": sag, "tagline_punto": s,
                              "tagline_genislik": cr.width,
                              "sigdi": cr.width <= d["tag_maks_w"]}
        t.convert("RGB").save(OUT / f"poster_{kod}3.png")
        q = kaydet(t, OUT / f"PILOT_{kod}3.jpg")
        log(f"PILOT_{kod}3.jpg q={q} {(OUT / f'PILOT_{kod}3.jpg').stat().st_size / 1e6:.2f} MB "
            f"| {json.dumps(d['yerlesim'][kod], ensure_ascii=False)}")
        gonder(f"PILOT_{kod}3.jpg")
        if kod == "A":
            jp = Image.open(OUT / "PILOT_A3.jpg")
            d["a_tag_doku"] = doku_olc(jp, d["ref_tag_kutu"])
            d["a_isim_doku"] = doku_olc(jp, d["ref_isim_kutu"])
            d["a_isim_fark"] = doku_fark(d["a_isim_doku"], d["ref_isim_doku"])
            log(f"PILOT_A3 ISIM satiri (ONAYLI) fark {json.dumps(d['a_isim_fark'])}")
            d["a_tag_fark"] = doku_fark(d["a_tag_doku"], d["ref_tag_doku"])
            log(f"PILOT_A3 tagline dokusu {json.dumps(d['a_tag_doku'])} "
                f"fark {json.dumps(d['a_tag_fark'])}")

    kiyas(d, ref)
    rapor(d)
    return d


def kiyas(d, ref):
    pa = Image.open(OUT / "poster_A3.png").convert("RGB")
    Wc = 820
    h = int(Wc * TUVAL[1] / TUVAL[0])
    ust = Image.new("RGB", (Wc * 2 + 20, h), (8, 10, 24))
    ust.paste(ref.resize((Wc, h), Image.LANCZOS), (0, 0))
    ust.paste(pa.resize((Wc, h), Image.LANCZOS), (Wc + 20, 0))
    kes = []
    for ad, kutu in (("LOGO", B["main"]), ("TAGLINE", d["ref_tag_kutu"])):
        if len(kutu) == 4 and ad == "LOGO":
            bx = (int(kutu[1]), int(kutu[0]), int(kutu[1] + kutu[2]), int(kutu[0] + kutu[3]))
        else:
            bx = (kutu[0] - 30, kutu[1] - 20, kutu[2] + 30, kutu[3] + 20)
        a, b = ref.crop(bx), pa.crop(bx)
        o = min((Wc * 2 + 20) / (a.width * 2), 2.0)      # 2x buyutme siniri
        o = max(o, 0.5)
        kes.append((a.resize((int(a.width * o), int(a.height * o)), Image.LANCZOS),
                    b.resize((int(b.width * o), int(b.height * o)), Image.LANCZOS)))
    alt = sum(a.height + 20 for a, _ in kes)
    kn = Image.new("RGB", (ust.width, h + 20 + alt), (8, 10, 24))
    kn.paste(ust, (0, 0))
    y = h + 20
    for a, b in kes:
        kn.paste(a, (0, y))
        kn.paste(b, (min(a.width + 20, ust.width - b.width), y))
        y += a.height + 20
    o = 1700 / kn.width
    kn = kn.resize((1700, int(kn.height * o)), Image.LANCZOS)
    log(f"KIYAS3 q={kaydet(kn, OUT / 'KIYAS3.jpg', 1_200_000)} (sol referans, sag PILOT_A3)")
    gonder("KIYAS3.jpg")


def rapor(d):
    s, f = d["tag_secim"], d["a_tag_fark"]
    m = ["# Pilot v5 - referans zeminli uretim", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "Zemin REFERANS_CANCER_LIBRA.jpg'dir. Logo, halka, kucuk semboller,",
         "sonsuzluk ve yildizlar referanstan AYNEN gelir; yeniden cizilmedi,",
         "renk duzeltmesi uygulanmadi.", "",
         "## Tagline", "",
         f"- Font: EB Garamond Italic **{s['wght']}**, punto {s['punto']}, "
         "harf araligi normal, yatay sikistirma yok, kucultme yok",
         f"- Buyuk harf yuksekligi: {d['ref_tag_cap']} px (referanstan olculdu)",
         f"- Genislik siniri (halka): {d['tag_maks_w']} px", "",
         "| aday | punto | genislik | cizgi kalinligi | kalinlik farki |",
         "| --- | --- | --- | --- | --- |"]
    for a in d["tag_adaylar"]:
        m.append(f"| EBG-It {a['wght']} | {a['punto']} | {a['genislik']} | "
                 f"{a['doku']['kalinlik']} | {a['fark']['kalinlik']} |")
    m += ["", f"Referans cizgi kalinligi: {d['ref_tag_doku']['kalinlik']} px", "",
          "## Doku olcumu (PILOT_A3 tagline vs referans tagline)", "",
          "| olcut | referans | pilot | fark | esik |", "| --- | --- | --- | --- | --- |",
          f"| ortalama RGB | {d['ref_tag_doku']['rgb']} | {d['a_tag_doku']['rgb']} "
          f"| {f['rgb']} | 5 |",
          f"| parlaklik | {d['ref_tag_doku']['parlaklik']} | {d['a_tag_doku']['parlaklik']} "
          f"| {f['parlaklik']} | 5 |",
          f"| kabartma kontrasti (std) | {d['ref_tag_doku']['kabartma_std']} "
          f"| {d['a_tag_doku']['kabartma_std']} | {f['kabartma_std']} | 5 |",
          f"| dikey parlaklik profili | {d['ref_tag_doku']['profil']} "
          f"| {d['a_tag_doku']['profil']} | {f['profil']} | 5 |", "",
          "## Ek izi (dolgu siniri)", "",
          "| kutu | temiz zemin | referans | fark | esik |", "| --- | --- | --- | --- | --- |"]
    for k, v in d["ek_izi"].items():
        m.append(f"| {k} | {v['temiz']} | {v['referans']} | {v['fark']} | 3 |")
    m += ["", "## Yerlesim", ""]
    for k, v in d["yerlesim"].items():
        m.append(f"- {k}: tagline punto {v['tagline_punto']}, genislik "
                 f"{v['tagline_genislik']} px / sinir {d['tag_maks_w']} "
                 f"({'sigdi' if v['sigdi'] else 'TASTI'})")
    m += ["", "## Uretim icin gerekenler (simdi yapilmadi)", "",
          "Bu pilot 2400x3000 JPG referans uzerinde kuruldu; degerlendirme icin yeterli.",
          "Satisa gidecek uretimde her cift icin Canva'dan TAM COZUNURLUKLU PNG",
          "gerekir. Gerekceler:",
          "- JPG sikistirmasi altin kenarlarda halka/blok izi birakir; baskida gorunur.",
          "- 2400x3000, 4:5 baskida ~240 dpi'ye denk; POD icin 300 dpi (3000x3750) veya",
          "  Canva tuvalinin tamami (4000x5000) gerekir.",
          "- Yazi temizligi kayipsiz zeminde daha temiz olur; JPG'de dolgu siniri",
          "  sikistirma gurultusu tasir.",
          "Gereken: sayfa 28 CANCER_LIBRA'nin PNG disa aktarimi + ayni islem icin",
          "her cift sayfasinin PNG'si (ya da yazisiz bir ana sayfa)."]
    (OUT / "RAPOR_V5.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    gonder("RAPOR_V5.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true", help="Drive'dan indirme, dosyalar hazir")
    a = ap.parse_args()
    kos(indir=not a.yerel)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
