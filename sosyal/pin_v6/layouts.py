"""Minimal design-system helpers used by pin_uret.py (copied from the approved v6 build)."""
import numpy as np, cv2

TYPE = {
    'label': dict(size=0.036, tracking=0.20),   # small caps line under the signs
}


def bright_ramp(P):
    # small text uses the upper (lit) half of the poster's own gold ramp, so it stays readable
    r = P.ramp
    idx = np.linspace(110, 255, 256)
    return np.stack([np.interp(idx, np.arange(256), r[:, c]) for c in range(3)], 1)


def stroke_width(layer):
    a = (np.asarray(layer)[..., 3] > 128).astype(np.uint8)
    dt = cv2.distanceTransform(a, cv2.DIST_L2, 5)
    return 2 * np.percentile(dt[dt > 0], 75)
