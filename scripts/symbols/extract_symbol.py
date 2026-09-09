#!/usr/bin/env python3
"""
Poster'dan sembol katmani cikarimi -> RGBA seffaf PNG (Mo 9 Eyl 2026).

MASK_V5 yontemi (Colab isiydi, script yoktu; burada kalici hale getirildi):
  1. Poster gri tonlanir, OTSU esigi ile murekkep maskesi cikarilir (koyu edisyonda
     murekkep zeminden PARLAK; acik edisyonda tersi - otomatik secilir).
  2. Satir izdusumuyle BANTLAR bulunur; glif satiri = halka merkezinin altindaki ilk
     KISA bant. Baslik, isim satiri ve tagline DISLANIR.
  3. Halka elipsi: olculmus oncelikten (wp_plate_pilot RING_ELLIPSE, normalize) baslanip
     goruntude ince ayarlanir. rho = sqrt(((x-cx)/a)^2+((y-cy)/b)^2); |rho-1|<=0.012 HALKA,
     rho<0.98 ve glif satirinin ustu FUSION (baslik/tagline rho>1.2 oldugu icin dusuyor).
  4. Glif satiri sutun izdusumuyle ikiye ayrilir: SOL ve SAG glif (en cok murekkepli
     iki kume). Cift adindaki burc sirasi SOL, SAG ile eslesir.
  5. Her katman bbox'una kirpilir; ALFA = (gri - zemin)/(murekkep - zemin) yumusak
     rampasi, katman maskesinin 2 px genisletilmis hali ile sinirlanir; RGB posterden
     BIREBIR alinir. Sembol yeniden cizilmez, sadelestirilmez, aynalanmaz.

Cikti: <out>/<KATMAN>.png (RGBA), <out>/<KATMAN>_preview.png (kucuk, gozle kontrol icin),
       <out>/extract_report.json (bbox, alan, esik, kesim + referansla kiyas).
Bagimlilik: pillow, numpy (baska paket YOK).
Kullanim: extract_symbol.py --poster CANCER_LIBRA.jpg --out OUT [--layers FUSION,GLIF_SOL,GLIF_SAG]
          [--ref MASK_V5_RAPOR.json --ref-pair CANCER_LIBRA --tol 0.02] [--preview 260]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None
LAYERS = ("HALKA", "FUSION", "GLIF_SOL", "GLIF_SAG")
# Halka geometrisi ONCELIGI: scripts/etsy/wp_plate_pilot.py RING_ELLIPSE (7200x9600 poster px'te
# 6 posterde olculdu: merkez 3602,3874 - yari eksen 2675x2710). Normalize edildi -> her cozunurluk.
# Goruntude ince ayara cekilir (asagida ellipse_fit); tahmin degil, olcumden turetilmis baslangic.
RING_PRIOR = (3602.0 / 7200, 3874.0 / 9600, 2675.0 / 7200, 2710.0 / 9600)
RING_TOL = 0.012          # |rho-1| <= tol -> halka cizgisi (cizgi ~15/7200 = %0.2 W, +-pay)
FUSION_MAX_RHO = 0.98     # halka icindeki her sey fusion (olcum: fusion max rho 0.77)


def otsu(gray):
    """8-bit gri goruntu icin Otsu esigi."""
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = hist.sum()
    omega = np.cumsum(hist) / total
    mu = np.cumsum(hist * np.arange(256)) / total
    mu_t = mu[-1]
    denom = omega * (1.0 - omega)
    denom[denom == 0] = np.nan
    sigma_b = (mu_t * omega - mu) ** 2 / denom
    return int(np.nanargmax(sigma_b))


def ink_mask(gray):
    """(maske, esik, koyu_zemin_mi). Murekkep = zeminden ayrisan taraf."""
    t = otsu(gray)
    koyu = float(gray.mean()) < 128.0
    return (gray > t) if koyu else (gray < t), t, koyu


def bands(profile, min_ink, gap):
    """Satir/sutun izdusumunden bantlar -> [(bas, son_dahil, toplam_murekkep)]."""
    on = profile >= min_ink
    out, i, n = [], 0, len(on)
    while i < n:
        if not on[i]:
            i += 1
            continue
        j = i
        bos = 0
        k = i
        while k < n:
            if on[k]:
                j, bos = k, 0
            else:
                bos += 1
                if bos > gap:
                    break
            k += 1
        out.append((i, j, int(profile[i:j + 1].sum())))
        i = j + bos + 1
    return out


def bbox_of(mask):
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def ellipse_fit(xs, ys, W, H, adim=13, tur=2):
    """Halka elipsini olculmus oncelikten baslayip goruntude ince ayarlar.
    Skor = |rho-1| <= RING_TOL bandina dusen murekkep piksel sayisi (halka cizgisi)."""
    p = [RING_PRIOR[0] * W, RING_PRIOR[1] * H, RING_PRIOR[2] * W, RING_PRIOR[3] * H]
    skor = 0
    for _ in range(tur):
        for i in range(4):
            en_iyi, en_skor = p[i], -1
            for d in np.linspace(-0.03, 0.03, adim):
                q = list(p)
                q[i] = p[i] * (1 + d) if i >= 2 else p[i] + d * (W if i == 0 else H)
                rho = np.sqrt(((xs - q[0]) / q[2]) ** 2 + ((ys - q[1]) / q[3]) ** 2)
                sc = int((np.abs(rho - 1.0) <= RING_TOL).sum())
                if sc > en_skor:
                    en_skor, en_iyi = sc, q[i]
            p[i], skor = en_iyi, en_skor
    return p[0], p[1], p[2], p[3], skor


def katmanlar(ink, W, H):
    """-> {katman: maske}, tespit bilgisi. Halka elipsle, glifler satir bandiyla ayrilir."""
    ys, xs = np.nonzero(ink)
    cx, cy, a, b = ellipse_fit(xs, ys, W, H)[:4]
    rho = np.sqrt(((xs - cx) / a) ** 2 + ((ys - cy) / b) ** 2)

    # glif satiri: halka merkezinin altindaki ilk KISA bant (baslik/isim/tagline dislanir)
    satir = ink.sum(axis=1)
    bl = bands(satir, max(3, int(0.0008 * W)), int(0.006 * H))
    bl = [x for x in bl if x[2] >= 0.0005 * satir.sum()]
    glif_bant = next((x for x in bl if x[0] > cy + 0.5 * b and (x[1] - x[0] + 1) < 0.15 * H), None)
    if glif_bant is None:
        raise SystemExit("HATA: glif satiri bulunamadi (halka merkezi altinda kisa bant yok)")

    m = {}
    for ad, sec in (("HALKA", np.abs(rho - 1.0) <= RING_TOL),
                    ("FUSION", (rho < FUSION_MAX_RHO) & (ys < glif_bant[0]))):
        mm = np.zeros_like(ink)
        mm[ys[sec], xs[sec]] = True
        m[ad] = mm

    gb = np.zeros_like(ink)
    gb[glif_bant[0]:glif_bant[1] + 1] = ink[glif_bant[0]:glif_bant[1] + 1]
    sut = gb.sum(axis=0)
    kume = bands(sut, max(3, int(0.0004 * H)), int(0.03 * W))
    if len(kume) < 2:
        raise SystemExit(f"HATA: glif satirinda {len(kume)} kume (2 bekleniyor)")
    ikisi = sorted(sorted(kume, key=lambda c: c[2], reverse=True)[:2])
    for ad, c in zip(("GLIF_SOL", "GLIF_SAG"), ikisi):
        mm = np.zeros_like(ink)
        mm[:, c[0]:c[1] + 1] = gb[:, c[0]:c[1] + 1]
        m[ad] = mm
    bilgi = {"glif_bant": list(glif_bant[:2]),
             "elips": [round(cx, 1), round(cy, 1), round(a, 1), round(b, 1)],
             "elips_norm": [round(cx / W, 4), round(cy / H, 4), round(a / W, 4), round(b / H, 4)],
             "halka_piksel": int(m["HALKA"].sum())}
    return m, bilgi


def rgba_katman(rgb, gray, mask, zemin, murekkep, pad=2):
    """Katmani bbox'una kirpar; alfa = yumusak rampa x genisletilmis maske."""
    bb = bbox_of(mask)
    if bb is None:
        return None, None
    x, y, w, h = bb
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(rgb.shape[1], x + w + pad), min(rgb.shape[0], y + h + pad)
    kirp_rgb = rgb[y0:y1, x0:x1]
    kirp_gray = gray[y0:y1, x0:x1].astype(np.float32)
    kirp_m = mask[y0:y1, x0:x1]
    genis = np.asarray(Image.fromarray((kirp_m * 255).astype(np.uint8))
                       .filter(ImageFilter.MaxFilter(2 * pad + 1))) > 0
    ramp = (kirp_gray - zemin) / max(1.0, (murekkep - zemin))
    alfa = np.clip(ramp, 0.0, 1.0) * genis
    out = np.dstack([kirp_rgb, (alfa * 255).astype(np.uint8)])
    return Image.fromarray(out, "RGBA"), bb


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--poster", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--layers", default="FUSION,GLIF_SOL,GLIF_SAG")
    ap.add_argument("--ref", help="MASK_V5_RAPOR.json (kiyas icin)")
    ap.add_argument("--ref-pair")
    ap.add_argument("--tol", type=float, default=0.05, help="bbox kiyas toleransi (oran)")
    ap.add_argument("--preview", type=int, default=260, help="0 = onizleme uretme")
    a = ap.parse_args()
    istenen = [x.strip().upper() for x in a.layers.split(",") if x.strip()]
    for k in istenen:
        if k not in LAYERS:
            raise SystemExit(f"bilinmeyen katman: {k} (gecerli: {LAYERS})")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    im = Image.open(a.poster).convert("RGB")
    rgb = np.asarray(im)
    H, W = rgb.shape[:2]
    r16 = rgb.astype(np.uint16)
    gray = ((r16[:, :, 0] * 299 + r16[:, :, 1] * 587 + r16[:, :, 2] * 114) // 1000).astype(np.uint8)
    ink, t, koyu = ink_mask(gray)
    print(f"poster {W}x{H} | otsu {t} | zemin {'koyu' if koyu else 'acik'} | murekkep piksel {int(ink.sum())}")
    m, bilgi = katmanlar(ink, W, H)
    zemin = float(np.median(gray[~ink])) if (~ink).any() else 0.0
    murekkep = float(np.percentile(gray[ink], 90)) if ink.any() else 255.0

    rapor = {"poster": Path(a.poster).name, "tuval": [W, H], "otsu": t, "koyu_zemin": bool(koyu),
             "zemin_ton": zemin, "murekkep_ton": murekkep, **bilgi, "katmanlar": {}}
    for k in istenen:
        img, bb = rgba_katman(rgb, gray, m[k], zemin, murekkep)
        if img is None:
            rapor["katmanlar"][k] = {"hata": "bos maske"}
            continue
        img.save(out / f"{k}.png")
        if a.preview:
            p = img.copy()
            p.thumbnail((a.preview, a.preview), Image.LANCZOS)
            arka = Image.new("RGBA", p.size, (18, 18, 22, 255))
            arka.alpha_composite(p)
            arka.convert("RGB").save(out / f"{k}_preview.png")
        rapor["katmanlar"][k] = {"bbox": list(bb), "png": [img.size[0], img.size[1]],
                                 "alan": int(m[k].sum()), "dosya": f"{k}.png"}
        print(f"{k}: bbox {bb} | png {img.size} | alan {int(m[k].sum())}")

    if a.ref and a.ref_pair:
        ref = json.load(open(a.ref, encoding="utf-8")).get(a.ref_pair, {})
        rk = ref.get("katmanlar", {})
        olcek = [W / ref["tuval"][0], H / ref["tuval"][1]] if ref.get("tuval") else [1.0, 1.0]
        kiyas = {}
        for k, v in rapor["katmanlar"].items():
            if k not in rk or "bbox" not in v:
                continue
            rb = [rk[k]["bbox"][0] * olcek[0], rk[k]["bbox"][1] * olcek[1],
                  rk[k]["bbox"][2] * olcek[0], rk[k]["bbox"][3] * olcek[1]]
            sapma = [abs(v["bbox"][i] - rb[i]) / max(1.0, rb[2] if i % 2 == 0 else rb[3]) for i in range(4)]
            kiyas[k] = {"ref_bbox": [round(x) for x in rb], "sapma_oran": [round(s, 4) for s in sapma],
                        "PASS": max(sapma) <= a.tol}
            print(f"kiyas {k}: ref {[round(x) for x in rb]} | sapma {[round(s, 4) for s in sapma]} "
                  f"-> {'PASS' if kiyas[k]['PASS'] else 'FAIL'}")
        rapor["referans_kiyas"] = kiyas
        rapor["kiyas_PASS"] = all(v["PASS"] for v in kiyas.values()) if kiyas else None
    (out / "extract_report.json").write_text(json.dumps(rapor, indent=1, ensure_ascii=False), encoding="utf-8")
    if rapor.get("kiyas_PASS") is False:
        sys.exit(1)


if __name__ == "__main__":
    main()
