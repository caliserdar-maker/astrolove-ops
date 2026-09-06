#!/usr/bin/env python3
"""
POD SKU semasi (6 Eyl 2026): Etsy SKU <= 32 karakter ("POD-<PAIR>-<ED>-<SIZE>" 43'e cikiyordu).
  POD-<S1_3>_<S2_3>-<ED2>-<SIZE>   or. POD-ARI_LEO-MB-30x40 (en uzun POD-SAG_SAG-WP-30x40 = 20)
Burc 3 harf: AQU ARI TAU GEM CAN LEO VIR LIB SCO SAG CAP PIS; edisyon: MB DB WP CI PW.
"""
import re

SIGN3 = {"AQUARIUS": "AQU", "ARIES": "ARI", "TAURUS": "TAU", "GEMINI": "GEM", "CANCER": "CAN", "LEO": "LEO",
         "VIRGO": "VIR", "LIBRA": "LIB", "SCORPIO": "SCO", "SAGITTARIUS": "SAG", "CAPRICORN": "CAP", "PISCES": "PIS"}
ED2 = {"MIDNIGHT_BLUE": "MB", "DEEP_BLACK": "DB", "WARM_PARCHMENT": "WP", "CHAMPAGNE_IVORY": "CI", "PURE_WHITE": "PW"}
SIGN_OF = {v: k for k, v in SIGN3.items()}
ED_OF = {v: k for k, v in ED2.items()}
SKU_RE = re.compile(r"^POD-([A-Z]{3})_([A-Z]{3})-([A-Z]{2})-([0-9]+x[0-9]+|A[234])$")
MAX_LEN = 32


def make_sku(pair, ed, size):
    s1, s2 = pair.upper().split("_", 1)
    sku = f"POD-{SIGN3[s1]}_{SIGN3[s2]}-{ED2[ed]}-{size}"
    assert len(sku) <= MAX_LEN, sku
    return sku


def parse_sku(sku):
    """-> (pair, ed, size) | None"""
    m = SKU_RE.match((sku or "").strip())
    if not m or m.group(1) not in SIGN_OF or m.group(2) not in SIGN_OF or m.group(3) not in ED_OF:
        return None
    return f"{SIGN_OF[m.group(1)]}_{SIGN_OF[m.group(2)]}", ED_OF[m.group(3)], m.group(4)
