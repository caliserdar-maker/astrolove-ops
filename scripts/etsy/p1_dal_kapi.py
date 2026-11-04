#!/usr/bin/env python3
"""P1 kuru ciktisinin DALA (acik depo) yazim kapisi (Serdar 4 Kas "A"). Yalniz izin listesi: FARK.csv, DUR.csv, ONCE_SONRA.json,
DIGER_URUNLER.csv, OZET.json, LOG.txt; alt klasor / HAM yolu yok; JSON'da yasak ANAHTAR (inventory, products, price, sku, quantity;
buyuk/kucuk harf duyarsiz, ozyinelemeli, anahtar adiyla) yok. Ihlal -> cikis 1 (yalniz dosya adi ve anahtar adi yazilir, deger yok).
Kullanim: p1_dal_kapi.py KLASOR [--staged DOSYA]  (--staged: git diff --cached --name-only ciktisi; hepsi KLASOR altinda olmali)"""
import argparse
import json
import pathlib
import sys

IZIN = {"FARK.csv", "DUR.csv", "ONCE_SONRA.json", "DIGER_URUNLER.csv", "OZET.json", "LOG.txt"}
YASAK = {"inventory", "products", "price", "sku", "quantity"}


def anahtarlar(o, yol=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k, f"{yol}/{k}"
            yield from anahtarlar(v, f"{yol}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from anahtarlar(v, f"{yol}[{i}]")


def kontrol(klasor, staged=None):
    h = []
    k = pathlib.Path(klasor)
    if not k.is_dir():
        return [f"klasor yok: {k}"]
    for p in sorted(k.rglob("*")):
        r = p.relative_to(k)
        if p.is_dir() or len(r.parts) > 1:
            h.append(f"alt klasor / izinsiz yol: {r}")
        elif r.name not in IZIN:
            h.append(f"izin listesi disi dosya: {r}")
        if "HAM" in r.parts:
            h.append(f"HAM yolu: {r}")
        if p.is_symlink():
            h.append(f"sembolik bag: {r}")
    for p in sorted(k.glob("*.json")):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            h.append(f"JSON okunamadi: {p.name}"); continue
        bad = sorted({y for a, y in anahtarlar(j) if str(a).lower() in YASAK})
        if bad:
            h.append(f"{p.name}: yasak anahtar {len(bad)} (ilk: {bad[0]})")
    for p in sorted(k.glob("*.csv")):   # inceleme C: CSV sutun adlari da yasak anahtar listesine tabi
        bas = (p.read_text(encoding="utf-8").splitlines() or [""])[0]
        bad = sorted({c.strip().lower() for c in bas.split(",")} & YASAK)
        if bad:
            h.append(f"{p.name}: yasak sutun {bad}")
    if staged is not None:
        on = k.as_posix().rstrip("/") + "/"
        disari = [s for s in staged if s and not s.startswith(on)]
        if disari:
            h.append(f"stage'de klasor disi yol {len(disari)}: {disari[:3]}")
    return h


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("klasor"); ap.add_argument("--staged")
    a = ap.parse_args(argv)
    st = pathlib.Path(a.staged).read_text(encoding="utf-8").split("\n") if a.staged else None
    h = kontrol(a.klasor, st)
    for x in h:
        print("P1 DAL KAPISI FAIL: " + x, flush=True)
    print(f"P1 DAL KAPISI: {'FAIL' if h else 'PASS'} ({len(h)} ihlal)", flush=True)
    return 1 if h else 0


if __name__ == "__main__":
    sys.exit(main())
