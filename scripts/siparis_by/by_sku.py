#!/usr/bin/env python3
"""1st Anniversary (BY / YD) SKU cozucusu: yeni KISA stil kodu ve canli eski UZUN kod (Serdar 31 Eki karar 1a).
Yeni (yd_yapi_kuru.envanter_plani): BY-<AAA_BBB>-<ST|TL|FP|LY|BO>-<boy>[-DIGITAL]   boy: 5x7 ... 24x36, A4, A3, A2 (en cok 27 kr.)
Eski (canli, by78_kargo_sku_aciklama):  BY-<AAA_BBB>-<STARLIT|TIMELESS|FIRSTPAGE|LAYERS|BOTANICAL>-<CARD5X7|FILE8X10|PRINT8X10>
Eski uzun kodla yeni boy da okunur (BY-CAN_LIB-FIRSTPAGE-12x18-DIGITAL; Etsy 32 siniri yuzunden yazilmaz ama cozulur).
coz(sku) -> dict(cift_kod, stil, stil_no, boy, dijital, eski, urun: poster | kart) | None. stil_no: by_siparis STYLE (1..5)."""
import re

STILLER = ("Starlit", "Timeless", "First Page", "Layers", "Botanical")
KISA = {"Starlit": "ST", "Timeless": "TL", "First Page": "FP", "Layers": "LY", "Botanical": "BO"}
UZUN = {"Starlit": "STARLIT", "Timeless": "TIMELESS", "First Page": "FIRSTPAGE", "Layers": "LAYERS", "Botanical": "BOTANICAL"}
KOD_STIL = {**{v: k for k, v in KISA.items()}, **{v: k for k, v in UZUN.items()}}
BOYLAR = ("5x7", "8x10", "11x14", "12x16", "12x18", "16x20", "16x24", "18x24", "20x30", "24x30", "24x36", "A4", "A3", "A2")
ESKI_FORMAT = {"CARD5X7": ("5x7", True), "FILE8X10": ("8x10", True), "PRINT8X10": ("8x10", False)}
SKU_MAX = 32
RX = re.compile(r"^BY-([A-Z]{3}_[A-Z]{3})-([A-Z]+)-(" + "|".join(map(re.escape, BOYLAR + tuple(ESKI_FORMAT))) + r")(-DIGITAL)?$")


def sku(cift_kod, stil, boy, dijital):
    """Yeni SKU (kisa kod)."""
    return f"BY-{cift_kod}-{KISA[stil]}-{boy}" + ("-DIGITAL" if dijital else "")


def coz(s):
    """Buyuk / kucuk harf duyarsiz (inceleme 31 Eki: BY-CAN_LIB-ST-8X10 da cozulur)."""
    t = (s or "").strip().upper()
    t = re.sub(r"-(\d+)X(\d+)(?=-DIGITAL$|$)", r"-\1x\2", t)
    m = RX.match(t)
    if not m or m.group(2) not in KOD_STIL:
        return None
    stil, kod, dig = KOD_STIL[m.group(2)], m.group(3), bool(m.group(4))
    if kod in ESKI_FORMAT:
        if dig:
            return None
        boy, dig = ESKI_FORMAT[kod]
    else:
        boy = kod
    return dict(cift_kod=m.group(1), stil=stil, stil_no=str(STILLER.index(stil) + 1), boy=boy, dijital=dig,
                eski=m.group(2) == UZUN[stil], urun="kart" if kod == "CARD5X7" else "poster")   # eski CARD5X7 = 5x7 kart tasarimi


if __name__ == "__main__":
    import sys
    for a in sys.argv[1:]:
        print(a, coz(a))
