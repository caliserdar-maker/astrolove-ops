# Printful ornament urunleri (salt okuma)

Kaynak: Printful API (v1 + v2), ham yanitlar `ham/`. Son istek: 2026-11-02T08:53:46Z. Istek: 560 (GET 128, POST 432: /shipping/rates, /v2/shipping-rates).
Olcu cm = inch x 2.54 (hesap). Fiyat: v1 `variants[].price` (USD, kargo haric); v2 `prices?currency=` (USD/EUR).
Kargo: 1 adet, ornek adres (baskent/merkez posta kodu), en ucuz secenek (v1 /shipping/rates). Cikis ulkesi: v2 /v2/shipping-rates `shipments[].departure_country`. Takip: API'de takip alani yoksa "API vermedi".

## 1. Urunler

| urun | sekil/olcu | yuz | fiyat USD (v1) | uretim yeri (cikis, v2) | satilabildigi bolgeler (v1) | baski dosyasi piksel |
|---|---|---|---|---|---|---|
| 634 Wooden Ornaments | Wooden Ornaments (Wood / Bell) [Bell]; Wooden Ornaments (Wood / Heart) [Heart]; Wooden Ornaments (Wood / Oval) [Oval]; Wooden Ornaments (Wood / Star) [Star]; Wooden Ornaments (Wood / Stocking) [Stocking]; Wooden Ornaments (Wood / Tree) [Tree] | cift yuz secenegi (front, back) | 8.37 | US (hedef US, CA); GB (hedef GB); IT (hedef DE, FR, IT, ES, NL); AU (hedef AU) | AU, EU, UK, US | front=585x945; back=585x945 |
| 793 Acrylic Ornaments | Acrylic Ornaments (Circle) [Circle]; Acrylic Ornaments (Rectangle) [Rectangle] | tek yuz (default) | 7.80 | US (hedef US); API vermedi (hedef CA, GB, DE, FR, IT, ES, NL, AU) | **YALNIZ ABD** (US) | default=1275x975; default=994x994 |
| 794 Metal Ornaments | Metal Ornaments (Pet Paw) [Pet Paw]; Metal Ornaments (Rectangle) [Rectangle]; Metal Ornaments (Scalloped) [Scalloped]; Metal Ornaments (Tag) [Tag] | cift yuz secenegi (front, back) | 8.27 | US (hedef US); API vermedi (hedef CA, GB, DE, FR, IT, ES, NL, AU) | **YALNIZ ABD** (US) | front=1239x1200; back=1239x1200; front=1275x975; back=1275x975; front=1278x918; back=1278x918; front=976x1576; back=976x1576 |
| 881 Ceramic Ornament | Ceramic Ornament (Circle) [Circle]; Ceramic Ornament (Heart) [Heart]; Ceramic Ornament (Snowflake) [Snowflake]; Ceramic Ornament (Star) [Star] | tek yuz (front) | 6.15-6.34 | LV (hedef US, CA, GB, DE, FR, IT, ES, NL, AU) | **YALNIZ ABD** (US) | front=1043x996; front=865x960; front=954x954; front=978x972 |
| 900 Ceramic Ornaments, 2-Side Print | Ceramic Ornaments, 2-Side Print (1 pc / Circle) [Circle]; Ceramic Ornaments, 2-Side Print (1 pc / Heart) [Heart]; Ceramic Ornaments, 2-Side Print (1 pc / Snowflake) [Snowflake]; Ceramic Ornaments, 2-Side Print (1 pc / Star) [Star] | tek yuz (front) | 7.73 | LV (hedef US, CA, GB, DE, FR, IT, ES, NL, AU) | **YALNIZ ABD** (US) | front=1043x996; front=865x960; front=954x954; front=978x972 |
| 901 Metal Christmas Ornament | Metal Christmas Ornament (White aluminum / Bell) [Bell]; Metal Christmas Ornament (White aluminum / Oval) [Oval]; Metal Christmas Ornament (White aluminum / Round) [Round]; Metal Christmas Ornament (White aluminum / Tree) [Tree] | cift yuz secenegi (front, back) | 4.61-4.74 | LV (hedef US, CA, GB, DE, FR, IT, ES, NL, AU) | **YALNIZ ABD** (US) | front=525x650; back=525x650; front=716x722; back=716x722; front=725x839; back=725x839; front=750x750; back=750x750 |
| 1664 Glass Ornaments | API vermedi | tek yuz (front) | API vermedi | API vermedi | API vermedi | API vermedi |
| 1729 Crystal Glass Ornament | API vermedi | tek yuz (front) | API vermedi | API vermedi | API vermedi | API vermedi |

## 2. Kargo ucreti (USD, 1 adet, en ucuz yontem; hucre: ucret (yontem id, min-max gun))

| urun | US | CA | GB | DE | FR | IT | ES | NL | AU |
|---|---|---|---|---|---|---|---|---|---|
| 634 Wooden Ornaments | 5.19 (STANDARD, 4-6 g) | 9.29 (STANDARD, 15-15 g) | 2.59 (STANDARD, 3-3 g) | 7.29 (STANDARD, 4-7 g) | 7.29 (STANDARD, 9-12 g) | 7.29 (STANDARD, 5-12 g) | 7.29 (STANDARD, 2-5 g) | 7.29 (STANDARD, 7-9 g) | 8.39 (STANDARD, 2-5 g) |
| 793 Acrylic Ornaments | 5.49 (STANDARD, 3-6 g) | HATA 400 | HATA 400 | HATA 400 | HATA 400 | HATA 400 | HATA 400 | HATA 400 | HATA 400 |
| 794 Metal Ornaments | 5.49 (STANDARD, 3-6 g) | HATA 400 | HATA 400 | HATA 400 | HATA 400 | HATA 400 | HATA 400 | HATA 400 | HATA 400 |
| 881 Ceramic Ornament | 5.49 (STANDARD, 4-6 g) | 9.89 (STANDARD, 12-18 g) | 9.89 (STANDARD, 4-12 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 12-18 g) |
| 900 Ceramic Ornaments, 2-Side Print | 5.89 (STANDARD, 4-6 g) | 9.89 (STANDARD, 12-18 g) | 9.89 (STANDARD, 4-12 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 12-18 g) |
| 901 Metal Christmas Ornament | 5.89 (STANDARD, 4-6 g) | 9.89 (STANDARD, 12-18 g) | 9.89 (STANDARD, 4-12 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 6-15 g) | 9.89 (STANDARD, 12-18 g) |
| 1664 Glass Ornaments | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi |
| 1729 Crystal Glass Ornament | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi | sorgulanmadi |

Yontem adlari (v1 `name`, ilk varyant):

- 634: AU: Flat Rate (Estimated delivery: Nov 5⁠–9)  | CA: Flat Rate (Estimated delivery: Nov 20)  | DE: Flat Rate (Estimated delivery: Nov 9⁠–14)  | ES: Flat Rate (Estimated delivery: Nov 6⁠–12)  | FR: Flat Rate (Estimated delivery: Nov 13⁠–19)  | GB: Flat Rate (Estimated delivery: Nov 7⁠–9)  | IT: Flat Rate (Estimated delivery: Nov 9⁠–19)  | NL: Flat Rate (Estimated delivery: Nov 11⁠–16)  | US: Flat Rate (Estimated delivery: Nov 9⁠–11) 
- 793: AU: API vermedi | CA: API vermedi | DE: API vermedi | ES: API vermedi | FR: API vermedi | GB: API vermedi | IT: API vermedi | NL: API vermedi | US: Flat Rate (Estimated delivery: Nov 10⁠–13) 
- 794: AU: API vermedi | CA: API vermedi | DE: API vermedi | ES: API vermedi | FR: API vermedi | GB: API vermedi | IT: API vermedi | NL: API vermedi | US: Flat Rate (Estimated delivery: Nov 9⁠–11) 
- 881: AU: Flat Rate (Estimated delivery: Nov 17⁠–23)  | CA: Flat Rate (Estimated delivery: Nov 17⁠–23)  | DE: Flat Rate (Estimated delivery: Nov 11⁠–20)  | ES: Flat Rate (Estimated delivery: Nov 11⁠–20)  | FR: Flat Rate (Estimated delivery: Nov 11⁠–20)  | GB: Flat Rate (Estimated delivery: Nov 9⁠–17)  | IT: Flat Rate (Estimated delivery: Nov 11⁠–20)  | NL: Flat Rate (Estimated delivery: Nov 11⁠–20)  | US: Flat Rate (Estimated delivery: Nov 9⁠–11) 
- 900: AU: Flat Rate (Estimated delivery: Nov 17⁠–23)  | CA: Flat Rate (Estimated delivery: Nov 17⁠–23)  | DE: Flat Rate (Estimated delivery: Nov 11⁠–20)  | ES: Flat Rate (Estimated delivery: Nov 11⁠–20)  | FR: Flat Rate (Estimated delivery: Nov 11⁠–20)  | GB: Flat Rate (Estimated delivery: Nov 9⁠–17)  | IT: Flat Rate (Estimated delivery: Nov 11⁠–20)  | NL: Flat Rate (Estimated delivery: Nov 11⁠–20)  | US: Flat Rate (Estimated delivery: Nov 9⁠–11) 
- 901: AU: Flat Rate (Estimated delivery: Nov 17⁠–23)  | CA: Flat Rate (Estimated delivery: Nov 17⁠–23)  | DE: Flat Rate (Estimated delivery: Nov 11⁠–20)  | ES: Flat Rate (Estimated delivery: Nov 11⁠–20)  | FR: Flat Rate (Estimated delivery: Nov 11⁠–20)  | GB: Flat Rate (Estimated delivery: Nov 9⁠–17)  | IT: Flat Rate (Estimated delivery: Nov 11⁠–20)  | NL: Flat Rate (Estimated delivery: Nov 11⁠–20)  | US: Flat Rate (Estimated delivery: Nov 9⁠–11) 

## 3. Urun ayrintilari

### 634 Wooden Ornaments

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description, gorev_listesi | HTTP v1 200 v2 200
- tur: Ornaments | Wood | model: Ornaments | Wood | marka: API vermedi | durdurulmus: False
- baski teknigi: UV printing
- yuz / baski alanlari: cift yuz secenegi (front, back) | v1 files ek ucret: default:None; back:1.49
- v2 placement fiyatlari USD: front:0.00; back:1.50
- v2 placement fiyatlari EUR: front:0.00; back:1.30
- v2 bolge fiyati (EUR europe / USD north_america), varyant sirasiyla: 16092: uv:9.25 / uv:8.37 | 16088: uv:9.25 / uv:8.37 | 16091: uv:9.25 / uv:8.37 | 16089: uv:9.25 / uv:8.37 | 16093: uv:9.25 / uv:8.37 | 16090: uv:9.25 / uv:8.37
- ort. uretim suresi (v1 avg_fulfillment_time): API vermedi | origin_country (v1): API vermedi
- tasma payi: API vermedi

Olcu tablosu (API):

- v1_sizes product_measure | Length (inches): Bell: 4.09; Heart: 4.72; Oval: 5.00; Star: 4.06; Stocking: 5.12; Tree: 5.20
- v1_sizes product_measure | Width (inches): Bell: 3.43; Heart: 3.46; Oval: 3.39; Star: 3.43; Stocking: 3.94; Tree: 3.54
- v1_sizes product_measure | Height (inches): Bell: 0.35; Heart: 0.35; Oval: 0.35; Star: 0.35; Stocking: 0.35; Tree: 0.35
- v1_sizes product_measure | Length (cm): Bell: 10.4; Heart: 12; Oval: 12.7; Star: 10.3; Stocking: 13; Tree: 13.2
- v1_sizes product_measure | Width (cm): Bell: 8.7; Heart: 8.8; Oval: 8.6; Star: 8.7; Stocking: 10; Tree: 9
- v1_sizes product_measure | Height (cm): Bell: 0.9; Heart: 0.9; Oval: 0.9; Star: 0.9; Stocking: 0.9; Tree: 0.9
- v2_sizes product_measure | Length (inches): Bell: 4.09; Heart: 4.72; Oval: 5.00; Star: 4.06; Stocking: 5.12; Tree: 5.20
- v2_sizes product_measure | Width (inches): Bell: 3.43; Heart: 3.46; Oval: 3.39; Star: 3.43; Stocking: 3.94; Tree: 3.54
- v2_sizes product_measure | Height (inches): Bell: 0.35; Heart: 0.35; Oval: 0.35; Star: 0.35; Stocking: 0.35; Tree: 0.35

| varyant | ad | size | inch | cm (hesap) | USD v1 | USD v2 | EUR v2 | stok | bolge v1 | printfile | px | dpi | fill |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16092 | Wooden Ornaments (Wood / Bell) | Bell | API vermedi | API vermedi | 8.37 | uv:10.25 | uv:9.25 | True | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | front=381; back=381 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover |
| 16088 | Wooden Ornaments (Wood / Heart) | Heart | API vermedi | API vermedi | 8.37 | uv:10.25 | uv:9.25 | True | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | front=403; back=403 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover |
| 16091 | Wooden Ornaments (Wood / Oval) | Oval | API vermedi | API vermedi | 8.37 | uv:10.25 | uv:9.25 | True | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | front=404; back=404 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover |
| 16089 | Wooden Ornaments (Wood / Star) | Star | API vermedi | API vermedi | 8.37 | uv:10.25 | uv:9.25 | True | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | front=405; back=405 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover |
| 16093 | Wooden Ornaments (Wood / Stocking) | Stocking | API vermedi | API vermedi | 8.37 | uv:10.25 | uv:9.25 | True | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | front=406; back=406 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover |
| 16090 | Wooden Ornaments (Wood / Tree) | Tree | API vermedi | API vermedi | 8.37 | uv:10.25 | uv:9.25 | True | AU:in_stock; US:in_stock; UK:in_stock; EU:in_stock | front=407; back=407 | front=585x945; back=585x945 | front=150; back=150 | front=cover; back=cover |

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

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description | HTTP v1 200 v2 200
- tur: Ornament | Acrylic | model: Ornament | Acrylic | marka: API vermedi | durdurulmus: False
- baski teknigi: UV printing
- yuz / baski alanlari: tek yuz (default) | v1 files ek ucret: default:None
- v2 placement fiyatlari USD: default:0.00
- v2 placement fiyatlari EUR: default:0.00
- v2 bolge fiyati (EUR europe / USD north_america), varyant sirasiyla: 20250: uv:7.25 / uv:7.80 | 20248: uv:7.25 / uv:7.80
- ort. uretim suresi (v1 avg_fulfillment_time): API vermedi | origin_country (v1): USA
- tasma payi: API vermedi

Olcu tablosu: API vermedi

| varyant | ad | size | inch | cm (hesap) | USD v1 | USD v2 | EUR v2 | stok | bolge v1 | printfile | px | dpi | fill |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20250 | Acrylic Ornaments (Circle) | Circle | API vermedi | API vermedi | 7.80 | uv:7.80 | uv:7.25 | True | US:in_stock | default=681 | default=994x994 | default=300 | default=cover |
| 20248 | Acrylic Ornaments (Rectangle) | Rectangle | API vermedi | API vermedi | 7.80 | uv:7.80 | uv:7.25 | True | US:in_stock | default=683 | default=1275x975 | default=300 | default=cover |

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

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description | HTTP v1 200 v2 200
- tur: Ornament | Metal | model: Ornament | Metal | marka: API vermedi | durdurulmus: False
- baski teknigi: Sublimation
- yuz / baski alanlari: cift yuz secenegi (front, back) | v1 files ek ucret: default:None; back:None
- v2 placement fiyatlari USD: front:0.00; back:0.00
- v2 placement fiyatlari EUR: front:0.00; back:0.00
- v2 bolge fiyati (EUR europe / USD north_america), varyant sirasiyla: 20253: sublimation:7.50 / sublimation:8.27 | 20255: sublimation:7.50 / sublimation:8.27 | 20252: sublimation:7.50 / sublimation:8.27 | 20254: sublimation:7.50 / sublimation:8.27
- ort. uretim suresi (v1 avg_fulfillment_time): API vermedi | origin_country (v1): USA
- tasma payi: API vermedi

Olcu tablosu: API vermedi

| varyant | ad | size | inch | cm (hesap) | USD v1 | USD v2 | EUR v2 | stok | bolge v1 | printfile | px | dpi | fill |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20253 | Metal Ornaments (Pet Paw) | Pet Paw | API vermedi | API vermedi | 8.27 | sublimation:8.27 | sublimation:7.50 | True | US:in_stock | front=685; back=685 | front=1239x1200; back=1239x1200 | front=300; back=300 | front=cover; back=cover |
| 20255 | Metal Ornaments (Rectangle) | Rectangle | API vermedi | API vermedi | 8.27 | sublimation:8.27 | sublimation:7.50 | True | US:in_stock | front=686; back=686 | front=1275x975; back=1275x975 | front=300; back=300 | front=cover; back=cover |
| 20252 | Metal Ornaments (Scalloped) | Scalloped | API vermedi | API vermedi | 8.27 | sublimation:8.27 | sublimation:7.50 | True | US:in_stock | front=687; back=687 | front=1278x918; back=1278x918 | front=300; back=300 | front=cover; back=cover |
| 20254 | Metal Ornaments (Tag) | Tag | API vermedi | API vermedi | 8.27 | sublimation:8.27 | sublimation:7.50 | False | US:supplier_out_of_stock | front=688; back=688 | front=976x1576; back=976x1576 | front=300; back=300 | front=cover; back=cover |

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

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description, gorev_listesi | HTTP v1 200 v2 200
- tur: Ornament | Ceramic | model: Ornament | Ceramic | marka: API vermedi | durdurulmus: False
- baski teknigi: Sublimation
- yuz / baski alanlari: tek yuz (front) | v1 files ek ucret: default:None
- v2 placement fiyatlari USD: front:0.00
- v2 placement fiyatlari EUR: front:0.00
- v2 bolge fiyati (EUR europe / USD north_america), varyant sirasiyla: 22782: sublimation:5.75 / sublimation:6.34 | 22783: sublimation:5.75 / sublimation:6.15 | 22785: sublimation:5.75 / sublimation:6.15 | 22784: sublimation:5.75 / sublimation:6.15
- ort. uretim suresi (v1 avg_fulfillment_time): API vermedi | origin_country (v1): China
- tasma payi: API vermedi

Olcu tablosu: API vermedi

| varyant | ad | size | inch | cm (hesap) | USD v1 | USD v2 | EUR v2 | stok | bolge v1 | printfile | px | dpi | fill |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 22782 | Ceramic Ornament (Circle) | Circle | API vermedi | API vermedi | 6.34 | sublimation:6.34 | sublimation:5.75 | True | US:in_stock | front=845 | front=954x954 | front=300 | front=cover |
| 22783 | Ceramic Ornament (Heart) | Heart | API vermedi | API vermedi | 6.15 | sublimation:6.15 | sublimation:5.75 | True | US:in_stock | front=843 | front=978x972 | front=300 | front=cover |
| 22785 | Ceramic Ornament (Snowflake) | Snowflake | API vermedi | API vermedi | 6.15 | sublimation:6.15 | sublimation:5.75 | True | US:in_stock | front=838 | front=865x960 | front=300 | front=cover |
| 22784 | Ceramic Ornament (Star) | Star | API vermedi | API vermedi | 6.15 | sublimation:6.15 | sublimation:5.75 | True | US:in_stock | front=844 | front=1043x996 | front=300 | front=cover |

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

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description, gorev_listesi | HTTP v1 200 v2 200
- tur: Ornament | Ceramic | Double-Sided | model: Ornament | Ceramic | Double-Sided | marka: API vermedi | durdurulmus: False
- baski teknigi: Sublimation
- yuz / baski alanlari: tek yuz (front) | v1 files ek ucret: default:None
- v2 placement fiyatlari USD: front:0.00
- v2 placement fiyatlari EUR: front:0.00
- v2 bolge fiyati (EUR europe / USD north_america), varyant sirasiyla: 23133: sublimation:6.95 / sublimation:7.73 | 23144: sublimation:6.95 / sublimation:7.73 | 23155: sublimation:6.95 / sublimation:7.73 | 23151: sublimation:6.95 / sublimation:7.73
- ort. uretim suresi (v1 avg_fulfillment_time): API vermedi | origin_country (v1): China
- tasma payi: API vermedi

Olcu tablosu: API vermedi

| varyant | ad | size | inch | cm (hesap) | USD v1 | USD v2 | EUR v2 | stok | bolge v1 | printfile | px | dpi | fill |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 23133 | Ceramic Ornaments, 2-Side Print (1 pc / Circle) | Circle | API vermedi | API vermedi | 7.73 | sublimation:7.73 | sublimation:6.95 | True | US:in_stock | front=845 | front=954x954 | front=300 | front=cover |
| 23144 | Ceramic Ornaments, 2-Side Print (1 pc / Heart) | Heart | API vermedi | API vermedi | 7.73 | sublimation:7.73 | sublimation:6.95 | True | US:in_stock | front=843 | front=978x972 | front=300 | front=cover |
| 23155 | Ceramic Ornaments, 2-Side Print (1 pc / Snowflake) | Snowflake | API vermedi | API vermedi | 7.73 | sublimation:7.73 | sublimation:6.95 | True | US:in_stock | front=838 | front=865x960 | front=300 | front=cover |
| 23151 | Ceramic Ornaments, 2-Side Print (1 pc / Star) | Star | API vermedi | API vermedi | 7.73 | sublimation:7.73 | sublimation:6.95 | True | US:in_stock | front=844 | front=1043x996 | front=300 | front=cover |

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

- eslesme: v1.title, v1.type_name, v1.model, v1.description, v2.name, v2.description | HTTP v1 200 v2 200
- tur: Ornament | Christmas | Metal | model: Ornament | Christmas | Metal | marka: API vermedi | durdurulmus: False
- baski teknigi: Sublimation
- yuz / baski alanlari: cift yuz secenegi (front, back) | v1 files ek ucret: default:None; back:None
- v2 placement fiyatlari USD: front:0.00; back:0.00
- v2 placement fiyatlari EUR: front:0.00; back:0.00
- v2 bolge fiyati (EUR europe / USD north_america), varyant sirasiyla: 23138: sublimation:4.50 / sublimation:4.74 | 23135: sublimation:4.25 / sublimation:4.61 | 23136: sublimation:4.25 / sublimation:4.61 | 23137: sublimation:4.25 / sublimation:4.61
- ort. uretim suresi (v1 avg_fulfillment_time): API vermedi | origin_country (v1): USA
- tasma payi: API vermedi

Olcu tablosu: API vermedi

| varyant | ad | size | inch | cm (hesap) | USD v1 | USD v2 | EUR v2 | stok | bolge v1 | printfile | px | dpi | fill |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 23138 | Metal Christmas Ornament (White aluminum / Bell) | Bell | API vermedi | API vermedi | 4.74 | sublimation:4.74 | sublimation:4.50 | True | US:in_stock | front=869; back=869 | front=716x722; back=716x722 | front=200; back=200 | front=cover; back=cover |
| 23135 | Metal Christmas Ornament (White aluminum / Oval) | Oval | API vermedi | API vermedi | 4.61 | sublimation:4.61 | sublimation:4.25 | True | US:in_stock | front=866; back=866 | front=525x650; back=525x650 | front=200; back=200 | front=cover; back=cover |
| 23136 | Metal Christmas Ornament (White aluminum / Round) | Round | API vermedi | API vermedi | 4.61 | sublimation:4.61 | sublimation:4.25 | True | US:in_stock | front=868; back=868 | front=750x750; back=750x750 | front=200; back=200 | front=cover; back=cover |
| 23137 | Metal Christmas Ornament (White aluminum / Tree) | Tree | API vermedi | API vermedi | 4.61 | sublimation:4.61 | sublimation:4.25 | True | US:in_stock | front=867; back=867 | front=725x839; back=725x839 | front=200; back=200 | front=cover; back=cover |

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

- eslesme: v2.name, v2.description | HTTP v1 404 v2 200
- tur: API vermedi | model: API vermedi | marka: API vermedi | durdurulmus: API vermedi
- baski teknigi: UV printing
- yuz / baski alanlari: tek yuz (front) | v1 files ek ucret: API vermedi
- v2 placement fiyatlari USD: front:0.00
- v2 placement fiyatlari EUR: front:0.00
- v2 bolge fiyati (EUR europe / USD north_america), varyant sirasiyla: 
- ort. uretim suresi (v1 avg_fulfillment_time): API vermedi | origin_country (v1): API vermedi
- tasma payi: API vermedi

Olcu tablosu: API vermedi

| varyant | ad | size | inch | cm (hesap) | USD v1 | USD v2 | EUR v2 | stok | bolge v1 | printfile | px | dpi | fill |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

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

- eslesme: v2.name, v2.description | HTTP v1 404 v2 200
- tur: API vermedi | model: API vermedi | marka: API vermedi | durdurulmus: API vermedi
- baski teknigi: UV printing
- yuz / baski alanlari: tek yuz (front) | v1 files ek ucret: API vermedi
- v2 placement fiyatlari USD: front:0.00
- v2 placement fiyatlari EUR: front:0.00
- v2 bolge fiyati (EUR europe / USD north_america), varyant sirasiyla: 
- ort. uretim suresi (v1 avg_fulfillment_time): API vermedi | origin_country (v1): API vermedi
- tasma payi: API vermedi

Olcu tablosu: API vermedi

| varyant | ad | size | inch | cm (hesap) | USD v1 | USD v2 | EUR v2 | stok | bolge v1 | printfile | px | dpi | fill |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

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

