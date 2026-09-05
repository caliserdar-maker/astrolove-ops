#!/usr/bin/env python3
"""Calib KOPYASINDA ekran alanlarini degistir: --set SAHNE:EKRAN:alan=deger (5 Eyl 2026)."""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib-json", required=True)
    ap.add_argument("--set", action="append", default=[], help="SAHNE:EKRAN:alan=deger")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    calib = json.loads(Path(a.calib_json).read_text())
    for s in a.set:
        adres, deger = s.split("=", 1)
        sahne, ekran, alan = adres.split(":")
        hedef = next(x for x in calib["scenes"][sahne]["screens"] if int(x["id"]) == int(ekran))
        print(f"{sahne}/{ekran} {alan}: {hedef.get(alan)!r} -> {deger!r}")
        hedef[alan] = deger
    Path(a.out).write_text(json.dumps(calib, indent=1))
    print(f"{a.out}: {len(a.set)} degisiklik (orijinale dokunulmadi)")


if __name__ == "__main__":
    main()
