# Pinterest pin metin sablonu V2 (KARAR, 2 Eylul 2026)

Pin CSV'lerindeki metin `scripts/pinterest/build_week_v2.py` icinde bu
sablondan uretilir. Eski GUN_01..30 CSV metinleri KULLANILMAZ (yalniz
cift -> Etsy listing eslesmesi oradan `TEMP/PIN_LISTING_MAP.csv`'ye alindi).

Degiskenler: `<Sign1>`, `<Sign2>` (Title Case, or. Capricorn), `<Edition>`
(Title Case, or. Warm Parchment), `<sign1> <sign2>` (kucuk harf).

## Title (<= 100 karakter)

```
<Sign1> & <Sign2> Zodiac Wall Art — Couple Compatibility Print, <Edition>
```

## Description (~400 karakter, EN, hashtag YOK)

```
<Sign1> & <Sign2> united in one original zodiac pair symbol — AstroLove couple
wall art in the <Edition> Edition. A meaningful anniversary or Valentine's gift
for astrology lovers, and a quiet statement piece for a shared bedroom or living
room. Instant digital download, printable in 5 sizes. Explore all 78 zodiac
pairs in 5 editions in the AstroLove shop.
```

Icerik zorunluluklari: birlesik burc sembolu, AstroLove cift duvar sanati,
edisyon adi, yildonumu / Sevgililer hediyesi (astroloji sevenler), ortak yatak
odasi / salon, aninda dijital indirme 5 boyutta basilabilir, magazada 78 cift x
5 edisyon.

## Keywords

```
zodiac wall art, couple gift, astrology decor, <sign1> <sign2>, compatibility art, celestial print
```

## Diger kolonlar

- Pinterest board: `Zodiac Compatibility Wall Art` (tek pano)
- Media URL: `TEMP/PIN_UPLOAD_STATE_V2.csv` webContentLink (PIN_MEDIA_V2)
- Link: `TEMP/PIN_LISTING_MAP.csv` (pair, edition -> listing_id)
- Publish date: gunde 12 pin, UTC 08:00-19:00, 60 dk arayla; 390 pin = 33 gun;
  haftalik dosya 84 pin (son hafta 54)
- Sira: 5 edisyon donusumlu, cift ofsetli (slot i: edisyon = i mod 5,
  cift = (i div 5 + 16 x (i mod 5)) mod 78, ciftler alfabetik)
