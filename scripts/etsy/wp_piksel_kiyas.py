#!/usr/bin/env python3
"""
PIKSEL KIYAS (5 Eyl 2026, Mo): uretilen render'i Mo'nun onayladigi ciktiyla
piksel piksel karsilastir. Olcu: tum goruntu uzerinde ortalama mutlak fark
(BGR ortalamasi, 0-255). Ortalama fark < ESIK (2.0) ise PASS.
  --cift  <uretilen.jpg>=<onayli.jpg>   (tekrarlanabilir)
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ESIK = 2.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cift", action="append", required=True, help="<uretilen>=<onayli>")
    ap.add_argument("--esik", type=float, default=ESIK)
    a = ap.parse_args()
    hepsi = True
    for c in a.cift:
        u, o = c.split("=", 1)
        A, B = cv2.imread(u), cv2.imread(o)
        if A is None or B is None:
            print(f"HATA: okunamadi {u if A is None else o}"); hepsi = False; continue
        if A.shape != B.shape:
            print(f"FAIL {Path(u).name}: olcu {A.shape[1]}x{A.shape[0]} != {B.shape[1]}x{B.shape[0]}"); hepsi = False; continue
        d = np.abs(A.astype(np.float32) - B.astype(np.float32)).mean(axis=2)
        ort = float(d.mean()); p99 = float(np.percentile(d, 99)); mx = float(d.max())
        ok = ort < a.esik
        hepsi &= ok
        print(f"{'PASS' if ok else 'FAIL'} {Path(u).name} vs {Path(o).name}: ortalama {ort:.3f} (esik {a.esik}), p99 {p99:.1f}, maks {mx:.0f}")
    print("SONUC PIKSEL KIYAS:", "PASS" if hepsi else "FAIL")
    return 0 if hepsi else 1


if __name__ == "__main__":
    sys.exit(main())
