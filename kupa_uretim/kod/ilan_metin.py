#!/usr/bin/env python3
"""78 kupa ilani: baslik, 13 etiket, aciklama, kisisellestirme talimati (SEO onayi 17 Eki 2026).
Kullanim: python3 kod/ilan_metin.py <cikti_csv>
Kurallar: baslik <= 140 kr ve < 15 kelime; etiket <= 20 kr, 13 benzersiz; uzun/orta tire yok."""
import csv, itertools, sys

B = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
ORTAK = ["personalized mug", "couple mug", "custom coffee mug", "custom name mug", "gift for couple", "newlywed gift",
         "zodiac mug", "zodiac symbols", "zodiac gift", "astrology mug", "evil eye mug", "engagement mug"]
YEDEK = "wedding mugs"   # cift adi 20 karaktere sigmazsa (MI 1,3k / 64,1k / Typical)
BASLIK = "{A} and {B} Personalized Mug, Zodiac Symbols with Names, Gift for Couples"

ACIKLAMA = """A personalized mug for {A} and {B} couples: your two zodiac symbols join into one original design, with both of your names printed underneath. This zodiac couple mug is printed on both sides, with the symbol, your names and your two signs on the front, and your own short message on the back. A custom coffee mug made just for the two of you.

[ A PERSONALIZED COUPLE GIFT ]
Made as a wedding gift for couples who love astrology, it is just as sweet as an engagement gift for couples, an anniversary surprise or a newlywed gift. A zodiac gift they will use every morning: a custom name mug that turns their two signs into one symbol.

[ 7 STYLES FOR YOUR {AU} AND {BU} MUG ]
Rose Ribbon, Botanical, Gold, Nazar Bond, Promise Line, Aegean Tile or Mediterranean. Looking for an evil eye mug? Choose Nazar Bond or Mediterranean. Every style of this zodiac mug uses the same original {A} and {B} symbol. See photo 2 for all seven.

[ YOUR PERSONALIZED COFFEE MUG IN TWO SIZES ]
- 11 oz (325 ml)
- 15 oz (444 ml)
Same design on both sizes.

[ HOW TO PERSONALIZE YOUR MUG ]
Write three lines in the personalization box:
1. {E1} (up to 10 letters)
2. {E2} (up to 10 letters)
3. Your message (up to 30 characters, one line)
Names are printed in capital letters on the front. Leave the message blank and we print the sample message shown for your style. Please check your spelling before you order.

[ DETAILS ]
- Glossy white ceramic mug, white inside
- Dishwasher and microwave safe
- Printed on both sides
- Made to order, just for you
- Original zodiac symbols designed by AstroLoveArt

[ RETURNS ]
Every mug is personalized, so we can't accept returns or exchanges. If your mug arrives damaged, send us a photo within 7 days and we'll replace it at no cost.

Questions? Send us a message, we're happy to help.
Lena & Serdar / AstroLoveArt"""

TALIMAT = "Please write 3 lines:\n{E1} (up to 10 letters)\n{E2} (up to 10 letters)\nMessage (up to 30 characters, one line)\nLeave the message blank for the sample message."

satirlar = []
for a, b in itertools.combinations_with_replacement(B, 2):
    a, b = sorted((a, b), key=str.lower)
    ayni = a == b
    e1, e2 = (f"Name under left {a}", f"Name under right {b}") if ayni else (f"Name under {a}", f"Name under {b}")
    t1 = f"{a} and {b}".lower()
    if len(t1) > 20:
        t1 = f"{a} {b}".lower()
    if len(t1) > 20:
        t1 = YEDEK
    etiket = [t1] + ORTAK
    baslik = BASLIK.format(A=a, B=b)
    aciklama = ACIKLAMA.format(A=a, B=b, AU=a.upper(), BU=b.upper(), E1=e1, E2=e2)
    talimat = TALIMAT.format(E1=e1, E2=e2)
    # kontroller
    assert len(baslik) <= 140 and len(baslik.split()) < 15, baslik
    assert len(etiket) == 13 and len(set(etiket)) == 13 and all(len(x) <= 20 for x in etiket), etiket
    assert len(talimat) <= 256, (len(talimat), talimat)
    for metin in (baslik, aciklama, talimat, *etiket):
        assert "—" not in metin and "–" not in metin
    satirlar.append({"kod": f"{a.upper()}_{b.upper()}", "baslik": baslik, "baslik_kr": len(baslik),
                     "etiketler": ", ".join(etiket), "kisisellestirme_talimati": talimat,
                     "talimat_kr": len(talimat), "aciklama": aciklama})

with open(sys.argv[1], "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(satirlar[0]))
    w.writeheader(); w.writerows(satirlar)
print(len(satirlar), "ilan; en uzun baslik", max(s["baslik_kr"] for s in satirlar),
      "kr; en uzun talimat", max(s["talimat_kr"] for s in satirlar), "kr; yedek etiketli:",
      [s["kod"] for s in satirlar if s["etiketler"].startswith(YEDEK)])
