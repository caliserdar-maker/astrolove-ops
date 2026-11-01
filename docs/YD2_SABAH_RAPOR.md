# YD2 hazirlik: sabah raporu (gece 1-2 Kas 2026; Etsy'ye YAZMA YOK)

Durum: TASLAK (gece boyunca dolduruluyor). Her rakamin kaynagi parantezde: (olcum), (API okuma, kosu no), (kod okumasi), (tahmin).

## 1. F5 sonucu + onay paketi
- (dolacak)

## 2. Biten / suren / atlanan, gece varsayimlari
- (dolacak)

## 3. Serdar karar listesi (en fazla 6)
- (dolacak)

## 4. Kuru kosu
- Kosu 41342310370 (yd-yapi-kuru, main b6216a4e, poster_ref 4570143815; salt okuma): 78/78 PLAN, BLOK 0, hata 0 (PLAN.csv).
  Bu kosu 248 istek, bitiste kalan kota 2166 (kosu OZET.md, x-remaining-today).
- Yazim tahmini (kod okumasi, yd_yapi_yaz.py): ilan basina 7 (en kotu 23) -> 78 ilan 546 (en kotu 1794).
- (galeri yukleme tahmini, parca plani, 06:00 kota: dolacak)

## Ek A: ilan yapisi onerisi (B)
- Stil: 5 (Starlit, Timeless, First Page, Layers, Botanical). Kaynak: canli Style (513) degerleri, kuru kosu kapisi "5 Style bagi"
  78/78 PASS (API okuma, 41342310370); kod scripts/siparis_by/by_sku.py STILLER. "5 stil" notu dogrulandi.
- Varyasyon: Style (513) x Format (514: Digital File, Print) x Size (516, ad "Size") = 5 x 2 x 14 = 140 urun / ilan (kod okumasi,
  yd_yapi_kuru.py; kuru PLAN 78/78 urun_sonra 140).
  Etsy siniri (3. taraf ozet, resmi sayfa bu oturumdan acilamadi: developers.etsy.com ag izni yok): 3 varyasyon icin envanter PUT
  ?max_variations_supported=3; urun ust siniri 2500, *_on_property tum varyasyon ozelliklerini kapsiyorsa 400. Plan sku_on_property
  [513, 514, 516] (hepsini kapsar) -> sinir 400; 140 < 400 SIGIYOR.
  RISK: ayni ozet "ucuncu varyasyon ozel (custom) olamaz; ozel varyasyonlar 513 ve 514" diyor. 516 taksonomide "Custom3"
  (kupa-yd-oku 41180774733 YD_BOY.json). Etsy 513 + 514 + 516 ucluzunu kabul ediyor mu YAZIMLA dogrulanmadi; pilotta boy_kabul()
  kapisi olcer, FAIL -> otomatik geri alma (kod okumasi, yd_yapi_yaz.py). B plani (gece varsayimi, uygulanmadi): 2 varyasyon
  Style (513) x "Format & Size" (514, 28 deger: Digital File 5x7 ... Print A2) = 140 urun; SKU ve fiyat ayni kalir.
- Fiyat (kuru kosu canli kapisi: wall art 4570143815 ile FARK YOK; API okuma 41342310370; kaynak print_fiyat_v2.py HEDEF, Serdar 25-26 Eki):

  | Boy | Print | Digital File |
  |---|---|---|
  | 5x7 | 19.90 | 3.90 |
  | 8x10 | 24.90 | 3.90 |
  | A4 | 24.90 | 3.90 |
  | 11x14 | 29.90 | 3.90 |
  | 12x16 | 32.90 | 3.90 |
  | A3 | 32.90 | 3.90 |
  | 12x18 | 34.90 | 3.90 |
  | 16x20 | 39.90 | 3.90 |
  | 16x24 | 42.90 | 3.90 |
  | A2 | 42.90 | 3.90 |
  | 18x24 | 44.90 | 3.90 |
  | 20x30 | 54.90 | 3.90 |
  | 24x30 | 59.90 | 3.90 |
  | 24x36 | 64.90 | 3.90 |

- SKU: wall art deseni POD-<S1>_<S2>-<ED>-<BOY> / -DIGITAL (scripts/etsy/pod_sku.py). YD ayni mantik (Serdar 31 Eki 1a, by_sku.py):
  BY-<S1>_<S2>-<ST|TL|FP|LY|BO>-<BOY>[-DIGITAL]. Ornek: BY-CAN_LIB-ST-8x10, BY-CAN_LIB-ST-8x10-DIGITAL, BY-CAN_LIB-TL-24x36,
  BY-CAN_LIB-FP-A3-DIGITAL, BY-CAN_LIB-BO-5x7. Tekillik (olcum, yerel): 78 cift x 140 = 10920 SKU, 10920 tekil, en uzun 27 kr
  (BY-AQU_AQU-ST-11x14-DIGITAL; Etsy siniri 32), by_sku.coz 10920/10920 cozuldu.
- Kargo: tek profil 318080539024 "BY Print 8x10 Worldwide", yalniz 78 YD ilaninda (API okuma 41342310370, PROFIL_PLAN.json).
  Tum hedefler ucretsiz. Teslim (gun): US 3-8, EU 5-12, GB 5-10, AU 5-10, diger 7-21. Serdar karari AU 7-22: MEVCUT profilde AU
  hedefi 5-10 -> 7-22 degisikligi gerekir (Etsy yazimi, onay). Yeni profil gerekmez (profili baska ilan kullanmiyor). Profil adi
  "8x10" diyor (14 boy sonrasi yaniltici; ad degisikligi istege bagli, yazim).
- Baslik / aciklama: Ek C (CANCER_LIBRA taslagi). D1-D6 kaynak belgesi (claude/AstroLove_YD_ACIKLAMA_YENI_20261031.md) bu oturumda
  YOK (depo tum dallar + Drive arandi) -> gece varsayimi: canli CANCER_LIBRA metninden yeni yapiya uyarlandi.

## Ek B: galeri plani (C)
- Galeri 10 (Serdar): rank 1 = canli kapak (1. asama; DOKUNULMAZ), rank 2-10 = Y02-Y10 (9 dosya). Y01 YUKLENMEZ (gece varsayimi:
  1. asamada Y01 zaten rank 1; 3 ciftte setteki Y01 eski, canli rank 1 yeni).
- BULGU (kod okumasi): yd_kapak_yukle.py bugunku haliyle kapagi da yukler (rank 1) ve 1. asama sonrasi rank 1 yeni alt metinli
  ama kendi kaydinda olmadigi icin ilani "BLOK (elle)" yapar (zaten()); N_ESKI = 13. 2. asama icin "kapak koru" modu gerekir.
- (Y06-Y10 olcumu, F stil eslemesi: dolacak)
