#!/usr/bin/env python3
"""
wp-plate-pilot: 16 temiz plaka (edisyon x cihaz), referans = CANLI PILOT
wallpaper dosyalari (WALLPAPER/FINAL_V2/CANCER_LIBRA). Mo 2 Eyl yontemi,
kapsam 2 (2 Eyl aksam):

* Halka ve tagline ("Two Souls · One Bond") pilottan AYNEN kalir; plakada
  silinmez (6 posterde de birebir ayni kutuda: halka 920,1147,6279,5696;
  tagline 2485,8226,4715,8454).
* Temizlenen yalniz cifte ozel murekkep: fuzyon sembolu (halka ici), iki
  isim, iki glif. Maske = bu bolgelerdeki murekkep + 12 px dilate; halka
  bandi (medyandan turetilen halka cizgisi + 2 px) maskeden DISLANIR: sembol
  halkayi kestigi yerde halka cizgisi pilottaki gibi kalir.
* OLCUM (6 CI posteri): ∞ logonun konumu cifte gore DEGISIR — "ISIM ∞ ISIM"
  satiri bir butun olarak ortalaniyor: ∞ merkezi 2890..3812 poster px
  (LEO_SAGITTARIUS 2578..3201, CANCER_LIBRA 3500..4124, GEMINI_SCORPIO
  3112..3735). Bu yuzden ∞ isim satiriyla birlikte temizlenir
  (KEEP_INFINITY=False) ve ink katmaninda posterden isimlerle beraber
  alinir; aksi halde uzun isimler pilotun ∞'sinin ustune binerdi.
* ∞ logo (pilotta poster kutusu 3500..4124 x 7110..7296) halka ve tagline gibi
  pilottan AYNEN kalir (Mo, 2 Eyl aksam 2. talimat); maske ve aday tespiti bu
  kutunun 6 px cevresini dislar. NOT (olcum, 6 CI posteri): ∞ konumu cifte
  gore kayar (∞ merkezi 2890..3812 poster px); ink katmani posterin kendi
  ∞'sini almaz — uzun isimli ciftlerde isimler pilot ∞'sinin ustune binebilir,
  bu uretim adiminda kontrol edilecek.
* Dolgu kaynagi: YALNIZ OPTIMIZED 3X4 78 posterin tam cozunurluk (7200x9600)
  piksel-MEDYANI (satir parcalariyla, uint8 partition; edisyon basina bir kez,
  MEDIAN_<EDISYON>.png). QC: medyanda eleman kutularinda (halka bandi ve ∞
  kutusu haric) murekkep pikseli = 0 beklenir (sayi + bilesen listesi raporda).
  Pilotun kendisinden doku orneklenmez. Medyan INTER_AREA ile cihaz olcegine
  indirilir, olculen afin yerlesimle pilot tuvaline hizalanir; dokusu
  (sigma-16 ustu, sabit ogelerin oldugu yerde 48 px kaydirilmis kopya) iki
  bantta (ince <4 px, orta 4..16) pilotun maske cevresi halkasindaki std'ye
  olceklenir + pilotun yerel tonu (halka 16..64 px, murekkepsiz, normalize
  konvolusyon sigma 32; agirlik yetersizse x2/x4/x8). Feather 24 px: maske =
  murekkep + 24 px; alfa murekkep+6 px'te 1 (olcum: kenar parlamasi 5 px'te
  biter), maske sinirinda 0. Inpaint yok.
* Yerel duman testi: ayni kod 6 posterle (6'nin medyani sembol/isim
  hayaletlerini TAM silemez — QC sayisi raporlanir; 78 posterde medyan temiz).
* QC her plakada: (a) maske disi fark pilotla = 0 (halka bandi dahil),
  (b) maske ici HF (luma - Gauss s=4) std / cevre halkasi, (c) 3 kesit
  600x600 1:1 pilot | plaka | fark x4: sembol merkezi, isim bolgesi, halka
  kesisimi (sembol murekkebinin halka bandina en cok degdigi yer).
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

# Poster px eleman kutulari (6 CI posterinde olculdu; sabit ogeler kutu DISINDA):
#   halka bbox (sabit)        : (920, 1147, 6279, 5696)
#   tagline bbox (sabit)      : (2485, 8226, 4715, 8454)
#   glif satiri (degisken)    : y 6066..6712, sol x 1533..2803, sag x 4494..5509
#   isim satiri + ∞ (degisken): y 7042..7388, x 1323..5876
REF_RING = (920, 1147, 6279, 5696)
# Halka geometrisi (medyan halka bilesenine elips uydurma; Phone/Tablet/Desktop, CI ve MB birebir):
# merkez (3602,3874), yari eksenler 2675 x 2710 poster px, egim ~1 derece, cizgi ~15 px;
# altta ACIK yay: uclar y=5696'da (bbox alt siniri). Band bu elipsten cizilir (WP yanik kenarda
# yerel kontrast tespiti bosluk birakiyordu -> halka orada maskelenip siliniyordu).
RING_ELLIPSE = (3602.0, 3874.0, 2675.0, 2710.0)
RING_TIP_Y = 5696
RING_LINE_PX = 15.0
REF_TAGLINE = (2485, 8226, 4715, 8454)
BOX_SYMBOL = (900, 1100, 6300, 5950)      # halka kutusu; halka bandi ayrica dislanir
BOX_GLYPHS = (1100, 5950, 6100, 6900)
BOX_NAMES = (900, 6950, 6300, 7500)       # isimler (+ ∞ kutusu ayrica dislanir)
ELEMENT_BOXES = [BOX_SYMBOL, BOX_GLYPHS, BOX_NAMES]
REF_INFINITY = (3500, 7110, 4124, 7296)   # pilot (Cancer_Libra) ∞ logosu, poster px; +6 px maske disi
INF_PAD = 6
CLEAN_INFINITY = True   # 3 Eyl: ∞ logosu da temizlenir (posterden gelir); False = pilottan kalir

HP_SIGMA = 16       # dolgu = medyanin yuksek frekans dokusu (sigma 16 ustu) + pilotun yerel tonu
DILATE_INK = 24     # maske = murekkep + 24 px (feather 24)
CORE_PAD = 6        # alfa = 1 bolgesi: murekkep + 6 px (olcum: kenar parlamasi/golgesi 5 px'te sifirlanir;
                    # 2 px'te birakinca MB/DB'de kontur boyunca 3-6 seviyelik parlak iz kaliyordu)
FEATHER = DILATE_INK - CORE_PAD   # 18 px'lik gecis maske ICINDE
RING_BAND = 3       # halka cizgisi (elips) + 3 px: maske disi (halka elipsten +-%0.5 sapiyor)
CORE_DEV = 60       # cekirdek icin morfolojik zeminden (kapama/acma 61 px) en az sapma. Olcum (WP, 3 cihaz):
                    # gercek murekkep |d| p5 145-159, yanik kenar kivrimlari (renk+Otsu'yu gecen) p50 31-39, p95 7-13.
                    # medianBlur 51 zemini kalin vuruslarda (Tablet/Desktop, >25 px) vurus icinde kaliyordu -> kullanilmaz.
RING_IN, RING_OUT = 16, 64
MEDIAN_CHUNK_ROWS = 800   # tam cozunurluk medyan: 78 x 800 x 7200 x 3 = 1.35 GB / parca
# Dikey cizgili bant (Phone/Tablet ust-alt kenar): satir olcusu = yatay gradyan enerjisi / dikey gradyan
# enerjisi; > BAND_RATIO olan satirlar bant (5 satir yumusatma). Olcum (pilot): CI Phone 31/33 px,
# WP Phone 37/38 px; MB/DB Phone ve tum Tablet 0 (kenar satir oranlari 0.5-2.3).
BAND_RATIO = 3.0
BAND_OVERLAP = 48        # dolgu = bant + 48 px (feather tamamen bant DISINDA: bant satirlarinda alfa 1)
BAND_FEATHER = 48        # dikey feather: bant sinirindan +48 px'e dogru 1 -> 0
# NOT (iterasyon 1): overlap 24 / feather +-24 ile bant satirlarinin yarisi pilotun cizgili
# satirlariyla harmanlaniyordu -> bant cizgi orani 1.5-2.8. Overlap 48 ile bant satirlari saf dolgu.
BAND_QC_RATIO = 1.2      # (eski dolgu QC'si; kirpma yonteminde kullanilmaz)
BAND_DEVICES = ("Phone", "Tablet")
# Bant yontemi 3 (Mo, 3 Eyl): dolgu YOK. Bant satirlari ust/alttan kirpilir (tespit + BAND_SAFETY px),
# kalan goruntu LANCZOS ile tam tuval yuksekligine dikey olceklenir (genislik sabit). Geometri
# (crop_top, crop_bot, scale_y) GEOM_<ED>_<DEV>.json'a yazilir; ink katmani ayni dikey carpani uygular.
# QC: kenar satirlarinda oran > BAND_RATIO satir sayisi 0; kenar satir orani ile pilotun dogal satir
# referansi (bant+64..+164) farki < BAND_QC_REF_DIFF.
BAND_SAFETY = 4
BAND_QC_REF_DIFF = 0.15
BAND_EDGE_ROWS = 40


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


def box_mask(shape, dev, boxes):
    m = np.zeros(shape[:2], np.uint8)
    for (bx0, by0, bx1, by1) in boxes:
        x0, y0 = poster_to_canvas(dev, bx0, by0); x1, y1 = poster_to_canvas(dev, bx1, by1)
        m[max(0, int(y0)):int(y1) + 1, max(0, int(x0)):int(x1) + 1] = 1
    return m


# ------------------------------------------------------------------ 78 poster medyani (tam cozunurluk)
def poster_median_fullres(poster_paths, rows=MEDIAN_CHUNK_ROWS):
    """7200x9600 posterlerin piksel medyani, satir parcalariyla (her parca icin posterler yeniden
    okunur: bellek 78 x rows x 7200 x 3). Cift sayida n: iki ortanca degerin ortalamasi."""
    n = len(poster_paths)
    out = np.empty((9600, 7200, 3), np.uint8)
    t0 = time.time()
    chunks = list(range(0, 9600, rows))
    for ci, y in enumerate(chunks):
        h = min(rows, 9600 - y)
        st = np.empty((n, h, 7200, 3), np.uint8)
        for i, p in enumerate(poster_paths):
            im = imread(p)
            if im.shape[1] != 7200 or im.shape[0] != 9600:
                raise SystemExit(f"HATA: {Path(p).name} {im.shape[1]}x{im.shape[0]} (7200x9600 degil)")
            st[i] = im[y:y + h]
        part = np.partition(st, (n // 2 - 1, n // 2) if n % 2 == 0 else (n // 2,), axis=0)
        if n % 2 == 0:
            a = part[n // 2 - 1].astype(np.uint16); b = part[n // 2].astype(np.uint16)
            out[y:y + h] = ((a + b + 1) // 2).astype(np.uint8)
        else:
            out[y:y + h] = part[n // 2]
        del st, part
        el = time.time() - t0
        log(f"  medyan parca {ci + 1}/{len(chunks)}  gecen {el:5.0f}s  kalan {el / (ci + 1) * (len(chunks) - ci - 1):5.0f}s")
    return out


def device_medians_from(median):
    """Tam cozunurluk medyani 4 cihaz boyutuna INTER_AREA ile indirir (poster -> wallpaper ile ayni yol)."""
    return {dev: cv2.resize(median, PLACEMENT[dev]["size"], interpolation=cv2.INTER_AREA) for dev in PLACEMENT}


def median_ink_qc(median, ed, tol=70):
    """Medyanda kalan cifte ozel murekkep (beklenen 0): eleman kutularinda, halka bandi ve ∞ kutusu
    disinda, renk+Otsu+morfolojik sapma (>= CORE_DEV) ile aday pikseller; bilesen >= 100 px.
    Donus: (piksel sayisi, bilesen bbox listesi, gorsel)."""
    r, g, b = INK_RGB[ed]
    Lu = luma(median); L = Lu.astype(np.float32)
    dist = np.sqrt(((median.astype(np.float32) - np.array([b, g, r], np.float32)) ** 2).sum(axis=2))
    t = otsu_thresh(Lu)
    ker = np.ones((61, 61), np.uint8)
    bg_m = (cv2.morphologyEx(Lu, cv2.MORPH_OPEN, ker) if ed in DARK else cv2.morphologyEx(Lu, cv2.MORPH_CLOSE, ker)).astype(np.float32)
    cand = (((L > t) if ed in DARK else (L < t)) & (dist < tol) & (np.abs(L - bg_m) > CORE_DEV)).astype(np.uint8)
    boxes = np.zeros(Lu.shape, np.uint8)
    for (x0, y0, x1, y1) in ELEMENT_BOXES:
        boxes[y0:y1 + 1, x0:x1 + 1] = 1
    ring = np.zeros_like(cand)
    cx, cy, ax, ay = RING_ELLIPSE
    cv2.ellipse(ring, (int(cx), int(cy)), (int(ax), int(ay)), 0, 0, 360, 1, int(RING_LINE_PX) + 2 * 5 * RING_BAND, cv2.LINE_8)
    ring[RING_TIP_Y + 1:, :] = 0
    inf = np.zeros_like(cand); x0, y0, x1, y1 = REF_INFINITY; inf[y0 - 30:y1 + 31, x0 - 30:x1 + 31] = 1
    cand = cand & boxes & (ring == 0) & (inf == 0)
    n, lab, st, _ = cv2.connectedComponentsWithStats(cand)
    comps = [tuple(int(v) for v in st[i, :5]) for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= 100]
    px = int(sum(c[4] for c in comps))
    vis = cv2.resize(median, (600, 800), interpolation=cv2.INTER_AREA)
    for (x, y, w, h, a) in comps:
        cv2.rectangle(vis, (int(x / 12), int(y / 12)), (int((x + w) / 12), int((y + h) / 12)), (0, 0, 255), 2)
    cv2.putText(vis, f"{ed} medyan murekkep: {px} px / {len(comps)} bilesen", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return px, comps, vis


# ------------------------------------------------------------------ maskeler
def otsu_thresh(vals):
    vals = vals.astype(np.uint8)
    t, _ = cv2.threshold(vals, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return float(t)


def texture_std(img, sigma_hp=6.0, sigma_win=12.0):
    """Yerel doku siddeti: luma yuksek frekansinin (sigma_hp ustu) Gauss pencereli std'si."""
    g = luma(img).astype(np.float32)
    hp = g - cv2.GaussianBlur(g, (0, 0), sigma_hp)
    return np.sqrt(np.maximum(cv2.GaussianBlur(hp * hp, (0, 0), sigma_win), 0.0))


def median_ink_core(med, ed, dloc=18, dlight=30):
    """Medyanin kendi murekkebi (halka, tagline, kismen isim/∞ hayaletleri), genisletmesiz."""
    Lu = luma(med)
    d = Lu.astype(np.float32) - cv2.medianBlur(Lu, 51).astype(np.float32)
    m = ((d > dloc) if ed in DARK else (np.abs(d) > dlight)).astype(np.uint8)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))


def ink_mask_median(med, ed):
    """Sabit ogeler + 25 px: dolgu dokusunun bu piksellerde kaydirilmis kopyadan alinacagi bolge."""
    return cv2.dilate(median_ink_core(med, ed), np.ones((25, 25), np.uint8))


def ring_band(med_canvas, ed, dev, region):
    """Halka bandi = RING_ELLIPSE'in cihaz olcegine afin izdusumu, kalinlik = cizgi (15 poster px)
    + 2*RING_BAND, yalniz y <= uc (acik yay). Dogrulama: medyanin halka kutusundaki en buyuk
    murekkep bileseninin bant tarafindan kapsanma orani (log)."""
    H, W = med_canvas.shape[:2]
    s, _, x0, y0 = placement(dev)
    cx, cy = poster_to_canvas(dev, RING_ELLIPSE[0], RING_ELLIPSE[1])
    ax, ay = RING_ELLIPSE[2] * s, RING_ELLIPSE[3] * s
    thick = int(round(RING_LINE_PX * s)) + 2 * RING_BAND
    band = np.zeros((H, W), np.uint8)
    cv2.ellipse(band, (int(round(cx)), int(round(cy))), (int(round(ax)), int(round(ay))), 0, 0, 360, 1, thick, cv2.LINE_8)
    _, ytip = poster_to_canvas(dev, 0, RING_TIP_Y)
    band[int(ytip) + 1:, :] = 0
    band &= region
    core = median_ink_core(med_canvas, ed) & region & box_mask(med_canvas.shape, dev, [BOX_SYMBOL])
    n, lab, st, _ = cv2.connectedComponentsWithStats(core)
    line = np.zeros_like(core)
    if n > 1:
        i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        line = (lab == i).astype(np.uint8)
        cov = float((line & band).sum()) / max(1, int(line.sum()))
        log(f"    halka bandi {dev}: elips kalinlik {thick} px, medyan halka bileseni {int(line.sum())} px, bant kapsama %{100 * cov:.1f}")
    return band, line


def ink_mask_pilot(pilot, ed, dev, canvas_region, exclude, tex=None, tol=70, dloc=18):
    """Pilotun cifte ozel murekkebi (eleman kutularinda; exclude = halka bandi + 6 px disari):
    cekirdek = murekkep rengine yakin (tol) + luma Otsu (MB/DB parlak, CI/WP koyu);
    uzanti   = yerel zeminden (medyan 51 px) sapan pikseller (kenar yumusatma, altin
               parlama/golge, kabartma), esik zemin dokusuyla olceklenir (>= 2.5*tex),
               YALNIZ cekirdegin 40 px komsulugundaki bilesenler (alan >= 12).
    Kenara degen bloblar (vinyet) atilir. 2x2 acma YOK (1 px kuyruk uclari)."""
    r, g, b = INK_RGB[ed]
    Lu = luma(pilot)
    L = Lu.astype(np.float32)
    dist = np.sqrt(((pilot.astype(np.float32) - np.array([b, g, r], np.float32)) ** 2).sum(axis=2))
    reg = (canvas_region > 0) & (box_mask(pilot.shape, dev, ELEMENT_BOXES) > 0) & (exclude == 0)
    t = otsu_thresh(Lu[canvas_region > 0])
    bg = cv2.medianBlur(Lu, 51).astype(np.float32)
    d = L - bg
    ker = np.ones((61, 61), np.uint8)
    bg_m = (cv2.morphologyEx(Lu, cv2.MORPH_OPEN, ker) if ed in DARK else cv2.morphologyEx(Lu, cv2.MORPH_CLOSE, ker)).astype(np.float32)
    core = ((L > t) if ed in DARK else (L < t)) & (dist < tol) & reg & (np.abs(L - bg_m) > CORE_DEV)
    # kucuk izole cekirdek benekleri (WP yanik kenar gozenekleri, koyu edisyonda yildiz cekirdegi) atilir:
    # alan < 30 px (Phone olcegi; olcekle kare orantili). Murekkep bilesenleri bunun cok ustunde.
    s_dev = placement(dev)[0]
    min_area = int(30 * (s_dev / 0.2) ** 2)
    core_u8 = core.astype(np.uint8)
    n0, lab0, st0, _ = cv2.connectedComponentsWithStats(core_u8)
    small = np.zeros(n0, bool); small[1:] = st0[1:, cv2.CC_STAT_AREA] < min_area
    core = core & ~small[lab0]
    thr = np.full(L.shape, float(dloc if ed in DARK else dloc * 2 / 3), np.float32)
    if tex is not None:
        thr = np.maximum(thr, 2.5 * tex)
    ext = (d > thr) if ed in DARK else (np.abs(d) > thr)
    ext &= reg
    cand = (ext | core).astype(np.uint8)
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
    loose = cv2.dilate(cand, np.ones((17, 17), np.uint8))   # ton halkasindan dislanacak gevsek murekkep
    return keep, t, loose


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


def _gblur(img, sigma, ds=1):
    """Gauss bulaniklik; ds>1: 1/ds cozunurlukte (sigma/ds) hesaplanip geri buyutulur (genis sigma icin hizli)."""
    if ds == 1:
        return cv2.GaussianBlur(img, (0, 0), sigma)
    H, W = img.shape[:2]
    small = cv2.resize(img, (max(1, int(W // ds)), max(1, int(H // ds))), interpolation=cv2.INTER_AREA)
    b = cv2.GaussianBlur(small, (0, 0), sigma / ds)
    out = cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
    return out if out.ndim == img.ndim else out[..., None]


def local_stats(img, w, sigma, min_den=0.02, sigmas=(2, 4, 8)):
    """Gauss-agirlikli yerel ortalama/std (normalize konvolusyon), kanal basina.
    Agirlik kutlesi (den) yetersiz kalan piksellerde (genis maske ici) sigma x2/x4/x8'e
    dusulur (1/k cozunurlukte hesaplanir: hiz)."""
    w3 = w[..., None]
    den = cv2.GaussianBlur(w, (0, 0), sigma)[..., None]
    mu = cv2.GaussianBlur(img * w3, (0, 0), sigma) / np.maximum(den, 1e-6)
    m2 = cv2.GaussianBlur((img ** 2) * w3, (0, 0), sigma) / np.maximum(den, 1e-6)
    for k in sigmas:
        bad = den < min_den
        if not bad.any():
            break
        den_k = _gblur(w, sigma * k, k)
        den_k = den_k if den_k.ndim == 3 else den_k[..., None]
        mu_k = _gblur(img * w3, sigma * k, k) / np.maximum(den_k, 1e-6)
        m2_k = _gblur((img ** 2) * w3, sigma * k, k) / np.maximum(den_k, 1e-6)
        mu = np.where(bad, mu_k, mu); m2 = np.where(bad, m2_k, m2); den = np.where(bad, den_k, den)
    var = m2 - mu ** 2
    return mu, np.sqrt(np.maximum(var, 1e-4))


def build_plate(pilot, med_dev, ed, dev):
    F, region = aligned_median_canvas(med_dev, dev, pilot.shape)
    band, ring_line = ring_band(F, ed, dev, region)
    band_wide = cv2.dilate(band, np.ones((13, 13), np.uint8))          # cekirdek/uzanti icin halka + 6 px disari
    inf = box_mask(pilot.shape, dev, [REF_INFINITY])
    inf = cv2.dilate(inf, np.ones((2 * INF_PAD + 1, 2 * INF_PAD + 1), np.uint8))   # ∞ logosu + 6 px
    # CLEAN_INFINITY (3 Eyl): ∞ logosu da plakadan temizlenir; cift kendi ∞'sini posterden
    # getirir (konumu isim uzunluguna gore kayar: olcum x0 3108..3516, pilot 3500 -> cift
    # ∞'si pilot ∞'siyle ust uste binmez, ikisi de kalsa cift ∞ gorunurdu).
    keep_out = ((band_wide > 0) | ((inf > 0) & (not CLEAN_INFINITY))).astype(np.uint8)
    tex = texture_std(F)
    ink, t, loose = ink_mask_pilot(pilot, ed, dev, region, keep_out, tex=tex)
    if CLEAN_INFINITY:
        ink = (ink | (inf & region)).astype(np.uint8)
    k = 2 * DILATE_INK + 1
    mask = cv2.dilate(ink, np.ones((k, k), np.uint8)) & region
    mask[band > 0] = 0                                                   # halka bandi pilottan aynen kalir
    if not CLEAN_INFINITY:
        mask[inf > 0] = 0                                                # ∞ logosu pilottan aynen kalir
    Pf = pilot.astype(np.float32); Ff = F.astype(np.float32)
    hpF = Ff - cv2.GaussianBlur(Ff, (0, 0), float(HP_SIGMA))
    mm = ink_mask_median(F, ed) & region
    hpF = shifted_fill(hpF, mm, region)
    d_in = cv2.dilate(mask, np.ones((2 * RING_IN + 1, 2 * RING_IN + 1), np.uint8))
    d_out = cv2.dilate(mask, np.ones((2 * RING_OUT + 1, 2 * RING_OUT + 1), np.uint8))
    ring = ((d_out > 0) & (d_in == 0) & (region > 0) & (loose == 0) & (keep_out == 0)).astype(np.float32)
    muP, _ = local_stats(Pf, ring, 32.0)
    # Doku kazanci iki bantta ayri (ince: sigma<4, orta: 4..16). Olcum (MB Watch): pilot parlama
    # bolgesi ince bantta 0.32, poster zemini 0.73 (bulut greni) — tek bant (sigma16) kazanci 1'e
    # yakin cikip ince greni oldugu gibi birakiyordu (lekeli gorunum). Taban 0.02: pilot puruzsuzse
    # dolgu da puruzsuz (DB siyah, Watch parlama).
    regw = region.astype(np.float32)
    g4P = cv2.GaussianBlur(Pf, (0, 0), 4.0); g4F = cv2.GaussianBlur(Ff, (0, 0), 4.0)
    fineP = Pf - g4P; midP = g4P - cv2.GaussianBlur(Pf, (0, 0), float(HP_SIGMA))
    g4F_sh = cv2.GaussianBlur(hpF, (0, 0), 4.0)          # hpF: kaydirilmis kopya uygulanmis HF
    fineF = hpF - g4F_sh; midF = g4F_sh
    _, sdPf = local_stats(fineP, ring, 32.0); _, sdFf = local_stats(fineF, regw, 32.0, sigmas=())
    _, sdPm = local_stats(midP, ring, 32.0); _, sdFm = local_stats(midF, regw, 32.0, sigmas=())
    gain_f = np.clip(sdPf / np.maximum(sdFf, 1e-3), 0.02, 2.0)
    gain_m = np.clip(sdPm / np.maximum(sdFm, 1e-3), 0.02, 2.0)
    Fm = fineF * gain_f + midF * gain_m + muP
    gain = gain_f
    core = cv2.dilate(ink, np.ones((2 * CORE_PAD + 1, 2 * CORE_PAD + 1), np.uint8))
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    alpha = np.clip(dist / float(FEATHER), 0, 1).astype(np.float32)
    alpha[core > 0] = 1.0
    alpha = alpha[..., None]
    alpha[mask[..., None] == 0] = 0.0
    out = Pf * (1 - alpha) + Fm * alpha
    out = np.clip(np.round(out), 0, 255).astype(np.uint8)
    out[mask == 0] = pilot[mask == 0]           # maske disi birebir (halka bandi dahil)
    info = dict(otsu=t, ink_px=int(ink.sum()), mask_px=int(mask.sum()), median_ink_px=int(mm.sum()),
                ring_band_px=int(band.sum()), ring_cross_px=int((core & band).sum()), inf_px=int(inf.sum()))
    return out, mask, ink, ring, band, info


# ------------------------------------------------------------------ dikey cizgili bant (ust/alt kenar)
def stripe_ratio_rows(img, smooth=5):
    """Satir basina yatay/dikey gradyan enerji orani (kenar dolgusu uzatilmis satirlarda >> 1)."""
    L = luma(img).astype(np.float32)
    gx = np.abs(np.diff(L, axis=1))[:-1, :]; gy = np.abs(np.diff(L, axis=0))[:, :-1]
    r = ((gx ** 2).mean(axis=1) + 1e-3) / ((gy ** 2).mean(axis=1) + 1e-3)
    k = smooth // 2
    return np.convolve(np.pad(r, k, mode="edge"), np.ones(smooth) / smooth, mode="valid")


def band_detect(pilot, thr=BAND_RATIO):
    """Ust ve alt kenardan iceri tarama: oran > thr olan ardisik satirlar = bant. (ust_px, alt_px, oranlar)"""
    rs = stripe_ratio_rows(pilot)
    n = len(rs)
    top = 0
    while top < n and rs[top] > thr:
        top += 1
    bot = 0
    while bot < n and rs[n - 1 - bot] > thr:
        bot += 1
    return int(top), int(bot), rs


def cover_median(median, shape):
    """Medyani tuval yuksekligine olcekler (INTER_AREA), genislikte ortadan kirpar (COVER)."""
    H, W = shape[:2]
    s = H / float(median.shape[0])
    w = max(W, int(round(median.shape[1] * s)))
    cov = cv2.resize(median, (w, H), interpolation=cv2.INTER_AREA)
    x0 = (w - W) // 2
    return cov[:, x0:x0 + W]


def band_fill(plate, pilot, cover, ed, top, bot, overlap=BAND_OVERLAP, feather=BAND_FEATHER):
    """Ust/alt bant + overlap satirlarini cover medyanla doldurur: medyanin dokusu (iki bant kazanc)
    + medyanin kendi alcak frekansi (posterin kenar tonu, WP amber kenar) + pilot-medyan ofseti
    (dolgu disindaki 16..64 px satirlardan, normalize konvolusyon) ; alfa dikeyde feather px'te
    1 -> 0 (bant siniri +-feather/2). Donus: (plaka, bant maskesi)."""
    H, W = plate.shape[:2]
    out = plate.astype(np.float32)
    Pf = pilot.astype(np.float32); Cf = cover.astype(np.float32)
    mm = ink_mask_median(cover, ed)                       # halka ustu / tagline / isim hayaleti cover'da
    Cf = shifted_fill(Cf, mm, None, k=48)
    lpC = cv2.GaussianBlur(Cf, (0, 0), float(HP_SIGMA)); hpC = Cf - lpC
    g4C = cv2.GaussianBlur(hpC, (0, 0), 4.0); fineC = hpC - g4C; midC = g4C
    g4P = cv2.GaussianBlur(Pf, (0, 0), 4.0); fineP = Pf - g4P; midP = g4P - cv2.GaussianBlur(Pf, (0, 0), float(HP_SIGMA))
    bmask = np.zeros((H, W), np.uint8)
    ones = np.ones((H, W), np.float32)
    for side, h in (("top", top), ("bot", bot)):
        if h <= 0:
            continue
        fill_h = min(H, h + overlap)
        mask = np.zeros((H, W), np.uint8)
        ring = np.zeros((H, W), np.float32)
        y = np.arange(H, dtype=np.float32)
        if side == "top":
            mask[:fill_h] = 1
            ring[min(H, fill_h + RING_IN):min(H, fill_h + RING_OUT)] = 1
            alpha = np.clip((fill_h - y) / float(feather), 0, 1)      # y <= h: 1 ; y = h + 48: 0
        else:
            mask[H - fill_h:] = 1
            ring[max(0, H - fill_h - RING_OUT):max(0, H - fill_h - RING_IN)] = 1
            alpha = np.clip((y - (H - fill_h)) / float(feather), 0, 1)
        muP, _ = local_stats(Pf, ring, 32.0)
        muT, _ = local_stats(lpC, ring, 32.0)
        _, sdPf = local_stats(fineP, ring, 32.0); _, sdCf = local_stats(fineC, ones, 32.0, sigmas=())
        _, sdPm = local_stats(midP, ring, 32.0); _, sdCm = local_stats(midC, ones, 32.0, sigmas=())
        gf = np.clip(sdPf / np.maximum(sdCf, 1e-3), 0.02, 2.0); gm = np.clip(sdPm / np.maximum(sdCm, 1e-3), 0.02, 2.0)
        Fm = fineC * gf + midC * gm + lpC + (muP - muT)
        a = (alpha[:, None] * mask)[..., None]
        out = out * (1 - a) + Fm * a
        bmask |= mask
    out = np.clip(np.round(out), 0, 255).astype(np.uint8)
    out[bmask == 0] = plate[bmask == 0]
    return out, bmask


def band_qc(plate, pilot, top, bot, overlap=BAND_OVERLAP, feather=BAND_FEATHER):
    """(a) dolgu sonrasi bant satirlarinda cizgi orani (maks) < BAND_QC_RATIO,
    (b) harman seridinde (bant siniri +-feather/2) HF (luma - Gauss s=4) std / disaridaki 16..64 px satirlar in [0.75, 1.33].
    Referans: pilotun bant disindaki dogal satir orani (bant+64..+164)."""
    H = plate.shape[0]
    rs = stripe_ratio_rows(plate); rp = stripe_ratio_rows(pilot)
    g = luma(plate).astype(np.float32); hp = g - cv2.GaussianBlur(g, (0, 0), 4.0)
    res = {}
    for side, h in (("top", top), ("bot", bot)):
        if h <= 0:
            res[side] = dict(band_px=0)
            continue
        fill_h = min(H, h + overlap)
        if side == "top":
            band_rows = slice(0, h); blend = slice(h, fill_h); outside = slice(fill_h + RING_IN, fill_h + RING_OUT); ref = slice(h + 64, h + 164)
        else:
            band_rows = slice(H - h, H); blend = slice(H - fill_h, H - h); outside = slice(H - fill_h - RING_OUT, H - fill_h - RING_IN); ref = slice(H - h - 164, H - h - 64)
        ratio_max = float(rs[band_rows].max()); ratio_ref = float(np.median(rp[ref]))
        hf_blend = float(hp[blend].std()); hf_out = float(hp[outside].std()); hf_ratio = hf_blend / hf_out if hf_out > 0 else float("nan")
        res[side] = dict(band_px=int(h), fill_px=int(fill_h), stripe_ratio_max=ratio_max, stripe_ratio_ref=ratio_ref,
                         hf_blend=hf_blend, hf_outside=hf_out, hf_ratio=hf_ratio,
                         pass_stripe=bool(ratio_max < BAND_QC_RATIO), pass_hf=bool(0.75 <= hf_ratio <= 1.33))
    return res


def band_crop_geom(H, top, bot, safety=BAND_SAFETY):
    """Kirpma geometrisi: crop_top/crop_bot (px), scale_y = H / (H - crop_top - crop_bot)."""
    ct = top + safety if top > 0 else 0
    cb = bot + safety if bot > 0 else 0
    return dict(crop_top=int(ct), crop_bot=int(cb), scale_y=float(H) / float(H - ct - cb))


def apply_geom(img, geom, interpolation=cv2.INTER_LANCZOS4):
    """Bant satirlarini kirpar, kalan goruntuyu tam yukseklige dikey olcekler (genislik sabit)."""
    H, W = img.shape[:2]
    ct, cb = geom["crop_top"], geom["crop_bot"]
    if ct == 0 and cb == 0:
        return img.copy()
    cropped = img[ct:H - cb]
    return cv2.resize(cropped, (W, H), interpolation=interpolation)


def band_crop_qc(plate, pilot, top, bot, edge_rows=BAND_EDGE_ROWS):
    """Kirpma sonrasi: (a) ust/alt kenar satirlarinda oran > BAND_RATIO satir sayisi (beklenen 0),
    (b) kenar satirlarinin (40) oran ortalamasi, pilotun dogal satirlarinin (bant+8..+400, 40'lik
    pencere ortalamalari) araliginda [p10 - 0.15, p90 + 0.15] olmali ("ayni aralik", BAND_QC_REF_DIFF)."""
    H = plate.shape[0]
    rs = stripe_ratio_rows(plate); rp = stripe_ratio_rows(pilot)
    res = {}
    for side, h in (("top", top), ("bot", bot)):
        if side == "top":
            edge = rs[:edge_rows]; nat = rp[h + 8:h + 400]
        else:
            edge = rs[H - edge_rows:]; nat = rp[H - h - 400:H - h - 8]
        win = np.convolve(nat, np.ones(edge_rows) / edge_rows, mode="valid")     # 40 satirlik pencere ortalamalari
        lo, hi = float(np.percentile(win, 10)), float(np.percentile(win, 90))
        n_band = int((edge > BAND_RATIO).sum()); em = float(edge.mean())
        res[side] = dict(band_px=int(h), edge_ratio_mean=em, edge_ratio_max=float(edge.max()),
                         ref_ratio_p10=lo, ref_ratio_p90=hi, ref_ratio_mean=float(nat.mean()),
                         band_rows_left=n_band, pass_trace=bool(n_band == 0),
                         pass_ref=bool(lo - BAND_QC_REF_DIFF <= em <= hi + BAND_QC_REF_DIFF))
    return res


# ------------------------------------------------------------------ ink katmani (uretim adimi icin)
def ink_layer_mask(poster, ed, tol=70):
    """Posterden (7200x9600) YALNIZ cifte ozel murekkep: sembol + glifler + isimler (+ ∞,
    KEEP_INFINITY=False). Halka ve tagline alinmaz. Halka cizgisi posterin kendisinden:
    RING_ELLIPSE bandi (cizgi 15 px + 2*15 px) disinda. Donus: uint8 maske (1 = murekkep)."""
    r, g, b = INK_RGB[ed]
    Lu = luma(poster); L = Lu.astype(np.float32)
    dist = np.sqrt(((poster.astype(np.float32) - np.array([b, g, r], np.float32)) ** 2).sum(axis=2))
    t = otsu_thresh(Lu)
    core = (((L > t) if ed in DARK else (L < t)) & (dist < tol)).astype(np.uint8)
    boxes = np.zeros(Lu.shape, np.uint8)
    for (x0, y0, x1, y1) in ELEMENT_BOXES:
        boxes[y0:y1 + 1, x0:x1 + 1] = 1
    ring = np.zeros_like(core)
    cx, cy, ax, ay = RING_ELLIPSE
    cv2.ellipse(ring, (int(cx), int(cy)), (int(ax), int(ay)), 0, 0, 360, 1, int(RING_LINE_PX) + 2 * 5 * RING_BAND, cv2.LINE_8)
    ring[RING_TIP_Y + 1:, :] = 0
    out = ((core & boxes) & (ring == 0)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(out)          # kucuk benekler (yanik kenar gozenekleri) atilir
    small = np.zeros(n, bool); small[1:] = st[1:, cv2.CC_STAT_AREA] < 750
    out = (out & ~small[lab]).astype(np.uint8)
    # posterin kendi ∞ logosu (isim satirinda, bbox ~620x190 poster px; harfler ~270 px yuksek) alinmaz:
    # pilotun ∞'si kalir. Konumu cifte gore kayar (olcum: merkez 2890..3812).
    x0, y0, x1, y1 = BOX_NAMES
    row = np.zeros_like(out); row[y0:y1 + 1, x0:x1 + 1] = 1
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(out & row, np.ones((15, 15), np.uint8)))
    for i in range(1, n):
        x, y, w, h = st[i, :4]
        if 500 <= w <= 760 and 140 <= h <= 240:
            out[y:y + h, x:x + w] = 0
    return out


# ------------------------------------------------------------------ QC
def hf_ratio(img, mask, ring):
    g = luma(img).astype(np.float32)
    hp = g - cv2.GaussianBlur(g, (0, 0), 4.0)
    si, so = float(hp[mask > 0].std()), float(hp[ring > 0].std())
    return si, so, (si / so if so > 0 else float("nan"))


def qc_points(dev, ink, band, shape):
    """Kesit merkezleri (tuval px): sembol merkezi (halka kutusundaki murekkebin agirlik
    merkezi), isim bolgesi (isim kutusu merkezi; tuval disindaysa sembolun en alt noktasi),
    halka kesisimi (murekkep+2 px ile halka bandinin en buyuk kesisim bileseni)."""
    H, W = shape[:2]
    sym_box = box_mask(shape, dev, [BOX_SYMBOL])
    ys, xs = np.nonzero(ink & sym_box)
    pts = []
    if len(xs):
        pts.append(("sembol", (float(xs.mean()), float(ys.mean()))))
    else:
        pts.append(("sembol", poster_to_canvas(dev, 3600, 3500)))
    nx, ny = poster_to_canvas(dev, (BOX_NAMES[0] + BOX_NAMES[2]) / 2, (BOX_NAMES[1] + BOX_NAMES[3]) / 2)
    if 0 <= ny < H:
        pts.append(("isimler", (nx, ny)))
    elif len(xs):
        j = int(np.argmax(ys)); pts.append(("sembol-alt (isimler tuval disi)", (float(xs[j]), float(ys[j]))))
    else:
        pts.append(("isimler (tuval disi)", (nx, min(ny, H - 1))))
    cross = (cv2.dilate(ink, np.ones((5, 5), np.uint8)) & band).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(cross)
    if n > 1:
        i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        pts.append(("halka kesisimi", (float(cen[i][0]), float(cen[i][1]))))
    else:
        pts.append(("halka (kesisim yok)", poster_to_canvas(dev, REF_RING[0] + 150, (REF_RING[1] + REF_RING[3]) / 2)))
    return pts


def qc_sheet(pilot, plate, dev, pts, path, side=600):
    """Sol: kucultulmus pilot + plaka. Sag: her kesit icin pilot | plaka | fark x4 (1:1)."""
    H, W = plate.shape[:2]
    side = min(side, H, W)
    small_w = 420
    sp = cv2.resize(pilot, (small_w, int(small_w * H / W)), interpolation=cv2.INTER_AREA)
    sq = cv2.resize(plate, (small_w, int(small_w * H / W)), interpolation=cv2.INTER_AREA)
    rows = []
    for name, (cx, cy) in pts:
        x0 = int(np.clip(cx - side // 2, 0, W - side)); y0 = int(np.clip(cy - side // 2, 0, H - side))
        pc = pilot[y0:y0 + side, x0:x0 + side]; qc = plate[y0:y0 + side, x0:x0 + side]
        d = np.abs(pc.astype(np.int16) - qc.astype(np.int16)).max(axis=2)
        dv = cv2.applyColorMap(np.clip(d * 4, 0, 255).astype(np.uint8), cv2.COLORMAP_JET)
        row = np.full((side + 40, 3 * side, 3), 40, np.uint8)
        row[40:, :side] = pc; row[40:, side:2 * side] = qc; row[40:, 2 * side:] = dv
        cv2.putText(row, f"{name}  1:1 @({x0},{y0})   pilot | plaka | fark x4 (maks {int(d.max())})", (8, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        rows.append(row)
    right = np.vstack(rows)
    left = np.full((right.shape[0], small_w + 20, 3), 40, np.uint8)
    hh = min(sp.shape[0], (right.shape[0] - 60) // 2)
    left[40:40 + hh, 10:10 + small_w] = sp[:hh]
    y2 = 40 + hh + 20
    h2 = min(hh, right.shape[0] - y2)
    left[y2:y2 + h2, 10:10 + small_w] = sq[:h2]
    cv2.putText(left, "pilot", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(left, "plaka", (10, y2 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(path), np.hstack([left, right]), [cv2.IMWRITE_JPEG_QUALITY, 92])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", required=True, choices=EDITIONS)
    ap.add_argument("--posters", required=True, help="bu edisyonun 78 OPTIMIZED 3X4 posteri")
    ap.add_argument("--pilot", required=True, help="FINAL_V2/CANCER_LIBRA")
    ap.add_argument("--pilot-pair", default="Cancer_Libra")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-posters", type=int, default=40)
    ap.add_argument("--devices", default="Phone,Tablet,Desktop,Watch")
    ap.add_argument("--median-in", default="", help="hazir MEDIAN_<ED>.png (varsa medyan yeniden hesaplanmaz)")
    a = ap.parse_args()
    ed = a.edition
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); (out / "qc").mkdir(exist_ok=True)
    posters = sorted(Path(a.posters).glob(f"WA_POSTER_*_{ed.upper()}_3X4.jpg"))
    log(f"{ed}: {len(posters)} poster")
    t0 = time.time()
    med_path = out / f"MEDIAN_{ed.upper()}.png"
    if a.median_in and Path(a.median_in).exists():
        median = imread(a.median_in); log(f"medyan okundu: {a.median_in}")
    else:
        if len(posters) < a.min_posters:
            raise SystemExit(f"HATA: {len(posters)} poster (>= {a.min_posters} beklenir)")
        median = poster_median_fullres([str(p) for p in posters])
        cv2.imwrite(str(med_path), median, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        log(f"medyan yazildi: {med_path.name} ({time.time() - t0:.0f}s)")
    mq_px, mq_comps, mq_vis = median_ink_qc(median, ed)
    cv2.imwrite(str(out / "qc" / f"MEDIAN_{ed.upper()}_qc.jpg"), mq_vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
    log(f"medyan QC: eleman kutularinda murekkep {mq_px} px, {len(mq_comps)} bilesen (beklenen 0)")
    med = device_medians_from(median)
    median_full = median            # bant dolgusu (cover) icin tam cozunurluk medyan
    report = {}
    for dev in a.devices.split(","):
        pilot = imread(Path(a.pilot) / f"AstroLove_{a.pilot_pair}_{ed}_{dev}.jpg")
        W, H = DEVICES[dev]
        if pilot.shape[1] != W or pilot.shape[0] != H:
            raise SystemExit(f"HATA: pilot {dev} {pilot.shape[1]}x{pilot.shape[0]}")
        plate, mask, ink, ring, band, info = build_plate(pilot, med[dev], ed, dev)
        ink_mask = mask.copy()
        # dikey cizgili bant (Phone/Tablet ust-alt): tespit -> bant satirlarini kirp + LANCZOS dikey olcek
        bq = {}; geom = dict(crop_top=0, crop_bot=0, scale_y=1.0)
        pilot_ref = pilot
        if dev in BAND_DEVICES:
            btop, bbot, _ = band_detect(pilot)
            if btop > 0 or bbot > 0:
                geom = band_crop_geom(H, btop, bbot)
                plate = apply_geom(plate, geom)
                pilot_ref = apply_geom(pilot, geom)
                mask = (apply_geom(mask * 255, geom, cv2.INTER_LINEAR) > 0).astype(np.uint8)
                mask = cv2.dilate(mask, np.ones((9, 9), np.uint8))          # LANCZOS 4 px komsuluk
                ink = (apply_geom(ink * 255, geom, cv2.INTER_LINEAR) > 127).astype(np.uint8)
                band = (apply_geom(band * 255, geom, cv2.INTER_LINEAR) > 127).astype(np.uint8)
                ring = (apply_geom((ring * 255).astype(np.uint8), geom, cv2.INTER_LINEAR) > 127).astype(np.float32)
                bq = band_crop_qc(plate, pilot, btop, bbot)
                bq_pass = all(v["pass_trace"] and v["pass_ref"] for v in bq.values())
                log(f"  {dev:8s} bant ust {btop} px / alt {bbot} px -> kirp {geom['crop_top']}/{geom['crop_bot']} px, scale_y {geom['scale_y']:.4f} | " + ", ".join(
                    f"{k}: kenar oran {v['edge_ratio_mean']:.2f} (dogal p10-p90 {v['ref_ratio_p10']:.2f}-{v['ref_ratio_p90']:.2f}, oran>3 satir {v['band_rows_left']})" for k, v in bq.items()) + f" | {'PASS' if bq_pass else 'FAIL'}")
            else:
                log(f"  {dev:8s} bant yok (ust 0 / alt 0)")
        (out / f"GEOM_{ed.upper()}_{dev.upper()}.json").write_text(json.dumps(geom))
        diff = np.abs(plate.astype(np.int16) - pilot_ref.astype(np.int16))
        outside = float(diff[mask == 0].max()) if (mask == 0).any() else 0.0
        band_diff = float(diff[band > 0].max()) if (band > 0).any() else 0.0
        if geom["scale_y"] != 1.0:
            ink_mask = (apply_geom(ink_mask * 255, geom, cv2.INTER_LINEAR) > 127).astype(np.uint8)
        si, so, r = hf_ratio(plate, ink_mask, ring)       # hayalet HF orani yalniz murekkep dolgusu icin
        name = f"PLATE_{ed.upper()}_{dev.upper()}.png"
        cv2.imwrite(str(out / name), plate, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        cv2.imwrite(str(out / "qc" / f"MASK_{ed.upper()}_{dev.upper()}.png"), mask * 255)
        pts = qc_points(dev, ink, band, plate.shape)
        if dev in BAND_DEVICES:
            pts += [("ust kenar", (W / 2, 300)), ("alt kenar", (W / 2, H - 300))]
        qc_sheet(pilot_ref, plate, dev, pts, out / "qc" / f"PLATE_{ed.upper()}_{dev.upper()}.jpg")
        report[dev] = dict(file=name, size=[W, H], outside_max_diff=outside, ring_band_max_diff=band_diff,
                           hf_inside=si, hf_ring=so, hf_ratio=r, qc_points={k: [round(x), round(y)] for k, (x, y) in pts}, band=bq, geom=geom, **info)
        log(f"  {dev:8s} maske {info['mask_px']} px (murekkep {info['ink_px']}, otsu {info['otsu']:.0f}, halka bandi {info['ring_band_px']}, kesisim {info['ring_cross_px']}) | maske disi maks fark {outside:.0f} (halka {band_diff:.0f}) | HF ic/halka {si:.2f}/{so:.2f} = {r:.2f}")
    (out / f"report_{ed}.json").write_text(json.dumps(dict(edition=ed, posters=len(posters), median_file=med_path.name,
                                                             median_ink_px=mq_px, median_ink_components=mq_comps, devices=report), indent=1))
    log(f"toplam {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
