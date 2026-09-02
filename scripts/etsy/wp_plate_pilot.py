#!/usr/bin/env python3
"""
wp-plate-pilot: 16 temiz plaka (edisyon x cihaz), referans = CANLI PILOT
wallpaper dosyalari (WALLPAPER/FINAL_V2/CANCER_LIBRA). Mo 2 Eyl yontemi:

1. Pilot dosyasi = taban. Murekkep maskesi pilotun kendisinden: murekkep
   rengine yakinlik (WP_LAYOUT_SPEC 7.1: CI 95,59,29 | WP 139,81,25 |
   MB 244,184,63 | DB 244,183,62) + luma Otsu (MB/DB'de parlak = murekkep),
   yalniz poster bolgesinde, + 16 px dilate. Maske disina DOKUNULMAZ.
2. Maske ici dolgu: OPTIMIZED 3X4 78 posterin piksel-medyani (cihaz
   olceginde: her poster bir kez okunur, 4 cihaz boyutuna INTER_AREA ile
   indirilir; medyan = uint8 partition, satir parcalariyla), olculen afin
   yerlesimle (Phone 0.2000 y+640; Tablet 0.2844 y+182; Desktop 0.2649
   x+966 y-193; Watch 0.2372 merkez (500,608)) pilot tuvaline hizalanir;
   YEREL ton eslestirme (maske cevresi 16-64 px halkasinin Gauss-agirlikli
   ort/std alanlari, sigma 32) + 24 px feather ile pilota harmanlanir.
   ISTISNA (medyanin kendi murekkebi): halka, ∞ ve tagline 78 posterde ayni
   yerde oldugu icin medyanda da vardir; bu piksellerde dolgu, medyanin
   kendi murekkepsiz dokusunun 48 px kaydirilmis kopyasindan alinir
   (inpaint/patch yok, ayni doku).
3. QC: (a) maske disi fark pilotla = 0 (birebir), (b) maske ici yuksek
   frekans (luma - Gauss s=4) std'si / cevre halkasi (hayalet/dikis),
   (c) 3 kesit 600x600 1:1 (halka, sembol merkezi, tagline) + kucultulmus
   tam plaka. ETA sayaci: poster okuma ilerlemesi.
"""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np

from wp_mockup_common import DEVICES, EDITIONS, imread, log

PLACEMENT = {
    "Phone": dict(s=0.2000, size=(1440, 1920), x0=0, y0=640),
    "Tablet": dict(s=0.2844, size=(2048, 2730), x0=0, y0=182),
    "Desktop": dict(s=0.2649, size=(1907, 2543), x0=966, y0=-193),
    "Watch": dict(s=0.2372, size=(1708, 2277), x0=None, y0=None),   # merkez kurali: poster (3600,3510) -> (500,608)
}
WATCH_SRC_CENTER = (3600.0, 3510.0)
WATCH_DST_CENTER = (500.0, 608.0)
INK_RGB = {"Champagne_Ivory": (95, 59, 29), "Warm_Parchment": (139, 81, 25), "Midnight_Blue": (244, 184, 63), "Deep_Black": (244, 183, 62)}
DARK = {"Midnight_Blue", "Deep_Black"}
# poster px referans kutulari (7.1): halka yayi, fuzyon merkezi, tagline satiri
REF_RING = (921, 1147, 6279, 4922)
REF_SYMBOL = (1934, 1939, 5261, 5081)
REF_TAGLINE = (1584, 7061, 5606, 7334)
# murekkebin bulunabilecegi yerlesim kutulari (poster px, WP_LAYOUT_SPEC 7.1): halka kutusu, isim/tagline satirlari
# Tek kutu: Cancer sembolunun ince kuyruklari poster y~5400-5800'e sarkiyor (kosu 5: iki kutu arasi
# boslukta kuyruk uclari kaldi). Kutu disindaki alan (kenar vinyeti) yine disarida.
LAYOUT_BOXES = [(800, 1000, 6400, 8600)]
HP_SIGMA = 16       # dolgu = medyanin yuksek frekans dokusu (sigma 16 ustu) + pilotun yerel tonu
DILATE_INK = 24     # maske = murekkep + 24 px
FEATHER = 22        # alfa: murekkep+2 px'te 1, maske sinirinda 0 (24 px'lik gecis maske ICINDE)
RING_IN, RING_OUT = 16, 64


def luma(bgr):
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def placement(dev):
    p = PLACEMENT[dev]
    if dev == "Watch":
        s = p["s"]
        return s, p["size"], WATCH_DST_CENTER[0] - s * WATCH_SRC_CENTER[0], WATCH_DST_CENTER[1] - s * WATCH_SRC_CENTER[1]
    return p["s"], p["size"], p["x0"], p["y0"]


def poster_to_canvas(dev, x, y):
    s, _, x0, y0 = placement(dev)
    return x * s + x0, y * s + y0


# ------------------------------------------------------------------ 78 poster medyani (cihaz olceginde)
def device_medians(poster_paths, log_every=5):
    sizes = {dev: PLACEMENT[dev]["size"] for dev in PLACEMENT}
    n = len(poster_paths)
    stacks = {dev: np.empty((n, sizes[dev][1], sizes[dev][0], 3), np.uint8) for dev in sizes}
    t0 = time.time()
    for i, p in enumerate(poster_paths):
        im = imread(p)
        if im.shape[1] != 7200 or im.shape[0] != 9600:
            raise SystemExit(f"HATA: {Path(p).name} {im.shape[1]}x{im.shape[0]} (7200x9600 degil)")
        for dev, (w, h) in sizes.items():
            stacks[dev][i] = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)
        if (i + 1) % log_every == 0 or i + 1 == n:
            el = time.time() - t0
            log(f"  poster {i + 1}/{n}  gecen {el:5.0f}s  kalan {el / (i + 1) * (n - i - 1):5.0f}s  %{100 * (i + 1) / n:.0f}")
    med = {}
    for dev, st in stacks.items():
        out = np.empty(st.shape[1:], np.uint8)
        rows = 256
        for y in range(0, st.shape[1], rows):
            part = np.partition(st[:, y:y + rows], (n // 2 - 1, n // 2), axis=0)
            a = part[n // 2 - 1].astype(np.uint16); b = part[n // 2].astype(np.uint16)
            out[y:y + rows] = ((a + b + 1) // 2).astype(np.uint8)
        med[dev] = out
        log(f"  medyan {dev}: {out.shape[1]}x{out.shape[0]}")
    del stacks
    return med


# ------------------------------------------------------------------ maskeler
def otsu_thresh(vals):
    vals = vals.astype(np.uint8)
    t, _ = cv2.threshold(vals, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return float(t)


def ink_mask_pilot(pilot, ed, dev, canvas_region, tex=None, tol=70, dloc=18):
    """Pilotun kendi murekkebi:
    cekirdek = murekkep rengine yakin (tol) + luma Otsu (MB/DB parlak, CI/WP koyu);
    uzanti   = yerel zeminden (medyan 51 px) >= dloc sapan pikseller (kenar
               yumusatma, altin parlama/golge, kabartma kenari), YALNIZ
               cekirdegin 24 px komsulugundaki bilesenler (doku benegi/lif
               ve yildizlar disarida; MB/DB'de ayrica altin ton sarti R-B>30).
    Poster bolgesine sinirli; kenara degen bloblar (vinyet) atilir."""
    r, g, b = INK_RGB[ed]
    Lu = luma(pilot)
    L = Lu.astype(np.float32)
    dist = np.sqrt(((pilot.astype(np.float32) - np.array([b, g, r], np.float32)) ** 2).sum(axis=2))
    reg = canvas_region > 0
    lay = np.zeros_like(canvas_region)
    for (bx0, by0, bx1, by1) in LAYOUT_BOXES:
        x0, y0 = poster_to_canvas(dev, bx0, by0); x1, y1 = poster_to_canvas(dev, bx1, by1)
        lay[max(0, int(y0)):int(y1) + 1, max(0, int(x0)):int(x1) + 1] = 1
    reg = reg & (lay > 0)                     # murekkep yalniz yerlesim kutularinda; vinyet/lif disarida
    t = otsu_thresh(Lu[canvas_region > 0])
    core = ((L > t) if ed in DARK else (L < t)) & (dist < tol) & reg
    bg = cv2.medianBlur(Lu, 51).astype(np.float32)
    d = L - bg
    thr = np.full(L.shape, float(dloc if ed in DARK else dloc * 2 / 3), np.float32)
    if tex is not None:
        # zeminin kendi dokusu yuksek kontrastliysa (WP yanik kenar kivrimlari) uzanti esigi
        # dokuyla olceklenir: doku murekkep sanilip medyanla degistirilmesin (kosu 5: WP halka dikisi)
        thr = np.maximum(thr, 2.5 * tex)
    if ed in DARK:
        ext = d > thr                     # parlama beyaza yakin (R-B kucuk): ton sarti YOK; yildizlar cekirdege uzak oldugu icin disarida
    else:
        ext = np.abs(d) > thr             # kabartma parlamasi soluk (12)
    ext &= reg
    cand = (ext | core).astype(np.uint8)
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    near_core = cv2.dilate(core.astype(np.uint8), np.ones((81, 81), np.uint8)) > 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(cand)
    keep = np.zeros_like(cand)
    border = (cv2.dilate(canvas_region, np.ones((3, 3), np.uint8)) - cv2.erode(canvas_region, np.ones((3, 3), np.uint8))) > 0
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 12:
            continue
        comp = lab == i
        if not (comp & near_core).any():
            continue
        if (comp & border).any():
            continue
        keep[comp] = 1
    keep |= core.astype(np.uint8)
    return keep, t


def ink_mask_median(med, ed, dloc=18, dlight=30):
    """Medyanin kendi murekkebi (halka, ∞, tagline; cifte ozel murekkep medyanda
    yok): yerel medyan zeminden sapma (koyu edisyon: parlak; acik: her iki yon),
    renk sarti YOK (halkanin beyaz parlamalari da dahil). 25 px genisletme."""
    Lu = luma(med)
    d = Lu.astype(np.float32) - cv2.medianBlur(Lu, 51).astype(np.float32)
    # acik edisyonda esik 30: parsomen lifleri (|d| 12-25) sabit murekkep sayilmasin
    m = ((d > dloc) if ed in DARK else (np.abs(d) > dlight)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    return cv2.dilate(m, np.ones((25, 25), np.uint8))


def shifted_fill(img, mask, region=None, k=48):
    """Maske piksellerini k px kaydirilmis maske-disi (ve bolge-ici) kopyadan doldurur."""
    out = img.copy(); todo = mask.astype(bool).copy()
    invalid = mask.astype(bool) | ((region == 0) if region is not None else False)
    for dx, dy in ((0, k), (0, -k), (k, 0), (-k, 0), (k, k), (-k, -k), (0, 2 * k), (0, -2 * k), (2 * k, 0), (-2 * k, 0)):
        if not todo.any():
            break
        src = np.roll(np.roll(img, dy, axis=0), dx, axis=1)
        srcm = np.roll(np.roll(invalid, dy, axis=0), dx, axis=1)
        ok = todo & ~srcm
        out[ok] = src[ok]; todo &= ~ok
    return out


# ------------------------------------------------------------------ dolgu
def aligned_median_canvas(med_dev, dev, canvas_shape):
    """Cihaz olcegindeki medyani pilot tuvaline yerlestirir; region maskesi doner."""
    s, (w, h), x0, y0 = placement(dev)
    H, W = canvas_shape[:2]
    canvas = np.zeros((H, W, 3), np.uint8)
    region = np.zeros((H, W), np.uint8)
    x0i, y0i = int(round(x0)), int(round(y0))
    ys0, ys1 = max(0, y0i), min(H, y0i + h)
    xs0, xs1 = max(0, x0i), min(W, x0i + w)
    canvas[ys0:ys1, xs0:xs1] = med_dev[ys0 - y0i:ys1 - y0i, xs0 - x0i:xs1 - x0i]
    region[ys0:ys1, xs0:xs1] = 1
    return canvas, region


def local_stats(img, w, sigma):
    """Gauss-agirlikli yerel ortalama/std (normalize konvolusyon), kanal basina."""
    w3 = w[..., None]
    den = cv2.GaussianBlur(w, (0, 0), sigma)[..., None]
    mu = cv2.GaussianBlur(img * w3, (0, 0), sigma) / np.maximum(den, 1e-4)
    var = cv2.GaussianBlur((img ** 2) * w3, (0, 0), sigma) / np.maximum(den, 1e-4) - mu ** 2
    return mu, np.sqrt(np.maximum(var, 1e-4))


def texture_std(img, sigma_hp=6.0, sigma_win=12.0):
    """Yerel doku siddeti: luma yuksek frekansinin (sigma_hp ustu) Gauss pencereli std'si."""
    g = luma(img).astype(np.float32)
    hp = g - cv2.GaussianBlur(g, (0, 0), sigma_hp)
    return np.sqrt(np.maximum(cv2.GaussianBlur(hp * hp, (0, 0), sigma_win), 0.0))


def build_plate(pilot, med_dev, ed, dev):
    F, region = aligned_median_canvas(med_dev, dev, pilot.shape)
    tex = texture_std(F)
    ink, t = ink_mask_pilot(pilot, ed, dev, region, tex=tex)
    mask = cv2.dilate(ink, np.ones((2 * DILATE_INK + 1, 2 * DILATE_INK + 1), np.uint8))
    mask &= region                              # dolgu kaynagi yalniz poster bolgesinde
    Pf = pilot.astype(np.float32); Ff = F.astype(np.float32)
    # Dolgu dokusu = medyanin yuksek frekansi (ton medyandan DEGIL, pilottan gelir).
    # Kosu 5'te dolgu = (F - muF)*gain + muP idi: muF halkadan tahmin edildigi icin maske
    # icinde medyanin kendi tonu tam cikmiyordu (CI halkada -2 seviyelik iz) ve kaydirilmis
    # kopya bloklari ton basamagi birakiyordu (WP). Simdi: hp = F - G16(F), yogun/kesin.
    lpF = cv2.GaussianBlur(Ff, (0, 0), float(HP_SIGMA))
    hpF = Ff - lpF
    # medyanin kendi murekkebi (sabit ogeler): yuksek frekans -> kaydirilmis kopya (tonsuz => dikissiz);
    # alcak frekans -> cevreden normalize konvolusyonla (blok yok)
    mm = ink_mask_median(F, ed) & region
    hpF = shifted_fill(hpF, mm, region)
    okw = ((region > 0) & (mm == 0)).astype(np.float32)
    lp_fill, _ = local_stats(lpF, okw, 32.0)
    toneF = np.where(mm[..., None] > 0, lp_fill, lpF)
    # yerel ton eslestirme: maske cevresi halkasi (16..64 px). Ton = medyanin kendi alcak
    # frekansi (yanik kenar egimi hizali gelir) + pilot-medyan farkinin halkadan olculen
    # puruzsuz ofseti. (Kosu 5: ton yalniz halkadan harmanlaniyordu -> dik egimde bant.)
    d_in = cv2.dilate(mask, np.ones((2 * RING_IN + 1, 2 * RING_IN + 1), np.uint8))
    d_out = cv2.dilate(mask, np.ones((2 * RING_OUT + 1, 2 * RING_OUT + 1), np.uint8))
    ring = ((d_out > 0) & (d_in == 0) & (region > 0)).astype(np.float32)
    muP, sdP = local_stats(Pf, ring, 32.0)
    muT, _ = local_stats(toneF, ring, 32.0)
    _, sdF = local_stats(hpF, region.astype(np.float32), 32.0)   # dolgu dokusunun yerel std'si (yogun)
    gain = np.clip(sdP / np.maximum(sdF, 1e-3), 0.15, 2.0)   # pilot zemini duzse (saat parlamasi, DB siyah) dolgu dokusu bastirilir
    Fm = hpF * gain + toneF + (muP - muT)
    # feather: murekkep cekirdegi (+2 px) tamamen dolgu (alfa 1); maske sinirina
    # dogru 22 px'te 0'a iner. (Onceki surum: alfa = mesafe/24 -> ince cizgilerde
    # hic 1'e ulasmiyor, pilot murekkebi %25-50 goruyordu = kabartma hayaleti.)
    core = cv2.dilate(ink, np.ones((5, 5), np.uint8))
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    alpha = np.clip(dist / float(FEATHER), 0, 1).astype(np.float32)
    alpha[core > 0] = 1.0
    alpha = alpha[..., None]
    alpha[mask[..., None] == 0] = 0.0
    out = Pf * (1 - alpha) + Fm * alpha
    out = np.clip(np.round(out), 0, 255).astype(np.uint8)
    out[mask == 0] = pilot[mask == 0]           # maske disi birebir
    return out, mask, ink, ring, dict(otsu=t, ink_px=int(ink.sum()), mask_px=int(mask.sum()), median_ink_px=int(mm.sum()))


# ------------------------------------------------------------------ QC
def hf_ratio(img, mask, ring):
    g = luma(img).astype(np.float32)
    hp = g - cv2.GaussianBlur(g, (0, 0), 4.0)
    si, so = float(hp[mask > 0].std()), float(hp[ring > 0].std())
    return si, so, (si / so if so > 0 else float("nan"))


def qc_sheet(plate, dev, path, side=600):
    H, W = plate.shape[:2]
    side = min(side, H, W)
    small_w = 600
    small = cv2.resize(plate, (small_w, int(small_w * H / W)), interpolation=cv2.INTER_AREA)
    tiles = [np.full((max(800, small.shape[0]), small_w, 3), 40, np.uint8)]
    tiles[0][:small.shape[0]] = small
    pts = [("halka", (REF_RING[0] + 200, (REF_RING[1] + REF_RING[3]) / 2)),
           ("sembol", ((REF_SYMBOL[0] + REF_SYMBOL[2]) / 2, (REF_SYMBOL[1] + REF_SYMBOL[3]) / 2)),
           ("tagline", ((REF_TAGLINE[0] + REF_TAGLINE[2]) / 2, (REF_TAGLINE[1] + REF_TAGLINE[3]) / 2))]
    for name, (px, py) in pts:
        cx, cy = poster_to_canvas(dev, px, py)
        x0 = int(np.clip(cx - side // 2, 0, W - side)); y0 = int(np.clip(cy - side // 2, 0, H - side))
        canvas = np.full((tiles[0].shape[0], 600, 3), 40, np.uint8)
        canvas[100:100 + side, :side] = plate[y0:y0 + side, x0:x0 + side]
        cv2.putText(canvas, f"{name} 1:1 @({x0},{y0})", (8, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(canvas)
    cv2.imwrite(str(path), np.hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 92])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", required=True, choices=EDITIONS)
    ap.add_argument("--posters", required=True, help="bu edisyonun 78 OPTIMIZED 3X4 posteri")
    ap.add_argument("--pilot", required=True, help="FINAL_V2/CANCER_LIBRA")
    ap.add_argument("--pilot-pair", default="Cancer_Libra")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-posters", type=int, default=40)
    a = ap.parse_args()
    ed = a.edition
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); (out / "qc").mkdir(exist_ok=True)
    posters = sorted(Path(a.posters).glob(f"WA_POSTER_*_{ed.upper()}_3X4.jpg"))
    log(f"{ed}: {len(posters)} poster")
    if len(posters) < a.min_posters:
        raise SystemExit(f"HATA: {len(posters)} poster (>= {a.min_posters} beklenir)")
    t0 = time.time()
    med = device_medians([str(p) for p in posters])
    log(f"medyanlar hazir: {time.time() - t0:.0f}s")
    report = {}
    for dev in ["Phone", "Tablet", "Desktop", "Watch"]:
        pilot = imread(Path(a.pilot) / f"AstroLove_{a.pilot_pair}_{ed}_{dev}.jpg")
        W, H = DEVICES[dev]
        if pilot.shape[1] != W or pilot.shape[0] != H:
            raise SystemExit(f"HATA: pilot {dev} {pilot.shape[1]}x{pilot.shape[0]}")
        plate, mask, ink, ring, info = build_plate(pilot, med[dev], ed, dev)
        outside = float(np.abs(plate.astype(np.int16) - pilot.astype(np.int16))[mask == 0].max()) if (mask == 0).any() else 0.0
        si, so, r = hf_ratio(plate, mask, ring)
        name = f"PLATE_{ed.upper()}_{dev.upper()}.png"
        cv2.imwrite(str(out / name), plate, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        cv2.imwrite(str(out / "qc" / f"MASK_{ed.upper()}_{dev.upper()}.png"), mask * 255)
        qc_sheet(plate, dev, out / "qc" / f"PLATE_{ed.upper()}_{dev.upper()}.jpg")
        report[dev] = dict(file=name, size=[W, H], outside_max_diff=outside, hf_inside=si, hf_ring=so, hf_ratio=r, **info)
        log(f"  {dev:8s} maske {info['mask_px']} px (murekkep {info['ink_px']}, otsu {info['otsu']:.0f}, medyan-murekkep {info['median_ink_px']}) | maske disi maks fark {outside:.0f} | HF ic/halka {si:.2f}/{so:.2f} = {r:.2f}")
    (out / f"report_{ed}.json").write_text(json.dumps(dict(edition=ed, posters=len(posters), devices=report), indent=1))
    log(f"toplam {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
