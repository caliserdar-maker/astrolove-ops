#!/usr/bin/env python3
"""78 dijital ilani donusturur; varsayilan mod salt-okur kuru kosudur."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_listing_create import personalization_questions  # noqa: E402

SIGNS = {x.upper(): x for x in (
    "Aquarius Aries Taurus Gemini Cancer Leo Virgo Libra Scorpio Sagittarius Capricorn Pisces"
).split()}
DIFF_FIELDS = ["ilan_id", "cift", "eylem", "alan", "once", "sonra", "sonuc"]

WALL_DESCRIPTION = """Personalized {A} and {B} zodiac wall art, a digital printable with your two names and your own short message. Our original AstroLove design joins both zodiac signs into one symbol, made especially for your pair.

WHAT YOU GET

• All 5 colors: Midnight Blue, Deep Black, Pure White, Champagne Ivory, Warm Parchment
• 5 files, one for each color
• Each color is prepared in 5 ratios: 4x5, 3x4, 2x3, 11x14, and A series
• These ratios fit common frame sizes such as 8x10, 16x20, 12x16, 18x24, 12x18, 24x36, 11x14, A4, and A3
• Your two names, with one name under each zodiac sign
• Your short personal message

HOW TO PERSONALIZE

1. Type each name in the field for its sign (same-sign pairs: type each name in its own field). Each name can be up to 11 letters. Please use English letters. Accents are fine. Names are printed in capitals.
2. Enter a short message of up to 35 characters. We print the message exactly as typed. Russian is welcome. Please do not use emoji.
3. Check your spelling carefully before placing your order.

HOW IT WORKS

This is a made to order digital item. We create your personalized files and check every order by hand. If anything needs a change, we message you.

When your files are ready, they are delivered through Etsy and can be found under Purchases. Please download them in a web browser because the Etsy app cannot download files.

GOOD TO KNOW

• This is a digital item. Nothing is shipped.
• Frame is not included.
• Colors may look slightly different on different screens and when printed.
• Because this item is personalized, we do not accept returns.
• If we make a mistake on our side, we fix it.
• A personalized fine art printed version is also available in our shop.

A meaningful personalized gift for an anniversary, wedding, or Valentine's Day."""


class Dur(RuntimeError):
    """Fail-closed kosu durdurma hatasi."""


def read_plan(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    required = {"ilan_id", "cift", "eylem"}
    if not rows or not required <= set(rows[0]):
        raise Dur("plan bos veya gerekli sutunlar eksik")
    if len({r["ilan_id"].strip() for r in rows}) != len(rows):
        raise Dur("planda yinelenen ilan_id")
    return rows


def read_keeper_ids(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise Dur("kalan ilan listesi bos")
    key = next((k for k in rows[0] if k.casefold() in {"ilan_id", "listing_id"}), None)
    if not key:
        raise Dur("kalan ilan listesinde ilan_id/listing_id yok")
    return {r[key].strip() for r in rows if r.get(key, "").strip()}


def validate_sources(rows: list[dict[str, str]], keepers: set[str]) -> None:
    planned = {r["ilan_id"].strip() for r in rows if r["eylem"].strip() == "TUT_VE_DONUSTUR"}
    if planned != keepers:
        raise Dur(f"iki liste celisiyor (plan={len(planned)}, kalan={len(keepers)})")
    if len(keepers) != 78:
        raise Dur(f"kalan ilan sayisi 78 degil: {len(keepers)}")


def pair_parts(pair: str) -> tuple[str, str]:
    bits = pair.upper().split("_")
    if len(bits) != 2 or any(x not in SIGNS for x in bits):
        raise Dur(f"gecersiz cift: {pair}")
    return SIGNS[bits[0]], SIGNS[bits[1]]


def pair_tag(a: str, b: str) -> str | None:
    value = f"{a.lower()} and {b.lower()}"
    if len(value) <= 20:
        return value
    value = f"{a.lower()} {b.lower()}"
    return value if len(value) <= 20 else None


def target(pair: str) -> dict[str, Any]:
    a, b = pair_parts(pair)
    cancer = lambda sign, suffix: "cancer zodiac gift" if sign == "Cancer" and suffix == "gift" else f"{sign.lower()} {suffix}"
    tags = [pair_tag(a, b), cancer(a, "gift"), cancer(a, "wall art"), cancer(b, "gift"), cancer(b, "wall art"),
            "printable wall art", "digital wall art", "personalized couple", "custom couple print",
            "zodiac couple gift", "astrology wall art", "anniversary gift", "couple gift"]
    tags = list(dict.fromkeys(x for x in tags if x))
    if any(len(x) > 20 for x in tags):
        raise Dur("20 karakteri asan etiket olustu")
    return {
        "title": f"{a} and {b} Zodiac Wall Art, Personalized Couple Printable with Names and Message, Digital Download",
        "tags": tags, "description": WALL_DESCRIPTION.format(A=a, B=b), "price": 14.99,
        "is_personalizable": True,
    }


def normalize(field: str, value: Any) -> Any:
    if field == "price":
        if isinstance(value, dict):
            return round(float(value.get("amount", 0)) / float(value.get("divisor", 100)), 2)
        return round(float(value or 0), 2)
    if field == "tags":
        return list(value or [])
    return value


def run(api: Any, shop: str, rows: list[dict[str, str]], selected: set[str], budget: int,
        apply: bool) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []

    def call(method: str, path: str, *args: Any, **kwargs: Any) -> Any:
        if api.calls >= budget:
            raise Dur(f"cagri butcesi asildi: {budget}")
        return getattr(api, method)(path, *args, **kwargs)

    for row in rows:
        lid, action = row["ilan_id"].strip(), row["eylem"].strip()
        if selected and lid not in selected:
            continue
        current = call("get", f"/listings/{lid}")  # Her ilanda ilk islem state okumadir.
        state = str(current.get("state") or "").casefold()
        if action == "TUT_VE_DONUSTUR":
            if state in {"draft", "edit"}:
                out.append({"ilan_id": lid, "cift": row["cift"], "eylem": action, "alan": "state",
                            "once": state, "sonra": state, "sonuc": "TASLAK_KORUNDU"})
                continue
            wanted = target(row["cift"])
            made_to_order_api = "is_made_to_order" in current
            if made_to_order_api:
                wanted["is_made_to_order"] = True
            changes = {k: v for k, v in wanted.items() if normalize(k, current.get(k)) != normalize(k, v)}
            for field, value in changes.items():
                out.append({"ilan_id": lid, "cift": row["cift"], "eylem": action, "alan": field,
                            "once": json.dumps(current.get(field), ensure_ascii=False),
                            "sonra": json.dumps(value, ensure_ascii=False), "sonuc": "PLANLANDI"})
            # Open API bu alani/soru semasini kabul etmeyebilir; panel adimi raporda aciktir.
            if not made_to_order_api:
                out.append({"ilan_id": lid, "cift": row["cift"], "eylem": action, "alan": "is_made_to_order",
                            "once": "API_ALANI_YOK", "sonra": "true", "sonuc": "ELLE_UI"})
            questions = personalization_questions(row["cift"])
            if apply and changes:
                payload = dict(changes)
                if "tags" in payload:
                    payload["tags"] = ",".join(payload["tags"])
                call("patch", f"/shops/{shop}/listings/{lid}", payload)
                call("put_json", f"/shops/{shop}/listings/{lid}/personalization",
                     {"personalization_questions": questions})
        elif action in {"TASLAGA_AL", "ARSIV"}:
            if state in {"draft", "edit"}:
                result = "TASLAK_KORUNDU"
            elif state == "inactive":
                result = "DEGISIM_YOK"
            else:
                result = "PLANLANDI"
                if apply:
                    call("patch", f"/shops/{shop}/listings/{lid}", {"state": "inactive"})
            out.append({"ilan_id": lid, "cift": row["cift"], "eylem": action, "alan": "state",
                        "once": state, "sonra": "inactive", "sonuc": result})
        else:
            raise Dur(f"bilinmeyen eylem: {action}")
    return out


def write_diff(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=DIFF_FIELDS)
        writer.writeheader(); writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", type=Path, required=True); ap.add_argument("--keepers", type=Path, required=True)
    ap.add_argument("--mode", choices=("kuru", "uygula"), default="kuru")
    ap.add_argument("--listings", default="", help="virgulle ayrilmis ilan idleri; bos=tumu")
    ap.add_argument("--budget", type=int, required=True); ap.add_argument("--approval-id", default="")
    ap.add_argument("--output", type=Path, default=Path("DIJITAL_DONUSUM_FARK.csv"))
    args = ap.parse_args(argv)
    try:
        if args.budget < 1: raise Dur("cagri butcesi pozitif olmali")
        if args.mode == "uygula" and not args.approval_id.strip(): raise Dur("uygula icin onay_kimligi zorunlu")
        rows = read_plan(args.plan); validate_sources(rows, read_keeper_ids(args.keepers))
        selected = {x.strip() for x in args.listings.split(",") if x.strip()}
        known = {r["ilan_id"].strip() for r in rows}
        if not selected <= known: raise Dur("istenen ilan planda yok")
        key, secret = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
        mask(key); mask(secret)
        store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
        if store.needs_refresh(): store.refresh()
        result = run(Etsy(store), os.environ["ETSY_SHOP_ID"], rows, selected, args.budget, args.mode == "uygula")
        write_diff(args.output, result)
        log(f"PASS: mod={args.mode}, fark={len(result)}; made-to-order API alani yoksa Etsy UI'da elle tamamlanir.")
        return 0
    except (Dur, OSError, KeyError, csv.Error) as exc:
        log(f"DUR: {exc}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
