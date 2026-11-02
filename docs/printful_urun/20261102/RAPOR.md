# Printful urun taramasi: ornament tasarimi hangi urunlere uyarlanir (2 Kas 2026)

Kaynak: Printful API (yalniz okuma; GET + POST /v2/shipping-rates fiyat sorgusu). Siparis / urun / magaza kaydi olusturulmadi, Etsy yok.
Kosular: liste https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41465886451 (1142 GET),
kargo https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41469469402 (25 GET + 990 POST /v2/shipping-rates). Ham JSON: ham/.
TUM_LISTE / SECILEN25 / RAPOR bu ham veriden YEREL yeniden uretildi (API yok; betik scripts/printful/urun_katalog.py tablo / secilen).
Sinif sayilari bu yuzden KOSU_LOG_1 ("A 3, B 144, C 42", ilk kural) ile farkli: kurallar bagimsiz inceleme bulgulariyla duzeltildi.
Ek kosu (urun3, Serdar onayi, tek seferlik): https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41476618387
(64 GET + 30 POST /v2/shipping-rates; log KOSU_LOG_3.txt).

## Ek kosu (urun3) sonucu

- v2 /prices kalan sayfalari okundu (50 GET). Fiyat kapsami artik tam; yalniz 938 ve 1716 fiyat yanitinda 0/1 (API fiyat vermiyor).
  Degisen en ucuz WW: 2 21.25 -> 20.76, 172 24.25 -> 23.93, 614 32.25 -> 31.95, 1708 48.48 -> 32.95 (NA de 32.95).
- Kargo: en ucuz 6 varyanti degisen secilen urunler 1 ve 2; yeni varyantlar icin 30 POST /v2/shipping-rates.
- 534 Jigsaw Puzzle eklendi (v1 / v2 kategori Collections > New products): B, en ucuz 15.25 USD WW.
- 900 Ceramic Ornament 2-Side baski sablonu: printfile 845 = 954 x 954 px, 300 dpi (80.8 mm). v2 mockup sablonu (Circle.png)
  900 ve 881 icin bayt bayt AYNI (sha256 5fe4a06f...). Sablonda: kesikli guvenli daire r 380 px (64.4 mm), duz kenar r 475 px
  (baski alani kenari). Urun kenari (70 ya da 76 mm) sablonda CIZILI DEGIL. Aciklama: 900 "Circle-shaped diameter 2.99 inc (7.6 cm)",
  881 "2.76 inc (7 cm)". v1 sablon gorselleri (900: 907652, 881: 905495) farkli URL, indirilmedi (yalniz "circle" adli URL alindi).
  v2 / v1 sizes: 900 icin olcu tablosu yok (400 / bos).
- Uretim / cikis ulkesi yalniz secilen 25 icin (kargo yanitindan). Kalan urunlerde yok; v1 bolgeleri uretim ulkesi DEGIL.
- Malzeme: v1 material alani cogu varyantta bos (API); malzeme_v1 sutunu dolu olanlar.

## Kapsam ve yontem

- Kok kategori Home & living ve Accessories: 190 urun (v1 + v2 katalog). Giyim kokleri (Men's, Women's, Kids' clothing, Hats) ve
  giyim sayilan alt kategoriler (Shoes, Socks, Flip flops) haric. Katalogda ayri "takı / jewelry" kategorisi YOK (v1 /categories).
- Sinif kurali (varyant bazinda, urun en uygun varyantinin sinifini alir; olcu v2 placement_dimensions inc, yoksa printfile / dpi):
  - C: giyilebilir aksesuar (gaiter, bandana, scrunchie, headband, pet hoodie / sweater), nakis (ad / v2 ya da v1 teknik),
    sarma (ad: mug, tumbler, bottle, pint / wine / rocks / can-shaped glass; ya da en/boy > 2.2), varyant kesim sekli daire degil
    (heart, star, bell, snowflake, stocking, tree, paw, scalloped), ortada yarik (aciklama),
    kisa kenar < 2.0 inc (esik DEGERLENDIRME; 2.0 inc = 51 mm dairede isim harfi 2.39 x 51 / 70 = 1.74 mm, hesap).
  - A: yuvarlak kaniti (varyant / urun adinda round / circle, aciklamada diameter, die-cut urun adi, varyant boyutu tek olcu) ve kare baski alani.
    Kesim sekli daire olmayan varyant kanit almaz (aciklamadaki diameter o varyanta uygulanmaz).
  - Fiziksel boyut: varyant boyutu tek olcu ise o (or. 660 pin 1.25 / 2.25 inc; baski alani 2.62 inc kenar sarma dahil).
  - B: kalan kare / dikdortgen.
  - Kanit turu her satirda "gerekce" sutununda. Sekil API'de dogrudan alan olarak YOK; kanit ad / aciklama / boyut metninden.
- Sonuc: A 9, B 136, C 45 (TUM_LISTE.csv).
- Fiyat: v2 /prices (USD) worldwide (WW) ve north_america (NA); v1 variants.price ayrica. En ucuz = katalog varyant listesindeki varyantlar
  (fiyat yanitinda listede olmayan ek kimlikler 11 urunde var; disarida birakildi).
- Uretim yeri: TUM_LISTE'de v1 availability_status bolgeleri (URETIM ULKESI DEGIL; onceki olcumde 881 v1 "US" ama cikis LV).
  Kesin cikis ulkesi yalniz secilen 25'te kargo yanitindan (shipments.departure_country).
- Kargo: urun basina en ucuz (v2 WW) 6 varyant x US, DE, GB, CA, AU x 1 ve 2 adet; en ucuz yontem. Ek urun = 2 adet - 1 adet ucreti (ayni yontem).
  Ornek adres: merkez posta kodu. Gumruk: customs_fees_possible (anlami Printful dokumaninda bulunamadi; bkz. ornament raporu).
  Kargo hucresi: ilk ucreti en dusuk varyant ve AYNI varyantin ek ucreti.
- Satis kisiti (TUM_LISTE satis_kisiti): aciklamada "US only" (743, 786, 793, 794, 805) ve v2 worldwide urun 404 (635, 716, 743;
  bunlarda WW fiyat yaniti yine geldi, yazildi). uygunluk_v2 yalniz worldwide sorgusu.

## Secilen 25 (SECILEN25.csv: tum varyantlar)

| urun | sinif | en ucuz USD WW / NA (fiyat kapsami) | temsil varyant USD WW | kargo ilk / ek USD: US | DE | GB | CA | AU | cikis US / DE / GB / CA / AU | gumruk olasi | kisit | uyarlama |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 656 Die-Cut Magnets | A | 3.39 / 3.39 (5/5) | 3.39 | 4.69 / 0.99 | 8.29 / 0.99 | 11.39 / 0.99 | 8.29 / 0.99 | 10.39 / 2.49 | US / US / US / US / US | DE,GB,CA | - | varyant 16366: daire 76 mm (baski alani (tasma payi dahil olabilir)), oldugu gibi oturur; delik kalkar; isim harfi yaklasik 2.6 mm (hesap) |
| 660 Set of Pin Buttons (paket fiyati: 1.25″, 2.25″) | A | 7.73 / 7.73 (2/2) | 8.67 | 4.69 / 0.99 | 8.29 / 0.99 | 10.39 / 0.99 | 7.79 / 0.99 | 7.79 / 2.49 | US / US / US / US / US | DE,GB,CA | - | varyant 16412: daire 57 mm (varyant boyutu), oldugu gibi oturur; delik kalkar; isim harfi yaklasik 2.0 mm (hesap); 2 mm alti, yazi kucuk kalir (ornament duzeni 70 mm icin) |
| 793 Acrylic Ornaments | A | 7.8 / 7.8 (2/2) | 7.8 | 5.49 / 0.80 | gonderilmez | gonderilmez | gonderilmez | gonderilmez | US / - / - / - / - | - | aciklama: yalniz ABD, kargo: yalniz ABD | varyant 20250: daire 76 mm (aciklama "diameter 3″"), oldugu gibi oturur; delik / asma noktasi urune gore yeniden olculmeli; isim harfi yaklasik 2.6 mm (hesap) |
| 881 Ceramic Ornament | A | 6.15 / 6.15 (4/4) | 6.34 | 5.49 / 0.80 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | LV / LV / LV / LV / LV | DE,GB,CA | - | varyant 22782: daire 70 mm (aciklama "diameter: 2.76″"), oldugu gibi oturur; delik / asma noktasi urune gore yeniden olculmeli; isim harfi yaklasik 2.4 mm (hesap) |
| 900 Ceramic Ornaments, 2-Side Print | A | 7.73 / 7.73 (4/4) | 7.73 | 5.89 / 0.70 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | LV / LV / LV / LV / LV | DE,GB,CA | - | varyant 23133: daire 76 mm (aciklama "diameter: 2.99″"), oldugu gibi oturur; delik / asma noktasi urune gore yeniden olculmeli; isim harfi yaklasik 2.6 mm (hesap) |
| 901 Metal Christmas Ornament | A | 4.61 / 4.61 (4/4) | 4.61 | 5.89 / 0.70 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | 9.89 / 1.99 | LV / LV / LV / LV / LV | DE,GB,CA | - | varyant 23136: daire 89 mm (aciklama "diameter: 3.5″"), oldugu gibi oturur; delik / asma noktasi urune gore yeniden olculmeli; isim harfi yaklasik 3.0 mm (hesap) |
| 957 Die-Cut Stickers | A | 3.86 / 3.86 (5/5) | 3.86 | 5.19 / 0.07 | 10.89 / 0.55 | 10.89 / 0.55 | 9.69 / 0.49 | 10.89 / 0.55 | LV / LV / LV / LV / LV | DE,GB,CA | - | varyant 24964: daire 51 mm (baski alani (tasma payi dahil olabilir)), oldugu gibi oturur; delik kalkar; isim harfi yaklasik 1.7 mm (hesap); 2 mm alti, yazi kucuk kalir (ornament duzeni 70 mm icin) |
| 1399 Round Mouse Pad | A | 9.31 / 9.31 (1/1) | 9.31 | 4.69 / 2.00 | 4.99 / 1.45 | 4.59 / 1.50 | 7.29 / 1.95 | 7.99 / 1.40 | US / LV / LV / US / US | GB,CA | - | varyant 25786: daire 203 mm (aciklama "Diameter: 8″"), oldugu gibi oturur; delik kalkar; isim harfi yaklasik 6.9 mm (hesap) |
| 1729 Crystal Glass Ornament | A | 5.59 / 5.59 (6/6) | 5.59 | 5.89 / 0.70 | gonderilmez | gonderilmez | gonderilmez | gonderilmez | LV / - / - / - / - | - | kargo ABD disi 400: Unavailable variant id used | varyant 54337: daire 76 mm (baski alani (tasma payi dahil olabilir)), oldugu gibi oturur; delik / asma noktasi urune gore yeniden olculmeli; isim harfi yaklasik 2.6 mm (hesap) |
| 611 Cork-Back Coaster | B | 5.55 / 5.55 (1/1) | 5.55 | 4.09 / 0.75 | 4.29 / 1.15 | 4.29 / 0.90 | 6.89 / 1.10 | 8.39 / 1.50 | US / LV / LV / US / US | GB,CA | - | varyant 15662: daire 90 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin koselere uzar; isim harfi yaklasik 3.1 mm (hesap) |
| 1470 Wall Clock | B | 29.57 / 29.57 (6/6) | 29.57 | 9.29 / 5.99 | 23.09 / 8.79 | 19.39 / 8.79 | 16.89 / 7.69 | 19.39 / 8.79 | LV / LV / LV / LV / LV | DE,GB,CA | - | varyant 46082: daire 229 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin koselere uzar; isim harfi yaklasik 7.8 mm (hesap) |
| 3 Canvas (in) | B | 14.5 / 13.72 (46/46) | 14.5 | 6.79 / 6.49 | 6.79 / 6.49 | 6.79 / 6.49 | 11.49 / 10.99 | 12.49 / 11.99 | US / ES / GB / CA / AU | - | - | varyant 19291: daire 206 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin koselere uzar; isim harfi yaklasik 7.0 mm (hesap) |
| 2 Enhanced Matte Paper Framed Poster | B | 20.76 / 20.76 (39/39) | 20.76 | 10.89 / 4.50 | 7.79 / 4.90 | 7.29 / 4.75 | 11.79 / 6.25 | 9.59 / 4.10 | US / CA,LV,US / CA,GB,US / CA,LV,US / AU | DE,GB,CA | - | varyant 15021: daire 183 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin uzun kenara uzar; isim harfi yaklasik 6.2 mm (hesap) |
| 1 Enhanced Matte Paper Poster (in) | B | 6.5 / 6.75 (37/37) | 6.5 | 4.99 / 0.40 | 5.79 / 0.30 | 5.79 / 0.30 | 5.69 / 0.30 | 6.69 / 0.30 | CA,US / LV / GB,LV / CA / AU,CA,US | US,GB | - | varyant 16364: daire 114 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin uzun kenara uzar; isim harfi yaklasik 3.9 mm (hesap) |
| 588 Glossy Metal Print (in) | B | 39.48 / 39.48 (6/6) | 39.48 | 12.99 / 4.50 | gonderilmez | gonderilmez | gonderilmez | gonderilmez | US / - / - / - / - | - | kargo: yalniz ABD | varyant 15134: daire 189 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin uzun kenara uzar; isim harfi yaklasik 6.4 mm (hesap) |
| 906 Jigsaw Puzzle with Tin | B | 18.0 / 18.0 (6/6) | 18.0 | 8.29 / 2.50 | 22.89 / 8.00 | 22.89 / 8.00 | 17.69 / 7.50 | 22.89 / 8.00 | LV / LV / LV / LV / LV | DE,GB,CA | - | varyant 23245: daire 179 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin uzun kenara uzar; isim harfi yaklasik 6.1 mm (hesap) |
| 83 All-Over Print Basic Pillow | B | 13.5 / 13.57 (5/5) | 13.5 | 10.89 / 4.50 | 13.79 / 5.75 | 11.49 / 4.95 | 12.69 / 6.75 | 37.59 / 7.30 | US / LV / LV / US / US | GB,CA | - | varyant 49853: daire 343 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin koselere uzar; isim harfi yaklasik 11.7 mm (hesap) |
| 395 Throw Blanket | B | 24.62 / 24.62 (3/3) | 24.62 | 8.29 / 2.50 | 7.29 / 2.40 | 7.29 / 2.40 | 9.79 / 2.35 | 12.49 / 2.25 | US / LV,US / LV,US / US / US | DE,GB,CA | - | varyant 22609: daire 754 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin uzun kenara uzar; isim harfi yaklasik 25.8 mm (hesap) |
| 518 Mouse Pad | B | 9.5 / 9.31 (1/1) | 9.5 | 4.69 / 2.00 | 4.99 / 1.45 | 4.59 / 1.50 | 7.29 / 1.95 | 7.99 / 1.40 | US / LV / LV / US / US | GB,CA | - | varyant 13097: daire 171 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin uzun kenara uzar; isim harfi yaklasik 5.9 mm (hesap) |
| 867 Hardcover Journal Matte | B | 9.77 / 9.77 (1/1) | 9.77 | 5.69 / 3.25 | 10.39 / 3.50 | 12.49 / 3.95 | 10.39 / 3.49 | 15.09 / 7.99 | LV / LV / LV / LV / LV | DE,GB,CA | - | varyant 22658: daire 217 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin uzun kenara uzar; isim harfi yaklasik 7.4 mm (hesap) |
| 568 Greeting Card | B | 2.55 / 2.55 (3/3) | 2.55 | 4.49 / 0.05 | 4.29 / 0.10 | 4.29 / 0.10 | 5.19 / 0.10 | 5.89 / 0.10 | LV,US / LV / LV / LV / LV | US,GB,CA | - | varyant 14457: daire 94 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin uzun kenara uzar; isim harfi yaklasik 3.2 mm (hesap) |
| 1553 Cotton Color Tote Bag | Westford M | B | 10.25 / 10.18 (12/12) | 10.25 | 4.69 / 2.00 | 4.99 / 1.45 | 4.59 / 1.50 | 7.29 / 1.95 | 7.99 / 1.40 | US / LV / LV / LV / LV | GB,CA | - | varyant 49313: daire 223 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin koselere uzar; isim harfi yaklasik 7.6 mm (hesap) |
| 634 Wooden Ornaments | B | 10.25 / 8.37 (6/6) | 10.25 | 5.19 / 1.00 | 7.29 / 3.00 | 2.59 / 0.90 | 9.29 / 0.90 | 8.39 / 1.90 | US / IT / GB / US / AU | CA | - | varyant 16091: daire 89 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin uzun kenara uzar; isim harfi yaklasik 3.0 mm (hesap) |
| 358 Kiss-Cut Stickers | B | 2.75 / 2.34 (10/10) | 2.75 | 4.49 / 0.05 | 4.29 / 0.07 | 4.29 / 0.07 | 5.19 / 0.10 | 5.89 / 0.10 | US / LV / GB,LV / CA,US / AU,LV | GB,CA | - | varyant 10163: daire 69 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin koselere uzar; isim harfi yaklasik 2.3 mm (hesap) |
| 1664 Glass Ornaments (paket fiyati: 1 Piece, 5 Pieces) | B | 19.0 / 19.0 (2/2) | 19.0 | 5.89 / 0.70 | gonderilmez | gonderilmez | gonderilmez | gonderilmez | LV / - / - / - / - | - | kargo ABD disi 400: Unavailable variant id used | varyant 52913: daire 86 mm ortada (baski alani (tasma payi dahil olabilir) %90), zemin koselere uzar; isim harfi yaklasik 2.9 mm (hesap) |

Secim gerekcesi: A sinifi (yuvarlak baski alani): hepsi alindi; B sinifi: Etsy hediye kategorisinde yaygin urun turu (DEGERLENDIRME; olculmus Etsy verisi yok).

- Kargo hucreleri: sorgulanan varyantlar icinde ilk ucreti en dusuk varyantin ilk / ek ucreti (USD, Printful API). Tum varyant ve gun bilgisi SECILEN25.csv.
- Fiyat kapsami: okunan / toplam varyant (v2 prices paging). Kapsam eksikse en ucuz WW degeri eksik okumadan.
- B secimi (16 urun) DEGERLENDIRMEDIR; urun basina olculmus Etsy talep verisi yok.
- "gonderilmez": API 400 (ornek "ships to United States only", "Unavailable variant id used").
- Uyarlama notundaki isim harfi boyu HESAPTIR (ornament duzeninin esit olcegi); urun basina tasarim yapilmadi.

## A sinifi (tumu)

- 656 Die-Cut Magnets: [temsil varyant 16366, en ucuz uygun] yuvarlak (die-cut: kesim tasarim kenarini izler (urun adi)); 3x3 inc (v2 placement_dimensions); fiziksel kisa 3 inc (+2 varyant ayni sinif)
- 660 Set of Pin Buttons: [temsil varyant 16412, en ucuz uygun] yuvarlak (varyant boyutu tek olcu (cap)); 2.62x2.62 inc (varyant boyutu 2.25 inc fiziksel (baski alani 2.62x2.62 sarma / tasma dahil)); fiziksel kisa 2.25 inc
- 793 Acrylic Ornaments: [temsil varyant 20250, en ucuz uygun] yuvarlak (adda round/circle); 3.31x3.31 inc (v2 placement_dimensions); fiziksel kisa 3.31 inc
- 881 Ceramic Ornament: [temsil varyant 22782, en ucuz uygun] yuvarlak (adda round/circle); 3.18x3.18 inc (v2 placement_dimensions); fiziksel kisa 3.18 inc
- 900 Ceramic Ornaments, 2-Side Print: [temsil varyant 23133, en ucuz uygun] yuvarlak (adda round/circle); 3.18x3.18 inc (v2 placement_dimensions); fiziksel kisa 3.18 inc
- 901 Metal Christmas Ornament: [temsil varyant 23136, en ucuz uygun] yuvarlak (adda round/circle); 3.75x3.75 inc (v2 placement_dimensions); fiziksel kisa 3.75 inc
- 957 Die-Cut Stickers: [temsil varyant 24964, en ucuz uygun] yuvarlak (die-cut: kesim tasarim kenarini izler (urun adi)); 2x2 inc (v2 placement_dimensions); fiziksel kisa 2 inc (+4 varyant ayni sinif)
- 1399 Round Mouse Pad: [temsil varyant 25786, en ucuz uygun] yuvarlak (adda round/circle); 8.75x8.75 inc (v2 placement_dimensions); fiziksel kisa 8.75 inc
- 1729 Crystal Glass Ornament: [temsil varyant 54337, en ucuz uygun] yuvarlak (adda round/circle); 3x3 inc (v2 placement_dimensions); fiziksel kisa 3 inc (+2 varyant ayni sinif)

## C sinifi gerekce dagilimi

- [temsil varyant 4830, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 8894, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 9286, en ucuz uygun] nakis: 1
- [temsil varyant 9323, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 9986, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 10798, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 10876, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 17358, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 11189, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 11414, en ucuz uygun] giyilebilir aksesuar: 1
- [temsil varyant 15569, en ucuz uygun] nakis: 1
- [temsil varyant 13350, en ucuz uygun] giyilebilir aksesuar: 1
- [temsil varyant 13444, en ucuz uygun] nakis: 1
- [temsil varyant 13802, en ucuz uygun] giyilebilir aksesuar: 1
- [temsil varyant 15004, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 15524, en ucuz uygun] kucuk: 1
- [temsil varyant 16031, en ucuz uygun] giyilebilir aksesuar: 1
- [temsil varyant 16046, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 16271, en ucuz uygun] nakis: 1
- [temsil varyant 16359, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 16440, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 16714, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 16785, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 17354, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 17353, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 17485, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 19107, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 19126, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 19186, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 19189, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 19192, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 19793, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 20175, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 21352, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 22232, en ucuz uygun] nakis: 1
- [temsil varyant 22016, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 23141, en ucuz uygun] giyilebilir aksesuar: 1
- [temsil varyant 23470, en ucuz uygun] sarma / uzun bant baski: 1
- varyant / baski olcusu API vermedi: 1
- [temsil varyant 23880, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 24565, en ucuz uygun] giyilebilir aksesuar: 1
- [temsil varyant 44158, en ucuz uygun] ortada yarik: 1
- [temsil varyant 44241, en ucuz uygun] nakis: 1
- [temsil varyant 53100, en ucuz uygun] sarma / uzun bant baski: 1
- [temsil varyant 54063, en ucuz uygun] sarma / uzun bant baski: 1
