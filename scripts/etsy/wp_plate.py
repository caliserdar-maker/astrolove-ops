#!/usr/bin/env python3
"""
wp-plate: edisyon basina TEK temiz zemin plakasi (7200x9600, cift-bagimsiz).
"Temiz plaka" yontemi (Mo, 2 Eyl): posterin gercek kagit/gokyuzu dokusu,
murekkepsiz, vinyeti dahil. Sonra her cihaz plakayi COVER ile kirpar,
murekkep katmani afin yerlesimle ustune gelir (wp_build_plate.py).

Plaka nasil cikarilir (olculen gercek: ayni edisyonun posterleri AYNI zemini
tasir, fark 0.00-0.19/255; yalniz murekkep degisir):
  1) CIFTE OZEL murekkep (sembol, glif, isimler): N cift posterinden piksel
     basina 2. en dusuk (koyu edisyon) / 2. en yuksek (acik edisyon) lumali
     ornek alinir -> o pikselde en az N-1 posterde zemin olan GERCEK doku.
     Inpaint gerekmez.
  2) SABIT murekkep (halka yayi, "∞", tagline satirlari; her posterde ayni
     yerde): maske DB zemininden (saf siyah uzerinde tek murekkep, luma>40,
     9 px genisletme); bu bolge PATCH TABANLI inpaint (OpenCV xphoto
     SHIFTMAP; blur yok) ile cevre dokusundan doldurulur.
  3) Guvenlik: V2 yuksek gecirgen + Otsu murekkep maskesi plakada yeniden
     kosulur; kalan murekkep pikseli sayilir (0 beklenir).
QC:
  - Hayalet olcumu: eski murekkep bolgelerinde yuksek frekans enerjisi
    (luma - Gauss s=4, std) cevre halkasina orani (1.0 = ayirt edilemez).
  - Kesit sayfasi: kucultulmus tam plaka + 3 bolgenin 600x600 1:1 kesiti
    (fuzyon merkezi, halka yayi, tagline satiri).
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from wp_mockup_common import EDITIONS, imread, log

PW, PH = 7200, 9600
ED_UP = {e: e.upper() for e in EDITIONS}
DARK = {"Midnight_Blue", "Deep_Black"}
# QC kesit merkezleri (poster px): fuzyon merkezi, halka sol yayi, tagline satiri
QC_CENTERS = [("fuzyon", 3600, 3300), ("halka", 1100, 3000), ("tagline", 3600, 7200)]


def poster_name(pair, ed):
    return f"WA_POSTER_{pair.upper()}_{ED_UP[ed]}_3X4.jpg"


def luma_u8(bgr):
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def order_bg(posters, dark, rows=400):
    """Piksel basina 2. sira istatistigi (satir parcalariyla, bellek dostu)."""
    out = np.empty_like(posters[0])
    L = [luma_u8(p) for p in posters]
    for y in range(0, PH, rows):
        ls = np.stack([l[y:y + rows] for l in L])                      # N x r x W
        order = np.argsort(ls, axis=0, kind="stable")
        pick = order[1] if dark else order[-2]
        stack = np.stack([p[y:y + rows] for p in posters])              # N x r x W x 3
        out[y:y + rows] = np.take_along_axis(stack, pick[None, ..., None], axis=0)[0]
    return out


def const_mask(bg_db, dil=24):
    m = (luma_u8(bg_db) > 40).astype(np.uint8)
    return cv2.dilate(m, np.ones((2 * dil + 1, 2 * dil + 1), np.uint8))


def inpaint_shiftmap(img, mask_u8, pad=160, max_side=2600):
    """Patch tabanli inpaint (xphoto SHIFTMAP), maske bilesenlerinin ROI'lerinde
    (tam 7200x9600'de SHIFTMAP cokuyor). Buyuk ROI'ler (halka) max_side'lik
    parcalara bolunur; parcalar 'pad' kadar ortusur, sonuc yalniz parca
    icinde yazilir (ortusme dolgu icin baglam saglar)."""
    m = (mask_u8 > 0).astype(np.uint8)
    out = img.copy()
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    H, W = m.shape
    for i in range(1, n):
        x, y, w, h, a = st[i]
        for ty in range(y, y + h, max_side):
            for tx in range(x, x + w, max_side):
                x0, y0 = max(0, tx - pad), max(0, ty - pad)
                x1, y1 = min(W, min(tx + max_side, x + w) + pad), min(H, min(ty + max_side, y + h) + pad)
                sub_m = (lab[y0:y1, x0:x1] == i).astype(np.uint8)
                if not sub_m.any():
                    continue
                crop = out[y0:y1, x0:x1].copy()
                res = np.zeros_like(crop)
                cv2.xphoto.inpaint(crop, 255 - sub_m * 255, res, cv2.xphoto.INPAINT_SHIFTMAP)
                iy0, ix0 = ty - y0, tx - x0
                iy1, ix1 = min(ty + max_side, y + h) - y0, min(tx + max_side, x + w) - x0
                sel = sub_m[iy0:iy1, ix0:ix1] > 0
                out[y0 + iy0:y0 + iy1, x0 + ix0:x0 + ix1][sel] = res[iy0:iy1, ix0:ix1][sel]
    return out


def fill_shift_lowpass(img, mask_u8, k=300, sigma=25.0):
    """Koyu, neredeyse duz zeminler (MB gece gradyani, DB siyah) icin dolgu:
    maske pikselleri ayni goruntunun k px kaydirilmis maske-disi kopyasindan
    alinir (SHIFTMAP gibi yama sinirlari ve maske disindan altin kopyalama
    olmaz), sonra yavas gradyan farki alcak gecirgen duzeltmeyle kapatilir."""
    m = mask_u8 > 0
    out = img.astype(np.float32).copy()
    todo = m.copy()
    for dx, dy in ((0, k), (0, -k), (k, 0), (-k, 0), (k, k), (-k, -k), (0, 2 * k), (0, -2 * k), (2 * k, 0), (-2 * k, 0)):
        if not todo.any():
            break
        src = np.roll(np.roll(img, dy, axis=0), dx, axis=1)
        srcm = np.roll(np.roll(m, dy, axis=0), dx, axis=1)
        ok = todo & ~srcm
        out[ok] = src[ok]
        todo &= ~ok
    if todo.any():
        out[todo] = cv2.blur(out, (51, 51))[todo]
    wgt = (~m).astype(np.float32)
    den = cv2.GaussianBlur(wgt, (0, 0), sigma)[..., None]
    corr = cv2.GaussianBlur((img.astype(np.float32) - out) * wgt[..., None], (0, 0), sigma) / np.maximum(den, 1e-3)
    out = out + corr * m[..., None]
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


INK_RGB = {"Champagne_Ivory": (95, 59, 29), "Warm_Parchment": (139, 81, 25), "Midnight_Blue": (244, 184, 63), "Deep_Black": (244, 183, 62)}


def residual_ink_mask(plate, ed, near_mask, tol=30, dil=6):
    """Ikinci gecis: bilinen murekkep rengine (WP_LAYOUT_SPEC 7.1) yakin
    pikseller, yalniz bilinen murekkep bolgelerinin (sabit + cift) 10 px
    komsulugunda. Kagit dokusunun koyu benekleri (WP) bu bolge disinda kalir."""
    r, g, b = INK_RGB[ed]
    d = np.sqrt(((plate.astype(np.float32) - np.array([b, g, r], np.float32)) ** 2).sum(axis=2))
    m = ((d < tol) & (near_mask > 0)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    return cv2.dilate(m, np.ones((2 * dil + 1, 2 * dil + 1), np.uint8))


def v2_ink_mask(bgr):
    """V2 olcum yontemi: yuksek gecirgen (gri - 1/8 medyan zemin) + Otsu (12-90)."""
    g = luma_u8(bgr).astype(np.float32)
    h, w = g.shape
    small = cv2.resize(g, (w // 8, h // 8), interpolation=cv2.INTER_AREA)
    k = max(5, (int(min(small.shape) * 0.09) // 2) * 2 + 1)
    bg = cv2.medianBlur(np.clip(small, 0, 255).astype(np.uint8), k).astype(np.float32)
    bg = cv2.resize(bg, (w, h), interpolation=cv2.INTER_LINEAR)
    paper = float(np.median(g[h // 4:3 * h // 4, w // 4:3 * w // 4]))
    d = np.clip((bg - g) if paper > 128 else (g - bg), 0, 255).astype(np.uint8)
    sel = d[d > 2]
    t, _ = cv2.threshold(sel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU) if sel.size else (12, None)
    t = int(min(max(t, 12), 90))
    m = (d > t).astype(np.uint8)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)), t


def hf_energy_ratio(plate, mask_u8, sigma=4.0, ring=(12, 60)):
    """Eski murekkep bolgesi (mask) ile cevre halkasinin yuksek frekans std orani."""
    g = luma_u8(plate).astype(np.float32)
    hp = g - cv2.GaussianBlur(g, (0, 0), sigma)
    inner = mask_u8 > 0
    d1 = cv2.dilate(mask_u8, np.ones((2 * ring[0] + 1, 2 * ring[0] + 1), np.uint8)) > 0
    d2 = cv2.dilate(mask_u8, np.ones((2 * ring[1] + 1, 2 * ring[1] + 1), np.uint8)) > 0
    outer = d2 & ~d1
    si, so = float(hp[inner].std()), float(hp[outer].std())
    return si, so, (si / so if so > 0 else float("nan"))


def qc_sheet(plate, path, side=600):
    small = cv2.resize(plate, (side, int(side * PH / PW)), interpolation=cv2.INTER_AREA)
    tiles = [np.full((800, side, 3), 40, np.uint8)]
    tiles[0][:small.shape[0]] = small
    for name, cx, cy in QC_CENTERS:
        x0, y0 = cx - side // 2, cy - side // 2
        t = plate[y0:y0 + side, x0:x0 + side].copy()
        canvas = np.full((800, side, 3), 40, np.uint8)
        canvas[100:700] = t
        cv2.putText(canvas, f"{name} 1:1 @({cx},{cy})", (8, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(canvas)
    cv2.imwrite(str(path), np.hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 92])


INTERIOR = (900, 1000, 6300, 9000)   # acik edisyonlarda vinyet kenari disinda kalan ic bolge (poster px)


def sweep_plate(plate, ed, tol=50, min_area=40, rounds=3):
    """Son suzgec: plakada kalan murekkep rengi bilesenleri (>= min_area px)
    kaydirmali kopya + alcak gecirgen dolgu ile silinir (SHIFTMAP kullanilmaz:
    yama kaynagi olarak kalintiyi kopyalayabiliyor). Acik edisyonlarda yalniz
    ic bolge (vinyet kenari murekkep rengine yakin). Donus: plaka, kalan sayisi."""
    r, g, b = INK_RGB[ed]
    x0, y0, x1, y1 = INTERIOR
    for _ in range(rounds):
        if ed in DARK:
            m = (luma_u8(plate) > 90).astype(np.uint8)
        else:
            d = np.sqrt(((plate.astype(np.float32) - np.array([b, g, r], np.float32)) ** 2).sum(axis=2))
            m = (d < tol).astype(np.uint8)
            box = np.zeros_like(m); box[y0:y1, x0:x1] = 1; m &= box
        n, lab, st, _ = cv2.connectedComponentsWithStats(m)
        keep = np.zeros_like(m)
        cnt = 0
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] >= min_area:
                keep[lab == i] = 1; cnt += 1
        if cnt == 0:
            return plate, 0
        keep = cv2.dilate(keep, np.ones((17, 17), np.uint8))
        plate = fill_shift_lowpass(plate, keep)
    return plate, cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--posters", required=True)
    ap.add_argument("--pairs", required=True, help="zemin icin cift listesi (virgullu, >= 4)")
    ap.add_argument("--pilot-pair", default="Cancer_Libra")
    ap.add_argument("--editions", default=",".join(EDITIONS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--sweep-only", default="", help="mevcut plaka klasoru: yalniz son suzgec + QC sayfasi")
    a = ap.parse_args()
    if a.sweep_only:
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True); (out / "qc").mkdir(exist_ok=True)
        for ed in a.editions.split(","):
            plate = imread(Path(a.sweep_only) / f"WP_PLATE_{ED_UP[ed]}_3X4.png")
            plate, left = sweep_plate(plate, ed)
            cv2.imwrite(str(out / f"WP_PLATE_{ED_UP[ed]}_3X4.png"), plate, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            qc_sheet(plate, out / "qc" / f"PLATE_{ED_UP[ed]}.jpg")
            log(f"{ed:16s} suzgec sonrasi kalan bilesen: {left}")
        return
    pairs = a.pairs.split(",")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); (out / "qc").mkdir(exist_ok=True)
    # sabit murekkep maskesi: DB zemininden (tum edisyonlar ayni yerlesim)
    db = [imread(Path(a.posters) / poster_name(p, "Deep_Black")) for p in pairs]
    bg_db = order_bg(db, True)
    cmask = const_mask(bg_db)
    del db
    log(f"sabit murekkep maskesi: {int((cmask > 0).sum())} px ({(cmask > 0).mean() * 100:.2f}%)")
    report = {}
    for ed in a.editions.split(","):
        posters = [imread(Path(a.posters) / poster_name(p, ed)) for p in pairs]
        bg = order_bg(posters, ed in DARK)
        pilot = imread(Path(a.posters) / poster_name(a.pilot_pair, ed))
        # cifte ozel murekkep (pilot) maskesi: QC icin
        dl = np.abs(luma_u8(pilot).astype(np.int16) - luma_u8(bg).astype(np.int16))
        pair_ink = cv2.dilate((dl > 25).astype(np.uint8), np.ones((5, 5), np.uint8))
        pair_ink_union = np.zeros_like(pair_ink)
        for q in posters:
            dq = np.abs(luma_u8(q).astype(np.int16) - luma_u8(bg).astype(np.int16))
            pair_ink_union = np.maximum(pair_ink_union, (dq > 25).astype(np.uint8))
        del posters
        # edisyona ozel sabit maske: DB maskesinin 72 px komsulugunda, bu edisyonun
        # zemininde yerel medyandan >35 sapan pikseller (edisyonlar arasi yerlesim
        # kaymasi ve kenar yumusatma artigi; WP "T" serifi orn.) DB maskesine eklenir
        gb = luma_u8(bg)
        loc = (np.abs(gb.astype(np.int16) - cv2.medianBlur(gb, 31).astype(np.int16)) > 35).astype(np.uint8)
        loc &= cv2.dilate(cmask, np.ones((145, 145), np.uint8))
        cmask_ed = np.maximum(cmask, cv2.dilate(loc, np.ones((13, 13), np.uint8)))
        plate = fill_shift_lowpass(bg, cmask_ed) if ed in DARK else inpaint_shiftmap(bg, cmask_ed * 255)
        # ikinci gecis: kalan murekkep parcalari (renk + bolge kurali)
        # yalniz CI: koyu edisyonlarda (MB/DB) 2. gecis duz zeminde yama izi birakiyor
        # (HF orani 0.97 -> 6.8), WP'de parsomen lifleri murekkep rengine yakin (8% yanlis).
        res_px = 0
        if ed == "Champagne_Ivory":
            near = cv2.dilate(np.maximum(cmask, pair_ink_union), np.ones((21, 21), np.uint8))
            rmask = residual_ink_mask(plate, ed, near)
            res_px = int((rmask > 0).sum())
        elif ed in DARK:
            # koyu zeminde (maks luma ~46) luma > 90 yalniz altin murekkep kalintisidir
            # (SHIFTMAP maske disindaki altin parcalari yama olarak kopyalayabiliyor)
            rmask = cv2.dilate((luma_u8(plate) > 90).astype(np.uint8), np.ones((21, 21), np.uint8))
            res_px = int((rmask > 0).sum())
        else:  # WP: yalniz inpaint edilmis (sabit) bolge icinde: murekkep rengi VEYA yerel zeminden >40 koyu
            g = luma_u8(plate).astype(np.float32)
            dark = ((cv2.GaussianBlur(g, (0, 0), 25) - g) > 40).astype(np.uint8) & (cmask_ed > 0)
            dark = cv2.dilate(cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)), np.ones((13, 13), np.uint8))
            rmask = np.maximum(residual_ink_mask(plate, ed, cmask, tol=35), dark)
            res_px = int((rmask > 0).sum())
        if res_px:
            plate = fill_shift_lowpass(plate, rmask) if ed in DARK else inpaint_shiftmap(plate, rmask * 255)
        plate, left = sweep_plate(plate, ed)
        # guvenlik: V2 murekkep maskesi plakada
        v2m, t = v2_ink_mask(plate)
        v2_px = int(v2m.sum())
        v2_frac = float(v2m.mean())
        # hayalet olcumu
        si_c, so_c, r_c = hf_energy_ratio(plate, cmask_ed)
        si_p, so_p, r_p = hf_energy_ratio(plate, pair_ink)
        # plaka kenar/orta luma (vinyet kaydi)
        g = luma_u8(plate)
        vign = dict(center=float(g[PH // 2 - 200:PH // 2 + 200, PW // 2 - 200:PW // 2 + 200].mean()),
                    top=float(g[:200].mean()), bottom=float(g[-200:].mean()), left=float(g[:, :200].mean()), right=float(g[:, -200:].mean()))
        name = f"WP_PLATE_{ED_UP[ed]}_3X4.png"
        cv2.imwrite(str(out / name), plate, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        qc_sheet(plate, out / "qc" / f"PLATE_{ED_UP[ed]}.jpg")
        report[ed] = dict(file=name, sweep_left=left, const_ink_px=int((cmask_ed > 0).sum()), pair_ink_px=int((pair_ink > 0).sum()), residual_pass_px=res_px,
                          v2_residual_px=v2_px, v2_residual_frac=v2_frac, v2_otsu=t,
                          hf_const=dict(inner=si_c, outer=so_c, ratio=r_c), hf_pair=dict(inner=si_p, outer=so_p, ratio=r_p), vignette=vign)
        log(f"{ed:16s} 2.gecis {res_px} px | V2 kalinti {v2_px} px ({v2_frac * 100:.3f}%, otsu {t}) | HF orani sabit-murekkep {r_c:.3f} ({si_c:.2f}/{so_c:.2f}) "
            f"| cift-murekkep {r_p:.3f} ({si_p:.2f}/{so_p:.2f}) | luma merkez {vign['center']:.0f} kenarlar {vign['top']:.0f}/{vign['bottom']:.0f}/{vign['left']:.0f}/{vign['right']:.0f}")
    (out / "plates.json").write_text(json.dumps(dict(pairs=pairs, pilot=a.pilot_pair, editions=report), indent=1))
    cv2.imwrite(str(out / "const_mask_small.png"), cv2.resize(cmask * 255, (900, 1200), interpolation=cv2.INTER_AREA))


if __name__ == "__main__":
    main()
