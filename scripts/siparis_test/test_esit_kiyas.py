#!/usr/bin/env python3
"""esit_kiyas v2 sahte testi (ayni surec; boyut sabitleri kucultulur): poster PASS + FAIL yollari, kupa bayt / durum / 15 oz.
Dosya bicimleri gercekle ayni: KAPI.json ust duzey PASS (siparis_kapi.py), OZET.json durum (kupa_siparis.py), SURE.json gpt_ref."""
import contextlib
import io
import json
import pathlib
import shutil
import sys
import tempfile

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import esit_kiyas as m  # noqa: E402

RE, RY = "a" * 40, "b" * 40


def poster_dir(kok, ad, gurultu, ref=RE, olcu="8x10", fazla=False, isim="EMILY", seed=0, kapi=True, boyut_bozuk=False):
    d = kok / ad; d.mkdir()
    rs = np.random.default_rng(seed)
    for n, (w, h) in (("AstroLoveArt_Cancer_Libra.jpg", m.ANA), (f"AstroLoveArt_Cancer_Libra_{olcu}.jpg", m.OLCU[olcu]),
                      ("AstroLoveArt_Cancer_Libra_2000.jpg", m.ONIZ)):
        if boyut_bozuk and n.endswith(f"_{olcu}.jpg"):
            w += 1
        a = np.full((h, w, 3), 100, np.int16) + rs.integers(-gurultu, gurultu + 1, (h, w, 3))
        Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(d / n, dpi=(300, 300), quality=100, subsampling=0)
    if fazla:
        Image.new("RGB", (8, 10)).save(d / "AstroLoveArt_Cancer_Libra_16x20.jpg", dpi=(300, 300))
    (d / "siparis.json").write_text(json.dumps(dict(cift="CANCER_LIBRA", isim1=isim, isim2="JAMES", tagline="x", olcu=olcu)))
    (d / "KAPI.json").write_text(json.dumps({"a": {"PASS": kapi}, "PASS": kapi}))
    (d / "SURE.json").write_text(json.dumps({"gpt_ref": ref}))
    return d


def kos(*arg):
    sys.argv = ["x", *map(str, arg)]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            m.main(); kod = 0
        except SystemExit as e:
            kod = e.code
    return kod, buf.getvalue()


def main():
    m.ANA, m.ONIZ, m.OLCU = (72, 108), (20, 30), {"8x10": (24, 30)}     # kucuk sahte dosyalar (oranlar gercekle ayni)
    t = pathlib.Path(tempfile.mkdtemp())
    s = []
    tb = [poster_dir(t, f"t{i}", 3, seed=i) for i in range(3)]
    e = poster_dir(t, "e", 3, seed=0)
    y = poster_dir(t, "y", 3, ref=RY, seed=1)
    ort = ["--tur", "poster", "--agac-eski", "AB", "--agac-yeni", "AB", "--ref-eski", RE, "--ref-yeni", RY]
    kod, out = kos(*ort, "--eski", e, "--yeni", y, "--out", t / "o0", "--taban", *tb)
    s.append(("poster PASS: agac ayni, 3 dosya, boyut/DPI, siparis.json, KAPI PASS, fark <= taban", kod == 0))
    kod, out = kos(*ort, "--eski", e, "--yeni", poster_dir(t, "y2", 40, ref=RY, seed=12), "--out", t / "o1", "--taban", *tb)
    s.append(("fark > taban -> FAIL", kod == 1 and "> taban" in out))
    kod, out = kos(*[x if x != "AB" or i != ort.index("--agac-yeni") + 1 else "AC" for i, x in enumerate(ort)],
                   "--eski", e, "--yeni", y, "--out", t / "o2", "--taban", *tb)
    s.append(("kod agaci farkli -> FAIL", kod == 1 and "kod agaci" in out))
    kod, out = kos(*ort, "--eski", e, "--yeni", poster_dir(t, "y3", 3, ref=RY, fazla=True, seed=1), "--out", t / "o3", "--taban", *tb)
    s.append(("eski testten kalan fazla dosya -> FAIL", kod == 1 and "dosya kumesi" in out))
    kod, out = kos(*ort, "--eski", e, "--yeni", poster_dir(t, "y4", 3, ref=RY, isim="ANNA", seed=1), "--out", t / "o4", "--taban", *tb)
    s.append(("isim farkli -> FAIL", kod == 1 and "siparis.json" in out))
    kod, out = kos(*ort, "--eski", e, "--yeni", y, "--out", t / "o5", "--taban", *tb[:2])
    s.append(("taban < 3 kosu -> FAIL", kod == 1 and "en az 3" in out))
    kod, out = kos(*ort, "--eski", e, "--yeni", poster_dir(t, "y5", 3, ref=RY, kapi=False, seed=1), "--out", t / "o6", "--taban", *tb)
    s.append(("KAPI.json PASS false -> FAIL (metin aramasi degil)", kod == 1 and "yeni KAPI.json" in out))
    tb_k = [poster_dir(t, "tk0", 3, isim="ANNA", seed=0), *tb[1:]]
    kod, out = kos(*ort, "--eski", e, "--yeni", y, "--out", t / "o7", "--taban", *tb_k)
    s.append(("taban kosusu farkli isim -> FAIL", kod == 1 and "siparis.json" in out))
    tb_r = [poster_dir(t, "tr0", 3, ref=RY, seed=0), *tb[1:]]
    kod, out = kos(*ort, "--eski", e, "--yeni", y, "--out", t / "o8", "--taban", *tb_r)
    s.append(("taban kosusu yanlis ref -> FAIL", kod == 1 and "taban0 SURE.json" in out))
    kod, out = kos(*ort, "--eski", e, "--yeni", y, "--out", t / "o9", "--taban", e, *tb[1:])
    s.append(("eski klasoru tabanda -> FAIL", kod == 1 and "ayri olmali" in out))
    kod, out = kos(*ort, "--eski", e, "--yeni", poster_dir(t, "y6", 3, ref=RY, seed=1, boyut_bozuk=True), "--out", t / "o10", "--taban", *tb)
    s.append(("teslim boyutu yanlis -> FAIL", kod == 1 and "beklenen" in out))
    kod, out = kos("--tur", "poster", "--agac-eski", "AB", "--agac-yeni", "AB", "--ref-eski", RE, "--ref-yeni", RE,
                   "--eski", e, "--yeni", y, "--out", t / "o11", "--taban", *tb)
    s.append(("ref_eski = ref_yeni -> FAIL", kod == 1 and "ayni" in out))
    for k in ("ke", "ky"):
        d = t / k / "9000000001" / "1"; d.mkdir(parents=True)
        Image.new("RGB", (2700, 1140), (5, 5, 5)).save(d / "BASKI_A_Orange_Blossom_15oz_2700x1140.png")
        Image.new("RGB", (200, 100), (5, 5, 5)).save(d / "ONIZLEME_A_15oz.jpg", quality=90)
        (d / "OZET.json").write_text('{"durum": "PASS"}'); (d / "PRINTFUL_TASLAK.json").write_text('{"a": 1}')
    kod, out = kos("--tur", "kupa", "--eski", t / "ke", "--yeni", t / "ky", "--out", t / "k0")
    s.append(("kupa 15 oz: bayt birebir + OZET durum PASS", kod == 0))
    (t / "ky" / "9000000001" / "1" / "PRINTFUL_TASLAK.json").write_text('{"a": 2}')
    kod, out = kos("--tur", "kupa", "--eski", t / "ke", "--yeni", t / "ky", "--out", t / "k1")
    s.append(("kupa PRINTFUL_TASLAK farkli -> FAIL", kod == 1))
    shutil.rmtree(t, ignore_errors=True)
    for ad, ok in s:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(ok for _, ok in s)
    print(f"esit_kiyas testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
