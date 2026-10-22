#!/usr/bin/env python3
"""SET.json benzeri sira -> alt metin sozlugunu cevrimdisi denetler."""

import argparse
import json
import re
from pathlib import Path


BURCLAR = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)
YASAK = (
    ("OBA-free", re.compile(r"\bOBA[\s-]*free\b", re.I)),
    ("bright white", re.compile(r"\bbright\s+white\b", re.I)),
    ("omur yili", re.compile(r"\b\d+\s*(?:-|to)\s*\d+\s*years?\b", re.I)),
    ("12-colour", re.compile(r"\b12[\s-]*colou?r\b", re.I)),
)


def cifti_ayir(deger):
    """ARIES_LEO ve 'Aries + Leo' bicimlerinden iki burc dondurur."""
    bulunan = [parca.capitalize() for parca in re.findall(r"[A-Za-z]+", deger)]
    if len(bulunan) == 2 and all(ad in BURCLAR for ad in bulunan):
        return bulunan
    raise ValueError("cift iki gecerli burc icermeli (ornek: ARIES_LEO)")


def denetle(metinler, cift):
    """Her sira icin ``(sira, PASS/FAIL, nedenler)`` listesi dondurur."""
    beklenen = cifti_ayir(cift)
    sonuc = []
    for sira, deger in metinler.items():
        hatalar = []
        if not isinstance(deger, str):
            sonuc.append((str(sira), "FAIL", ["alt metin string degil"]))
            continue
        if len(deger) > 250:
            hatalar.append(f"250 karakter siniri asildi ({len(deger)})")
        if deger != deger.rstrip():
            hatalar.append("sonda bosluk var")
        if "—" in deger or "–" in deger:
            hatalar.append("uzun/orta tire var")
        if re.search(r"\bHahnemuhle\b", deger, re.I):
            hatalar.append("Hahnemühle yazimi hatali")
        for ad, kalip in YASAK:
            if kalip.search(deger):
                hatalar.append(f"yasak ifade: {ad}")

        sayilar = {ad: len(re.findall(rf"\b{ad}\b", deger, re.I)) for ad in BURCLAR}
        if beklenen[0] == beklenen[1]:
            if sayilar[beklenen[0]] < 2:
                hatalar.append(f"ayni burc iki kez gecmiyor: {beklenen[0]}")
        else:
            for ad in beklenen:
                if sayilar[ad] < 1:
                    hatalar.append(f"cift burcu eksik: {ad}")
        fazladan = [ad for ad in BURCLAR if ad not in beklenen and sayilar[ad]]
        if fazladan:
            hatalar.append("cifte ait olmayan burc: " + ", ".join(fazladan))
        sonuc.append((str(sira), "FAIL" if hatalar else "PASS", hatalar))
    return sonuc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dosya", type=Path, help="{sira: alt_metin} JSON dosyasi")
    ap.add_argument("--cift", required=True, help="ornek: ARIES_LEO")
    args = ap.parse_args(argv)
    try:
        veri = json.loads(args.dosya.read_text(encoding="utf-8"))
        if not isinstance(veri, dict):
            raise ValueError("JSON kok degeri sozluk olmali")
        sonuc = denetle(veri, args.cift)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 2
    for sira, durum, hatalar in sonuc:
        ek = "" if not hatalar else ": " + "; ".join(hatalar)
        print(f"{sira}: {durum}{ek}")
    return 1 if any(durum == "FAIL" for _, durum, _ in sonuc) else 0


if __name__ == "__main__":
    raise SystemExit(main())
