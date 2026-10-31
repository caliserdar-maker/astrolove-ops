#!/usr/bin/env python3
"""Kupa kart uretimi determinizm teshisi (Serdar 31 Eki karar 8a). ETSY YOK.
sha  : bir uretimin her ara dosyasi (gorunum/*.jpg, baski/*, z_*.png, k_*.npy) ve kartinin sha256'si + kosucu CPU (model, bayraklar) +
       kutuphane surumleri + (varsa) gece dosyasina karsi kart piksel farki ve farkin yeri (satir / sutun kutusu, fark > 16 pikselleri).
kiyas: iki (ya da daha cok) SHA_*.json -> ilk ayrisan asama (dosya listesi sirasi: gorunum -> baski -> zemin -> kart).
Kullanim: kart_determinizm.py sha --is <sahne dir> --out-kart <kart dir> [--gece <dir>] --etiket a --json SHA_a.json
          kart_determinizm.py kiyas SHA_a.json SHA_b.json [...]"""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path


def cpu():
    d = {}
    try:
        t = Path("/proc/cpuinfo").read_text()
        for ln in t.splitlines():
            if ln.startswith("model name") and "model" not in d:
                d["model"] = ln.split(":", 1)[1].strip()
            if ln.startswith("flags") and "flags" not in d:
                f = set(ln.split(":", 1)[1].split())
                d["simd"] = sorted(x for x in f if x.startswith(("avx", "sse4", "fma", "f16c", "amx")))
        d["cekirdek"] = t.count("processor\t:")
    except OSError:
        pass
    d["python"] = platform.python_version()
    d["libc"] = "-".join(platform.libc_ver())
    try:
        d["os"] = next(x.split("=", 1)[1].strip('"') for x in Path("/etc/os-release").read_text().splitlines() if x.startswith("PRETTY_NAME="))
    except (OSError, StopIteration):
        pass
    return d


def fark(a_yol, b_yol):
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(a_yol).convert("RGB")).astype(int)
    b = np.asarray(Image.open(b_yol).convert("RGB")).astype(int)
    if a.shape != b.shape:
        return dict(boyut=[list(a.shape), list(b.shape)])
    d = np.abs(a - b).max(2)
    ys, xs = np.nonzero(d > 16)
    return dict(ort=round(float(d.mean()), 4), max=int(d.max()), px_16=int(len(ys)),
                kutu=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(ys) else None)


def sha(a):
    import numpy, PIL, cv2
    s = Path(a.is_)
    dos = {}
    for alt in ("gorunum", "baski", "."):
        for p in sorted((s / alt).glob("*") if alt != "." else s.glob("*")):
            if p.is_file():
                dos[str(p.relative_to(s))] = hashlib.sha256(p.read_bytes()).hexdigest()
    kart = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(a.out_kart).glob("*_K0*.jpg"))}
    gece = {}
    if a.gece:
        for p in sorted(Path(a.out_kart).glob("*_K0*.jpg")):
            g = Path(a.gece) / p.name
            if g.is_file():
                gece[p.name] = dict(sha_esit=hashlib.sha256(g.read_bytes()).hexdigest() == kart[p.name], **fark(p, g))
    r = dict(etiket=a.etiket, cpu=cpu(), surum=dict(numpy=numpy.__version__, pillow=PIL.__version__, opencv=cv2.__version__),
             ara=dos, kart=kart, gece_fark=gece)
    Path(a.json).write_text(json.dumps(r, indent=1))
    print(json.dumps(dict(etiket=a.etiket, cpu=r["cpu"].get("model"), simd=r["cpu"].get("simd"), kart=kart, gece_fark=gece), indent=1))
    return 0


def kiyas(dosyalar):
    R = [json.loads(Path(f).read_text()) for f in dosyalar]
    ilk = R[0]
    sonuc = {}
    for r in R[1:]:
        farkli = [k for k in ilk["ara"] if ilk["ara"].get(k) != r["ara"].get(k)]
        sonuc[f"{ilk['etiket']}~{r['etiket']}"] = dict(cpu=[ilk["cpu"].get("model"), r["cpu"].get("model")],
                                                       ara_farkli=farkli, kart_farkli=[k for k in ilk["kart"] if ilk["kart"][k] != r["kart"].get(k)])
    print(json.dumps(sonuc, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="mod", required=True)
    s = sp.add_parser("sha")
    s.add_argument("--is", dest="is_", required=True)
    s.add_argument("--out-kart", required=True)
    s.add_argument("--gece", default="")
    s.add_argument("--etiket", required=True)
    s.add_argument("--json", required=True)
    k = sp.add_parser("kiyas")
    k.add_argument("dosyalar", nargs="+")
    a = ap.parse_args(argv)
    return sha(a) if a.mod == "sha" else kiyas(a.dosyalar)


if __name__ == "__main__":
    sys.exit(main())
