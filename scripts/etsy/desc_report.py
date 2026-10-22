#!/usr/bin/env python3
"""pod-desc-batch durum CSV'sinden ozet rapor basar."""
import collections
import csv
import sys


def main(yol: str) -> int:
    with open(yol, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    say = collections.Counter(r["sonuc"] for r in rows)
    print("### Sonuc:", dict(say))
    for durum in ("ATLANDI", "FAIL"):
        kotu = [(r["pair"], r.get("not", "")[:80]) for r in rows if r["sonuc"] == durum]
        if kotu:
            print(f"\n{durum}:")
            for pair, nt in kotu:
                print(f"  - {pair}: {nt}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "_work/desc_state.csv"))
