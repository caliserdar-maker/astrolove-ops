#!/usr/bin/env python3
"""Canli Etsy renk-varyasyon baglantilarini ilan basina uc GET ile denetler."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import APIKeyStore, Etsy  # noqa: E402
from varyasyon_denetle import denetle  # noqa: E402

REF_ID = "4570143815"


def state_hedefleri(state: dict[str, Any]) -> list[tuple[str, str]]:
    """GALERI_TAMSET durumundaki PASS ilanlari ve referansi tekillestirir."""
    bulunan: dict[str, str] = {}
    for cift, kayit in (state.get("ilan") or {}).items():
        if kayit.get("sonuc") == "PASS" and kayit.get("ilan_id"):
            bulunan[str(kayit["ilan_id"])] = cift
    bulunan.setdefault(REF_ID, "CANCER_LIBRA")
    return [(cift, ilan) for ilan, cift in bulunan.items()]


def set_bul(setler: Path, cift: str) -> Path:
    adaylar = (setler / cift / "TAM_SET" / "SET.json", setler / cift / "SET.json")
    return next((p for p in adaylar if p.is_file()), adaylar[0])


def ilanlari_denetle(hedefler: list[tuple[str, str]], setler: Path,
                     getir: Callable[[str, str], Any]) -> tuple[list[dict[str, str]], int]:
    """Bagimlilik enjekte edilebilir ilan dongusu; her ilan tam uc GET yapar."""
    satirlar: list[dict[str, str]] = []
    cagri = 0
    for cift, ilan in hedefler:
        try:
            inventory = getir(ilan, "inventory"); cagri += 1
            variation_images = getir(ilan, "variation-images"); cagri += 1
            images = getir(ilan, "images"); cagri += 1
            set_data = json.loads(set_bul(setler, cift).read_text(encoding="utf-8"))
            rapor = denetle(inventory, variation_images, images, set_data)
            neden = list(rapor["genel_nedenler"])
            neden.extend(f"{x['renk']}: {', '.join(x['nedenler'])}" for x in rapor["renkler"] if x["nedenler"])
            durum = rapor["durum"]
        except (Exception, SystemExit) as exc:  # Etsy istemcisi HTTP hatalarinda SystemExit kullanir.
            durum, neden = "FAIL", [f"{type(exc).__name__}: {exc}"]
        satirlar.append({"ilan": ilan, "cift": cift, "durum": durum, "neden": " | ".join(neden)})
    return satirlar, cagri


def _hedef_arg(deger: str) -> list[tuple[str, str]]:
    hedefler = []
    for parca in filter(None, (x.strip() for x in deger.split(","))):
        cift, ilan = parca.split(":", 1)
        if not re.fullmatch(r"[A-Z]+_[A-Z]+", cift) or not ilan.isdigit():
            raise ValueError(f"gecersiz hedef: {parca}")
        hedefler.append((cift, ilan))
    return hedefler


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", required=True, help="GALERI_TAMSET.json")
    ap.add_argument("--setler", required=True, help="<CIFT>/TAM_SET/SET.json kok dizini")
    ap.add_argument("--output", default="VARYASYON_CANLI.csv")
    ap.add_argument("--hedefler", default="", help="istege bagli CIFT:ilan_id,...")
    args = ap.parse_args()

    api = Etsy(APIKeyStore(os.environ.get("ETSY_API_KEY", ""),
                           os.environ.get("ETSY_SHARED_SECRET", "")))
    shop = os.environ["ETSY_SHOP_ID"]
    hedefler = _hedef_arg(args.hedefler) if args.hedefler else state_hedefleri(
        json.loads(Path(args.state).read_text(encoding="utf-8")))

    def getir(ilan: str, kaynak: str) -> Any:
        if kaynak == "inventory":
            return api.get(f"/listings/{ilan}/inventory")
        if kaynak == "variation-images":
            return api.get(f"/shops/{shop}/listings/{ilan}/variation-images")
        return api.get(f"/listings/{ilan}/images")

    satirlar, cagri = ilanlari_denetle(hedefler, Path(args.setler), getir)
    with Path(args.output).open("w", encoding="utf-8", newline="") as fh:
        yaz = csv.DictWriter(fh, fieldnames=["ilan", "cift", "durum", "neden"])
        yaz.writeheader(); yaz.writerows(satirlar)
    basarili = sum(x["durum"] == "PASS" for x in satirlar)
    ozet = f"{basarili}/{len(satirlar)} PASS"
    print(f"{ozet} | Etsy GET: {cagri} (en fazla 3/ilan)")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(ozet + "\n\n")
            fh.write("| Ilan | Cift | Durum | Neden |\n|---|---|---|---|\n")
            for x in satirlar:
                fh.write(f"| {x['ilan']} | {x['cift']} | {x['durum']} | {x['neden']} |\n")
    return 0 if basarili == len(satirlar) else 1


if __name__ == "__main__":
    raise SystemExit(main())
