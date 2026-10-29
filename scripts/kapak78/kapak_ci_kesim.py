#!/usr/bin/env python3
"""Galeri v11 CI kapak / PW karti icin poster kesimleri (Merkez 29 Eki; Canva uretimi bu dosyalara bagli). Etsy yok.
Kaynak: TEMP/POSTER_GALERI_V10/20261026_181944/<CIFT>_G8.jpg (CI karti) ve <CIFT>_G7.jpg (PW karti), 3000x2250.
Kesim kutusu (901,601)-(2107,2118) -> PNG 1206x1517 (compress_level=9): <out>/CI_<CIFT>.png (G8), <out>/PW_<CIFT>.png (G7).
Dalda duran dosya: piksel esitse compress_level=9 surumuyle degistirilir (AYNI_YENIDEN); farkliysa UZERINE YAZILMAZ (FARK).
Kullanim: kapak_ci_kesim.py <kaynak dizin> <cift csv> <out dizin> <KESIM.csv>   (cikis 1: eksik / FARK / boyut hatasi)"""
import csv
import hashlib
import sys
from pathlib import Path

import numpy as np
from PIL import Image

KUTU, BOY, KAYNAK_BOY = (901, 601, 2107, 2118), (1206, 1517), (3000, 2250)


def main():
    src, cift_csv, out, rapor = map(Path, sys.argv[1:5])
    out.mkdir(parents=True, exist_ok=True)
    ciftler = [r["cift"] for r in csv.DictReader(open(cift_csv))]
    S = []
    for c in ciftler:
        for on, g in (("CI", "G8"), ("PW", "G7")):
            ad, kp, hp = f"{on}_{c}.png", src / f"{c}_{g}.jpg", out / f"{on}_{c}.png"
            r = dict(cift=c, dosya=ad, kaynak=kp.name, sha256="", boyut="", durum="")
            if not kp.exists():
                r["durum"] = "KAYNAK_YOK"; S.append(r); continue
            im = Image.open(kp); im.load()
            if im.size != KAYNAK_BOY:
                r["durum"] = f"KAYNAK_BOYUT_{im.size[0]}x{im.size[1]}"; S.append(r); continue
            k = im.convert("RGB").crop(KUTU)
            if hp.exists():
                eski = np.asarray(Image.open(hp).convert("RGB")).astype(int)
                fark = np.abs(eski - np.asarray(k).astype(int)) if eski.shape == (BOY[1], BOY[0], 3) else None
                if fark is None or fark.max():
                    r["durum"] = "FARK" if fark is None else f"FARK_max{int(fark.max())}_px{int((fark.max(2) > 0).sum())}"
                else:
                    k.save(hp, optimize=False, compress_level=9); r["durum"] = "AYNI_YENIDEN"
            else:
                k.save(hp, optimize=False, compress_level=9); r["durum"] = "YENI"
            if hp.exists():
                w = Image.open(hp); r["boyut"] = f"{w.size[0]}x{w.size[1]}"
                r["sha256"] = hashlib.sha256(hp.read_bytes()).hexdigest()
                if w.size != BOY and not r["durum"].startswith("FARK"):
                    r["durum"] = "BOYUT_HATASI"
            S.append(r)
    with open(rapor, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(S[0])); w.writeheader(); w.writerows(S)
    iyi = sum(1 for r in S if r["durum"] in ("YENI", "AYNI_YENIDEN"))
    print(f"kesim: {iyi}/{len(S)} iyi; durumlar {sorted({r['durum'] for r in S})}", flush=True)
    return 0 if iyi == len(S) == 2 * len(ciftler) else 1


if __name__ == "__main__":
    sys.exit(main())
