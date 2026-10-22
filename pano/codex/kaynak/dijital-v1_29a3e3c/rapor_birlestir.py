#!/usr/bin/env python3
"""Iki kosunun raporunu tek WP_KISISEL_RAPOR.json'da birlestirir (son kosu kazanir)."""
import json
import sys
from pathlib import Path


def main(kok):
    k = Path(kok)
    kayit = {}
    for ad in ("WP_KISISEL_RAPOR.json", "WP_KISISEL_RAPOR_EKSIK3.json"):
        y = k / ad
        if y.exists():
            for r in json.loads(y.read_text()):
                kayit[r["dosya"]] = r
    birlesik = [kayit[a] for a in sorted(kayit)]
    (k / "WP_KISISEL_RAPOR.json").write_text(json.dumps(birlesik, indent=1))
    gecen = sum(1 for r in birlesik if r["kapi"]["gecti"])
    print(f"birlesik kayit: {len(birlesik)} | kapidan gecen: {gecen}")
    for r in birlesik:
        if not r["kapi"]["gecti"]:
            print(f"  KALDI: {r['dosya']} | {r.get('hata') or 'kapi'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
