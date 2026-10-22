"""Genel ikame cekirdegi (kart insetleri/panelleri). master.py ile ayni ilkeler:
Cancer murekkebi tam bilesen sinirlariyla silinir; Kova ozgun sanat/sembolleri gercek alpha ile eklenir."""
import numpy as np
from PIL import Image
from scipy import ndimage
import master as M

KSRC = {}
def kova_src(c):
    cache = M.ROOT / f'out/ksrc_{c}.npz'
    if c not in KSRC and cache.exists():
        z = np.load(cache); KSRC[c] = {k: z[k] for k in z.files}; KSRC[c]['light'] = bool(KSRC[c]['light'])
    if c not in KSRC:
        kn = M.COLORS[c][1]
        im = Image.open(M.ROOT / f'src/{c}/05_WA_01_TECH_PRODUCT_TRUTH_AQUARIUS_AQUARIUS_{kn}.jpg').convert('RGB').crop(M.KP)
        K = np.asarray(im).astype(np.float64)
        small = np.asarray(Image.fromarray(K.astype(np.uint8)).resize((K.shape[1] // 4, K.shape[0] // 4), Image.BOX)).astype(np.float64)
        bgs = M.local_bg(small, 25)
        bg = np.asarray(Image.fromarray(np.clip(bgs, 0, 255).astype(np.uint8)).resize((K.shape[1], K.shape[0]), Image.BILINEAR)).astype(np.float64)
        light = K[40:200, 80:1450].mean() > 128
        ink = M.ink(K, bg, 18 if light else 30)
        yy, xx = np.mgrid[:K.shape[0], :K.shape[1]]
        disk = np.hypot(xx - 767.4, yy - 819.7) <= 571.3 + 20
        art = M.components(ink & disk & (yy < 1290), 800)
        groi = ((xx >= 250) & (xx <= 560)) | ((xx >= 970) & (xx <= 1290))
        gly = M.components(ink & groi & (yy >= 1300) & (yy < 1420), 300)
        txt = M.components(ink & (yy >= 1420), 20)
        kbg = M.harmonic(K, ndimage.binary_dilation(art | gly | txt, iterations=4))
        KSRC[c] = dict(K=K, kbg=kbg, art=art, gly=gly, light=light)
        np.savez_compressed(cache, **KSRC[c])
    return KSRC[c]

def ring_fit(xs, ys):
    A = np.c_[2 * xs, 2 * ys, np.ones_like(xs)]; b = xs ** 2 + ys ** 2
    cx, cy, c = np.linalg.lstsq(A, b, rcond=None)[0]; return cx, cy, np.sqrt(c + cx ** 2 + cy ** 2)

def layer(c, part, s, W, H, ox, oy, side=None):
    """Kova katmani: K, zemini ve maske hedef olcege tasinir, alpha HEDEF olcekte hesaplanir (master ile ayni sira)."""
    k = kova_src(c)
    if part == 'art':
        m = k['art']
    else:
        lab, n = ndimage.label(k['gly']); keep = []
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            if (xs.mean() < 768) == (side == 0): keep.append(i)
        m = np.isin(lab, keep)
    ys, xs = np.where(m)
    pad = 12
    y0, y1, x0, x1 = ys.min() - pad, ys.max() + pad, xs.min() - pad, xs.max() + pad
    Kc, Bc, Mc = k['K'][y0:y1, x0:x1], k['kbg'][y0:y1, x0:x1], m[y0:y1, x0:x1].astype(float)
    tx, ty = x0 * s + ox, y0 * s + oy
    fx, fy = int(np.floor(tx)) - 2, int(np.floor(ty)) - 2
    tw, th = int(np.ceil((x1 - x0) * s)) + 5, int(np.ceil((y1 - y0) * s)) + 5
    Kw = warp_full(Kc, s, tx - fx, ty - fy, tw, th); Bw = warp_full(Bc, s, tx - fx, ty - fy, tw, th)
    Mw = warp_full(Mc, s, tx - fx, ty - fy, tw, th) > 0.2
    valid = Kw[..., 0] >= 0
    Kw[~valid] = 0; Bw[~valid] = 0
    a, F = M.matte(Kw, Bw, core_r=max(2, int(round(3 * s / M.S))))
    a = a * ndimage.binary_dilation(Mw, iterations=2) * valid
    out_a = np.zeros((H, W)); out_Fa = np.zeros((H, W, 3))
    Y0, X0 = max(fy, 0), max(fx, 0); Y1, X1 = min(fy + th, H), min(fx + tw, W)
    if Y1 > Y0 and X1 > X0:
        out_a[Y0:Y1, X0:X1] = a[Y0 - fy:Y1 - fy, X0 - fx:X1 - fx]
        out_Fa[Y0:Y1, X0:X1] = (F * a[..., None])[Y0 - fy:Y1 - fy, X0 - fx:X1 - fx]
    return out_a, out_Fa

def composite(dst, a, Fa):
    # premultiplied: out = dst*(1-a) + F*a
    return dst * (1 - a[..., None]) + np.clip(Fa, 0, 255 * a[..., None])

def grain_fill(img, mask, ref_mask):
    """Harmonik dolgu + cevre zeminden olculen gren (std) eklenir."""
    out = M.harmonic(img, mask)
    smooth = np.stack([ndimage.gaussian_filter(img[..., i], 2) for i in range(3)], 2)
    resid = (img - smooth)[ref_mask]
    sd = resid.std(0) if len(resid) > 50 else np.zeros(3)
    rng = np.random.default_rng(7)
    noise = rng.normal(0, 1, img.shape) * sd
    out[mask] = out[mask] + noise[mask]
    return out

def cancer_ink(R, thr, min_area, zone):
    bg = M.local_bg(R, 41)
    return M.components(M.ink(R, bg, thr) & zone, min_area)

def warp_full(img, s, ox, oy, W, H):
    out = []
    for i in range(img.shape[2] if img.ndim == 3 else 1):
        ch = img[..., i] if img.ndim == 3 else img
        im = Image.fromarray(ch.astype(np.float32), mode='F')
        sw, sh = im.width * s, im.height * s
        im2 = im.resize((max(1, int(round(sw))), max(1, int(round(sh)))), Image.LANCZOS)
        fx, fy = im2.width / sw, im2.height / sh
        im3 = im2.transform((W, H), Image.AFFINE, (fx, 0, -ox * fx, 0, fy, -oy * fy), resample=Image.BICUBIC, fillcolor=-1)
        out.append(np.asarray(im3))
    o = np.stack(out, 2) if len(out) > 1 else out[0]
    return o

def find_ring(R, light):
    H, W = R.shape[:2]
    ink = M.ink(R, M.local_bg(R, 41), 18 if light else 30)
    lab, n = ndimage.label(ink); objs = ndimage.find_objects(lab)
    cnt = np.bincount(lab.ravel())
    sel = np.zeros_like(ink)
    for i, o in enumerate(objs, 1):
        h = o[0].stop - o[0].start; w = o[1].stop - o[1].start
        edge = o[0].start <= 3 or o[1].start <= 3 or o[0].stop >= H - 3 or o[1].stop >= W - 3
        if not edge and max(h, w) > 0.30 * W and cnt[i] / (h * w) < 0.05:
            sel |= lab == i
    ys, xs = np.where(sel)
    cx, cy, r = ring_fit(xs.astype(float), ys.astype(float))
    for _ in range(3):
        d = np.abs(np.hypot(xs - cx, ys - cy) - r); k = d < max(3, 0.02 * r)
        if k.sum() < 50: break
        cx, cy, r = ring_fit(xs[k].astype(float), ys[k].astype(float))
    return cx, cy, r, ink

REL45 = {'ring': (0.49945, 0.40055, 0.34815), 'gly': ((0.33715, 0.6660), (0.6663, 0.6662))}  # kart 06/09 olcumu

def subst_poster(R, c, rings_out=None, rel=None):
    """R: referans poster bolgesi (float, HxWx3). Donus: Kova ikameli bolge + meta."""
    H, W = R.shape[:2]
    light = R[int(H * 0.02):int(H * 0.08), int(W * 0.1):int(W * 0.9)].mean() > 128
    if rel is None:
        cx, cy, r, ink = find_ring(R, light)
    else:
        cx, cy, r = rel['ring'][0] * W, rel['ring'][1] * H, rel['ring'][2] * W
        ink = M.ink(R, M.local_bg(R, 41), 18 if light else 30)
    k = kova_src(c)
    s = r / 571.3; ox = cx - 767.4 * s; oy = cy - 819.7 * s
    yy, xx = np.mgrid[:H, :W]
    amin = max(8, int(60 * (s / M.S) ** 2))
    disk = np.hypot(xx - cx, yy - cy) <= r + max(6, 0.04 * r)
    art = M.components(ink & disk & (yy < cy + 0.80 * r), amin)
    band = (yy >= cy + 0.80 * r) & (yy < cy + 1.10 * r)
    if rel is not None:
        roi = np.zeros((H, W), bool)
        for gx, gy in rel['gly']:
            roi[int(gy * H - 0.05 * H):int(gy * H + 0.05 * H), int(gx * W - 0.10 * W):int(gx * W + 0.10 * W)] = True
        band &= roi
    gly = M.components(ink & band, max(6, int(40 * (s / M.S) ** 2)))
    # Kova zemini (ton esli) hizali
    kb = warp_full(k['kbg'], s, ox, oy, W, H)
    valid = kb[..., 0] >= 0
    kink_w = warp_full(np.stack([k['art'] | k['gly'] | ndimage.binary_dilation(k['gly'], iterations=3)] * 1, 2).astype(float)[..., 0], s, ox, oy, W, H) > 0.05
    both = valid & ~ndimage.binary_dilation(ink, iterations=3)
    kt = kb.copy()
    for ch in range(3):
        x = kb[..., ch][both]; y = R[..., ch][both]
        p = np.linalg.lstsq(np.c_[x, np.ones_like(x)], y, rcond=None)[0]
        if not (0.7 <= p[0] <= 1.4) or x.std() < 4: p = np.array([1.0, float(np.median(y - x))])
        kt[..., ch] = kb[..., ch] * p[0] + p[1]
    Ew = warp_full(k['art'].astype(float), s, ox, oy, W, H) > 0.02
    # koruma yalniz metin: sembol kutusunun (+%4 r) tamamen icinde kalan kucuk murekkep parcalari (esik alti Cancer/Libra
    # uclari) korunmaz, silinir
    gzone = np.zeros((H, W), bool)
    if gly.any():
        lab_g, ng = ndimage.label(gly); pz = int(round(0.04 * r))
        for side in (0, 1):
            pts = [np.where(lab_g == i) for i in range(1, ng + 1)]
            pts = [p for p in pts if (p[1].mean() < cx) == (side == 0)]
            if not pts: continue
            ys = np.concatenate([p[0] for p in pts]); xs = np.concatenate([p[1] for p in pts])
            gzone[max(ys.min() - pz, 0):ys.max() + pz + 1, max(xs.min() - pz, 0):xs.max() + pz + 1] = True
    low = ink & (yy >= cy + 0.80 * r) & ~gly
    lab_t, nt = ndimage.label(low)
    inside = ndimage.minimum(gzone.astype(int), lab_t, index=np.arange(1, nt + 1)) if nt else []
    frag = np.isin(lab_t, [i + 1 for i, v in enumerate(inside) if v == 1])
    protect = ndimage.binary_dilation(low & ~frag, iterations=3)
    allowed = valid & ~ndimage.binary_dilation(Ew, iterations=3) & ~protect
    r_art, _ = M.halo_radius(R, art, kt, allowed & (yy < cy + 0.80 * r + 20), local=True)
    r_gly, _ = M.halo_radius(R, gly, kt, allowed & (yy >= cy + 0.70 * r), local=True) if gly.any() else (0, [])
    rem = (ndimage.binary_dilation(art, iterations=r_art + 1) | ndimage.binary_dilation(gly, iterations=r_gly + 1)) & ~protect
    # kucuk sembol: esikte kopan ince uc kiriktilari da gitsin diye her tarafin sembol kutusu (+halo) komple silinir
    if gly.any():
        lab_g, ng = ndimage.label(gly); gbox = np.zeros((H, W), bool); pg = r_gly + 2
        for side in (0, 1):
            pts = [np.where(lab_g == i) for i in range(1, ng + 1)]
            pts = [p for p in pts if (p[1].mean() < cx) == (side == 0)]
            if not pts: continue
            ys = np.concatenate([p[0] for p in pts]); xs = np.concatenate([p[1] for p in pts])
            gbox[max(ys.min() - pg, 0):ys.max() + pg + 1, max(xs.min() - pg, 0):xs.max() + pg + 1] = True
        rem |= gbox & (yy < cy + 1.10 * r) & ~protect
    fill = R.copy()
    ok = rem & valid
    fill[ok] = kt[ok]
    fill = M.harmonic(fill, rem & ~valid)
    clean = M.soft_blend(R, fill, rem)
    a, Fa = layer(c, 'art', s, W, H, ox, oy)
    out = composite(clean, a, Fa)
    meta = {'ring': [float(cx), float(cy), float(r)], 's': float(s), 'glyph_dst': []}
    lab, n = ndimage.label(gly)
    for side in (0, 1):
        pts = [np.where(lab == i) for i in range(1, n + 1)]
        pts = [p for p in pts if (p[1].mean() < cx) == (side == 0)]
        if not pts: continue
        ys = np.concatenate([p[0] for p in pts]); xs = np.concatenate([p[1] for p in pts])
        dcx, dcy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        if rel is not None: dcx, dcy = rel['gly'][side][0] * W, rel['gly'][side][1] * H
        # kaynak sembol merkezi (kaynak koordinat) -> hedefte dcx,dcy
        kl, kn_ = ndimage.label(k['gly']); sp = [np.where(kl == i) for i in range(1, kn_ + 1)]
        sp = [p for p in sp if (p[1].mean() < 768) == (side == 0)]
        sys_ = np.concatenate([p[0] for p in sp]); sxs = np.concatenate([p[1] for p in sp])
        scx, scy = (sxs.min() + sxs.max()) / 2, (sys_.min() + sys_.max()) / 2
        ga, gFa = layer(c, 'gly', s, W, H, dcx - scx * s, dcy - scy * s, side=side)
        out = composite(out, ga, gFa)
        meta['glyph_dst'].append([float(dcx), float(dcy)])
    meta.update({'art_px': int(art.sum()), 'gly_px': int(gly.sum()), 'light': bool(light), 'halo_r_art': int(r_art), 'halo_r_gly': int(r_gly)})
    return np.clip(out, 0, 255), meta, {'rem': rem, 'art': art, 'gly': gly}

def layer_part_mask(c, part):
    k = kova_src(c)
    if part == 'fusion':
        lab, n = ndimage.label(k['art']); objs = ndimage.find_objects(lab)
        hs = [o[0].stop - o[0].start for o in objs]
        ring = int(np.argmax(hs)) + 1
        return (lab > 0) & (lab != ring)
    return None

def layer_mask(c, m, s, W, H, ox, oy):
    """Verilen kaynak maskesi icin (alpha, F*alpha) hedefte; alpha hedef olcekte."""
    k = kova_src(c)
    ys, xs = np.where(m); pad = 12
    y0, y1, x0, x1 = ys.min() - pad, ys.max() + pad, xs.min() - pad, xs.max() + pad
    Kc, Bc, Mc = k['K'][y0:y1, x0:x1], k['kbg'][y0:y1, x0:x1], m[y0:y1, x0:x1].astype(float)
    tx, ty = x0 * s + ox, y0 * s + oy
    fx, fy = int(np.floor(tx)) - 2, int(np.floor(ty)) - 2
    tw, th = int(np.ceil((x1 - x0) * s)) + 5, int(np.ceil((y1 - y0) * s)) + 5
    Kw = warp_full(Kc, s, tx - fx, ty - fy, tw, th); Bw = warp_full(Bc, s, tx - fx, ty - fy, tw, th)
    Mw = warp_full(Mc, s, tx - fx, ty - fy, tw, th) > 0.2
    valid = Kw[..., 0] >= 0; Kw[~valid] = 0; Bw[~valid] = 0
    a, F = M.matte(Kw, Bw, core_r=max(2, int(round(3 * s / M.S))))
    a = a * ndimage.binary_dilation(Mw, iterations=2) * valid
    out_a = np.zeros((H, W)); out_Fa = np.zeros((H, W, 3))
    Y0, X0 = max(fy, 0), max(fx, 0); Y1, X1 = min(fy + th, H), min(fx + tw, W)
    out_a[Y0:Y1, X0:X1] = a[Y0 - fy:Y1 - fy, X0 - fx:X1 - fx]
    out_Fa[Y0:Y1, X0:X1] = (F * a[..., None])[Y0 - fy:Y1 - fy, X0 - fx:X1 - fx]
    return out_a, out_Fa

def glyph_src_mask(c, side):
    k = kova_src(c); lab, n = ndimage.label(k['gly']); keep = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if (xs.mean() < 768) == (side == 0): keep.append(i)
    return np.isin(lab, keep)

REF_GLYPH_W = (68.0, 79.0)   # referans kapakta Cancer / Libra kucuk sembol genisligi (px, S olceginde)
REF_FUSION_WH = (344.0, 326.0)

def smooth_bg(img, allink, sigma=25):
    w = (~ndimage.binary_dilation(allink, iterations=6)).astype(float)
    num = np.stack([ndimage.gaussian_filter(img[..., i] * w, sigma) for i in range(3)], 2)
    den = ndimage.gaussian_filter(w, sigma)[..., None]
    return num / np.maximum(den, 1e-3)

def subst_glyphs(R, c, band, flat_bg=None, thr=30):
    """Panel: yalniz kucuk semboller. band=(y0,y1) satir araligi. Olcek referans sembol genisliginden."""
    H, W = R.shape[:2]
    bg = M.local_bg(R, 61)
    ink = M.ink(R, bg, thr); z = np.zeros((H, W), bool); z[band[0]:band[1]] = True
    gly = M.components(ink & z, 30)
    lab, n = ndimage.label(gly)
    sides = []
    for side in (0, 1):
        pts = [np.where(lab == i) for i in range(1, n + 1)]
        pts = [p for p in pts if (p[1].mean() < W / 2) == (side == 0)]
        ys = np.concatenate([p[0] for p in pts]); xs = np.concatenate([p[1] for p in pts])
        sides.append((xs.min(), xs.max(), ys.min(), ys.max()))
    # sol/sag hangi burc: referans panelde Cancer genisligi ~ Libra'dan dar; olcek iki tarafin ortalamasi
    ws = sorted([b[1] - b[0] + 1 for b in sides])
    f = (ws[0] / REF_GLYPH_W[0] + ws[1] / REF_GLYPH_W[1]) / 2
    s = M.S * f
    other = M.components(ink & ~z, 30)
    protect = ndimage.binary_dilation(other, iterations=3)
    bgest = smooth_bg(R, ink)
    r_h, _ = M.halo_radius(R, gly, bgest, ~protect, local=True)
    rem = ndimage.binary_dilation(gly, iterations=r_h + 1) & ~protect
    if flat_bg is not None:
        fill = R.copy(); fill[rem] = flat_bg
    else:
        ring = ndimage.binary_dilation(rem, iterations=6) & ~rem & ~protect
        fill = grain_fill(R, rem, ring)
    out = M.soft_blend(R, fill, rem)
    meta = {'scale_f': float(f), 's': float(s), 'dst': [], 'halo_r': int(r_h)}
    for side, (x0, x1, y0, y1) in enumerate(sides):
        dcx, dcy = (x0 + x1) / 2, (y0 + y1) / 2
        m = glyph_src_mask(c, side); ys, xs = np.where(m)
        scx, scy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        a, Fa = layer_mask(c, m, s, W, H, dcx - scx * s, dcy - scy * s)
        out = composite(out, a, Fa)
        meta['dst'].append([float(dcx), float(dcy)])
    return np.clip(out, 0, 255), meta, rem
