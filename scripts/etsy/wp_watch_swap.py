#!/usr/bin/env python3
"""
CANVA SAAT DOSYALARINI DOGRULA VE YERINE KOY - 4 Eyl 2026.

Girdi: Canva'dan disa aktarilmis PNG'ler (1000x1220). Her dosya icin:
  1) olcu 1000x1220 mi,
  2) sembol gercekten O CIFTIN sembolu mu: uretimdeki FINAL_V2 Watch dosyasinin
     murekkep maskesi ile IoU olculur; hedef ciftin IoU'su hem esigin ustunde
     hem de diger ciftinkinden buyuk olmali (sayfa -> cift eslesmesinin kaniti),
  3) edisyon dogru mu: zemin (murekkep disi) ortalama BGR'si 4 edisyonun
     FINAL_V2 Watch zeminleriyle karsilastirilir, en yakin olan yazilir.
Gecen dosyalar uretim kodunun bekledigi adla (AstroLove_<Cift>_<Ed>_Watch.jpg)
JPEG q95 4:4:4 olarak yazilir. FINAL_V2'ye DOKUNULMAZ.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import DEVICES, imread, imwrite_jpeg, ink_mask, log  # noqa: E402

IOU_MIN = 0.50


def zemin_bgr(img, ink):
    dis = cv2.dilate((ink > 0).astype(np.uint8), np.ones((31, 31), np.uint8)) == 0
    return np.array([float(img[..., c][dis].mean()) for c in range(3)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="indirilen PNG klasoru (<Cift>__<Ed>.png)")
    ap.add_argument("--wp-old", required=True, help="FINAL_V2 (dogrulama referansi)")
    ap.add_argument("--out", required=True, help="cikti klasoru (<UP>/AstroLove_...jpg)")
    ap.add_argument("--report", required=True)
    a = ap.parse_args()

    W0, H0 = DEVICES["Watch"]
    dosyalar = sorted(Path(a.src).glob("*.png"))
    if not dosyalar:
        raise SystemExit("HATA: PNG bulunamadi")
    ciftler = sorted({f.stem.split("__")[0] for f in dosyalar})
    ref_ink, ref_zemin = {}, {}
    for p in ciftler:
        up = p.upper()
        for ed in ("Midnight_Blue", "Deep_Black", "Champagne_Ivory", "Warm_Parchment"):
            f = Path(a.wp_old) / up / f"AstroLove_{p}_{ed}_Watch.jpg"
            if f.exists():
                im = imread(f)
                ik = ink_mask(im)
                ref_ink[(p, ed)] = ik > 0
                ref_zemin[(p, ed)] = zemin_bgr(im, ik)

    satirlar, ok_all = [], True
    for f in dosyalar:
        pair, ed = f.stem.split("__")
        im = cv2.imread(str(f), cv2.IMREAD_COLOR)
        if im is None:
            raise SystemExit(f"HATA: okunamadi {f}")
        r = dict(dosya=f.name, cift=pair, edisyon=ed, olcu=f"{im.shape[1]}x{im.shape[0]}")
        if (im.shape[1], im.shape[0]) != (W0, H0):
            im = cv2.resize(im, (W0, H0), interpolation=cv2.INTER_AREA)
            r["olcu_duzeltildi"] = f"{W0}x{H0}"
        ik = ink_mask(im) > 0
        for p in ciftler:
            m = ref_ink.get((p, "Midnight_Blue"))
            r[f"iou_{p}"] = round(float((ik & m).sum() / max(1, (ik | m).sum())), 3) if m is not None else None
        iou_hedef = r.get(f"iou_{pair}") or 0.0
        iou_diger = max([v for k, v in r.items() if k.startswith("iou_") and k != f"iou_{pair}" and v] or [0.0])
        z = zemin_bgr(im, ik.astype(np.uint8) * 255)
        r["zemin_bgr"] = "/".join(f"{v:.1f}" for v in z)
        mesafeler = {e: float(np.linalg.norm(z - ref_zemin[(pair, e)]))
                     for e in ("Midnight_Blue", "Deep_Black", "Champagne_Ivory", "Warm_Parchment")
                     if (pair, e) in ref_zemin}
        en_yakin = min(mesafeler, key=mesafeler.get) if mesafeler else None
        r["zemin_en_yakin"] = en_yakin
        r["zemin_mesafe"] = round(mesafeler.get(ed, float("nan")), 1) if mesafeler else None
        r["cift_ok"] = "EVET" if (iou_hedef >= IOU_MIN and iou_hedef > iou_diger) else "HAYIR"
        r["edisyon_ok"] = "EVET" if en_yakin == ed else f"HAYIR ({en_yakin})"
        ok_all &= (r["cift_ok"] == "EVET") and r["edisyon_ok"] == "EVET"
        up = pair.upper()
        hedef = Path(a.out) / up / f"AstroLove_{pair}_{ed}_Watch.jpg"
        hedef.parent.mkdir(parents=True, exist_ok=True)
        imwrite_jpeg(hedef, im)
        r["cikti"] = hedef.name
        satirlar.append(r)
        log(f"  {f.name:<40} IoU(hedef) {iou_hedef:.3f} vs diger {iou_diger:.3f} -> cift {r['cift_ok']} | "
            f"zemin {r['zemin_bgr']} en yakin {en_yakin} -> edisyon {r['edisyon_ok']}")

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    with open(a.report, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    log(f"\nSONUC {'PASS' if ok_all else 'FAIL'}: {len(satirlar)} dosya -> {a.out}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
