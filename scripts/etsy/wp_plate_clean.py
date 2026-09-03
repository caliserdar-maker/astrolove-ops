#!/usr/bin/env python3
"""
wp-plate-clean: 16 plakadan KALAN sabit ogeleri (tagline, halka, ∞) siler;
geriye yalniz bos zemin kalir.

Kapsam OLCULEN kutulardan gelir, yeni maske tahmini YOK:
  halka   : wp_plate_pilot.RING_ELLIPSE (merkez 3602,3874; yari eksen 2675x2710;
            cizgi 15 poster px; acik yay ucu y=5696) -> ring_band()
  ∞       : wp_plate_pilot.REF_INFINITY (3500,7110,4124,7296) + INF_PAD
  tagline : docs/WP_LAYOUT_SPEC.md 7.1 satir 3 = (2505,8223,4711,8450)
            ("Two Souls · One Bond"; poster px, 12 dosyada ayni afin konum)
Bu kutularin ICINDE, plakanin hizalanmis MEDIAN'dan sapmasi (maks kanal > 12,
pair maskesiyle ayni olculen esik) murekkep sayilir; disinda hicbir piksele
dokunulmaz.

Dolgu (wp_plate_pilot.build_plate ile ayni, QC gecmis yontem): MEDIAN_<ED>.png
cover-fit hizalanir (aligned_median_canvas + plakanin GEOM sidecar'i), yuksek
frekans dokusu iki bantta kazanc ile alinir, yerel ton plakanin maske cevresi
halkasindan olculur (normalize konvolusyon), feather 24 px (alfa murekkep+6'da 1).

QC (dosya basina, PASS/FAIL):
  a) HF enerji orani: doldurulan bolge / cevre halkasi, 0.7-1.4
  b) maske disi fark 0 (plaka birebir korunur)
  c) kalinti: maske icinde |cikti - hizali medyan tonu| p99 <= cevre p99 + 4
Kesitler: qc/CROP_<ED>_<DEV>_TAGLINE.png ve _RING.png (1:1, 600x600,
plaka | cikti | fark x4).

Kullanim:
  wp_plate_clean.py --plates _plates --medians _plates --out _out [--devices ...]
"""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np

from wp_mockup_common import DEVICES, EDITIONS, imread, log
from wp_plate_pilot import (CORE_DEV, CORE_PAD, DARK, DILATE_INK, FEATHER, HP_SIGMA, INF_PAD, REF_INFINITY,
                            RING_ELLIPSE, RING_IN, RING_LINE_PX, RING_OUT, RING_TIP_Y, aligned_median_canvas,
                            apply_geom, box_mask, device_medians_from, hf_ratio, ink_mask_median, local_stats,
                            ring_band, shifted_fill)

# docs/WP_LAYOUT_SPEC.md 7.1: poster px, "TWO SOULS · ONE BOND" satiri
BOX_TAGLINE = (2505, 8223, 4711, 8450)
TAG_PAD = 12          # olculen kutu + 12 px (kabartma golgesi/parlamasi)
DIFF_THR = 12         # maks kanal |plaka - medyan| (pair maskesiyle ayni esik)
BAND_EXTRA = 6        # halka bandi + 6 px (kenar yumusatmasi)
QC_HF_LO, QC_HF_HI = 0.7, 1.4
QC_HF_ABS = 1.2       # oran disi kalinca: |HF ic - HF cevre| gri seviye siniri (olcum tabanli, qc()'ye bak)
CROP = 600
POSTER_W, POSTER_H = 3000, 4000   # poster orani temiz plaka (3:4)
TONE_MUL = 1.0        # poster modunda yerel ton penceresi carpani. 4.0 denendi (iterasyon 2):
                      # CI poster kalintisi 9.8 -> 10.6, DUZELMEDI; ton penceresi sebep degil.


def target_mask(shape, dev, F, region, ed):
    """Silinecek ogelerin OLCULEN kutulari (tuval maskesi) + parcali dokum."""
    band, _ = ring_band(F, ed, dev, region)
    band = cv2.dilate(band, np.ones((2 * BAND_EXTRA + 1, 2 * BAND_EXTRA + 1), np.uint8))
    inf = cv2.dilate(box_mask(shape, dev, [REF_INFINITY]), np.ones((2 * INF_PAD + 1, 2 * INF_PAD + 1), np.uint8))
    tag = cv2.dilate(box_mask(shape, dev, [BOX_TAGLINE]), np.ones((2 * TAG_PAD + 1, 2 * TAG_PAD + 1), np.uint8))
    parts = dict(ring=int(band.sum()), inf=int(inf.sum()), tagline=int(tag.sum()))
    return ((band | inf | tag) & region).astype(np.uint8), parts


def clean_one(plate, med_dev, ed, dev, geom):
    """Plakadan hedef kutulardaki murekkebi siler; (cikti, maske, ink, cevre halkasi, bilgi)."""
    H0, W0 = DEVICES[dev][1], DEVICES[dev][0]
    F0, region0 = aligned_median_canvas(med_dev, dev, (H0, W0, 3))
    tgt0, parts = target_mask((H0, W0, 3), dev, F0, region0, ed)
    # plaka bant kirpma geometrisindeyse medyan ve maskeler ayni donusumden gecer
    F = apply_geom(F0, geom)
    region = (apply_geom(region0 * 255, geom, cv2.INTER_LINEAR) > 127).astype(np.uint8)
    tgt = (apply_geom(tgt0 * 255, geom, cv2.INTER_LINEAR) > 127).astype(np.uint8)

    Pf = plate.astype(np.float32); Ff = F.astype(np.float32)
    dev_max = np.abs(plate.astype(np.int16) - F.astype(np.int16)).max(axis=2)
    ink = ((dev_max > DIFF_THR) & (tgt > 0)).astype(np.uint8)
    k = 2 * DILATE_INK + 1
    mask = (cv2.dilate(ink, np.ones((k, k), np.uint8)) & region & tgt).astype(np.uint8)

    hpF = Ff - cv2.GaussianBlur(Ff, (0, 0), float(HP_SIGMA))
    mm = ink_mask_median(F, ed) & region
    hpF = shifted_fill(hpF, mm, region)
    d_in = cv2.dilate(mask, np.ones((2 * RING_IN + 1, 2 * RING_IN + 1), np.uint8))
    d_out = cv2.dilate(mask, np.ones((2 * RING_OUT + 1, 2 * RING_OUT + 1), np.uint8))
    ring = ((d_out > 0) & (d_in == 0) & (region > 0) & (tgt == 0)).astype(np.float32)
    muP, _ = local_stats(Pf, ring, 32.0)
    regw = region.astype(np.float32)
    g4P = cv2.GaussianBlur(Pf, (0, 0), 4.0)
    fineP = Pf - g4P; midP = g4P - cv2.GaussianBlur(Pf, (0, 0), float(HP_SIGMA))
    g4F_sh = cv2.GaussianBlur(hpF, (0, 0), 4.0)
    fineF = hpF - g4F_sh; midF = g4F_sh
    _, sdPf = local_stats(fineP, ring, 32.0); _, sdFf = local_stats(fineF, regw, 32.0, sigmas=())
    _, sdPm = local_stats(midP, ring, 32.0); _, sdFm = local_stats(midF, regw, 32.0, sigmas=())
    gain_f = np.clip(sdPf / np.maximum(sdFf, 1e-3), 0.02, 2.0)
    gain_m = np.clip(sdPm / np.maximum(sdFm, 1e-3), 0.02, 2.0)
    Fm = fineF * gain_f + midF * gain_m + muP

    core = cv2.dilate(ink, np.ones((2 * CORE_PAD + 1, 2 * CORE_PAD + 1), np.uint8))
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    alpha = np.clip(dist / float(FEATHER), 0, 1).astype(np.float32)
    alpha[core > 0] = 1.0
    alpha = alpha[..., None]
    alpha[mask[..., None] == 0] = 0.0
    out = np.clip(np.round(Pf * (1 - alpha) + Fm * alpha), 0, 255).astype(np.uint8)
    out[mask == 0] = plate[mask == 0]
    info = dict(boxes=parts, target_px=int(tgt.sum()), ink_px=int(ink.sum()), mask_px=int(mask.sum()))
    return out, mask, ink, (ring > 0).astype(np.uint8), info


def qc(plate, out, mask, ring):
    """PASS/FAIL olcumleri: HF orani, maske disi fark, kalinti."""
    if int(mask.sum()) == 0:
        return dict(hf_in=0.0, hf_ring=0.0, hf_ratio=1.0, outside_max=0, resid_p99=0.0, ring_p99=0.0, ok=True, empty=True)
    _, _, r = hf_ratio(out, mask, ring)
    si, so, _ = hf_ratio(out, mask, ring)
    outside = int(np.abs(out.astype(np.int16) - plate.astype(np.int16)).max(axis=2)[mask == 0].max())
    g = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY).astype(np.float32)
    lo = cv2.GaussianBlur(g, (0, 0), 32.0)
    resid = np.abs(g - lo)
    rp99 = float(np.percentile(resid[mask > 0], 99)); ringp99 = float(np.percentile(resid[ring > 0], 99)) if ring.sum() else rp99
    # HF kapisi: oran 0.7-1.4 VEYA mutlak fark <= QC_HF_ABS gri seviye.
    # Gerekce (EK KURAL, olculen dogal referans): DB zemini duz siyah, medyanin
    # dokusu da sifir -> oran 0.38 cikiyor ama mutlak HF 0.16 / 0.43 gri seviye,
    # 8-bit'te gorunmez. Olculen 6 dosyada |HF ic - HF cevre|: DB 0.27, CI 0.23,
    # MB 0.20 / 0.16, WP 1.00 / 0.17 -> esik 1.2 (en buyuk olcum + pay).
    hf_ok = (QC_HF_LO <= r <= QC_HF_HI) or abs(si - so) <= QC_HF_ABS
    ok = bool(hf_ok and outside == 0 and rp99 <= ringp99 + 4)
    return dict(hf_in=si, hf_ring=so, hf_ratio=r, hf_abs=abs(si - so), hf_ok=bool(hf_ok),
                outside_max=outside, resid_p99=rp99, ring_p99=ringp99, ok=ok, empty=False)


def poster_clean(median, ed, out_w=POSTER_W, out_h=POSTER_H):
    """Poster oraninda temiz plaka: MEDIAN_<ED>.png (78 posterin medyani; cift-ozel
    murekkep yok, halka/tagline/∞ sabit oldugu icin duruyor) olcege indirilir ve
    olculen kutulardaki sabit ogeler silinir.

    Dolgu kaynagi medyanin KENDI zemini (baska ink-free kaynak yok): sabit oge
    bolgesinin yuksek frekansi shifted_fill ile komsu zemin dokusundan kopyalanir,
    yerel ton maske cevresi halkasindan olculur (build_plate ile ayni yontem).
    """
    m = cv2.resize(median, (out_w, out_h), interpolation=cv2.INTER_AREA)
    s = out_w / 7200.0                                   # poster px -> cikti px
    H, W = m.shape[:2]

    def box(b, pad):
        x0, y0, x1, y1 = [int(round(v * s)) for v in b]
        k = np.zeros((H, W), np.uint8)
        k[max(0, y0 - pad):y1 + pad + 1, max(0, x0 - pad):x1 + pad + 1] = 1
        return k
    band = np.zeros((H, W), np.uint8)
    cx, cy, ax, ay = [v * s for v in RING_ELLIPSE]
    thick = int(round(RING_LINE_PX * s)) + 2 * BAND_EXTRA
    cv2.ellipse(band, (int(round(cx)), int(round(cy))), (int(round(ax)), int(round(ay))), 0, 0, 360, 1, thick, cv2.LINE_8)
    band[int(round(RING_TIP_Y * s)) + 1:, :] = 0
    tgt = (band | box(REF_INFINITY, int(round(INF_PAD / 0.2 * s))) | box(BOX_TAGLINE, int(round(TAG_PAD / 0.2 * s)))).astype(np.uint8)

    Mf = m.astype(np.float32)
    bg_op = cv2.MORPH_OPEN if ed in DARK else cv2.MORPH_CLOSE
    kb = int(round(61 / 0.2 * s)) | 1                    # 61 tuval px -> cikti olcegi
    bg = cv2.morphologyEx(m, bg_op, np.ones((kb, kb), np.uint8)).astype(np.float32)
    dev_max = np.abs(Mf - bg).max(axis=2)
    ink = ((dev_max > CORE_DEV) & (tgt > 0)).astype(np.uint8)
    dil = int(round(DILATE_INK / 0.2 * s)) | 1
    mask = (cv2.dilate(ink, np.ones((dil, dil), np.uint8)) & tgt).astype(np.uint8)

    region = np.ones((H, W), np.uint8)
    sig = HP_SIGMA / 0.2 * s
    hp = Mf - cv2.GaussianBlur(Mf, (0, 0), sig)
    hp = shifted_fill(hp, mask, region, k=int(round(48 / 0.2 * s)))
    r_in, r_out = int(round(RING_IN / 0.2 * s)) | 1, int(round(RING_OUT / 0.2 * s)) | 1
    d_in = cv2.dilate(mask, np.ones((r_in, r_in), np.uint8))
    d_out = cv2.dilate(mask, np.ones((r_out, r_out), np.uint8))
    ring = ((d_out > 0) & (d_in == 0) & (tgt == 0)).astype(np.float32)
    # Ton penceresi tagline bandinin genisliginden buyuk olmali: bant ~95 px yuksek,
    # sigma 66'da normalize konvolusyonun agirlik kutlesi bandin ortasinda esigin altina
    # dusup coklu-olcek yedegine geciyor ve yama sinirlari aciklik lekesi birakiyor
    # (CI poster kosu 1: kalinti p99 9.8 / cevre 2.1). TONE_MUL ile pencere buyutulur.
    mu, _ = local_stats(Mf, ring, TONE_MUL * 32.0 / 0.2 * s)
    fill = hp + mu
    core = cv2.dilate(ink, np.ones((int(round(CORE_PAD / 0.2 * s)) | 1,) * 2, np.uint8))
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    alpha = np.clip(dist / max(1.0, FEATHER / 0.2 * s), 0, 1).astype(np.float32)
    alpha[core > 0] = 1.0
    alpha = alpha[..., None]
    alpha[mask[..., None] == 0] = 0.0
    out = np.clip(np.round(Mf * (1 - alpha) + fill * alpha), 0, 255).astype(np.uint8)
    out[mask == 0] = m[mask == 0]
    info = dict(scale=s, target_px=int(tgt.sum()), ink_px=int(ink.sum()), mask_px=int(mask.sum()))
    return m, out, mask, (ring > 0).astype(np.uint8), info


def crop_at(img, cx, cy, size=CROP):
    H, W = img.shape[:2]
    x0 = min(max(0, cx - size // 2), max(0, W - size)); y0 = min(max(0, cy - size // 2), max(0, H - size))
    c = img[y0:y0 + size, x0:x0 + size]
    pad = np.zeros((size, size, 3), np.uint8); pad[:c.shape[0], :c.shape[1]] = c
    return pad


def crop_sheet(plate, out, cx, cy, path, label):
    d = np.clip(np.abs(out.astype(np.int16) - plate.astype(np.int16)).max(axis=2) * 4, 0, 255).astype(np.uint8)
    sheet = np.hstack([crop_at(plate, cx, cy), crop_at(out, cx, cy), crop_at(cv2.cvtColor(d, cv2.COLOR_GRAY2BGR), cx, cy)])
    for i, t in enumerate((f"plaka {label}", "cikti", "fark x4")):
        cv2.putText(sheet, t, (i * CROP + 8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.imwrite(str(path), sheet)


def centers(dev, geom, shape):
    """Kesit merkezleri (tuval px): tagline kutusu ve halkanin sol yayi."""
    from wp_plate_pilot import poster_to_canvas
    sy = float(geom["scale_y"]); ct = geom["crop_top"]

    def to_c(px, py):
        x, y = poster_to_canvas(dev, px, py)
        return int(round(x)), int(round((y - ct) * sy))
    tx, ty = to_c((BOX_TAGLINE[0] + BOX_TAGLINE[2]) / 2, (BOX_TAGLINE[1] + BOX_TAGLINE[3]) / 2)
    rx, ry = to_c(3602 - 2675, 3874)          # halkanin sol yayi (RING_ELLIPSE merkez - yari eksen)
    return (tx, ty), (rx, ry)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plates", required=True, help="PLATE_<ED>_<DEV>.png + GEOM_*.json")
    ap.add_argument("--medians", required=True, help="MEDIAN_<ED>.png")
    ap.add_argument("--out", required=True)
    ap.add_argument("--editions", default=",".join(EDITIONS))
    ap.add_argument("--devices", default="Phone,Tablet,Desktop,Watch")
    ap.add_argument("--poster", action="store_true", help="ayrica 3000x4000 poster orani temiz plaka (medyandan)")
    ap.add_argument("--poster-only", action="store_true", help="yalniz poster orani ciktisi")
    a = ap.parse_args()
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "qc").mkdir(exist_ok=True)
    eds = [e for e in a.editions.split(",") if e]
    devs = [d for d in a.devices.split(",") if d]
    t0 = time.time(); rep = {}; all_ok = True; n = 0
    if a.poster_only:
        devs = []
    total = len(eds) * (len(devs) + (1 if (a.poster or a.poster_only) else 0))
    for ed in eds:
        median = imread(Path(a.medians) / f"MEDIAN_{ed.upper()}.png")
        rep[ed] = {}
        if a.poster or a.poster_only:
            src, out, mask, ring, info = poster_clean(median, ed)
            q = qc(src, out, mask, ring)
            name = f"PLATE_{ed.upper()}_POSTER_CLEAN.png"
            cv2.imwrite(str(out_dir / name), out, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            sc = info["scale"]
            crop_sheet(src, out, int((BOX_TAGLINE[0] + BOX_TAGLINE[2]) / 2 * sc), int((BOX_TAGLINE[1] + BOX_TAGLINE[3]) / 2 * sc),
                       out_dir / "qc" / f"CROP_{ed.upper()}_POSTER_TAGLINE.png", "tagline")
            crop_sheet(src, out, int((RING_ELLIPSE[0] - RING_ELLIPSE[2]) * sc), int(RING_ELLIPSE[1] * sc),
                       out_dir / "qc" / f"CROP_{ed.upper()}_POSTER_RING.png", "halka yayi")
            info.update(q, file=name)
            rep[ed]["Poster"] = info
            all_ok &= bool(q["ok"])
            n += 1
            log(f"  {ed} {'Poster':8s} -> {name} | hedef {info['target_px']} px, murekkep {info['ink_px']}, maske {info['mask_px']} | "
                f"HF {q['hf_ratio']:.2f} (mutlak fark {q.get('hf_abs', 0):.2f}), disi {q['outside_max']}, kalinti p99 {q['resid_p99']:.1f} "
                f"(cevre {q['ring_p99']:.1f}) -> {'PASS' if q['ok'] else 'FAIL'} | {n}/{total}")
            del src, out, mask, ring
        med = device_medians_from(median) if devs else {}
        del median
        for dev in devs:
            plate = imread(Path(a.plates) / f"PLATE_{ed.upper()}_{dev.upper()}.png")
            gf = Path(a.plates) / f"GEOM_{ed.upper()}_{dev.upper()}.json"
            geom = json.loads(gf.read_text()) if gf.exists() else dict(crop_top=0, crop_bot=0, scale_y=1.0)
            out, mask, ink, ring, info = clean_one(plate, med[dev], ed, dev, geom)
            q = qc(plate, out, mask, ring)
            name = f"PLATE_{ed.upper()}_{dev.upper()}_CLEAN.png"
            cv2.imwrite(str(out_dir / name), out, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            (tx, ty), (rx, ry) = centers(dev, geom, plate.shape)
            crop_sheet(plate, out, tx, ty, out_dir / "qc" / f"CROP_{ed.upper()}_{dev.upper()}_TAGLINE.png", "tagline")
            crop_sheet(plate, out, rx, ry, out_dir / "qc" / f"CROP_{ed.upper()}_{dev.upper()}_RING.png", "halka yayi")
            info.update(q, file=name)
            rep[ed][dev] = info
            all_ok &= bool(q["ok"])
            n += 1
            el = time.time() - t0
            log(f"  {ed} {dev:8s} -> {name} | hedef {info['target_px']} px, murekkep {info['ink_px']}, maske {info['mask_px']} | "
                f"HF {q['hf_ratio']:.2f}, disi {q['outside_max']}, kalinti p99 {q['resid_p99']:.1f} (cevre {q['ring_p99']:.1f}) "
                f"-> {'PASS' if q['ok'] else 'FAIL'} | {n}/{total} gecen {el:.0f}s kalan {el / n * (total - n):.0f}s")
    (out_dir / "clean_report.json").write_text(json.dumps(dict(ok=all_ok, files=n, editions=rep), indent=1))
    log(f"SONUC: {'PASS' if all_ok else 'FAIL'} {n} dosya | toplam {time.time() - t0:.0f}s")
    raise SystemExit(0 if all_ok else 2)


if __name__ == "__main__":
    main()
