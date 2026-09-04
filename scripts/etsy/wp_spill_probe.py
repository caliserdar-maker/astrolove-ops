#!/usr/bin/env python3
"""
WP TASMA (EDISYON BAZLI) + SAAT WALLPAPER KAYNAK HALESI - SALT OLCUM - 4 Eyl 2026.

KISIM 1 - TASMA
  Telefon sahnelerinde (SET01/SET03/SET04) her ekrana 4 edisyon (MB/DB/CI/WP)
  TEK TEK yerlestirilir (uretimdeki paste yolu: out = (1-soft*Maa)*master +
  soft*Maa*warp_cover) ve cikti master ile karsilastirilir:
    D = kanal ortalamasi |cikti - master|
    Maskenin SERT sinirindan (soft >= 0.5) DISARI dogru 1..8 px bantlarda
    D'nin ortalamasi ve D > ESIK olan piksel orani olculur.
    tasma_px = orani %10'u asan en uzak bant (yoksa 0).
    Kenar dagilimi: tasan piksel en yakin quad kenarina gore sayilir.
  Ayrica edisyonun kenar rengi olculur:
    wp_kenar_luma : yerlestirilen wallpaper'in quad ICINDE 3 px'lik kenar bandi
    cerceve_luma  : master'in maske DISINDA 1-4 px bandi
    kontrast      : wp_kenar_luma - cerceve_luma  (gorunurlugun kaynagi)
  Boylece "maske mi, edisyonun acik kenari mi" sorusu sayiyla ayrilir: maske
  ayni (tasma_px esit) ama kontrast farkliysa sebep renktir.
  Uretimdeki gercek edisyon calib'den (screen["edition"]) yazilir.

KISIM 2 - SAAT KAYNAGI
  Her edisyonun Watch dosyasi (1000x1220) ve varsa ayni edisyonun temiz
  plakasi (PLATE_<ED>_Watch.png) ayni olcutle olculur:
    hale bantlari (0-5 / 5-10 / 10-20 / 20-40 px, uzak zemine gore fark)
    halka kalintisi (murekkebin 21 px komsulugu) ve uzak zemin kalintisi
  Plaka murekkepsizdir; wallpaper'da halka kalintisi plakadakinden buyukse
  hale murekkep aktariminda (wp_build_pair maskesi/feather'i veya posterin
  kendi halesi) dogmustur, sahnede degil.
  Ek: (wallpaper - plaka) farkinin murekkep sinirindan uzaklik profili.

Uretim yok, duzeltme yok, Etsy'ye dokunulmaz.
"""
import argparse
import csv
import os
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import (DEVICES, EDITIONS, imread, imwrite_jpeg, ink_mask,  # noqa: E402
                              log, poly_mask_aa, render_screen, warp_cover)
from wp_watch_probe import hale_profili, hale_haritasi  # noqa: E402

KISA = {"Midnight_Blue": "MB", "Deep_Black": "DB", "Champagne_Ivory": "CI", "Warm_Parchment": "WP"}
ESIK = 8.0          # master'dan gorunur sapma (kanal ortalamasi)
ORAN = 0.10         # bandin tasmis sayilmasi icin gereken piksel orani
BANT_N = 8          # disari dogru olculen en fazla px
KENAR_ADI = ["UST", "SAG", "ALT", "SOL"]
PENCERE = (420, 280)
ZOOM = 4


def etiket(img, metin, y=34):
    cv2.putText(img, metin, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(img, metin, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def luma(bgr, sel):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return round(float(g[sel].mean()), 2) if sel.sum() > 20 else None


def kenar_dagilimi(quad, ys, xs):
    """Tasan piksellerin en yakin quad kenarina gore sayimi."""
    q = np.asarray(quad, np.float32)
    p = np.stack([xs, ys], axis=1).astype(np.float32)
    d = []
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]
        ab = b - a
        L = float(np.linalg.norm(ab)) or 1.0
        u = ab / L
        n = np.float32([-u[1], u[0]])
        t = np.clip((p - a) @ u, 0, L)
        yak = a + t[:, None] * u
        d.append(np.linalg.norm(p - yak, axis=1))
    idx = np.argmin(np.stack(d, axis=1), axis=1)
    return {KENAR_ADI[i]: int((idx == i).sum()) for i in range(4)}


def tasma_olc(out, master, soft, quad, wn):
    """Maskenin sert sinirindan disari dogru bant analizi."""
    D = np.abs(out.astype(np.float32) - master.astype(np.float32)).mean(axis=2)
    sert = (soft >= 0.5).astype(np.uint8)
    disari = cv2.distanceTransform(1 - sert, cv2.DIST_L2, 5)
    m_aa = poly_mask_aa(master.shape, quad)
    yakin = (disari > 0) & (disari <= BANT_N)
    satir, tasma = {}, 0
    for k in range(1, BANT_N + 1):
        sel = yakin & (disari > k - 1) & (disari <= k)
        if sel.sum() < 30:
            continue
        oran = float((D[sel] > ESIK).mean())
        satir[f"bant{k}_D"] = round(float(D[sel].mean()), 2)
        satir[f"bant{k}_oran"] = round(oran, 3)
        if oran > ORAN:
            tasma = k
    satir["tasma_px"] = tasma
    if tasma:
        sel = yakin & (disari <= tasma) & (D > ESIK)
        ys, xs = np.nonzero(sel)
        satir["tasma_piksel"] = int(sel.sum())
        satir.update({f"tasma_{k}": v for k, v in kenar_dagilimi(quad, ys, xs).items()})
    else:
        satir["tasma_piksel"] = 0
    # kenar rengi / cerceve rengi
    ic = (cv2.erode(sert, np.ones((7, 7), np.uint8)) == 0) & (sert > 0) & (m_aa > 0.9)
    dis = (disari >= 1) & (disari <= 4)
    satir["wp_kenar_luma"] = luma(wn, ic)
    satir["cerceve_luma"] = luma(master, dis)
    if satir["wp_kenar_luma"] is not None and satir["cerceve_luma"] is not None:
        satir["kontrast"] = round(satir["wp_kenar_luma"] - satir["cerceve_luma"], 2)
    return satir


def ust_pencere(img, quad):
    c = (np.asarray(quad[0], np.float32) + np.asarray(quad[1], np.float32)) / 2.0
    W, H = PENCERE
    x0 = max(0, min(img.shape[1] - W, int(round(c[0] - W / 2))))
    y0 = max(0, min(img.shape[0] - H, int(round(c[1] - H / 2))))
    return img[y0:y0 + H, x0:x0 + W].copy()


def kisim1(pair, calib, calib_dir, masters_dir, wps, scenes, satirlar, crop_dir, dosyalar):
    from wp_mockup_common import SCENES
    for scene in scenes:
        cfg = SCENES[scene]
        src = cfg.get("calib_from", scene)
        master = imread(Path(masters_dir) / cfg["master"])
        for s in calib["scenes"][src]["screens"]:
            if s["device"] != "Phone":
                continue
            quad = np.asarray(s["quad"], np.float32)
            mp = Path(calib_dir) / "masks" / f"{src}_{s['id']}.png"
            soft = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
            if soft is None:
                log(f"  {scene}/{s['id']}: maske yok ({mp.name}) - atlandi")
                continue
            soft = soft.astype(np.float32) / 255.0
            paneller = []
            for ed in EDITIONS:
                wp = wps.get((ed, "Phone"))
                if wp is None:
                    continue
                out = master.astype(np.float32).copy()
                render_screen(out, master, s, wp, wp, "paste", soft, edition_swap=False)
                out_u8 = np.clip(np.round(out), 0, 255).astype(np.uint8)
                wn = warp_cover(wp, quad, master.shape)
                r = dict(cift=pair, kisim="1_TASMA", sahne=scene, ekran=s["id"],
                         edisyon=KISA[ed], uretim_edisyonu=KISA.get(s.get("edition"), s.get("edition")),
                         uretim_modu=s.get("mode"))
                r.update(tasma_olc(out_u8, master, soft, quad, wn))
                satirlar.append(r)
                log(f"  {scene}/{s['id']} {r['edisyon']}: tasma {r['tasma_px']} px "
                    f"({r['tasma_piksel']} px alan) | wp kenar luma {r['wp_kenar_luma']} - "
                    f"cerceve {r['cerceve_luma']} = kontrast {r.get('kontrast')}")
                p = ust_pencere(out_u8, quad)
                etiket(p, f"{r['edisyon']}  tasma {r['tasma_px']}px  kontrast {r.get('kontrast')}")
                paneller.append(p)
            if paneller:
                sat = np.hstack([np.hstack([p, np.full((p.shape[0], 8, 3), 255, np.uint8)]) for p in paneller])
                z = [cv2.resize(p[p.shape[0] // 2 - 35:p.shape[0] // 2 + 35,
                                  p.shape[1] // 2 - 105:p.shape[1] // 2 + 105],
                                (PENCERE[0], PENCERE[1]), interpolation=cv2.INTER_NEAREST) for p in paneller]
                zsat = np.hstack([np.hstack([q, np.full((q.shape[0], 8, 3), 255, np.uint8)]) for q in z])
                panel = np.vstack([sat, np.full((10, sat.shape[1], 3), 255, np.uint8), zsat])
                etiket(panel, f"{pair} {scene} ekran {s['id']} - ust kenar, 4 edisyon (ust 1:1, alt {ZOOM}x)", 300)
                f = Path(crop_dir) / f"M09_{pair}_{scene}_S{s['id']}_UST_4EDISYON.jpg"
                f.parent.mkdir(parents=True, exist_ok=True)
                imwrite_jpeg(f, panel)
                dosyalar.append(f.name)


def hale_satiri(ad, bgr, ink, ek):
    h, _ = hale_profili(bgr, ink)
    r = np.abs(hale_haritasi(bgr))
    kendi = cv2.dilate((ink > 0).astype(np.uint8), np.ones((3, 3), np.uint8))
    halka = (cv2.dilate(kendi, np.ones((21, 21), np.uint8)) > 0) & (kendi == 0)
    uzak = ~(cv2.dilate(kendi, np.ones((41, 41), np.uint8)) > 0)
    row = dict(ek)
    row.update(dosya=ad, hale_0_5=h.get("fark_0_5"), hale_5_10=h.get("fark_5_10"),
               hale_10_20=h.get("fark_10_20"), hale_20_40=h.get("fark_20_40"),
               halka_kalinti=round(float(r[halka].mean()), 3) if halka.sum() > 50 else None,
               uzak_zemin=round(float(r[uzak].mean()), 3) if uzak.sum() > 50 else None,
               murekkep_px=h.get("murekkep_piksel"))
    return row


def kisim2(pair, wp_dir, plate_dir, satirlar):
    up = pair.upper()
    ref = Path(wp_dir) / up / f"AstroLove_{pair}_Midnight_Blue_Watch.jpg"
    ink_ref = ink_mask(imread(ref)) if ref.exists() else None
    for ed in EDITIONS:
        p = Path(wp_dir) / up / f"AstroLove_{pair}_{ed}_Watch.jpg"
        if not p.exists():
            log(f"  {KISA[ed]}: {p.name} yok")
            continue
        wp = imread(p)
        ink = ink_mask(wp)
        kaynak_ink = "kendi"
        # acik edisyonlarda renk tabanli murekkep maskesi bos kalabilir; ayni
        # ciftin MB dosyasi ayni geometriyi tasir, olcum bolgesi karsilastirilabilir olsun
        if (ink > 0).sum() < 50 and ink_ref is not None:
            ink, kaynak_ink = ink_ref, "MB referans"
        ek = dict(cift=pair, kisim="2_SAAT", edisyon=KISA[ed], kaynak="wallpaper",
                  murekkep_maskesi=kaynak_ink, olcu=f"{wp.shape[1]}x{wp.shape[0]}")
        r = hale_satiri(p.name, wp, ink, ek)
        satirlar.append(r)
        log(f"  {KISA[ed]} wallpaper: hale 0-5 {r['hale_0_5']} | 5-10 {r['hale_5_10']} | "
            f"10-20 {r['hale_10_20']} | halka {r['halka_kalinti']} | uzak {r['uzak_zemin']}")
        # wp_build_pair plakalari BUYUK harf adlandirir: PLATE_<ED>_<DEV>.png
        adaylar = [Path(plate_dir) / f"PLATE_{ed.upper()}_WATCH.png",
                   Path(plate_dir) / f"PLATE_{ed}_Watch.png"]
        pl = next((c for c in adaylar if c.exists()), adaylar[0])
        if pl.exists():
            plate = cv2.imread(str(pl), cv2.IMREAD_COLOR)
            if plate is not None and plate.shape[:2] == wp.shape[:2]:
                ek2 = dict(ek); ek2["kaynak"] = "plaka (murekkepsiz)"
                r2 = hale_satiri(pl.name, plate, ink, ek2)
                satirlar.append(r2)
                d = np.abs(wp.astype(np.float32) - plate.astype(np.float32)).mean(axis=2)
                dist = cv2.distanceTransform(1 - (ink > 0).astype(np.uint8), cv2.DIST_L2, 5)
                prof = {}
                for lo, hi in [(0, 2), (2, 5), (5, 10), (10, 20), (20, 40)]:
                    sel = (dist > lo) & (dist <= hi)
                    prof[f"fark_{lo}_{hi}"] = round(float(d[sel].mean()), 2) if sel.sum() > 30 else None
                r3 = dict(cift=pair, kisim="2_SAAT", edisyon=KISA[ed], kaynak="wallpaper - plaka farki",
                          dosya=f"{p.name} - {pl.name}")
                r3.update(prof)
                satirlar.append(r3)
                log(f"  {KISA[ed]} plaka   : hale 0-5 {r2['hale_0_5']} | halka {r2['halka_kalinti']} | "
                    f"uzak {r2['uzak_zemin']}   || fark profili {prof}")
            else:
                log(f"  {KISA[ed]}: plaka olcusu uyusmuyor, atlandi")
        else:
            log(f"  {KISA[ed]}: plaka yok ({pl.name})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True)
    ap.add_argument("--wp-dir", required=True)
    ap.add_argument("--plates", default="")
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--spill-pair", default="", help="kisim 1 icin cift (bos = ilk cift)")
    ap.add_argument("--scenes", default="SET01,SET03,SET04")
    ap.add_argument("--crop-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    pairs = [p.strip() for p in a.pairs.split(",") if p.strip()]
    scenes = [s.strip() for s in a.scenes.split(",") if s.strip()]
    spill = a.spill_pair or pairs[0]
    satirlar, dosyalar = [], []

    up = spill.upper()
    wps = {}
    for ed in EDITIONS:
        f = Path(a.wp_dir) / up / f"AstroLove_{spill}_{ed}_Phone.jpg"
        if f.exists():
            wps[(ed, "Phone")] = imread(f)
    log(f"=== KISIM 1: tasma, {spill} ({len(wps)}/4 edisyon Phone dosyasi) ===")
    kisim1(spill, calib, a.calib, a.masters, wps, scenes, satirlar, a.crop_dir, dosyalar)

    for pair in pairs:
        log(f"\n=== KISIM 2: saat kaynagi, {pair} ===")
        kisim2(pair, a.wp_dir, a.plates or "_yok_", satirlar)

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    log(f"\n{a.out}: {len(satirlar)} satir, {len(dosyalar)} kanit dosyasi")

    lines = ["## 1) TASMA (edisyon bazli)", "",
             "| sahne | ekran | uretim ed. | edisyon | tasma px | tasan piksel | kenarlar | "
             "wp kenar luma | cerceve luma | kontrast |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        if r["kisim"] == "1_TASMA":
            kenar = ", ".join(f"{k} {r[f'tasma_{k}']}" for k in KENAR_ADI if r.get(f"tasma_{k}")) or "-"
            lines.append(f"| {r['sahne']} | {r['ekran']} | {r['uretim_edisyonu']} | {r['edisyon']} | "
                         f"{r['tasma_px']} | {r['tasma_piksel']} | {kenar} | {r['wp_kenar_luma']} | "
                         f"{r['cerceve_luma']} | {r.get('kontrast')} |")
    lines += ["", "## 2) SAAT WALLPAPER KAYNAGI", "",
              "| cift | edisyon | kaynak | hale 0-5 | 5-10 | 10-20 | 20-40 | halka kalinti | uzak zemin |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        if r["kisim"] == "2_SAAT" and "hale_0_5" in r:
            lines.append(f"| {r['cift']} | {r['edisyon']} | {r['kaynak']} | {r['hale_0_5']} | "
                         f"{r['hale_5_10']} | {r['hale_10_20']} | {r['hale_20_40']} | "
                         f"{r['halka_kalinti']} | {r['uzak_zemin']} |")
    fark = [r for r in satirlar if r.get("kaynak") == "wallpaper - plaka farki"]
    if fark:
        lines += ["", "| cift | edisyon | wallpaper-plaka farki 0-2 | 2-5 | 5-10 | 10-20 | 20-40 |",
                  "|---|---|---|---|---|---|---|"]
        for r in fark:
            lines.append(f"| {r['cift']} | {r['edisyon']} | {r.get('fark_0_2')} | {r.get('fark_2_5')} | "
                         f"{r.get('fark_5_10')} | {r.get('fark_10_20')} | {r.get('fark_20_40')} |")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
