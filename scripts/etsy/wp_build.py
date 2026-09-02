#!/usr/bin/env python3
"""
wp-build: bir ciftin 16 wallpaper'ini (4 edisyon x Phone/Tablet/Desktop/Watch)
OPTIMIZED 3X4 posterlerden uretir. docs/WP_LAYOUT_SPEC.md bolum 7 kurallari.

OLCULEN GERCEKLER (2 Eyl, pilot Cancer_Libra):
- Ayni edisyonun posterleri AYNI zemini tasir (cift ciftler arasi zemin farki
  0.00-0.19/255); yalniz murekkep (sembol, glif, isim) degisir. Halka,
  tagline, "∞" sabittir.
- Pilot wallpaper = posterin afin yerlesimi (Phone 0.2000 y+640; Tablet
  0.2844 y+182; Desktop 0.2649 x+966 y-193) + zemine eklenen DUZ (alcak
  gecirgen) parlama/vinyet alani + poster disi bantlar. Poster bolgesinde
  zemin farki: DB 0.12, MB 1.0 (toplamsal model), CI 1.7; WP 6.4 (pilot WP
  dokusu posterin dokusuyla ayni ORNEK degil).
- Murekkep pilotta poster murekkebiyle aynidir (parlama eklenmez).

YONTEM (sablon + murekkep degisimi):
- Zemin sablonu: pilot wallpaper (cifte bagli olmayan her sey: bantlar,
  parlama, doku). Pilotun murekkep izleri (poster-BG farki > esik, 6 px
  genisletme) ayni dokudan KAYDIRMALI KOPYA ile doldurulur; alcak gecirgen
  fark duzeltilir. Sablonlar kalibrasyonda bir kez uretilir (TEMPLATES/).
- Edisyon zemin posteri BG = N cift posterinin (cihaz olceginde) MEDYANI
  (murekkep ciftten cifte farkli oldugu icin medyan zemini verir).
- Yeni cift: R = down(poster_yeni); alfa A = clip(|luma(R) - luma(BG)| / C, 0, 1)
  (C = edisyon murekkep kontrasti, olculur); out = T*(1-A) + R*A.
- Watch: yalniz fuzyon sembolu (halka icindeki bilesenler), olcek 0.2372,
  kutu merkezi (500, 610); sablon = pilot saat zemini.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from wp_mockup_common import DEVICES, EDITIONS, imread, log, template_candidate

# cihaz -> (olcek, poster boyutu (w,h), tuvalde x0, y0)  [WP_LAYOUT_SPEC 7.1]
PLACEMENT = {
    "Phone": dict(s=0.2000, size=(1440, 1920), x0=0, y0=640),
    "Tablet": dict(s=0.2844, size=(2048, 2730), x0=0, y0=182),
    "Desktop": dict(s=0.2649, size=(1907, 2543), x0=966, y0=-193),
}
WATCH = dict(s=0.2372, center=(500, 610), ring_box=(921, 1147, 6279, 4922))   # poster px
ED_UP = {e: e.upper() for e in EDITIONS}
JPEG_Q = 95


def poster_name(pair, ed):
    return f"WA_POSTER_{pair.upper()}_{ED_UP[ed]}_3X4.jpg"


def luma(bgr):
    return cv2.cvtColor(bgr.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32) if bgr.dtype != np.float32 else \
        (0.114 * bgr[..., 0] + 0.587 * bgr[..., 1] + 0.299 * bgr[..., 2])


def down(poster, size):
    return cv2.resize(poster, size, interpolation=cv2.INTER_AREA)


# ------------------------------------------------------------------ BG (edisyon zemini)
def edition_bg(posters, size, dark):
    """posters: list[bgr 7200x9600] ayni edisyon; zemin (cihaz olceginde).
    Murekkep koyu zeminde AYDINLIK, acik zeminde KOYU oldugu icin piksel
    basina 2. en dusuk (koyu edisyon) / 2. en yuksek (acik) lumali ornek
    alinir; medyan yerine bu, 6 posterin >=3'unde ustuste gelen sembol
    cizgilerinden etkilenmez. Donus: bg(float32), contamination(bool)."""
    R = np.stack([down(p, size).astype(np.float32) for p in posters])
    L = np.stack([luma(r) for r in R])
    order = np.argsort(L, axis=0)
    pick = order[1] if dark else order[-2]
    bg = np.take_along_axis(R, pick[None, ..., None], axis=0)[0]
    dl = np.abs(L - luma(bg)[None])
    contam = (dl > 20).sum(axis=0) >= len(posters) - 1
    return bg, contam


def ink_contrast(R, bg):
    """Edisyon murekkep kontrasti C: |luma(R)-luma(bg)| > 20 olan piksellerin p90'i."""
    d = np.abs(luma(R) - luma(bg))
    core = d[d > 20]
    return float(np.percentile(core, 90)) if core.size else 100.0


def smoothstep(x, a, b):
    u = np.clip((x - a) / max(b - a, 1e-3), 0, 1)
    return (u * u * (3 - 2 * u)).astype(np.float32)


def noise_floor(R, bg):
    """Poster-BG gurultu tabani: murekkep disi |dluma| p99 (WP dokusunda ~10, digerlerinde ~2)."""
    d = np.abs(luma(R) - luma(bg))
    core = d[d < 40]
    return float(np.percentile(core, 99)) if core.size else 5.0


def alpha_of(R, bg, C, t0=5.0):
    """Murekkep kapsama alfasi: |dluma| t0..t0+17 arasi yumusak gecis, ustu tam
    poster pikseli (posterin kendi kenar yumusatmasi R'de zaten var). t0 =
    edisyon gurultu tabani (noise_floor); ince metin (3. satir) tam basilir."""
    d = np.abs(luma(R) - luma(bg))
    return smoothstep(d, t0, t0 + 17.0)


def alpha_core(R, bg, C):
    """Kati murekkep: parlama alani (L) burada eklenmez (pilotta murekkep parlamasiz)."""
    d = np.abs(luma(R) - luma(bg))
    return smoothstep(d, 40.0, 0.6 * C)


# ------------------------------------------------------------------ sablon (pilot temizleme)
def shifted_fill(img, mask, shifts=((0, 48), (0, -48), (48, 0), (-48, 0), (48, 48), (-48, -48), (0, 96), (0, -96))):
    """mask (bool) piksellerini, ayni goruntunun maske disi kaydirilmis
    kopyasindan doldurur (doku korunur). Kalan bosluk Telea inpaint."""
    out = img.copy()
    todo = mask.copy()
    H, W = mask.shape
    for dx, dy in shifts:
        if not todo.any():
            break
        src = np.roll(np.roll(img, dy, axis=0), dx, axis=1)
        srcm = np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
        ok = todo & ~srcm
        # kenar tasmasi: roll ile sarilan bolge gecersiz
        ys, xs = np.where(ok)
        out[ys, xs] = src[ys, xs]
        todo &= ~ok
    if todo.any():
        out = cv2.inpaint(np.clip(out, 0, 255).astype(np.uint8), todo.astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA).astype(np.float32)
    return out


def clean_template(pilot_canvas, R_pilot, bg, C, place, use_poster_bg, t0=5.0, sigma=25.0):
    """Pilot tuvalinde poster bolgesindeki pilot murekkebini siler.
    use_poster_bg=True (CI/MB/DB: pilot dokusu = poster dokusu, fark 0.1-1.7):
      dolgu = BG + alcak gecirgen parlama alani (murekkep disi olculur).
    use_poster_bg=False (WP: farkli doku ornegi): kaydirmali kopya.
    Donus: sablon (float32, tam tuval), poster bolgesi maskesi."""
    T = pilot_canvas.astype(np.float32).copy()
    w, h = place["size"]
    x0, y0 = place["x0"], place["y0"]
    Hc, Wc = T.shape[:2]
    ys0, ys1 = max(0, y0), min(Hc, y0 + h)
    xs0, xs1 = max(0, x0), min(Wc, x0 + w)
    sub = T[ys0:ys1, xs0:xs1]
    Rs = R_pilot[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
    bgs = bg[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
    A = alpha_of(Rs, bgs, C, t0)
    ink = cv2.dilate((A > 0.02).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    wgt = (~ink).astype(np.float32)
    den = cv2.GaussianBlur(wgt, (0, 0), sigma)[..., None]
    if use_poster_bg:
        L = cv2.GaussianBlur((sub - bgs) * wgt[..., None], (0, 0), sigma) / np.maximum(den, 1e-3)
        filled = bgs + L
    else:
        filled = shifted_fill(sub, ink)
        filled = filled + cv2.GaussianBlur((sub - filled) * wgt[..., None], (0, 0), sigma) / np.maximum(den, 1e-3)
    soft = cv2.GaussianBlur(ink.astype(np.float32), (0, 0), 1.5)[..., None]
    T[ys0:ys1, xs0:xs1] = sub * (1 - soft) + filled * soft
    region = np.zeros((Hc, Wc), bool)
    region[ys0:ys1, xs0:xs1] = True
    return T, region


def compose(T, R_new, bg, C, place, t0=5.0):
    """out = T*(1-A) + (R + L*(1-Acore))*A ; L = T - BG (sablonun parlama/vinyet
    alani): kenar pikselleri parlamayi korur, kati murekkep poster rengiyle basilir."""
    out = T.copy()
    w, h = place["size"]
    x0, y0 = place["x0"], place["y0"]
    Hc, Wc = T.shape[:2]
    ys0, ys1 = max(0, y0), min(Hc, y0 + h)
    xs0, xs1 = max(0, x0), min(Wc, x0 + w)
    Rs = R_new[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0].astype(np.float32)
    bgs = bg[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
    Ts = T[ys0:ys1, xs0:xs1]
    A = alpha_of(Rs, bgs, C, t0)[..., None]
    Ac = alpha_core(Rs, bgs, C)[..., None]
    L = cv2.GaussianBlur(Ts - bgs, (0, 0), 3.0)
    out[ys0:ys1, xs0:xs1] = Ts * (1 - A) + (Rs + L * (1 - Ac)) * A
    return out


# ------------------------------------------------------------------ Watch
def symbol_box(poster, bg_full_small, C, scale=0.125):
    """Halka icindeki fuzyon sembolunun poster kutusu (halka ve metin haric).
    Analiz 1/8 olcekte. Donus (x0,y0,x1,y1) poster px."""
    s = scale
    R = cv2.resize(poster, None, fx=s, fy=s, interpolation=cv2.INTER_AREA).astype(np.float32)
    A = alpha_of(R, bg_full_small, C)
    m = (A > 0.15).astype(np.uint8)
    rx0, ry0, rx1, ry1 = [int(v * s) for v in WATCH["ring_box"]]
    inner = np.zeros_like(m)
    inner[ry0 + 8:int(5700 * s), rx0 + 8:rx1 - 8] = 1     # halka ustu .. isim satiri ustu (6110)
    m &= inner
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    boxes = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < 30:
            continue
        boxes.append((x, y, x + w, y + h))
    if not boxes:
        raise SystemExit("HATA: fuzyon sembolu bulunamadi")
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
    return int(x0 / s), int(y0 / s), int(x1 / s), int(y1 / s)


def watch_place(poster, bg_poster_small, C, box, s=None, center=None, t0=5.0):
    """Poster -> saat tuvali (1000x1220): olcek s (varsayilan 0.2372), sembol
    kutusu merkezi center (varsayilan 500,610); kalibrasyon pilottan olcer.
    Donus: R (sembol bolgesi warp), A (alfa), affine, saat kutusu."""
    s = WATCH["s"] if s is None else s
    center = WATCH["center"] if center is None else center
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    tx, ty = center[0] - s * cx, center[1] - s * cy
    M = np.float32([[s, 0, tx], [0, s, ty]])
    pre = cv2.resize(poster, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)   # 2x hedef olcek
    M2 = M.copy(); M2[:, :2] *= 2.0
    R = cv2.warpAffine(pre, M2, (1000, 1220), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
    bg_pre = cv2.resize(bg_poster_small, (pre.shape[1], pre.shape[0]), interpolation=cv2.INTER_LINEAR)
    BG = cv2.warpAffine(bg_pre, M2, (1000, 1220), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    A = alpha_of(R.astype(np.float32), BG, C, t0)
    # yalniz sembol kutusu (pad) icinde
    bx0, by0 = int(s * box[0] + tx) - 6, int(s * box[1] + ty) - 6
    bx1, by1 = int(s * box[2] + tx) + 6, int(s * box[3] + ty) + 6
    lim = np.zeros_like(A); lim[max(0, by0):by1, max(0, bx0):bx1] = 1
    return R.astype(np.float32), A * lim, M, (bx0, by0, bx1, by1)



# ------------------------------------------------------------------ kural (b): bant ve bolge sentezi
FIELD_DS = 8   # alanlar (parlama/vinyet, sigma 25) 1/8 olcekte saklanir


def band_mask(dev, shape):
    p = PLACEMENT[dev]; w, h = p["size"]; x0, y0 = p["x0"], p["y0"]; H, W = shape
    m = np.ones((H, W), bool)
    m[max(0, y0):min(H, y0 + h), max(0, x0):min(W, x0 + w)] = False
    return m


def tile_bg(bg, dev, shape):
    """BG dokusunu (cihaz olceginde) tuvale dosemek: poster bolgesi (x0,y0)'da
    hizali, bantlar ayni olcekli dokunun periyodik uzatmasi (ayna YOK)."""
    p = PLACEMENT[dev]; w, h = p["size"]; x0, y0 = p["x0"], p["y0"]; H, W = shape
    ys = (np.arange(H) - y0) % h
    xs = (np.arange(W) - x0) % w
    return bg[ys][:, xs]


def lowpass_field(diff, wgt, sigma=25.0):
    den = cv2.GaussianBlur(wgt, (0, 0), sigma)[..., None]
    return cv2.GaussianBlur(diff * wgt[..., None], (0, 0), sigma) / np.maximum(den, 1e-3)


def field_save(path, F):
    small = cv2.resize(F, (max(1, F.shape[1] // FIELD_DS), max(1, F.shape[0] // FIELD_DS)), interpolation=cv2.INTER_AREA)
    np.save(str(path), small.astype(np.float32))


def field_load(path, shape):
    small = np.load(str(path))
    return cv2.resize(small, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)



def const_mask_from_db(bg_db):
    """Sabit ogelerin (halka, ∞, tagline satirlari) maskesi: DB edisyon zemini
    saf siyah oldugu icin uzerindeki tek murekkep sabit ogelerdir (luma > 40).
    Ayni yerlesim 4 edisyonda ortaktir (WP_LAYOUT_SPEC 7.1). 6 px genisletilir."""
    m = (luma(bg_db.astype(np.float32)) > 40).astype(np.uint8)
    return cv2.dilate(m, np.ones((13, 13), np.uint8)) > 0


def clean_bg(bg, const_mask):
    """BG'den sabit ogeleri kaldirir (bant doku kaynagi). Dolgu ayni dokudan
    uzak kaydirmali kopya (poster 1500 px ~ cihazda 300-430 px)."""
    h, w = bg.shape[:2]
    k = int(1500 * w / 7200.0)
    shifts = ((0, k), (0, -k), (k, 0), (-k, 0), (k, k), (-k, -k), (0, 2 * k), (0, -2 * k))
    return shifted_fill(bg.astype(np.float32), const_mask.copy(), shifts)


def edge_continue(bg, dev, shape, zone=40):
    """Poster kenarindan disari 'zone' px: kenar dokusunun yansitilmis kopyasi
    (yalniz gecis seridi icin; bant govdesi periyodik uzatmadir)."""
    p = PLACEMENT[dev]; w, h = p["size"]; x0, y0 = p["x0"], p["y0"]; H, W = shape
    ys = np.arange(H) - y0
    ys = np.where(ys < 0, -ys - 1, np.where(ys >= h, 2 * h - ys - 1, ys))
    xs = np.arange(W) - x0
    xs = np.where(xs < 0, -xs - 1, np.where(xs >= w, 2 * w - xs - 1, xs))
    return bg[np.clip(ys, 0, h - 1)][:, np.clip(xs, 0, w - 1)]


def seam_weights(dev, shape, z1=16, z2=64):
    """d = poster kenarina uzaklik (disarida). wm: 0..z1 yansitilmis kenar
    (C0 sureklilik); wt: z1..z2 arasinda doseme fazlari arasinda capraz gecis."""
    p = PLACEMENT[dev]; w, h = p["size"]; x0, y0 = p["x0"], p["y0"]; H, W = shape
    yy, xx = np.mgrid[0:H, 0:W]
    dy = np.maximum(np.maximum(y0 - yy, yy - (y0 + h - 1)), 0)
    dx = np.maximum(np.maximum(x0 - xx, xx - (x0 + w - 1)), 0)
    d = np.sqrt(dx * dx + dy * dy).astype(np.float32)
    wm = 1.0 - smoothstep(d, 0.0, float(z1)); wm[d == 0] = 0.0
    wt = smoothstep(d, float(z1), float(z2))
    return wm, wt


def synth_texture(bg, bg_clean, dev, shape):
    """Kural (b) doku tuvali: poster bolgesi = BG (sabit ogeler dahil); bant =
    TEMIZ BG'nin periyodik uzatmasi (ayna yok); kenarda 16 px yansitilmis
    gecis + 16-64 px'te iki doseme fazi arasinda capraz gecis (sert dikis yok)."""
    p = PLACEMENT[dev]; w, h = p["size"]; x0, y0 = p["x0"], p["y0"]; H, W = shape
    tile = tile_bg(bg_clean, dev, shape)
    tile2 = np.roll(np.roll(tile, 37, axis=0), 53, axis=1)
    ext = edge_continue(bg_clean, dev, shape)
    wm, wt = seam_weights(dev, shape)
    wm = wm[..., None]; wt = wt[..., None]
    band = tile * (1 - wt) + tile2 * wt
    tex = ext * wm + band * (1 - wm)
    tex[max(0, y0):min(H, y0 + h), max(0, x0):min(W, x0 + w)] = bg[max(0, -y0):min(h, H - y0), max(0, -x0):min(w, W - x0)]
    return tex


def synth_canvas(bg, bg_clean, F, dev, dark_black):
    """Kural (b) tuvali = doku + F (pilottan olculen TEK surekli parlama/vinyet
    alani, sigma 25). DB: bant saf siyah (pilot olcumu 0,0,0)."""
    H, W = F.shape[:2]
    tex = synth_texture(bg, bg_clean, dev, (H, W))
    out = tex + F
    if dark_black:
        out[band_mask(dev, (H, W))] = 0.0
    return out


# ------------------------------------------------------------------ ana akis
def build_templates(pilot_pair, pilot_dir, poster_dir, bg_pairs, out_dir):
    """Kalibrasyon: edisyon x cihaz sablonlari + BG + C + saat kutusu -> out_dir."""
    out = Path(out_dir); (out / "templates").mkdir(parents=True, exist_ok=True); (out / "bg").mkdir(exist_ok=True)
    meta = dict(pilot_pair=pilot_pair, bg_pairs=bg_pairs, editions={})
    db_posters = [imread(Path(poster_dir) / poster_name(p, "Deep_Black")) for p in bg_pairs]
    const_masks = {dev: const_mask_from_db(edition_bg(db_posters, place["size"], True)[0]) for dev, place in PLACEMENT.items()}
    del db_posters
    for ed in EDITIONS:
        posters = [imread(Path(poster_dir) / poster_name(p, ed)) for p in bg_pairs]
        p_pilot = imread(Path(poster_dir) / poster_name(pilot_pair, ed))
        emeta = dict(devices={})
        # tam poster 1/8 zemin (saat ve sembol kutusu icin)
        small = (900, 1200)
        dark = ed in ('Midnight_Blue', 'Deep_Black')
        bg_small, _ = edition_bg(posters, small, dark)
        C_small = ink_contrast(down(p_pilot, small).astype(np.float32), bg_small)
        t0_small = max(5.0, noise_floor(down(p_pilot, small).astype(np.float32), bg_small))
        cv2.imwrite(str(out / "bg" / f"{ed}_small.png"), np.clip(bg_small, 0, 255).astype(np.uint8))
        for dev, place in PLACEMENT.items():
            size = place["size"]
            bg, contam = edition_bg(posters, size, dark)
            Rp = down(p_pilot, size).astype(np.float32)
            C = ink_contrast(Rp, bg)
            t0 = max(5.0, noise_floor(Rp, bg))
            pilot = imread(Path(pilot_dir) / f"AstroLove_{pilot_pair}_{ed}_{dev}.jpg")
            T, region = clean_template(pilot, Rp, bg, C, place, use_poster_bg=(ed != "Warm_Parchment"), t0=t0)
            cv2.imwrite(str(out / "templates" / f"{ed}_{dev}.png"), np.clip(np.round(T), 0, 255).astype(np.uint8))
            cv2.imwrite(str(out / "bg" / f"{ed}_{dev}.png"), np.clip(np.round(bg), 0, 255).astype(np.uint8))
            emeta["devices"][dev] = dict(C=C, t0=t0, contamination_px=int(contam.sum()), size=list(size))
            # kural (b) alani: F = lowpass(pilot - doku) tum tuvalde (murekkep haric), TEK surekli alan
            (out / "fields").mkdir(exist_ok=True)
            Hc, Wc = pilot.shape[:2]
            bg_clean = clean_bg(bg, const_masks[dev])
            cv2.imwrite(str(out / "bg" / f"{ed}_{dev}_clean.png"), np.clip(np.round(bg_clean), 0, 255).astype(np.uint8))
            tex = synth_texture(bg, bg_clean, dev, (Hc, Wc))
            bm = band_mask(dev, (Hc, Wc))
            pil = pilot.astype(np.float32)
            Ap = np.zeros((Hc, Wc), np.float32)
            ys0, ys1 = max(0, place["y0"]), min(Hc, place["y0"] + size[1]); xs0, xs1 = max(0, place["x0"]), min(Wc, place["x0"] + size[0])
            Ap[ys0:ys1, xs0:xs1] = alpha_of(Rp[ys0 - place["y0"]:ys1 - place["y0"], xs0 - place["x0"]:xs1 - place["x0"]],
                                            bg[ys0 - place["y0"]:ys1 - place["y0"], xs0 - place["x0"]:xs1 - place["x0"]], C, t0)
            wgt = (cv2.dilate((Ap > 0.02).astype(np.uint8), np.ones((9, 9), np.uint8)) == 0).astype(np.float32)
            F = lowpass_field(pil - tex, wgt)
            field_save(out / "fields" / f"{ed}_{dev}_F.npy", F)
            syn = synth_canvas(bg, bg_clean, F, dev, dark_black=(ed == "Deep_Black"))
            d = np.abs(pil - syn).mean(axis=2)
            dband = float(d[bm].mean()) if bm.any() else 0.0
            dreg = float(d[(~bm) & (wgt > 0)].mean())
            emeta["devices"][dev].update(band_err=dband, region_bg_err=dreg)
            log(f"  {ed:16s} {dev:8s} kural(b) bant hatasi {dband:.2f} | bolge zemin hatasi {dreg:.2f}")
            log(f"  {ed:16s} {dev:8s} C={C:.1f} t0={t0:.1f} BG kirlilik {int(contam.sum())} px")
        # Watch: olcek ve merkez PILOTTAN olculur: poster sembol kesiti (kutu+100 px)
        # pilot saat dosyasinda yuksek gecirgen sablon eslestirme ile bulunur
        # (kaba 0.005 / ince 0.0005 olcek, 4x alt-piksel; wp_mockup_common).
        box = symbol_box(p_pilot, bg_small, C_small)
        pilot_w = imread(Path(pilot_dir) / f"AstroLove_{pilot_pair}_{ed}_Watch.jpg")
        pad = 100
        crop = p_pilot[box[1] - pad:box[3] + pad, box[0] - pad:box[2] + pad]
        fit = template_candidate(cv2.cvtColor(pilot_w, cv2.COLOR_BGR2GRAY), crop, s_lo=0.215, s_hi=0.265)
        if fit is None or fit["corr"] < 0.7:
            raise SystemExit(f"HATA: {ed} saat sembolu pilotta bulunamadi (corr {None if fit is None else fit['corr']:.3f})")
        s_cal = fit["scale"]
        tx, ty = float(fit["H"][0, 2]), float(fit["H"][1, 2])
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        center = (tx + (cx - (box[0] - pad)) * s_cal, ty + (cy - (box[1] - pad)) * s_cal)
        pbox = (int(round(center[0] - (cx - box[0]) * s_cal)), int(round(center[1] - (cy - box[1]) * s_cal)),
                int(round(center[0] + (box[2] - cx) * s_cal)), int(round(center[1] + (box[3] - cy) * s_cal)))
        log(f"  {ed:16s} Watch   sablon corr {fit['corr']:.3f} olcek {s_cal:.4f} merkez ({center[0]:.1f},{center[1]:.1f}) kutu {pbox}")
        R, A, M, wbox = watch_place(p_pilot, bg_small, C_small, box, s_cal, center, t0_small)
        ink = cv2.dilate((A > 0.02).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        Tw = pilot_w.astype(np.float32)
        filled = shifted_fill(Tw, ink)
        wgt = (~ink).astype(np.float32)
        num = cv2.GaussianBlur((Tw - filled) * wgt[..., None], (0, 0), 25); den = cv2.GaussianBlur(wgt, (0, 0), 25)[..., None]
        filled = filled + num / np.maximum(den, 1e-3)
        soft = cv2.GaussianBlur(ink.astype(np.float32), (0, 0), 1.5)[..., None]
        Tw = Tw * (1 - soft) + filled * soft
        cv2.imwrite(str(out / "templates" / f"{ed}_Watch.png"), np.clip(np.round(Tw), 0, 255).astype(np.uint8))
        emeta["watch"] = dict(C=C_small, t0=t0_small, pilot_symbol_box=list(box), pilot_watch_box=list(pbox), scale=s_cal, center=list(center))
        meta["editions"][ed] = emeta
    (out / "templates.json").write_text(json.dumps(meta, indent=1))
    return meta


def build_pair(pair, poster_dir, tpl_dir, out_dir, compare_dir=None, mode="rule"):
    meta = json.loads((Path(tpl_dir) / "templates.json").read_text())
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    rows = []
    for ed in EDITIONS:
        p = imread(Path(poster_dir) / poster_name(pair, ed))
        for dev, place in PLACEMENT.items():
            size = place["size"]
            bg = imread(Path(tpl_dir) / "bg" / f"{ed}_{dev}.png").astype(np.float32)
            C = meta["editions"][ed]["devices"][dev]["C"]
            R = down(p, size).astype(np.float32)
            if mode == "rule":
                W_, H_ = DEVICES[dev]
                F = field_load(Path(tpl_dir) / "fields" / f"{ed}_{dev}_F.npy", (H_, W_))
                bg_clean = imread(Path(tpl_dir) / "bg" / f"{ed}_{dev}_clean.png").astype(np.float32)
                T = synth_canvas(bg, bg_clean, F, dev, dark_black=(ed == "Deep_Black"))
            else:
                T = imread(Path(tpl_dir) / "templates" / f"{ed}_{dev}.png").astype(np.float32)
            out = compose(T, R, bg, C, place, meta["editions"][ed]["devices"][dev].get("t0", 5.0))
            rows.append(_save(out, pair, ed, dev, out_dir, compare_dir))
        # Watch
        bg_small = imread(Path(tpl_dir) / "bg" / f"{ed}_small.png").astype(np.float32)
        C = meta["editions"][ed]["watch"]["C"]
        box = symbol_box(p, bg_small, C)
        wm = meta["editions"][ed]["watch"]
        R, A, M, wbox = watch_place(p, bg_small, C, box, wm["scale"], tuple(wm["center"]), wm.get("t0", 5.0))
        Tw = imread(Path(tpl_dir) / "templates" / f"{ed}_Watch.png").astype(np.float32)
        out = Tw * (1 - A[..., None]) + R * A[..., None]
        r = _save(out, pair, ed, "Watch", out_dir, compare_dir)
        r["symbol_box"] = list(box); r["watch_box"] = list(wbox)
        rows.append(r)
    return rows


def _save(out, pair, ed, dev, out_dir, compare_dir):
    from PIL import Image
    name = f"AstroLove_{pair}_{ed}_{dev}.jpg"
    u8 = np.clip(np.round(out), 0, 255).astype(np.uint8)
    W, H = DEVICES[dev]
    assert u8.shape[1] == W and u8.shape[0] == H, (name, u8.shape)
    Image.fromarray(cv2.cvtColor(u8, cv2.COLOR_BGR2RGB)).save(str(Path(out_dir) / name), "JPEG", quality=JPEG_Q,
                                                             subsampling=0, optimize=True, progressive=False, dpi=(300, 300))
    r = dict(file=name, edition=ed, device=dev, size=[W, H])
    if compare_dir and (Path(compare_dir) / name).exists():
        ref = imread(Path(compare_dir) / name).astype(np.float32)
        back = imread(Path(out_dir) / name).astype(np.float32)
        d = np.abs(back - ref).mean(axis=2)
        r.update(cmp_mean=float(d.mean()), cmp_p95=float(np.percentile(d, 95)), cmp_max=float(d.max()))
    return r


def contact_sheet(out_dir, pair, path, tw=360):
    tiles = []
    for ed in EDITIONS:
        row = []
        for dev in ["Phone", "Tablet", "Desktop", "Watch"]:
            im = imread(Path(out_dir) / f"AstroLove_{pair}_{ed}_{dev}.jpg")
            h = int(im.shape[0] * tw / im.shape[1])
            t = cv2.resize(im, (tw, h), interpolation=cv2.INTER_AREA)
            canvas = np.full((800, tw, 3), 40, np.uint8)
            y = (800 - h) // 2
            canvas[y:y + h] = t
            cv2.putText(canvas, f"{ed} {dev}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            row.append(canvas)
        tiles.append(np.hstack(row))
    cv2.imwrite(str(path), np.vstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 88])


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("templates"); a.add_argument("--pilot-pair", default="Cancer_Libra"); a.add_argument("--pilot-dir", required=True)
    a.add_argument("--posters", required=True); a.add_argument("--bg-pairs", required=True); a.add_argument("--out", required=True)
    b = sub.add_parser("build"); b.add_argument("--pair", required=True); b.add_argument("--posters", required=True)
    b.add_argument("--templates", required=True); b.add_argument("--out", required=True); b.add_argument("--compare", default="")
    b.add_argument("--mode", choices=["rule", "template"], default="rule", help="rule = kural (b) sentez (bant+bolge); template = pilot zemin sablonu")
    args = ap.parse_args()
    if args.cmd == "templates":
        build_templates(args.pilot_pair, args.pilot_dir, args.posters, args.bg_pairs.split(","), args.out)
    else:
        rows = build_pair(args.pair, args.posters, args.templates, args.out, args.compare or None, args.mode)
        contact_sheet(args.out, args.pair, Path(args.out) / f"CONTACT_{args.pair}.jpg")
        md = ["| Dosya | Boyut | Kiyas ort | p95 | maks |", "|---|---|---|---|---|"]
        for r in rows:
            md.append(f"| {r['file']} | {r['size'][0]}x{r['size'][1]} | {r.get('cmp_mean', float('nan')):.2f} | {r.get('cmp_p95', float('nan')):.1f} | {r.get('cmp_max', float('nan')):.0f} |")
        (Path(args.out) / "report.md").write_text("\n".join(md) + "\n")
        (Path(args.out) / "report.json").write_text(json.dumps(rows, indent=1))
        log("\n".join(md))


if __name__ == "__main__":
    main()
