# Printful urun taramasi: ornament tasarimi hangi urunlere uyarlanir (2 Kas 2026)

Kaynak: Printful API (yalniz okuma; GET + POST /v2/shipping-rates fiyat sorgusu). Siparis / urun / magaza kaydi olusturulmadi, Etsy yok.
Kosular: liste https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41465886451 (1142 GET),
kargo https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41469469402 (25 GET + 990 POST /v2/shipping-rates). Ham JSON: ham/.

## Kapsam ve yontem

- Kok kategori Home & living ve Accessories: 189 urun (v1 + v2 katalog). Giyim kokleri (Men's, Women's, Kids' clothing, Hats) ve
  giyim sayilan alt kategoriler (Shoes, Socks, Flip flops) haric. Katalogda ayri "takı / jewelry" kategorisi YOK (v1 /categories).
- Sinif kurali (varyant bazinda, urun en uygun varyantinin sinifini alir; olcu v2 placement_dimensions inc, yoksa printfile / dpi):
  - C: nakis (ad / teknik), sarma (ad: mug, tumbler, bottle, pint / wine / rocks / can-shaped glass, can cooler, candle; ya da en/boy > 2.2),
    ortada yarik (aciklama), kisa kenar < 2.0 inc (51 mm: isim 2.38 mm sigmaz).
  - A: yuvarlak kaniti (adda round / circle, aciklamada diameter, die-cut urun adi, varyant boyutu tek olcu) ve kare baski alani.
  - B: kalan kare / dikdortgen.
  - Kanit turu her satirda "gerekce" sutununda. Sekil API'de dogrudan alan olarak YOK; kanit ad / aciklama / boyut metninden.
- Sonuc: A 9, B 136, C 44 (TUM_LISTE.csv).
- Fiyat: v2 /prices (USD) worldwide (WW) ve north_america (NA); v1 variants.price ayrica. En ucuz = katalog varyant listesindeki varyantlar
  (fiyat yanitinda listede olmayan ek kimlikler 11 urunde var; disarida birakildi).
- Uretim yeri: TUM_LISTE'de v1 availability_status bolgeleri (URETIM ULKESI DEGIL; onceki olcumde 881 v1 "US" ama cikis LV).
  Kesin cikis ulkesi yalniz secilen 25'te kargo yanitindan (shipments.departure_country).
- Kargo: urun basina en ucuz (v2 WW) 6 varyant x US, DE, GB, CA, AU x 1 ve 2 adet; en ucuz yontem. Ek urun = 2 adet - 1 adet ucreti (ayni yontem).
  Ornek adres: merkez posta kodu. Gumruk: customs_fees_possible (anlami Printful dokumaninda bulunamadi; bkz. ornament raporu).

## Secilen 25 (SECILEN25.csv: tum varyantlar)

| urun | sinif | en ucuz USD WW / NA | kargo ilk / ek USD: US | DE | GB | CA | AU | cikis (US / DE / GB) | gumruk (DE GB CA) | kisit | uyarlama |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 656 Die-Cut Magnets | A | 3.39 / 3.39 | 4.69 / 0.99 | 8.29 / 0.99 | 11.39 / 0.99 | 8.29 / 0.99 | 10.39 / 2.49 | US / US / US | CA,DE,GB | - | daire 76 mm, oldugu gibi oturur; delik kalkar; isim harfi yaklasik 2.6 mm (hesap) |
| 660 Set of Pin Buttons | A | 7.73 / 7.73 | 4.69 / 0.99 | 8.29 / 0.99 | 10.39 / 0.99 | 7.79 / 0.99 | 7.79 / 2.49 | US / US / US | CA,DE,GB | - | daire 67 mm, oldugu gibi oturur; delik kalkar; isim harfi yaklasik 2.3 mm (hesap) |
| 793 Acrylic Ornaments | A | 7.8 / 7.8 | 5.49 / 0.80 | gonderilmez | gonderilmez | gonderilmez | gonderilmez | US / - / - | - | yalniz ABD | daire 84 mm, oldugu gibi oturur; delik / asma noktasi urune gore yeniden olculmeli; isim harfi yaklasik 2.9 mm (hesap) |
| 881 Ceramic Ornament | A | 6.15 / 6.15 | 5.49 / 0.80 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | LV / LV / LV | CA,DE,GB | - | daire 81 mm, oldugu gibi oturur; delik / asma noktasi urune gore yeniden olculmeli; isim harfi yaklasik 2.8 mm (hesap) |
| 900 Ceramic Ornaments, 2-Side Print | A | 7.73 / 7.73 | 5.89 / 0.70 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | LV / LV / LV | CA,DE,GB | - | daire 81 mm, oldugu gibi oturur; delik / asma noktasi urune gore yeniden olculmeli; isim harfi yaklasik 2.8 mm (hesap) |
| 901 Metal Christmas Ornament | A | 4.61 / 4.61 | 5.89 / 0.70 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | LV / LV / LV | CA,DE,GB | - | daire 91 mm, oldugu gibi oturur; delik / asma noktasi urune gore yeniden olculmeli; isim harfi yaklasik 3.1 mm (hesap) |
| 957 Die-Cut Stickers | A | 3.86 / 3.86 | 5.19 / 0.07 | 10.89 / 0.55 | 10.89 / 0.55 | 9.69 / 0.49 | 10.89 / 0.55 | LV / LV / LV | CA,DE,GB | - | daire 51 mm, oldugu gibi oturur; delik kalkar; isim harfi yaklasik 1.7 mm (hesap); 2 mm alti, yazi kucuk kalir (ornament duzeni 70 mm icin) |
| 1399 Round Mouse Pad | A | 9.31 / 9.31 | 4.69 / 2.00 | 4.99 / 1.45 | 4.59 / 1.50 | 7.29 / 1.95 | 7.99 / 1.40 | US / LV / LV | CA,GB | - | daire 222 mm, oldugu gibi oturur; delik kalkar; isim harfi yaklasik 7.6 mm (hesap) |
| 1729 Crystal Glass Ornament | A | 5.59 / 5.59 | 5.89 / 0.70 | gonderilmez | gonderilmez | gonderilmez | gonderilmez | LV / - / - | - | ABD disi:  Unavailable variant id used | daire 76 mm, oldugu gibi oturur; delik / asma noktasi urune gore yeniden olculmeli; isim harfi yaklasik 2.6 mm (hesap) |
| 611 Cork-Back Coaster | B | 5.55 / 5.55 | 4.09 / 0.75 | 4.29 / 1.15 | 4.29 / 0.90 | 6.89 / 1.10 | 8.39 / 1.50 | US / LV / LV | CA,GB | - | daire 90 mm ortada, zemin koselere uzar; isim harfi yaklasik 3.1 mm (hesap) |
| 1470 Wall Clock | B | 29.57 / 29.57 | 9.29 / 5.99 | 23.09 / 8.79 | 19.39 / 8.79 | 16.89 / 7.69 | 19.39 / 8.79 | LV / LV / LV | CA,DE,GB | - | daire 229 mm ortada, zemin koselere uzar; isim harfi yaklasik 7.8 mm (hesap) |
| 3 Canvas (in) | B | 14.5 / 13.72 | 6.79 / 6.49 | 6.79 / 6.49 | 6.79 / 6.49 | 11.49 / 10.99 | 12.49 / 11.99 | US / ES / GB | - | - | daire 297 mm ortada, zemin koselere uzar; isim harfi yaklasik 10.1 mm (hesap) |
| 2 Enhanced Matte Paper Framed Poster | B | 21.25 / 20.76 | 10.89 / 4.50 | 7.79 / 4.90 | 7.29 / 4.75 | 11.79 / 6.25 | 9.59 / 4.10 | US / LV,US / GB,US | CA,DE,GB | - | daire 229 mm ortada, zemin koselere uzar; isim harfi yaklasik 7.8 mm (hesap) |
| 1 Enhanced Matte Paper Poster (in) | B | 6.5 / 6.75 | 4.99 / 0.40 | 5.79 / 0.30 | 5.79 / 0.30 | 5.69 / 0.30 | 6.69 / 0.30 | US / LV / GB,LV | GB | - | daire 267 mm ortada, zemin uzun kenara uzar; isim harfi yaklasik 9.1 mm (hesap) |
| 588 Glossy Metal Print (in) | B | 39.48 / 39.48 | 12.99 / 4.50 | gonderilmez | gonderilmez | gonderilmez | gonderilmez | US / - / - | - | yalniz ABD | daire 263 mm ortada, zemin uzun kenara uzar; isim harfi yaklasik 9.0 mm (hesap) |
| 906 Jigsaw Puzzle with Tin | B | 18.0 / 18.0 | 8.29 / 2.50 | 22.89 / 8.00 | 22.89 / 8.00 | 17.69 / 7.50 | 22.89 / 8.00 | LV / LV / LV | CA,DE,GB | - | daire 179 mm ortada, zemin uzun kenara uzar; isim harfi yaklasik 6.1 mm (hesap) |
| 83 All-Over Print Basic Pillow | B | 13.5 / 13.57 | 10.89 / 4.50 | 13.79 / 5.75 | 11.49 / 4.95 | 12.69 / 6.75 | 37.59 / 7.30 | US / LV / LV | CA,GB | - | daire 343 mm ortada, zemin koselere uzar; isim harfi yaklasik 11.7 mm (hesap) |
| 395 Throw Blanket | B | 24.62 / 24.62 | 8.29 / 2.50 | 7.29 / 2.40 | 7.29 / 2.40 | 9.79 / 2.35 | 12.49 / 2.25 | US / LV,US / LV,US | CA,DE,GB | - | daire 1429 mm ortada, zemin uzun kenara uzar; isim harfi yaklasik 48.8 mm (hesap) |
| 518 Mouse Pad | B | 9.5 / 9.31 | 4.69 / 2.00 | 4.99 / 1.45 | 4.59 / 1.50 | 7.29 / 1.95 | 7.99 / 1.40 | US / LV / LV | CA,GB | - | daire 171 mm ortada, zemin uzun kenara uzar; isim harfi yaklasik 5.9 mm (hesap) |
| 867 Hardcover Journal Matte | B | 9.77 / 9.77 | 5.69 / 3.25 | 10.39 / 3.50 | 12.49 / 3.95 | 10.39 / 3.49 | 15.09 / 7.99 | LV / LV / LV | CA,DE,GB | - | daire 217 mm ortada, zemin uzun kenara uzar; isim harfi yaklasik 7.4 mm (hesap) |
| 568 Greeting Card | B | 2.55 / 2.55 | 4.49 / 0.05 | 4.29 / 0.10 | 4.29 / 0.10 | 5.19 / 0.10 | 5.89 / 0.10 | LV,US / LV / LV | CA,GB | - | daire 94 mm ortada, zemin uzun kenara uzar; isim harfi yaklasik 3.2 mm (hesap) |
| 1553 Cotton Color Tote Bag | Westford M | B | 10.25 / 10.18 | 4.69 / 2.00 | 4.99 / 1.45 | 4.59 / 1.50 | 7.29 / 1.95 | 7.99 / 1.40 | US / LV / LV | CA,GB | - | daire 223 mm ortada, zemin koselere uzar; isim harfi yaklasik 7.6 mm (hesap) |
| 634 Wooden Ornaments | B | 10.25 / 8.37 | 5.19 / 1.00 | 7.29 / 3.00 | 2.59 / 0.90 | 9.29 / 0.90 | 8.39 / 1.90 | US / IT / GB | CA | - | daire 89 mm ortada, zemin uzun kenara uzar; isim harfi yaklasik 3.0 mm (hesap) |
| 358 Kiss-Cut Stickers | B | 2.75 / 2.34 | 4.49 / 0.05 | 4.29 / 0.07 | 4.29 / 0.07 | 5.19 / 0.10 | 5.89 / 0.10 | US / LV / GB,LV | CA,GB | - | daire 69 mm ortada, zemin koselere uzar; isim harfi yaklasik 2.3 mm (hesap) |
| 1664 Glass Ornaments | B | 19.0 / 19.0 | 5.89 / 0.70 | gonderilmez | gonderilmez | gonderilmez | gonderilmez | LV / - / - | - | ABD disi:  Unavailable variant id used | daire 86 mm ortada, zemin koselere uzar; isim harfi yaklasik 2.9 mm (hesap) |

Secim gerekcesi: A sinifi (yuvarlak baski alani): hepsi alindi; B sinifi: Etsy hediye kategorisinde yaygin urun turu (DEGERLENDIRME; olculmus Etsy verisi yok).

- Kargo hucreleri: sorgulanan varyantlar icinde en ucuz ilk urun / ek urun (USD, Printful API). Tum varyant ve gun bilgisi SECILEN25.csv.
- "gonderilmez": API 400 (ornek "ships to United States only", "Unavailable variant id used").
- Uyarlama notundaki isim harfi boyu HESAPTIR (ornament duzeninin esit olcegi); urun basina tasarim yapilmadi.

## A sinifi (tumu)

- 656 Die-Cut Magnets: yuvarlak (die-cut: kesim tasarim kenarini izler (urun adi)); 3x3 inc (v2 placement_dimensions) (+2 varyant ayni sinif)
- 660 Set of Pin Buttons: yuvarlak (varyant boyutu tek olcu (cap)); 2.62x2.62 inc (v2 placement_dimensions) (+1 varyant ayni sinif)
- 793 Acrylic Ornaments: yuvarlak (adda round/circle); 3.31x3.31 inc (v2 placement_dimensions)
- 881 Ceramic Ornament: yuvarlak (adda round/circle); 3.18x3.18 inc (v2 placement_dimensions) (+2 varyant ayni sinif)
- 900 Ceramic Ornaments, 2-Side Print: yuvarlak (adda round/circle); 3.18x3.18 inc (v2 placement_dimensions) (+2 varyant ayni sinif)
- 901 Metal Christmas Ornament: yuvarlak (aciklamada diameter); 3.58x3.61 inc (v2 placement_dimensions) (+1 varyant ayni sinif)
- 957 Die-Cut Stickers: yuvarlak (die-cut: kesim tasarim kenarini izler (urun adi)); 2x2 inc (v2 placement_dimensions) (+4 varyant ayni sinif)
- 1399 Round Mouse Pad: yuvarlak (adda round/circle); 8.75x8.75 inc (v2 placement_dimensions)
- 1729 Crystal Glass Ornament: yuvarlak (adda round/circle); 3x3 inc (v2 placement_dimensions) (+2 varyant ayni sinif)

## C sinifi gerekce dagilimi

- sarma / uzun bant baski: 36
- nakis: 5
- kucuk: 1
- varyant / baski olcusu API vermedi: 1
- ortada yarik: 1
