#!/usr/bin/env python3
"""Tam log maskesi (IP adim 0 c3, 18 Kas 2026): stdin -> stdout, order_router.maskeli_metin_tam ile ayni kural.

Siparis no (10-12 hane) ve merchantReference etsy-<no>-<boy> -> opak kod (anahtarsiz "S-gizli"); Prodigi ord_ kimligi ve
takip no yalniz son 4 hane (kargo_maske). Adim ozeti / log icin; Drive dosyalari tam kalir. ::add-mask:: satirlari degismez.
Kullanim: python3 scripts/guvenlik/tam_maske.py < rapor.md >> "$GITHUB_STEP_SUMMARY"
"""
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
for p in ("scripts/guvenlik", "scripts/etsy", "scripts/prodigi"):
    sys.path.insert(0, str(KOK / p))
import order_router as R  # noqa: E402

if __name__ == "__main__":
    sys.stdout.write(R.maskeli_metin_tam(sys.stdin.read()))
