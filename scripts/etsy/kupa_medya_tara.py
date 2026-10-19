#!/usr/bin/env python3
"""KUPA medya taramasi (Drive'a yazmaz, Etsy'ye dokunmaz). rclone lsjson ciktilarindan cift basina karar:
YAZ = tam bir klasor, galeri 01-14 (her sira tek dosya) + video tek mp4; aksi halde ATLA (neden yazilir).

Kullanim: kupa_medya_tara.py <kok_dirs.json> <dosyalar.json> <cikti_dizini> <cift ...> [--haric CIFT=neden ...]
  kok_dirs.json : rclone lsjson "$K" --dirs-only
  dosyalar.json : rclone lsjson -R "$K" --files-only --include "/*/galeri/[01][0-9]_*.jpg" --include "/*/video/*.mp4"
Cikti: <cikti>/YAZ_LISTE.txt (bosluk ayrimli), <cikti>/ATLA.txt (CIFT|neden), <cikti>/INDIR.txt (rclone --files-from)
"""
import collections
import json
import re
import sys
from pathlib import Path

GALERI = re.compile(r"^([01][0-9])_.+\.jpg$")


def tara(kok, dosyalar, ciftler, haric):
    adet = collections.Counter(d["Name"] for d in kok if d.get("IsDir"))
    yollar = collections.defaultdict(list)
    for f in dosyalar:
        parca = f["Path"].split("/")
        if len(parca) == 3:
            yollar[parca[0]].append((parca[1], parca[2]))
    yaz, atla, indir = [], [], []
    for c in ciftler:
        if c in haric:
            atla.append((c, haric[c])); continue
        if adet[c] != 1:
            atla.append((c, f"Drive'da {adet[c]} klasor (1 olmali)")); continue
        g = [ad for alt, ad in yollar[c] if alt == "galeri" and GALERI.match(ad)]
        v = [ad for alt, ad in yollar[c] if alt == "video" and ad.endswith(".mp4")]
        sira = collections.Counter(int(GALERI.match(ad).group(1)) for ad in g)
        if sorted(sira) != list(range(1, 15)) or any(n != 1 for n in sira.values()) or len(v) != 1:
            atla.append((c, f"galeri {len(g)} dosya (01-14 tekil degil) / video {len(v)}")); continue
        yaz.append(c)
        indir += [f"{c}/galeri/{ad}" for ad in sorted(g)] + [f"{c}/video/{v[0]}"]
    return yaz, atla, indir


def main():
    a = sys.argv[1:]
    haric = {}
    if "--haric" in a:
        i = a.index("--haric")
        for h in a[i + 1:]:
            c, _, neden = h.partition("=")
            haric[c] = neden or "haric tutuldu"
        a = a[:i]
    kok, dosyalar, out, ciftler = json.load(open(a[0])), json.load(open(a[1])), Path(a[2]), a[3:]
    yaz, atla, indir = tara(kok, dosyalar, ciftler, haric)
    out.mkdir(parents=True, exist_ok=True)
    (out / "YAZ_LISTE.txt").write_text(" ".join(yaz) + "\n")
    (out / "ATLA.txt").write_text("".join(f"{c}|{n}\n" for c, n in atla))
    (out / "INDIR.txt").write_text("".join(f"{p}\n" for p in indir))
    print(f"medya: yaz {len(yaz)} | atla {len(atla)} {atla} | indirilecek dosya {len(indir)}")


if __name__ == "__main__":
    main()
