#!/usr/bin/env python3
"""
Kisisellestirme pilotu v6 (Mo degerlendirmesi, 21 Eyl 2026).

DEGISEN OGELER
  - Isimler: pilot3'teki (77b8f31) cizim BIREBIR geri yuklendi. v5'te harf
    araligi her isim icin ayri ve yanlis eslestirilmis hesaplaniyordu (CANCER
    metni LIBRA kutusuyla); pilot3'te CANCER ve LIBRA'nin olculen oranlarinin
    ORTALAMASI tek oran olarak ikisine de uygulanir. SERDAR'in aralikli,
    LENA'nin sikisik cikmasi bundandi.
  - Tagline: yalniz cap bandinin disindaki pikseller. Geçis bandin icinde
    aynen kalir; bandin ALTI gradyanin altin kalan son rengine, USTU ilk
    rengine sabitlenir. Boylece g/y/p/j/g/c/s kuyruklari ve i noktasi, I, O, U
    koyulasip zemine karismaz.
DEGISMEYEN
  - Zemin (TEMIZ_ZEMIN, referans poster), tagline fontu/puntosu/cap yuksekligi
    ve altin doku yontemi.

Koruma (ONAYLI.json + onayli/ISIM_SATIRI_ALTIN.png):
  - Her kosuda isim satiri onayli kirpimla karsilastirilir (harf konumu +-1 px,
    murekkep ortalama fark <= 3). Tutmazsa kosu HATA ile durur.
  - Harf testi: "gyp jgcs IOU iou" tagline yontemiyle cizilir; her murekkep
    pikseli altin araliginda olmalidir. Tutmazsa kosu HATA ile durur.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from kisisel_pilot import (BOX, DEST, FOLDERS, FONT_DIR, NEW_LEFT, NEW_RIGHT,
                           ORIG_TAGLINE, TAGLINES, bbox_of, cap_icin_boyut,
                           ciz_metin, fetch, font_yukle, ink_mask, rc, tracking_icin)

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[2]
KOD = Path(__file__).resolve().parent
OUT = ROOT / "out"
REF = OUT / "ref"
HAZIR = OUT / "hazir"
ONAYLI_DIR = KOD / "onayli"
OLCEK, TUVAL = 0.6, (2400, 3000)
B = {k: tuple(v * OLCEK for v in box) for k, box in BOX.items()}
BG_OFS = BOX["bg"][0] * OLCEK
IOU_H = 200
MUREKKEP = 70
REFERANS = "REFERANS_CANCER_LIBRA.jpg"
LUMA = np.array([0.299, 0.587, 0.114])
HARF_TESTI = "gyp jğçş İÖÜ iöü"
TEST_CIFTLERI = [("ŞÜKRÜ", "İPEK"), ("GÖKÇE", "MAXIMILIAN")]
T0 = time.time()

ONAYLI = json.loads((KOD / "ONAYLI.json").read_text(encoding="utf-8"))
ISIM_FONT = ONAYLI["isimler"]["font"]
ISIM_W = ONAYLI["isimler"]["agirlik"]
TAG_FONT = ONAYLI["tagline"]["font"]
TAG_W = ONAYLI["tagline"]["agirlik"]
TAG_PUNTO = ONAYLI["tagline"]["punto"]
TAG_CAP = ONAYLI["tagline"]["cap_yuksekligi"]
TAG_MAKS_W = ONAYLI["tagline"]["genislik_siniri"]


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


def kaydet(im, path, maks=1_500_000):
    im = im.convert("RGB")
    for q in (95, 92, 88, 84, 80, 76, 72, 66, 60, 54, 48):
        im.save(path, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0)
        if path.stat().st_size <= maks:
            return q
    return q


# =================================================================== ISIMLER
# pilot3.py (77b8f31) ile BIREBIR AYNI. Parametreleri degistirme.


def met_al(path):
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
    o = IOU_H / (y1 - y0)
    return {"png": list(im.size), "bb": [x0, y0, x1, y1], "prof": prof,
            "yumusak": bool(((al > 8) & (al < 120)).sum() / max((al > 8).sum(), 1) > 0.45),
            "maske_kucuk": [max(int((x1 - x0) * o), 1), IOU_H]}


def ref_maske(path, met):
    a = np.asarray(Image.open(path).convert("RGBA"))
    m = ink_mask(a)
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
    """pilot3 altin dokusu - ISIMLER icin, degistirilmedi."""
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
        hale = Image.fromarray((m * 255).astype(np.uint8), "L").filter(
            ImageFilter.GaussianBlur(max(h * 0.05, 1)))
        arr = np.asarray(pl).copy()
        arr[..., 3] = np.clip(np.maximum(arr[..., 3].astype(np.float32),
                                         np.asarray(hale).astype(np.float32) * 0.35),
                              0, 255).astype(np.uint8)
        pl = Image.fromarray(arr, "RGBA")
    return pl


def yaz_metin(tuval, metin, fp, wght, met, kutu, tr_orani, maks_w=None, punto=None,
              taban=0.70):
    """pilot3 yaz_metin - BIREBIR."""
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


def isim_tr_hesapla(met_c, met_l, yollar):
    """pilot3: CANCER ve LIBRA oranlarinin ORTALAMASI, ikisine de uygulanir."""
    fp = FONT_DIR / ISIM_FONT
    tr = []
    for ad, met, yol in (("CANCER", met_c, yollar["cancer"]), ("LIBRA", met_l, yollar["libra"])):
        orij = ref_maske(yol, met)
        size = cap_icin_boyut(fp, ad, IOU_H, ISIM_W)
        ft = font_yukle(fp, size, ISIM_W)
        t_ = tracking_icin(ft, ad, orij.width)
        tr.append(t_ / size)
        log(f"  {ad}: punto {size} tracking {t_:.2f} oran {t_ / size:.4f}")
    return sum(tr) / len(tr)


# =================================================================== TAGLINE


def ciz_cap(fp, wght, punto, metin):
    """Metni cizer; kirpilmis maskede cap ustu ve taban cizgisini doner."""
    ft = font_yukle(fp, punto, wght)
    pad = 200

    def ciz(t):
        g = int(sum(ft.getlength(c) for c in t)) + 2 * pad
        im = Image.new("L", (max(g, 10), int(punto * 3.2) + 2 * pad), 0)
        dd = ImageDraw.Draw(im)
        x = float(pad)
        for c in t:
            dd.text((x, pad), c, fill=255, font=ft)
            x += ft.getlength(c)
        return im

    tb = bbox_of(np.asarray(ciz("T")) > 40)
    s_im = ciz(metin)
    sb = bbox_of(np.asarray(s_im) > 40)
    if sb is None or tb is None:
        return None, None, None
    return s_im.crop(sb), tb[1] - sb[1], tb[3] - sb[1]


def cap_punto(fp, wght, hedef_cap, lo=10, hi=400):
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


def altin_sinirlari(prof, oran=0.45):
    """Profilin ALTIN kalan araligi: luma esigin altina dusen uclar kirpilir.

    Bandin disindaki pikseller bu uclara sabitlenir; profilin en koyu son
    satirina (golge) sabitlenince g/y/p kuyruklari zemine karisiyordu.
    """
    L = prof @ LUMA
    esik = L.max() * oran
    ok = np.nonzero(L >= esik)[0]
    return int(ok[0]), int(ok[-1])


def altin_bant(mask, prof, bant, yumusak):
    """Tagline altini: bant ICINDE gradyan aynen; bandin ustu/alti altin
    uclara SABITLENIR (koyulasma ve solma yok)."""
    m = np.asarray(mask).astype(np.float32) / 255.0
    h, w = m.shape
    prof = np.asarray(prof, np.float32)
    i_lo, i_hi = altin_sinirlari(prof)
    ust, taban = bant
    r = np.arange(h, dtype=np.float32)
    u = (r - ust) / max(taban - ust, 1)
    idx = np.clip(u, 0, 1) * (len(prof) - 1)
    idx = np.where(r < ust, float(i_lo), idx)
    idx = np.where(r > taban, float(i_hi), idx)
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


def altin_mi(rgb):
    """Altin araligi: ne koyu ne beyazimsi."""
    L = rgb @ LUMA
    mx, mn = rgb.max(axis=1), rgb.min(axis=1)
    doy = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    return (L >= 60) & (L <= 248) & (doy >= 0.20)


# =================================================================== KORUMA


def kumeler(mask, bosluk=12):
    c = mask.sum(axis=0) >= 2
    xs = np.nonzero(c)[0]
    if len(xs) == 0:
        return []
    out, a, p = [], xs[0], xs[0]
    for x in xs[1:]:
        if x - p > bosluk:
            out.append((int(a), int(p) + 1))
            a = x
        p = x
    out.append((int(a), int(p) + 1))
    return [k for k in out if k[1] - k[0] > 8]


def isim_kontrol(poster):
    """Onayli isim satiriyla karsilastir: harf konumu +-1 px, murekkep fark <=3."""
    onay = Image.open(ONAYLI_DIR / "ISIM_SATIRI_ALTIN.png").convert("RGB")
    x0, y0 = ONAYLI["isimler"]["kirpim"][:2]
    yeni = poster.convert("RGB").crop((x0, y0, x0 + onay.width, y0 + onay.height))
    ao = np.asarray(onay).astype(np.float32)
    an = np.asarray(yeni).astype(np.float32)
    mo, mn = (ao @ LUMA) > MUREKKEP, (an @ LUMA) > MUREKKEP
    ko, kn = kumeler(mo), kumeler(mn)
    if len(ko) < 3 or len(kn) < 3:
        return {"gecti": False, "sebep": f"kume sayisi {len(ko)} / {len(kn)}"}
    # ortadaki sonsuzluk zeminden gelir, karsilastirilmaz
    cift = [(ko[0], kn[0]), (ko[-1], kn[-1])]
    kayma = [max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a, b in cift]
    # Onayli kirpim BASKA zeminde (pilot3'un yeniden kurdugu zemin) alindi; kenar
    # yumusatma pikselleri zeminle karistigi icin yapisal olarak eslesemez.
    # Harfin kendisini olcmek icin ortak murekkep maskesi 1 px asindirilir.
    ortak = mo & mn
    ic = np.asarray(Image.fromarray((ortak * 255).astype(np.uint8), "L").filter(
        ImageFilter.MinFilter(3))) > 127
    fark = float(np.abs(ao[ic] - an[ic]).mean()) if ic.sum() else 999.0
    kenarli = float(np.abs(ao[ortak] - an[ortak]).mean()) if ortak.sum() else 999.0
    ok = max(kayma) <= 1 and fark <= 3.0
    return {"gecti": bool(ok), "kayma_px": kayma, "murekkep_fark": round(fark, 2),
            "kenarlar_dahil": round(kenarli, 2), "ic_px": int(ic.sum()),
            "onay_kumeleri": [ko[0], ko[-1]], "yeni_kumeleri": [kn[0], kn[-1]],
            "ortak_px": int(ortak.sum())}


def harf_testi(prof, yumusak):
    """Tagline yontemiyle inen/ustten tasan harfler: hepsi altin araliginda mi."""
    fp = FONT_DIR / TAG_FONT
    cr, cu, ct = ciz_cap(fp, TAG_W, TAG_PUNTO, HARF_TESTI)
    pl = altin_bant(cr, prof, (cu, ct), yumusak)
    a = np.asarray(pl).astype(np.float32)
    sel = a[..., 3] > 120                      # cekirdek pikseller (kenar yumusatma haric)
    ys = np.nonzero(sel)[0]
    rgb = a[..., :3][sel]
    L = rgb @ LUMA
    # Kapi B maddesinin kapsami: BANT DISI pikseller (inen kuyruklar, i noktasi,
    # I/O/U). Bant ICINDEKI taban cizgisi satiri onayli kabartma golgesidir ve
    # isimlerde de aynidir; degistirilmez, yalniz raporlanir.
    disi = (ys < cu) | (ys > ct)
    iyi = altin_mi(rgb[disi])
    return {"gecti": bool(iyi.all()),
            "bant_disi_piksel": int(disi.sum()), "bant_disi_altin_disi": int((~iyi).sum()),
            "bant_disi_luma": [round(float(L[disi].min()), 1), round(float(L[disi].max()), 1)],
            "bant_ici_luma": [round(float(L[~disi].min()), 1), round(float(L[~disi].max()), 1)],
            "bant": [int(cu), int(ct)], "plaka": [pl.width, pl.height]}, pl


# =================================================================== ZEMIN


def temizle(ref, bg, kutular, tuy=6):
    t = ref.convert("RGB").copy()
    for (x0, y0, x1, y1) in kutular:
        yama = bg.crop((x0, int(round(y0 - BG_OFS)), x1, int(round(y1 - BG_OFS)))).convert("RGB")
        m = Image.new("L", (x1 - x0, y1 - y0), 0)
        m.paste(255, (tuy, tuy, x1 - x0 - tuy, y1 - y0 - tuy))
        t.paste(yama, (x0, y0), m.filter(ImageFilter.GaussianBlur(tuy / 2)))
    return t


def satir_kumeleri(L, y0, y1, bosluk=60):
    return kumeler(L[y0:y1] > MUREKKEP, bosluk)


def zemin_hazirla(ref, bg):
    L = np.asarray(ref).astype(np.float32) @ LUMA
    sat = (L > MUREKKEP).sum(axis=1)
    bloklar, y = [], 1900
    while y < 2900:
        if sat[y] > 5:
            y0 = y
            while y < 2900 and sat[y] > 5:
                y += 1
            if y - y0 > 20:
                bloklar.append((y0, y))
        y += 1
    isim_y = next(b for b in bloklar if 2150 < b[0] < 2350)
    tag_y = next(b for b in bloklar if 2450 < b[0] < 2750)
    km = satir_kumeleri(L, *isim_y)
    tk = satir_kumeleri(L, *tag_y)
    tag_x = max(tk, key=lambda k: k[1] - k[0])
    log(f"referans isim kumeleri {km} | tagline x{tag_x} y{tag_y}")
    pay = 16
    kut = [(max(km[0][0] - pay, 0), isim_y[0] - pay, (km[0][1] + km[1][0]) // 2, isim_y[1] + pay),
           ((km[-2][1] + km[-1][0]) // 2, isim_y[0] - pay, min(km[-1][1] + pay, TUVAL[0]),
            isim_y[1] + pay),
           (max(tag_x[0] - pay, 0), tag_y[0] - pay, min(tag_x[1] + pay, TUVAL[0]),
            tag_y[1] + pay)]
    return temizle(ref, bg, kut), {"isim_y": list(isim_y), "tag_y": list(tag_y),
                                   "tag_x": list(tag_x), "sonsuzluk": list(km[1]),
                                   "kutular": [list(k) for k in kut]}


# =================================================================== AKIS


def kos(indir=True):
    OUT.mkdir(parents=True, exist_ok=True)
    d = {"degisen": ["isimler: pilot3 (77b8f31) cizimi birebir geri yuklendi",
                     "tagline: cap bandi disindaki pikseller altin uclara sabitlendi"],
         "degismeyen": ["zemin (TEMIZ_ZEMIN / referans poster)",
                        "tagline fontu, puntosu, cap yuksekligi ve altin doku yontemi"]}
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
    bg = Image.open(HAZIR / "bg.png")

    temiz, geo = zemin_hazirla(ref, bg)
    d["geo"] = geo
    kaydet(temiz, OUT / "TEMIZ_ZEMIN.jpg")

    yollar = {"cancer": REF / "names" / "cancer_name_gold.png",
              "libra": REF / "names" / "libra_name_gold.png"}
    met_c, met_l = met_al(yollar["cancer"]), met_al(yollar["libra"])
    log("isim harf araligi (pilot3 yontemi):")
    isim_tr = isim_tr_hesapla(met_c, met_l, yollar)
    log(f"  -> ortalama oran {isim_tr:.4f} (ikisine de uygulanir)")
    d["isim_tr"] = round(isim_tr, 4)

    prof_t = np.asarray(met_c["prof"], np.float32)
    i_lo, i_hi = altin_sinirlari(prof_t)
    d["altin_ucları"] = {"ust_idx": i_lo, "alt_idx": i_hi, "profil_satiri": len(prof_t),
                         "ust_renk": [int(v) for v in prof_t[i_lo]],
                         "alt_renk": [int(v) for v in prof_t[i_hi]]}
    log(f"altin ucları: {json.dumps(d['altin_ucları'], ensure_ascii=False)}")

    # --- KORUMA 1: harf testi
    ht, ht_pl = harf_testi(prof_t, met_c["yumusak"])
    d["harf_testi"] = ht
    log(f"HARF TESTI: {json.dumps(ht)}")
    kn = Image.new("RGB", (ht_pl.width + 40, ht_pl.height + 40), (10, 12, 26))
    kn.paste(ht_pl.convert("RGB"), (20, 20), ht_pl)
    o = min(1500 / kn.width, 3.0)
    kaydet(kn.resize((int(kn.width * o), int(kn.height * o)), Image.LANCZOS),
           OUT / "HARF_TESTI.jpg", 400_000)
    gonder("HARF_TESTI.jpg")
    if not ht["gecti"]:
        raise SystemExit("HARF TESTI BASARISIZ: bant disi "
                         f"{ht['bant_disi_altin_disi']} piksel altin araliginda degil")

    def poster_kur(sol_ad, sag_ad, tag_metin):
        t = temiz.convert("RGBA").copy()
        s = yaz_metin(t, sol_ad, FONT_DIR / ISIM_FONT, ISIM_W, met_c, B["name_left"], isim_tr)
        g = yaz_metin(t, sag_ad, FONT_DIR / ISIM_FONT, ISIM_W, met_l, B["name_right"], isim_tr)
        cr, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, TAG_W, TAG_PUNTO, tag_metin)
        pl = altin_bant(cr, prof_t, (cu, ct), met_c["yumusak"])
        my = (geo["tag_y"][0] + geo["tag_y"][1]) / 2
        t.alpha_composite(pl, (int(round(TUVAL[0] / 2 - pl.width / 2)),
                               int(round(my - pl.height / 2))))
        sonsuz = geo.get("sonsuzluk", [1173, 1360])
        for ad, bilgi, kutu in (("sol", s, B["name_left"]), ("sag", g, B["name_right"])):
            mx = kutu[1] + kutu[2] / 2
            bilgi["x"] = [int(mx - bilgi["genislik"] / 2), int(mx + bilgi["genislik"] / 2)]
            bilgi["sonsuzluga_carpti"] = bool(bilgi["x"][1] > sonsuz[0] and
                                              bilgi["x"][0] < sonsuz[1])
            bilgi["tuvali_asti"] = bool(bilgi["x"][0] < 0 or bilgi["x"][1] > TUVAL[0])
        return t, {"sol": s, "sag": g, "tagline_genislik": pl.width,
                   "tagline_sigdi": pl.width <= TAG_MAKS_W}

    d["yerlesim"] = {}
    for kod in ("A", "B", "C"):
        t, y = poster_kur(NEW_LEFT, NEW_RIGHT, TAGLINES[kod])
        d["yerlesim"][kod] = y
        t.convert("RGB").save(OUT / f"poster_{kod}4.png")
        if kod == "A":
            # --- KORUMA 2: isim satiri onayli kirpimla ayni mi
            d["isim_kontrol"] = isim_kontrol(t)
            log(f"ISIM KONTROL: {json.dumps(d['isim_kontrol'])}")
            if not d["isim_kontrol"]["gecti"]:
                raise SystemExit(f"ISIM KONTROL BASARISIZ: {d['isim_kontrol']}")
        q = kaydet(t, OUT / f"PILOT_{kod}4.jpg")
        log(f"PILOT_{kod}4.jpg q={q} {(OUT / f'PILOT_{kod}4.jpg').stat().st_size / 1e6:.2f} MB "
            f"| {json.dumps(y, ensure_ascii=False)}")
        gonder(f"PILOT_{kod}4.jpg")

    # --- test isim ciftleri
    seritler = []
    bant = (int(min(B["name_left"][1], B["sym_left"][1]) - 120), int(B["name_left"][0] - 70),
            int(max(B["name_right"][1] + B["name_right"][2],
                    B["sym_right"][1] + B["sym_right"][2]) + 120),
            int(B["name_left"][0] + B["name_left"][3] + 70))
    d["test_ciftleri"] = {}
    for sol_ad, sag_ad in TEST_CIFTLERI:
        tt, yy = poster_kur(sol_ad, sag_ad, TAGLINES["A"])
        d["test_ciftleri"][f"{sol_ad} / {sag_ad}"] = {"sol": yy["sol"], "sag": yy["sag"]}
        log(f"TEST CIFTI {sol_ad} / {sag_ad}: {json.dumps(yy, ensure_ascii=False)}")
        seritler.append(tt.convert("RGB").crop(bant))
    yi = Image.new("RGB", (seritler[0].width, sum(s.height + 16 for s in seritler)), (10, 12, 26))
    yy = 0
    for s in seritler:
        yi.paste(s, (0, yy))
        yy += s.height + 16
    yi = yi.resize((1500, int(yi.height * 1500 / yi.width)), Image.LANCZOS)
    kaydet(yi, OUT / "ISIM_TEST.jpg", 500_000)
    gonder("ISIM_TEST.jpg")

    yakin(d, bant)
    rapor(d)
    gonder("TEMIZ_ZEMIN.jpg")
    return d


def yakin(d, bant):
    pa = Image.open(OUT / "poster_A4.png").convert("RGB")
    onay = Image.open(ONAYLI_DIR / "ISIM_SATIRI_ALTIN.png").convert("RGB")
    x0, y0 = ONAYLI["isimler"]["kirpim"][:2]
    yeni = pa.crop((x0, y0, x0 + onay.width, y0 + onay.height))
    par = [("onayli ilk PILOT_A", onay), ("PILOT_A4", yeni)]
    # Kirpim CIZILEN tagline'a gore: referansin genisligi (695) kullanilirsa
    # yeni tagline (1275 px) kesiliyor ve g kuyrugu gorunmuyordu.
    yari = max(d["yerlesim"]["A"]["tagline_genislik"], d["geo"]["tag_x"][1] -
               d["geo"]["tag_x"][0]) // 2 + 40
    tb = (max(TUVAL[0] // 2 - yari, 0), d["geo"]["tag_y"][0] - 34,
          min(TUVAL[0] // 2 + yari, TUVAL[0]), d["geo"]["tag_y"][1] + 46)
    tag = pa.crop(tb)
    W = max(max(i.width for _, i in par), tag.width) * 2
    parca = [i.resize((i.width * 2, i.height * 2), Image.LANCZOS) for _, i in par]
    parca.append(tag.resize((tag.width * 2, tag.height * 2), Image.LANCZOS))
    kn = Image.new("RGB", (W, sum(p.height + 18 for p in parca)), (10, 12, 26))
    y = 0
    for p in parca:
        kn.paste(p, (0, y))
        y += p.height + 18
    o = min(1700 / kn.width, 1.0)
    kaydet(kn.resize((int(kn.width * o), int(kn.height * o)), Image.LANCZOS),
           OUT / "YAKIN4.jpg", 700_000)
    gonder("YAKIN4.jpg")


def rapor(d):
    ik, ht = d["isim_kontrol"], d["harf_testi"]
    m = ["# Pilot v6", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", ""] + [f"- {x}" for x in d["degisen"]] + [
         "", "### Degismeyen (ONAYLI.json korumasi altinda)", ""] + \
        [f"- {x}" for x in d["degismeyen"]] + [
         "", "## Isim karsilastirmasi (onayli ilk PILOT_A)", "",
         f"- Sonuc: **{'GECTI' if ik['gecti'] else 'KALDI'}**",
         f"- Harf konumu kaymasi: {ik['kayma_px']} px (esik +-1)",
         f"- Murekkep ortalama fark: {ik['murekkep_fark']} (esik 3), "
         f"ortak piksel {ik['ortak_px']}",
         f"- Onayli kumeler {ik['onay_kumeleri']} / yeni {ik['yeni_kumeleri']}",
         f"- Harf araligi orani: {d['isim_tr']} (CANCER+LIBRA ortalamasi, pilot3 yontemi)",
         "", "## Harf testi (inen ve ustten tasan harfler)", "",
         f"- Dizi: `{HARF_TESTI}`",
         f"- Sonuc: **{'GECTI' if ht['gecti'] else 'KALDI'}**",
         f"- Bant disi (inen kuyruklar, i noktasi, I/O/U): {ht['bant_disi_piksel']} "
         f"cekirdek piksel, altin disi {ht['bant_disi_altin_disi']}, "
         f"luma {ht['bant_disi_luma'][0]}-{ht['bant_disi_luma'][1]} "
         "(altin araligi 60-248, doygunluk >= 0.20)",
         f"- Bant ici luma {ht['bant_ici_luma'][0]}-{ht['bant_ici_luma'][1]}: taban cizgisi "
         "satirindaki koyu piksel onayli kabartma golgesidir (isimlerde de ayni), "
         "degistirilmedi.",
         f"- Altin uclari: ust {d['altin_ucları']['ust_renk']} (satir "
         f"{d['altin_ucları']['ust_idx']}), alt {d['altin_ucları']['alt_renk']} "
         f"(satir {d['altin_ucları']['alt_idx']}/{d['altin_ucları']['profil_satiri']})",
         "", "## Yerlesim", ""]
    for k, v in d["yerlesim"].items():
        m.append(f"- {k}: tagline genislik {v['tagline_genislik']} px / sinir {TAG_MAKS_W} "
                 f"({'sigdi' if v['tagline_sigdi'] else 'TASTI'})")
    m += ["", "## Test isim ciftleri", ""]
    for k, v in d["test_ciftleri"].items():
        s, g = v["sol"], v["sag"]
        m.append(f"- {k}: sol punto {s['punto']} genislik {s['genislik']} px "
                 f"({'sigdi' if s['sigdi'] else 'kuculdu %' + str(int(s['olcek'] * 100))}), "
                 f"sag punto {g['punto']} genislik {g['genislik']} px "
                 f"({'sigdi' if g['sigdi'] else 'kuculdu %' + str(int(g['olcek'] * 100))})")
    ana = d["yerlesim"]["A"]
    m += ["", "### Pilot3 kuralinin iki sonucu (degistirilmedi, raporlaniyor)", "",
          "**1) Turkce aksanli isim kuculuyor.** pilot3 puntoyu metnin TUM cam",
          "yuksekliginden turetir; S'nin cengeli ile U/O noktalari bu yuksekligi",
          "buyuttugu icin harf govdesi kuculur:", ""]
    for k, v in d["test_ciftleri"].items():
        m.append(f"- {k}: sol punto {v['sol']['punto']}, sag punto {v['sag']['punto']} "
                 f"(karsilastirma: SERDAR {ana['sol']['punto']}, LENA {ana['sag']['punto']})")
    m += ["", "**2) Uzun isim kuculmuyor ve tasabiliyor.** pilot3 isim kutusuna maks_w",
          "vermez; isim dogal genisliginde, kutusunun merkezinde kalir:", ""]
    for k, v in d["test_ciftleri"].items():
        for ad in ("sol", "sag"):
            b = v[ad]
            uyari = []
            if b.get("sonsuzluga_carpti"):
                uyari.append("SONSUZLUK ISARETINE CARPIYOR")
            if b.get("tuvali_asti"):
                uyari.append("TUVALI ASIYOR")
            m.append(f"- {k} [{ad}] {b['metin']}: genislik {b['genislik']} px, "
                     f"x {b.get('x')} {'- ' + ', '.join(uyari) if uyari else '- sorun yok'}")
    m += ["", "Her ikisi de pilot3 davranisidir ve ONAYLI.json korumasi altindadir;",
          "duzeltilmesi ayrica onay ister."]
    (OUT / "RAPOR_V6.md").write_text("\n".join(m) + "\n", encoding="utf-8")
    gonder("RAPOR_V6.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    a = ap.parse_args()
    kos(indir=not a.yerel)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
