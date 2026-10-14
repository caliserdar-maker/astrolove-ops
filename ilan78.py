"""Bizim Yilimiz Paper: 78 per-pair listing texts (title, 13 tags, description).
Data: Etsy Marketplace Insights 10 Eki + 14 Eki (research_notes/Bizim Yilimiz SEO). Serdar: 3 groups OK, no signature."""
import csv, itertools, re
S = "aries taurus gemini cancer leo virgo libra scorpio sagittarius capricorn aquarius pisces".split()
PAIRS = sorted(set(tuple(sorted(p)) for p in itertools.combinations_with_replacement(S, 2)))
assert len(PAIRS) == 78
# sign gift tag: most searched non-ambiguous form (MI 10 Eki); cancer avoids medical "cancer gift"
SIGN_TAG = {"aries": "aries gifts", "taurus": "taurus gifts", "gemini": "gemini gifts", "cancer": "cancer zodiac gift",
            "leo": "leo gifts", "virgo": "virgo gifts", "libra": "libra gift", "scorpio": "scorpio gifts",
            "sagittarius": "sagittarius gifts", "capricorn": "capricorn gift", "aquarius": "aquarius gift", "pisces": "pisces gift"}
COMMON = ["1st anniversary gift", "paper anniversary", "1 year anniversary", "first anniversary", "anniversary card",
          "1st anniversary card", "gift for husband", "gift for boyfriend", "newlywed gift", "wedding keepsake", "anniversary gift"]
LEAD = {"A": "1st Anniversary Gift for Husband", "B": "1 Year Anniversary Gift for Boyfriend", "C": "1st Wedding Anniversary Gift"}
OPEN = {"A": "A personalized 1st anniversary gift for your husband or your wife, made from your two zodiac signs, {a} and {b}.",
        "B": "A personalized 1 year anniversary gift for your boyfriend or your girlfriend, made from your two zodiac signs, {a} and {b}.",
        "C": "A personalized 1st wedding anniversary gift made from your two zodiac signs, {a} and {b}."}
BODY = """{open} Your names and your special date are added to your own shared symbol, for married couples and for couples celebrating one year together.

Every AstroLoveArt design merges two zodiac signs into one shared symbol. This listing is for the {a} and {b} symbol shown in the photos.

HOW TO ORDER
1. Choose your style and your format.
2. Fill in the personalization boxes: {names} and your special date (your wedding day or the day you met). Example: {ex}, 14 June 2025.
3. Top line: "Paper Anniversary" for married couples or "Our First Year" for couples who are dating. The card always says "Happy First Anniversary".
4. Optional short line: up to 20 characters of your own to replace "Year One". Leave it empty to keep "Year One".

FREE PREVIEW BEFORE YOU ORDER
Would you like to see your design first? Message us your names, your date and your chosen style, and we will send you a free preview.

AFTER YOU ORDER
We send your final preview in Etsy Messages within 24 hours. As soon as you approve it, we prepare your file or your print.

STYLES
Starlit, Timeless, First Page, Layers, Botanical.

FORMATS
- Digital card 5x7: a single-sided flat card sent as a digital file, to print at home or at a print shop. Nothing is shipped.
- Digital file 8x10: an 8x10 inch, 300 dpi JPG for your own printing. Nothing is shipped.
- Shipped print 8x10: printed on matte paper and shipped to you by our production partner. Unframed; it fits standard frames.

PLEASE NOTE
The gold, relief and paper layer looks are printed visual effects. Prints are flat matte prints, with no foil, no raised layers and no cut paper pieces. Colors can look slightly different on screens and on paper.

WHY PAPER
Paper is the traditional gift for the first wedding anniversary. A print of your own two signs, your names and your date is a paper gift made only for the two of you.

ABOUT OUR DESIGNS
We use AI tools in our design process, and we check every file by hand before it is delivered or printed."""
rows = []
for i, (x, y) in enumerate(PAIRS):
    g = "ABC"[i % 3]
    a, b = x.capitalize(), y.capitalize()
    title = f"{LEAD[g]}, Personalized {a} {b} Zodiac Couple Print with Names and Date, Paper Anniversary Card"
    tags = COMMON + ([SIGN_TAG[x], SIGN_TAG[y]] if x != y else [SIGN_TAG[x], "couple gift"])
    if x != y:
        names, ex = f"the name under {a}, the name under {b}", f"{a}: Emma, {b}: James"
    else:
        names, ex = "the name on the left, the name on the right", "Emma, James"
    desc = BODY.format(open=OPEN[g].format(a=a, b=b), a=a, b=b, names=names, ex=ex)
    # checks
    assert len(title) <= 140, title
    assert len(tags) == 13 and len(set(tags)) == 13 and all(len(t) <= 20 for t in tags), tags
    for t in [title, desc] + tags:
        assert not re.search("[–—]", t), t
    rows.append({"no": i + 1, "cift": f"{x.upper()}_{y.upper()}", "grup": g, "baslik": title, "baslik_uzunluk": len(title),
                 **{f"etiket_{k+1}": t for k, t in enumerate(tags)}, "aciklama": desc})
with open("BIZIM_YILIMIZ_78_ILAN_METIN.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
from collections import Counter
print(Counter(r["grup"] for r in rows), max(r["baslik_uzunluk"] for r in rows))
for r in rows:
    if r["cift"] in ("CANCER_LIBRA", "ARIES_LEO", "LEO_LEO"): print(r["no"], r["grup"], r["baslik"], [r[f"etiket_{k}"] for k in (12, 13)])
