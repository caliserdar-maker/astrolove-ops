#!/usr/bin/env python3
"""
wp-bg-synth: referans wallpaper'in ZEMININI olcer ve ayni parametrelerle
sifirdan yeni zemin uretir. Referanstan hicbir piksel kopyalanmaz -> hayalet iz
imkansiz; uretilen zeminde murekkep de yoktur.

OLCUM (yalniz murekkepsiz pikseller; murekkep = INK_RGB'ye uzaklik < INK_TOL,
+ INK_PAD px genisletilmis):
  gradyan : elips radyal model r = sqrt(((x-cx)/ax)^2 + ((y-cy)/ay)^2); merkez ve
            yari eksenler kaba izgara aramasiyla (kucultulmus goruntude, artik
            en kucuk olacak sekilde) bulunur. Profil: r'nin RBINS kovasindaki
            kanal medyanlari (olculen egri; parametrik varsayim yok).
  yildizlar: gri - medyan(15) > STAR_THR tepe noktalari; sayi/megapiksel, alan,
            tepe parlakligi, BGR renk orani ve radyal yogunluk dagilimi.
  gren    : duzgun modelden (Gauss sigma NOISE_SIGMA) artik; kanal std'si ve
            sigma 2 bulaniklik sonrasi std orani (korelasyon uzunlugu vekili).

URETIM: hedef olcude normalize koordinatlarda profil yeniden orneklenir, olculen
korelasyona gore filtrelenmis Gauss greni eklenir, yildizlar olculen yogunluk/
boyut/parlaklik/radyal dagilima gore rastgele yerlestirilir (sabit tohum).

QC (PASS/FAIL): uretilen (murekkepsiz) ile referansin murekkepsiz bolgesi
arasinda kanal basina |ort|, |std|, |medyan| farki < TOL ve kantil RMSE < TOL.

Kullanim:
  wp_bg_synth.py --ref pilot_phone.jpg --edition Midnight_Blue \
      --sizes Phone,Tablet,Desktop,Watch --out-dir _out [--report r.json]
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from wp_mockup_common import DEVICES, imread, log
from wp_plate_pilot import INK_RGB

INK_TOL, INK_PAD = 120, 25
RBINS = 64            # radyal profil kovasi
SMALL_W = 320         # gradyan aramasi bu genislikte yapilir
NOISE_SIGMA = 8.0     # duzgun model = Gauss sigma 8 (bunun ustu "gren")
STAR_THR = 18         # gri - medyan(15) esigi
STAR_MAX_AREA = 40
TOL = 3.0
SEED = 20260903


def ink_free(img, ed):
    r, g, b = INK_RGB[ed]
    d = np.sqrt(((img.astype(np.float32) - np.array([b, g, r], np.float32)) ** 2).sum(axis=2))
    ink = cv2.dilate((d < INK_TOL).astype(np.uint8), np.ones((2 * INK_PAD + 1,) * 2, np.uint8))
    return ink == 0


def radial(shape, cx, cy, ax, ay):
    h, w = shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    return np.sqrt(((xs - cx * w) / (ax * w)) ** 2 + ((ys - cy * h) / (ay * h)) ** 2)


def fit_gradient(img, mask):
    """Elips radyal merkez/eksen aramasi + kanal profilleri (normalize koordinat)."""
    h, w = img.shape[:2]
    sw = SMALL_W; sh = max(1, int(round(h * sw / w)))
    small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA).astype(np.float32)
    smask = cv2.resize(mask.astype(np.uint8) * 255, (sw, sh), interpolation=cv2.INTER_AREA) > 200
    gray = small.mean(axis=2)
    best = None
    for cx in np.linspace(0.30, 0.70, 9):
        for cy in np.linspace(0.15, 0.85, 15):
            for ax in (0.5, 0.75, 1.0, 1.5):
                for ay in (0.5, 0.75, 1.0, 1.5):
                    r = radial((sh, sw), cx, cy, ax, ay)
                    rn = np.clip(r / max(r[smask].max(), 1e-6), 0, 1)
                    idx = np.clip((rn * (RBINS - 1)).astype(int), 0, RBINS - 1)
                    prof = np.zeros(RBINS, np.float32); cnt = np.zeros(RBINS, np.float32)
                    np.add.at(prof, idx[smask], gray[smask]); np.add.at(cnt, idx[smask], 1)
                    ok = cnt > 20
                    if ok.sum() < RBINS // 2:
                        continue
                    prof[ok] /= cnt[ok]
                    pred = np.interp(rn, np.arange(RBINS)[ok] / (RBINS - 1), prof[ok])
                    res = float(np.sqrt(((gray[smask] - pred[smask]) ** 2).mean()))
                    if best is None or res < best[0]:
                        best = (res, float(cx), float(cy), float(ax), float(ay))
    res, cx, cy, ax, ay = best
    r = radial((h, w), cx, cy, ax, ay)
    rmax = float(r[mask].max())
    rn = np.clip(r / rmax, 0, 1)
    idx = np.clip((rn * (RBINS - 1)).astype(int), 0, RBINS - 1)
    prof = np.zeros((RBINS, 3), np.float32)
    for c in range(3):
        s = np.zeros(RBINS, np.float32); cnt = np.zeros(RBINS, np.float32)
        np.add.at(s, idx[mask], img[..., c][mask].astype(np.float32)); np.add.at(cnt, idx[mask], 1)
        ok = cnt > 50
        xs = np.arange(RBINS)[ok] / (RBINS - 1)
        prof[:, c] = np.interp(np.arange(RBINS) / (RBINS - 1), xs, (s[ok] / cnt[ok]))
    return dict(cx=cx, cy=cy, ax=ax, ay=ay, rmse=res, profile=prof.tolist()), rn


def measure_stars(img, mask):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    top = cv2.subtract(gray, cv2.medianBlur(gray, 15))
    cand = ((top > STAR_THR) & mask).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(cand)
    areas, peaks, cols, pos = [], [], [], []
    for i in range(1, n):
        a = int(st[i, cv2.CC_STAT_AREA])
        if a > STAR_MAX_AREA:
            continue
        m = lab == i
        areas.append(a); peaks.append(float(top[m].max()))
        cols.append(img[m].mean(axis=0)); pos.append((float(cen[i][0]), float(cen[i][1])))
    if not areas:
        return dict(n=0, per_mpx=0.0)
    col = np.array(cols).mean(axis=0)
    return dict(n=len(areas), per_mpx=len(areas) / (img.shape[0] * img.shape[1] / 1e6),
                area_mean=float(np.mean(areas)), area_p90=float(np.percentile(areas, 90)),
                peak_mean=float(np.mean(peaks)), peak_std=float(np.std(peaks)),
                peak_p10=float(np.percentile(peaks, 10)), peak_p90=float(np.percentile(peaks, 90)),
                color_bgr=[float(v) for v in col], pos=pos)


def measure_noise(img, mask):
    f = img.astype(np.float32)
    resid = f - cv2.GaussianBlur(f, (0, 0), NOISE_SIGMA)
    out = {}
    for c, name in enumerate(("B", "G", "R")):
        v = resid[..., c][mask]
        b2 = cv2.GaussianBlur(resid[..., c], (0, 0), 2.0)[mask]
        out[name] = dict(std=float(v.std()), std_blur2=float(b2.std()))
    return out


def synth(size, grad, stars, noise, star_radial, rng):
    w, h = size
    r = radial((h, w), grad["cx"], grad["cy"], grad["ax"], grad["ay"])
    rn = np.clip(r / r.max(), 0, 1)
    prof = np.asarray(grad["profile"], np.float32)
    xs = np.arange(RBINS) / (RBINS - 1)
    out = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        out[..., c] = np.interp(rn, xs, prof[:, c])
    # gren: beyaz gurultu -> olculen korelasyona gore bulanik -> olculen std'ye olcekle
    for c, name in enumerate(("B", "G", "R")):
        st = noise[name]["std"]; ratio = noise[name]["std_blur2"] / max(st, 1e-6)
        sg = float(np.clip(0.6 / max(ratio, 1e-3) - 0.6, 0.0, 3.0))     # ratio kucukse daha ince gren
        nz = rng.standard_normal((h, w)).astype(np.float32)
        if sg > 0.05:
            nz = cv2.GaussianBlur(nz, (0, 0), sg)
        nz *= st / max(nz.std(), 1e-6)
        out[..., c] += nz
    # yildizlar: olculen yogunluk, radyal dagilim, alan ve tepe parlakligi
    n = int(round(stars.get("per_mpx", 0.0) * w * h / 1e6))
    if n and star_radial is not None:
        cdf = np.cumsum(star_radial); cdf = cdf / max(cdf[-1], 1e-9)
        col = np.asarray(stars["color_bgr"], np.float32); col = col / max(col.max(), 1e-6)
        for _ in range(n):
            rr = float(np.interp(rng.random(), cdf, np.linspace(0, 1, len(cdf))))
            th = rng.random() * 2 * np.pi
            x = int(round((grad["cx"] + rr * grad["ax"] * np.cos(th)) * w))
            y = int(round((grad["cy"] + rr * grad["ay"] * np.sin(th)) * h))
            if not (2 <= x < w - 2 and 2 <= y < h - 2):
                continue
            peak = float(np.clip(rng.normal(stars["peak_mean"], max(stars["peak_std"], 1.0)),
                                 stars["peak_p10"], stars["peak_p90"] * 1.2))
            rad = max(0.6, np.sqrt(max(stars["area_mean"], 1.0) / np.pi))
            yy, xx = np.mgrid[-3:4, -3:4].astype(np.float32)
            g = np.exp(-(xx ** 2 + yy ** 2) / (2 * rad ** 2))
            out[y - 3:y + 4, x - 3:x + 4] += (g[..., None] * col[None, None, :] * peak)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def star_radial_hist(stars, grad, shape, bins=12):
    if not stars.get("n"):
        return None
    h, w = shape
    hist = np.zeros(bins, np.float64)
    for (x, y) in stars["pos"]:
        rr = np.sqrt(((x - grad["cx"] * w) / (grad["ax"] * w)) ** 2 + ((y - grad["cy"] * h) / (grad["ay"] * h)) ** 2)
        hist[min(bins - 1, int(rr / max(1e-6, 1.0) * bins) if rr < 1 else bins - 1)] += 1
    return (hist / max(hist.sum(), 1)).tolist()


def qc(gen, ref, mask):
    """Ayni uzamsal destek uzerinde karsilastirma: referansin murekkepsiz maskesi
    (gerekirse hedef olcuye buyutulup) uretilen zemine de uygulanir. Aksi halde
    uretilenin merkezi (referansta murekkep altinda kalan, olculemeyen bolge)
    karsilastirmaya girip yapay sapma yaratiyordu (kosu 1: B ort +3.54)."""
    gm = mask
    if gen.shape[:2] != mask.shape:
        gm = cv2.resize(mask.astype(np.uint8) * 255, (gen.shape[1], gen.shape[0]),
                        interpolation=cv2.INTER_NEAREST) > 127
    out = {}
    ok = True
    qs = np.linspace(1, 99, 99)
    for c, name in enumerate(("B", "G", "R")):
        gv = gen[..., c][gm].astype(np.float32)
        rv = ref[..., c][mask].astype(np.float32)
        d_mean = float(gv.mean() - rv.mean()); d_std = float(gv.std() - rv.std())
        d_med = float(np.median(gv) - np.median(rv))
        qrmse = float(np.sqrt(((np.percentile(gv, qs) - np.percentile(rv, qs)) ** 2).mean()))
        out[name] = dict(d_mean=d_mean, d_std=d_std, d_median=d_med, quantile_rmse=qrmse,
                         gen_mean=float(gv.mean()), ref_mean=float(rv.mean()))
        ok &= abs(d_mean) < TOL and abs(d_std) < TOL and abs(d_med) < TOL and qrmse < TOL
    out["ok"] = bool(ok)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="olcum icin referans wallpaper")
    ap.add_argument("--edition", default="Midnight_Blue")
    ap.add_argument("--sizes", default="Phone,Tablet,Desktop,Watch")
    ap.add_argument("--prefix", default="BG_MB")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--report", default="")
    a = ap.parse_args()

    ref = imread(a.ref)
    mask = ink_free(ref, a.edition)
    log(f"referans {Path(a.ref).name} {ref.shape[1]}x{ref.shape[0]}, murekkepsiz %{100 * mask.mean():.1f}")
    grad, _ = fit_gradient(ref, mask)
    log(f"gradyan: merkez ({grad['cx']:.3f},{grad['cy']:.3f}) eksen ({grad['ax']:.2f},{grad['ay']:.2f}) "
        f"artik RMSE {grad['rmse']:.2f}; profil {np.asarray(grad['profile'])[0].round(1).tolist()} -> "
        f"{np.asarray(grad['profile'])[-1].round(1).tolist()}")
    stars = measure_stars(ref, mask)
    sr = star_radial_hist(stars, grad, ref.shape[:2])
    log(f"yildiz: {stars.get('n', 0)} adet ({stars.get('per_mpx', 0):.1f}/Mpx), alan ort {stars.get('area_mean', 0):.1f}, "
        f"tepe {stars.get('peak_mean', 0):.1f}+-{stars.get('peak_std', 0):.1f}, renk BGR {np.round(stars.get('color_bgr', [0, 0, 0]), 1).tolist()}")
    noise = measure_noise(ref, mask)
    log("gren std (B/G/R): " + " / ".join(f"{noise[n]['std']:.2f}" for n in ("B", "G", "R")))

    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    rep = dict(ref=Path(a.ref).name, edition=a.edition,
               gradient={k: v for k, v in grad.items() if k != "profile"},
               profile_ends=[np.asarray(grad["profile"])[0].tolist(), np.asarray(grad["profile"])[-1].tolist()],
               stars={k: v for k, v in stars.items() if k != "pos"}, noise=noise, devices={}, ok=True)
    for dev in [d for d in a.sizes.split(",") if d]:
        w, h = DEVICES[dev]
        gen = synth((w, h), grad, stars, noise, sr, rng)
        name = f"{a.prefix}_{dev.upper()}.png"
        cv2.imwrite(str(out_dir / name), gen, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        q = qc(gen, ref, mask)
        rep["devices"][dev] = dict(file=name, size=[w, h], qc=q)
        rep["ok"] &= q["ok"]
        log(f"  {dev:8s} -> {name} | " + ", ".join(
            f"{n}: ort {q[n]['d_mean']:+.2f} std {q[n]['d_std']:+.2f} med {q[n]['d_median']:+.2f} qRMSE {q[n]['quantile_rmse']:.2f}"
            for n in ("B", "G", "R")) + f" -> {'PASS' if q['ok'] else 'FAIL'}")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1))
    log(f"SONUC: {'PASS' if rep['ok'] else 'FAIL'}")
    raise SystemExit(0 if rep["ok"] else 2)


if __name__ == "__main__":
    main()
