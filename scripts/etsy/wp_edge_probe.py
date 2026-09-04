#!/usr/bin/env python3
"""
SET07 KUCULTME YONTEMI + SET03/SET04 EKRAN KENARI - SALT OLCUM - 4 Eyl 2026.

A) SET07 saat: hale sicramasini ureten adim olcekleme oldugu icin (kaynak 5.03
   -> olcek sonrasi 13.68), uc kucultme yolu ayni olcutle karsilastirilir:
     mevcut   : ~2x hedef olcege INTER_AREA on-indirme + INTER_CUBIC perspektif
                (wp_mockup_common.warp_cover)
     INTER_AREA: cover kirpmasi DOGRUDAN quad olcusune INTER_AREA, sonra
                birebir olcekte INTER_LINEAR perspektif
     LANCZOS4 : on-indirme yok, dogrudan INTER_LANCZOS4 perspektif
   Her yolun ciktisi ayni sekilde (inv(Hc), INTER_CUBIC) kaynak izgarasina
   dondurulur ve hale bantlari olculur; kaynaga en yakin olan yazilir.

B) SET03 / SET04 ekran kenari: kenar yumusakligi ve tirtiklanma OLCULUR.
   Render'in ekran kenari, kalibre yumusak maskenin (masks/<SET>_<id>.png)
   0.5 seviyesinin gectigi yerdir; bu yuzden olcum maske uzerinde yapilir:
     gecis_px    : 0.05<m<0.95 bandinin kalinligi (ara piksel / kontur boyu)
     tirtik_rms  : maske 0.5 konturunun, kenara uydurulan DOGRUdan dik sapmasi
     tirtik_maks : ayni sapmanin en buyugu (px; wallpaper pikseli karsiligi da)
     kalite      : maske alani / quad alani (1'den kucuk = quad icinde maske
                   disi kalan bolge)
   Ayrica quad olcusu, olcek ve cover kirpmasi (yuzde + kenar) yazilir.

C) Kanit gorselleri (tam cozunurluk, yeniden ornekleme yok):
     M08_<cift>_<sahne>_S<id>_KENAR.jpg  4 kenar; her satir 1:1 pencere + 4x
                                          NEAREST buyutme
     M08_<cift>_<sahne>_TAM.jpg          tam sahne + ekran bolgesi 1:1

Uretim yok, duzeltme yok, Etsy'ye dokunulmaz.
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import (DEVICES, cover_homography, imread, imwrite_jpeg,  # noqa: E402
                              ink_mask, log, poly_mask_aa, quad_scale, warp_cover)
from wp_audit_crop import crop_geometry  # noqa: E402
from wp_watch_probe import hale_profili, hale_haritasi  # noqa: E402

KENAR_ADI = ["UST", "SAG", "ALT", "SOL"]     # quad kose sirasi TL,TR,BR,BL
PENCERE = (420, 280)                          # 1:1 kenar penceresi (gen x yuk)
ZOOM = 4                                      # NEAREST buyutme carpani
BANT = 6.0                                    # kontur noktasi kenara en fazla bu kadar uzak
UC_PAY = 0.12                                 # kenar uclarindan atilan oran (kose disarida)


# --------------------------------------------------------------- ortak yardimci
def etiket(img, metin, y=34):
    cv2.putText(img, metin, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(img, metin, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def geri(scene, wp_shape, quad):
    H0, W0 = wp_shape[:2]
    Hc, _ = cover_homography(wp_shape, quad)
    return cv2.warpPerspective(scene, np.linalg.inv(Hc.astype(np.float64)), (W0, H0),
                               flags=cv2.INTER_CUBIC)


# --------------------------------------------------------------- A) SET07 yontemleri
def warp_area_dogrudan(wp, quad, shape):
    """Cover kirpmasi DOGRUDAN quad olcusune INTER_AREA; sonra 1:1 perspektif."""
    Hc, src = cover_homography(wp.shape, quad)
    x0, y0 = int(round(float(src[0][0]))), int(round(float(src[0][1])))
    x1, y1 = int(round(float(src[2][0]))), int(round(float(src[2][1])))
    crop = wp[y0:y1, x0:x1]
    qw = max(1, int(round(float(np.linalg.norm(np.asarray(quad[1]) - np.asarray(quad[0]))))))
    qh = max(1, int(round(float(np.linalg.norm(np.asarray(quad[3]) - np.asarray(quad[0]))))))
    kucuk = cv2.resize(crop, (qw, qh), interpolation=cv2.INTER_AREA)
    rect = np.float32([[0, 0], [qw, 0], [qw, qh], [0, qh]])
    H2 = cv2.getPerspectiveTransform(rect, np.asarray(quad, np.float32))
    return cv2.warpPerspective(kucuk, H2, (shape[1], shape[0]), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT)


def warp_lanczos(wp, quad, shape):
    """On-indirme yok: dogrudan LANCZOS4 perspektif."""
    Hc, _ = cover_homography(wp.shape, quad)
    return cv2.warpPerspective(wp, Hc.astype(np.float64), (shape[1], shape[0]),
                               flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT)


def olc_hale(ad, bgr, ink, pair, satirlar, ek=None):
    h, _ = hale_profili(bgr, ink)
    r = np.abs(hale_haritasi(bgr))
    kendi = cv2.dilate((ink > 0).astype(np.uint8), np.ones((3, 3), np.uint8))
    halka = (cv2.dilate(kendi, np.ones((21, 21), np.uint8)) > 0) & (kendi == 0)
    uzak = ~(cv2.dilate(kendi, np.ones((41, 41), np.uint8)) > 0)
    row = dict(cift=pair, kisim="A_SET07_YONTEM", yontem=ad,
               hale_0_5=h.get("fark_0_5"), hale_5_10=h.get("fark_5_10"),
               hale_10_20=h.get("fark_10_20"), hale_20_40=h.get("fark_20_40"),
               halka_kalinti=round(float(r[halka].mean()), 3) if halka.sum() > 50 else None,
               uzak_zemin=round(float(r[uzak].mean()), 3) if uzak.sum() > 50 else None)
    row.update(ek or {})
    satirlar.append(row)
    log(f"  {ad:<38} hale 0-5 {row['hale_0_5']:>7} | 5-10 {row['hale_5_10']:>7} | "
        f"10-20 {row['hale_10_20']:>7} | halka {row['halka_kalinti']} | uzak {row['uzak_zemin']}")
    return row


def kisim_a(pair, calib, wp_path, master, satirlar):
    scr = next(s for s in calib["scenes"]["SET07"]["screens"] if s["device"] == "Watch")
    quad = np.asarray(scr["quad"], np.float32)
    src = imread(wp_path)
    W0, H0 = DEVICES["Watch"]
    if (src.shape[1], src.shape[0]) != (W0, H0):
        raise SystemExit(f"HATA: kaynak {src.shape[1]}x{src.shape[0]}")
    ink = ink_mask(src)
    m_aa = poly_mask_aa(master.shape, quad)[..., None]
    log(f"--- A) SET07 kucultme yontemleri, {pair} "
        f"(quad {np.linalg.norm(quad[1]-quad[0]):.1f}x{np.linalg.norm(quad[3]-quad[0]):.1f}, "
        f"olcek {scr['scale']:.4f})")
    kaynak = olc_hale("0 KAYNAK (islemsiz)", src, ink, pair, satirlar)
    k0 = float(kaynak["hale_0_5"])
    yollar = [
        ("mevcut: INTER_AREA ~2x + INTER_CUBIC", warp_cover),
        ("INTER_AREA (dogrudan quad olcusune)", warp_area_dogrudan),
        ("LANCZOS4 (on-indirme yok)", warp_lanczos),
    ]
    sonuc = []
    for ad, fn in yollar:
        wn = fn(src, quad, master.shape)
        s = (m_aa * wn.astype(np.float32)).astype(np.uint8)
        row = olc_hale(ad, geri(s, src.shape, quad), ink, pair, satirlar,
                       ek={"kaynaga_fark": None})
        row["kaynaga_fark"] = round(float(row["hale_0_5"]) - k0, 2)
        sonuc.append((abs(row["kaynaga_fark"]), ad, row["hale_0_5"]))
    sonuc.sort()
    log(f"  KAYNAGA EN YAKIN: {sonuc[0][1]}  (hale 0-5 {sonuc[0][2]}, kaynak {k0}, "
        f"fark {sonuc[0][0]:+.2f})")
    return sonuc[0][1], k0, sonuc


# --------------------------------------------------------------- B) kenar olcumu
def kontur_05(soft):
    b = (soft > 0.5).astype(np.uint8)
    cs, _ = cv2.findContours(b, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None, 0.0
    c = max(cs, key=cv2.contourArea)
    return c.reshape(-1, 2).astype(np.float32), float(cv2.arcLength(c, True))


def kenar_tirtik(pts, a, b):
    """a-b kenarina yakin kontur noktalarinin, o noktalara uydurulan DOGRUdan
    dik sapmasi (rms, maks, n). Kose bolgeleri UC_PAY ile disarida birakilir."""
    a = np.asarray(a, np.float32); b = np.asarray(b, np.float32)
    d = b - a
    L = float(np.linalg.norm(d))
    if L < 1 or pts is None or len(pts) == 0:
        return None, None, 0
    u = d / L
    n = np.float32([-u[1], u[0]])
    rel = pts - a
    t = rel @ u
    h = rel @ n
    sel = (np.abs(h) <= BANT) & (t > UC_PAY * L) & (t < (1 - UC_PAY) * L)
    if sel.sum() < 20:
        return None, None, int(sel.sum())
    p = pts[sel]
    vx, vy, x0, y0 = cv2.fitLine(p, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
    nn = np.float32([-vy, vx])
    res = (p - np.float32([x0, y0])) @ nn
    return round(float(np.sqrt((res ** 2).mean())), 3), round(float(np.abs(res).max()), 2), int(sel.sum())


def kenar_pencere(render, a, b):
    """Kenar ortasinda 1:1 pencere + ayni pencerenin 4x NEAREST buyutmesi."""
    c = ((np.asarray(a, np.float32) + np.asarray(b, np.float32)) / 2.0)
    W, H = PENCERE
    x0 = int(round(c[0] - W / 2)); y0 = int(round(c[1] - H / 2))
    x0 = max(0, min(render.shape[1] - W, x0)); y0 = max(0, min(render.shape[0] - H, y0))
    win = render[y0:y0 + H, x0:x0 + W].copy()
    zw, zh = W // ZOOM, H // ZOOM
    sub = win[H // 2 - zh // 2:H // 2 - zh // 2 + zh, W // 2 - zw // 2:W // 2 - zw // 2 + zw]
    zoom = cv2.resize(sub, (W, H), interpolation=cv2.INTER_NEAREST)
    return win, zoom, (x0, y0)


def kisim_b(pair, scene, calib, calib_dir, render, satirlar, crop_dir):
    up = pair.upper()
    scr_list = calib["scenes"][scene]["screens"]
    paneller = []
    for scr in scr_list:
        quad = np.asarray(scr["quad"], np.float32)
        dev = scr["device"]
        sid = scr["id"]
        mp = Path(calib_dir) / "masks" / f"{scene}_{sid}.png"
        soft = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
        if soft is None:
            log(f"  {scene}/{sid}: maske yok ({mp.name})")
            continue
        soft = soft.astype(np.float32) / 255.0
        g = crop_geometry(dev, quad)
        qw = float(np.linalg.norm(quad[1] - quad[0]))
        qh = float(np.linalg.norm(quad[3] - quad[0]))
        olcek = quad_scale(quad, float(g["kept"][2] - g["kept"][0]))
        pts, cevre = kontur_05(soft)
        ara = int(((soft > 0.05) & (soft < 0.95)).sum())
        row = dict(cift=pair, kisim="B_KENAR", sahne=scene, ekran=sid, cihaz=dev,
                   quad_px=f"{qw:.1f}x{qh:.1f}", olcek=round(olcek, 5),
                   kirpma_yuzde=round(g["crop_pct"], 3), kirpma_kenar=g["edges"],
                   maske_kalitesi=scr.get("mask_quality"), kontur_px=round(cevre, 1),
                   ara_piksel=ara, gecis_px=round(ara / cevre, 3) if cevre > 1 else None)
        for i, ad in enumerate(KENAR_ADI):
            rms, mx, n = kenar_tirtik(pts, quad[i], quad[(i + 1) % 4])
            row[f"tirtik_rms_{ad}"] = rms
            row[f"tirtik_maks_{ad}"] = mx
            row[f"tirtik_n_{ad}"] = n
        rmsler = [row[f"tirtik_rms_{a}"] for a in KENAR_ADI if row[f"tirtik_rms_{a}"] is not None]
        mxler = [row[f"tirtik_maks_{a}"] for a in KENAR_ADI if row[f"tirtik_maks_{a}"] is not None]
        row["tirtik_rms_ort"] = round(float(np.mean(rmsler)), 3) if rmsler else None
        row["tirtik_maks_en"] = max(mxler) if mxler else None
        row["tirtik_maks_wp_px"] = round(max(mxler) / olcek, 1) if (mxler and olcek) else None
        satirlar.append(row)
        log(f"  {scene}/{sid} {dev:<7} quad {row['quad_px']:>13} olcek {olcek:.4f} | "
            f"gecis {row['gecis_px']} px | tirtik rms {row['tirtik_rms_ort']} maks "
            f"{row['tirtik_maks_en']} px ({row['tirtik_maks_wp_px']} wp px) | "
            f"maske kalite {row['maske_kalitesi']}")

        # kanit paneli: 4 kenar, her satir [1:1 | 4x NEAREST]
        satir_img = []
        for i, ad in enumerate(KENAR_ADI):
            win, zoom, (x0, y0) = kenar_pencere(render, quad[i], quad[(i + 1) % 4])
            etiket(win, f"{ad} 1:1  ({x0},{y0})")
            etiket(zoom, f"{ad} {ZOOM}x  rms {row[f'tirtik_rms_{ad}']} maks {row[f'tirtik_maks_{ad}']}")
            satir_img.append(np.hstack([win, np.full((win.shape[0], 8, 3), 255, np.uint8), zoom]))
        panel = np.vstack([np.vstack([s, np.full((8, s.shape[1], 3), 255, np.uint8)])
                           for s in satir_img])
        p = Path(crop_dir) / f"M08_{pair}_{scene}_S{sid}_KENAR.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        imwrite_jpeg(p, panel)
        paneller.append(p.name)

    # tam sahne + ekran bolgeleri 1:1
    qs = [np.asarray(s["quad"], np.float32) for s in scr_list]
    tam = render.copy()
    kucuk = cv2.resize(tam, (1600, int(round(1600 * tam.shape[0] / tam.shape[1]))),
                       interpolation=cv2.INTER_AREA)
    etiket(kucuk, f"{pair} {scene} - tam sahne (kucultulmus goruntu)")
    parcalar = []
    for s, q in zip(scr_list, qs):
        x0, y0 = int(q[:, 0].min()) - 20, int(q[:, 1].min()) - 20
        x1, y1 = int(q[:, 0].max()) + 20, int(q[:, 1].max()) + 20
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(render.shape[1], x1), min(render.shape[0], y1)
        c = render[y0:y1, x0:x1].copy()
        etiket(c, f"ekran {s['id']} 1:1")
        parcalar.append(c)
    hmax = max(p.shape[0] for p in parcalar)
    parcalar = [np.vstack([p, np.full((hmax - p.shape[0], p.shape[1], 3), 255, np.uint8)])
                for p in parcalar]
    alt = np.hstack([np.hstack([p, np.full((hmax, 10, 3), 255, np.uint8)]) for p in parcalar])
    gen = max(kucuk.shape[1], alt.shape[1])
    ust = np.hstack([kucuk, np.full((kucuk.shape[0], gen - kucuk.shape[1], 3), 255, np.uint8)])
    alt = np.hstack([alt, np.full((alt.shape[0], gen - alt.shape[1], 3), 255, np.uint8)])
    p = Path(crop_dir) / f"M08_{pair}_{scene}_TAM.jpg"
    imwrite_jpeg(p, np.vstack([ust, np.full((12, gen, 3), 255, np.uint8), alt]))
    paneller.append(p.name)
    return paneller


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--masters", required=True, help="pilot FINAL sahne masterlari")
    ap.add_argument("--mock-dir", required=True, help="MOCKUP_V2 (cift klasorleri)")
    ap.add_argument("--wp-dir", required=True, help="FINAL_V2 (cift klasorleri)")
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--scenes", default="SET03,SET04")
    ap.add_argument("--crop-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    master07 = imread(Path(a.masters) / "WA_MOCKUP_V2_SET07_Cancer_Libra_FINAL.jpg")
    pairs = [p.strip() for p in a.pairs.split(",") if p.strip()]
    scenes = [s.strip() for s in a.scenes.split(",") if s.strip()]
    satirlar, dosyalar, ozet_a = [], [], []

    for pair in pairs:
        up = pair.upper()
        log(f"\n=== {pair} ===")
        wp07 = Path(a.wp_dir) / up / f"AstroLove_{pair}_Midnight_Blue_Watch.jpg"
        if wp07.exists():
            en_yakin, k0, sira = kisim_a(pair, calib, wp07, master07, satirlar)
            ozet_a.append((pair, en_yakin, k0, sira))
        else:
            log(f"  A atlandi: {wp07.name} yok")
        for scene in scenes:
            ren = Path(a.mock_dir) / up / f"WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg"
            if not ren.exists():
                log(f"  B atlandi: {ren.name} yok")
                continue
            log(f"--- B) {scene} ekran kenarlari, {pair}")
            dosyalar += kisim_b(pair, scene, calib, a.calib, imread(ren), satirlar, a.crop_dir)

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    log(f"\n{a.out}: {len(satirlar)} satir, {len(dosyalar)} kanit dosyasi")

    lines = ["## A) SET07 kucultme yontemi", "",
             "| cift | yontem | hale 0-5 | 5-10 | 10-20 | kaynaga fark |", "|---|---|---|---|---|---|"]
    for r in satirlar:
        if r["kisim"] == "A_SET07_YONTEM":
            lines.append(f"| {r['cift']} | {r['yontem']} | {r['hale_0_5']} | {r['hale_5_10']} | "
                         f"{r['hale_10_20']} | {r.get('kaynaga_fark')} |")
    for pair, en_yakin, k0, _ in ozet_a:
        lines.append(f"\n**{pair}: kaynaga en yakin -> {en_yakin}** (kaynak hale 0-5 {k0})")
    lines += ["", "## B) SET03 / SET04 ekran kenari", "",
              "| cift | sahne | ekran | cihaz | quad | olcek | kirpma % | gecis px | "
              "tirtik rms | tirtik maks | wp px | maske kalite |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        if r["kisim"] == "B_KENAR":
            lines.append(f"| {r['cift']} | {r['sahne']} | {r['ekran']} | {r['cihaz']} | {r['quad_px']} | "
                         f"{r['olcek']} | {r['kirpma_yuzde']} | {r['gecis_px']} | {r['tirtik_rms_ort']} | "
                         f"{r['tirtik_maks_en']} | {r['tirtik_maks_wp_px']} | {r['maske_kalitesi']} |")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
