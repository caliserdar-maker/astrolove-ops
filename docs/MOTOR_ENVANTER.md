# MOTOR ENVANTER (3 Eki 2026, oturum motor)

Yontem: Drive aramasi + depo dallari (kisisel-v1 3a4cd64, siparis-baski-v1 cc39335, wp-katman 3f3c9d2, main 400e76f).
Kod yazilmadi, kosu acilmadi. Renk = edisyon eslemesi (siparis_dosyasi.RENK_ED):
MIDNIGHT_BLUE=blue, DEEP_BLACK=black, PURE_WHITE=pure_white, CHAMPAGNE_IVORY=modern, WARM_PARCHMENT=vintage.
Siparis boylari -> oran: 16x20=4x5, 18x24=3x4, 24x36=2x3, 11x14=11x14, A2=A.

## Tablo

| # | Kalem | Durum | Nerede / nereden gelir |
|---|---|---|---|
| 1 | Temiz yazisiz zemin, CIFTE OZEL (22 Eyl) | 21/390 (yalniz CANCER_LIBRA; blue yalniz 4x5) | Drive TEMP/KISISEL_PILOT/HAZIR/zemin_<ed>_<oran>.png (black/pure_white/modern/vintage x 5 oran + blue_4x5). Icinde CANCER_LIBRA kucuk sembolleri/sonsuz/yildiz VAR (ONAYLI.json zemin.korunan). Kaynak: Canva zemin tasarimlari DAHV2* (asagida). |
| 1b | Temiz zemin, GENEL (edisyon x boy, cift sembolsuz "medyan plate") | var: BLUE 16, BLACK 17, PURE_WHITE 16, MODERN 17, VINTAGE 12 (+VINTAGE_B/B1-3 sayfa 45-78 kagit) | Drive TEMP/SIPARIS_ISIM/PLATES/<ED>_<boy>.png. 5 siparis boyu her edisyonda VAR. Halka plate'te var (wp_bakir: "daire plate'te zaten bakir"). Ayrica <ED>_CANVA_<boy>.png kumesi (16'sar) onay bekliyor. |
| 2 | Buyuk cift sembolu (fusion), seffaf | 78/78 | Drive .../main_symbols/<a>_<b>_gold.png (25 Haz, 7-24 MB). Yalniz ALTIN; seffaflik ve cozunurluk OLCULMEDI. |
| 3 | Kucuk burc sembolu, seffaf | 12/12 altin + 12/12 duz | Drive .../zodiac_symbols_gold/<burc>_symbol_gold.png, .../zodiac_symbols_flat/<burc>.png |
| 4 | Burc adi altin plakasi (isim dokusu kaynagi) | 12/12 | Drive .../zodiac_names/<burc>_name_gold.png (ONAYLI: isim/tagline dokusu cancer_name_gold satir profili) |
| 5 | Sonsuzluk isareti | 1 (CANCER_LIBRA kirpimi) | HAZIR/infinity.png (1370x423). Ortak oge; edisyon renkleri ayri yok. |
| 6 | Halka / logo / marka tagline | var (tek renk) | Drive .../background_circle_logo_logo_tagline/{circle,logo,tagline}.png; bg yalniz deep_black_bg.jpg, midnight_blue_bg.jpg |
| 7 | Isim fontu | var | kisisel-v1 assets/fonts/Cinzel.ttf (v2.000, degisken wght 400-900, sha f4d83d34d1f6). Onayli: wght 500. C G S I O U + Turkce + J K B Z F P X W Q: EKSIK YOK |
| 8 | Tagline fontu | var | kisisel-v1 assets/fonts/EBGaramond-Italic.ttf (v1.003, wght 400-800, sha bba2c4499c93). Onayli: 400, punto 102 (11x14 ref.). Kucuk f c y w + Turkce: EKSIK YOK |
| 9 | Altin efekt | DOSYA (Canva efekti degil) | Isim/tagline: zodiac_names/<burc>_name_gold.png satir profili (ONAYLI.json). Semboller: Canva'dan altin olarak disa aktarilmis PNG'ler (#2-#4). |
| 10 | Bakir efekt (WARM_PARCHMENT) | KOD MODELI (dosya yok) | wp-katman dali scripts/medya_v1/wp_bakir.py + wp_kilit.json (kilitli, Serdar 1 Eki). Hedef bakir plate dairesinden olculur (~169/109/47). Tum ogeler bakir. |
| 11 | Canva: zemin tasarimlari (cift CANCER_LIBRA) | 21 kimlik | black 2x3 DAHV2qgHN94, 3x4 DAHV2u0ruS8, 4x5 DAHV2UGblFk, 11x14 DAHV2jPTFIw, A DAHV2uXYQ2o; pure_white 2x3 DAHV2gHBlrs, 3x4 DAHV2vionwg, 4x5 DAHV2oynqWE, 11x14 DAHV2uRbwHo, A DAHV2h1wM9Y; modern 2x3 DAHV2RA8xBo, 3x4 DAHV2eqQPpU, 4x5 DAHV2Za4uTY, 11x14 DAHV2WHmC6w, A DAHV2d-vzgs; vintage 2x3 DAHV2VWeVyk, 3x4 DAHV2SVR6Ow, 4x5 DAHV2WqQQdY, 11x14 DAHV2ZLe1po, A DAHV2TOT9_k; blue 4x5 DAHV2TI6AWU |
| 12 | Canva: plate tasarimlari (edisyon x oran) | 25 kimlik | BLUE 2x3 DAHWSk46GKg, 3x4 DAHWSXzDvAg, 4x5 DAHWSvV3KC0, 11x14 DAHWSjieBjk, A DAHWSssgVpM; BLACK 2x3 DAHWS6YMnHo, 3x4 DAHWSmpBbJs, 4x5 DAHWS4qJvqI, 11x14 DAHWS5t8100, A DAHWS3MZfgI; PURE_WHITE 2x3 DAHWSxeUhgE, 3x4 DAHWSWahOV0, 4x5 DAHWS0ksNfI, 11x14 DAHWS4yVKCw, A DAHWSwW8mPA; MODERN 2x3 DAHWSi-ShDE, 3x4 DAHWSopOFck, 4x5 DAHWSpAqHek, 11x14 DAHWSnI9sKE, A DAHWSsMkOMQ; VINTAGE 2x3 DAHWS6SHVmY, 3x4 DAHWSsHgJ04, 4x5 DAHWS-oaX6Q, 11x14 DAHWS5mtsKs, A DAHWS9oKngE (kaynak: Drive PLATES/CANVA_*.json) |
| 13 | Canva: 25 orijinal 78 sayfalik urun tasarimi | EKSIK | Kimlikler Drive/depoda yazili degil (KAYNAK_RAPOR_v1 yalniz esleme). Canva MCP olan oturumdan alinmali; bu oturumda Canva baglayicisi yok. |
| 14 | Yerlesim sabitleri (isim satiri, tagline) | var (5 oran, 5 edisyon) | kisisel-v1 scripts/kisisel/ORAN_SABITLERI.json + onayli/<ed>/KIRPIM.json, ONAYLI.json (SECENEK D kurallari) |
| 15 | Yerlesim sabitleri (buyuk sembol konum/olcek, kucuk sembol konumu) | EKSIK | Onayli 78 tasarimdan OLCULMEDI. Kaynak: POD_PRINT/<cift>/<renk>/<boy>.jpg - PLATES farki ile olculur. |
| 16 | Eski sistem referans ciktilari (yan yana) | var | Test 5 PDF klasoru Drive 1LnfDT9da1mXGlHKojdFkYsezhzJjb2n9; POD_PRINT/<cift>/<renk>/<boy>.jpg |

## Motoru engelleyen eksikler

1. Buyuk sembol yalniz ALTIN: black / pure_white / modern / vintage edisyonlarinda sembol rengi altindan farkliysa
   edisyon renkleri yok (vintage icin bakir kod modeli var, digerleri icin olcum yok). Once 5 edisyonda orijinal
   sembol rengi POD_PRINT'ten olculmeli.
2. main_symbols PNG'lerinin seffafligi, cozunurlugu ve halka/sembol icerigi dogrulanmadi (7-24 MB, 25 Haz 2026).
   Halka plate'te de varsa cift cizim riski.
3. Buyuk/kucuk sembol ve sonsuz icin oran bazli konum-olcek sabitleri yok (#15). Isim satiri sabitleri var.
4. Cifte ozel temiz zemin yalniz CANCER_LIBRA. 77 cift icin zemin = PLATES (genel) + katmanlar; PLATES "medyan"
   oldugu icin doku/iz kalintisi riski (PLATES_YEDEK_IZ_* klasorleri: 1 Eki'de iz duzeltmesi yapildi).
5. VINTAGE kagidi sayfa 45-78'de farkli (VINTAGE_B*): cift bazli plate secimi gerekli.
6. 25 orijinal Canva tasarim kimligi yok (#13); Canva'dan yeniden disa aktarim gerekirse Canva MCP'li oturum lazim.

Engellemeyen: fontlar (aksan destegi tam), burc sembolleri 12/12, burc adi altin plakalari 12/12, 5 siparis boyu
icin PLATES 5 edisyonda tam, bakir model kilitli.
