#!/usr/bin/env python3
"""Plate onay defterini guvenli bicimde yoneten yerel CLI."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[2]
VARSAYILAN_DOSYA = ROOT / "config" / "plate_onay.json"

EDISYONLAR = {
    "MIDNIGHT_BLUE",
    "DEEP_BLACK",
    "PURE_WHITE",
    "CHAMPAGNE_IVORY",
    "WARM_PARCHMENT",
}
EDISYON_ESLESME = {
    "BLUE": "MIDNIGHT_BLUE",
    "BLACK": "DEEP_BLACK",
    "WHITE": "PURE_WHITE",
    "CHAMPAGNE": "CHAMPAGNE_IVORY",
    "PARCHMENT": "WARM_PARCHMENT",
}
BOYLAR = {
    "8x10", "A4", "11x14", "12x16", "A3", "12x18", "16x20", "16x24",
    "A2", "18x24", "20x30", "24x30", "24x32", "A1", "24x36", "30x40",
}
KAYIT_ALANLARI = {"edisyon", "boy", "kanit", "onaylayan", "tarih_utc"}


class DefterHatasi(ValueError):
    """Onay defteri girdisi veya semasi gecersiz."""


def edisyon_duzelt(deger: str) -> str:
    edisyon = deger.strip().upper()
    edisyon = EDISYON_ESLESME.get(edisyon, edisyon)
    if edisyon not in EDISYONLAR:
        raise DefterHatasi(f"bilinmeyen edisyon: {deger}")
    return edisyon


def boylari_oku(deger: str) -> list[str]:
    boylar = [boy.strip() for boy in deger.split(",") if boy.strip()]
    if not boylar:
        raise DefterHatasi("en az bir boy gerekli")
    gecersiz = sorted(set(boylar) - BOYLAR)
    if gecersiz:
        raise DefterHatasi(f"bilinmeyen boy: {', '.join(gecersiz)}")
    return list(dict.fromkeys(boylar))


def defteri_oku(yol: Path) -> dict:
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DefterHatasi(f"defter bulunamadi: {yol}") from exc
    except json.JSONDecodeError as exc:
        raise DefterHatasi(f"gecersiz JSON: {exc}") from exc
    dogrula(veri)
    return veri


def dogrula(veri: object) -> None:
    if not isinstance(veri, dict) or set(veri) != {"onayli"} or not isinstance(veri["onayli"], list):
        raise DefterHatasi("kok sema tam olarak {'onayli': [...]} olmali")

    gorulen: set[tuple[str, str]] = set()
    for sira, kayit in enumerate(veri["onayli"], 1):
        if not isinstance(kayit, dict) or set(kayit) != KAYIT_ALANLARI:
            raise DefterHatasi(f"kayit {sira}: alanlar gecersiz")
        edisyon = edisyon_duzelt(str(kayit["edisyon"]))
        if edisyon != kayit["edisyon"]:
            raise DefterHatasi(f"kayit {sira}: edisyon kanonik degil")
        if kayit["boy"] not in BOYLAR:
            raise DefterHatasi(f"kayit {sira}: bilinmeyen boy: {kayit['boy']}")
        if not all(isinstance(kayit[alan], str) and kayit[alan].strip()
                   for alan in ("kanit", "onaylayan", "tarih_utc")):
            raise DefterHatasi(f"kayit {sira}: metin alanlari bos olamaz")
        try:
            tarih = datetime.fromisoformat(kayit["tarih_utc"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise DefterHatasi(f"kayit {sira}: tarih_utc gecersiz") from exc
        if tarih.tzinfo is None or tarih.utcoffset() != timezone.utc.utcoffset(tarih):
            raise DefterHatasi(f"kayit {sira}: tarih_utc UTC olmali")
        anahtar = (edisyon, kayit["boy"])
        if anahtar in gorulen:
            raise DefterHatasi(f"kayit {sira}: yinelenen onay: {edisyon}/{kayit['boy']}")
        gorulen.add(anahtar)


def atomik_yaz(yol: Path, veri: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=yol.parent,
                                         prefix=f".{yol.name}.", delete=False) as fh:
            gecici = Path(fh.name)
            json.dump(veri, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(gecici, yol)
    finally:
        if gecici is not None:
            gecici.unlink(missing_ok=True)


def ekle(veri: dict, edisyon: str, boylar: list[str], kanit: str, onaylayan: str) -> int:
    if not kanit.strip() or not onaylayan.strip():
        raise DefterHatasi("kanit ve onaylayan bos olamaz")
    mevcut = {(k["edisyon"], k["boy"]) for k in veri["onayli"]}
    yeni = [(edisyon, boy) for boy in boylar if (edisyon, boy) not in mevcut]
    tarih = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    veri["onayli"].extend({"edisyon": edisyon, "boy": boy, "kanit": kanit.strip(),
                           "onaylayan": onaylayan.strip(), "tarih_utc": tarih}
                          for _, boy in yeni)
    return len(yeni)


def kaldir(veri: dict, edisyon: str, boylar: list[str]) -> int:
    once = len(veri["onayli"])
    secilen = set(boylar)
    veri["onayli"] = [k for k in veri["onayli"]
                       if not (k["edisyon"] == edisyon and k["boy"] in secilen)]
    return once - len(veri["onayli"])


def parser_olustur() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dosya", type=Path, default=VARSAYILAN_DOSYA)
    alt = parser.add_subparsers(dest="komut", required=True)
    ekle_p = alt.add_parser("ekle")
    ekle_p.add_argument("--edisyon", required=True)
    ekle_p.add_argument("--boylar", required=True)
    ekle_p.add_argument("--kanit", required=True)
    ekle_p.add_argument("--onaylayan", required=True)
    alt.add_parser("listele")
    kaldir_p = alt.add_parser("kaldir")
    kaldir_p.add_argument("--edisyon", required=True)
    kaldir_p.add_argument("--boylar", required=True)
    alt.add_parser("dogrula")
    return parser


def main() -> int:
    args = parser_olustur().parse_args()
    try:
        veri = defteri_oku(args.dosya)
        if args.komut == "listele":
            print(json.dumps(veri, ensure_ascii=False, indent=2))
        elif args.komut == "dogrula":
            print(f"PASS: {len(veri['onayli'])} onay kaydi dogrulandi")
        else:
            edisyon = edisyon_duzelt(args.edisyon)
            boylar = boylari_oku(args.boylar)
            if args.komut == "ekle":
                adet = ekle(veri, edisyon, boylar, args.kanit, args.onaylayan)
                dogrula(veri)
                if adet:
                    atomik_yaz(args.dosya, veri)
                print(f"OK: {adet} kayit eklendi")
            else:
                adet = kaldir(veri, edisyon, boylar)
                dogrula(veri)
                if adet:
                    atomik_yaz(args.dosya, veri)
                print(f"OK: {adet} kayit kaldirildi")
        return 0
    except DefterHatasi as exc:
        parser_olustur().error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
