#!/usr/bin/env python3
"""
SET07 SAAT EKRANI - KALAN HALENIN KAYNAGI (SALT OLCUM) - 4 Eyl 2026.

Relight kapatildiktan sonra da duran sembol-dibi hale (0-5 px) icin, kaynak ile
render arasindaki islem zinciri TEK TEK ele alinir. Her adim ayni olcutle
(hale_profili: murekkep maskesinden uzaklik bantlarinda ortalama parlaklik,
uzak zemine gore fark) olculur, boylece sicramanin hangi adimda oldugu okunur.

Zincir (paste yolu, relight KAPALI):
  0 KAYNAK        kaynak Watch wallpaper, hicbir islem yok
  1 OLCEK         warp_cover ile quad'a yerlestir (0.225) ve inv(Hc) ile geri
                  getir - yalniz yeniden ornekleme (INTER_AREA on-indirme +
                  INTER_CUBIC perspektif + geri INTER_CUBIC)
  2 OLCEK+JPEG    1'in ustune uretimdeki JPEG kodlamasi (q95, 4:4:4, 3000x2250)
  3 +MASKE        2'nin ustune kalibre yumusak maske ile sahne master'ina
                  yapistirma (paste): out = (1-Mp)*master + Mp*warp_cover
  4 MASTER        wallpaper KOYULMADAN sahne master'inin ayni bolgesi

Adim 1-4 hep KAYNAK izgarasinda (1000x1220) olculur: quad 225x274.5 px oldugu
icin geri getirme kacinilmaz olarak buyutme icerir; bu buyutme her adimda AYNI
oldugu icin adimlar arasi FARK anlamlidir. Ayrica kucultulmus uzayda (225x274)
dogrudan olcum de verilir (bant sinirlari o uzayda piksel cinsindendir).

Uretim yok, duzeltme yok, Etsy'ye dokunulmaz.
"""
import argparse
import csv
import json
import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import (DEVICES, cover_homography, imread, imwrite_jpeg,  # noqa: E402
                              ink_mask, log, poly_mask_aa, warp_cover)
from wp_watch_probe import BANDS, hale_profili, hale_haritasi  # noqa: E402


def geri(scene, wp_shape, quad):
    """Sahneden kaynak izgarasina (cover homografisinin tersi)."""
    H0, W0 = wp_shape[:2]
    Hc, _ = cover_homography(wp_shape, quad)
    return cv2.warpPerspective(scene, np.linalg.inv(Hc.astype(np.float64)), (W0, H0),
                               flags=cv2.INTER_CUBIC)


def jpeg_tur(bgr):
    """Uretimdeki kodlama: PIL q95, 4:4:4, baseline (wp_mockup_common.imwrite_jpeg)."""
    tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
    try:
        imwrite_jpeg(tmp, bgr)
        return imread(tmp)
    finally:
        tmp.unlink(missing_ok=True)


def olc(ad, bgr, ink, satirlar, uzay="kaynak (1000x1220)"):
    h, _ = hale_profili(bgr, ink)
    r = np.abs(hale_haritasi(bgr))
    kendi = cv2.dilate((ink > 0).astype(np.uint8), np.ones((3, 3), np.uint8))
    halka = (cv2.dilate(kendi, np.ones((21, 21), np.uint8)) > 0) & (kendi == 0)
    uzak = ~(cv2.dilate(kendi, np.ones((41, 41), np.uint8)) > 0)
    row = dict(adim=ad, uzay=uzay,
               hale_0_5=h.get("fark_0_5"), hale_5_10=h.get("fark_5_10"),
               hale_10_20=h.get("fark_10_20"), hale_20_40=h.get("fark_20_40"),
               halka_kalinti=round(float(r[halka].mean()), 3) if halka.sum() > 50 else None,
               uzak_zemin_kalinti=round(float(r[uzak].mean()), 3) if uzak.sum() > 50 else None,
               murekkep_px=h.get("murekkep_piksel"))
    satirlar.append(row)
    g = lambda k: (f"{row[k]:.2f}" if isinstance(row[k], float) else str(row[k]))  # noqa: E731
    log(f"  {ad:<28} hale 0-5 {g('hale_0_5'):>7} | 5-10 {g('hale_5_10'):>7} | "
        f"10-20 {g('hale_10_20'):>7} | halka kalinti {g('halka_kalinti')} | "
        f"uzak zemin {g('uzak_zemin_kalinti')}")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", required=True)
    ap.add_argument("--master", required=True, help="pilot SET07 FINAL (sahne masteri)")
    ap.add_argument("--wp", required=True, help="kaynak Watch MB wallpaper")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    scr = next(s for s in calib["scenes"]["SET07"]["screens"] if s["device"] == "Watch")
    quad = np.asarray(scr["quad"], np.float32)
    src = imread(a.wp)
    master = imread(a.master)
    W0, H0 = DEVICES["Watch"]
    if (src.shape[1], src.shape[0]) != (W0, H0):
        raise SystemExit(f"HATA: kaynak olcusu {src.shape[1]}x{src.shape[0]}")
    ink = ink_mask(src)
    log(f"=== SET07 saat: hale zinciri, {a.pair} ===")
    log(f"  quad {quad[1][0]-quad[0][0]:.1f}x{quad[3][1]-quad[0][1]:.1f} px, "
        f"olcek {scr['scale']:.4f}, mod {scr.get('mode')} (bu olcumde paste yolu)")
    log(f"  murekkep maskesi: {int((ink>0).sum())} px\n")

    satirlar = []
    # 0 KAYNAK
    olc("0 KAYNAK (islemsiz)", src, ink, satirlar)

    # 1 OLCEK: warp_cover -> geri
    wn = warp_cover(src, quad, master.shape)
    m_aa = poly_mask_aa(master.shape, quad)[..., None]
    s1 = (m_aa * wn.astype(np.float32)).astype(np.uint8)
    olc("1 OLCEK (0.225 + geri)", geri(s1, src.shape, quad), ink, satirlar)

    # 2 OLCEK + uretimdeki JPEG
    s2 = jpeg_tur(s1)
    olc("2 OLCEK + JPEG q95", geri(s2, src.shape, quad), ink, satirlar)

    # 3 + MASKE (paste, master ustune) -- uretimin gercek yolu
    mp = Path(a.calib) / "masks" / f"SET07_{scr['id']}.png"
    soft = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
    if soft is None:
        raise SystemExit(f"HATA: maske yok {mp}")
    soft = soft.astype(np.float32) / 255.0
    log(f"  maske {mp.name}: kapsam {float((soft>0).mean())*100:.2f}% tuval, "
        f"quad icinde ortalama {float(soft[poly_mask_aa(master.shape, quad)>0.5].mean()):.4f}")
    Mp = (soft[..., None] * m_aa)
    s3 = ((1 - Mp) * master.astype(np.float32) + Mp * wn.astype(np.float32))
    s3 = jpeg_tur(np.clip(np.round(s3), 0, 255).astype(np.uint8))
    olc("3 + MASKE (paste+master)", geri(s3, src.shape, quad), ink, satirlar)

    # 4 MASTER: wallpaper KOYULMADAN
    olc("4 MASTER (wallpaper YOK)", geri(master, src.shape, quad), ink, satirlar)

    # kucultulmus uzayda dogrudan olcum (bantlar o uzayin pikseli)
    log("")
    kw = int(round(float(np.linalg.norm(quad[1] - quad[0]))))
    kh = int(round(float(np.linalg.norm(quad[3] - quad[0]))))
    kucuk = cv2.resize(src, (kw, kh), interpolation=cv2.INTER_AREA)
    ink_k = cv2.resize((ink > 0).astype(np.uint8) * 255, (kw, kh), interpolation=cv2.INTER_AREA)
    olc(f"K KAYNAK {kw}x{kh} (INTER_AREA)", kucuk, ink_k, satirlar,
        uzay=f"kucuk ({kw}x{kh}); 1 px = {W0/kw:.2f} kaynak px")

    # --- sicrama analizi (kaynak izgarasindaki 0-4 adimlari)
    zincir = [r for r in satirlar if r["uzay"].startswith("kaynak")][:5]
    log("\n=== SICRAMA (kaynak izgarasi, ardisik adim farki) ===")
    en_buyuk, ad_buyuk = 0.0, ""
    for a_, b_ in zip(zincir, zincir[1:]):
        d = float(b_["hale_0_5"] or 0) - float(a_["hale_0_5"] or 0)
        log(f"  {a_['adim']}  ->  {b_['adim']}: hale 0-5 {a_['hale_0_5']} -> {b_['hale_0_5']}  "
            f"({d:+.2f})")
        if abs(d) > abs(en_buyuk):
            en_buyuk, ad_buyuk = d, f"{a_['adim']} -> {b_['adim']}"
    log(f"\n  EN BUYUK SICRAMA: {ad_buyuk}  ({en_buyuk:+.2f})")

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    log(f"\n{a.out}: {len(satirlar)} satir")

    lines = [f"## SET07 saat: hale zinciri ({a.pair})", "",
             "| adim | uzay | hale 0-5 | 5-10 | 10-20 | halka kalinti | uzak zemin |",
             "|---|---|---|---|---|---|---|"]
    for r in satirlar:
        lines.append(f"| {r['adim']} | {r['uzay']} | {r['hale_0_5']} | {r['hale_5_10']} | "
                     f"{r['hale_10_20']} | {r['halka_kalinti']} | {r['uzak_zemin_kalinti']} |")
    lines += ["", f"**En buyuk sicrama:** {ad_buyuk} ({en_buyuk:+.2f})"]
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
