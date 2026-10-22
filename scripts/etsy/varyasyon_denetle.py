#!/usr/bin/env python3
"""Etsy renk-varyasyon gorsel baglantilarini cevrimdisi denetler."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _sonuclar(veri: Any) -> list[dict[str, Any]]:
    """Etsy liste yanitini veya dogrudan verilen listeyi tek bicime getirir."""
    if isinstance(veri, list):
        return veri
    if isinstance(veri, dict) and isinstance(veri.get("results"), list):
        return veri["results"]
    return []


def _renkler(inventory: dict[str, Any]) -> tuple[int | None, list[tuple[str, int]]]:
    """Envanterden Primary color property kimligini ve essiz renkleri okur."""
    property_id: int | None = None
    renkler: dict[int, str] = {}
    for urun in inventory.get("products") or []:
        for ozellik in urun.get("property_values") or []:
            ad = str(ozellik.get("property_name") or ozellik.get("formatted_name") or "").strip().casefold()
            if ad not in {"primary color", "primary colour"}:
                continue
            pid = ozellik.get("property_id")
            if property_id is None:
                property_id = pid
            degerler = ozellik.get("values") or []
            kimlikler = ozellik.get("value_ids") or []
            for sira, value_id in enumerate(kimlikler):
                renkler[value_id] = str(degerler[sira] if sira < len(degerler) else value_id)
    return property_id, [(ad, value_id) for value_id, ad in renkler.items()]


def _beklenenler(inventory: dict[str, Any], images: Any, set_data: dict[str, Any]) -> tuple[int | None, list[dict[str, Any]]]:
    property_id, renkler = _renkler(inventory)
    dosya_sira = {x.get("dosya"): x.get("sira") for x in set_data.get("galeri") or []}
    renk_dosya = set_data.get("renk_gorselleri") or {}
    sira_image = {x.get("rank"): x.get("listing_image_id") for x in _sonuclar(images)}
    return property_id, [
        {
            "renk": renk,
            "property_id": property_id,
            "value_id": value_id,
            "dosya": renk_dosya.get(renk),
            "sira": dosya_sira.get(renk_dosya.get(renk)),
            "image_id": sira_image.get(dosya_sira.get(renk_dosya.get(renk))),
        }
        for renk, value_id in renkler
    ]


def hedef_liste(inventory: dict[str, Any], images: Any, set_data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Envanterdeki renklerden Etsy POST govdesini kurar.

    Eksik SET veya galeri eslesmesi sessizce eksik bir govde uretmesin diye
    ``ValueError`` verir; bu fonksiyon tek basina herhangi bir ag cagrisi yapmaz.
    """
    property_id, beklenenler = _beklenenler(inventory, images, set_data)
    if property_id is None or len(beklenenler) != 5:
        raise ValueError(f"Primary color sayisi 5 olmali (bulunan {len(beklenenler)})")
    eksik = [x["renk"] for x in beklenenler if x["dosya"] is None or x["sira"] is None or x["image_id"] is None]
    if eksik:
        raise ValueError("SET/galeri eslesmesi eksik: " + ", ".join(eksik))
    return {"variation_images": [
        {"property_id": x["property_id"], "value_id": x["value_id"], "image_id": x["image_id"]}
        for x in beklenenler
    ]}


def denetle(inventory: dict[str, Any], variation_images: Any, images: Any,
            set_data: dict[str, Any]) -> dict[str, Any]:
    """Tum baglantilari denetleyip makinece okunabilir rapor dondurur."""
    property_id, beklenenler = _beklenenler(inventory, images, set_data)
    mevcut = _sonuclar(variation_images)
    galeri_ids = {x.get("listing_image_id") for x in _sonuclar(images)}
    sayac = Counter(x.get("value_id") for x in mevcut)
    renk_raporu = []

    for beklenen in beklenenler:
        value_id = beklenen["value_id"]
        kayitlar = [x for x in mevcut if x.get("value_id") == value_id]
        nedenler: list[str] = []
        if sayac[value_id] == 0:
            nedenler.append("variation_images kaydi eksik")
        elif sayac[value_id] > 1:
            nedenler.append(f"variation_images kaydi {sayac[value_id]} kez var")
        if beklenen["dosya"] is None:
            nedenler.append("renk SET renk_gorselleri icinde yok")
        elif beklenen["sira"] is None:
            nedenler.append("renk dosyasi SET galeri icinde yok")
        elif beklenen["image_id"] is None:
            nedenler.append("beklenen sirada galeri gorseli yok")
        for kayit in kayitlar:
            if kayit.get("property_id") != property_id:
                nedenler.append("property_id Primary color ile farkli")
            if kayit.get("image_id") not in galeri_ids:
                nedenler.append("image_id galeride yok")
            elif kayit.get("image_id") != beklenen["image_id"]:
                nedenler.append(f"image_id yanlis siraya bagli (beklenen sira {beklenen['sira']})")
        renk_raporu.append({**beklenen, "durum": "FAIL" if nedenler else "PASS", "nedenler": nedenler})

    envanter_ids = {x["value_id"] for x in beklenenler}
    fazla = [x for x in mevcut if x.get("value_id") not in envanter_ids]
    genel_nedenler = []
    if property_id is None:
        genel_nedenler.append("Primary color property bulunamadi")
    if len(beklenenler) != 5:
        genel_nedenler.append(f"Primary color sayisi 5 degil: {len(beklenenler)}")
    if fazla:
        genel_nedenler.append(f"envanter disi variation_images kaydi: {len(fazla)}")
    durum = "PASS" if not genel_nedenler and all(x["durum"] == "PASS" for x in renk_raporu) else "FAIL"
    return {"durum": durum, "genel_nedenler": genel_nedenler, "renkler": renk_raporu, "fazla_kayitlar": fazla}


def _json_oku(yol: str) -> Any:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--variation-images", required=True)
    parser.add_argument("--images", required=True)
    parser.add_argument("--set", dest="set_yolu", required=True)
    args = parser.parse_args()
    rapor = denetle(_json_oku(args.inventory), _json_oku(args.variation_images),
                    _json_oku(args.images), _json_oku(args.set_yolu))
    print(rapor["durum"])
    print(json.dumps(rapor, ensure_ascii=False, indent=2))
    return 0 if rapor["durum"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
