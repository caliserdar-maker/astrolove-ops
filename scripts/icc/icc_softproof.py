#!/usr/bin/env python3
"""
ICC soft-proof olcumu (yerel; Actions yok, Etsy yok).

Girdi: baski dosyalari (gomulu profil yoksa sRGB varsayilir) + hedef baski
profili (ICC). Her dosya icin:
  - soft-proof: sRGB -> [proof: hedef profil] -> sRGB, rendering intent
    relative colorimetric, black point compensation ACIK (littleCMS
    SOFTPROOFING + BLACKPOINTCOMPENSATION).
  - deltaE (CIEDE2000): orijinal ile proof arasindaki fark, ortalama ve
    maksimum (Lab'a sRGB profiliyle donusturulur, D50).
  - gamut disi piksel yuzdesi: BPC KAPALI relative colorimetric ile hedefe
    donup geri donuldugunde deltaE00 > --gamut-esik (varsayilan 2.0) olan
    piksel orani (kirpilma olcusu).
  - yan yana PNG: solda profil oncesi, sagda soft-proof.

Kullanim:
  python icc_softproof.py --profile HPR.icc --src DIR --out DIR [--max-px 1500]
  python icc_softproof.py --self-test        # sRGB'yi proof olarak kullanir (dE ~ 0)
"""
import argparse
import csv
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageDraw

INTENT = ImageCms.Intent.RELATIVE_COLORIMETRIC
FIELDS = ["edisyon", "dosya", "px", "ort_deltaE00", "maks_deltaE00",
          "p95_deltaE00", "gamut_disi_yuzde", "gamut_esigi"]


def log(m):
    print(m, flush=True)


def srgb():
    return ImageCms.createProfile("sRGB")


def to_lab(im, src_profile):
    """Goruntuyu Lab'a cevirir; L 0..100, a/b -128..127 (float)."""
    lab_p = ImageCms.createProfile("LAB")
    tr = ImageCms.buildTransform(src_profile, lab_p, "RGB", "LAB",
                                 renderingIntent=INTENT,
                                 flags=ImageCms.Flags.BLACKPOINTCOMPENSATION)
    a = np.asarray(ImageCms.applyTransform(im, tr))
    L = a[..., 0].astype(np.float64) * 100.0 / 255.0
    ab = a[..., 1:3].view(np.int8).astype(np.float64)   # a/b isaretli saklanir (offset yok)
    return np.stack([L, ab[..., 0], ab[..., 1]], axis=-1)


def ciede2000(lab1, lab2):
    """CIEDE2000 (Sharma ve ark. 2005 formulasyonu), dizi girdisi."""
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cbar = (C1 + C2) / 2.0
    G = 0.5 * (1 - np.sqrt(Cbar ** 7 / (Cbar ** 7 + 25.0 ** 7 + 1e-12)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0
    dLp = L2 - L1
    dCp = C2p - C1p
    dhp = h2p - h1p
    dhp = np.where(dhp > 180, dhp - 360, np.where(dhp < -180, dhp + 360, dhp))
    dhp = np.where((C1p * C2p) == 0, 0.0, dhp)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2.0))
    Lbp = (L1 + L2) / 2.0
    Cbp = (C1p + C2p) / 2.0
    hsum, hdiff = h1p + h2p, np.abs(h1p - h2p)
    hbp = np.where(C1p * C2p == 0, hsum,
                   np.where(hdiff <= 180, hsum / 2.0,
                            np.where(hsum < 360, (hsum + 360) / 2.0, (hsum - 360) / 2.0)))
    T = (1 - 0.17 * np.cos(np.radians(hbp - 30))
         + 0.24 * np.cos(np.radians(2 * hbp))
         + 0.32 * np.cos(np.radians(3 * hbp + 6))
         - 0.20 * np.cos(np.radians(4 * hbp - 63)))
    dTheta = 30 * np.exp(-(((hbp - 275) / 25.0) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25.0 ** 7 + 1e-12))
    Sl = 1 + (0.015 * (Lbp - 50) ** 2) / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dTheta)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                   + Rt * (dCp / Sc) * (dHp / Sh))


def soft_proof(im, src_p, proof_p, bpc=True):
    flags = ImageCms.Flags.SOFTPROOFING
    if bpc:
        flags |= ImageCms.Flags.BLACKPOINTCOMPENSATION
    tr = ImageCms.buildProofTransform(src_p, src_p, proof_p, "RGB", "RGB",
                                      renderingIntent=INTENT,
                                      proofRenderingIntent=INTENT,
                                      flags=flags)
    return ImageCms.applyTransform(im, tr)


def side_by_side(before, after, title, path):
    w, h = before.size
    pad, bar = 24, 56
    canvas = Image.new("RGB", (w * 2 + pad * 3, h + bar + pad * 2), (245, 245, 245))
    canvas.paste(before, (pad, bar + pad // 2))
    canvas.paste(after, (pad * 2 + w, bar + pad // 2))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 16), f"{title}  |  SOL: profil oncesi (sRGB)   SAG: soft-proof (HPR)",
           fill=(20, 20, 20))
    canvas.save(path, "PNG", optimize=True)
    return path


def measure(path, proof_p, out_dir, max_px, gamut_thr):
    im = Image.open(path)
    icc = im.info.get("icc_profile")
    src_p = ImageCms.ImageCmsProfile(io.BytesIO(icc)) if icc else srgb()
    im = im.convert("RGB")
    full = im.size
    if max_px and max(im.size) > max_px:                 # olcum ve PNG icin kucult
        im = im.copy()
        im.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
    proof = soft_proof(im, src_p, proof_p, bpc=True)
    lab1, lab2 = to_lab(im, src_p), to_lab(proof, src_p)
    de = ciede2000(lab1, lab2)
    hard = soft_proof(im, src_p, proof_p, bpc=False)     # BPC kapali = kirpilma gorunur
    de_clip = ciede2000(lab1, to_lab(hard, src_p))
    png = side_by_side(im, proof, Path(path).stem, out_dir / f"ICC_{Path(path).stem}.png")
    return {
        "edisyon": Path(path).stem, "dosya": Path(path).name, "px": f"{full[0]}x{full[1]}",
        "ort_deltaE00": round(float(de.mean()), 2),
        "maks_deltaE00": round(float(de.max()), 2),
        "p95_deltaE00": round(float(np.percentile(de, 95)), 2),
        "gamut_disi_yuzde": round(float((de_clip > gamut_thr).mean() * 100), 2),
        "gamut_esigi": gamut_thr,
    }, png


# CIEDE2000 dogrulama ciftleri (Sharma, Wu, Dalal 2005 - Tablo 1)
DE_CASES = [
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 0.0000, -2.5000), 4.3065),
    ((50.0000, 2.5000, 0.0000), (73.0000, 25.0000, -18.0000), 27.1492),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.1736, 0.5854), 1.0000),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
]


def self_test():
    """(a) CIEDE2000 literatur ciftleri, (b) Lab kodlamasi, (c) proof=kaynak -> dE ~ 0."""
    for lab1, lab2, want in DE_CASES:
        got = float(ciede2000(np.array([lab1]), np.array([lab2]))[0])
        assert abs(got - want) < 0.02, (lab1, lab2, got, want)
    log(f"  CIEDE2000: {len(DE_CASES)}/{len(DE_CASES)} literatur cifti PASS")
    probe = Image.new("RGB", (3, 1))
    probe.putdata([(0, 0, 0), (128, 128, 128), (255, 255, 255)])
    lab = to_lab(probe, srgb())
    assert abs(lab[0, 0, 0] - 0) < 1 and abs(lab[0, 1, 0] - 53.6) < 1.5 and abs(lab[0, 2, 0] - 100) < 1, lab
    assert abs(lab[0, 1, 1]) < 2 and abs(lab[0, 1, 2]) < 2, lab      # notr gri: a,b ~ 0
    log(f"  Lab kodlamasi: siyah L={lab[0,0,0]:.1f} gri L={lab[0,1,0]:.1f} beyaz L={lab[0,2,0]:.1f} PASS")
    d = Path("/tmp/icc_selftest")
    (d / "src").mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    Image.fromarray(rng.integers(0, 256, (64, 48, 3), dtype=np.uint8)).save(d / "src/TEST.jpg", quality=95)
    row, png = measure(d / "src/TEST.jpg", srgb(), d, 0, 2.0)
    assert row["ort_deltaE00"] < 0.5 and row["gamut_disi_yuzde"] < 1.0, row
    assert Path(png).exists()
    log(f"self-test PASS: {row}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", help="hedef baski ICC profili (.icc)")
    ap.add_argument("--src", help="kaynak dosyalarin dizini")
    ap.add_argument("--out", default="out")
    ap.add_argument("--max-px", type=int, default=1500, help="0 = tam cozunurluk")
    ap.add_argument("--gamut-esik", type=float, default=2.0)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not (a.profile and a.src):
        sys.exit("HATA: --profile ve --src gerekli.")
    proof_p = ImageCms.ImageCmsProfile(a.profile)
    log(f"profil: {ImageCms.getProfileDescription(proof_p).strip()} "
        f"({ImageCms.getProfileInfo(proof_p).strip()[:60]})")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in sorted(Path(a.src).glob("*.jpg")):
        row, png = measure(p, proof_p, out, a.max_px, a.gamut_esik)
        rows.append(row)
        log(f"  {row['edisyon']:<18} ort dE {row['ort_deltaE00']:<6} maks {row['maks_deltaE00']:<6} "
            f"gamut disi %{row['gamut_disi_yuzde']}  -> {Path(png).name}")
    with (out / "ICC_TEST_REPORT.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    log(f"yazildi: {out / 'ICC_TEST_REPORT.csv'}")


if __name__ == "__main__":
    main()
