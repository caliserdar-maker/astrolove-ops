"""AstroLoveArt social template library (static visuals).
All poster pixels are only cut, scaled and moved. Added text and operators are
rendered as metallic gold using a colour ramp sampled from the poster's own
merged symbol (single texture unity rule)."""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

FONT_R = None
FONT_I = None


def set_fonts(reg, ita):
    global FONT_R, FONT_I
    FONT_R, FONT_I = reg, ita


# ---------------------------------------------------------------- poster
class Poster:
    def __init__(self, path):
        self.img = np.asarray(Image.open(path).convert('RGB')).astype(np.float32)
        self.h, self.w = self.img.shape[:2]
        R, B = self.img[..., 0], self.img[..., 2]
        core = ((R - B) > 40).astype(np.uint8)
        self.core = core
        # background estimate: inpaint the dilated gold area (downscaled for speed)
        dil = cv2.dilate(core, np.ones((9, 9), np.uint8))
        s = 0.25
        small = cv2.resize(self.img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        sm = cv2.resize(dil, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
        sm = cv2.dilate(sm, np.ones((3, 3), np.uint8))
        bgs = cv2.inpaint(np.clip(small, 0, 255).astype(np.uint8), sm, 6, cv2.INPAINT_TELEA)
        self.bg = cv2.resize(bgs.astype(np.float32), (self.w, self.h), interpolation=cv2.INTER_CUBIC)
        # alpha from red-channel excess over background (navy has almost no red)
        ex = self.img[..., 0] - self.bg[..., 0]
        a = np.clip((ex - 4.0) / 40.0, 0, 1)
        self.alpha = a
        n, lab, st, _ = cv2.connectedComponentsWithStats(core, 8)
        self.comps = [(i, *st[i]) for i in range(1, n)]
        self.lab = lab
        self._find_parts()
        self.ramp = self._gold_ramp()

    def _find_parts(self):
        comps = sorted(self.comps, key=lambda c: -c[5])
        W, H = self.w, self.h
        # merged symbol = largest component that is not the thin ring
        cand = [c for c in comps if c[5] > 0.01 * W * H * 0.1]
        ring = None
        merged = None
        for c in comps[:4]:
            i, x, y, w, h, ar = c
            fill = ar / float(w * h)
            if fill < 0.03 and w > 0.6 * W:
                ring = c
            elif merged is None and fill >= 0.03:
                merged = c
        self.ring, self.merged = ring, merged
        my = merged[2] + merged[4]
        below = [c for c in comps if c[2] > my and c[5] > 300]
        rows = {}
        for c in below:
            key = None
            for k in rows:
                if abs(k - (c[2] + c[4] / 2)) < 60:
                    key = k
            rows.setdefault(key if key is not None else c[2] + c[4] / 2, []).append(c)
        ks = sorted(rows)
        # row 0: two small signs; row 1: names; row 2: message
        signs = sorted(rows[ks[0]], key=lambda c: c[1])
        self.sign_a, self.sign_b = signs[0], signs[-1]
        self.names_row = self._union(rows[ks[1]])
        self.msg_row = self._union([c for k in ks[2:] for c in rows[k]])

    @staticmethod
    def _union(cs):
        x0 = min(c[1] for c in cs); y0 = min(c[2] for c in cs)
        x1 = max(c[1] + c[3] for c in cs); y1 = max(c[2] + c[4] for c in cs)
        return (None, x0, y0, x1 - x0, y1 - y0, 0)

    def layer(self, comp, pad=10, only_label=True):
        """RGBA cut-out with clean alpha and background un-mixed colour."""
        _, x, y, w, h, _ = comp
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(self.w, x + w + pad), min(self.h, y + h + pad)
        img = self.img[y0:y1, x0:x1]
        bg = self.bg[y0:y1, x0:x1]
        a = self.alpha[y0:y1, x0:x1].copy()
        if only_label and comp[0] is not None:
            keep = (self.lab[y0:y1, x0:x1] == comp[0]).astype(np.uint8)
            keep = cv2.dilate(keep, np.ones((7, 7), np.uint8))
            a *= keep
        else:
            # exclude ring pixels from region layers
            if self.ring is not None:
                rk = (self.lab[y0:y1, x0:x1] == self.ring[0]).astype(np.uint8)
                rk = cv2.dilate(rk, np.ones((7, 7), np.uint8))
                a *= (1 - rk)
        aa = np.maximum(a, 1e-3)[..., None]
        col = (img - (1 - a[..., None]) * bg) / aa
        col = np.clip(col, 0, 255)
        out = np.dstack([col, a * 255]).astype(np.uint8)
        return Image.fromarray(out, 'RGBA')

    def _gold_ramp(self):
        i = self.merged[0]
        m = (self.lab == i) & (self.alpha > 0.98)
        px = self.img[m]
        lum = px @ np.array([0.299, 0.587, 0.114])
        order = np.argsort(lum)
        px = px[order]
        q = np.linspace(0, len(px) - 1, 256).astype(int)
        ramp = px[q]
        ramp = cv2.GaussianBlur(ramp.reshape(1, 256, 3), (1, 9), 0).reshape(256, 3)
        return ramp

    def bg_profile(self):
        """median background colour by normalised radius from poster centre."""
        yy, xx = np.mgrid[0:self.h:8, 0:self.w:8]
        cy, cx = self.h * 0.40, self.w * 0.5
        r = np.sqrt(((xx - cx) / (self.w * 0.5)) ** 2 + ((yy - cy) / (self.h * 0.5)) ** 2)
        bg = self.bg[::8, ::8]
        core = self.core[::8, ::8] == 0
        bins = np.linspace(0, 1.5, 31)
        prof = []
        for k in range(30):
            sel = core & (r >= bins[k]) & (r < bins[k + 1])
            prof.append(np.median(bg[sel], axis=0) if sel.sum() > 20 else prof[-1])
        return bins[:-1] + 0.025, np.array(prof)


# ---------------------------------------------------------------- canvas
def navy_canvas(W, H, profile, cy_frac=0.42, spread=1.0):
    rs, prof = profile
    # smooth the measured profile (no kinks between bins) and evaluate it as a smooth curve
    from scipy.ndimage import gaussian_filter1d
    sm = np.stack([gaussian_filter1d(prof[:, c].astype(np.float64), 2.5, mode='nearest') for c in range(3)], 1)
    fine_r = np.linspace(rs[0], rs[-1], 2048)
    from scipy.interpolate import PchipInterpolator
    fine = np.stack([PchipInterpolator(rs, sm[:, c])(fine_r) for c in range(3)], 1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    cx, cy = W / 2, H * cy_frac
    r = np.sqrt(((xx - cx) / (W * 0.5)) ** 2 + ((yy - cy) / (H * 0.5)) ** 2) / spread
    out = np.zeros((H, W, 3), np.float64)
    for c in range(3):
        out[..., c] = np.interp(r, fine_r, fine[:, c])
    # triangular dither of +-1 level before rounding: breaks 8-bit steps into fine grain
    rng = np.random.default_rng(1)
    out += 1.5 * (rng.uniform(-0.5, 0.5, out.shape) + rng.uniform(-0.5, 0.5, out.shape))
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), 'RGB')


# ---------------------------------------------------------------- metallic rendering
def metal_from_mask(mask, ramp, bevel=None, light=(-0.55, -0.75), contrast=1.0):
    """mask: float 0..1 (H,W). returns RGBA Image with bevelled gold."""
    m = mask.astype(np.float32)
    if bevel is None:
        # estimate stroke width from distance transform
        dt = cv2.distanceTransform((m > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
        sw = np.percentile(dt[dt > 0], 90) if (dt > 0).any() else 2
        bevel = max(1.0, sw * 0.9)
    h = cv2.GaussianBlur(m, (0, 0), bevel)
    gy, gx = np.gradient(h)
    k = 2.2 * bevel
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(h)
    nl = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    lx, ly = light
    lz = 0.62
    ln = np.sqrt(lx * lx + ly * ly + lz * lz)
    d = (nx * lx + ny * ly + nz * lz) / (nl * ln)
    # base tone: slight vertical gradient inside glyph, bright face, shaded bevel
    H = m.shape[0]
    vert = np.linspace(0.08, -0.08, H)[:, None]
    t = np.clip(0.50 + (d - lz / ln) * 1.25 * contrast + vert, 0, 1)
    # specular
    spec = np.clip((d - 0.93) / 0.07, 0, 1) ** 2
    idx = (t * 255).astype(int)
    col = ramp[idx]
    col = col + spec[..., None] * 60
    col = np.clip(col, 0, 255)
    rgba = np.dstack([col, np.clip(m, 0, 1) * 255]).astype(np.uint8)
    return Image.fromarray(rgba, 'RGBA')


def text_mask(text, font_path, size, tracking=0.0, ss=4):
    """render text at ss x supersampling, tracking in em. returns float mask."""
    f = ImageFont.truetype(font_path, size * ss)
    x = 0
    pos = []
    for ch in text:
        pos.append(x)
        x += f.getlength(ch) + tracking * size * ss
    pad = int(size * ss * 0.4)
    W = int(x - tracking * size * ss) + 2 * pad
    asc, desc = f.getmetrics()
    Hh = asc + desc + 2 * pad
    im = Image.new('L', (W, Hh), 0)
    d = ImageDraw.Draw(im)
    if tracking == 0:
        d.text((pad, pad), text, font=f, fill=255)
    else:
        for ch, px in zip(text, pos):
            d.text((px + pad, pad), ch, font=f, fill=255)
    im = im.resize((max(1, W // ss), max(1, Hh // ss)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    return a


def trim(img):
    a = np.asarray(img)[..., 3]
    ys, xs = np.where(a > 8)
    return img.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def metal_text(text, size, ramp, italic=False, tracking=0.0, bevel=None):
    m = text_mask(text, FONT_I if italic else FONT_R, size, tracking)
    if bevel is None:
        bevel = max(0.8, size / 40.0)
    return trim(metal_from_mask(m, ramp, bevel=bevel))


def soft_shadow(layer, blur=6, opacity=0.55, offset=(0, 3)):
    a = np.asarray(layer)[..., 3].astype(np.float32) / 255
    pad = int(blur * 3) + max(abs(offset[0]), abs(offset[1]))
    A = np.pad(a, pad)
    A = cv2.GaussianBlur(A, (0, 0), blur) * opacity
    sh = np.zeros(A.shape + (4,), np.uint8)
    sh[..., 3] = np.clip(A * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(sh, 'RGBA'), pad


def paste(canvas, layer, cx, cy, shadow=True, anchor='center'):
    """paste RGBA layer centred at (cx, cy) on RGB canvas (in place)."""
    w, h = layer.size
    x = int(round(cx - w / 2)) if anchor == 'center' else int(round(cx))
    y = int(round(cy - h / 2))
    if shadow:
        sh, pad = soft_shadow(layer)
        canvas.paste(sh, (x - pad + 0, y - pad + 3), sh)
    canvas.paste(layer, (x, y), layer)
    return (x, y, x + w, y + h)


def scale_h(layer, h):
    w0, h0 = layer.size
    return layer.resize((max(1, round(w0 * h / h0)), int(h)), Image.LANCZOS)


def scale_w(layer, w):
    w0, h0 = layer.size
    return layer.resize((int(w), max(1, round(h0 * w / w0))), Image.LANCZOS)


# ---------------------------------------------------------------- operators drawn geometrically
def op_mask(kind, size, stroke):
    ss = 4
    S = size * ss
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    t = stroke * ss
    c = S / 2
    if kind == '+':
        d.rounded_rectangle((c - S * 0.42, c - t / 2, c + S * 0.42, c + t / 2), radius=t / 2, fill=255)
        d.rounded_rectangle((c - t / 2, c - S * 0.42, c + t / 2, c + S * 0.42), radius=t / 2, fill=255)
    elif kind == '=':
        g = S * 0.16
        d.rounded_rectangle((c - S * 0.42, c - g - t / 2, c + S * 0.42, c - g + t / 2), radius=t / 2, fill=255)
        d.rounded_rectangle((c - S * 0.42, c + g - t / 2, c + S * 0.42, c + g + t / 2), radius=t / 2, fill=255)
    im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255
