#!/usr/bin/env python3
"""Kupa galeri 78 ilan x 14 gorsel alt metni (data/pod/kupa_galeri78_alt.csv ONAYLI sablonundan; kupa_galeri78.alt_metin + alt_gecerli
kapisi + uzun / orta tire yok). ETSY YOK. Kullanim: kupa_alt78.py --out <dir> -> KUPA_GALERI78_ALT_78.csv (cift, sira, alt)"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kupa_galeri78 as K  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args(argv)
    alt = K.alt_oku(K.ALT_CSV)
    if not K.alt_onayli(alt):
        raise SystemExit("DUR: alt metin sablonu ONAYLI degil")
    rows, hata = [], []
    for c in K.CIFTLER:
        x, y = (K.ad_burc(b) for b in c.split("_"))
        for s in range(1, K.N + 1):
            t = K.alt_metin(alt[s], x, y)
            if not K.alt_gecerli(t) or re.search("[‒-―−]", t):
                hata.append((c, s, t))
            rows.append(dict(cift=c, sira=s, alt=t))
    if hata or len(rows) != 78 * K.N:
        raise SystemExit(f"DUR: alt metin kapisi {len(rows)} satir, hata {hata[:3]}")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    with open(out / "KUPA_GALERI78_ALT_78.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cift", "sira", "alt"], lineterminator="\n"); w.writeheader(); w.writerows(rows)
    print(f"ALT78: {len(rows)} satir PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
