"""AstroLoveArt 24 s vertical video v9 (1080x1920, 30 fps) for one zodiac pair. Approved design (Serdar, 12 Oct 2026, Gemini & Leo).

0-4.3 question "{A} & {B}, as one?" | 3.8-7.6 gold dust leaves the two signs and builds the merged symbol | 8.4-12 "Two signs /
Your shared symbol" | 11.6-15.4 names | 15.4-18.6 the poster forms around the symbol, the room lights up, camera pulls back |
18.8-19.8 wall dissolves into navy | 19.6-24 end card "Make it yours / ASTROLOVEART / On Etsy". Poster pixels only.
Reuses lib.py, layouts.py, fonts and PosterR from ../pin_v6, the question mark from ../ig_v6.

Usage:
  python3 video_uret.py --poster AstroLoveArt_Gemini_Leo_2000.jpg --a Gemini --b Leo --out cikti/ [--muzik muzik.m4a] [--kareler 2,5,8]
  --a = first sign of the pair key (LEFT small sign on the poster), --b = second (RIGHT).
  --muzik: final 24 s audio track (already shaped and at -16 LUFS); it is copied in without re-encoding.
  --kareler: only write these seconds as JPG frames (fast check), no video.
  --acilis A|B (K1 sample, 19 Oct 2026; default = approved v9 unchanged):
    A: frame 0 shows the merged symbol, the pair names and the question fully (no black opening); 0.6-1.4 s the symbol
       cross-fades into the question mark, then the approved animation continues unchanged.
    B: starts at the moment the merged symbol is complete (T_LAND_END + 1.0 s); the rest plays at the same speed; the
       end card is held so the video stays 24 s; same 0.9 s fade-out at the end.
  --acilis B1|C (19 Oct 2026; from 3 s on identical to B):
    B1: 0-0.8 s B's first frame with the top text ("Two signs / Your shared symbol") fully shown, merged symbol in the
        centre; 0.8-1.2 s soft cross-fade to the wall scene of the video (wall + real poster, full view, as at 18.6 s);
        2.7-3.0 s cross-fade back into B.
    C:  0-1.2 s the real poster on the wall (poster 90% of the frame width, its names readable); 1.2-1.5 s cross-fade
        into B; B from 1.5 s on.
Writes {a}-and-{b}-astroloveart-reel.mp4
"""
import argparse, json, os, subprocess, sys, time
import numpy as np, cv2
from PIL import Image
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import PchipInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pin_v6'))
import pin_uret as PU
import lib
import layouts as L

AS = os.path.join(HERE, 'assets')
W, H, FPS, DUR = 1080, 1920, 30, 24.0
NF = int(FPS * DUR); CY = 770; ZN = 1.03
SIGN_H, D = 120, 610


def ease(t, a, b):
    s = np.clip((t - a) / (b - a), 0, 1); return 0.5 - 0.5 * np.cos(np.pi * s)


A_HOLD, A_CROSS = 0.6, 1.4      # acilis A: symbol fully shown 0-0.6 s, cross-fade to the question mark until 1.4 s
T_END_FREEZE = 23.1              # end card is complete and still from here until the fade-out


def kaynak_t(t, acilis, t0):
    """Output time -> time on the approved v9 timeline. B: shifted by t0, end card held (no change for None / A)."""
    return min(t + t0, T_END_FREEZE) if acilis in ('B', 'B1', 'C') else t


def acilis_alfa(t, acilis):
    """Acilis A opening: weight of the full merged symbol (1 at frame 0, 0 from A_CROSS on)."""
    return 1 - ease(t, A_HOLD, A_CROSS) if acilis == 'A' else 0.0


def navy_glow(profile, cy_frac, gain=0.70, sigma=0.42):
    rs, prof = profile
    sm = np.stack([gaussian_filter1d(prof[:, c].astype(np.float64), 2.5, mode='nearest') for c in range(3)], 1)
    fine_r = np.linspace(rs[0], rs[-1], 2048)
    fine = np.stack([PchipInterpolator(rs, sm[:, c])(fine_r) for c in range(3)], 1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    r = np.sqrt(((xx - W / 2) / (W * 0.5)) ** 2 + ((yy - H * cy_frac) / (H * 0.5)) ** 2)
    out = np.stack([np.interp(r, fine_r, fine[:, c]) for c in range(3)], -1)
    out *= (1 + gain * np.exp(-(r / sigma) ** 2))[..., None]
    rng = np.random.default_rng(1)
    out += 1.5 * (rng.uniform(-0.5, 0.5, out.shape) + rng.uniform(-0.5, 0.5, out.shape))
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), 'RGB')


def build(poster_path, A, B, out_dir, muzik=None, kareler=None, bilgi=None, acilis=None):
    os.makedirs(out_dir, exist_ok=True)
    slug = f'{A.lower()}-and-{B.lower()}'
    P = PU.PosterR(poster_path)
    prof = P.bg_profile()
    BR = L.bright_ramp(P)
    Q = Image.open(os.path.join(HERE, '..', 'ig_v6', 'assets', 'soru_isareti_v6.png')).convert('RGBA')

    def text(t, frac, max_frac=0.88):
        return PU.fit(lambda s: lib.metal_text(t, s, BR), int(W * frac), W * max_frac)

    def brand(frac):
        return lib.metal_text('ASTROLOVEART', int(W * frac), BR, tracking=0.14, bevel=0.9)

    SA, SB, SW, R = PU.sign_pair(P, SIGN_H)
    Qv = PU.fit_center(PU.center_scaled(Q, 265 * Q.size[1] / 997, SA, SB, SIGN_H, 'q'), D, SA, SB)
    MER = PU.fit_center(PU.center_scaled(P.layer(P.merged, only_label=False), 380, SA, SB, SIGN_H), D, SA, SB)

    def orbit_base(cv):
        sw = SW
        lab_gap = 44
        lab_h = lib.metal_text(A.upper(), int(W * L.TYPE['label']['size']), BR, tracking=L.TYPE['label']['tracking'], bevel=0.9).size[1]
        rm = PU.ring_mask(D, max(1.6, sw * 0.30), -SIGN_H / 2 - 28, SIGN_H / 2 + lab_gap + lab_h + 26)
        lib.paste(cv, lib.metal_from_mask(rm, P.ramp, bevel=0.9), W / 2, CY, shadow=False)
        lib.paste(cv, SA, W / 2 - D / 2, CY); lib.paste(cv, SB, W / 2 + D / 2, CY)
        # labels may not reach the merged symbol that appears later in the centre
        PU.sign_labels(cv, W, D, CY + SIGN_H / 2 + lab_gap, MER.size[0], A, B, BR,
                       int(W * L.TYPE['label']['size']), L.TYPE['label']['tracking'])

    def full(layer, cx, cy, shadow=True):
        fr = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        w, h = layer.size; x = int(round(cx - w / 2)); y = int(round(cy - h / 2))
        if shadow:
            sh, pad = lib.soft_shadow(layer)
            tmp = Image.new('RGBA', (W, H), (0, 0, 0, 0)); tmp.paste(sh, (x - pad, y - pad + 3)); fr = Image.alpha_composite(fr, tmp)
        tmp = Image.new('RGBA', (W, H), (0, 0, 0, 0)); tmp.paste(layer, (x, y)); fr = Image.alpha_composite(fr, tmp)
        a = np.asarray(fr).astype(np.float32); return a[..., :3], a[..., 3] / 255

    def merge_layers(items):
        rgb = np.zeros((H, W, 3), np.float32); al = np.zeros((H, W), np.float32)
        for c, a in items:
            rgb = rgb * (1 - a[..., None]) + c * a[..., None]; al = al + a * (1 - al)
        return np.where(al[..., None] > 1e-4, rgb, 0), al

    def centred(layer):
        a_ = np.asarray(layer)[..., 3].astype(np.float32); yy, xx = np.mgrid[0:a_.shape[0], 0:a_.shape[1]]
        return W / 2 + (layer.size[0] / 2 - (xx * a_).sum() / a_.sum()) * 0.8, CY + (layer.size[1] / 2 - (yy * a_).sum() / a_.sum()) * 0.5

    # ---------- layers
    bg = navy_glow(prof, CY / H)
    base = bg.copy(); orbit_base(base)
    BASE = np.asarray(base).astype(np.float32); BG = np.asarray(bg).astype(np.float32)
    t1 = merge_layers([full(text(f'{A} & {B}, as one?', 0.084), W / 2, 330), full(text('Zodiac art with your names & message', 0.056), W / 2, 1190)])
    qx, qy = centred(Qv); LQ = full(Qv, qx, qy)
    mx, my = centred(MER); LM = full(MER, mx, my)
    tA = merge_layers([full(text('Two signs', 0.070), W / 2, 318), full(text('Your shared symbol', 0.070), W / 2, 404)])
    names = lib.scale_w(P.layer(P.names_row, only_label=False), round(W * 0.74))
    tB = merge_layers([full(names, W / 2, 1150), full(text('Your names, your message', 0.054), W / 2, 1272)])
    end = bg.copy()
    _e1, _e2, _e3 = text('Make it yours', 0.090), brand(0.046), text('On Etsy', 0.052)
    lib.paste(end, _e1, W / 2, CY - 130); lib.paste(end, _e2, W / 2, CY + 10, shadow=False); lib.paste(end, _e3, W / 2, CY + 135)
    END = np.asarray(end).astype(np.float32)
    kutu = json.load(open(os.path.join(AS, 'wall916_kutu.json')))
    PX, PY, PW, PH = kutu['PX'], kutu['PY'], kutu['PW'], kutu['PH']
    WALL = Image.open(os.path.join(AS, 'WALL916_2x_temiz.png')).convert('RGB')
    WALL.paste(Image.open(poster_path).convert('RGB').resize((round(PW), round(PH)), Image.LANCZOS), (round(PX), round(PY)))

    # ---------- dust: half from the left sign, half from the right sign, curved paths into the merged symbol
    rng = np.random.default_rng(5)
    N = 60000

    def ink(layer, cx, cy, n, thr=0.55):
        arr = np.asarray(layer).astype(np.float32)
        ys, xs = np.nonzero(arr[..., 3] / 255 > thr); i = rng.integers(0, len(xs), n)
        pos = np.stack([xs[i] - layer.size[0] / 2 + cx + rng.uniform(-.5, .5, n), ys[i] - layer.size[1] / 2 + cy + rng.uniform(-.5, .5, n)], 1)
        return pos, arr[ys[i], xs[i], :3]

    ax, ay = W / 2 - D / 2, CY; bx, by = W / 2 + D / 2, CY
    (pa, ca), (pb, cb) = ink(SA, ax, ay, N // 2), ink(SB, bx, by, N - N // 2)
    pm, cm = ink(MER, mx, my, N)
    o = np.argsort(pm[:, 0] + rng.normal(0, 18, N)); pm, cm = pm[o], cm[o]
    oa = np.argsort(pa[:, 1]); ob = np.argsort(pb[:, 1])
    p0 = np.concatenate([pa[oa], pb[ob]]); c0 = np.concatenate([ca[oa], cb[ob]])
    l1 = np.argsort(pm[:N // 2, 1]); r1 = np.argsort(pm[N // 2:, 1]) + N // 2
    p1 = np.concatenate([pm[l1], pm[r1]]); c1 = np.concatenate([cm[l1], cm[r1]])
    T_GO0, T_SPREAD = 3.8, 2.0
    t_go = T_GO0 + T_SPREAD * rng.uniform(0, 1, N) ** 0.9
    t_dur = 1.6 + rng.uniform(-0.2, 0.2, N)
    lift = rng.uniform(40, 140, N) * rng.choice([-1, 1], N, p=[0.35, 0.65])
    size_w = rng.uniform(0.35, 0.9, N)
    T_LAND_END = float((t_go + t_dur).max())

    def bezier(s, idx):
        a, b = p0[idx], p1[idx]
        ctrl = (a + b) / 2 + np.stack([np.zeros(len(a)), -lift[idx]], 1)
        return ((1 - s) ** 2)[:, None] * a + (2 * (1 - s) * s)[:, None] * ctrl + (s ** 2)[:, None] * b

    def splat4(pos, w, col):
        acc = np.zeros((H, W), np.float32); rgb = np.zeros((H, W, 3), np.float32)
        x, y = pos[:, 0], pos[:, 1]; x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
        for dx, dy, ww in [(0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)]:
            yy = np.clip(y0 + dy, 0, H - 1); xx = np.clip(x0 + dx, 0, W - 1); k = ww * w
            np.add.at(acc, (yy, xx), k)
            for c in range(3):
                np.add.at(rgb[..., c], (yy, xx), k * col[:, c])
        return acc, rgb

    def dust_and_reveal(t):
        s = np.clip((t - t_go) / t_dur, 0, 1)
        solid = ease(t, T_LAND_END - 0.3, T_LAND_END + 1.0)
        on = np.nonzero(t >= t_go)[0]
        if len(on) == 0 or solid >= 1:
            return None, solid ** 0.45
        ss = s[on]; e = ss * ss * (3 - 2 * ss)
        pos = bezier(e, on)
        col = c0[on] * (1 - e[:, None]) + c1[on] * e[:, None]
        shimmer = 0.85 + 0.15 * np.sin(t * 9 + on * 0.7)
        w = size_w[on] * np.minimum(1, ss / 0.12) * np.where(ss >= 1, 0.8 * shimmer, 1.0) * (1 - solid) ** 1.5
        acc, rgb = splat4(pos, w, col)
        acc_b = cv2.GaussianBlur(acc, (0, 0), 0.55); rgb_b = cv2.GaussianBlur(rgb, (0, 0), 0.55)
        colour = rgb_b / np.maximum(acc_b, 1e-6)[..., None]
        alpha = np.clip(acc_b * 1.6, 0, 1)
        glow_a = np.clip(cv2.GaussianBlur(acc, (0, 0), 3.0) * 0.5, 0, 0.35)
        glow_c = cv2.GaussianBlur(rgb, (0, 0), 3.0) / np.maximum(cv2.GaussianBlur(acc, (0, 0), 3.0), 1e-6)[..., None]
        return (alpha, colour, glow_a, glow_c), solid ** 0.45

    def zoom(img, z):
        if abs(z - 1) < 1e-4:
            return img
        cw, ch = W / z, H / z; x0 = (W - cw) / 2; y0 = (H - ch) / 2
        return np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))).astype(np.float32)

    T_G0, T_G1 = 13.9, 15.4

    def grown(t):
        g = 1 + (G - 1) * ease(t, T_G0, T_G1)
        lay = MER.resize((max(1, round(MER.size[0] * g)), max(1, round(MER.size[1] * g))), Image.LANCZOS)
        x, y = centred(lay)
        return full(lay, x, y)

    def navy(t, tam_ust=False):
        keep = 1 - ease(t, 14.4, 15.4)
        f = BG + (BASE - BG) * keep
        a1 = (1.0 if acilis == 'A' else ease(t, 0.3, 1.3)) * (1 - ease(t, 3.3, 4.3))
        ko = acilis_alfa(t, acilis)
        aq = (1 - ease(t, 3.4, 4.6)) * (1 - ko)
        d, reveal = dust_and_reveal(t)
        aA = 1.0 if tam_ust else ease(t, 8.4, 9.4) * (1 - ease(t, 11.0, 12.0))
        aB = ease(t, 11.6, 12.6) * keep
        lm = LM if (G <= 1.0 or t < T_G0) else grown(t)
        for (c, a), k in [(t1, a1), (LQ, aq), (lm, max(reveal, ko)), (tA, aA), (tB, aB)]:
            if np.any(np.asarray(k) > 0):
                al = a * k; f = f * (1 - al[..., None]) + c * al[..., None]
        if d is not None:
            alpha, colour, glow_a, glow_c = d
            f = f * (1 - glow_a[..., None]) + glow_c * glow_a[..., None]
            f = f * (1 - alpha[..., None]) + colour * alpha[..., None]
        return zoom(f, 1 + (ZN - 1) * ease(t, 0, 15.4))

    # ---------- wall: start on the poster's own symbol (same size and place as the navy symbol), then pull back
    sp = PW / P.w
    pcx = P.merged[1] + P.merged[3] / 2; pcy = P.merged[2] + P.merged[4] / 2
    # The orbit symbol is small (65%). To keep the match cut, the camera would have to start wider than the wall
    # image. Instead the symbol alone grows gently by G while the orbit, signs and names fade out (13.9-15.4 s),
    # so the poster's symbol appears at exactly the same size and place and the camera can still pull back.
    cw0 = W * sp / (MER.size[1] / (P.merged[4] + 20) * ZN)
    G = max(1.0, cw0 / 2160.0 * 1.12)                       # 12% headroom so a short pull-back always remains
    if G > 1.0:
        MER_G = MER.resize((round(MER.size[0] * G), round(MER.size[1] * G)), Image.LANCZOS)
    else:
        MER_G = MER
    mxg, myg = centred(MER_G)
    f_out = MER_G.size[1] / (P.merged[4] + 20) * ZN
    sx = W / 2 + (mxg - W / 2) * ZN; sy = H / 2 + (myg - H / 2) * ZN
    cw_a = W * sp / f_out
    if bilgi is not None:
        bilgi['sembol_buyume'] = round(G, 3)
    if bilgi is not None:
        bilgi['kamera_orani'] = round(cw_a / 2160, 3)
    # a very large symbol on the poster (ARIES_CAPRICORN) would need a crop wider than the wall image: start from the
    # full wall width (symbol then smaller than in the navy part by 1/kamera_orani); pairs below the limit are unchanged
    cw_a = min(cw_a, 2160.0); ch_a = cw_a * 16 / 9
    BOX_A = (PX + pcx * sp - sx * cw_a / W + cw_a / 2, PY + pcy * sp - sy * ch_a / H + ch_a / 2, cw_a)
    BOX_F = (1080.0, 1920.0, 2160.0)
    _yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def cam(t):
        e = ease(t, 16.6, 18.6)
        cx, cy, cw = [BOX_A[i] * (1 - e) + BOX_F[i] * e for i in range(3)]
        cw = min(float(cw), 2160.0); ch = min(cw * 16 / 9, 3840.0)   # float rounding may overshoot the wall by ~1e-13
        cy = float(np.clip(cy, ch / 2, 3840 - ch / 2)); cx = float(np.clip(cx, cw / 2, 2160 - cw / 2))
        return cx, cy, cw, ch

    def wall(t):
        cx, cy, cw, ch = cam(t)
        return np.asarray(WALL.resize((W, H), Image.LANCZOS, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))).astype(np.float32)

    def poster_mask(t, feather=6.0):
        cx, cy, cw, ch = cam(t); k = W / cw
        x0, y0 = (PX - (cx - cw / 2)) * k, (PY - (cy - ch / 2)) * k; x1, y1 = x0 + PW * k, y0 + PH * k
        mx_ = np.clip(np.minimum(_xx - x0, x1 - _xx) / feather + 0.5, 0, 1); my_ = np.clip(np.minimum(_yy - y0, y1 - _yy) / feather + 0.5, 0, 1)
        return mx_ * my_

    T_B0 = np.ceil((T_LAND_END + 1.0) * FPS) / FPS    # first frame with the merged symbol complete (dust gone)
    if bilgi is not None:
        bilgi.update(T_LAND_END=round(T_LAND_END, 3), T_B0=float(T_B0), acilis=acilis or 'eski',
                     sembol_kutu=[int(round(mx - MER.size[0] / 2)), int(round(my - MER.size[1] / 2)), MER.size[0], MER.size[1]],
                     etiket_y=int(CY + SIGN_H / 2 + 44), soru_y=330)
    def wall_box(cx, cy, cw):
        ch = cw * 16 / 9
        return np.asarray(WALL.resize((W, H), Image.LANCZOS, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))).astype(np.float32)

    C_BOX = (PX + PW / 2, PY + PH / 2, PW / 0.90)     # acilis C: poster 90% of the frame width, centred
    if bilgi is not None:
        k = W / C_BOX[2]; x0 = C_BOX[0] - C_BOX[2] / 2; y0 = C_BOX[1] - C_BOX[2] * 8 / 9
        nr = P.names_row
        bilgi['c_isim_kutu'] = [int(round((PX + nr[1] * sp - x0) * k)), int(round((PY + nr[2] * sp - y0) * k)),
                                int(round(nr[3] * sp * k)), int(round(nr[4] * sp * k))]
        bilgi['ust_yazi_y'] = [318, 404]
    ACIL = {}

    def acilis_kare(to, f):
        """B1 / C opening on top of B's frame f (output time to < 3 s); B unchanged from 3 s on."""
        if acilis == 'B1' and to < 3.0:
            if 'O' not in ACIL:
                ACIL['O'] = navy(T_B0, tam_ust=True); ACIL['W'] = wall(18.6)
            O, Wf = ACIL['O'], ACIL['W']
            if to < 0.8:
                return O
            if to < 1.2:
                u = ease(to, 0.8, 1.2); return O * (1 - u) + Wf * u
            if to < 2.7:
                return Wf
            u = ease(to, 2.7, 3.0); return Wf * (1 - u) + f * u
        if acilis == 'C' and to < 1.5:
            if 'C' not in ACIL:
                ACIL['C'] = wall_box(*C_BOX)
            if to < 1.2:
                return ACIL['C']
            u = ease(to, 1.2, 1.5); return ACIL['C'] * (1 - u) + f * u
        return f

    _g = np.random.default_rng(99)
    GRAIN = (_g.uniform(-0.5, 0.5, (H, W, 3)) + _g.uniform(-0.5, 0.5, (H, W, 3))).astype(np.float32)

    def frame(n):
        to = n / FPS
        t = kaynak_t(to, acilis, T_B0)
        if t < 15.4:
            f = navy(t)
        elif t < 18.4:
            pm = poster_mask(t)
            a = (pm * ease(t, 15.4, 16.6) + (1 - pm) * ease(t, 15.9, 18.4))[..., None]
            f = navy(t) * (1 - a) + wall(t) * a
        elif t < 18.8:
            f = wall(t)
        elif t < 19.8:
            u = ease(t, 18.8, 19.8); f = wall(t) * (1 - u) + BG * u
        else:
            v = ease(t, 19.6, 20.6); f = BG + (END - BG) * v
        f = acilis_kare(to, f)
        if acilis is None:
            f = f * ease(t, 0, 1.0) * (1 - ease(t, 23.1, 24.0)) if (t < 1.0 or t > 23.1) else f
        elif to > T_END_FREEZE:      # A and B: no black opening, same fade-out on the output clock
            f = f * (1 - ease(to, T_END_FREEZE, 24.0))
        r = np.random.default_rng(n)
        tpdf = r.uniform(-0.5, 0.5, f.shape) + r.uniform(-0.5, 0.5, f.shape)
        # fine static grain (3 levels) + light moving grain: no visible rings in the navy gradient, also after
        # Instagram/TikTok re-encoding (tested 12 Oct 2026); too small to be seen as noise
        return np.clip(f + GRAIN * 3.0 + tpdf * 0.6, 0, 255).astype(np.uint8)

    if kareler:
        outs = []
        for sec in kareler:
            p = os.path.join(out_dir, f'{slug}-kare_{sec:g}s.jpg')
            Image.fromarray(frame(int(round(sec * FPS)))).save(p, quality=95); outs.append(p)
        return outs

    tmp = os.path.join(out_dir, f'_{slug}_sessiz.mp4')
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'slow', '-tune', 'grain', '-aq-mode', '3', '-r', str(FPS), tmp],
                           stdin=subprocess.PIPE)
    t0 = time.time()
    for n in range(NF):
        enc.stdin.write(frame(n).tobytes())
        if n % 60 == 0 or n == NF - 1:
            el = time.time() - t0
            print(f'{slug}: {n + 1}/{NF} kare  %{100 * (n + 1) / NF:.0f}  gecen {el:.0f} sn  kalan {el / (n + 1) * (NF - n - 1):.0f} sn', flush=True)
    enc.stdin.close(); enc.wait()
    out = os.path.join(out_dir, f'{slug}-astroloveart-reel.mp4')
    if muzik:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-i', muzik, '-map', '0:v', '-map', '1:a', '-c', 'copy',
                        '-t', '24', '-movflags', '+faststart', out], check=True)
        os.remove(tmp)
    else:
        os.replace(tmp, out)
    return [out]


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--poster', required=True)
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--muzik')
    ap.add_argument('--kareler')
    ap.add_argument('--acilis', choices=['A', 'B', 'B1', 'C'])
    ap.add_argument('--bilgi', help='write layout/timing info (JSON) here')
    g = ap.parse_args()
    k = [float(x) for x in g.kareler.split(',')] if g.kareler else None
    bi = {} if g.bilgi else None
    print(build(g.poster, g.a, g.b, g.out, g.muzik, k, bi, g.acilis))
    if g.bilgi:
        json.dump(bi, open(g.bilgi, 'w'), indent=1)
