#!/usr/bin/env python3
"""Onayli metinlerden 78 cift icin iki dijital ilan kaydi uretir."""
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations_with_replacement
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pod_listing_create import SIGNS, personalization_questions  # noqa: E402

PRODUCTS = ("wall_art", "phone_wallpaper")

TITLE = {
    "wall_art": "{A} and {B} Zodiac Wall Art, Personalized Couple Printable with Names and Message, Digital Download",
    "phone_wallpaper": "{A} and {B} Zodiac Phone Wallpaper, Personalized Couple Wallpaper with Names, Digital Download",
}
TAG_TEMPLATES = {
    "wall_art": ("{a} and {b}", "{a} gift", "{a} wall art", "{b} gift", "{b} wall art",
                 "printable wall art", "digital wall art", "personalized couple", "custom couple print",
                 "zodiac couple gift", "astrology wall art", "anniversary gift", "couple gift"),
    "phone_wallpaper": ("{a} and {b}", "{a} gift", "{a} wallpaper", "{b} gift", "{b} wallpaper",
                         "phone wallpaper", "couple wallpaper", "zodiac wallpaper", "custom wallpaper",
                         "name wallpaper", "digital wallpaper", "anniversary gift", "couple gift"),
}

PERSONALIZE = """1. Type each name in the field for its sign (same-sign pairs: type each name in its own field). Each name can be up to 11 letters. Please use English letters. Accents are fine. Names are printed in capitals.
2. Enter a short message of up to 35 characters. We print the message exactly as typed. Russian is welcome. Please do not use emoji.
3. Check your spelling carefully before placing your order."""
HOW = """This is a made to order digital item. We create your personalized files and check every order by hand. If anything needs a change, we message you.

When your files are ready, they are delivered through Etsy and can be found under Purchases. Please download them in a web browser because the Etsy app cannot download files."""

DESCRIPTION = {
    "wall_art": """Personalized {A} and {B} zodiac wall art, a digital printable with your two names and your own short message. Our original AstroLove design joins both zodiac signs into one symbol, made especially for your pair.

WHAT YOU GET

• All 5 colors: Midnight Blue, Deep Black, Pure White, Champagne Ivory, Warm Parchment
• 5 files, one for each color
• Each color is prepared in 5 ratios: 4x5, 3x4, 2x3, 11x14, and A series
• These ratios fit common frame sizes such as 8x10, 16x20, 12x16, 18x24, 12x18, 24x36, 11x14, A4, and A3
• Your two names, with one name under each zodiac sign
• Your short personal message

HOW TO PERSONALIZE

{personalize}

HOW IT WORKS

{how}

GOOD TO KNOW

• This is a digital item. Nothing is shipped.
• Frame is not included.
• Colors may look slightly different on different screens and when printed.
• Because this item is personalized, we do not accept returns.
• If we make a mistake on our side, we fix it.
• A personalized fine art printed version is also available in our shop.

A meaningful personalized gift for an anniversary, wedding, or Valentine's Day.""",
    "phone_wallpaper": """Personalized {A} and {B} zodiac phone wallpaper with your two names and your own short message. Our original AstroLove design joins both zodiac signs into one symbol for a personal look across your devices.

WHAT YOU GET

• All 4 colors: Midnight Blue, Deep Black, Champagne Ivory, Warm Parchment
• Sizes for phone, tablet, desktop, and watch
• Your two names and your short personal message on the phone, tablet, and desktop versions
• The watch size shows your zodiac symbol only, with no names

HOW TO PERSONALIZE

{personalize}

HOW IT WORKS

{how}

GOOD TO KNOW

• This is a digital item. Nothing is shipped.
• Colors may look slightly different on different screens.
• Because this item is personalized, we do not accept returns.
• If we make a mistake on our side, we fix it.

A personal zodiac gift for an anniversary, wedding, or Valentine's Day, made for the two of you.""",
}


def zodiac_pairs():
    return list(combinations_with_replacement(SIGNS, 2))


def _sign(value):
    signs = {sign.casefold(): sign.capitalize() for sign in SIGNS}
    try:
        return signs[value.casefold()]
    except KeyError as exc:
        raise ValueError(f"Bilinmeyen burc: {value}") from exc


def _tags(first, second, product):
    a, b = first.casefold(), second.casefold()
    tags = []
    for index, template in enumerate(TAG_TEMPLATES[product]):
        tag = template.format(a=a, b=b)
        if "cancer gift" in tag:
            tag = tag.replace("cancer gift", "cancer zodiac gift")
        if index == 0 and len(tag) > 20:
            tag = f"{a} {b}"
            if len(tag) > 20:
                continue
        tags.append(tag)
    return tags


def build(sign1, sign2, product):
    if product not in PRODUCTS:
        raise ValueError(f"Urun turu {PRODUCTS} degerlerinden biri olmali")
    first, second = _sign(sign1), _sign(sign2)
    pair = f"{first.upper()}_{second.upper()}"
    values = {"A": first, "B": second, "a": first.casefold(), "b": second.casefold(),
              "personalize": PERSONALIZE, "how": HOW}
    return {"pair": pair, "product": product, "title": TITLE[product].format(**values),
            "tags": _tags(first, second, product), "description": DESCRIPTION[product].format(**values),
            "is_personalizable": True, "personalization_questions": personalization_questions(pair)}


def catalog():
    return [build(a, b, product) for a, b in zodiac_pairs() for product in PRODUCTS]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair")
    parser.add_argument("--product", choices=PRODUCTS)
    args = parser.parse_args(argv)
    if args.product and not args.pair:
        parser.error("--product yalniz --pair ile kullanilabilir")
    try:
        if args.pair:
            first, second = args.pair.split("_", 1)
            products = (args.product,) if args.product else PRODUCTS
            result = [build(first, second, product) for product in products]
        else:
            result = catalog()
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
