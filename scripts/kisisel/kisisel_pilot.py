#!/usr/bin/env python3
"""
Kisisellestirme pilotu: poster uzerindeki burc isimleri yerine kisi isimleri,
"Two Souls * One Bond" yerine kisiye ozel tagline. Tamamen kodla, orijinal
altin yazi kalitesinde.

Neden Actions: Claude konteynerinin ag politikasi drive.google.com'a 403
veriyor; Drive bilesenleri (bg 8 MB, tagline 7.2 MB, ana sembol ~12 MB) yalniz
rclone yetkili runner'da alinabiliyor.

Asamalar:
  --stage kesif : Drive'dan referanslari ceker, olcer, font eslemesi yapar.
                  Hicbir seyi Drive'a YAZMAZ. Ciktilar out/ altina.
  --stage uret  : kesif bulgulariyla plakalari + posterleri uretir ve
                  ASTROLOVE/TEMP/KISISEL_PILOT/ altina yazar.

Yontem (tahmin degil, olcum):
  - Font: aday fontlar referans plakanin cap yuksekligine oturtulur, harf
    araligi referans genisligini tutturacak sekilde aranir, maske IoU ile
    siralanir. "Gozle bakma" yok, tek olculebilir esik.
  - Altin doku: referans plakanin cam pikselllerinden satir bazli medyan RGB
    profili cikarilir; yeni metne ayni normalize profil uygulanir.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "assets" / "fonts"
OUT = ROOT / "out"
REF = OUT / "ref"

# Drive klasor ID'leri (Canva incelemesi, Mo)
FOLDERS = {
    "names": "1-7-94DG92CB9VqxTQ4IzKZ6hMw3Tuk-U",      # zodiac_names
    "parts": "1AMdYwBXUVa8GfZ4i1Q4_rji2Y5i9yz7o",      # background_circle_logo_logo_tagline
    "main": "1Zu0pp9DUMOkUVco_haywVz9zlEfNeDgH",       # main_symbols
    "small": "1j9TBPj86_5njsmf_t0v6tczuwcDyLuXu",      # zodiac_symbols_gold
}
DEST = "gdrive:ASTROLOVE/TEMP/KISISEL_PILOT"

# Canva "Blue 4/5" sayfa 28 CANCER_LIBRA, tuval 4000x5000 (top, left, w, h)
CANVAS = (4000, 5000)
BOX = {
    "bg":        (-168.1, 0.0, 4000.0, 5336.3),
    "ring":      (600.0, 605.7, 2788.5, 2380.7),
    "main":      (1013.5, 1131.6, 1736.8, 1632.6),
    "sym_left":  (3185.5, 1171.9, 336.9, 292.1),
    "sym_right": (3182.0, 2567.9, 404.0, 302.4),
    "name_left": (3677.4, 950.9, 778.8, 142.2),
    "infinity":  (3701.1, 1954.3, 311.9, 96.3),
    "name_right":(3680.6, 2490.7, 558.3, 138.9),
    "tagline":   (4280.6, 1419.8, 1160.3, 119.4),
}

TAGLINES = {
    "A": "It Began With a Kiss in the Rain",
    "B": "Our First Kiss Under the Umbrella",
    "C": "Yagmurun Altindaki Ilk Opucuk".replace("Yagmurun", "Yağmurun")
         .replace("Altindaki", "Altındaki").replace("Ilk", "İlk")
         .replace("Opucuk", "Öpücük"),
}
ORIG_TAGLINE = "Two Souls · One Bond"
NEW_LEFT, NEW_RIGHT = "SERDAR", "LENA"

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def eta(i, n, what):
    el = time.time() - T0
    kalan = el / max(i, 1) * (n - i)
    log(f"{what}: {i}/{n} (%{100 * i / n:.0f}) gecen {el:.0f}s kalan ~{kalan:.0f}s")


def rc(*args, capture=True):
    cmd = ["rclone", *args]
    r = subprocess.run(cmd, capture_output=capture, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"rclone hata ({r.returncode}): {' '.join(args[:3])}\n{r.stderr[-800:]}")
    return r.stdout if capture else ""


def lsf(folder_id):
    return [x for x in rc("lsf", "gdrive:", "--drive-root-folder-id", folder_id).splitlines() if x]


def fetch(folder_id, filename, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    tgt = dest_dir / filename
    if tgt.exists():
        return tgt
    rc("copy", f"gdrive:{filename}", str(dest_dir), "--drive-root-folder-id", folder_id)
    if not tgt.exists():
        raise FileNotFoundError(f"Drive'dan inmedi: {filename}")
    return tgt


# ---------------------------------------------------------------- olcum


def alpha_of(path):
    im = Image.open(path)
    im = im.convert("RGBA")
    a = np.asarray(im)
    return im, a


def ink_mask(rgba, thr=40):
    return rgba[..., 3] > thr


def bbox_of(mask):
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def olc(path, ad):
    im, a = alpha_of(path)
    m = ink_mask(a)
    bb = bbox_of(m)
    rgb = a[..., :3][m]
    info = {
        "ad": ad, "dosya": Path(path).name, "tuval": [im.width, im.height],
        "bbox": bb, "doluluk": round(float(m.mean()), 4),
        "alpha_max": int(a[..., 3].max()),
        "rgb_medyan": [int(v) for v in np.median(rgb, axis=0)] if len(rgb) else None,
        "rgb_min": [int(v) for v in rgb.min(axis=0)] if len(rgb) else None,
        "rgb_max": [int(v) for v in rgb.max(axis=0)] if len(rgb) else None,
    }
    if bb:
        info["ic_boyut"] = [bb[2] - bb[0], bb[3] - bb[1]]
        # yumusak hale (glow) belirtisi: dusuk alfa pikselleri orani
        al = a[..., 3]
        info["yumusak_oran"] = round(float(((al > 8) & (al < 120)).sum() / max((al > 8).sum(), 1)), 3)
    return info


def satir_profili(rgba, mask, bb):
    """Cam piksellerinden satir bazli medyan RGB (altin gradyan profili)."""
    x0, y0, x1, y1 = bb
    prof = []
    for y in range(y0, y1):
        row = rgba[y, x0:x1]
        mrow = mask[y, x0:x1]
        if mrow.sum() >= 3:
            prof.append(np.median(row[mrow][:, :3], axis=0))
        else:
            prof.append(prof[-1] if prof else np.array([200.0, 170.0, 110.0]))
    return np.asarray(prof, dtype=np.float32)          # (h, 3)


# ---------------------------------------------------------------- font


def font_yukle(path, size, wght=None):
    f = ImageFont.truetype(str(path), size)
    if wght is not None:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def variable_agirliklar(path):
    try:
        f = ImageFont.truetype(str(path), 64)
        axes = f.get_variation_axes()
    except Exception:
        return [None]
    if not axes:
        return [None]
    a = axes[0]
    lo, hi = a["minimum"], a["maximum"]
    return [w for w in (300, 400, 500, 600, 700) if lo <= w <= hi] or [None]


def ciz_metin(font, metin, tracking):
    """Metni harf harf, verilen tracking ile cizer; kirpilmis L maskesi doner."""
    pad = 200
    W = int(sum(font.getlength(c) for c in metin) + tracking * max(len(metin) - 1, 0) + 2 * pad)
    H = int(font.size * 2.6) + 2 * pad
    img = Image.new("L", (max(W, 10), max(H, 10)), 0)
    d = ImageDraw.Draw(img)
    x = float(pad)
    for c in metin:
        d.text((x, pad), c, fill=255, font=font)
        x += font.getlength(c) + tracking
    a = np.asarray(img)
    bb = bbox_of(a > 40)
    if bb is None:
        return None, None
    return img.crop(bb), bb


def cap_icin_boyut(path, metin, hedef_cap, wght, lo=10, hi=900):
    """Cizilen metnin yuksekligi hedef_cap olacak punto (ikili arama)."""
    for _ in range(24):
        mid = (lo + hi) / 2
        f = font_yukle(path, max(int(round(mid)), 4), wght)
        cr, _ = ciz_metin(f, metin, 0.0)
        if cr is None:
            lo = mid
            continue
        if cr.height < hedef_cap:
            lo = mid
        else:
            hi = mid
        if hi - lo < 0.5:
            break
    return max(int(round((lo + hi) / 2)), 4)


def tracking_icin(font, metin, hedef_w):
    """Toplam genisligi hedef_w yapan harf araligi (ikili arama)."""
    lo, hi = -font.size * 0.3, font.size * 1.2
    for _ in range(26):
        mid = (lo + hi) / 2
        cr, _ = ciz_metin(font, metin, mid)
        if cr is None:
            lo = mid
            continue
        if cr.width < hedef_w:
            lo = mid
        else:
            hi = mid
        if hi - lo < 0.05:
            break
    return (lo + hi) / 2


def iou(a, b):
    a = a > 127
    b = b > 127
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


def font_esle(ref_mask_img, metin, adaylar, etiket, maks_h=200):
    """Her aday fontu referansin kutusuna oturtup IoU olcer.

    IoU olcek-degismez oldugu icin tarama normalize yukseklikte yapilir:
    tagline referansi 1000+ px olunca her aday icin ~50 buyuk render gerekiyor
    ve tarama dakikalar suruyor. Kucultme sonucu degistirmez, sureyi ~50x kisar.
    """
    if ref_mask_img.height > maks_h:
        o = maks_h / ref_mask_img.height
        ref_mask_img = ref_mask_img.resize(
            (max(int(ref_mask_img.width * o), 1), maks_h), Image.LANCZOS)
    hedef_w, hedef_h = ref_mask_img.size
    ref = np.asarray(ref_mask_img)
    sonuc = []
    n = sum(len(variable_agirliklar(p)) for p in adaylar)
    i = 0
    for p in adaylar:
        for w in variable_agirliklar(p):
            i += 1
            try:
                size = cap_icin_boyut(p, metin, hedef_h, w)
                f = font_yukle(p, size, w)
                tr = tracking_icin(f, metin, hedef_w)
                cr, _ = ciz_metin(f, metin, tr)
                if cr is None:
                    continue
                cand = np.asarray(cr.resize((hedef_w, hedef_h), Image.LANCZOS))
                sonuc.append({"font": p.name, "wght": w, "punto": size,
                              "tracking": round(tr, 2), "iou": round(iou(ref, cand), 4)})
            except Exception as e:                       # tek font patlarsa tarama sursun
                sonuc.append({"font": p.name, "wght": w, "hata": str(e)[:80], "iou": 0.0})
            if i % 6 == 0 or i == n:
                eta(i, n, f"font taramasi ({etiket})")
    sonuc.sort(key=lambda r: -r["iou"])
    return sonuc


# ---------------------------------------------------------------- uretim


def altin_plaka(metin, font_path, wght, hedef_w, hedef_h, prof, yumusak, min_oran=0.70):
    """Referans olculeriyle altin yazi plakasi uretir.

    Genislik asilirsa punto orantili kuculur; min_oran altina inilmez.
    Doner: (RGBA plaka, uygulanan olcek).
    """
    olcek = 1.0
    size = cap_icin_boyut(font_path, metin, hedef_h, wght)
    f = font_yukle(font_path, size, wght)
    dogal_w = ciz_metin(f, metin, 0.0)[0].width
    if dogal_w > hedef_w:                                 # sigmiyor -> puntoyu kucult
        olcek = max(hedef_w / dogal_w, min_oran)
        size = max(int(round(size * olcek)), 4)
        f = font_yukle(font_path, size, wght)
        dogal_w = ciz_metin(f, metin, 0.0)[0].width
    tr = tracking_icin(f, metin, hedef_w) if dogal_w <= hedef_w else 0.0
    cr, _ = ciz_metin(f, metin, tr)
    m = np.asarray(cr).astype(np.float32) / 255.0         # (h, w)
    h, w = m.shape

    # altin: referans satir profilini yeni yukseklige gerdir
    idx = np.linspace(0, len(prof) - 1, h)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(prof) - 1)
    t = (idx - lo)[:, None]
    grad = prof[lo] * (1 - t) + prof[hi] * t              # (h, 3)
    rgb = np.repeat(grad[:, None, :], w, axis=1)

    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    plaka = Image.fromarray(out, "RGBA")
    if yumusak:
        from PIL import ImageFilter
        hale = Image.fromarray((m * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(h * 0.05))
        a = np.asarray(plaka)[..., 3].astype(np.float32)
        a = np.maximum(a, np.asarray(hale).astype(np.float32) * 0.35)
        arr = np.asarray(plaka).copy()
        arr[..., 3] = np.clip(a, 0, 255).astype(np.uint8)
        plaka = Image.fromarray(arr, "RGBA")
    return plaka, olcek


def yerlestir(tuval, plaka, kutu, ortala_kutu=None):
    """Plakayi kutunun (top,left,w,h) merkezine, kutu yuksekligine olceklenmis koyar."""
    top, left, w, h = kutu
    oran = min(w / plaka.width, h / plaka.height)
    yeni = plaka.resize((max(int(plaka.width * oran), 1), max(int(plaka.height * oran), 1)), Image.LANCZOS)
    cx = left + w / 2 if ortala_kutu is None else ortala_kutu
    x = int(round(cx - yeni.width / 2))
    y = int(round(top + (h - yeni.height) / 2))
    tuval.alpha_composite(yeni, (x, y))
    return (x, y, yeni.width, yeni.height)


def kutu_yerlestir(tuval, im, kutu):
    top, left, w, h = kutu
    yeni = im.convert("RGBA").resize((max(int(round(w)), 1), max(int(round(h)), 1)), Image.LANCZOS)
    tuval.alpha_composite(yeni, (int(round(left)), int(round(top))))


def jpg_kaydet(im, path, max_bayt):
    """Hedef boyutun altina inene kadar kaliteyi dusurur."""
    im = im.convert("RGB")
    for q in (95, 92, 88, 84, 80, 76, 72, 68, 62, 56, 50):
        im.save(path, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0)
        if path.stat().st_size <= max_bayt:
            return q
    return q


# ---------------------------------------------------------------- asamalar


def stage_kesif(a):
    REF.mkdir(parents=True, exist_ok=True)
    rapor = {"klasorler": {}, "olcumler": [], "font": {}}

    for k, fid in FOLDERS.items():
        rapor["klasorler"][k] = lsf(fid)
        log(f"klasor {k}: {len(rapor['klasorler'][k])} dosya -> {rapor['klasorler'][k][:14]}")

    def bul(k, kalip):
        for f in rapor["klasorler"][k]:
            if re.fullmatch(kalip, f, re.I):
                return f
        return None

    istek = [("names", "cancer_name_gold.png"), ("names", "libra_name_gold.png"),
             ("parts", "tagline.png"), ("parts", "logo.png"), ("parts", "circle.png"),
             ("parts", "midnight_blue_bg.jpg")]
    ana = bul("main", r"(cancer_libra|libra_cancer)_gold\.png")
    if ana:
        istek.append(("main", ana))
    for kalip in (r"cancer.*\.png", r"libra.*\.png"):
        s = bul("small", kalip)
        if s:
            istek.append(("small", s))

    for i, (k, f) in enumerate(istek, 1):
        try:
            p = fetch(FOLDERS[k], f, REF / k)
            log(f"indi: {k}/{f} ({p.stat().st_size / 1e6:.1f} MB)")
            rapor["olcumler"].append(olc(p, f"{k}/{f}"))
        except Exception as e:
            log(f"ATLANDI {k}/{f}: {e}")
        eta(i, len(istek), "referans indirme")

    adaylar = sorted(FONT_DIR.glob("*.ttf"))
    log(f"{len(adaylar)} aday font")

    # isim plakasi font eslemesi
    cn = REF / "names" / "cancer_name_gold.png"
    if cn.exists():
        im, arr = alpha_of(cn)
        m = ink_mask(arr)
        bb = bbox_of(m)
        ref_img = Image.fromarray((m[bb[1]:bb[3], bb[0]:bb[2]] * 255).astype(np.uint8), "L")
        log(f"CANCER referans ic kutu: {ref_img.size}")
        duz = [p for p in adaylar if "Italic" not in p.name]
        rapor["font"]["isim"] = font_esle(ref_img, "CANCER", duz, "isim")
        log("ISIM font sirasi: " + json.dumps(rapor["font"]["isim"][:8], ensure_ascii=False))

    # tagline font eslemesi
    tg = REF / "parts" / "tagline.png"
    if tg.exists():
        im, arr = alpha_of(tg)
        m = ink_mask(arr)
        bb = bbox_of(m)
        ref_img = Image.fromarray((m[bb[1]:bb[3], bb[0]:bb[2]] * 255).astype(np.uint8), "L")
        log(f"TAGLINE referans ic kutu: {ref_img.size}")
        rapor["font"]["tagline"] = font_esle(ref_img, ORIG_TAGLINE, adaylar, "tagline")
        log("TAGLINE font sirasi: " + json.dumps(rapor["font"]["tagline"][:8], ensure_ascii=False))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "kesif.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1))
    log("OLCUMLER: " + json.dumps(rapor["olcumler"], ensure_ascii=False))
    log("kesif bitti -> out/kesif.json")
    return rapor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="kesif", choices=["kesif", "uret", "tam"])
    ap.add_argument("--isim-font", default="")
    ap.add_argument("--isim-wght", default="")
    ap.add_argument("--tagline-font", default="")
    ap.add_argument("--tagline-wght", default="")
    a = ap.parse_args()
    if a.stage == "kesif":
        stage_kesif(a)
        return
    if a.stage == "tam":
        rapor = stage_kesif(a)
        sec = en_iyi(rapor)
        a.isim_font, a.isim_wght = sec["isim"][0], sec["isim"][1]
        a.tagline_font, a.tagline_wght = sec["tagline"][0], sec["tagline"][1]
    from kisisel_uret import stage_uret
    stage_uret(a)


def en_iyi(rapor):
    """Kesif siralamasindan font secer. Esik altinda kalirsa uyarir ama durmaz."""
    sec = {}
    for rol in ("isim", "tagline"):
        sira = [r for r in rapor["font"].get(rol, []) if "hata" not in r]
        if not sira:
            raise RuntimeError(f"{rol}: font eslemesi bos")
        ilk = sira[0]
        ikinci = sira[1]["iou"] if len(sira) > 1 else 0.0
        log(f"SECIM {rol}: {ilk['font']} wght={ilk['wght']} IoU={ilk['iou']} "
            f"(2. {ikinci}, fark {ilk['iou'] - ikinci:+.3f})")
        if ilk["iou"] < 0.50:
            log(f"UYARI {rol}: en iyi IoU {ilk['iou']} < 0.50; orijinal font aday "
                f"setinde olmayabilir, en yakin esdeger kullanilacak.")
        sec[rol] = (ilk["font"], str(ilk["wght"]) if ilk["wght"] else "")
    return sec


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
