#!/usr/bin/env python3
"""by_boy altin yamasi testi (Serdar 31 Eki, Gorev C: YD boylu siparis altin duzeltmesi). ETSY YOK.
by_poster (bizim-yilimiz-v3 KOD_REF) gold_layer doku ortalamasi float32 SCALE 2'de koyulasiyordu (1_Starlit_Altin_1024: SCALE 1 4:5
R 231,6 = onayli 8x10; SCALE 2 4:5 149,1, 2:3 124,3, 3:4 139,8). by_boy.YAMA ortalamayi onayli 8x10 degerine sabitler.
T1 yama kaliplari beklenen sayida (by_boy.yamala DUR vermez)
T2 SCALE 2, her oran ailesi: yamali ortalama = onayli 8x10 ortalamasi (fark <= 0,05); yamasiz SCALE 2 ortalamasi R'de >= 50 koyu (hata canli)
T3 SCALE 1, 4:5 (onayli 8x10): yamali gold_layer ciktisi yamasizla birebir ayni (8x10 gorunumu degismez)
Calistir: python3 scripts/siparis_by/test_by_boy_altin.py   (git fetch KOD_REF gerekir)"""
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import by_boy as B  # noqa: E402

KOD_REF = "e3d168cef6821d0bd6b6ae5b4dfba503025c5753"   # by-boy-ornek / by-ornek3 / by-zemin-8x10 ile ayni
TEX = "z/Altin_1024x1024/1_Starlit_Altin_1024.png"
sonuc = []


def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))


def git_show(yol):
    subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", KOD_REF], check=True, cwd=HERE)
    return subprocess.run(["git", "show", f"{KOD_REF}:{yol}"], check=True, capture_output=True, cwd=HERE).stdout


def gold_fn(src, scale, W, H):
    """kaynaktaki gold_layer fonksiyonunu yalitip SCALE / W / H ile calistirilabilir hale getirir"""
    i = src.index("def gold_layer"); j = src.index("\ndef ", i + 10)
    ns = dict(np=np, cv2=cv2, Image=Image, SCALE=scale, W=W, H=H, P=lambda v: v * scale)
    exec(src[i:j], ns)
    return ns["gold_layer"]


def ortalama_yakala(src, scale, W, H, tex):
    """gold_layer'in kullandigi 'mean' degerini kaynaktan aynen hesaplar (fonksiyon govdesi mean satirina kadar)"""
    i = src.index("def gold_layer"); j = src.index("    a = np.clip(a / low", i)
    govde = src[i:j].split("\n", 1)[1] + "    return mean\n"
    ns = dict(np=np, cv2=cv2, Image=Image, SCALE=scale, W=W, H=H, P=lambda v: v * scale)
    exec("def _m(tex, k=1.0):\n" + govde, ns)
    return ns["_m"](tex)


def main():
    import tempfile
    t = Path(tempfile.mkdtemp(prefix="by_altin_"))
    (t / "tex.png").write_bytes(git_show(TEX))
    asil = git_show("kod/by_poster.py").decode("utf-8")
    try:
        yamali = B.yamala(asil)
        k("T1 yama kaliplari beklenen sayida (altin yamasi dahil)", "_d1 = np.concatenate" in yamali and "_d1 = np.concatenate" not in asil)
    except SystemExit as e:
        k("T1 yama kaliplari beklenen sayida (altin yamasi dahil)", False, str(e)); yamali = asil
    tex = str(t / "tex.png")
    onay = ortalama_yakala(asil, 1, 2400, 3000, tex)
    for aile, oran in B.AILE.items():
        W = 4800; H = round(W / oran)
        y = ortalama_yakala(yamali, 2, W, H, tex)
        e = ortalama_yakala(asil, 2, W, H, tex)
        k(f"T2 SCALE 2 {aile}: yamali ortalama = onayli 8x10 {onay.round(1).tolist()} (yamasiz {e.round(1).tolist()})",
          np.abs(y - onay).max() <= 0.05 and onay[0] - e[0] >= 50, y.round(2).tolist())
    g0, g1 = gold_fn(asil, 1, 2400, 3000), gold_fn(yamali, 1, 2400, 3000)
    a0, a1 = g0(tex), g1(tex)
    k("T3 SCALE 1 4:5 (onayli 8x10): yamali gold_layer ciktisi birebir ayni", a0.shape == a1.shape and np.array_equal(a0, a1),
      f"en buyuk fark {float(np.abs(a0 - a1).max())}")
    print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
    return 0 if all(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
