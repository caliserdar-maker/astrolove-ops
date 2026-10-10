#!/usr/bin/env python3
"""Etsy arama capraz kontrolu (Serdar 10 Eki 2026): Marketplace insights (MI, ANA) x eRank (yardimci).

Girdi CSV sutunlari: terim | MI arama/30g | MI rekabet | eRank hacim | eRank rekabet | fark oranı | not
Script 'fark oranı' sutununu doldurur: hacim orani (buyuk/kucuk) ve rekabet orani; biri 2'den buyukse 'CELISKILI'.
Karar MI'ya gore: MI bos ise satir 'MI YOK: karar verilmez' olur (eRank tek basina kanit sayilmaz).
Sayi bicimleri: 1234, 1,234, 1.2k, 1.7M, 2,4 bin. Cikis: 0 = tum satirlarda MI var, 1 = MI eksik satir var.
Kullanim: python3 arama_capraz.py girdi.csv cikti.csv
"""
import csv
import re
import sys

SUT = ["terim", "MI arama/30g", "MI rekabet", "eRank hacim", "eRank rekabet", "fark oranı", "not"]
ESIK = 2.0


def sayi(v):
    s = (v or "").strip().lower().replace(" ", "")
    if not s or s in {"-", "yok", "na", "n/a"}:
        return None
    carp = 1
    for son, k in (("bin", 1e3), ("k", 1e3), ("m", 1e6), ("mn", 1e6)):
        if s.endswith(son):
            s, carp = s[: -len(son)], k
            break
    if carp > 1:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "").replace(".", "") if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s) else s.replace(",", ".")
    try:
        return float(s) * carp
    except ValueError:
        return None


def oran(a, b):
    if a is None or b is None:
        return None
    if a == 0 and b == 0:
        return 1.0
    if min(a, b) == 0:
        return float("inf")
    return max(a, b) / min(a, b)


def yaz(o):
    return "-" if o is None else ("inf" if o == float("inf") else f"{o:.2f}")


def isle(satirlar):
    eksik = 0
    for r in satirlar:
        mi_h, mi_r = sayi(r["MI arama/30g"]), sayi(r["MI rekabet"])
        h = oran(mi_h, sayi(r["eRank hacim"]))
        k = oran(mi_r, sayi(r["eRank rekabet"]))
        if mi_h is None:
            eksik += 1
            r["fark oranı"] = "MI YOK: karar verilmez"
            continue
        celis = any(x is not None and x > ESIK for x in (h, k))
        r["fark oranı"] = f"hacim {yaz(h)} | rekabet {yaz(k)}" + (" | CELISKILI (karar MI)" if celis else "")
    return eksik


def main(gir, cik):
    with open(gir, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        if rd.fieldnames != SUT:
            raise SystemExit(f"FAIL: sutunlar {rd.fieldnames} != {SUT}")
        satirlar = list(rd)
    eksik = isle(satirlar)
    with open(cik, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SUT)
        w.writeheader()
        w.writerows(satirlar)
    celis = sum("CELISKILI" in r["fark oranı"] for r in satirlar)
    print(f"{'PASS' if not eksik else 'FAIL'}: {len(satirlar)} terim | MI eksik {eksik} | celiskili {celis}")
    return 0 if not eksik else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
