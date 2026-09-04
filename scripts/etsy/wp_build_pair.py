#!/usr/bin/env python3
"""
wp-build-pair: bir ciftin 16 wallpaper'i (4 edisyon x 4 cihaz) = temiz plaka
(PLATE_<ED>_<DEV>.png) + posterden MUREKKEP AKTARIMI.

Maske (Mo, 3 Eyl duzeltmesi; parlaklikla degil FARKLA):
  m = maks kanal |poster - MEDIAN_<ED>| > 12
      -> eleman kutulari (sembol / glifler / isimler, ∞ dahil), halka bandi disi
      -> morfolojik kapama 9 px -> kucuk benek filtresi (< 750 px^2, gren)
      -> delik doldurma (binary_fill_holes; yalniz <= HOLE_MAX px^2 delikler:
         strok ici gozenekler dolar, harf ici bosluklar plaka kalir)
      -> dilate 2 px -> 2 px feather (mesafe rampasi)
  Maske icinde posterin RGB'si AYNEN aktarilir (agirlik/ton yok); disinda plaka.
  MB/DB isima: maske disinda, murekkep alfasinin Gauss'u ile (poster - MEDIAN).
  Halka, tagline plakadan (pilot). ∞ posterden gelir (plaka CLEAN_INFINITY ile temiz).
Poster ve maske olculen afin yerlesimle (wp_plate_pilot.PLACEMENT + GEOM sidecar)
cihaz olcegine INTER_AREA ile indirilir.

QC kapisi (her dosya):
  1) aktarim (JPEG oncesi): cekirdek (alfa=1, 1 px asindirilmis) icinde |cikti - poster|
     ort 0, maks 0; plakaya posterden daha yakin piksel 0 (delik yok).
  2) JPEG turu (geri okuma): |cikti - poster| ort <= 1.15 x posterin kendi q95 turu,
     maks <= referans + 4. (Mo'nun "ort<2, maks<8" esigi JPEG q95'te dogal olarak
     asilir: olcum ARIES_LEO Phone MB ort 3.2/maks 20 = posterin kendi turuyla ayni;
     EK KURAL geregi esik olculen dogal referansa gore yeniden tanimlandi.)
  3) tuval boyutu.
Cikti: AstroLove_<Pair>_<Edition>_<Device>.jpg (16), CONTACT_<PAIR>.jpg,
qc/CROP_*.png (sembol 1:1 kesit: poster | cikti | plaka), build_<pair>.json.
--compare <pilot dir>: Cancer_Libra icin FINAL_V2 ile kiyas (bilgi; kapi degil).
"""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage

from wp_mockup_common import DEVICES, EDITIONS, imread, imwrite_jpeg, log
from wp_plate_pilot import (BOX_NAMES, BOX_SYMBOL, ELEMENT_BOXES, INK_RGB, RING_BAND, RING_ELLIPSE, RING_LINE_PX,
                            RING_TIP_Y, placement)

DIFF_THR = 12        # maks kanal |poster - medyan|
DIFF_HI = 60         # murekkep renginde olmayan fark pikseli icin esik (parlama/golge kalir, zemin sapmasi atilir)
CLOSE_PX = 9
MIN_COMP = 750       # poster px^2 (ink_layer_mask ile ayni gren filtresi)
INK_TOL = 70         # murekkep rengine uzaklik (ink_layer_mask ile ayni); bilesende en az INK_MIN murekkep renkli piksel
INK_MIN = 50         # yoksa bilesen zemin lekesi (bulut/yanik doku medyandan >12 sapiyor), atilir
INK_HALO = 0         # poster px: >0 ise fark maskesi murekkep renkli piksellerin bu komsulugunda gecerli (0 = kapali;
                     # 6 px denemesi strok icindeki parlama bandini kesti, olcum ARIES_LEO MB Phone)
HOLE_MAX = 2500      # poster px^2: bundan buyuk delikler (harf ici bosluk) doldurulmaz
DILATE_PX = 2
FEATHER_PX = 2
GLOW_EDITIONS = ("Midnight_Blue", "Deep_Black")
# 4 Eyl 2026 (Mo): sembol dibindeki hale saat ekraninda kabul edilmiyor; glow
# yalniz buyuk cihazlarda uygulanir (olcum: Watch MB hale 0-5 = 5.03, plaka 2.77).
GLOW_DEVICES = ("Phone", "Tablet", "Desktop")
GLOW_DILATE = 20     # poster px (olcum: halo ~5 px cihaz olcegi ~ 25 poster px)
GLOW_SOFT = 6.0
QC_JPEG_RATIO = 1.15  # JPEG turu hatasi / posterin kendi JPEG turu hatasi (dogal referans)
CONTACT_W = 300
CROP = 600


def region_mask(shape):
    """Eleman kutulari, halka bandi (elips, cizgi + 2*5*RING_BAND) disi. ∞ dahil."""
    boxes = np.zeros(shape[:2], np.uint8)
    for (x0, y0, x1, y1) in ELEMENT_BOXES:
        boxes[y0:y1 + 1, x0:x1 + 1] = 1
    ring = np.zeros_like(boxes)
    cx, cy, ax, ay = RING_ELLIPSE
    cv2.ellipse(ring, (int(cx), int(cy)), (int(ax), int(ay)), 0, 0, 360, 1, int(RING_LINE_PX) + 2 * 5 * RING_BAND, cv2.LINE_8)
    ring[RING_TIP_Y + 1:, :] = 0
    return (boxes & (ring == 0)).astype(np.uint8)


def diff_ink_mask(poster, median, ed):
    d = np.abs(poster.astype(np.int16) - median.astype(np.int16)).max(axis=2)
    raw = (d > DIFF_THR)
    m = (raw & (region_mask(poster.shape) > 0)).astype(np.uint8)
    # Fark maskesi murekkep KOMSULUGU ile sinirlanir (EK KURAL, olcum ARIES_LEO MB/WP Phone):
    # posterin bulut/yanik zemin dokusu medyandan >12 sapiyor (MB 1.8M px, WP 5.9M px), stroka
    # bitisik koyu zemin parcalari 1:1 kesitte gorunuyordu. Murekkep renkli fark pikseli
    # (INK_RGB'ye uzaklik < INK_TOL) + INK_HALO px komsulugu disindaki fark atilir; kabartma
    # kenar parlamasi/golgesi (olcum 5 px) komsulukta kalir.
    ys, xs = np.nonzero(m)
    r, g, b = INK_RGB[ed]
    d2 = ((poster[ys, xs].astype(np.int16) - np.array([b, g, r], np.int16)) ** 2).sum(axis=1)
    sel = d2 < INK_TOL * INK_TOL
    inkc = np.zeros(m.shape, np.uint8); inkc[ys[sel], xs[sel]] = 1
    # Murekkep renginde OLMAYAN fark pikseli yalniz fark > DIFF_HI ise kalir: strok parlamasi/golgesi
    # (olcum ARIES_LEO, temiz medyan: murekkepten 8-30 px uzak parlama pikselleri fark p10 127-158)
    # kalir; zemin bulut/doku sapmasi (fark 12-40) ve isima (MB/DB, Gauss terimiyle eklenir) atilir.
    strong = sel | (d[ys, xs] > DIFF_HI)
    m[ys[~strong], xs[~strong]] = 0
    del d
    if INK_HALO > 0:
        halo = cv2.dilate(inkc, np.ones((2 * INK_HALO + 1, 2 * INK_HALO + 1), np.uint8))
        m = (m & halo).astype(np.uint8)
        del halo
    del d2, ys, xs, sel
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((CLOSE_PX, CLOSE_PX), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    small = np.zeros(n, bool); small[1:] = st[1:, cv2.CC_STAT_AREA] < MIN_COMP
    # zemin lekeleri: medyandan >12 sapan ama murekkep rengi icermeyen bilesenler (olcum: MB bulut,
    # WP yanik doku; ARIES_LEO Phone'da sembol icinde koyu/acik parcalar) atilir
    ys, xs = np.nonzero(m)
    r, g, b = INK_RGB[ed]
    pix = poster[ys, xs].astype(np.int16)
    d2 = ((pix - np.array([b, g, r], np.int16)) ** 2).sum(axis=1)
    ink_cnt = np.bincount(lab[ys, xs][d2 < INK_TOL * INK_TOL], minlength=n)
    drop = small | (ink_cnt < INK_MIN); drop[0] = False
    n_drop = int(drop[1:].sum())
    m = (m & ~drop[lab]).astype(np.uint8)
    filled = ndimage.binary_fill_holes(m > 0)
    holes = (filled & (m == 0)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(holes)
    fill = np.zeros(n, bool); fill[1:] = st[1:, cv2.CC_STAT_AREA] <= HOLE_MAX
    core = (m | fill[lab]).astype(np.uint8)
    k = 2 * DILATE_PX + 1
    dil = cv2.dilate(core, np.ones((k, k), np.uint8))
    dist = cv2.distanceTransform(dil, cv2.DIST_L2, 3)
    alpha = np.clip(dist / (FEATHER_PX + 1.0), 0, 1).astype(np.float32)
    far = cv2.distanceTransform((cv2.dilate(inkc, np.ones((3, 3), np.uint8)) == 0).astype(np.uint8), cv2.DIST_L2, 3) > 15
    leak = int(((core > 0) & (inkc == 0) & far).sum())     # zemin sizintisi: murekkep renginden > 15 px uzak cekirdek pikseli
    del far, inkc
    stats = dict(diff_px=int(raw.sum()), core_px=int(core.sum()), comps_dropped=n_drop, leak_px=leak, holes_filled=int(fill[1:].sum()),
                 holes_kept=int((~fill[1:]).sum()), holes_kept_max_px=int(st[1:, cv2.CC_STAT_AREA][~fill[1:]].max()) if (~fill[1:]).any() else 0)
    return alpha, core, stats


def load_geom(plates, ed, dev):
    """Plakanin bant kirpma geometrisi (GEOM_<ED>_<DEV>.json); yoksa birim."""
    f = Path(plates) / f"GEOM_{ed.upper()}_{dev.upper()}.json"
    if f.exists():
        return json.loads(f.read_text())
    return dict(crop_top=0, crop_bot=0, scale_y=1.0)


def place(src, dev, canvas_shape, geom=None):
    """Poster olcegindeki (7200x9600) goruntuyu cihaz olcegine indirip tuvale yerlestirir (disi 0).
    geom: plakanin bant kirpma geometrisi -> ayni dikey carpan (scale_y) ve kaydirma uygulanir."""
    s, (w, h), x0, y0 = placement(dev)
    sy = float(geom["scale_y"]) if geom else 1.0
    if geom and sy != 1.0:
        y0 = (y0 - geom["crop_top"]) * sy
        h = int(round(h * sy))
    small = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA)
    H, W = canvas_shape[:2]
    out = np.zeros((H, W) + src.shape[2:], np.float32)
    x0i, y0i = int(round(x0)), int(round(y0))
    ys0, ys1 = max(0, y0i), min(H, y0i + h); xs0, xs1 = max(0, x0i), min(W, x0i + w)
    out[ys0:ys1, xs0:xs1] = small[ys0 - y0i:ys1 - y0i, xs0 - x0i:xs1 - x0i]
    return out


def symbol_center(core_c, dev, geom):
    """Sembol kutusundaki cekirdegin agirlik merkezi (tuval px)."""
    s, _, x0, y0 = placement(dev)
    sy = float(geom["scale_y"]) if geom else 1.0
    if geom and sy != 1.0:
        y0 = (y0 - geom["crop_top"]) * sy
    bx0, by0, bx1, by1 = BOX_SYMBOL
    H, W = core_c.shape
    cx0, cy0 = max(0, int(bx0 * s + x0)), max(0, int(by0 * s * sy + y0)); cx1, cy1 = min(W, int(bx1 * s + x0)), min(H, int(by1 * s * sy + y0))
    sub = core_c[cy0:cy1, cx0:cx1] > 0.5
    if not sub.any():
        return W // 2, H // 2
    ys, xs = np.nonzero(sub)
    return int(xs.mean()) + cx0, int(ys.mean()) + cy0


def names_center(dev, geom, shape):
    s, _, x0, y0 = placement(dev)
    sy = float(geom["scale_y"]) if geom else 1.0
    if geom and sy != 1.0:
        y0 = (y0 - geom["crop_top"]) * sy
    bx0, by0, bx1, by1 = BOX_NAMES
    return int((bx0 + bx1) / 2 * s + x0), int((by0 + by1) / 2 * s * sy + y0)


def crop_at(img, cx, cy, size=CROP):
    H, W = img.shape[:2]
    x0 = min(max(0, cx - size // 2), max(0, W - size)); y0 = min(max(0, cy - size // 2), max(0, H - size))
    c = img[y0:y0 + size, x0:x0 + size]
    pad = np.zeros((size, size, 3), np.uint8); pad[:c.shape[0], :c.shape[1]] = c
    return pad


def build_edition(pair, ed, plates, poster_path, median_path, out_dir, devices, compare_dir=None, crops=()):
    poster = imread(poster_path)
    if poster.shape[1] != 7200 or poster.shape[0] != 9600:
        raise SystemExit(f"HATA: poster {poster.shape[1]}x{poster.shape[0]}")
    median = imread(median_path)
    alpha, core, mstats = diff_ink_mask(poster, median, ed)
    log(f"  {ed}: fark>{DIFF_THR} {mstats['diff_px']} px, cekirdek {mstats['core_px']} px, zemin lekesi atildi {mstats['comps_dropped']}, sizinti {mstats['leak_px']} px, delik dolduruldu {mstats['holes_filled']}, "
        f"birakildi {mstats['holes_kept']} (en buyuk {mstats['holes_kept_max_px']} px)")
    glow_w = diff = None
    if ed in GLOW_EDITIONS:
        k = 2 * GLOW_DILATE + 1
        glow_w = cv2.GaussianBlur(cv2.dilate(core, np.ones((k, k), np.uint8)).astype(np.float32), (0, 0), GLOW_SOFT)
        diff = poster.astype(np.float32) - median.astype(np.float32)
    del median
    core_f = core.astype(np.float32)
    results = {}
    for dev in devices:
        plate = imread(plates / f"PLATE_{ed.upper()}_{dev.upper()}.png")
        W, H = DEVICES[dev]
        if plate.shape[1] != W or plate.shape[0] != H:
            raise SystemExit(f"HATA: plaka {dev} {plate.shape[1]}x{plate.shape[0]}")
        geom = load_geom(plates, ed, dev)
        P = place(poster.astype(np.float32), dev, plate.shape, geom)
        A = place(alpha, dev, plate.shape, geom)[..., None]
        base = plate.astype(np.float32)
        if glow_w is not None and dev in GLOW_DEVICES:
            base = base + place(glow_w, dev, plate.shape, geom)[..., None] * place(diff, dev, plate.shape, geom)
        outp = np.clip(np.round(A * P + (1.0 - A) * base), 0, 255).astype(np.uint8)
        name = f"AstroLove_{pair}_{ed}_{dev}.jpg"
        imwrite_jpeg(out_dir / name, outp)
        # ---- QC (geri okuma)
        back = imread(out_dir / name)
        core_c = place(core_f, dev, plate.shape, geom)
        # cekirdek = alfa tam 1 olan tuval pikselleri (1 px asindirilmis): burada cikti == poster birebir
        corem = cv2.erode((A[..., 0] >= 0.9999).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        Pu = np.clip(np.round(P), 0, 255).astype(np.uint8)
        dP = np.abs(back.astype(np.int16) - Pu.astype(np.int16)).max(axis=2)
        dL = np.abs(back.astype(np.int16) - plate.astype(np.int16)).max(axis=2)
        n_core = int(corem.sum())
        # 1) aktarim (JPEG oncesi): cekirdekte cikti == poster birebir, plakaya daha yakin piksel 0
        d0 = np.abs(outp.astype(np.int16) - Pu.astype(np.int16)).max(axis=2)
        dL0 = np.abs(outp.astype(np.int16) - plate.astype(np.int16)).max(axis=2)
        t_mean = float(d0[corem].mean()) if n_core else 0.0; t_max = int(d0[corem].max()) if n_core else 0
        plate_like = int(((dL0 < d0) & corem).sum())
        # 2) JPEG turu: |geri okunan - poster| posterin KENDI q95 turuyla ayni duzeyde (dogal referans)
        (out_dir / "qc").mkdir(exist_ok=True)
        imwrite_jpeg(out_dir / "qc" / "_ref.jpg", Pu); ref_b = imread(out_dir / "qc" / "_ref.jpg")
        dR = np.abs(ref_b.astype(np.int16) - Pu.astype(np.int16)).max(axis=2)
        q_mean = float(dP[corem].mean()) if n_core else 0.0; q_max = int(dP[corem].max()) if n_core else 0
        r_mean = float(dR[corem].mean()) if n_core else 0.0; r_max = int(dR[corem].max()) if n_core else 0
        jpeg_ok = q_mean <= r_mean * QC_JPEG_RATIO + 0.1 and q_max <= r_max + 4
        size_ok = back.shape[1] == W and back.shape[0] == H
        # yuvarlama siniri (x.5) tek tek piksellerde 1 seviye oynatabilir: ort < 0.01, maks <= 1
        ok = bool(size_ok and n_core > 0 and t_mean < 0.01 and t_max <= 1 and plate_like == 0 and jpeg_ok)
        info = dict(file=name, geom=geom, core_px=n_core, transfer_mean=t_mean, transfer_max=t_max, plate_like_px=plate_like,
                    jpeg_mean=round(q_mean, 3), jpeg_max=q_max, jpeg_ref_mean=round(r_mean, 3), jpeg_ref_max=r_max,
                    jpeg_ok=bool(jpeg_ok), size_ok=size_ok, ok=ok)
        if compare_dir is not None:
            ref = imread(Path(compare_dir) / name)
            if geom["scale_y"] != 1.0:                       # pilotu ayni geometriye getir
                ref = cv2.resize(ref[geom["crop_top"]:ref.shape[0] - geom["crop_bot"]], (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_LANCZOS4)
            d = np.abs(back.astype(np.int16) - ref.astype(np.int16)).max(axis=2)
            info.update(cmp_ink_mean=float(d[corem].mean()) if n_core else 0.0, cmp_outside_mean=float(d[~corem].mean()))
        if (ed, dev) in crops or "all" in crops:
            cx, cy = symbol_center(core_c, dev, geom)
            pts = [("SYM", cx, cy)]
            if dev != "Watch":
                nx, ny = names_center(dev, geom, plate.shape)
                if 0 <= ny < H:
                    pts.append(("NAMES", nx, ny))
            for tag, px, py in pts:
                sheet = np.hstack([crop_at(Pu, px, py), crop_at(back, px, py), crop_at(plate, px, py)])
                for i, t in enumerate(("poster", "cikti", "plaka")):
                    cv2.putText(sheet, t, (i * CROP + 8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.imwrite(str(out_dir / "qc" / f"CROP_{pair.upper()}_{ed.upper()}_{dev.upper()}_{tag}.png"), sheet)
        results[dev] = info
        log(f"  {ed} {dev:8s} -> {name} | cekirdek {n_core} px | aktarim ort {t_mean:.2f} maks {t_max}, plaka renkli {plate_like} | "
            f"JPEG ort {q_mean:.2f} maks {q_max} (ref {r_mean:.2f}/{r_max}) -> {'PASS' if ok else 'FAIL'}"
            + (f" | pilot kiyas: murekkep ort {info['cmp_ink_mean']:.2f}, disi ort {info['cmp_outside_mean']:.2f}" if compare_dir else ""))
    return results, mstats


def contact_sheet(pair, in_dir, out_path, editions=EDITIONS, devices=("Phone", "Tablet", "Desktop", "Watch")):
    tiles = []
    for ed in editions:
        row = []
        for dev in devices:
            f = Path(in_dir) / f"AstroLove_{pair}_{ed}_{dev}.jpg"
            W, H = DEVICES[dev]
            th = int(CONTACT_W * H / W)
            cell = np.full((420, CONTACT_W, 3), 40, np.uint8)
            if f.exists():
                im = imread(f)
                t = cv2.resize(im, (CONTACT_W, th), interpolation=cv2.INTER_AREA)
                if th > 400:
                    t = t[:400]
                cell[:t.shape[0], :] = t
                cv2.putText(cell, f"{ed[:2]} {dev}", (6, 415), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            else:
                cv2.putText(cell, f"{ed[:2]} {dev} YOK", (6, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
            row.append(cell)
        tiles.append(np.hstack(row))
    sheet = np.vstack(tiles)
    cv2.putText(sheet, f"{pair}  16 wallpaper", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.imwrite(str(out_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])


def parse_crops(s):
    out = set()
    for tok in [t for t in s.split(",") if t]:
        if tok == "all":
            out.add("all"); continue
        ed, dev = tok.rsplit("_", 1)
        out.add((ed, dev))
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--pair", required=True, help="Aries_Leo")
    b.add_argument("--plates", required=True)
    b.add_argument("--posters", required=True, help="WA_POSTER_<PAIR>_<ED>_3X4.jpg dosyalari")
    b.add_argument("--medians", required=True, help="MEDIAN_<ED>.png dosyalari")
    b.add_argument("--out", required=True)
    b.add_argument("--editions", default=",".join(EDITIONS))
    b.add_argument("--devices", default="Phone,Tablet,Desktop,Watch")
    b.add_argument("--compare", default="", help="pilot dizini (ayni cift): FINAL_V2 ile kiyas")
    b.add_argument("--crops", default="Deep_Black_Tablet,Champagne_Ivory_Phone", help="1:1 sembol kesitleri (<Ed>_<Dev>,... | all)")
    c = sub.add_parser("contact")
    c.add_argument("--pair", required=True)
    c.add_argument("--dir", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "contact":
        contact_sheet(a.pair, a.dir, a.out)
        log(f"kontak sayfasi: {a.out}")
        return
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    eds = [e for e in a.editions.split(",") if e]
    devs = [d for d in a.devices.split(",") if d]
    crops = parse_crops(a.crops)
    t0 = time.time(); rep = {}; masks = {}; all_ok = True
    for i, ed in enumerate(eds):
        poster = Path(a.posters) / f"WA_POSTER_{a.pair.upper()}_{ed.upper()}_3X4.jpg"
        median = Path(a.medians) / f"MEDIAN_{ed.upper()}.png"
        if not poster.exists() or not median.exists():
            raise SystemExit(f"HATA: eksik girdi {poster if not poster.exists() else median}")
        rep[ed], masks[ed] = build_edition(a.pair, ed, Path(a.plates), poster, median, out, devs, a.compare or None, crops)
        all_ok &= all(v["ok"] for v in rep[ed].values())
        el = time.time() - t0
        log(f"edisyon {i + 1}/{len(eds)}  gecen {el:4.0f}s  kalan {el / (i + 1) * (len(eds) - i - 1):4.0f}s  %{100 * (i + 1) / len(eds):.0f}")
    n_files = sum(len(v) for v in rep.values()); n_pass = sum(1 for v in rep.values() for r in v.values() if r["ok"])
    (out / f"build_{a.pair}.json").write_text(json.dumps(dict(pair=a.pair, ok=all_ok, files=n_files, passed=n_pass, masks=masks, editions=rep), indent=1))
    if len(eds) == len(EDITIONS) and len(devs) == 4:
        contact_sheet(a.pair, out, out / f"CONTACT_{a.pair.upper()}.jpg")
    log(f"SONUC {a.pair}: {'PASS' if all_ok else 'FAIL'} {n_pass}/{n_files} | toplam {time.time() - t0:.0f}s")
    if not all_ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
