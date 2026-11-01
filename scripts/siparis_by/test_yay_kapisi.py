#!/usr/bin/env python3
"""YD ORNEK3 yay kapisi testi (Denetim 20261101B, bagimsiz inceleme 1 Kas: kapi kendini dogruluyordu). ETSY YOK, Drive yok.
Eski 8x10 zemin (KOD_REF) uzerinden yol cikarilir, sentetik zemine (yildiz / toz noktali) cizilir, by_ornek3.yay_kapisi 8x10:
  Y1 normal cizim PASS
  Y2 6 px dar tumsek (sigma 0,5 derece) FAIL     Y3 3 px tumsek (sigma 1 derece) FAIL
  Y4 15 derece eksik yay FAIL (kapsama)            Y5 sol uc 1 derece kisa FAIL     Y6 sag uc 1 derece kisa FAIL
  Y7 zemin noktalari sonucu degistirmez (iki tohum ayni)
Calistir: python3 scripts/siparis_by/test_yay_kapisi.py   (git fetch KOD_REF gerekir; ~3-5 dk)"""
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import by_ornek3 as B  # noqa: E402
import yay_olcum as YO  # noqa: E402

KOD_REF = "e3d168cef6821d0bd6b6ae5b4dfba503025c5753"
sonuc = []


def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""), flush=True)


def main():
    subprocess.run(["git", "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", KOD_REF], check=True, cwd=HERE)
    t = Path(tempfile.mkdtemp(prefix="yay_kapi_")) / "eski.png"
    t.write_bytes(subprocess.run(["git", "show", f"{KOD_REF}:{B.ESKI}"], check=True, capture_output=True, cwd=HERE).stdout)
    eski = np.asarray(Image.open(t).convert("RGB"))
    o = B.olc(eski); yol = YO.eski_yol(eski, B.YOL_SEED); o["yay"].update(B.yay_profil(eski, yol))

    def zemin(tohum):
        rng = np.random.default_rng(tohum)
        z = np.full((3000, 2400, 3), (5, 14, 31), np.float32) + rng.normal(0, 4, (3000, 2400, 1))
        for _ in range(600):
            x, y = rng.integers(0, 2400), rng.integers(0, 3000); cv2.circle(z, (int(x), int(y)), 2, (200, 180, 120), -1)
        return np.clip(z, 0, 255).astype(np.uint8)
    Z = zemin(1)
    yol["sonum"], _ = B.uc_kalibre(o, yol, zem=Z)

    def kapi(yl, zem=Z):
        s8 = B.isiltilar(B.yildiz(B.yay(zem, 1.0, 0, o, yl)[0], 1.0, 0, eski)[0], 1.0, 0, eski, yl)[0]
        return B.yay_kapisi(s8, None, yol, z8=zem)[0]["8x10"]
    v = kapi(yol)
    k(f"Y1 normal cizim PASS ({v['cikti_px']}, kapsama {v['kapsama']}, uclar {v['uclar']['fark_derece']})", v["pass_"])
    a = np.arange(1440) * 0.25
    for ad, deg in (("Y2 6 px dar tumsek @210", dict(r=np.asarray(yol["r"]) + 6 * np.exp(-0.5 * ((a - 210) / 0.5) ** 2))),
                    ("Y3 3 px tumsek @315", dict(r=np.asarray(yol["r"]) + 3 * np.exp(-0.5 * ((a - 315) / 1.0) ** 2))),
                    ("Y4 15 derece eksik 200-215", dict(sonum=np.where((a > 200) & (a < 215), 0, np.asarray(yol["sonum"])))),
                    ("Y5 sol uc 1 derece kisa", dict(sonum=np.where((a > 135) & (a < 137.0), 0, np.asarray(yol["sonum"])))),
                    ("Y6 sag uc 1 derece kisa", dict(sonum=np.where((a > 39.75) & (a < 42), 0, np.asarray(yol["sonum"]))))):
        w = kapi(dict(yol, **deg))
        k(f"{ad} -> FAIL ({w['cikti_px']['en_buyuk']} px, kapsama {w['kapsama']}, uc farki {w['uclar']['fark_derece']})", not w["pass_"])
    v2 = kapi(yol, zemin(2))
    k(f"Y7 zemin noktalari sonucu degistirmez ({v['cikti_px']['en_buyuk']} / {v2['cikti_px']['en_buyuk']})",
      abs(v["cikti_px"]["en_buyuk"] - v2["cikti_px"]["en_buyuk"]) < 0.05 and v2["pass_"])
    print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
    return 0 if all(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
