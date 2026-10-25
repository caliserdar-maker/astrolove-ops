#!/usr/bin/env python3
"""V3 uretim hattinin GERCEK olcudeki (7200x9600) adim sureleri - sentetik girdiyle.

GOREV_0014 HIZ maddesi: 26 dk -> hedef 10 dk. Drive'daki gercek baski dosyalari
bu kapta yok; bu yuzden ayni piksel sayisi ve ayni kod yolu sentetik veriyle
olculur. Tahmin yok: her adim ayri ayri saniye cinsinden yazilir ve toplam kosu
suresi olculen adimlardan turetilir.

Kullanim: python3 olc_hiz.py [--cihaz-isci 1,3] [--tekrar 1]
"""
import argparse, json, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

import importlib.util
_s = importlib.util.spec_from_file_location("wp_siparis", Path(__file__).resolve().parent / "wp_siparis.py")
SP = importlib.util.module_from_spec(_s); _s.loader.exec_module(SP)
V2 = SP.V2
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
from wp_plate_pilot import INK_RGB, BOX_NAMES                                  # noqa: E402
import wp_build_pair as WBP                                                    # noqa: E402

W, H = SP.POSTER_W, SP.POSTER_H
ED = "Midnight_Blue"


def sentetik(kok):
    """plate + isimli baski (24x32) ve CLEAN cihaz plakalari - gercek olculerde."""
    kok = Path(kok); kok.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    zemin = np.array(V2.ZEMIN[ED] if hasattr(V2, "ZEMIN") else (60, 40, 25), np.int16)
    plate = np.clip(zemin[None, None, :] + rng.integers(-3, 4, (H, W, 3)), 0, 255).astype(np.uint8)
    ink = np.array(INK_RGB[ED][::-1] if ED in INK_RGB else (210, 200, 180), np.uint8)  # BGR
    baski = plate.copy()
    x0, y0, x1, y1 = V2.BOX_SYMBOL_CORE
    baski[y0:y1, x0:x1] = ink                                   # fuzyon sembolu
    hb = SP.halka_bandi()
    baski[hb > 0] = ink                                         # halka bandi
    ny0, ny1 = BOX_NAMES[1] + 50, BOX_NAMES[3] - 50
    for cx0, cx1 in ((1800, 2900), (3300, 3900), (4300, 5400)):  # isim + sonsuz + isim
        baski[ny0:ny1, cx0:cx1] = ink
    mb = SP.MESAJ_BANT
    baski[mb[1] + 150:mb[3] - 150, 2600:4600] = ink             # mesaj
    cv2.imwrite(str(kok / f"{ED.upper()}_24X32.png"), plate)
    cv2.imwrite(str(kok / f"SIPARIS_TEST_{ED}_24x32.png"), baski)
    for dev, (dw, dh) in SP.DEVICES.items():
        cv2.imwrite(str(kok / f"PLATE_{ED.upper()}_{dev.upper()}_CLEAN.png"),
                    np.clip(zemin[None, None, :] + rng.integers(-3, 4, (dh, dw, 3)), 0, 255).astype(np.uint8))
        cv2.imwrite(str(kok / f"PLATE_{ED.upper()}_{dev.upper()}.png"),
                    np.clip(zemin[None, None, :] + rng.integers(-3, 4, (dh, dw, 3)), 0, 255).astype(np.uint8))
    return kok


def olc(kok, cikti, isci=1, tani_hale=False):
    kok, cikti = Path(kok), Path(cikti); cikti.mkdir(parents=True, exist_ok=True)
    s = {}
    t = time.time(); baski = SP.imread(kok / f"SIPARIS_TEST_{ED}_24x32.png"); plate = SP.imread(kok / f"{ED.upper()}_24X32.png")
    s["okuma_2_dosya"] = round(time.time() - t, 2)
    t = time.time(); _f, _a, alfa_o1, _t1 = SP.murekkep(baski, plate, ED, "birak", "uzaklik",
                                                        sadece_olcum=True)
    s["murekkep_olcum"] = round(time.time() - t, 2)      # 1. asama (fark/alfa uretilmez)
    del _f, _a, alfa_o1
    t = time.time(); fark, alfa, alfa_o, tani = SP.murekkep(baski, plate, ED, "birak", "uzaklik")
    s["murekkep"] = round(time.time() - t, 2)            # 2. asama (tam)
    t = time.time(); kutu, _b = SP.kutular_olc(alfa_o, True)
    s["kutular_olc"] = round(time.time() - t, 2)
    bant = SP.halka_bandi()
    urun, rapor = {}, []
    t = time.time()
    if isci > 1:                      # cihaz basina sinirli paralellik (ayni girdi, ayri tuval)
        def tek(dev):
            u, r = {}, []
            SP.uret(ED, baski, plate, fark, alfa, kok, kok, cikti, "TEST", kutu, "fark", u, r,
                    str(kok), bant, tani, ED, tani_hale, [dev])
            return u, r
        with ThreadPoolExecutor(max_workers=isci) as ex:
            for u, r in ex.map(tek, list(V2.CIHAZLAR)):
                urun.update(u); rapor += r
    else:
        SP.uret(ED, baski, plate, fark, alfa, kok, kok, cikti, "TEST", kutu, "fark", urun, rapor,
                str(kok), bant, tani, ED, tani_hale)
    s["uret_3_cihaz"] = round(time.time() - t, 2)
    s["tani_hale"] = tani_hale
    s["cihaz_isci"] = isci
    s["dosya"] = len(rapor)
    del baski, plate, fark, alfa, alfa_o
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default="_hiz")
    ap.add_argument("--cihaz-isci", default="1")
    ap.add_argument("--cift", type=int, default=3, help="kosu tahmini icin cift sayisi")
    ap.add_argument("--edisyon", type=int, default=2, help="kosu tahmini icin edisyon sayisi")
    a = ap.parse_args()
    kok = Path(a.kok)
    if not (kok / f"{ED.upper()}_24X32.png").exists():
        t = time.time(); sentetik(kok); print(f"sentetik girdi: {round(time.time() - t, 1)}s", flush=True)
    sonuc = []
    for isci in [int(x) for x in a.cihaz_isci.split(",")]:
        for hale in (True, False):
            s = olc(kok, kok / f"out_{isci}_{int(hale)}", isci, hale)
            n, m = a.cift, a.edisyon
            # 1. asama: okuma+murekkep+kutular her (cift,edisyon); 2. asama: okuma+murekkep+uret
            asama1 = n * m * (s["okuma_2_dosya"] + s.get("murekkep_olcum", s["murekkep"])
                              + s["kutular_olc"])
            asama2 = n * m * (s["okuma_2_dosya"] + s["murekkep"] + s["uret_3_cihaz"])
            s["tahmin_kosu_dk"] = round((asama1 + asama2) / 60, 1)
            s["tahmin_asama1_dk"] = round(asama1 / 60, 1)
            s["tahmin_asama2_dk"] = round(asama2 / 60, 1)
            print(json.dumps(s), flush=True)
            sonuc.append(s)
    (kok / "HIZ_OLCUM.json").write_text(json.dumps(sonuc, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
