#!/usr/bin/env python3
"""Etsy dijital ilanlari icin salt okunur 78-ilan donusum plani olusturur."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from alt_metin_kontrol import BURCLAR
from magaza_denetim import ilan_turu

ALANLAR = [
    "ilan_id", "durum", "taslak_uyarisi", "cift", "esleme_durumu", "eylem",
    "satis", "favori", "goruntulenme", "olusturma_zamani", "esleme_kaynagi",
]


def _sonuclar(veri: Any) -> list[dict[str, Any]]:
    """Magaza denetimi veya Etsy batch cevaplarindaki ilan listesini ac."""
    if isinstance(veri, list):
        return [x for x in veri if isinstance(x, dict)]
    if not isinstance(veri, dict):
        return []
    for anahtar in ("results", "listings", "active", "draft"):
        if anahtar in veri:
            deger = veri[anahtar]
            if anahtar in ("active", "draft"):
                kalan = _sonuclar(deger)
                for ilan in kalan:
                    ilan.setdefault("state", anahtar)
                diger = _sonuclar(veri.get("draft" if anahtar == "active" else "active", []))
                for ilan in diger:
                    ilan.setdefault("state", "draft" if anahtar == "active" else "active")
                return kalan + diger
            return _sonuclar(deger)
    return []


def _sku_metinleri(deger: Any) -> list[str]:
    bulunan: list[str] = []
    if isinstance(deger, dict):
        for anahtar, alt in deger.items():
            if anahtar.casefold() == "sku" and alt is not None:
                bulunan.append(str(alt))
            else:
                bulunan.extend(_sku_metinleri(alt))
    elif isinstance(deger, list):
        for alt in deger:
            bulunan.extend(_sku_metinleri(alt))
    return bulunan


def _kaynak_cifti(metin: str) -> tuple[str, str] | None | str:
    isimler = re.findall(r"(?<![A-Za-z])(?:" + "|".join(BURCLAR) + r")(?![A-Za-z])", metin, re.I)
    isimler = [ad.capitalize() for ad in isimler]
    farkli = list(dict.fromkeys(isimler))
    if len(farkli) > 2:
        return "CAKISMA"
    if len(farkli) == 2:
        return tuple(sorted(farkli, key=BURCLAR.index))
    if len(farkli) == 1 and len(isimler) >= 2:
        return (farkli[0], farkli[0])
    return None


def cifti_bul(ilan: dict[str, Any]) -> tuple[str, str]:
    """Baslik, etiket ve SKU kanitlarini birlestirip (cift, kaynak) dondur."""
    kaynaklar = {
        "baslik": str(ilan.get("title") or ""),
        "etiket": " ".join(map(str, ilan.get("tags") or [])),
        "SKU": " ".join(_sku_metinleri(ilan)),
    }
    adaylar: dict[tuple[str, str], list[str]] = {}
    catismali = []
    for kaynak, metin in kaynaklar.items():
        sonuc = _kaynak_cifti(metin)
        if sonuc == "CAKISMA":
            catismali.append(kaynak)
        elif isinstance(sonuc, tuple):
            adaylar.setdefault(sonuc, []).append(kaynak)
    if catismali or len(adaylar) > 1:
        ayrinti = ",".join(catismali + ["/".join(cift) for cift in adaylar])
        return "", "CAKISMA:" + ayrinti
    if not adaylar:
        return "", "ESLESMEDI"
    cift, kanit = next(iter(adaylar.items()))
    return "_".join(ad.upper() for ad in cift), "+".join(kanit)


def _sayi(ilan: dict[str, Any], *adlar: str) -> int | None:
    for ad in adlar:
        if ilan.get(ad) is not None:
            try:
                return int(ilan[ad])
            except (TypeError, ValueError):
                pass
    return None


def _siralama(ilan: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
    satis = _sayi(ilan, "sales", "num_sales", "sales_count")
    favori = _sayi(ilan, "num_favorers", "favorites", "favorite_count")
    goruntulenme = _sayi(ilan, "views", "view_count")
    zaman = _sayi(ilan, "creation_timestamp", "created_timestamp", "create_timestamp")
    metrik_var = any(x is not None for x in (satis, favori, goruntulenme))
    # max(): metrik varsa etkilesim oncelikli; yoksa daha eski zaman oncelikli.
    return (int(metrik_var), satis or 0, favori or 0, goruntulenme or 0, -(zaman or 2**63), str(ilan.get("listing_id") or ""))


def planla(ilanlar: list[dict[str, Any]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    dijital = [ilan for ilan in ilanlar if ilan_turu(ilan) == "dijital"]
    bilgiler = []
    kumeler: dict[str, list[dict[str, Any]]] = {}
    for ilan in dijital:
        cift, kaynak = cifti_bul(ilan)
        kayit = {"ilan": ilan, "cift": cift, "kaynak": kaynak}
        bilgiler.append(kayit)
        if cift:
            kumeler.setdefault(cift, []).append(kayit)
    kazananlar = {id(max(kume, key=lambda x: _siralama(x["ilan"]))) for kume in kumeler.values()}
    satirlar: list[dict[str, str]] = []
    for bilgi in bilgiler:
        ilan, cift, kaynak = bilgi["ilan"], bilgi["cift"], bilgi["kaynak"]
        durum = str(ilan.get("state") or "bilinmiyor").casefold()
        taslak = durum in {"draft", "edit"}
        if id(bilgi) in kazananlar:
            eylem = "TUT_VE_DONUSTUR"
        else:
            eylem = "ARSIV" if taslak else "TASLAGA_AL"
        satirlar.append({
            "ilan_id": str(ilan.get("listing_id") or ""), "durum": durum,
            "taslak_uyarisi": "UPDATE_LISTING_YAYINA_ALABILIR" if taslak and eylem == "TUT_VE_DONUSTUR" else "",
            "cift": cift, "esleme_durumu": "ESLESTI" if cift else kaynak.split(":", 1)[0], "eylem": eylem,
            "satis": str(_sayi(ilan, "sales", "num_sales", "sales_count") or ""),
            "favori": str(_sayi(ilan, "num_favorers", "favorites", "favorite_count") or ""),
            "goruntulenme": str(_sayi(ilan, "views", "view_count") or ""),
            "olusturma_zamani": str(_sayi(ilan, "creation_timestamp", "created_timestamp", "create_timestamp") or ""),
            "esleme_kaynagi": kaynak,
        })
    satirlar.sort(key=lambda x: (x["cift"] or "ZZZ", x["eylem"], x["ilan_id"]))
    ozet = {
        "dijital_ilan": len(satirlar), "eslesen_cift": len(kumeler),
        "eylemler": dict(Counter(x["eylem"] for x in satirlar)),
        "cakismalar": [x["ilan_id"] for x in satirlar if x["esleme_durumu"] == "CAKISMA"],
        "eslesmeyenler": [x["ilan_id"] for x in satirlar if x["esleme_durumu"] == "ESLESMEDI"],
        "eksik_cift_sayisi": 78 - len(kumeler),
        "uyari": "Taslak TUT_VE_DONUSTUR ilanlarda updateListing otomatik yayin riski vardir; uygulama bu aracın kapsami disindadir.",
    }
    return satirlar, ozet


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path, help="magaza_denetim veya getListingsByListingIds ham JSON")
    ap.add_argument("--output", type=Path, default=Path("PLAN.csv"))
    ap.add_argument("--summary", type=Path, help="Turkce Markdown ozet yolu")
    args = ap.parse_args(argv)
    try:
        ilanlar = _sonuclar(json.loads(args.input.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"HATA: girdi okunamadi: {exc}")
        return 2
    satirlar, ozet = planla(ilanlar)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as dosya:
        yazici = csv.DictWriter(dosya, fieldnames=ALANLAR)
        yazici.writeheader()
        yazici.writerows(satirlar)
    if args.summary:
        eylemler = ozet["eylemler"]
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(
            "# Dijital Donusum Plani Ozeti\n\n"
            f"- TUT_VE_DONUSTUR: {eylemler.get('TUT_VE_DONUSTUR', 0)}\n"
            f"- TASLAGA_AL: {eylemler.get('TASLAGA_AL', 0)}\n"
            f"- ARSIV: {eylemler.get('ARSIV', 0)}\n"
            f"- Eslesmeyen: {len(ozet['eslesmeyenler'])}\n"
            f"- Cakisan: {len(ozet['cakismalar'])}\n"
            f"- 78 cift kapsami: {ozet['eslesen_cift']}/78 (eksik: {ozet['eksik_cift_sayisi']})\n",
            encoding="utf-8",
        )
    print(json.dumps(ozet, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
