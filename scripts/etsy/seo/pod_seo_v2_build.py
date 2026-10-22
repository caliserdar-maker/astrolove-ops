#!/usr/bin/env python3
"""POD SEO v2 verisi: 78 POD ilani icin title, description, 13 tag (15 Eyl 2026).
Beklenen SHA-256 tutmazsa DURUR. Kullanim: pod_seo_v2_build.py --out <json>
"""
import argparse
import hashlib
import json
import pathlib
import sys

EXPECTED_SHA256 = "d72bf6b31b8b964c962bebdd758f7a7d141e6e79ee0213291a07bcc81b258065"

TITLE_T = "{A} and {B} Zodiac Couple Print, Minimalist Gold Line Art, Hahnemühle Giclée, Unframed"

SHARED_TAGS = ["zodiac couple print", "compatibility print", "giclee wall art",
               "unframed art print", "minimal gold art", "couple bedroom art",
               "relationship gift", "astrology home decor", "celestial poster"]

DESC_T = """TWO SIGNS. ONE ORIGINAL SYMBOL.

Designed for {A} and {B} couples, this fine art zodiac print merges both glyphs into one continuous emblem drawn by the AstroLove studio. It creates a quiet, meaningful focal point for a bedroom, living room or gallery wall, and makes a lasting anniversary, wedding or engagement gift.

WHY IT IS DIFFERENT
• One original {A} and {B} fusion symbol created in-house
• Minimal gold line art in five carefully developed color editions
• Museum-quality cotton paper with a soft, matte finish
• Made to order and shipped unframed

PAPER AND PRINT
• Hahnemühle Photo Rag 308 gsm, 100% cotton
• Archival pigment giclée print
• Matte and non-reflective surface
• Acid-free and lignin-free, ISO 9706
• Vegan-certified paper and plastic-free packaging

Gold tones are printed as flat golden ink, not metallic foil.

CHOOSE YOUR EDITION
Champagne Ivory, Pure White, Warm Parchment, Midnight Blue or Deep Black. Select your preferred edition from the Color menu.

CHOOSE YOUR SIZE
Thirteen sizes are available, from 8 × 10 in to 30 × 40 in, plus A4, A3 and A2. Use the size-guide image above to choose the best fit for your space.

MADE TO ORDER AND SHIPPING
Each print is produced by our production partner, Prodigi. The current processing and delivery estimate appears in Etsy's shipping section. The 8 × 10 in and A4 sizes ship flat; all other sizes ship rolled in a protective tube. US orders are printed in the US. EU and UK orders are printed at our UK/EU lab. Other orders are produced at the nearest available lab.

PLEASE NOTE
• This listing is for an unframed physical print.
• Frames and room scenes shown in the photographs are presentation examples only.
• Colors may vary slightly between screens and the finished print.
• On matte cotton paper, Deep Black prints as a rich charcoal rather than screen black. This is a natural characteristic of fine art paper.

CARE
Handle the print by its edges. If a rolled print curls, place it flat under a clean weight for one or two days before framing. Frame behind glass and keep away from direct sunlight, fire and moisture.

RETURNS AND DAMAGE
Every print is made specifically for your order, so returns and exchanges are not accepted. If the print arrives damaged, send us a photograph within seven days and we will arrange a replacement at no cost.

ORIGINAL ASTROLOVE ARTWORK
All AstroLove fusion symbols are original studio artwork. The {A} and {B} emblem preserves the exact geometry of the original design."""

# listing_id|burc1|burc2 (listing_id sirali)
ROWS = """
4570031205|Aries|Leo
4570110121|Aquarius|Aquarius
4570110641|Aquarius|Aries
4570112095|Aquarius|Gemini
4570113157|Aquarius|Libra
4570113675|Aquarius|Pisces
4570114301|Aquarius|Scorpio
4570125580|Aquarius|Cancer
4570126104|Aquarius|Capricorn
4570127160|Aquarius|Leo
4570128546|Aquarius|Sagittarius
4570136319|Aquarius|Virgo
4570138967|Aries|Pisces
4570139913|Aries|Scorpio
4570140539|Aries|Taurus
4570141945|Cancer|Cancer
4570143387|Cancer|Leo
4570143815|Cancer|Libra
4570144239|Cancer|Pisces
4570144663|Cancer|Sagittarius
4570145103|Cancer|Scorpio
4570147149|Capricorn|Gemini
4570148769|Capricorn|Pisces
4570149603|Capricorn|Scorpio
4570150148|Aquarius|Taurus
4570151370|Aries|Aries
4570151950|Aries|Cancer
4570152121|Gemini|Leo
4570152410|Aries|Capricorn
4570152561|Gemini|Libra
4570152820|Aries|Gemini
4570153015|Gemini|Pisces
4570153208|Aries|Libra
4570153495|Gemini|Sagittarius
4570154042|Aries|Sagittarius
4570154049|Gemini|Scorpio
4570155327|Gemini|Virgo
4570155846|Aries|Virgo
4570155945|Leo|Leo
4570157258|Cancer|Capricorn
4570157716|Cancer|Gemini
4570160260|Cancer|Taurus
4570160676|Cancer|Virgo
4570161266|Capricorn|Capricorn
4570162562|Capricorn|Leo
4570163164|Capricorn|Libra
4570163968|Capricorn|Sagittarius
4570164962|Capricorn|Taurus
4570165628|Capricorn|Virgo
4570166282|Gemini|Gemini
4570169354|Gemini|Taurus
4570198669|Leo|Libra
4570199091|Leo|Pisces
4570199509|Leo|Sagittarius
4570200893|Leo|Virgo
4570201313|Libra|Libra
4570202333|Libra|Sagittarius
4570202793|Libra|Scorpio
4570203229|Libra|Taurus
4570203731|Libra|Virgo
4570204167|Pisces|Pisces
4570204681|Pisces|Sagittarius
4570205473|Pisces|Scorpio
4570205899|Pisces|Taurus
4570206865|Sagittarius|Sagittarius
4570207855|Sagittarius|Taurus
4570208321|Sagittarius|Virgo
4570209015|Scorpio|Scorpio
4570210411|Scorpio|Virgo
4570214304|Leo|Scorpio
4570214784|Leo|Taurus
4570216030|Libra|Pisces
4570220634|Pisces|Virgo
4570221662|Sagittarius|Scorpio
4570224058|Scorpio|Taurus
4570225672|Taurus|Taurus
4570226386|Taurus|Virgo
4570227104|Virgo|Virgo
"""


def fit(full, short):
    return full if len(full) <= 20 else short


def pair_tags(A, B):
    a, b = A.lower(), B.lower()
    za = lambda s: fit(f"{s} zodiac art", f"{s} art")  # noqa: E731
    if a != b:
        return [fit(f"{a} {b}", f"{a[:3]} {b[:3]} zodiac"), za(a), za(b),
                fit(f"{a} {b} gift", f"{a[:3]} {b[:3]} gift")]
    return [fit(f"{a} {a}", f"{a[:3]} {a[:3]} zodiac"), za(a), f"{a} gift",
            fit(f"{a} couple gift", f"{a[:3]} couple gift")]


def build():
    recs = []
    for line in ROWS.strip().splitlines():
        lid, A, B = line.split("|")
        recs.append({"id": lid, "pair": f"{A} + {B}",
                     "title": TITLE_T.replace("{A}", A).replace("{B}", B),
                     "description": DESC_T.replace("{A}", A).replace("{B}", B),
                     "tags": pair_tags(A, B) + SHARED_TAGS})
    return sorted(recs, key=lambda r: r["id"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    recs = build()
    canon = json.dumps(recs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sha = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    print(f"ilan {len(recs)} | aciklama {len(DESC_T)} karakter | sha256 {sha}")
    if len(recs) != 78 or len({r["id"] for r in recs}) != 78:
        sys.exit("HATA: 78 benzersiz ilan yok. DUR.")
    if sha != EXPECTED_SHA256:
        sys.exit("HATA: SHA-256 tutmadi - metin gorevdekiyle birebir degil. DUR.")
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(recs, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"PASS -> {out}")


if __name__ == "__main__":
    main()
