#!/usr/bin/env python3
"""
CANVA SAAT SAYFALARI -> CIFT ESLEME (5 Eyl 2026, Mo). Yalniz Midnight_Blue.

Canva API sayfa basligi vermiyor (design_content bos: sayfalarda metin yok).
Bu yuzden esleme ICERIKTEN yapilir: her sayfanin murekkep maskesi, 78 ciftin
uretimdeki FINAL_V2 Midnight_Blue Watch murekkebiyle IoU olarak karsilastirilir;
en yuksek IoU'lu cift o sayfanin ciftidir. Sartlar:
  - en iyi IoU >= IOU_MIN ve ikinci en iyiden en az MARJ kat buyuk,
  - 78 sayfa <-> STATE'teki 78 cift birebir (eksik/fazla/cift sayfa -> HATA, yazma yok),
  - olcu 1000x1220, zemin edisyonu Midnight_Blue (4 edisyon zemin rengine gore),
  - beklenen sayfa sirasi (watch_sayfa_sirasi.txt, alfabetik) ile fark varsa
    raporlanir (hata degil; esleme icerikten).
Gecenler <out>/<UP>/AstroLove_<Cift>_Midnight_Blue_Watch.jpg (q95, 4:4:4) olarak yazilir.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import DEVICES, EDITIONS, imread, imwrite_jpeg, ink_mask, log  # noqa: E402

IOU_MIN = 0.50
MARJ = 1.25
ED = "Midnight_Blue"


def zemin_bgr(img, ink):
    dis = cv2.dilate((ink > 0).astype(np.uint8), np.ones((31, 31), np.uint8)) == 0
    return np.array([float(img[..., c][dis].mean()) for c in range(3)])


def iou(a, b):
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum()) / u if u else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, help="sayfa dosyalari (page_NN.png/jpg)")
    ap.add_argument("--ref", required=True, help="FINAL_V2 koku (<UP>/AstroLove_<Cift>_<Ed>_Watch.jpg)")
    ap.add_argument("--pairs", required=True, help="STATE csv (ilk sutun cift)")
    ap.add_argument("--sira", default=str(Path(__file__).parent / "watch_sayfa_sirasi.txt"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    pairs = [r[0].strip() for r in csv.reader(open(a.pairs, encoding="utf-8")) if r and r[0].strip() and r[0] != "pair"]
    FIX = {"VIGRO": "VIRGO"}
    sira = []
    for ln in Path(a.sira).read_text().split():
        s1, s2 = (FIX.get(x, x) for x in ln.strip().upper().split("_"))
        sira.append(f"{s1.capitalize()}_{s2.capitalize()}")
    W0, H0 = DEVICES["Watch"]
    sayfalar = sorted([p for p in Path(a.pages).iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")],
                      key=lambda p: int(re.findall(r"\d+", p.stem)[-1]))
    log(f"sayfa {len(sayfalar)}, cift {len(pairs)}")
    # referans murekkepler (MB) + zemin renkleri (4 edisyon; edisyon tespiti icin)
    ref_ink, zeminler = {}, {ed: [] for ed in EDITIONS}
    for p in pairs:
        up = p.upper()
        for ed in EDITIONS:
            f = Path(a.ref) / up / f"AstroLove_{p}_{ed}_Watch.jpg"
            if not f.exists():
                if ed == ED:
                    raise SystemExit(f"HATA: referans yok {f}")
                continue
            im = imread(f)
            ik = ink_mask(im) > 0
            if ed == ED:
                ref_ink[p] = ik
            zeminler[ed].append(zemin_bgr(im, ik))
    zemin_ed = {ed: np.median(np.stack(v), axis=0) for ed, v in zeminler.items() if v}
    satirlar, esleme, hata = [], {}, []
    for i, f in enumerate(sayfalar):
        no = i + 1
        im = imread(f)
        h, w = im.shape[:2]
        if (w, h) != (W0, H0):
            hata.append(f"sayfa {no}: olcu {w}x{h}")
            satirlar.append([no, f.name, "", "", "", "", "FAIL olcu"])
            continue
        ik = ink_mask(im) > 0
        skor = sorted(((iou(ik, r), p) for p, r in ref_ink.items()), reverse=True)
        (s1, p1), (s2, p2) = skor[0], skor[1]
        z = zemin_bgr(im, ik)
        ed = min(zemin_ed, key=lambda e: np.linalg.norm(zemin_ed[e] - z))
        bekl = sira[i] if i < len(sira) else ""
        durum = "PASS"
        if s1 < IOU_MIN or s1 < MARJ * s2:
            durum = "FAIL esleme"
        if ed != ED:
            durum = "FAIL edisyon"
        if durum == "PASS":
            if p1 in esleme:
                durum = f"FAIL cift sayfa ({esleme[p1]})"
            else:
                esleme[p1] = no
        if durum != "PASS":
            hata.append(f"sayfa {no}: {durum} (en iyi {p1} {s1:.3f}, ikinci {p2} {s2:.3f}, zemin {ed})")
        satirlar.append([no, f.name, p1, f"{s1:.3f}", f"{p2}:{s2:.3f}", ed, durum + ("" if bekl == p1 else f" | sira farki: beklenen {bekl}")])
        log(f"  sayfa {no:2d}: {p1:<24} IoU {s1:.3f} (2. {p2} {s2:.3f}) zemin {ed} {durum}"
            + ("" if bekl == p1 else f" | SIRA FARKI beklenen {bekl}"))
    eksik = sorted(set(pairs) - set(esleme))
    fazla = [p for p in esleme if p not in pairs]
    with open(a.report, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sayfa", "dosya", "cift", "iou", "ikinci", "zemin_edisyon", "durum"])
        w.writerows(satirlar)
        w.writerow(["OZET", f"sayfa {len(sayfalar)}", f"eslesen {len(esleme)}", f"eksik {len(eksik)}", f"fazla {len(fazla)}", "", "PASS" if not (hata or eksik or fazla) else "FAIL"])
    if hata or eksik or fazla or len(esleme) != len(pairs):
        for h_ in hata:
            log("HATA " + h_)
        if eksik:
            log("EKSIK cift: " + ", ".join(eksik))
        if fazla:
            log("FAZLA cift: " + ", ".join(fazla))
        raise SystemExit(f"DUR: esleme tamamlanmadi (sayfa {len(sayfalar)}, eslesen {len(esleme)}, cift {len(pairs)}); hicbir dosya yazilmadi")
    for p, no in esleme.items():
        up = p.upper()
        (Path(a.out) / up).mkdir(parents=True, exist_ok=True)
        imwrite_jpeg(Path(a.out) / up / f"AstroLove_{p}_{ED}_Watch.jpg", imread(sayfalar[no - 1]))
    sira_fark = sum(1 for i, f in enumerate(sayfalar) if i < len(sira) and satirlar[i][2] != sira[i])
    log(f"SONUC PASS: {len(esleme)} sayfa -> {len(esleme)} cift, sira farki {sira_fark}, yazildi {a.out}")


if __name__ == "__main__":
    main()
