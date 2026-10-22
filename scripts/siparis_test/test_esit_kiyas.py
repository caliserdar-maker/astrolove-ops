#!/usr/bin/env python3
"""esit_kiyas v2 sahte testi: poster taban kurali, dosya kumesi, siparis.json, kupa bayt."""
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

B = pathlib.Path(__file__).resolve().parent / "esit_kiyas.py"


def poster_dir(kok, ad, gurultu, olcu="8x10", fazla=False, isim="EMILY", seed=0):
    d = kok / ad; d.mkdir()
    rs = np.random.default_rng(seed)
    for n, (w, h) in (("AstroLoveArt_Cancer_Libra.jpg", (720, 1080)), (f"AstroLoveArt_Cancer_Libra_{olcu}.jpg", (240, 300)),
                      ("AstroLoveArt_Cancer_Libra_2000.jpg", (200, 300))):
        a = np.full((h, w, 3), 100, np.int16) + rs.integers(-gurultu, gurultu + 1, (h, w, 3))
        Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(d / n, dpi=(300, 300), quality=100, subsampling=0)
    if fazla:
        Image.new("RGB", (480, 600)).save(d / "AstroLoveArt_Cancer_Libra_16x20.jpg", dpi=(300, 300))
    (d / "siparis.json").write_text(json.dumps(dict(cift="CANCER_LIBRA", isim1=isim, isim2="JAMES", tagline="x", olcu=olcu)))
    (d / "KAPI.json").write_text('{"a": "PASS"}')
    return d


def kos(*arg):
    r = subprocess.run([sys.executable, str(B), *map(str, arg)], capture_output=True, text=True)
    return r.returncode, r.stdout


def main():
    import esit_kiyas as m
    m.beklenen_boyut  # noqa: B018
    t = pathlib.Path(tempfile.mkdtemp())
    s = []
    # boyutlar kucuk tutuldu: beklenen boyut kontrolunu test icin olcu tablosu disinda dogrulamak gerekir -> m.beklenen_boyut testi ayri
    s.append(("beklenen_boyut 8x10 = 2400x3000, A4 yok", m.beklenen_boyut("8x10") == (2400, 3000) and m.beklenen_boyut("A4") is None))
    tb = [poster_dir(t, f"t{i}", 3, seed=i) for i in range(3)]
    e, y = poster_dir(t, "e", 3, seed=0), poster_dir(t, "y", 3, seed=1)   # taban t0/t1 ile ayni icerik: fark = bir taban cifti
    kod, out = kos("--tur", "poster", "--eski", e, "--yeni", y, "--out", t / "o1", "--agac-eski", "AB", "--agac-yeni", "AB", "--taban", *tb)
    son = out.strip().splitlines()[-1]
    s.append(("poster: yalniz boyut beklentisi FAIL (kucuk sahte dosya), taban/agac/isim/dosya kurallari gecer", kod == 1
              and "> taban" not in son and "kod agaci" not in son and "siparis.json" not in son and "dosya kumesi" not in son
              and "beklenen (2400, 3000)" in son))
    y2 = poster_dir(t, "y2", 40, seed=12)
    kod, out = kos("--tur", "poster", "--eski", e, "--yeni", y2, "--out", t / "o2", "--agac-eski", "AB", "--agac-yeni", "AB", "--taban", *tb)
    s.append(("poster: fark > taban -> FAIL", kod == 1 and "> taban" in out))
    kod, out = kos("--tur", "poster", "--eski", e, "--yeni", y, "--out", t / "o3", "--agac-eski", "AB", "--agac-yeni", "AC", "--taban", *tb)
    s.append(("poster: kod agaci farkli -> FAIL", kod == 1 and "kod agaci" in out))
    y3 = poster_dir(t, "y3", 3, fazla=True, seed=13)
    kod, out = kos("--tur", "poster", "--eski", e, "--yeni", y3, "--out", t / "o4", "--agac-eski", "AB", "--agac-yeni", "AB", "--taban", *tb)
    s.append(("poster: fazla (eski testten kalan) dosya -> FAIL", kod == 1 and "dosya kumesi" in out))
    y4 = poster_dir(t, "y4", 3, isim="ANNA", seed=14)
    kod, out = kos("--tur", "poster", "--eski", e, "--yeni", y4, "--out", t / "o5", "--agac-eski", "AB", "--agac-yeni", "AB", "--taban", *tb)
    s.append(("poster: isim farkli -> FAIL", kod == 1 and "siparis.json" in out))
    kod, out = kos("--tur", "poster", "--eski", e, "--yeni", y, "--out", t / "o6", "--agac-eski", "AB", "--agac-yeni", "AB", "--taban", *tb[:2])
    s.append(("poster: taban < 3 kosu -> FAIL", kod == 1 and "en az 3" in out))
    for k in ("ke", "ky"):
        d = t / k / "9000000001" / "1"; d.mkdir(parents=True)
        Image.new("RGB", (2700, 1050), (5, 5, 5)).save(d / "BASKI_A_11oz_2700x1050.png")
        Image.new("RGB", (200, 100), (5, 5, 5)).save(d / "ONIZLEME_A.jpg", quality=90)
        (d / "OZET.json").write_text('{"sonuc": "PASS"}'); (d / "PRINTFUL_TASLAK.json").write_text('{"a": 1}')
    kod, out = kos("--tur", "kupa", "--eski", t / "ke", "--yeni", t / "ky", "--out", t / "o7")
    s.append(("kupa: bayt birebir PASS", kod == 0))
    (t / "ky" / "9000000001" / "1" / "PRINTFUL_TASLAK.json").write_text('{"a": 2}')
    kod, out = kos("--tur", "kupa", "--eski", t / "ke", "--yeni", t / "ky", "--out", t / "o8")
    s.append(("kupa: PRINTFUL_TASLAK farkli -> FAIL", kod == 1))
    for ad, ok in s:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(ok for _, ok in s)
    print(f"esit_kiyas testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    sys.path.insert(0, str(B.parent))
    main()
