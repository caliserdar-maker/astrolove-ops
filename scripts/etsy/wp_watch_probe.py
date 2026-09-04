#!/usr/bin/env python3
"""
SET07 SAAT EKRANI - KUSUR OLCUMU (SALT OKUR) - 4 Eyl 2026 Mo gorevi.

Uretim yok, duzeltme yok, Etsy'ye dokunulmaz. Uretilen tek sey olcum
sayilari ve gorsel kontrol icin kirpmalardir.

  1) KAYNAK MI, YERLESTIRME MI
     Kaynak Watch wallpaper'i (FINAL_V2, Midnight_Blue) ile SET07
     render'indan ayiklanan saat ekrani bolgesi yan yana konur (her ikisi
     de KENDI tam cozunurlugunde; ayrica render bolgesinin x4 NEAREST
     buyutmesi ayri panel olarak eklenir - yeni ayrinti uretmez, yalniz
     ayni pikselleri buyutur).
     Sayisal olcum: zemin gradyaninin duzgunlugu (satir/sutun ortalamasi
     profilinin ikinci turevi) ve sembol cevresi hale profili (murekkep
     maskesinden uzaklik bantlarinda ortalama parlaklik - uzak zemine gore).
     Ayni iki olcum HEM kaynakta HEM render'da yapilir; boylece kusurun
     kaynakta mi yoksa yerlestirmede mi olustugu okunabilir.

  2) YERLESTIRME OLCUSU
     Saat quad'i: kirpma yuzdesi ve hangi kenardan kac px (crop-to-fill),
     olcek faktoru, homografi turu. Mod "relight" ise katman parametreleri
     yazilir ve AYNI bolge iki kez uretilir:
       ONCE  = out + M*(warp(yeni) - warp(pilot))          [yalniz fark]
       SONRA = + murekkep komsulugunda P ile (warp(yeni)+L) [tam relight]
     Ikisi yan yana konur, aralarindaki fark sayiyla verilir.

  3) KAPSAM
     Ayni olcum 3 cift icin kosar; sayilar yan yana raporlanir.
"""
import argparse
import csv
import json
import os
import random
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import (DEVICES, cover_homography, imread, ink_mask, log,  # noqa: E402
                              poly_mask, poly_mask_aa, relight_layer, warp_cover,
                              warp_mask)
from wp_audit_crop import crop_geometry  # noqa: E402

# relight_layer / render_screen icindeki sabitler (wp_mockup_common):
RELIGHT_PARAMS = dict(L_sigma=6.0, L_ink_dilate="7x7", P_ink_dilate="13x13",
                      P_blur_sigma=2.0, M="poly_mask_aa (4x ornekleme)")
BANDS = [(0, 5), (5, 10), (10, 20), (20, 40), (40, 80)]
UP = 4                      # render panelinin NEAREST buyutme carpani
KAPLAMA_ESIK = 12.0         # kaplanmis sayilmak icin en fazla ortalama kanal farki
LABEL_H = 46


def etiket(img, metin):
    bar = np.full((LABEL_H, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, metin, (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (25, 25, 25), 2, cv2.LINE_AA)
    return np.vstack([bar, img])


def yanyana(paneller, bosluk=10):
    h = max(p.shape[0] for p in paneller)
    out = []
    for i, p in enumerate(paneller):
        if p.shape[0] < h:
            pad = np.full((h - p.shape[0], p.shape[1], 3), 245, np.uint8)
            p = np.vstack([p, pad])
        out.append(p)
        if i < len(paneller) - 1:
            out.append(np.full((h, bosluk, 3), 255, np.uint8))
    return np.hstack(out)


# ------------------------------------------------------------------ olcumler
def gradyan_duzgunlugu(bgr, maske_disla=None):
    """Zemin gradyaninin duzgunlugu: satir ve sutun ortalamasi profillerinin
    ikinci turevi. Duzgun gradyanda |d2| kucuk ve bantlanma yok; basamak
    (banding) varsa |d2| tepe yapar."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if maske_disla is not None:
        m = (maske_disla == 0)
        g = np.where(m, g, np.nan)
    with np.errstate(invalid="ignore"):
        satir = np.nanmean(g, axis=1)
        sutun = np.nanmean(g, axis=0)
    out = {}
    for ad, prof in (("satir", satir), ("sutun", sutun)):
        p = prof[~np.isnan(prof)]
        if p.size < 8:
            out[f"{ad}_d2_maks"] = out[f"{ad}_d2_ort"] = float("nan"); continue
        d2 = np.abs(np.diff(p, 2))
        out[f"{ad}_d2_maks"] = round(float(d2.max()), 4)
        out[f"{ad}_d2_ort"] = round(float(d2.mean()), 4)
        out[f"{ad}_aralik"] = round(float(p.max() - p.min()), 2)
    return out


def hale_profili(bgr, ink):
    """Sembol (murekkep) cevresinde uzaklik bantlarinda ortalama parlaklik;
    en uzak bant zemin kabul edilip fark verilir. Hale varsa yakin bantlar
    uzak zeminden belirgin yuksektir."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    ink_b = (ink > 0).astype(np.uint8)
    if ink_b.sum() < 50:
        return {"hale": "murekkep maskesi bos"}, None
    dist = cv2.distanceTransform(1 - ink_b, cv2.DIST_L2, 5)
    out, degerler = {}, []
    for lo, hi in BANDS:
        sel = (dist > lo) & (dist <= hi)
        v = float(g[sel].mean()) if sel.sum() > 30 else float("nan")
        degerler.append(v)
        out[f"bant_{lo}_{hi}"] = round(v, 2) if v == v else None
    uzak = degerler[-1]
    for (lo, hi), v in zip(BANDS, degerler):
        out[f"fark_{lo}_{hi}"] = round(v - uzak, 2) if (v == v and uzak == uzak) else None
    out["murekkep_piksel"] = int(ink_b.sum())
    return out, dist


def kaplama_olcumu(render, src, quad):
    """KUSUR 1: yerlestirilen goruntu quad'i gercekten dolduruyor mu.
    Kaynak cover ile ayni quad'a yeniden yerlestirilir; render ile farki
    KUCUK olan pikseller 'kaplanmis' sayilir. Kaplanmis bolgenin sinir
    kutusu quad sinir kutusuyla karsilastirilip kenar bosluklari olculur."""
    q = np.asarray(quad, np.float32)
    wn = warp_cover(src, q, render.shape).astype(np.float32)
    M = poly_mask(render.shape, q) > 0
    d = np.abs(render.astype(np.float32) - wn).mean(axis=2)
    kapli = M & (d <= KAPLAMA_ESIK)
    x0q, y0q = float(q[:, 0].min()), float(q[:, 1].min())
    x1q, y1q = float(q[:, 0].max()), float(q[:, 1].max())
    out = dict(quad_w=round(x1q - x0q, 1), quad_h=round(y1q - y0q, 1),
               quad_alan_px=int(M.sum()), kapli_px=int(kapli.sum()),
               kaplama_yuzde=round(100.0 * kapli.sum() / max(1, M.sum()), 2),
               kaplama_esik=KAPLAMA_ESIK)
    ys, xs = np.nonzero(kapli)
    if xs.size:
        out.update(kapli_kutu=f"{xs.min()},{ys.min()},{xs.max()},{ys.max()}",
                   bosluk_sol=round(float(xs.min()) - x0q, 1),
                   bosluk_sag=round(x1q - float(xs.max()), 1),
                   bosluk_ust=round(float(ys.min()) - y0q, 1),
                   bosluk_alt=round(y1q - float(ys.max()), 1))
    else:
        out.update(kapli_kutu="yok", bosluk_sol=None, bosluk_sag=None,
                   bosluk_ust=None, bosluk_alt=None)
    return out


def hale_haritasi(bgr):
    """Zeminin genis olcekli bileseninden sapma (kalinti). Hale/leke burada
    gorunur; duzgun gradyanda kalinti sifira yakindir."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = g.shape
    kucuk = cv2.resize(g, (max(1, w // 8), max(1, h // 8)), interpolation=cv2.INTER_AREA)
    k = max(5, (int(min(kucuk.shape) * 0.25) // 2) * 2 + 1)
    bg = cv2.medianBlur(np.clip(kucuk, 0, 255).astype(np.uint8), k).astype(np.float32)
    return g - cv2.resize(bg, (w, h), interpolation=cv2.INTER_LINEAR)


def hale_kaynagi(bgr, kendi_ink, pilot_ink):
    """KUSUR 2: hale kendi sembolunu mu izliyor, yoksa pilot (Cancer_Libra)
    plakasinin murekkep izini mi. Iki maskenin cevre halkasinda kalinti
    enerjisi ayri ayri olculur; kendi murekkebi her iki olcumden de cikarilir."""
    r = np.abs(hale_haritasi(bgr))
    kendi = cv2.dilate((kendi_ink > 0).astype(np.uint8), np.ones((3, 3), np.uint8))
    halka = lambda m: (cv2.dilate(m, np.ones((21, 21), np.uint8)) > 0) & (m == 0) & (kendi == 0)  # noqa: E731
    pil = (pilot_ink > 0).astype(np.uint8) if pilot_ink is not None else None
    out = dict(kalinti_ort=round(float(r.mean()), 3), kalinti_p99=round(float(np.percentile(r, 99)), 2))
    h1 = halka(kendi)
    out["kendi_halka_kalinti"] = round(float(r[h1].mean()), 3) if h1.sum() > 50 else None
    if pil is not None:
        h2 = halka(pil)
        out["pilot_halka_kalinti"] = round(float(r[h2].mean()), 3) if h2.sum() > 50 else None
        uzak = ~(cv2.dilate(np.maximum(kendi, pil), np.ones((41, 41), np.uint8)) > 0)
        out["uzak_zemin_kalinti"] = round(float(r[uzak].mean()), 3) if uzak.sum() > 50 else None
        out["kendi_ink_px"] = int(kendi.sum()); out["pilot_ink_px"] = int(pil.sum())
    return out, r


def ekran_bolgesi(render, quad, pay=6):
    q = np.asarray(quad, np.float32)
    x0, y0 = int(np.floor(q[:, 0].min())) - pay, int(np.floor(q[:, 1].min())) - pay
    x1, y1 = int(np.ceil(q[:, 0].max())) + pay, int(np.ceil(q[:, 1].max())) + pay
    h, w = render.shape[:2]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    return render[y0:y1, x0:x1].copy(), (x0, y0, x1, y1)


def dewarp_ekran(render, wp_shape, quad):
    """Render'daki ekrani kaynak wallpaper koordinatlarina geri tasir
    (cover homografisinin tersi) - kaynakla ayni izgarada karsilastirmak icin."""
    H0, W0 = wp_shape[:2]
    Hc, _ = cover_homography(wp_shape, quad)
    return cv2.warpPerspective(render, np.linalg.inv(Hc.astype(np.float64)), (W0, H0),
                               flags=cv2.INTER_CUBIC)


# ------------------------------------------------------------------ relight
def relight_panelleri(master, screen, wp_new, wp_pilot):
    """render_screen'in relight dalini iki asamada uretir:
    ONCE  = master + M*(w_new - w_pil)                (yalniz fark)
    SONRA = ustune murekkep komsulugu yamasi P*(w_new + L)"""
    quad = np.asarray(screen["quad"], np.float32)
    w_new = warp_cover(wp_new, quad, master.shape).astype(np.float32)
    w_pil = warp_cover(wp_pilot, quad, master.shape).astype(np.float32)
    M = poly_mask_aa(master.shape, quad)[..., None]
    Hc_pilot, _ = cover_homography(wp_pilot.shape, quad)
    ink_w = warp_mask(ink_mask(wp_pilot), Hc_pilot, master.shape)
    L = relight_layer(master, w_pil, quad, ink_w)
    once = master.astype(np.float32) + M * (w_new - w_pil)
    P = cv2.GaussianBlur(cv2.dilate(ink_w, np.ones((13, 13), np.uint8)).astype(np.float32) / 255.0,
                         (0, 0), 2.0)
    P = (P * M[..., 0])[..., None]
    sonra = (1 - P) * once + P * (w_new + L)
    q = poly_mask(master.shape, quad) > 0
    fark = np.abs(sonra - once)[q]
    olcum = dict(P_kapsam_px=int((P[..., 0] > 0.01).sum()),
                 P_maks=round(float(P.max()), 3),
                 L_ort=round(float(np.abs(L[q]).mean()), 3),
                 L_p99=round(float(np.percentile(np.abs(L[q]), 99)), 2),
                 relight_fark_ort=round(float(fark.mean()), 3),
                 relight_fark_maks=round(float(fark.max()), 2))
    clip = lambda a: np.clip(a, 0, 255).astype(np.uint8)   # noqa: E731
    return clip(once), clip(sonra), olcum


# ------------------------------------------------------------------ cift islemi
def do_pair(pair, calib, mock_dir, wp_dir, master_img, pilot_wp, crop_dir, satirlar, haleler,
            mock_dir2=None, etiket2="YENI (paste)"):
    up = pair.upper()
    scr = next(s for s in calib["scenes"]["SET07"]["screens"] if s["device"] == "Watch")
    quad = np.asarray(scr["quad"], np.float32)
    W0, H0 = DEVICES["Watch"]

    src_p = Path(wp_dir) / f"AstroLove_{pair}_Midnight_Blue_Watch.jpg"
    ren_p = Path(mock_dir) / up / f"WA_MOCKUP_V2_SET07_{pair}_FINAL.jpg"
    if not src_p.exists() or not ren_p.exists():
        log(f"  {pair}: eksik dosya ({src_p.name if not src_p.exists() else ren_p.name})")
        return
    src = imread(src_p)
    ren = imread(ren_p)

    # --- 2) yerlestirme olcusu
    g = crop_geometry("Watch", quad)
    kw = float(np.linalg.norm(quad[1] - quad[0]))
    kh = float(np.linalg.norm(quad[3] - quad[0]))
    row = dict(pair=pair, mod=scr.get("mode"), quad_px=f"{kw:.1f}x{kh:.1f}",
               kaynak_px=f"{W0}x{H0}", olcek=round(kw / W0, 5),
               oran_quad=round(g["quad_aspect"], 4), oran_kaynak=round(g["src_aspect"], 4),
               kirpma_yuzde=round(g["crop_pct"], 3), kirpma_kenar=g["edges"],
               kirpilan_oge=g["clipped"], corr=scr.get("corr"), inliers=scr.get("inliers"),
               maske_kalitesi=scr.get("mask_quality"))

    row["kaynak_olcu_dogru"] = "EVET" if (src.shape[1], src.shape[0]) == (W0, H0) else \
        f"HAYIR {src.shape[1]}x{src.shape[0]}"
    row["oran_uyum"] = "EVET" if abs(g["quad_aspect"] - g["src_aspect"]) < 1e-3 else \
        f"HAYIR (fark {g['quad_aspect'] - g['src_aspect']:+.4f})"

    # --- KUSUR 1: quad ne kadar kaplanmis
    row.update(kaplama_olcumu(ren, src, quad))

    # --- 1) kaynak vs render, ayni izgarada olcum
    ink_src = ink_mask(src)
    hale_src, _ = hale_profili(src, ink_src)
    grad_src = gradyan_duzgunlugu(src, maske_disla=cv2.dilate(ink_src, np.ones((15, 15), np.uint8)))
    dew = dewarp_ekran(ren, src.shape, quad)
    hale_ren, _ = hale_profili(dew, ink_src)
    grad_ren = gradyan_duzgunlugu(dew, maske_disla=cv2.dilate(ink_src, np.ones((15, 15), np.uint8)))
    for k, v in hale_src.items():
        row[f"kaynak_hale_{k}"] = v
    for k, v in hale_ren.items():
        row[f"render_hale_{k}"] = v
    for k, v in grad_src.items():
        row[f"kaynak_grad_{k}"] = v
    for k, v in grad_ren.items():
        row[f"render_grad_{k}"] = v
    # --- KUSUR 2: hale kaynagi (kendi sembolu mu, pilot plaka izi mi)
    pilot_ink = ink_mask(pilot_wp) if pilot_wp is not None else None
    hk_src, r_src = hale_kaynagi(src, ink_src, pilot_ink)
    for k, v in hk_src.items():
        row[f"kaynak_{k}"] = v
    hk_ren, _ = hale_kaynagi(dew, ink_src, pilot_ink)
    for k, v in hk_ren.items():
        row[f"render_{k}"] = v
    haleler[pair] = r_src

    # --- 1) gorsel: kaynak | render (native) | render x4 NEAREST
    bolge, kutu = ekran_bolgesi(ren, quad)
    buyuk = cv2.resize(bolge, (bolge.shape[1] * UP, bolge.shape[0] * UP),
                       interpolation=cv2.INTER_NEAREST)
    p1 = etiket(src, f"KAYNAK Watch MB {W0}x{H0} (tam cozunurluk)")
    p2 = etiket(bolge, f"RENDER SET07 saat bolgesi {bolge.shape[1]}x{bolge.shape[0]} (tam coz.)")
    p3 = etiket(buyuk, f"RENDER x{UP} NEAREST {buyuk.shape[1]}x{buyuk.shape[0]} (ayni piksel)")
    Path(crop_dir).mkdir(parents=True, exist_ok=True)
    n1 = f"M07_{pair}_KAYNAK_vs_RENDER.jpg"
    cv2.imwrite(str(Path(crop_dir) / n1), yanyana([p1, p2, p3]),
                [int(cv2.IMWRITE_JPEG_QUALITY), 97])
    row["kirpma_1"] = n1

    # --- 2) relight once/sonra
    if scr.get("mode") == "relight" and master_img is not None and pilot_wp is not None:
        once, sonra, olcum = relight_panelleri(master_img, scr, src, pilot_wp)
        row.update(olcum)
        b1, _ = ekran_bolgesi(once, quad)
        b2, _ = ekran_bolgesi(sonra, quad)
        u1 = cv2.resize(b1, (b1.shape[1] * UP, b1.shape[0] * UP), interpolation=cv2.INTER_NEAREST)
        u2 = cv2.resize(b2, (b2.shape[1] * UP, b2.shape[0] * UP), interpolation=cv2.INTER_NEAREST)
        n2 = f"M07_{pair}_RELIGHT_ONCE_SONRA.jpg"
        cv2.imwrite(str(Path(crop_dir) / n2), yanyana([
            etiket(b1, f"ONCE: fark katmani {b1.shape[1]}x{b1.shape[0]}"),
            etiket(b2, f"SONRA: tam relight {b2.shape[1]}x{b2.shape[0]}"),
            etiket(u1, f"ONCE x{UP} NEAREST"), etiket(u2, f"SONRA x{UP} NEAREST")]),
            [int(cv2.IMWRITE_JPEG_QUALITY), 97])
        row["kirpma_2"] = n2
    # --- ikinci render (or. relight KAPALI): ayni olcumler + uc panelli kanit
    if mock_dir2:
        ren2_p = Path(mock_dir2) / up / f"WA_MOCKUP_V2_SET07_{pair}_FINAL.jpg"
        if not ren2_p.exists():
            log(f"  {pair}: ikinci render yok ({ren2_p})")
        else:
            ren2 = imread(ren2_p)
            k2 = kaplama_olcumu(ren2, src, quad)
            for k, v in k2.items():
                row[f"yeni_{k}"] = v
            dew2 = dewarp_ekran(ren2, src.shape, quad)
            h2, _ = hale_profili(dew2, ink_src)
            for k, v in h2.items():
                row[f"yeni_render_hale_{k}"] = v
            g2 = gradyan_duzgunlugu(dew2, maske_disla=cv2.dilate(ink_src, np.ones((15, 15), np.uint8)))
            for k, v in g2.items():
                row[f"yeni_render_grad_{k}"] = v
            hk2, _ = hale_kaynagi(dew2, ink_src, pilot_ink)
            for k, v in hk2.items():
                row[f"yeni_render_{k}"] = v
            b1, _ = ekran_bolgesi(ren, quad)
            b2, _ = ekran_bolgesi(ren2, quad)
            bs = cv2.resize(src, (b1.shape[1], int(round(src.shape[0] * b1.shape[1] / src.shape[1]))),
                            interpolation=cv2.INTER_AREA)
            u1 = cv2.resize(b1, (b1.shape[1] * UP, b1.shape[0] * UP), interpolation=cv2.INTER_NEAREST)
            u2 = cv2.resize(b2, (b2.shape[1] * UP, b2.shape[0] * UP), interpolation=cv2.INTER_NEAREST)
            n3 = f"M07_{pair}_MEVCUT_YENI_KAYNAK.jpg"
            cv2.imwrite(str(Path(crop_dir) / n3), yanyana([
                etiket(b1, f"MEVCUT (relight) {b1.shape[1]}x{b1.shape[0]}"),
                etiket(b2, f"{etiket2} {b2.shape[1]}x{b2.shape[0]}"),
                etiket(bs, f"KAYNAK (panel enine olcekli, karsilastirma icin)"),
                etiket(u1, f"MEVCUT x{UP} NEAREST"), etiket(u2, f"{etiket2} x{UP} NEAREST"),
                etiket(src, f"KAYNAK {src.shape[1]}x{src.shape[0]} TAM COZUNURLUK")]),
                [int(cv2.IMWRITE_JPEG_QUALITY), 97])
            row["kirpma_3"] = n3
            log(f"  {pair} YENI: kaplama %{k2['kaplama_yuzde']} "
                f"(mevcut %{row['kaplama_yuzde']}) | hale 0-5 {h2.get('fark_0_5')} "
                f"(mevcut {row.get('render_hale_fark_0_5')}, kaynak {row.get('kaynak_hale_fark_0_5')})")

    satirlar.append(row)
    log(f"  {pair}: olcek {row['olcek']}, kirpma %{row['kirpma_yuzde']} [{row['kirpma_kenar']}], "
        f"mod {row['mod']} | kaynak hale 0-5 {row.get('kaynak_hale_fark_0_5')} / "
        f"render {row.get('render_hale_fark_0_5')} | relight fark ort "
        f"{row.get('relight_fark_ort')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--mock-dir", required=True)
    ap.add_argument("--wp-dir", required=True, help="Watch MB wallpaper'lar (duz klasor)")
    ap.add_argument("--master", default="", help="pilot SET07 FINAL (relight icin)")
    ap.add_argument("--pilot-wp", default="", help="pilot Watch MB wallpaper (arsiv)")
    ap.add_argument("--pairs", required=True, help="virgullu cift listesi")
    ap.add_argument("--crop-dir", default="_crops")
    ap.add_argument("--mock-dir2", default="", help="ikinci render koku (or. relight kapali)")
    ap.add_argument("--etiket2", default="YENI (paste)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    scr = next(s for s in calib["scenes"]["SET07"]["screens"] if s["device"] == "Watch")
    log("=== SET07 saat ekrani, kalibrasyon ===")
    log(f"  quad: {np.round(np.asarray(scr['quad']), 2).tolist()}")
    log(f"  mod: {scr.get('mode')}  olcek: {scr.get('scale')}  corr: {scr.get('corr')}  "
        f"inliers: {scr.get('inliers')}  maske kalitesi: {scr.get('mask_quality')}")
    log(f"  homografi: {np.round(np.asarray(scr['H']), 6).tolist()}")
    if scr.get("mode") == "relight":
        log("  relight parametreleri (wp_mockup_common.render_screen / relight_layer):")
        for k, v in RELIGHT_PARAMS.items():
            log(f"    {k} = {v}")

    master_img = imread(a.master) if a.master and Path(a.master).exists() else None
    pilot_wp = imread(a.pilot_wp) if a.pilot_wp and Path(a.pilot_wp).exists() else None
    if scr.get("mode") == "relight" and (master_img is None or pilot_wp is None):
        log("  UYARI: master/pilot wallpaper yok - relight once/sonra uretilemeyecek")

    satirlar, haleler = [], {}
    for pair in [p.strip() for p in a.pairs.split(",") if p.strip()]:
        log(f"\n--- {pair} ---")
        do_pair(pair, calib, a.mock_dir, a.wp_dir, master_img, pilot_wp, a.crop_dir,
                satirlar, haleler, a.mock_dir2 or None, a.etiket2)

    if satirlar:
        cols = list(dict.fromkeys(k for r in satirlar for k in r))
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in satirlar:
                w.writerow(r)
        log(f"\n{a.out}: {len(satirlar)} satir")
        if len(haleler) > 1:
            log("\n=== kaynak hale haritalarinin ciftler arasi benzerligi (NCC) ===")
            adlar = list(haleler)
            for i in range(len(adlar)):
                for j in range(i + 1, len(adlar)):
                    x = haleler[adlar[i]].ravel(); y = haleler[adlar[j]].ravel()
                    xc, yc = x - x.mean(), y - y.mean()
                    d = float(np.sqrt((xc * xc).sum()) * np.sqrt((yc * yc).sum()))
                    log(f"  {adlar[i]} vs {adlar[j]}: NCC {float((xc*yc).sum()/d) if d else float('nan'):.4f}")
        ozet(satirlar)
    return 0


def ozet(rows):
    anahtar = ["kaynak_olcu_dogru", "oran_uyum", "quad_w", "quad_h", "kaplama_yuzde",
               "bosluk_sol", "bosluk_sag", "bosluk_ust", "bosluk_alt",
               "kaynak_kendi_halka_kalinti", "kaynak_pilot_halka_kalinti",
               "kaynak_uzak_zemin_kalinti", "render_kendi_halka_kalinti",
               "render_pilot_halka_kalinti", "render_uzak_zemin_kalinti",
               "yeni_kaplama_yuzde", "yeni_render_hale_fark_0_5", "yeni_render_hale_fark_5_10",
               "yeni_render_hale_fark_10_20", "yeni_render_kendi_halka_kalinti",
               "yeni_render_uzak_zemin_kalinti",
               "olcek", "kirpma_yuzde", "kirpma_kenar", "kirpilan_oge", "mod",
               "kaynak_hale_fark_0_5", "kaynak_hale_fark_5_10", "kaynak_hale_fark_10_20",
               "render_hale_fark_0_5", "render_hale_fark_5_10", "render_hale_fark_10_20",
               "kaynak_grad_satir_d2_maks", "render_grad_satir_d2_maks",
               "kaynak_grad_sutun_d2_maks", "render_grad_sutun_d2_maks",
               "relight_fark_ort", "relight_fark_maks", "L_ort", "L_p99", "P_kapsam_px"]
    lines = ["## SET07 saat ekrani olcumu", "",
             "| olcum | " + " | ".join(r["pair"] for r in rows) + " |",
             "|" + "---|" * (len(rows) + 1)]
    for k in anahtar:
        lines.append(f"| {k} | " + " | ".join(str(r.get(k, "-")) for r in rows) + " |")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
