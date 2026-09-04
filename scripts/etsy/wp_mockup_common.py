#!/usr/bin/env python3
"""
wp-mockup hatti - ortak parcalar (docs/WP_MOCKUP_PIPELINE.md).

Sahne masteri = pilot (Cancer_Libra) galeri mockup'inin kendisi. Pilot
ekranlarinin FINAL_V2 wallpaper'larin BIREBIR perspektif yerlesimi oldugu
olculdu (SET01: ic fark 1.5/255, uyum 0.4 px, aydinlatma orani 1.00). Bu
yuzden yeni bir cift icin ekran icerigi su formulle degistirilir:

  paste modu  : out = M*warp(yeni) + (1-M)*master, M = kalibre yumusak
                ekran maskesi (yuvarlak kose, cerceve, Dynamic Island disarida).
                Telefon/tablet/masaustu. Edisyon degisiminde (SET04 = SET01
                sahnesi, MB->DB, CI->WP) maske 1 px genisletilir.
  relight modu: dortgen icinde out = master + warp(yeni) - warp(pilot)
                (zemin/grain aynen), pilot murekkebinin komsulugunda
                out = warp(yeni) + L, L = murekkep disi alcak gecirgen
                (master - warp(pilot)). Kadranda parlama olan ve pilot
                sembolu kaynakla birebir olmayan Watch icin.
  diff modu   : out = master + warp(yeni) - warp(pilot); ince cizgide
                alt-piksel orneklem farki (13-36/255) hayalet biraktigi
                icin otomatik secilmez.

Ekran dortgeni: SIFT + RANSAC homografi (wallpaper -> master). Saat icin
SIFT yetersiz (15 eslesme); yuksek gecirgen sablon eslestirme (kaba 0.005,
ince 0.0005 olcek adimi, 4x alt-piksel) kullanilir.
"""
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

EDITIONS = ["Midnight_Blue", "Deep_Black", "Champagne_Ivory", "Warm_Parchment"]
DEVICES = {"Phone": (1440, 3200), "Tablet": (2048, 2732), "Desktop": (3840, 2160), "Watch": (1000, 1220)}
OUT_W, OUT_H = 3000, 2250

# Sahne tanimi (B93 mockup haritasi + pilot dosyalari). master = pilot FINAL
# dosyasi; expect = beklenen ekran sayisi (cihaz -> adet); edition_map =
# render'da edisyon degisimi (x'e gore soldan saga sirali ekranlar).
SCENES = {
    "SET01": dict(master="WA_MOCKUP_V2_SET01_Cancer_Libra_FINAL.jpg", expect={"Phone": 2}),
    "SET03": dict(master="WA_MOCKUP_V2_SET03_Cancer_Libra_FINAL.jpg", expect={"Phone": 4}),
    # SET04: 2 Eyl 2026 onayli 3000x2250 master (SET01 sahnesinden DB+WP ile
    # uretildi, Etsy rank 3'e yuklendi; 2048 dosya ARCHIVE'da). Kendi masteri.
    "SET04": dict(master="WA_MOCKUP_V2_SET04_Cancer_Libra_FINAL.jpg", expect={"Phone": 2}),
    "SET06": dict(master="WA_MOCKUP_V2_SET06_Cancer_Libra_FINAL.jpg", expect={"Desktop": 2, "Tablet": 1}),
    "SET07": dict(master="WA_MOCKUP_V2_SET07_Cancer_Libra_FINAL.jpg", expect={"Phone": 1, "Watch": 1}),
    "SET10Y": dict(master="WA_MOCKUP_V2_SET10_YAZILI_Cancer_Libra_FINAL.jpg", expect={"Phone": 1},
                   out_name="WA_MOCKUP_V2_SET10_YAZILI_{pair}_FINAL.jpg"),
}
GALLERY_ORDER = ["SET01", "SET03", "SET04", "SET06", "SET07", "SET10Y"]

JPEG_QUALITY = 95

# 4 Eyl 2026: kucultme yolu. "mevcut" = ~2x hedef olcege INTER_AREA on-indirme +
# INTER_CUBIC perspektif; "lanczos" = on-indirme yok, dogrudan INTER_LANCZOS4
# (olcum: SET07 saat halesi 13.68 -> 10.77; kaynak 5.03).
WARP_MODE = "mevcut"


def set_warp_mode(m):
    global WARP_MODE
    if m not in ("mevcut", "lanczos"):
        raise SystemExit(f"bilinmeyen warp yontemi {m}")
    WARP_MODE = m


def log(msg):
    print(msg, flush=True)


# ------------------------------------------------------------------ IO
def imread(path):
    im = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if im is None:
        raise FileNotFoundError(path)
    return im


def imwrite_jpeg(path, bgr):
    """3000x2250, sRGB, kalite 95, 4:4:4, baseline, 300 dpi."""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb).save(str(path), "JPEG", quality=JPEG_QUALITY, subsampling=0,
                              optimize=True, progressive=False, dpi=(300, 300))


def wallpaper_name(pair, edition, device):
    return f"AstroLove_{pair}_{edition}_{device}.jpg"


def load_wallpapers(wp_dir, pair):
    """{(edition, device): bgr} - bulunan dosyalar; boyut dogrulanir."""
    out = {}
    for ed in EDITIONS:
        for dev, (w, h) in DEVICES.items():
            p = Path(wp_dir) / wallpaper_name(pair, ed, dev)
            if p.exists():
                im = imread(p)
                if im.shape[1] != w or im.shape[0] != h:
                    raise SystemExit(f"HATA: {p.name} boyutu {im.shape[1]}x{im.shape[0]}, beklenen {w}x{h}")
                out[(ed, dev)] = im
    return out


# ------------------------------------------------------------------ geometri
def quad_of(H, w, h):
    c = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(c, np.asarray(H, np.float64)).reshape(-1, 2)


def quad_scale(quad, w):
    return float(np.linalg.norm(quad[1] - quad[0]) / w)


def poly_mask(shape, quad, value=255):
    m = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(m, [np.round(quad).astype(np.int32)], value)
    return m


def poly_mask_aa(shape, quad):
    """Kenari yumusatilmis (4x ornekleme) 0..1 poligon maskesi."""
    U = 4
    m = np.zeros((shape[0] * U, shape[1] * U), np.uint8)
    cv2.fillPoly(m, [np.round(np.asarray(quad) * U).astype(np.int32)], 255)
    return cv2.resize(m, (shape[1], shape[0]), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


def center_inside(qa, qb):
    """qa'nin merkezi qb icinde mi (ayni ekranin farkli cihaz/edisyon adaylari)."""
    c = np.asarray(qa, np.float32).mean(axis=0)
    return cv2.pointPolygonTest(np.asarray(qb, np.float32).reshape(-1, 1, 2), (float(c[0]), float(c[1])), False) >= 0


def iou(qa, qb, shape):
    a = poly_mask(shape, qa) > 0
    b = poly_mask(shape, qb) > 0
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


def warp_full(wp, H, shape, scale):
    """Wallpaper'i master tuvaline tasir. Once ~2x hedef olcege INTER_AREA ile
    indirir (orneklem hatasi/merdivenlenme onlemi), sonra kubik perspektif.
    Ayni (wp boyutu, olcek) icin deterministiktir: diff modunda warp(yeni) ve
    warp(pilot) birebir ayni yolu izler."""
    H0, W0 = wp.shape[:2]
    f = max(1.0, 1.0 / (scale * 2.0))
    pre = cv2.resize(wp, (max(1, int(round(W0 / f))), max(1, int(round(H0 / f)))), interpolation=cv2.INTER_AREA)
    S = np.diag([W0 / pre.shape[1], H0 / pre.shape[0], 1.0])
    return cv2.warpPerspective(pre, np.asarray(H, np.float64) @ S, (shape[1], shape[0]),
                               flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)


def aspect_of_quad(quad):
    """Dortgenin en/boy orani (ust+alt kenar ortalamasi / sol+sag kenar ortalamasi)."""
    q = np.asarray(quad, np.float32)
    top, bottom = np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[3])
    left, right = np.linalg.norm(q[3] - q[0]), np.linalg.norm(q[2] - q[1])
    h = (left + right) / 2
    return (top + bottom) / 2 / h if h else 0.0


def cover_src_rect(W0, H0, target_aspect):
    """Kaynagin (W0xH0) hedef orana esit, ORTALANMIS, en buyuk alt-dikdortgeni
    ("cover"/crop-to-fill): kaynak hedeften genisse yanlardan, darsa ust-alttan
    kirpilir. Donus: 4 kose (orijinal piksel koord., quad_of ile ayni sira:
    TL,TR,BR,BL)."""
    src_aspect = W0 / H0
    if src_aspect > target_aspect:
        w = max(1, int(round(H0 * target_aspect)))
        x0 = (W0 - w) // 2
        return np.float32([[x0, 0], [x0 + w, 0], [x0 + w, H0], [x0, H0]])
    h = max(1, int(round(W0 / target_aspect)))
    y0 = (H0 - h) // 2
    return np.float32([[0, y0], [W0, y0], [W0, y0 + h], [0, y0 + h]])


def cover_homography(wp_shape, quad):
    """quad'in olculen orani ile eslesen, kaynagin ORTALANMIS alt-dikdortgenini
    (cover_src_rect) DOGRUDAN quad'in 4 kosesine esler (stretch yok, quad
    DEGISMEZ). Donus: (Hc, src_rect)."""
    H0, W0 = wp_shape[:2]
    src = cover_src_rect(W0, H0, aspect_of_quad(quad))
    return cv2.getPerspectiveTransform(src, np.asarray(quad, np.float32)), src


def warp_cover(wp, quad, shape, yontem=None):
    """warp_full'un stretch-to-fill'i YERINE: kaynagin TAMAMINI degil, quad
    orani ile eslesen ORTALANMIS bir alt-bolgesini (cover_homography) quad'a
    esler - dairesel/simetrik desenler orani BOZULMADAN (crop-to-fill) yerlesir.
    Ayni alt-piksel-orneklem onlemi (once ~2x hedef olcege INTER_AREA).
    yontem="lanczos": on-indirme yok, dogrudan INTER_LANCZOS4."""
    H0, W0 = wp.shape[:2]
    Hc, src = cover_homography(wp.shape, quad)
    if (yontem or WARP_MODE) == "lanczos":
        return cv2.warpPerspective(wp, Hc.astype(np.float64), (shape[1], shape[0]),
                                   flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT)
    crop_w = float(src[1][0] - src[0][0])
    scale = quad_scale(quad, crop_w)
    f = max(1.0, 1.0 / (scale * 2.0))
    pre = cv2.resize(wp, (max(1, int(round(W0 / f))), max(1, int(round(H0 / f)))), interpolation=cv2.INTER_AREA)
    S = np.diag([W0 / pre.shape[1], H0 / pre.shape[0], 1.0])
    return cv2.warpPerspective(pre, Hc.astype(np.float64) @ S, (shape[1], shape[0]),
                               flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)


def warp_mask(mask_u8, H, shape):
    return cv2.warpPerspective(mask_u8, np.asarray(H, np.float64), (shape[1], shape[0]), flags=cv2.INTER_NEAREST)


def highpass(gray, sigma=6.0):
    g = gray.astype(np.float32)
    return g - cv2.GaussianBlur(g, (0, 0), sigma)


def ink_mask(wp):
    """Wallpaper murekkep maskesi (V2 yontemi: yuksek gecirgen + esik).
    Polarite orta banttan: acik kagit -> koyu murekkep, koyu zemin -> acik."""
    g = cv2.cvtColor(wp, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = g.shape
    paper = float(np.median(g[h // 4:3 * h // 4, w // 4:3 * w // 4]))
    small = cv2.resize(g, (max(1, w // 8), max(1, h // 8)), interpolation=cv2.INTER_AREA)
    k = max(5, (int(min(small.shape) * 0.09) // 2) * 2 + 1)
    bg = cv2.medianBlur(np.clip(small, 0, 255).astype(np.uint8), k).astype(np.float32)
    bg = cv2.resize(bg, (w, h), interpolation=cv2.INTER_LINEAR)
    d = (bg - g) if paper > 128 else (g - bg)
    m = (d > 25).astype(np.uint8) * 255
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


# ------------------------------------------------------------------ tespit: SIFT
class MasterFeatures:
    """Master'in SIFT ozellikleri bir kez cikarilir; dislama maskesi
    anahtar nokta konumuna gore uygulanir (her aramada yeniden hesaplanmaz)."""

    def __init__(self, gray, nfeatures=12000):
        self.gray = gray
        self.sift = cv2.SIFT_create(nfeatures=nfeatures)
        self.kp, self.desc = self.sift.detectAndCompute(gray, None)
        self.pts = np.float32([k.pt for k in self.kp]) if self.kp else np.zeros((0, 2), np.float32)

    def subset(self, mask):
        if mask is None:
            return self.pts, self.desc
        ix = np.round(self.pts).astype(int)
        keep = mask[np.clip(ix[:, 1], 0, mask.shape[0] - 1), np.clip(ix[:, 0], 0, mask.shape[1] - 1)] > 0
        return self.pts[keep], (self.desc[keep] if self.desc is not None else None)


def sift_matches(master, wp, exclude=None, work_h=1200):
    """Wallpaper -> master iyi eslesmeler (oran testi 0.75). Donus: (p1, p2, master)
    p1 wallpaper pikseli, p2 master pikseli."""
    if not isinstance(master, MasterFeatures):
        master = MasterFeatures(master)
    H0, W0 = wp.shape[:2]
    s = work_h / H0
    wps = cv2.resize(wp, (int(W0 * s), int(H0 * s)), interpolation=cv2.INTER_AREA)
    k1, d1 = master.sift.detectAndCompute(cv2.cvtColor(wps, cv2.COLOR_BGR2GRAY), None)
    mask = np.full(master.gray.shape, 255, np.uint8)
    if exclude is not None:
        mask[exclude > 0] = 0
    p2all, d2 = master.subset(mask)
    if d1 is None or len(k1) < 10 or d2 is None or len(p2all) < 10:
        return np.zeros((0, 2), np.float32), np.zeros((0, 2), np.float32), master
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(d1, d2, k=2)
    good = [a for a, b in (p for p in pairs if len(p) == 2) if a.distance < 0.75 * b.distance]
    p1 = np.float32([k1[a.queryIdx].pt for a in good]) / s
    p2 = np.float32([p2all[a.trainIdx] for a in good])
    return p1, p2, master


def sift_candidates(master, wp, exclude=None, max_n=6, min_inl=25, work_h=1200):
    """Wallpaper'in master icindeki tum orneklerini bulur (bulunani maskeleyip
    tekrar arar). master: MasterFeatures veya gri goruntu.
    Donus: [dict(H, quad, inliers, rms)]."""
    if not isinstance(master, MasterFeatures):
        master = MasterFeatures(master)
    H0, W0 = wp.shape[:2]
    mask = np.full(master.gray.shape, 255, np.uint8)
    if exclude is not None:
        mask[exclude > 0] = 0
    out = []
    for _ in range(max_n):
        p1, p2, _ = sift_matches(master, wp, exclude=(mask == 0).astype(np.uint8), work_h=work_h)
        if len(p1) < min_inl:
            break
        H, inl = cv2.findHomography(p1, p2, cv2.RANSAC, 3.0)
        n = int(inl.sum()) if inl is not None else 0
        if H is None or n < min_inl:
            break
        sel = inl.ravel() == 1
        proj = cv2.perspectiveTransform(p1[sel].reshape(-1, 1, 2), H).reshape(-1, 2)
        err = np.linalg.norm(proj - p2[sel], axis=1)
        quad = quad_of(H, W0, H0)
        if not cv2.isContourConvex(np.round(quad).astype(np.int32)) or quad_scale(quad, W0) < 0.02:
            break
        out.append(dict(H=H, quad=quad, inliers=n, rms=float(np.sqrt((err ** 2).mean()))))
        cv2.fillPoly(mask, [np.round(quad).astype(np.int32)], 0)
    return out


# ------------------------------------------------------------------ tespit: sablon (saat)
def template_candidate(master_gray, wp, roi=None, s_lo=0.15, s_hi=0.45):
    """Olcek+oteleme araması (yuksek gecirgen, TM_CCOEFF_NORMED). Kaba adim
    0.005; ince adim 0.0005 ve 4x alt-piksel. Donus dict(H, quad, corr, scale)."""
    H0, W0 = wp.shape[:2]
    gw = cv2.cvtColor(wp, cv2.COLOR_BGR2GRAY)
    x0, y0 = 0, 0
    gm = master_gray
    if roi is not None:
        x0, y0, x1, y1 = roi
        gm = master_gray[y0:y1, x0:x1]
    gmh = highpass(gm)
    best = None
    for s in np.arange(s_lo, s_hi, 0.005):
        t = cv2.resize(gw, (int(round(W0 * s)), int(round(H0 * s))), interpolation=cv2.INTER_AREA)
        if t.shape[0] >= gmh.shape[0] or t.shape[1] >= gmh.shape[1]:
            continue
        r = cv2.matchTemplate(gmh, highpass(t), cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        if best is None or mx > best[0]:
            best = (mx, s, loc)
    if best is None:
        return None
    mx, s0, (lx, ly) = best
    # ince: ROI'yi 4x buyut, olcek +-0.005 / 0.0005 adim
    U = 4
    pad = int(W0 * s0 * 0.15) + 8
    rx0, ry0 = max(0, lx - pad), max(0, ly - pad)
    rx1, ry1 = min(gmh.shape[1], lx + int(W0 * s0) + pad), min(gmh.shape[0], ly + int(H0 * s0) + pad)
    sub = cv2.resize(gmh[ry0:ry1, rx0:rx1], None, fx=U, fy=U, interpolation=cv2.INTER_CUBIC)
    fine = None
    for s in np.arange(s0 - 0.005, s0 + 0.0051, 0.0005):
        t = cv2.resize(gw, (int(round(W0 * s * U)), int(round(H0 * s * U))), interpolation=cv2.INTER_AREA)
        if t.shape[0] >= sub.shape[0] or t.shape[1] >= sub.shape[1]:
            continue
        r = cv2.matchTemplate(sub, highpass(t, 6.0 * U), cv2.TM_CCOEFF_NORMED)
        _, m2, _, l2 = cv2.minMaxLoc(r)
        if fine is None or m2 > fine[0]:
            fine = (m2, s, l2)
    if fine is None:
        return None
    corr, s, (fx, fy) = fine
    tx, ty = x0 + rx0 + fx / U, y0 + ry0 + fy / U
    H = np.array([[s, 0, tx], [0, s, ty], [0, 0, 1]], np.float64)
    return dict(H=H, quad=quad_of(H, W0, H0), corr=float(corr), scale=float(s), inliers=0, rms=0.0)


# ------------------------------------------------------------------ olcum
def screen_metrics(master, wp, H, ink=None):
    """Master ile warp(wp) farki: ekran ici (15 px erozyon), murekkep ustu,
    murekkep disi uzak, aydinlatma orani. Tumu 0-255 birim."""
    H0, W0 = wp.shape[:2]
    quad = quad_of(H, W0, H0)
    sc = quad_scale(quad, W0)
    w = warp_full(wp, H, master.shape, sc)
    inq = poly_mask(master.shape, quad)
    er = cv2.erode(inq, np.ones((15, 15), np.uint8)) > 0
    d = np.abs(master.astype(np.float32) - w.astype(np.float32)).mean(axis=2)
    out = dict(inside_mean=float(d[er].mean()), inside_p95=float(np.percentile(d[er], 95)))
    if ink is None:
        ink = ink_mask(wp)
    inkw = warp_mask(ink, H, master.shape) > 0
    near = cv2.dilate(inkw.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    far = (cv2.dilate(inkw.astype(np.uint8), np.ones((41, 41), np.uint8)) == 0) & er
    gm = cv2.cvtColor(master, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gw = cv2.cvtColor(w, cv2.COLOR_BGR2GRAY).astype(np.float32)
    out.update(ink_mean=float(d[inkw & er].mean()) if (inkw & er).any() else None,
               near_ink_mean=float(d[near & er].mean()) if (near & er).any() else None,
               bg_far_mean=float(d[far].mean()) if far.any() else None,
               luma_ratio_p50=float(np.median((gm[er] + 1) / (gw[er] + 1))),
               luma_ratio_p95=float(np.percentile((gm[er] + 1) / (gw[er] + 1), 95)))
    return out, w, quad


def screen_soft_mask(master, warped_pilot, quad, ink_w=None, thresh=10.0, hole_max=1500):
    """Paste modu maskesi: dortgen icinde master ~ warp(pilot) olan piksel.
    Yuvarlak kose, cerceve, Dynamic Island (>hole_max px^2 delik) DISARIDA;
    doku kaynakli kucuk delikler (<= hole_max) doldurulur. Yumusak 0..1.
    Donus: (maske, kalite = maske/dortgen, buyuk delikler [(alan,x,y,w,h)])."""
    d = np.abs(master.astype(np.float32) - warped_pilot.astype(np.float32)).mean(axis=2)
    if ink_w is not None:   # pilot murekkebi (ince cizgi orneklem farki) delik sayilmaz
        d[cv2.dilate(ink_w, np.ones((9, 9), np.uint8)) > 0] = 0.0
    d = cv2.blur(d, (5, 5))
    inq = poly_mask(master.shape, quad)
    m = ((d < thresh) & (inq > 0)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        m = (lab == k).astype(np.uint8) * 255
    # delikler: maske disi ama dortgen ici bilesenler
    holes = ((m == 0) & (inq > 0)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(holes)
    big = []
    border = cv2.dilate(inq, np.ones((3, 3), np.uint8)) - cv2.erode(inq, np.ones((3, 3), np.uint8))
    for i in range(1, n):
        a = int(st[i, cv2.CC_STAT_AREA])
        touches = bool((border[lab == i] > 0).any())
        if a <= hole_max and not touches:
            m[lab == i] = 255
        else:
            big.append((a, int(st[i, cv2.CC_STAT_LEFT]), int(st[i, cv2.CC_STAT_TOP]),
                        int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])))
    soft = cv2.GaussianBlur(m.astype(np.float32) / 255.0, (0, 0), 0.8)
    quality = float(m.sum() / 255 / max(1, inq.sum() / 255))
    big = [b for b in big if not (b[3] > 0.9 * (np.asarray(quad)[:, 0].max() - np.asarray(quad)[:, 0].min()))]
    return soft, quality, sorted(big, reverse=True)[:8]


def corner_radius(mask_u8, quad, scale):
    """Kose yuvarlamasi tahmini: kose 80x80 karesinde eksik piksel ->
    r = sqrt(eksik / (1 - pi/4)); wallpaper pikseli cinsinden."""
    q = np.round(quad).astype(int)
    x0, y0 = q.min(0)
    x1, y1 = q.max(0)
    out = {}
    for nm, (ys, xs) in {"TL": (slice(y0, y0 + 80), slice(x0, x0 + 80)), "TR": (slice(y0, y0 + 80), slice(x1 - 80, x1)),
                         "BL": (slice(y1 - 80, y1), slice(x0, x0 + 80)), "BR": (slice(y1 - 80, y1), slice(x1 - 80, x1))}.items():
        miss = 80 * 80 - mask_u8[ys, xs].sum() / 255.0
        r = math.sqrt(max(0.0, miss) / (1 - math.pi / 4))
        out[nm] = round(r / scale, 1)
    return out


# ------------------------------------------------------------------ render
def relight_layer(master, warped_pilot, quad, ink_w, sigma=6.0):
    """L = murekkep disi normalize alcak gecirgen (master - warp(pilot))."""
    d = master.astype(np.float32) - warped_pilot.astype(np.float32)
    w = (poly_mask(master.shape, quad) > 0).astype(np.float32)
    w[cv2.dilate(ink_w, np.ones((7, 7), np.uint8)) > 0] = 0.0
    num = cv2.GaussianBlur(d * w[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(w, (0, 0), sigma)[..., None]
    return num / np.maximum(den, 1e-3)


def render_screen(out, master, screen, wp_new, wp_pilot, mode, soft_mask=None, edition_swap=False):
    """Tek ekrani out uzerine isler (out float32, yerinde).
    paste  : M = kalibre yumusak maske (edisyon degisiminde 1 px genisletilir:
             kenar yumusatma pikseli eski edisyon rengini tasimasin);
             out = M*warp(yeni) + (1-M)*out
    relight: diff + eski murekkep yamasi. Dortgen icinde
             out = out + (warp(yeni) - warp(pilot))   [zemin/grain aynen kalir]
             ve pilot murekkebinin 6 px komsulugunda (yumusak yama P)
             out = (1-P)*out + P*(warp(yeni) + L),  L = murekkep disi alcak
             gecirgen (master - warp(pilot)).  Pilot ekrani kaynakla birebir
             degilse (saat) hayalet birakmaz, dikdortgen sinir olusturmaz.
    diff   : out = out + M*(warp(yeni) - warp(pilot))   (yalniz elle secim)

    NOT (3 Eyl 2026, SET06 ekran-2 halka-oval kusuru): kalibrasyonun olctugu
    quad DOGRU (SIFT/RANSAC), ama warp_full kaynagin TAMAMINI (orijinal
    wallpaper orani) quad'a stretch-to-fill esler - quad orani kaynaktan
    farkliysa (SET06 ekran-2: 1.536 vs kaynak 1.778) bu dairesel/simetrik
    desenleri oval'e gerer. Bu yuzden burada warp_cover (crop-to-fill,
    quad DEGISMEZ, kaynaktan ORTALANMIS kirpilir) kullanilir."""
    quad = np.asarray(screen["quad"], np.float32)
    w_new = warp_cover(wp_new, quad, master.shape).astype(np.float32)
    M = poly_mask_aa(master.shape, quad)[..., None]
    if mode == "paste":
        if soft_mask is None:
            raise SystemExit("paste modu icin maske gerekli")
        sm = soft_mask
        if edition_swap:
            hard = (sm > 0.5).astype(np.uint8)
            sm = cv2.GaussianBlur(cv2.dilate(hard, np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 0.8)
        Mp = sm[..., None] * M
        out[...] = (1 - Mp) * out + Mp * w_new
    elif mode == "relight":
        w_pil = warp_cover(wp_pilot, quad, master.shape).astype(np.float32)
        Hc_pilot, _ = cover_homography(wp_pilot.shape, quad)
        ink_w = warp_mask(ink_mask(wp_pilot), Hc_pilot, master.shape)
        L = relight_layer(master, w_pil, quad, ink_w)
        out[...] = out + M * (w_new - w_pil)
        P = cv2.GaussianBlur(cv2.dilate(ink_w, np.ones((13, 13), np.uint8)).astype(np.float32) / 255.0, (0, 0), 2.0)
        P = (P * M[..., 0])[..., None]
        out[...] = (1 - P) * out + P * (w_new + L)
    elif mode == "diff":
        w_pil = warp_cover(wp_pilot, quad, master.shape).astype(np.float32)
        out[...] = out + M * (w_new - w_pil)
    else:
        raise SystemExit(f"bilinmeyen mod {mode}")
    return mode


# ------------------------------------------------------------------ QC gorselleri
def qc_sheet(img, screens, path, crop=300):
    """Kucuk tam gorsel + ekran basina 4 kose ve merkez kesitleri (1:1)."""
    tiles = []
    for s in screens:
        q = np.asarray(s["quad"], np.float32)
        cx, cy = q.mean(axis=0)
        pts = [q[0], q[1], q[3], q[2], (cx, cy)]
        row = []
        for (x, y) in pts:
            x0 = int(np.clip(x - crop // 2, 0, img.shape[1] - crop))
            y0 = int(np.clip(y - crop // 2, 0, img.shape[0] - crop))
            row.append(img[y0:y0 + crop, x0:x0 + crop].copy())
        tiles.append(np.hstack(row))
    small = cv2.resize(img, (crop * 5, int(img.shape[0] * crop * 5 / img.shape[1])), interpolation=cv2.INTER_AREA)
    sheet = np.vstack([small] + tiles)
    cv2.imwrite(str(path), sheet, [cv2.IMWRITE_PNG_COMPRESSION, 6])


def to_jsonable(o):
    if isinstance(o, np.ndarray):
        return [to_jsonable(v) for v in o.tolist()]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, dict):
        return {k: to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    return o


def dump_json(obj, path):
    Path(path).write_text(json.dumps(to_jsonable(obj), indent=1, ensure_ascii=False))
