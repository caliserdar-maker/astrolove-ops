#!/usr/bin/env python3
"""medya-v1 Kova-Kova ana gorsel (5 renk) ureticisi.
Taban: referans Cancer-Libra kapaginin baski acikligi (776x1006).
Kova ozgun poster (05_WA_01) halka-uydurma donusumuyle ayni geometriye oturtulur.
- Cancer halka/sembol/kucuk semboller: gercek bilesen sinirlariyla bulunur, Kova'nin
  ton-eslenmis ayni sablon zemini ile (ikisi de murekkepli yerde harmonik dolgu) silinir.
- Kova halka+birlesik sembol ve kucuk semboller: gercek alpha ile (out=dst*(1-a)+F*a).
- Isimler/mesaj/sahne referanstan aynen.
Cikti: out/master_<C>.png (776x1006), out/cover_<C>.png (1080x1350), out/master_meta.json
"""
import json, sys, time
import numpy as np
from PIL import Image
from scipy import ndimage, sparse
from scipy.sparse.linalg import spsolve

ROOT = __import__('pathlib').Path(__file__).resolve().parent
OPEN = (151, 171, 927, 1177)  # x0,y0,x1,y1 baski acikligi (1080x1350 kapak)
S = 0.4897074453362084; OX, OY = 12.405604724370676, 2.228360592509887
KP = (732, 101, 2268, 2149)  # Kova 05_WA_01 poster dikdortgeni
COLORS = {'MB': ('01_Cover.png', 'MIDNIGHT_BLUE'), 'DB': ('12_Deep_Black.png', 'DEEP_BLACK'),
          'CI': ('13_Champagne_Ivory.png', 'CHAMPAGNE_IVORY'), 'PW': ('14_Pure_White.png', 'PURE_WHITE'),
          'WP': ('15_Warm_Parchment.png', 'WARM_PARCHMENT')}
TEXT_Y = (725, 905)   # isim + mesaj bandi (baski koordinati) -- referanstan aynen kalir
GLYPH_Y = (630, 712)  # kucuk sembol satiri
GLYPH_ROI_X = ((150, 300), (470, 620))
RING_C, RING_R = (388.22, 403.51), 279.65   # referans halka (baski koordinati)
DST_C = ((258.0, 670.5), (522.5, 671.0))     # MB/DB'de olculen referans sembol merkezleri


def arr(p): return np.asarray(Image.open(p).convert('RGB')).astype(np.float64)


def local_bg(a, size=31):
    return np.stack([ndimage.median_filter(a[:, :, i], size=size) for i in range(3)], 2)


def ink(a, bg, thr):
    return np.abs(a - bg).max(2) > thr


def harmonic(img, mask):
    a = img.copy(); m = mask.copy(); m[[0, -1], :] = False; m[:, [0, -1]] = False
    ys, xs = np.where(m); n = len(ys)
    if not n: return a
    idx = -np.ones(m.shape, int); idx[ys, xs] = np.arange(n)
    rows = list(range(n)); cols = list(range(n)); vals = [4.0] * n; b = np.zeros((n, 3))
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nn = idx[ys + dy, xs + dx]; ins = nn >= 0
        rows += list(np.where(ins)[0]); cols += list(nn[ins]); vals += [-1.0] * int(ins.sum())
        out = ~ins; b[out] += a[ys[out] + dy, xs[out] + dx]
    A = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))
    a[ys, xs] = spsolve(A.tocsc(), b)
    return a


def matte(pix, bg, core_r=3):
    """Gercek alpha: d=|pix-bg|, yerel en guclu murekkep rengi F; a=d/dmax, F=bg+(pix-bg)/a."""
    d = np.linalg.norm(pix - bg, axis=2)
    dmax = ndimage.maximum_filter(d, size=2 * core_r + 1)
    a = np.clip(d / np.maximum(dmax, 1e-6), 0, 1)
    a[dmax < 12] = 0
    F = bg + (pix - bg) / np.maximum(a, 1e-3)[..., None]
    F = np.clip(F, 0, 255)
    return a, F


def components(mask, min_area):
    lab, n = ndimage.label(mask)
    if not n: return mask & False
    sz = ndimage.sum(mask, lab, range(1, n + 1))
    keep = np.where(sz >= min_area)[0] + 1
    return np.isin(lab, keep)


def kova_aligned(c):
    kn = COLORS[c][1]
    K = Image.open(ROOT / f'src/{c}/05_WA_01_TECH_PRODUCT_TRUTH_AQUARIUS_AQUARIUS_{kn}.jpg').convert('RGB').crop(KP)
    W, H = OPEN[2] - OPEN[0], OPEN[3] - OPEN[1]
    sw, sh = (KP[2] - KP[0]) * S, (KP[3] - KP[1]) * S
    Ks = K.resize((int(round(sw)), int(round(sh))), Image.LANCZOS)
    fx, fy = Ks.width / sw, Ks.height / sh
    kt = Ks.transform((W, H), Image.AFFINE, (fx, 0, -OX * fx, 0, fy, -OY * fy), resample=Image.BICUBIC)
    valid = np.zeros((H, W), bool)
    x0, y0 = int(np.ceil(OX)) + 1, int(np.ceil(OY)) + 1
    x1, y1 = int(OX + KP[2] * 0 + (KP[2] - KP[0]) * S) - 1, int(OY + (KP[3] - KP[1]) * S) - 1
    valid[y0:y1, x0:x1] = True
    return np.asarray(kt).astype(np.float64), valid


def build(c, cov=None, tag=None, rois=None, detect_dst=False):
    tag = tag or c
    if cov is None:
        cov = arr(ROOT / 'refs_centered' / COLORS[c][0])
    rois = rois or GLYPH_ROI_X
    R = cov[OPEN[1]:OPEN[3], OPEN[0]:OPEN[2]].copy()
    K, valid = kova_aligned(c)
    H, W = R.shape[:2]
    light = R[20:100, 40:730].mean() > 128
    thr = 18 if light else 30
    Rbg = local_bg(R); Kbg = local_bg(K)
    Rink = ink(R, Rbg, thr); Kink = ink(K, Kbg, thr) & valid
    # Cancer sanat: halka+sembol (y<TEXT_Y0) ve kucuk semboller (GLYPH_Y); yildizlar (kucuk) haric
    yy = np.arange(H)[:, None]
    zoneArt = (yy < GLYPH_Y[0])
    zoneGly = (yy >= GLYPH_Y[0]) & (yy < GLYPH_Y[1])
    xx = np.arange(W)[None, :]
    disk = np.hypot(xx - RING_C[0], yy - RING_C[1]) <= RING_R + 10
    roi = np.zeros((H, W), bool)
    for (a0, a1) in rois: roi[GLYPH_Y[0]:GLYPH_Y[1], a0:a1] = True
    R_art = components(Rink & zoneArt & disk, 60)
    R_gly = components(Rink & roi, 40)
    K_art = components(Kink & zoneArt & disk, 60)
    K_gly = components(Kink & roi, 40)
    K_txt = components(Kink & (yy >= GLYPH_Y[1]) & (xx > 20) & (xx < W - 20), 10)
    # ton eslemesi K->R (ikisinde de murekkepsiz zemin)
    both_bg = valid & ~ndimage.binary_dilation(Rink | Kink, iterations=4)
    Kt = K.copy(); tone = []
    for ch in range(3):
        x = K[..., ch][both_bg]; y = R[..., ch][both_bg]
        A = np.c_[x, np.ones_like(x)]; p = np.linalg.lstsq(A, y, rcond=None)[0]
        if not (0.7 <= p[0] <= 1.4) or x.std() < 4:
            p = np.array([1.0, float(np.median(y - x))])
        Kt[..., ch] = K[..., ch] * p[0] + p[1]; tone.append([float(p[0]), float(p[1])])
    Kt = np.clip(Kt, 0, 255)
    # 1) Cancer sanatini sil: tam bilesen bolgesi (dilate 3)
    rem = ndimage.binary_dilation(R_art | R_gly, iterations=4)
    kova_dirty = ndimage.binary_dilation(Kink, iterations=3) | ~valid
    clean = R.copy()
    fill_k = rem & ~kova_dirty
    clean[fill_k] = Kt[fill_k]
    clean = harmonic(clean, rem & kova_dirty)
    # 2) Kova halka + birlesik sembol: gercek alpha
    Kbg_raw = harmonic(K, ndimage.binary_dilation(K_art | K_gly | K_txt, iterations=3))
    a, F = matte(K, Kbg_raw)
    art_zone = ndimage.binary_dilation(K_art, iterations=2)
    aa = np.where(art_zone, a, 0)[..., None]
    out = clean * (1 - aa) + F * aa
    # 3) kucuk Kova sembolleri: gercek sinirlar, isim merkezlerine
    labK, nK = ndimage.label(K_gly)
    gbox = []
    for i in range(1, nK + 1):
        ys, xs = np.where(labK == i); gbox.append((xs.min(), xs.max(), ys.min(), ys.max()))
    # Aquarius sembolu iki dalga = iki bilesen; x'e gore sol/sag grupla
    gbox.sort()
    mid = 385
    groups = [[b for b in gbox if (b[0] + b[1]) / 2 < mid], [b for b in gbox if (b[0] + b[1]) / 2 >= mid]]
    labR, nR = ndimage.label(R_gly)
    rgroups = [[], []]
    for i in range(1, nR + 1):
        ys, xs = np.where(labR == i)
        rgroups[0 if xs.mean() < mid else 1].append((xs.min(), xs.max(), ys.min(), ys.max()))
    meta = {'tone': tone, 'glyph_src': [], 'glyph_dst_center': []}
    for side in (0, 1):
        g = groups[side]; r = rgroups[side]
        gx0, gx1 = min(b[0] for b in g), max(b[1] for b in g); gy0, gy1 = min(b[2] for b in g), max(b[3] for b in g)
        rx0, rx1 = min(b[0] for b in r), max(b[1] for b in r); ry0, ry1 = min(b[2] for b in r), max(b[3] for b in r)
        pad = 4
        sx0, sx1, sy0, sy1 = gx0 - pad, gx1 + pad + 1, gy0 - pad, gy1 + pad + 1
        patch_a = a[sy0:sy1, sx0:sx1] * ndimage.binary_dilation(K_gly, iterations=2)[sy0:sy1, sx0:sx1]
        patch_F = F[sy0:sy1, sx0:sx1]
        cxs, cys = (gx0 + gx1) / 2, (gy0 + gy1) / 2
        cxd, cyd = ((rx0 + rx1) / 2, (ry0 + ry1) / 2) if detect_dst else DST_C[side]
        dx, dy = int(round(cxd - cxs)), int(round(cyd - cys))
        ty0, tx0 = sy0 + dy, sx0 + dx
        dst = out[ty0:ty0 + patch_a.shape[0], tx0:tx0 + patch_a.shape[1]]
        pa = patch_a[..., None]
        out[ty0:ty0 + patch_a.shape[0], tx0:tx0 + patch_a.shape[1]] = dst * (1 - pa) + patch_F * pa
        meta['glyph_src'].append([int(gx0), int(gx1), int(gy0), int(gy1)])
        meta['glyph_dst_center'].append([float(cxd), float(cyd)])
        meta.setdefault('glyph_ref_box', []).append([int(rx0), int(rx1), int(ry0), int(ry1)])
    out = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    cover = cov.astype(np.uint8).copy()
    cover[OPEN[1]:OPEN[3], OPEN[0]:OPEN[2]] = out
    Image.fromarray(out).save(ROOT / f'out/master_{tag}.png')
    Image.fromarray(cover).save(ROOT / f'out/cover_{tag}.png')
    np.savez_compressed(ROOT / f'out/masks_{tag}.npz', R_art=R_art, R_gly=R_gly, K_art=K_art, K_gly=K_gly, rem=rem, Kt=Kt.astype(np.uint8))
    meta.update({'light': bool(light), 'thr': thr, 'R_art_px': int(R_art.sum()), 'K_art_px': int(K_art.sum()),
                 'harmonic_px': int((rem & kova_dirty).sum())})
    return meta


if __name__ == '__main__':
    cs = sys.argv[1:] or list(COLORS)
    t0 = time.time(); allm = {}
    for i, c in enumerate(cs, 1):
        allm[c] = build(c)
        el = time.time() - t0
        print(f'[{i}/{len(cs)}] %{100*i/len(cs):.0f} gecen {el:.0f}s kalan ~{el/i*(len(cs)-i):.0f}s  {c} {allm[c]}', flush=True)
    json.dump(allm, open(ROOT / 'out/master_meta.json', 'w'), indent=1)
