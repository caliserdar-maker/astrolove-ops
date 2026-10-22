#!/usr/bin/env python3
"""P0.5 (Serdar 22 Eki, daraltilmis): verilen git agaclarindaki gorseller (jpg/png/webp/gif/pdf ilk sayfa yok; mp4 1 kare/sn)
OCR ile metne cevrilir; metin YALNIZ <out>/<blob sha12>.txt'ye yazilir (log'a sayi). Desen taramasi desen_uret.py --tara-ek ile.
Kullanim: gorsel_ocr.py --out DIZIN AGAC [AGAC ...]   (AGAC: git deposu ya da worktree yolu)"""
import argparse
import os
import pathlib
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
UZANTI = {"jpg", "jpeg", "png", "webp", "gif"}
VIDEO = {"mp4", "mov"}
KENAR = 1600                     # OCR oncesi en uzun kenar (yerel olcum: 260 gorsel 73 sn, 4 is parcacigi)


def bloblar(agac):
    out = {}
    for x in subprocess.run(["git", "-C", agac, "ls-tree", "-r", "-z", "HEAD"], capture_output=True, check=True).stdout.decode().split("\0"):
        if not x:
            continue
        meta, yol = x.split("\t", 1)
        uz = yol.rsplit(".", 1)[-1].lower()
        if uz in UZANTI | VIDEO:
            out[meta.split()[2]] = uz
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("agac", nargs="+")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    tum = {}
    for agac in a.agac:
        for sha, uz in bloblar(agac).items():
            tum.setdefault(sha, (uz, agac))
    tmp = pathlib.Path(tempfile.mkdtemp())
    env = dict(os.environ, OMP_THREAD_LIMIT="1")

    def bir(item):
        sha, (uz, agac) = item
        ham = tmp / f"{sha}.{uz}"
        ham.write_bytes(subprocess.run(["git", "-C", agac, "cat-file", "-p", sha], capture_output=True, check=True).stdout)
        if uz in VIDEO:
            kd = tmp / f"{sha}_k"; kd.mkdir()
            subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(ham), "-vf", "fps=1", str(kd / "%03d.png")], capture_output=True)
            metin = []
            for k in sorted(kd.glob("*.png")):
                r = subprocess.run(["tesseract", str(k), "-", "--psm", "11"], capture_output=True, env=env, timeout=120)
                metin.append(r.stdout.decode("utf-8", "replace"))
            (out / f"{sha[:12]}.txt").write_text("\n".join(metin), encoding="utf-8")
            return "video"
        try:
            im = Image.open(ham); im.draft("L", (KENAR, KENAR)); im = im.convert("L"); im.thumbnail((KENAR, KENAR))
            k = tmp / f"{sha}_k.png"; im.save(k)
        except Exception:
            return "acilamadi"
        r = subprocess.run(["tesseract", str(k), "-", "--psm", "11"], capture_output=True, env=env, timeout=120)
        (out / f"{sha[:12]}.txt").write_text(r.stdout.decode("utf-8", "replace"), encoding="utf-8")
        return "gorsel"

    t0 = time.time(); sonuc = {}
    with ThreadPoolExecutor(4) as ex:
        for i, s in enumerate(ex.map(bir, tum.items()), 1):
            sonuc[s] = sonuc.get(s, 0) + 1
            if i % 50 == 0 or i == len(tum):
                g = time.time() - t0
                print(f"[{i}/{len(tum)}] %{100 * i // len(tum)} gecen {g:.0f} sn kalan ~{g / i * (len(tum) - i):.0f} sn", flush=True)
    print(f"GORSEL_OCR agac {len(a.agac)} | tekil blob {len(tum)} | {sonuc}")


if __name__ == "__main__":
    main()
