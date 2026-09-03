#!/usr/bin/env python3
"""
wp-tone-match: temiz bir zemini (kaynak) hedef wallpaper'in tonuna cevirir.

Kaynak murekkepsizdir (Canva temiz zemin), hedef (pilot wallpaper) murekkeplidir.
Olcum yalniz MUREKKEPSIZ piksellerden yapilir; kaynakta murekkep olmadigi icin
hayalet iz imkansizdir. Piksel kopyalama, maske ile yapistirma, inpaint YOK --
tek yapilan sey kanal basina bir ton egrisi uygulamak.

Yontem (kanal bazli):
  1. Hedefte murekkep maskesi: INK_RGB[ed] rengine uzaklik < INK_TOL, + INK_PAD px
     genisletme (kabartma parlamasi/golgesi). Kalan pikseller "murekkepsiz".
  2. Kaynak ve hedefin murekkepsiz piksellerinin kantilleri (Q_LO..Q_HI arasi
     QN adet) eslestirilir ve en kucuk kareler ile y = a*x + b uydurulur.
     Kantil eslesmesi kullanilir cunku iki zemin uzamsal olarak hizali degildir;
     piksel-piksel regresyon anlamsiz olurdu.
  3. Dogrusal uyumun kantil hatasi GAMMA_TRIGGER'i asarsa y = A*(x/255)^g*255 + B
     bicimi (log-log dogrusu) denenir ve hatayi dusuruyorsa o kullanilir.
QC (PASS/FAIL): donusturulmus kaynagin ortalama/std'si ile hedefin murekkepsiz
bolge ortalama/std'si arasindaki fark kanal basina < MEAN_TOL / STD_TOL.

Kullanim:
  wp_tone_match.py --src canva_clean.png --ref pilot.jpg --edition Midnight_Blue
                   --out PLATE_MB_PHONE_TONE.png [--report r.json]
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import imread, log  # noqa: E402
from wp_plate_pilot import INK_RGB  # noqa: E402

INK_TOL = 120        # murekkep rengine uzaklik (BGR oklid); altindakiler murekkep sayilir
INK_PAD = 25         # murekkep + 25 px: kabartma parlamasi/golgesi de olcum disi
Q_LO, Q_HI, QN = 1.0, 99.0, 99
GAMMA_TRIGGER = 1.5  # dogrusal uyumun kantil RMSE'si bunu asarsa gamma denenir
MEAN_TOL, STD_TOL = 3.0, 3.0


def ink_free_mask(img, ed):
    """Murekkep renginden uzak (ve murekkebe INK_PAD'den uzak) pikseller."""
    r, g, b = INK_RGB[ed]
    d = np.sqrt(((img.astype(np.float32) - np.array([b, g, r], np.float32)) ** 2).sum(axis=2))
    ink = (d < INK_TOL).astype(np.uint8)
    k = 2 * INK_PAD + 1
    ink = cv2.dilate(ink, np.ones((k, k), np.uint8))
    return (ink == 0)


def fit_channel(sv, tv):
    """Kantil eslesmesinden y = a*x + b; gerekirse y = A*(x/255)^g*255 + B."""
    qs = np.linspace(Q_LO, Q_HI, QN)
    xs = np.percentile(sv, qs).astype(np.float64)
    ys = np.percentile(tv, qs).astype(np.float64)
    a, b = np.polyfit(xs, ys, 1)
    rmse_lin = float(np.sqrt(((a * xs + b - ys) ** 2).mean()))
    fit = dict(kind="linear", a=float(a), b=float(b), rmse=rmse_lin)
    if rmse_lin > GAMMA_TRIGGER:
        x1 = np.clip(xs, 1e-3, None) / 255.0
        y1 = np.clip(ys, 1e-3, None) / 255.0
        g, c = np.polyfit(np.log(x1), np.log(y1), 1)       # log y = g*log x + c
        A = float(np.exp(c))
        pred = A * (x1 ** g) * 255.0
        rmse_g = float(np.sqrt(((pred - ys) ** 2).mean()))
        if rmse_g < rmse_lin:
            fit = dict(kind="gamma", A=A, g=float(g), rmse=rmse_g)
    return fit


def apply_fit(ch, fit):
    x = ch.astype(np.float32)
    if fit["kind"] == "linear":
        return fit["a"] * x + fit["b"]
    return fit["A"] * np.power(np.clip(x, 1e-3, None) / 255.0, fit["g"]) * 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="temiz zemin (murekkepsiz)")
    ap.add_argument("--ref", required=True, help="hedef ton kaynagi (pilot wallpaper)")
    ap.add_argument("--edition", default="Midnight_Blue")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", default="")
    a = ap.parse_args()

    src = imread(a.src)
    ref = imread(a.ref)
    if src.shape[:2] != ref.shape[:2]:
        log(f"NOT: olculer farkli (kaynak {src.shape[1]}x{src.shape[0]}, hedef {ref.shape[1]}x{ref.shape[0]}); "
            "ton eslesmesi hizalama gerektirmez, cikti kaynak olcusunde kalir.")
    sm = ink_free_mask(src, a.edition)          # kaynakta murekkep yok; yine de guvenlik
    tm = ink_free_mask(ref, a.edition)
    log(f"murekkepsiz piksel: kaynak {int(sm.sum())} ({100 * sm.mean():.1f}%), hedef {int(tm.sum())} ({100 * tm.mean():.1f}%)")

    out = np.zeros(src.shape, np.float32)
    fits = {}
    for i, name in enumerate(("B", "G", "R")):
        fit = fit_channel(src[..., i][sm], ref[..., i][tm])
        fits[name] = fit
        out[..., i] = apply_fit(src[..., i], fit)
        log(f"  {name}: {fit['kind']} " + (f"a={fit['a']:.4f} b={fit['b']:+.2f}" if fit["kind"] == "linear"
                                           else f"A={fit['A']:.4f} g={fit['g']:.4f}") + f"  kantil RMSE {fit['rmse']:.2f}")
    out_u8 = np.clip(np.round(out), 0, 255).astype(np.uint8)
    cv2.imwrite(a.out, out_u8, [cv2.IMWRITE_PNG_COMPRESSION, 3])

    qc = {}
    ok = True
    om = ink_free_mask(out_u8, a.edition)
    for i, name in enumerate(("B", "G", "R")):
        om_v = out_u8[..., i][om]; rv = ref[..., i][tm]
        dmean = float(om_v.mean() - rv.mean()); dstd = float(om_v.std() - rv.std())
        qc[name] = dict(out_mean=float(om_v.mean()), ref_mean=float(rv.mean()), d_mean=dmean,
                        out_std=float(om_v.std()), ref_std=float(rv.std()), d_std=dstd)
        ok &= abs(dmean) < MEAN_TOL and abs(dstd) < STD_TOL
        log(f"  QC {name}: ort {om_v.mean():6.2f} / {rv.mean():6.2f} (fark {dmean:+.2f}), "
            f"std {om_v.std():5.2f} / {rv.std():5.2f} (fark {dstd:+.2f})")
    rep = dict(src=Path(a.src).name, ref=Path(a.ref).name, edition=a.edition, out=Path(a.out).name,
               size=[out_u8.shape[1], out_u8.shape[0]], fits=fits, qc=qc, ok=bool(ok))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1))
    log(f"SONUC: {'PASS' if ok else 'FAIL'} -> {a.out}")
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
