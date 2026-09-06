# POD (Prodigi fiziksel poster) ilan sablonu (tag + aciklama, EN)

Karar: 6 Eyl 2026 (Mo). Bu dosya `scripts/etsy/pod_listing_update.py`
tarafindan OKUNUR: EN aciklama metni asagidaki isaretli bloktan alinir; tag
seti scriptte sabittir ve bu dokumanla aynidir. Yer tutucular: `{PAIR}`
("Aries & Leo"), `{S1}`/`{S2}` (bas harf buyuk), `{s1}`/`{s2}` (kucuk harf,
yalniz tag). Isaretlerin disindaki metin scripte girmez.

Baslik bu sablonda YOK: mevcut ilan basligina dokunulmaz.

## Tag seti (EN, 13, hepsi kucuk harf, <= 20 karakter)

| # | tag |
|---|---|
| 1 | zodiac wall art |
| 2 | {s1} {s2} print - 20'yi asarsa `{s1} print` (29 cift asar; raporlanir) |
| 3 | couple compatibility |
| 4 | astrology wall art |
| 5 | zodiac couple gift |
| 6 | anniversary gift |
| 7 | star sign poster |
| 8 | couples wall decor |
| 9 | astrology lover gift |
| 10 | minimalist wall art |
| 11 | fine art print |
| 12 | wedding gift couple |
| 13 | celestial home decor |

## Aciklama (EN)

<!-- EN_DESCRIPTION_BEGIN -->
{PAIR} zodiac wall art: a minimalist fine art print that unites both star signs in one clean, line-drawn compatibility symbol. Museum-quality giclée, made to order, shipped unframed.

✦ THE ARTWORK
One original emblem merges the {S1} and {S2} symbols: fine lines on a calm, solid ground. Designed in-house by AstroLove for couples who love astrology. A quiet, modern statement for a bedroom, living room, or gallery wall.

✦ MUSEUM-QUALITY MATERIALS
- Hahnemühle Photo Rag 308 gsm, 100% cotton fine art paper
- Acid- and lignin-free, ISO 9706 conform
- Archival pigment giclée printing at 300 dpi
- Matte, non-reflective surface
- Gold tones are printed as flat golden ink, not metallic foil

✦ 5 COLOR EDITIONS
Champagne Ivory · Pure White · Warm Parchment · Midnight Blue · Deep Black
Select your edition from the Color menu.

✦ 13 SIZES (select from the Size menu)
8x10 in (20.3×25.4 cm) · 4:5
A4 (21×29.7 cm)
11x14 in (27.9×35.6 cm) · 11:14
12x16 in (30.5×40.6 cm) · 3:4
A3 (29.7×42 cm)
12x18 in (30.5×45.7 cm) · 2:3
16x20 in (40.6×50.8 cm) · 4:5
16x24 in (40.6×61 cm) · 2:3
A2 (41.9×59.4 cm)
18x24 in (45.7×61 cm) · 3:4
20x30 in (50.8×76.2 cm) · 2:3
24x36 in (61×91.4 cm) · 2:3
30x40 in (76.2×101.6 cm) · 3:4
See the size guide in the photos to compare sizes on a wall.

✦ MADE TO ORDER & SHIPPING
Each print is made to order by our production partner, Prodigi. Processing time is shown in the shipping details above. 8x10 and A4 ship flat; all other sizes ship rolled in a sturdy tube. US orders are printed in the US; EU and UK orders are printed at our UK/EU lab for faster delivery.

✦ CARE
Handle by the edges. If a rolled print curls, lay it flat under a weight for 24–48 hours before framing. Frame behind glass, away from direct sunlight.

✦ PLEASE NOTE
- Frame not included: prints are sold unframed; frames in photos are for display only.
- Colors may vary slightly between your screen and the printed piece.
- Prefer an instant download? The same design is available as a digital edition in our shop.

✦ A GIFT THAT MEANS SOMETHING
A thoughtful anniversary, wedding, engagement, or Valentine's gift for a couple who share a love of astrology.

All AstroLove designs are original artwork created by our studio.
<!-- EN_DESCRIPTION_END -->

## Uygulama sirasi

1. `pod-listing-update` dry_run=true, listing_id bos -> magazadaki taslak
   (draft) ilanlar listelenir (WP durum dosyasindakiler haric); POD ilani secilir.
2. `pod-listing-update` dry_run=true, listing_id=<POD> -> mevcut/yeni fark tablosu.
3. Mo onayi -> dry_run=false: description + tags PATCH, geri okuma PASS/FAIL, CSV.
