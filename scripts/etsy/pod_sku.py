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
SKU_RE = re.compile(r"^POD-([A-Z]{3})_([A-Z]{3})-([A-Z]{2})-([0-9]+x[0-9]+|A[1234])(?:-F(BK|WH|NA))?$")
MAX_LEN = 32
# Dijital secenek (GOREV 0036): ayni ilanda Size = "Digital File", SKU POD-<S1>_<S2>-<ED2>-DIGITAL.
# SKU_RE'ye UYMAZ (boy degil) -> parse_sku None; Prodigi'ye asla gitmez (order_router.dijital_mi ayrica yakalar).
DIGITAL = "DIGITAL"


def make_sku(pair, ed, size):
    s1, s2 = pair.upper().split("_", 1)
    sku = f"POD-{SIGN3[s1]}_{SIGN3[s2]}-{ED2[ed]}-{size}"
    assert len(sku) <= MAX_LEN, sku
    return sku


def make_digital_sku(pair, ed):
    s1, s2 = pair.upper().split("_", 1)
    sku = f"POD-{SIGN3[s1]}_{SIGN3[s2]}-{ED2[ed]}-{DIGITAL}"
    assert len(sku) <= MAX_LEN, sku
    return sku


def is_digital_sku(sku):
    return (sku or "").strip().upper().endswith("-" + DIGITAL)


def parse_sku(sku):
    """-> (pair, ed, size) | None"""
    m = SKU_RE.match((sku or "").strip())
    if not m or m.group(1) not in SIGN_OF or m.group(2) not in SIGN_OF or m.group(3) not in ED_OF:
        return None
    return f"{SIGN_OF[m.group(1)]}_{SIGN_OF[m.group(2)]}", ED_OF[m.group(3)], m.group(4)


# Yapi v2 (Serdar 27 Eyl 2026, 3 menu: Format / Primary color / Size): SKU RENK ICERMEZ
#   POD-<S1_3>_<S2_3>-<SIZE>[-F<BK|WH|NA>]  ya da  POD-<S1_3>_<S2_3>-<SIZE>-DIGITAL
# Renk (edisyon) siparis kalemindeki "Primary color" varyasyonundan okunur (parse_tx). Etsy urun siniri 400 -> 2500.
SKU2_RE = re.compile(r"^POD-([A-Z]{3})_([A-Z]{3})-([0-9]+x[0-9]+|A[1234])(?:-F(BK|WH|NA))?$")
RENK_ADI = {"MIDNIGHT BLUE": "MIDNIGHT_BLUE", "DEEP BLACK": "DEEP_BLACK", "WARM PARCHMENT": "WARM_PARCHMENT",
            "CHAMPAGNE IVORY": "CHAMPAGNE_IVORY", "PURE WHITE": "PURE_WHITE"}


def renk_of(t):
    """Siparis kalemi -> edisyon (MIDNIGHT_BLUE ...) | None. Yalniz 'color' adli varyasyon; bilinmeyen deger None."""
    for v in (t or {}).get("variations") or []:
        ad = str(v.get("formatted_name") or v.get("property_name") or "").lower()
        if "color" in ad:
            deger = " ".join(str(v.get("formatted_value") or v.get("value") or "").upper().split())
            return RENK_ADI.get(deger)
    return None


def make_sku2(pair, size, cerceve=None):
    s1, s2 = pair.upper().split("_", 1)
    sku = f"POD-{SIGN3[s1]}_{SIGN3[s2]}-{size}" + (f"-F{cerceve}" if cerceve else "")
    assert len(sku) <= MAX_LEN, sku
    return sku


def parse_tx(t):
    """Siparis kalemi -> (pair, ed, size, cerceve, kanonik_sku) | None.
    Eski SKU (renkli) aynen cozulur. Yeni SKU'da renk varyasyondan gelir; renk yoksa/bilinmiyorsa None (fail-closed).
    kanonik_sku = eski semadaki renkli SKU (+ -F..): ic anahtar; ayni sepette farkli renkler carpismaz."""
    sku = ((t or {}).get("sku") or "").strip()
    p = parse_sku(sku)
    if p:
        cer = frame_code(sku)
        return p[0], p[1], p[2], cer, sku
    m = SKU2_RE.match(sku)
    if not m or m.group(1) not in SIGN_OF or m.group(2) not in SIGN_OF:
        return None
    ed = renk_of(t)
    if not ed:
        return None
    pair = f"{SIGN_OF[m.group(1)]}_{SIGN_OF[m.group(2)]}"
    kanon = make_sku(pair, ed, m.group(3)) + (f"-F{m.group(4)}" if m.group(4) else "")
    return pair, ed, m.group(3), m.group(4), kanon


def frame_code(sku):
    """Cerceveli POD SKU'su icin BK/WH/NA, diger SKU'lar icin None."""
    m = SKU_RE.match((sku or "").strip())
    return m.group(5) if m else None
