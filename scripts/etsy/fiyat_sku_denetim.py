#!/usr/bin/env python3
"""POD ilanlarinin fiyat, SKU ve envanterini salt okunur denetler."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore  # noqa: E402
from pod_listing_create import SIZE_LABEL, SIZES  # noqa: E402

RENK_SAYISI = 5
URUN_SAYISI = len(SIZES) * RENK_SAYISI
ALANLAR = ["ilan_id", "durum", "kural", "boy", "renk", "sku", "fiyat", "ayrinti"]


def _para(value: Any) -> float | None:
    if isinstance(value, dict):
        try:
            return round(float(value.get("amount")) / float(value.get("divisor") or 100), 2)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _ozellik(product: dict[str, Any], ad: str) -> dict[str, Any] | None:
    for prop in product.get("property_values") or []:
        name = str(prop.get("property_name") or prop.get("formatted_name") or "").strip()
        if name == ad:
            return prop
    return None


def _deger(prop: dict[str, Any] | None) -> str:
    values = (prop or {}).get("values") or []
    return str(values[0]).strip() if len(values) == 1 else ""


def denetle_ilan(listing_id: str, inventory: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Tek envanteri denetler; hata satirlari ve boy fiyatlarini dondurur."""
    products = inventory.get("products") or []
    errors: list[dict[str, Any]] = []
    prices: dict[str, set[float]] = defaultdict(set)
    combinations: Counter[tuple[str, str]] = Counter()
    colors: set[str] = set()

    def fail(rule: str, detail: str, *, size: str = "", color: str = "", sku: str = "", price: Any = "") -> None:
        errors.append({"ilan_id": listing_id, "durum": "FAIL", "kural": rule, "boy": size,
                       "renk": color, "sku": sku, "fiyat": price, "ayrinti": detail})

    if len(products) != URUN_SAYISI:
        fail("varyasyon_sayisi", f"{len(products)} != {URUN_SAYISI}")

    for index, product in enumerate(products, 1):
        size_prop, color_prop = _ozellik(product, "Size"), _ozellik(product, "Primary color")
        names = [str(p.get("property_name") or p.get("formatted_name") or "").strip()
                 for p in product.get("property_values") or []]
        size, color = _deger(size_prop), _deger(color_prop)
        sku = str(product.get("sku") or "").strip()
        offerings = product.get("offerings") or []
        offering = offerings[0] if len(offerings) == 1 else {}
        price = _para(offering.get("price"))

        if names != ["Primary color", "Size"] and names != ["Size", "Primary color"]:
            fail("property_adlari", f"urun {index}: {names!r}", size=size, color=color, sku=sku)
        if not size or size not in SIZE_LABEL.values():
            fail("boy_etiketi", f"beklenmeyen etiket: {size!r}", size=size, color=color, sku=sku)
        size_key = next((key for key, label in SIZE_LABEL.items() if label == size), "")
        if not color:
            fail("renk_degeri", "Primary color tek deger olmali", size=size, sku=sku)
        else:
            colors.add(color)
        if size_key and color:
            combinations[(size_key, color)] += 1
        expected_sku = f"GLOBAL-HPR-{size_key}" if size_key else ""
        if not expected_sku or sku != expected_sku:
            fail("sku", f"beklenen {expected_sku or 'tanimlanamadi'}", size=size_key, color=color, sku=sku)
        if len(offerings) != 1:
            fail("offering_sayisi", f"{len(offerings)} != 1", size=size_key, color=color, sku=sku)
        elif not offering.get("is_enabled") or not isinstance(offering.get("quantity"), (int, float)) or offering.get("quantity") <= 0:
            fail("envanter", "is_enabled true ve quantity > 0 olmali", size=size_key, color=color, sku=sku, price=price)
        if price is None:
            fail("fiyat", "fiyat okunamadi", size=size_key, color=color, sku=sku)
        elif size_key:
            prices[size_key].add(price)

    if len(colors) != RENK_SAYISI:
        fail("renk_sayisi", f"{len(colors)} != {RENK_SAYISI}")
    expected = {(size, color) for size in SIZES for color in colors}
    bad = sorted((size, color, combinations[(size, color)]) for size, color in expected
                 if combinations[(size, color)] != 1)
    if bad:
        fail("varyasyon_matrisi", "; ".join(f"{s}/{c}={n}" for s, c, n in bad))
    for size, values in sorted(prices.items()):
        if len(values) != 1:
            fail("renk_fiyat_farki", f"fiyatlar={sorted(values)}", size=size)
    return errors, {size: next(iter(values)) for size, values in prices.items() if len(values) == 1}


def beklenen_fiyatlar(path: Path = Path(__file__).resolve().parents[2] / "config" / "pod_fiyat.json") -> dict[str, float]:
    """config/pod_fiyat.json 'sizes' (16 boy); bossa beklenen fiyat kurali calismaz."""
    try:
        return {k: round(float(v), 2) for k, v in (json.loads(path.read_text(encoding="utf-8")).get("sizes") or {}).items()}
    except (OSError, ValueError):
        return {}


def denetle_tumu(inventories: list[tuple[str, dict[str, Any]]],
                 beklenen: dict[str, float] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    listing_prices: dict[str, dict[str, float]] = {}
    for listing_id, inventory in inventories:
        item_errors, listing_prices[listing_id] = denetle_ilan(listing_id, inventory)
        errors.extend(item_errors)
        for size, want in (beklenen or {}).items():
            got = listing_prices[listing_id].get(size)
            if got is not None and got != want:
                errors.append({"ilan_id": listing_id, "durum": "FAIL", "kural": "beklenen_fiyat", "boy": size,
                               "renk": "", "sku": "", "fiyat": got, "ayrinti": f"beklenen {want}"})
    for size in SIZES:
        groups: dict[float | None, list[str]] = defaultdict(list)
        for listing_id, prices in listing_prices.items():
            groups[prices.get(size)].append(listing_id)
        if len(groups) > 1 or None in groups:
            detail = "; ".join(f"{price if price is not None else 'YOK'}: {','.join(ids)}"
                               for price, ids in sorted(groups.items(), key=lambda x: str(x[0])))
            errors.append({"ilan_id": ",".join(listing_id for ids in groups.values() for listing_id in ids),
                           "durum": "FAIL", "kural": "ilanlar_arasi_fiyat", "boy": size,
                           "renk": "", "sku": "", "fiyat": "", "ayrinti": detail})
    summary = {"durum": "FAIL" if errors else "PASS", "ilan_sayisi": len(inventories),
               "beklenen_ilan_sayisi": 78, "hata_sayisi": len(errors),
               "kural_hatalari": dict(sorted(Counter(row["kural"] for row in errors).items()))}
    if len(inventories) != 78:
        summary["durum"] = "FAIL"
        summary["kural_hatalari"]["ilan_sayisi"] = 1
        errors.append({"ilan_id": "", "durum": "FAIL", "kural": "ilan_sayisi", "boy": "", "renk": "",
                       "sku": "", "fiyat": "", "ayrinti": f"{len(inventories)} != 78"})
        summary["hata_sayisi"] = len(errors)
    return errors, summary


def _ids(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    ids = [str(row.get("ilan_id") or row.get("listing_id") or "").strip() for row in rows]
    return list(dict.fromkeys(x for x in ids if x))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listings", required=True, type=Path, help="ilan_id/listing_id sutunlu CSV")
    parser.add_argument("--output", type=Path, default=Path("FIYAT_SKU.csv"))
    parser.add_argument("--summary", type=Path, default=Path("FIYAT_SKU_OZET.json"))
    args = parser.parse_args(argv)
    store = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""),
                       os.environ.get("ETSY_SHARED_SECRET", ""))
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    inventories = [(listing_id, api.get(f"/listings/{listing_id}/inventory")) for listing_id in _ids(args.listings)]
    beklenen = beklenen_fiyatlar()
    errors, summary = denetle_tumu(inventories, beklenen)
    summary["beklenen_fiyat_boy"] = len(beklenen)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ALANLAR)
        writer.writeheader()
        writer.writerows(errors or [{"ilan_id": "", "durum": "PASS", "kural": "-", "boy": "", "renk": "",
                                     "sku": "", "fiyat": "", "ayrinti": "tum kurallar gecti"}])
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['durum']}: {summary['ilan_sayisi']}/78 ilan, {summary['hata_sayisi']} hata")
    return 0 if summary["durum"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
