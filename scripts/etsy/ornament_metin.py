#!/usr/bin/env python3
"""ORNAMENT 78 ilan metinleri (baslik, 13 etiket, aciklama, 11 alt metin, 3 kisisellestirme kutusu) -> data/pod/ORNAMENT78_METIN.csv.
Kaynak (bagli): claude/AstroLove_ORNAMENT_SEO_KARAR_20261103.md (baslik S1, etiket kalibi, aciklama), KARARLAR_20261106 (D1 onizleme
adimlari, D2 stil adlari), KARARLAR_20261106_2 (6 Kas gece: 3 ayri zorunlu kutu, christmas ornament etiketi anniversary ornament yerine,
fiyat: Serdar 29,99 secti; .90 kurali (ANA_1 1.1) ile ornament_taslak FIYAT 29.90, sabah teyit; ucretsiz kargo, hazirlik 3-5 gun). Kart metinleri (K03 "Letters A to Z only, printed in capitals", K05 onizleme adimlari) Serdar
"hepsi ok" (6 Kas) ile onayli; aciklama ayni sozleri kullanir. Tarih bicimi sipariş hatti ciktisi "JUNE 14, 2025" (siparis_girdi.py).
Isim: ilanda harf siniri YOK (Serdar 5 Kas "Sinir yok, sigmazsa sor", ORNAMENT_SEO_DUZELTME_20261104 bolum 3; onayli cumle aynen);
Etsy kutusu karakter siniri ISIM_MAX (yalniz Etsy alani; sigmayi siparis kapisi olcer, etsy-yayin-hatti 9).
Gumruk cumlesi CIKARILDI (6 Kas gece Merkez): Etsy ABD'ye yurt disi gonderimde DDP zorunlu (ANA_1 1.3); "buyer's responsibility" ABD icin celisir,
cumle hic onaylanmamisti (ANA_1 4.3 "ONERI"); Serdar'a sabah sorusu.
Alt metin: <= 250, magaza adi yok, gorseldeki yazi icinde (ANA_1 4.1, SADE_SEO_KARAR).
Kurallar: uzun/orta tire yok, kisi adi yok, kanitsiz soz yok (premium, long-lasting, free preview), AI beyani aciklamada.
Kullanim: python3 scripts/etsy/ornament_metin.py [--kontrol]  (cikti CSV + kapi; FAIL -> cikis 1)"""
import csv
import itertools
import re
import sys
from pathlib import Path

BURCLAR = ["ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN", "AQUARIUS", "PISCES"]
CIFTLER = sorted("_".join(sorted(p)) for p in itertools.combinations_with_replacement(BURCLAR, 2))   # 78, alfabetik
STILLER = ["Ruby", "Sapphire", "Emerald", "White", "Ivory"]                                            # D2 (sira bu)
SABIT_ETIKET = ["couple ornament", "custom ornament", "engagement ornament", "wedding ornament", "custom name ornament",
                "newlywed ornament", "christmas ornament", "ceramic ornament", "zodiac ornament"]   # 6 Kas gece: christmas, anniversary yerine
AI = "We use AI tools to help create the artwork"
YASAK = re.compile(r"premium|long.lasting|free preview|printful|gold foil|lena|serdar|astrolove(?!art)|\bletters\)|\{N\}", re.I)
TIRE = re.compile("[–—]")
ALAN = ["kod", "baslik", "etiketler", "aciklama"] + [f"alt_{i:02d}" for i in range(1, 12)] + ["soru1", "soru2", "soru3", "talimat_isim", "talimat_tarih"]


def adlar(c):
    a, b = (x.capitalize() for x in c.split("_"))
    return a, b, a == b


def baslik(c):
    a, b, ayni = adlar(c)
    return (f"Personalized Ornament, {a} and {b} Zodiac Couple Keepsake with Names and Date, {a} Gifts"
            + ("" if ayni else f", {b} Gifts"))


def etiketler(c):
    a, b, ayni = (x.lower() if isinstance(x, str) else x for x in adlar(c))
    e1 = f"{a} and {b}" if len(f"{a} and {b}") <= 20 else (f"{a} {b}" if len(f"{a} {b}") <= 20 else "astrology ornament")
    if ayni:
        son = [f"{a} gifts", f"{a} zodiac"]
    else:
        son = [f"{a} gifts", f"{b} gifts"]
    if e1 == "astrology ornament":
        e13 = "mr and mrs ornament"
    elif "cancer" in (a, b):
        e13 = "cancer zodiac gift"
    else:
        e13 = "astrology ornament"
    return [e1] + SABIT_ETIKET + son + [e13]


def aciklama(c):
    a, b, ayni = adlar(c)
    hed = f"Among {a} Gifts, this one" if ayni else f"Among {a} Gifts and {b} Gifts, this one"
    n1, n2 = ("First Name", "Second Name") if ayni else (f"Name for {a}", f"Name for {b}")   # kutu ve K03 karti ile birebir (inceleme 6 Kas)
    return f"""A personalized ornament for {a} and {b} couples: your two zodiac signs join into one original symbol, with your two names and your special date. A couple ornament and zodiac keepsake made just for the two of you, for an engagement, a wedding, an anniversary or your first holiday season together. {hed} carries both of your signs and your names.

The zodiac symbol is an original AstroLoveArt design. {AI}, and every design is reviewed and finished by us.

[ WHAT YOU GET ]
One round ceramic ornament, printed on both sides with the same design.
Center: the {a} and {b} symbol inside a thin ring, with the two small zodiac signs below it.
Below: your two names in capital letters with our small logo between them, and your date at the bottom.

[ 5 STYLES ]
Ruby, Sapphire or Emerald: a deep jewel-toned background with gold-colored details.
White: clean white ceramic with gold-colored details.
Ivory: a soft cream background with gold-colored details.
The gold is a printed color, not metallic foil. See the style photos.

[ SIZE AND DETAILS ]
- 100% ceramic with a glossy finish
- Round, 2.99 in (7.6 cm) across and 0.1 in (2.5 mm) thick
- Gold-colored string included
- Made to order, just for you

[ HOW TO PERSONALIZE ]
Fill in the three personalization boxes:
1. {n1}
2. {n2}
3. Your date, for example JUNE 14, 2025
Names must use English letters. Names are printed in capital letters.
Please check your spelling, we print exactly what you write.
If your two names are too long to fit together, we'll message you before your ornament goes into production and ask for a shorter version or a nickname.

[ YOUR PREVIEW ]
For every order, we send a preview of your ornament via Etsy Messages. We make your ornament once you approve the preview.

[ SHIPPING ]
Made and shipped by our production partner, with free shipping. You can see the estimated delivery time for your country at checkout.

[ RETURNS ]
Every ornament is personalized, so we can't accept returns or exchanges for a change of mind. If your ornament arrives damaged, send us a photo within 7 days of delivery and we'll replace it at no cost.

Questions? Send us a message, we're happy to help."""


def alt_metinler(c):
    """Gorseldeki yazi + ne gosterdigi (ANA_1 4.1: <= 250, magaza adi yok). Kart yazilari kart_orn/ornament_kart.py ile birebir."""
    a, b, ayni = adlar(c)
    ab, amp = f"{a} and {b}", f"{a.upper()} & {b.upper()}"
    s2 = (f"Two Signs, One Shared Symbol: two {a} signs joined into one original design" if ayni
          else f"Two Signs, One Shared Symbol: {ab} joined into one original design") + ", personalized with your two names and your date"
    n1, n2 = ("First Name", "Second Name") if ayni else (f"Name for {a}", f"Name for {b}")
    return [f"{amp} Personalized Ornament: {ab} zodiac couple ornament in Ruby, round ceramic, shown with sample names and date",
            s2,
            f"Your Names, Your Date: {n1} and {n2}, letters A to Z only, printed in capitals, and your date, for example JUNE 14, 2025. Please check your spelling before you order",
            "Size & Details: round ceramic, 2.99 in (7.6 cm) across, 0.1 in (2.5 mm) thick, the same design on both sides with a glossy finish, gold-colored string included",
            "Made for You, Step by Step: your preview via Etsy Messages, your approval, then we print your ornament and ship it to you",
            "Choose Your Style: Ruby, Sapphire, Emerald, White and Ivory, every style printed on both sides"] + \
           [f"{amp}, {s.upper()} STYLE: {ab} zodiac couple ornament in {s}, shown with sample names and date, hanging from a gold-colored string" for s in STILLER]


def satir(c):
    a, b, ayni = adlar(c)
    n1, n2 = ("First Name", "Second Name") if ayni else (f"Name for {a}", f"Name for {b}")
    r = dict(kod=c, baslik=baslik(c), etiketler=",".join(etiketler(c)), aciklama=aciklama(c),
             soru1=n1, soru2=n2, soru3="Your Date", talimat_isim="Letters A to Z only, printed in capitals",
             talimat_tarih="For example JUNE 14, 2025")
    for i, t in enumerate(alt_metinler(c), 1):
        r[f"alt_{i:02d}"] = t
    return r


def kapi(r):
    h = []
    tags = r["etiketler"].split(",")
    hepsi = "\n".join(str(v) for v in r.values())
    if TIRE.search(hepsi):
        h.append("uzun/orta tire")
    if YASAK.search(hepsi.replace("not metallic foil", "")):
        h.append(f"yasak soz {YASAK.findall(hepsi.replace('not metallic foil', ''))}")
    if len(r["baslik"]) > 140:
        h.append(f"baslik {len(r['baslik'])}")
    if len(tags) != 13 or len(set(tags)) != 13 or any(len(t) > 20 for t in tags) or any(not re.fullmatch(r"[a-z ]+", t) for t in tags):
        h.append(f"etiket {tags}")
    if AI not in r["aciklama"]:
        h.append("AI beyani yok")
    if "{" in hepsi or "}" in hepsi:
        h.append("yer tutucu kaldi")
    a, b, ayni = adlar(r["kod"])
    if any(f"{x} Gifts" not in r[k] for x in (a, b) for k in ("baslik", "aciklama")) or f"{a.lower()} gifts" not in tags or f"{b.lower()} gifts" not in tags:
        h.append("tek burc hediye kurali")
    if any(len(r[f"alt_{i:02d}"]) > 250 for i in range(1, 12)):
        h.append("alt metin > 250")
    if any(len(r[k]) > 45 for k in ("soru1", "soru2", "soru3")) or any(len(r[k]) > 120 for k in ("talimat_isim", "talimat_tarih")):
        h.append("kutu metni uzun")
    if any(n not in r["aciklama"] for n in (r["soru1"], r["soru2"])) or r["soru1"] not in r["alt_03"]:
        h.append("kutu / aciklama / alt_03 isim etiketi farkli")
    for s in STILLER:
        if s not in r["aciklama"]:
            h.append(f"stil {s} aciklamada yok")
    return h


def main():
    out = Path(__file__).resolve().parents[2] / "data" / "pod" / "ORNAMENT78_METIN.csv"
    rows = [satir(c) for c in CIFTLER]
    hata = {r["kod"]: kapi(r) for r in rows}
    hata = {k: v for k, v in hata.items() if v}
    assert len(rows) == 78
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALAN); w.writeheader(); w.writerows(rows)
    L = [len(r["baslik"]) for r in rows]
    print(f"78 satir -> {out} | baslik {min(L)}-{max(L)} kr | etiket 13 | kapi FAIL {len(hata)} {hata}")
    sys.exit(1 if hata else 0)


if __name__ == "__main__":
    main()
