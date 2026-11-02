# Printful ornament urunleri (salt okuma)

Kaynak: Printful API v1 + v2, ham yanitlar `ham/`. Son istek 2026-11-02T09:48:48Z. Istek 642: GET 138, POST 504 (yalniz /shipping/rates, /v2/shipping-rates).

Notlar:
- Fiyat USD (kargo haric): WW = v2 `prices?currency=USD&selling_region_name=worldwide`; NA = north_america. v1 `price` NA ile ayni (CSV `fiyat_usd_v1`). EUR CSV'de (`fiyat_eur_v2`, `fiyat_eur_v2_europe`). Arka yuz ek ucreti ayri yazildi.
- Olcu, malzeme, kurdele/paket: urun aciklama metni (API, aynen); aciklamada olcu yoksa v1 /products/{id}/sizes tablosu. Hesap yok.
- Baski alani inch = v2 `placement_dimensions`. Tasma payi: API vermedi (aciklamada ve alanlarda yok).
- Uretim yeri = v2 /v2/shipping-rates `shipments[].departure_country` (hedef ulke basina). v1 `availability_status` bolgesi CSV'de (`uretim_bolgesi_durum_v1`); uretim yeriyle ayni sey degil (881: v1 'US', cikis LV).
- Satilabildigi bolge = 9 ulke kargo sorgusunda ucret donen ulkeler; donmeyende API hata mesaji. Gumruk = v2 `customs_fees_possible: true` (alici gumruk/vergi odeyebilir).
- Kargo: 1 adet, ornek adres (merkez posta kodu), USD, en ucuz secenek (hep STANDARD 'Flat Rate'; diger secenek CO2 offset, daha pahali). Takip: yanitlarda takip alani yok -> API vermedi.
- Gun = API `minDeliveryDays`-`maxDeliveryDays`; is/takvim gunu oldugunu API belirtmiyor. Tarihler KARGO.csv'de.
- 1664 ve 1729 v1'de yok: kargolari yalniz v2 /v2/shipping-rates ile sorgulandi (ek kosu); KARGO.csv `kargo_kaynagi=v2`, `http_v1=sorgulanmadi`. Gun = v2 `min_delivery_days`-`max_delivery_days`.

## 1. Urunler

| urun | sekil/olcu | yuz | fiyat USD (WW / NA) | uretim yeri (cikis ulkesi) | satilabildigi bolgeler (9 ulke testi) | baski dosyasi piksel (dpi) / alan inch |
|---|---|---|---|---|---|---|
| 634 Wooden Ornaments | Bell: v1 olcu tablosu: Length 4.09 inches; Width 3.43 inches; Height 0.35 inches; Length 10.4 cm; Width 8.7 cm; Height 0.9 cm<br>Heart: v1 olcu tablosu: Length 4.72 inches; Width 3.46 inches; Height 0.35 inches; Length 12 cm; Width 8.8 cm; Height 0.9 cm<br>Oval: v1 olcu tablosu: Length 5.00 inches; Width 3.39 inches; Height 0.35 inches; Length 12.7 cm; Width 8.6 cm; Height 0.9 cm<br>Star: v1 olcu tablosu: Length 4.06 inches; Width 3.43 inches; Height 0.35 inches; Length 10.3 cm; Width 8.7 cm; Height 0.9 cm<br>Stocking: v1 olcu tablosu: Length 5.12 inches; Width 3.94 inches; Height 0.35 inches; Length 13 cm; Width 10 cm; Height 0.9 cm<br>Tree: v1 olcu tablosu: Length 5.20 inches; Width 3.54 inches; Height 0.35 inches; Length 13.2 cm; Width 9 cm; Height 0.9 cm | cift yuz: on + arka ayri baski alani | WW 10.25 / NA 8.37; arka yuz ek: WW 1.50 / NA 1.49 | US (hedef US, CA); GB (hedef GB); IT (hedef DE, FR, IT, ES, NL); AU (hedef AU) | US, CA, GB, DE, FR, IT, ES, NL, AU; gumruk olasi: CA; aciklama: Important: This product cannot be shipped to South Korea, Hong Kong, Taiwan, Japan, or Singapore. If your shipping address is in these regions, please choose a different product. | front=585x945; back=585x945 (150 dpi) / front=3.9x6.3; back=3.9x6.3 |
| 793 Acrylic Ornaments | Circle: Circle diameter 3″ (7.8 cm)<br>Rectangle: Sizes: Rectangle 3″ × 4″ (7.62 × 10.16 cm) | tek yuz | WW 7.80 / NA 7.80 | US (hedef US) | **YALNIZ ABD** (API: ships to United States only) | default=994x994 (300 dpi) / default=3.31x3.31<br>default=1275x975 (300 dpi) / default=4.25x3.25 |
| 794 Metal Ornaments | Pet Paw: Pet Paw 3.5″ x 3.75″ (8.89 × 9.53 cm)<br>Rectangle: Sizes: Rectangle and Scalloped 3″ × 4″ (7.62 × 10.16 cm)<br>Scalloped: Sizes: Rectangle and Scalloped 3″ × 4″ (7.62 × 10.16 cm)<br>Tag: Tag 3″ x 5″ (7.62 × 12.7 cm) | cift yuz: on + arka ayri baski alani | WW 8.27 / NA 8.27; arka yuz ek: WW 0.00 / NA 0.00 | US (hedef US) | **YALNIZ ABD** (API: ships to United States only) | front=1239x1200; back=1239x1200 (300 dpi) / front=4.13x4.0; back=4.13x4.0<br>front=1275x975; back=1275x975 (300 dpi) / front=4.25x3.25; back=4.25x3.25<br>front=1278x918; back=1278x918 (300 dpi) / back=4.26x3.06; front=4.26x3.06<br>front=976x1576; back=976x1576 (300 dpi) / front=3.25x5.25; back=3.25x5.25 |
| 881 Ceramic Ornament | Circle: Circle-shaped diameter: 2.76″ (7 cm)<br>Heart: Heart-shaped size: 3.11″ × 2.9″ (7.9 cm × 7.37 cm)<br>Snowflake: Snowflake-shape size: 2.17″ × 3″ (5.5 cm × 7.62 cm)<br>Star: Star-shaped size: 3.19″ × 2.68″ (8.1 cm × 6.8 cm) | tek yuz | WW 6.15-6.34 (Circle 6.34; Heart 6.15; Snowflake 6.15; Star 6.15) / NA 6.15-6.34 (Circle 6.34; Heart 6.15; Snowflake 6.15; Star 6.15) | LV (hedef US, CA, GB, DE, FR, IT, ES, NL, AU) | US, CA, GB, DE, FR, IT, ES, NL, AU; gumruk olasi: CA, GB, DE, FR, IT, ES, NL | front=954x954 (300 dpi) / front=3.18x3.18<br>front=978x972 (300 dpi) / front=3.26x3.24<br>front=865x960 (300 dpi) / front=2.88x3.2<br>front=1043x996 (300 dpi) / front=3.48x3.32 |
| 900 Ceramic Ornaments, 2-Side Print | Circle: Circle-shaped diameter: 2.99″ (7.6 cm)<br>Heart: Heart-shaped size: 2.91″ × 2.68″ (7.4 cm × 6.8 cm)<br>Snowflake: Snowflake-shaped size: 2.17″ × 2.99″ (5.5 cm × 7.6 cm)<br>Star: Star-shaped size: 3.35″ × 2.68″ (8.5 cm × 6.8 cm) | cift yuz: ayni tasarim, tek dosya | WW 7.73 / NA 7.73 | LV (hedef US, CA, GB, DE, FR, IT, ES, NL, AU) | US, CA, GB, DE, FR, IT, ES, NL, AU; gumruk olasi: CA, GB, DE, FR, IT, ES, NL | front=954x954 (300 dpi) / front=3.18x3.18<br>front=978x972 (300 dpi) / front=3.26x3.24<br>front=865x960 (300 dpi) / front=2.88x3.2<br>front=1043x996 (300 dpi) / front=3.48x3.32 |
| 901 Metal Christmas Ornament | Bell: Bell-shaped size: 3.31″ × 3.31″ (84 mm × 84 mm)<br>Oval: Oval-shaped size: 2.36″ × 2.99″ (60 mm × 76 mm)<br>Round: Round-shaped diameter: 3.5″ (89 mm)<br>Tree: Tree-shaped size: 3.39″ × 3.94″ (86 mm × 100 mm) | cift yuz: on + arka ayri baski alani | WW 4.61-4.74 (Bell 4.74; Oval 4.61; Round 4.61; Tree 4.61) / NA 4.61-4.74 (Bell 4.74; Oval 4.61; Round 4.61; Tree 4.61); arka yuz ek: WW 0.00 / NA 0.00 | LV (hedef US, CA, GB, DE, FR, IT, ES, NL, AU) | US, CA, GB, DE, FR, IT, ES, NL, AU; gumruk olasi: CA, GB, DE, FR, IT, ES, NL | front=716x722; back=716x722 (200 dpi) / back=3.58x3.61; front=3.58x3.61<br>front=525x650; back=525x650 (200 dpi) / front=2.63x3.25; back=2.63x3.25<br>front=750x750; back=750x750 (200 dpi) / front=3.75x3.75; back=3.75x3.75<br>front=725x839; back=725x839 (200 dpi) / front=3.63x4.2; back=3.63x4.2 |
| 1664 Glass Ornaments | 1 Piece: Size: 3.5″ (88.9 mm<br>5 Pieces: Size: 3.5″ (88.9 mm | tek yuz | WW 19.00-82.98 (1 Piece 19.00; 5 Pieces 82.98) / NA 19.00-82.98 (1 Piece 19.00; 5 Pieces 82.98) | LV (hedef US) | US (eksik ulke: tablo 2); v2 bolge uygunlugu: australia: HTTP 404 Not Found, canada: HTTP 404 Not Found, europe: HTTP 404 Not Found, north_america:not fulfillable, uk: HTTP 404 Not Found | front=1125x1125 (300 dpi) / front=3.75x3.75 |
| 1729 Crystal Glass Ornament | Circle + Gold Gift Packaging: Size: 3.5″ (88.9 mm)<br>Circle + White Gift Packaging: Size: 3.5″ (88.9 mm)<br>Circle: Size: 3.5″ (88.9 mm)<br>Heart + Gold Gift Packaging: Size: 3.5″ (88.9 mm)<br>Heart + White Gift Packaging: Size: 3.5″ (88.9 mm)<br>Heart: Size: 3.5″ (88.9 mm) | tek yuz | WW 5.59-7.73 (Circle + Gold Gift Packaging 7.73; Circle + White Gift Packaging 7.73; Circle 5.59; Heart + Gold Gift Packaging 7.73; Heart + White Gift Packaging 7.73; Heart 5.59) / NA 5.59-7.73 (Circle + Gold Gift Packaging 7.73; Circle + White Gift Packaging 7.73; Circle 5.59; Heart + Gold Gift Packaging 7.73; Heart + White Gift Packaging 7.73; Heart 5.59) | LV (hedef US) | US (eksik ulke: tablo 2); v2 bolge uygunlugu: australia: HTTP 404 Not Found, canada: HTTP 404 Not Found, europe: HTTP 404 Not Found, north_america:not fulfillable, uk: HTTP 404 Not Found | front=900x900 (300 dpi) / front=3.0x3.0 |

## 2. Kargo ucreti (USD, 1 adet, en ucuz yontem). Hucre: ucret (yontem id, min-max gun). † = v2 customs_fees_possible true (alici gumruk/vergi odeyebilir)

| urun | US | CA | GB | DE | FR | IT | ES | NL | AU |
|---|---|---|---|---|---|---|---|---|---|
| 634 Wooden Ornaments | 5.19 (STANDARD, 4-6 g) | 9.29 (STANDARD, 15-15 g) † | 2.59 (STANDARD, 3-3 g) | 7.29 (STANDARD, 4-7 g) | 7.29 (STANDARD, 9-12 g) | 7.29 (STANDARD, 5-12 g) | 7.29 (STANDARD, 2-5 g) | 7.29 (STANDARD, 7-9 g) | 8.39 (STANDARD, 2-5 g) |
| 793 Acrylic Ornaments | 5.49 (STANDARD, 3-6 g) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) |
| 794 Metal Ornaments | 5.49 (STANDARD, 3-6 g; 1 varyant HATA: Order contains products that are out of stock) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) | GONDERILMEZ (API: ships to United States only) |
| 881 Ceramic Ornament | 5.49 (STANDARD, 4-6 g) | 9.89 (STANDARD, 12-18 g) † | 9.89 (STANDARD, 4-12 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 12-18 g) |
| 900 Ceramic Ornaments, 2-Side Print | 5.89 (STANDARD, 4-6 g) | 9.89 (STANDARD, 12-18 g) † | 9.89 (STANDARD, 4-12 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 12-18 g) |
| 901 Metal Christmas Ornament | 5.89 (STANDARD, 4-6 g) | 9.89 (STANDARD, 12-18 g) † | 9.89 (STANDARD, 4-12 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 6-15 g) † | 9.89 (STANDARD, 12-18 g) |
| 1664 Glass Ornaments | 5.89-7.29 (STANDARD, 4-6 g) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) |
| 1729 Crystal Glass Ornament | 5.89 (STANDARD, 4-6 g) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) | GONDERILMEZ (API: Unavailable variant id used) |

Yontem adlari (v1 `name`, tahmini teslim tarihi kismi atildi): STANDARD = Flat Rate

## 2b. Gumruk isareti (customs_fees_possible) neden LV cikisli AB gonderimlerinde acik?

Bilinmiyor. Printful resmi dokumaninda bu alanin ne zaman `true` oldugunu aciklayan bir metin bulunamadi (developers.printful.com ve support.printful.com bu oturumun ag izninde degildi; web aramasinda resmi aciklama cikmadi).
Bulunan resmi metinler alanin mantigini aciklamiyor, yalniz genel kural veriyor:
- Printful Help Center, 'Who pays the customs duties & taxes?': gumruk ucretini son alici oder, Printful tahsil etmez. https://help.printful.com/hc/en-us/articles/360014066159-Who-pays-the-customs-duties-taxes
- printful.com/shipping: siparis teslim bolgesinden farkli bolgedeki tesisten cikarsa teslimde gumruk/islem ucreti olabilir. https://www.printful.com/shipping
- Printful 2017 basin bulteni (Riga tesisi acilisi): AB uye ulkesine giden siparislere gumruk vergisi alinmaz. https://www.printful.com/news/printful-invests-1-million-to-open-its-first-fulfillment-center-in-europe (eski metin; API'nin 2026 isaretiyle celisiyor).
Ham veride gorulen: LV cikisli 881/900/901 icin CA, GB, DE, FR, IT, ES, NL `true`, US ve AU `false`; IT cikisli 634 icin AB ulkeleri `false`, US cikisli 634 -> CA `true`. Ayni AB icinde cikis ulkesine gore fark var; nedeni API'de yok. Kesin yanit icin Printful destegine sorulmali.

## 2c. Aciklama metni ile API verisi arasindaki celiskiler (bagimsiz inceleme, ham dosyaya dayali)

- 634: v1 `price` 8.37 ve v1 back `additional_price` 1.49 = v2 north_america fiyati; v2 worldwide 10.25 ve back 1.50 (urun_634_v2_prices_USD*.json). Diger urunlerde v1 = v2 worldwide.
- 634: aciklamada hem 'Magnetic back' hem 'Two-sided print' var; API'de back placement var (urun_634_v2.json).
- 634: kalinlik aciklamada 0.37″ (9 mm), v1 olcu tablosunda Height 0.35 in / 0.9 cm; tablo notu 'Actual product measurements may vary by up to 1/2"' (urun_634_v1_sizes.json).
- 634: printfile 585x945 px, 150 dpi (diger urunlerde 200-300 dpi) (urun_634_printfiles.json).
- 793: aciklama '4 shapes (Rectangle, Scalloped, Circle, Heart)'; API varyantlari yalniz Circle ve Rectangle. Circle '3″ (7.8 cm)' (3″ = 7.62 cm); v2 baski alani 3.31x3.31 in (urun_793_v2*.json).
- 881 ve 900: Circle icin ayni printfile 845 (954x954 px, 300 dpi = 3.18 in); aciklama capi 2.76″ (881) ve 2.99″ (900).
- 900: aciklama 'bundles of 3, 5, or 10', 901: '3, 5, or 10-unit packs'; API'de ikisinde de yalniz 4 sekil varyanti var, paket varyanti yok (urun_900/901_v2_variants.json).
- 1664: '5 Pieces' varyanti 5'li paket (tek tasarim): 82.98 USD worldwide; tekli 19.00. Baski alani 3.75x3.75 in, urun 3.5″.
- 1729: aciklama 'Gift packaging included'; paketsiz varyantlar (Circle, Heart) 5.59, paketliler 7.73 USD. Printfile 900 px = 3.0 in, urun 3.5″.
- 1664 ve 1729: v2 availability worldwide 'not fulfillable' (793/794 yalniz ABD urunleriyle ayni deger; 881/900/901 'in stock'). Bolge bazli availability ve kargo sonucu tablo 1 ve 2'de (ek kosu, yalniz v2).

## 3. Urun ayrintilari

### 634 Wooden Ornaments

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description, gorev_listesi | HTTP v1 200 v2 200 | varyant kaynagi v1 | durdurulmus: False
- yuz: cift yuz: on + arka ayri baski alani | alanlar: front 'Front print'; back 'Back print' | aciklama: Add a cozy vibe to your home with these double-sided wooden ornaments. Made from Hinoki wood, they’re durable yet lightweight and soft to the touch. / Two-sided print
- baski teknigi (v2 placement:technique): back:uv, front:uv
- alan ek ucreti: v1 files default:None; back:1.49 | v2 USD WW front:0.00; back:1.50 | v2 USD NA front:0.00; back:1.49 | v2 EUR WW front:0.00; back:1.30
- malzeme: Add a cozy vibe to your home with these double-sided wooden ornaments. Made from Hinoki wood, they’re durable yet lightweight and soft to the touch. / Material: solid, natural Hinoki wood / This product is made from natural wood, so darker-colored wooden knots and other slight imperfections may appear anywhere on the ornament. / Due to the characteristics of Hinoki wood, it’s expected to have naturally occurring resin on these wooden ornaments. | kalinlik: Ornament thickness 0.37″ (9 mm)
- kurdele/paket: Comes with a red paper ribbon and a hole to thread it through / Magnetic back
- mense: Product sourced from Korea | v1 origin_country: API vermedi
- kisit (aciklama): Important: This product cannot be shipped to South Korea, Hong Kong, Taiwan, Japan, or Singapore. If your shipping address is in these regions, please choose a different product.
- v2 bolgesel uygunluk (ek kosu): sorgulanmadi
- tasma payi: API vermedi

| varyant | ad | USD v1 | USD v2 WW | USD v2 NA | EUR v2 WW | EUR v2 europe | v1 bolge | v2 uygunluk | printfile | px | dpi | fill | alan inch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16092 | Wooden Ornaments (Wood / Bell) | 8.37 | uv:10.25 | uv:8.37 | uv:9.25 | uv:9.25 | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | worldwide:in stock | front=381; back=381 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover | front=3.9x6.3; back=3.9x6.3 |
| 16088 | Wooden Ornaments (Wood / Heart) | 8.37 | uv:10.25 | uv:8.37 | uv:9.25 | uv:9.25 | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | worldwide:in stock | front=403; back=403 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover | front=3.9x6.3; back=3.9x6.3 |
| 16091 | Wooden Ornaments (Wood / Oval) | 8.37 | uv:10.25 | uv:8.37 | uv:9.25 | uv:9.25 | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | worldwide:in stock | front=404; back=404 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover | front=3.9x6.3; back=3.9x6.3 |
| 16089 | Wooden Ornaments (Wood / Star) | 8.37 | uv:10.25 | uv:8.37 | uv:9.25 | uv:9.25 | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | worldwide:in stock | front=405; back=405 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover | front=3.9x6.3; back=3.9x6.3 |
| 16093 | Wooden Ornaments (Wood / Stocking) | 8.37 | uv:10.25 | uv:8.37 | uv:9.25 | uv:9.25 | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | worldwide:in stock | front=406; back=406 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover | front=3.9x6.3; back=3.9x6.3 |
| 16090 | Wooden Ornaments (Wood / Tree) | 8.37 | uv:10.25 | uv:8.37 | uv:9.25 | uv:9.25 | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | worldwide:in stock | front=407; back=407 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover | front=3.9x6.3; back=3.9x6.3 |

Aciklama metni (API, aynen):

```
Add a cozy vibe to your home with these double-sided wooden ornaments. Made from Hinoki wood, they’re durable yet lightweight and soft to the touch.

• Material: solid, natural Hinoki wood
• Ornament thickness 0.37″ (9 mm)
• Comes with a red paper ribbon and a hole to thread it through
• Magnetic back
• Two-sided print 
• Product sourced from Korea

Disclaimers: 
• This product is made from natural wood, so darker-colored wooden knots and other slight imperfections may appear anywhere on the ornament.
• Due to the characteristics of Hinoki wood, it’s expected to have naturally occurring resin on these wooden ornaments.

Important: This product cannot be shipped to South Korea, Hong Kong, Taiwan, Japan, or Singapore. If your shipping address is in these regions, please choose a different product.
```

### 793 Acrylic Ornaments

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description | HTTP v1 200 v2 200 | varyant kaynagi v1 | durdurulmus: False
- yuz: tek yuz | alanlar: default 'Print file'
- baski teknigi (v2 placement:technique): default:uv
- alan ek ucreti: v1 files default:None | v2 USD WW default:0.00 | v2 USD NA default:0.00 | v2 EUR WW default:0.00
- malzeme: Make special occasions even more joyful with lovely acrylic ornaments. Choose from 4 shapes (Rectangle, Scalloped, Circle, and Heart), and get a beautiful ornament with a glossy finish and red ribbon for hanging. / Material: Optically clear digital-grade acrylic | kalinlik: Ornament thickness: 0.25″ (6.35 mm)
- kurdele/paket: Make special occasions even more joyful with lovely acrylic ornaments. Choose from 4 shapes (Rectangle, Scalloped, Circle, and Heart), and get a beautiful ornament with a glossy finish and red ribbon for hanging. / Comes with a red ribbon for hanging
- mense: Blank product sourced from China | v1 origin_country: USA
- kisit (aciklama): This product is available in the US only. If your shipping address is outside this region, please choose a different product.
- v2 bolgesel uygunluk (ek kosu): sorgulanmadi
- tasma payi: API vermedi

| varyant | ad | USD v1 | USD v2 WW | USD v2 NA | EUR v2 WW | EUR v2 europe | v1 bolge | v2 uygunluk | printfile | px | dpi | fill | alan inch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20250 | Acrylic Ornaments (Circle) | 7.80 | uv:7.80 | uv:7.80 | uv:7.25 | uv:7.25 | US:in_stock | worldwide:not fulfillable | default=681 | default=994x994 | default=300 | default=cover | default=3.31x3.31 |
| 20248 | Acrylic Ornaments (Rectangle) | 7.80 | uv:7.80 | uv:7.80 | uv:7.25 | uv:7.25 | US:in_stock | worldwide:not fulfillable | default=683 | default=1275x975 | default=300 | default=cover | default=4.25x3.25 |

Aciklama metni (API, aynen):

```
Make special occasions even more joyful with lovely acrylic ornaments. Choose from 4 shapes (Rectangle, Scalloped, Circle, and Heart), and get a beautiful ornament with a glossy finish and red ribbon for hanging.

• Material: Optically clear digital-grade acrylic
• Sizes: Rectangle 3″ × 4″ (7.62 × 10.16 cm) , Scalloped 3″ × 4.25″ (7.62 × 10.8 cm), • Circle diameter 3″ (7.8 cm), Heart 3.3″ × 3.2″ (8.4 × 8.1 cm)
• Ornament thickness: 0.25″ (6.35 mm)
• Comes with a red ribbon for hanging
• Blank product sourced from China

Disclaimers:
• This product is available in the US only. If your shipping address is outside this region, please choose a different product.
• The product includes a small QR code on the back which may be slightly visible through the material. This is intended only for the production team's use.
```

### 794 Metal Ornaments

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description | HTTP v1 200 v2 200 | varyant kaynagi v1 | durdurulmus: False
- yuz: cift yuz: on + arka ayri baski alani | alanlar: front 'Front print'; back 'Back print'
- baski teknigi (v2 placement:technique): back:sublimation, front:sublimation
- alan ek ucreti: v1 files default:None; back:None | v2 USD WW front:0.00; back:0.00 | v2 USD NA front:0.00; back:0.00 | v2 EUR WW front:0.00; back:0.00
- malzeme: Material: metal aluminum | kalinlik: Ornament thickness 0.04″ (1 mm)
- kurdele/paket: Personalize your festive tree or home with these high-quality metal ornaments. Choose your favorite from 4 charming shapes (Rectangle, Scalloped, Pet Paw, and Tag) or get all of them for creative variety. Includes a red ribbon for easy hanging. / Comes with a red ribbon and a hole to thread it through
- mense: Blank product sourced from China | v1 origin_country: USA
- kisit (aciklama): Disclaimer: This product is available in the US only. If your shipping address is outside this region, please choose a different product.
- v2 bolgesel uygunluk (ek kosu): sorgulanmadi
- tasma payi: API vermedi

| varyant | ad | USD v1 | USD v2 WW | USD v2 NA | EUR v2 WW | EUR v2 europe | v1 bolge | v2 uygunluk | printfile | px | dpi | fill | alan inch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20253 | Metal Ornaments (Pet Paw) | 8.27 | sublimation:8.27 | sublimation:8.27 | sublimation:7.50 | sublimation:7.50 | US:in_stock | worldwide:not fulfillable | front=685; back=685 | front=1239x1200; back=1239x1200 | front=300; back=300 | front=cover; back=cover | front=4.13x4.0; back=4.13x4.0 |
| 20255 | Metal Ornaments (Rectangle) | 8.27 | sublimation:8.27 | sublimation:8.27 | sublimation:7.50 | sublimation:7.50 | US:in_stock | worldwide:not fulfillable | front=686; back=686 | front=1275x975; back=1275x975 | front=300; back=300 | front=cover; back=cover | front=4.25x3.25; back=4.25x3.25 |
| 20252 | Metal Ornaments (Scalloped) | 8.27 | sublimation:8.27 | sublimation:8.27 | sublimation:7.50 | sublimation:7.50 | US:in_stock | worldwide:not fulfillable | front=687; back=687 | front=1278x918; back=1278x918 | front=300; back=300 | front=cover; back=cover | back=4.26x3.06; front=4.26x3.06 |
| 20254 | Metal Ornaments (Tag) | 8.27 | sublimation:8.27 | sublimation:8.27 | sublimation:7.50 | sublimation:7.50 | US:supplier_out_of_stock | worldwide:not fulfillable | front=688; back=688 | front=976x1576; back=976x1576 | front=300; back=300 | front=cover; back=cover | front=3.25x5.25; back=3.25x5.25 |

Aciklama metni (API, aynen):

```
Personalize your festive tree or home with these high-quality metal ornaments. Choose your favorite from 4 charming shapes (Rectangle, Scalloped, Pet Paw, and Tag) or get all of them for creative variety. Includes a red ribbon for easy hanging.

• Material: metal aluminum
• Sizes: Rectangle and Scalloped 3″ × 4″ (7.62 × 10.16 cm), Pet Paw 3.5″ x 3.75″ (8.89 × 9.53 cm), Tag 3″ x 5″ (7.62 × 12.7 cm)
• Ornament thickness 0.04″ (1 mm)
• Comes with a red ribbon and a hole to thread it through
• Blank product sourced from China

Disclaimer: This product is available in the US only. If your shipping address is outside this region, please choose a different product.
```

### 881 Ceramic Ornament

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description, gorev_listesi | HTTP v1 200 v2 200 | varyant kaynagi v1 | durdurulmus: False
- yuz: tek yuz | alanlar: front 'Front print'
- baski teknigi (v2 placement:technique): front:sublimation
- alan ek ucreti: v1 files default:None | v2 USD WW front:0.00 | v2 USD NA front:0.00 | v2 EUR WW front:0.00
- malzeme: Bring charm to your home with a glossy ceramic ornament available in heart, star, snowflake, or circle shapes. With a smooth finish and elegant gold-toned string, it stands out in any festive setting. / 100% ceramic | kalinlik: Ornament thickness: 0.125″ (3 mm)
- kurdele/paket: Bring charm to your home with a glossy ceramic ornament available in heart, star, snowflake, or circle shapes. With a smooth finish and elegant gold-toned string, it stands out in any festive setting. / Gold-colored string included
- mense: Blank product sourced from China | v1 origin_country: China
- kisit (aciklama): API vermedi
- v2 bolgesel uygunluk (ek kosu): sorgulanmadi
- tasma payi: API vermedi

| varyant | ad | USD v1 | USD v2 WW | USD v2 NA | EUR v2 WW | EUR v2 europe | v1 bolge | v2 uygunluk | printfile | px | dpi | fill | alan inch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 22782 | Ceramic Ornament (Circle) | 6.34 | sublimation:6.34 | sublimation:6.34 | sublimation:5.75 | sublimation:5.75 | US:in_stock | worldwide:in stock | front=845 | front=954x954 | front=300 | front=cover | front=3.18x3.18 |
| 22783 | Ceramic Ornament (Heart) | 6.15 | sublimation:6.15 | sublimation:6.15 | sublimation:5.75 | sublimation:5.75 | US:in_stock | worldwide:in stock | front=843 | front=978x972 | front=300 | front=cover | front=3.26x3.24 |
| 22785 | Ceramic Ornament (Snowflake) | 6.15 | sublimation:6.15 | sublimation:6.15 | sublimation:5.75 | sublimation:5.75 | US:in_stock | worldwide:in stock | front=838 | front=865x960 | front=300 | front=cover | front=2.88x3.2 |
| 22784 | Ceramic Ornament (Star) | 6.15 | sublimation:6.15 | sublimation:6.15 | sublimation:5.75 | sublimation:5.75 | US:in_stock | worldwide:in stock | front=844 | front=1043x996 | front=300 | front=cover | front=3.48x3.32 |

Aciklama metni (API, aynen):

```
Bring charm to your home with a glossy ceramic ornament available in heart, star, snowflake, or circle shapes. With a smooth finish and elegant gold-toned string, it stands out in any festive setting.

• 100% ceramic
• Circle-shaped diameter: 2.76″ (7 cm)
• Heart-shaped size: 3.11″ × 2.9″ (7.9 cm × 7.37 cm)
• Star-shaped size: 3.19″ × 2.68″ (8.1 cm × 6.8 cm)
• Snowflake-shape size: 2.17″ × 3″ (5.5 cm × 7.62 cm)
• Ornament thickness: 0.125″ (3 mm)
• Glossy finish
• White backing
• Gold-colored string included
• Blank product sourced from China
```

### 900 Ceramic Ornaments, 2-Side Print

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description, gorev_listesi | HTTP v1 200 v2 200 | varyant kaynagi v1 | durdurulmus: False
- yuz: cift yuz: ayni tasarim, tek dosya | alanlar: front '2-Side print' | aciklama: Shiny from all angles, these two-sided ornaments bring double the cheer. Great for personal gifting or maxing your seasonal decor, they come in four festive shapes with a high-gloss finish. Available solo or in three, five, or ten-unit packs. / Two-sided print with the same design
- baski teknigi (v2 placement:technique): front:sublimation
- alan ek ucreti: v1 files default:None | v2 USD WW front:0.00 | v2 USD NA front:0.00 | v2 EUR WW front:0.00
- malzeme: 100% ceramic | kalinlik: Ornament thickness: 0.1″ (2.5 mm)
- kurdele/paket: Shiny from all angles, these two-sided ornaments bring double the cheer. Great for personal gifting or maxing your seasonal decor, they come in four festive shapes with a high-gloss finish. Available solo or in three, five, or ten-unit packs. / Gold-colored string included / Available individually or in bundles of 3, 5, or 10
- mense: Blank product sourced from China | v1 origin_country: China
- kisit (aciklama): API vermedi
- v2 bolgesel uygunluk (ek kosu): sorgulanmadi
- tasma payi: API vermedi

| varyant | ad | USD v1 | USD v2 WW | USD v2 NA | EUR v2 WW | EUR v2 europe | v1 bolge | v2 uygunluk | printfile | px | dpi | fill | alan inch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 23133 | Ceramic Ornaments, 2-Side Print (1 pc / Circle) | 7.73 | sublimation:7.73 | sublimation:7.73 | sublimation:6.95 | sublimation:6.95 | US:in_stock | worldwide:in stock | front=845 | front=954x954 | front=300 | front=cover | front=3.18x3.18 |
| 23144 | Ceramic Ornaments, 2-Side Print (1 pc / Heart) | 7.73 | sublimation:7.73 | sublimation:7.73 | sublimation:6.95 | sublimation:6.95 | US:in_stock | worldwide:in stock | front=843 | front=978x972 | front=300 | front=cover | front=3.26x3.24 |
| 23155 | Ceramic Ornaments, 2-Side Print (1 pc / Snowflake) | 7.73 | sublimation:7.73 | sublimation:7.73 | sublimation:6.95 | sublimation:6.95 | US:in_stock | worldwide:in stock | front=838 | front=865x960 | front=300 | front=cover | front=2.88x3.2 |
| 23151 | Ceramic Ornaments, 2-Side Print (1 pc / Star) | 7.73 | sublimation:7.73 | sublimation:7.73 | sublimation:6.95 | sublimation:6.95 | US:in_stock | worldwide:in stock | front=844 | front=1043x996 | front=300 | front=cover | front=3.48x3.32 |

Aciklama metni (API, aynen):

```
Shiny from all angles, these two-sided ornaments bring double the cheer. Great for personal gifting or maxing your seasonal decor, they come in four festive shapes with a high-gloss finish. Available solo or in three, five, or ten-unit packs.

• 100% ceramic
• Circle-shaped diameter: 2.99″ (7.6 cm)
• Heart-shaped size: 2.91″ × 2.68″ (7.4 cm × 6.8 cm)
• Star-shaped size: 3.35″ × 2.68″ (8.5 cm × 6.8 cm)
• Snowflake-shaped size: 2.17″ × 2.99″ (5.5 cm × 7.6 cm)
• Ornament thickness: 0.1″ (2.5 mm)
• Glossy finish
• Two-sided print with the same design
• Gold-colored string included
• Available individually or in bundles of 3, 5, or 10
• Blank product sourced from China
```

### 901 Metal Christmas Ornament

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description | HTTP v1 200 v2 200 | varyant kaynagi v1 | durdurulmus: False
- yuz: cift yuz: on + arka ayri baski alani | alanlar: front 'Front print'; back 'Back print' | aciklama: Shiny from all angles—these two-sided ornaments bring double the cheer. Great for personal gifting or maxing your seasonal decor, they come in 4 festive shapes with a high-gloss finish. Available solo or in 3, 5, or 10-unit packs.
- baski teknigi (v2 placement:technique): back:sublimation, front:sublimation
- alan ek ucreti: v1 files default:None; back:None | v2 USD WW front:0.00; back:0.00 | v2 USD NA front:0.00; back:0.00 | v2 EUR WW front:0.00; back:0.00
- malzeme: White aluminum base | kalinlik: Ornament thickness: 0.025″ (0.6 mm)
- kurdele/paket: Shiny from all angles—these two-sided ornaments bring double the cheer. Great for personal gifting or maxing your seasonal decor, they come in 4 festive shapes with a high-gloss finish. Available solo or in 3, 5, or 10-unit packs. / Red ribbon included
- mense: Blank product sourced from China | v1 origin_country: USA
- kisit (aciklama): API vermedi
- v2 bolgesel uygunluk (ek kosu): sorgulanmadi
- tasma payi: API vermedi

| varyant | ad | USD v1 | USD v2 WW | USD v2 NA | EUR v2 WW | EUR v2 europe | v1 bolge | v2 uygunluk | printfile | px | dpi | fill | alan inch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 23138 | Metal Christmas Ornament (White aluminum / Bell) | 4.74 | sublimation:4.74 | sublimation:4.74 | sublimation:4.50 | sublimation:4.50 | US:in_stock | worldwide:in stock | front=869; back=869 | front=716x722; back=716x722 | front=200; back=200 | front=cover; back=cover | back=3.58x3.61; front=3.58x3.61 |
| 23135 | Metal Christmas Ornament (White aluminum / Oval) | 4.61 | sublimation:4.61 | sublimation:4.61 | sublimation:4.25 | sublimation:4.25 | US:in_stock | worldwide:in stock | front=866; back=866 | front=525x650; back=525x650 | front=200; back=200 | front=cover; back=cover | front=2.63x3.25; back=2.63x3.25 |
| 23136 | Metal Christmas Ornament (White aluminum / Round) | 4.61 | sublimation:4.61 | sublimation:4.61 | sublimation:4.25 | sublimation:4.25 | US:in_stock | worldwide:in stock | front=868; back=868 | front=750x750; back=750x750 | front=200; back=200 | front=cover; back=cover | front=3.75x3.75; back=3.75x3.75 |
| 23137 | Metal Christmas Ornament (White aluminum / Tree) | 4.61 | sublimation:4.61 | sublimation:4.61 | sublimation:4.25 | sublimation:4.25 | US:in_stock | worldwide:in stock | front=867; back=867 | front=725x839; back=725x839 | front=200; back=200 | front=cover; back=cover | front=3.63x4.2; back=3.63x4.2 |

Aciklama metni (API, aynen):

```
Shiny from all angles—these two-sided ornaments bring double the cheer. Great for personal gifting or maxing your seasonal decor, they come in 4 festive shapes with a high-gloss finish. Available solo or in 3, 5, or 10-unit packs.

• White aluminum base
• Round-shaped diameter: 3.5″ (89 mm)
• Bell-shaped size: 3.31″ × 3.31″ (84 mm × 84 mm)
• Oval-shaped size: 2.36″ × 2.99″ (60 mm × 76 mm)
• Tree-shaped size: 3.39″ × 3.94″ (86 mm × 100 mm)
• Ornament thickness: 0.025″ (0.6 mm)
• Glossy finish
• Red ribbon included
• Blank product sourced from China

Disclaimer: The displayed price is for a single item.
```

### 1664 Glass Ornaments

- eslesme: v2.name, v2.description | HTTP v1 404 v2 200 | varyant kaynagi v2 | durdurulmus: False
- yuz: tek yuz | alanlar: front 'Front print' | aciklama: These classic glass ornaments are made for showcasing your artwork and adding a personalized touch to any decoration. Customize them with your design and create beautiful ornaments for gifts, seasonal decorating, or your online store. Each ornament features beveled edges, a one-sided print, and a gold ribbon for hanging. / One-sided print
- baski teknigi (v2 placement:technique): front:uv
- alan ek ucreti: v1 files API vermedi | v2 USD WW front:0.00 | v2 USD NA front:0.00 | v2 EUR WW front:0.00
- malzeme: These classic glass ornaments are made for showcasing your artwork and adding a personalized touch to any decoration. Customize them with your design and create beautiful ornaments for gifts, seasonal decorating, or your online store. Each ornament features beveled edges, a one-sided print, and a gold ribbon for hanging. / 100% glass | kalinlik: API vermedi
- kurdele/paket: These classic glass ornaments are made for showcasing your artwork and adding a personalized touch to any decoration. Customize them with your design and create beautiful ornaments for gifts, seasonal decorating, or your online store. Each ornament features beveled edges, a one-sided print, and a gold ribbon for hanging. / Available as a single ornament or in bundles of 5 / One design for the whole bundle / Gold ribbon for hanging
- mense: API vermedi | v1 origin_country: API vermedi
- kisit (aciklama): API vermedi
- v2 bolgesel uygunluk (ek kosu): north_america:not fulfillable; australia: HTTP 404 Not Found; canada: HTTP 404 Not Found; europe: HTTP 404 Not Found; uk: HTTP 404 Not Found
- tasma payi: API vermedi

| varyant | ad | USD v1 | USD v2 WW | USD v2 NA | EUR v2 WW | EUR v2 europe | v1 bolge | v2 uygunluk | printfile | px | dpi | fill | alan inch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 52913 | Generic brand  (1 Piece) | API vermedi (v1 HTTP 404) | uv:19.00 | uv:19.00 | uv:17.25 | uv:17.25 | API vermedi | worldwide:not fulfillable | front=2111 | front=1125x1125 | front=300 | front=cover | front=3.75x3.75 |
| 52816 | Generic brand  (5 Pieces) | API vermedi (v1 HTTP 404) | uv:82.98 | uv:82.98 | uv:74.75 | uv:74.75 | API vermedi | worldwide:not fulfillable | front=2111 | front=1125x1125 | front=300 | front=cover | front=3.75x3.75 |

Aciklama metni (API, aynen):

```
These classic glass ornaments are made for showcasing your artwork and adding a personalized touch to any decoration. Customize them with your design and create beautiful ornaments for gifts, seasonal decorating, or your online store. Each ornament features beveled edges, a one-sided print, and a gold ribbon for hanging.

• 100% glass
• Size: 3.5″ (88.9 mm
• Available as a single ornament or in bundles of 5
• One design for the whole bundle
• Beveled edges
• One-sided print
• Gold ribbon for hanging
```

### 1729 Crystal Glass Ornament

- eslesme: v2.name, v2.description | HTTP v1 404 v2 200 | varyant kaynagi v2 | durdurulmus: False
- yuz: tek yuz | alanlar: front 'Front print' | aciklama: These classic crystal glass ornaments are made for showcasing your artwork and adding a personalized touch to any decoration. Customize them with your design and create beautiful ornaments for gifts, seasonal decorating, or your online store. Each ornament features beveled edges, a one-sided print, a red ribbon for hanging, and comes in gift-ready packaging. / One-sided print
- baski teknigi (v2 placement:technique): front:uv
- alan ek ucreti: v1 files API vermedi | v2 USD WW front:0.00 | v2 USD NA front:0.00 | v2 EUR WW front:0.00
- malzeme: These classic crystal glass ornaments are made for showcasing your artwork and adding a personalized touch to any decoration. Customize them with your design and create beautiful ornaments for gifts, seasonal decorating, or your online store. Each ornament features beveled edges, a one-sided print, a red ribbon for hanging, and comes in gift-ready packaging. / 100% crystal glass | kalinlik: API vermedi
- kurdele/paket: These classic crystal glass ornaments are made for showcasing your artwork and adding a personalized touch to any decoration. Customize them with your design and create beautiful ornaments for gifts, seasonal decorating, or your online store. Each ornament features beveled edges, a one-sided print, a red ribbon for hanging, and comes in gift-ready packaging. / Available as a single ornament or in bundles of 5 / One design for the whole bundle / Red ribbon for hanging / Gift packaging included
- mense: API vermedi | v1 origin_country: API vermedi
- kisit (aciklama): API vermedi
- v2 bolgesel uygunluk (ek kosu): north_america:not fulfillable; australia: HTTP 404 Not Found; canada: HTTP 404 Not Found; europe: HTTP 404 Not Found; uk: HTTP 404 Not Found
- tasma payi: API vermedi

| varyant | ad | USD v1 | USD v2 WW | USD v2 NA | EUR v2 WW | EUR v2 europe | v1 bolge | v2 uygunluk | printfile | px | dpi | fill | alan inch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 54341 | Crystal Glass Ornament (Circle + Gold Gift Packaging) | API vermedi (v1 HTTP 404) | uv:7.73 | uv:7.73 | uv:6.95 | uv:6.95 | API vermedi | worldwide:not fulfillable | front=2353 | front=900x900 | front=300 | front=cover | front=3.0x3.0 |
| 54339 | Crystal Glass Ornament (Circle + White Gift Packaging) | API vermedi (v1 HTTP 404) | uv:7.73 | uv:7.73 | uv:6.95 | uv:6.95 | API vermedi | worldwide:not fulfillable | front=2353 | front=900x900 | front=300 | front=cover | front=3.0x3.0 |
| 54337 | Crystal Glass Ornament (Circle) | API vermedi (v1 HTTP 404) | uv:5.59 | uv:5.59 | uv:5.25 | uv:5.25 | API vermedi | worldwide:not fulfillable | front=2353 | front=900x900 | front=300 | front=cover | front=3.0x3.0 |
| 54342 | Crystal Glass Ornament (Heart + Gold Gift Packaging) | API vermedi (v1 HTTP 404) | uv:7.73 | uv:7.73 | uv:6.95 | uv:6.95 | API vermedi | worldwide:not fulfillable | front=2353 | front=900x900 | front=300 | front=cover | front=3.0x3.0 |
| 54340 | Crystal Glass Ornament (Heart + White Gift Packaging) | API vermedi (v1 HTTP 404) | uv:7.73 | uv:7.73 | uv:6.95 | uv:6.95 | API vermedi | worldwide:not fulfillable | front=2353 | front=900x900 | front=300 | front=cover | front=3.0x3.0 |
| 54338 | Crystal Glass Ornament (Heart) | API vermedi (v1 HTTP 404) | uv:5.59 | uv:5.59 | uv:5.25 | uv:5.25 | API vermedi | worldwide:not fulfillable | front=2353 | front=900x900 | front=300 | front=cover | front=3.0x3.0 |

Aciklama metni (API, aynen):

```
These classic crystal glass ornaments are made for showcasing your artwork and adding a personalized touch to any decoration. Customize them with your design and create beautiful ornaments for gifts, seasonal decorating, or your online store. Each ornament features beveled edges, a one-sided print, a red ribbon for hanging, and comes in gift-ready packaging.

• 100% crystal glass
• Size: 3.5″ (88.9 mm)
• Available as a single ornament or in bundles of 5
• One design for the whole bundle
• Beveled edges
• One-sided print
• Red ribbon for hanging
• Gift packaging included
```

