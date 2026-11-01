# YD2 hazirlik: sabah raporu (gece 1-2 Kas 2026; Etsy'ye YAZMA YOK)

Durum: gece sonu (06:00 UTC kota olcumu bolum 4'te). Her rakamin kaynagi parantezde: (olcum), (API okuma, kosu no), (kod okumasi), (tahmin).

## 1. F5 sonucu + onay paketi
- Kosu 41342400404 (by-ornek3, dal yd-stil4 5fc66633, 2. iterasyon, son hak): **PASS** (Drive OLCUM.json sonuc PASS, FirstPage pass true, Layers_B pass true).
- Kapilar gevsetilmedi; 1. iterasyon (41339810943) ile ayni esikler. Eski / yeni yan yana (olcum, OLCUM.json):

  | Kapi | Esik | it.1 | it.2 |
  |---|---|---|---|
  | FirstPage kose tasma, 14 boy (px) | 0 | 14 boy 0 | 14 boy 0 |
  | FirstPage gercek doku oz-test 12x18 (1 px / 5 px tasma yakalanir) | > 0 / > 0 | 14 / 67 | 14 / 67 |
  | FirstPage gercek doku oz-test 8x10 | > 0 / > 0 | 9 / 45 | 9 / 45 |
  | Layers B 4500 alti eski piksel | 0 | 0 | 0 |
  | Layers B yatay cizgi (max) | <= 1,0 (oneri) | 0,88 | 0,88 |
  | Layers B kemer kesim (px) | 0 | 0 | 0 |
  | Layers B yerel dikis dE76 max | <= 2,3 (oneri) | 2,332 FAIL | 1,39 |
  | Layers B kenar gradyan p99 | <= 1,5 | 1,028 | 1,054 |
  | Layers B eklenen bantta oge (px) | 0 | - | 0 |

  Tek degisiklik: Layers B gecis rampasi 60 -> 120 px (commit 5fc66633). Bilgi (kapi degil): rampa bolgesi 0-20 px ile 60-80 px karolari arasi dE76 max 3,185 (OLCUM rampa_uclari_0_20_vs_60_80_bilgi).
- Paket: Drive ASTROLOVE/TEMP/YD_STIL4_ORNEK/20261101_193620 (klasor 1po8Sj6Ynwa_OPSOZLZrm0RUN_EujawI5):
  KONTAK_STIL4.jpg (her stil eski 8x10 | yeni 12x18) 1FZua7HAHhZQcRnaoCpTCZup_BlyQeDAf; FP_KOSE_YAKIN.jpg (eski 8x10 / yeni 8x10 / yeni 12x18,
  4 kose, 2x) 1LdP_dqAre25_KBPXcD0i1IdMrhCBRNIr; LB_4500_YAKIN_x2.jpg 1UiX4CDrM8yWSyl8exXTkruq4IneCK1ga; CIZGI_KESIT_Layers_B.png
  1lkmSQBrcJAhl7CibbD6MYPXVysX_kZFq; Layers_B_12x18.jpg 10uiiaH5aCgCXS9xEryMHQXZwMBAxYN4Q; OLCUM.json 1HAdCB75kjRkUwXBTEkO0lLVfK7PF5DBP.
  Timeless ve Botanical bu turda degismedi: docs/yd_stil4/F_ONAY_KONTAK_4STIL.jpg (95e84d1b).
- SINIR: paket gorselleri Drive'da; bu oturum buyuk Drive dosyasini indiremedi, gorsellere GOZLE BAKILMADI. Sonuc yalniz olcume dayanir;
  gorsel onay Serdar.

## 2. Biten / suren / atlanan, gece varsayimlari
- Biten:
  - A) F5 2. iterasyon PASS (yukarida).
  - B) Ilan yapisi onerisi (Ek A): stil, varyasyon, fiyat, SKU, metin taslagi, kargo.
  - C) Galeri girdileri (Ek B): Y01 yeri, 3 cift Y06-Y10 olcumu, stil esleme tablosu.
  - D) Kuru kosu 41342310370 78/78 PLAN (bolum 4).
  - E) 2. asama galeri kodu, dal yd-asama2 85a04f79 (KOSTURMA YOK): yd2 profili (rank 1 DOKUNMA, Y02-Y10, 12 eski CIKAR, Style 513 baglari,
    Size 516 = 14 boy kapisi, ara galeri <= 20). Sahte Etsy testi 14/14 PASS; regresyon v11 32/32, v11b 15/15, v11 paralel 19/19,
    v10_wf 7/7, eski78 55/55, pilot 37/37, yd_kapak 42/42, yd_liste rc 0; galeri_v10 55/58 (ayni FAIL main fff34005'te de var, bu
    degisiklikten degil).
  - yd-envanter-oku.yml: cikti klasoru girdisi + --immutable (main fff34005); 1. asama sonrasi envanter TEMP/YD_ENVANTER_20261101_ASAMA1_SONRASI.
  - G-OKU (sade kupa 12 ilan, salt okuma): kosu 41342604196, 529 PASS / 0 FAIL / 24 BILGI, 62 istek, kota 2165 -> 2104 (kosu ciktisi);
    Drive TEMP/SADE12_OKU/20261101_193646/OKU.csv (1LoiCONwAvvtfbgvVvo4XT9KYI3b4xMru).
- Atlanan / basarisiz:
  - CDN yedek (yd-kapak-yedek 41343915309) FAIL, "Girdi kapisi" adimi: kapi ad kurali YD_ENVANTER_<8 rakam>(_<6 rakam>), benim verdigim ad
    ..._ASAMA1_SONRASI. Hata benim (fff34005'te iki is akisinin ad kurali uyumsuz). Etsy istegi yok, Drive'a yazim yok.
    Yeniden okuma (~390 istek, 5 x 78; kod okumasi) kotadan yiyecegi icin ve sahte damgali kopya kaynagi bulandiracagi icin YAPILMADI.
    Sabah: yedek kapisina tek satir (YD_ENVANTER_[A-Za-z0-9_]+) ya da yeni envanter okumasi. 2. asama yazimindan ONCE yedek zorunlu.
  - yd2 liste kosusu (LISTE_<ilan>.csv, manifest dokunma_id): ALT.csv Drive kimligi bilinmiyor -> kosulmadi.
  - D1-D6 kaynak belgesi (claude/...): erisilemedi -> metin canli CANCER_LIBRA'dan uyarlandi.
- Gece varsayimlari (hepsi geri alinabilir, Etsy'ye yazim yok):
  1. Y01 2. asamada yuklenmez; rank 1 = 1. asamanin canli kapagi (DOKUNMA).
  2. F 12x18 stil gorselleri galeri gorseli degil, baski (Print) uretim ana dosyasi; galeride Y06-Y10 Style bagli kalir (Ek B tablo).
  3. Varyasyon B plani (Style x "Format & Size" 28 deger) yalniz yedek; ana plan 513 x 514 x 516.
  4. Baslik / aciklama: canli CANCER_LIBRA metninden yeni yapiya uyarlandi (D1-D6 yok).
  5. CDN yedegi zorlanmadi (yukarida).

## 3. Serdar karar listesi (en fazla 6)
1. Stil + varyasyon: 5 stil (Starlit, Timeless, First Page, Layers, Botanical) x Format x 14 boy = 140 urun. Layers icin uretimde Layers B mi?
   Risk: 3. ozel varyasyon (516) Etsy'de kabul edilmeyebilir (3. taraf ozet); pilotta boy_kabul olcer, FAIL -> otomatik geri alma.
2. Fiyat tablosu (Ek A; wall art 4570143815 ile birebir): onay.
3. SKU semasi BY-<S1>_<S2>-<ST|TL|FP|LY|BO>-<BOY>[-DIGITAL] (10920 tekil): onay.
4. Baslik / aciklama: docs/yd2/CANCER_LIBRA_METIN_TASLAK.txt (metin_kurali PASS): onay ya da D1-D6 belgesinin yeri.
5. Kargo: profil 318080539024'te AU 5-10 -> 7-22 (Etsy yazimi; profili yalniz 78 YD ilani kullaniyor). Profil adi "8x10" degissin mi?
6. Pilot baslatma (CANCER_LIBRA 4595350971): once CDN yedegi (kapi duzeltmesi) + ALT.csv kimligi + yd2 liste kosusu; sonra envanter ->
   galeri. Ayrica: SAGITTARIUS_SAGITTARIUS Y03 gorsel kontrolu (NCC 0,9082) ve "Serdar onayli 60 kart seti" kaynagi (dogrulanmadi).

## 4. Kuru kosu
- Kosu 41342310370 (yd-yapi-kuru, main b6216a4e, poster_ref 4570143815; salt okuma): 78/78 PLAN, BLOK 0, hata 0 (PLAN.csv).
  Bu kosu 248 istek, bitiste kalan kota 2166 (kosu OZET.md, x-remaining-today).
- Yazim tahmini (kod okumasi, yd_yapi_yaz.py): ilan basina 7 (en kotu 23) -> 78 ilan 546 (en kotu 1794).
- Galeri yukleme tahmini (kod okumasi, eski78_gorsel_yukle.py; 2. asama "kapak koru": 12 eski sil, 9 yukle Y02-Y10, bag, sira; kapak adimi YOK):
  - bugunku YD yolu (adim_plani, ara galeri okumali): ilan basina en az 75, en kotu 478 -> 78 ilan en az 5850, en kotu 37284.
    En iyi durumda bile gunluk kota (5000, son 24 saat) ASILIR.
  - yalin plan (galeri v11, Merkez 29 Eki karar 3): en az 29, en kotu 279 -> 78 ilan en az 2262, en kotu 21762.
  - yd2 profili yazildi (yd-asama2 85a04f79): sahte Etsy testinde ilan basina 34 istek (en kotu 291) -> 78 ilan 2652 (en kotu 22698)
    (olcum, sahte API sayaci; gercek Etsy yanitlariyla farkli olabilir).
- Toplam (en iyi durum, tahmin): envanter 546 + galeri (yd2) 2652 = 3198 istek -> tek gunde sigar. En kotu durum sigmaz; ilan basina
  kota kapisi (kalan - en kotu < 10 ise ilan baslamaz) kosuyu kendisi durdurur, ertesi gun kaldigi yerden.
- Parca plani (oneri): P0 pilot CANCER_LIBRA 4595350971 (envanter -> boy_kabul -> galeri); P1-P3 26'sar ilan (envanter once, galeri
  sonra; 30 Eki karari: galeri yeni yapidan once yuklenmez). Her parca once kuru / kontrol (salt okuma).

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
- 3 cift Y06-Y10 kontrolu (olcum, yd-kapak-qc mod olc kosu 41342783602; Drive QC OLCUM.json; kaynak = canli stil gorselleri yedegi
  TEMP/YD_KAPAK_V1_YEDEK/20261027_105540, 1. asama yalniz kapak + videoyu degistirdi, stil gorselleri ayni):
  poster bolgesi NCC (kart / ciftin canli stil gorseli), referans CANCER_LIBRA (Serdar onayli ornek):

  | Cift | Y06 Starlit | Y07 Timeless | Y08 First Page | Y09 Layers | Y10 Botanical | Y03 | Y05 |
  |---|---|---|---|---|---|---|---|
  | CANCER_LIBRA (referans) | 0.9576 | 0.9251 | 0.9514 | 0.9787 | 0.9554 | 0.9791 | 0.9421 |
  | ARIES_LEO | 0.9561 | 0.9219 | 0.9504 | 0.9815 | 0.9579 | 0.9766 | 0.9315 |
  | CAPRICORN_SAGITTARIUS | 0.9629 | 0.9331 | 0.9560 | 0.9811 | 0.9624 | 0.9784 | 0.9380 |
  | SAGITTARIUS_SAGITTARIUS | 0.9550 | 0.9253 | 0.9506 | 0.9793 | 0.9569 | 0.9082 | 0.9358 |

  Y06-Y10: 3 cift referansla kart basina +-0,01 icinde, kutu sapmasi 0-1 px -> eski poster dosyasi izi yok; poster ciftin kendi canli
  stil gorseliyle eslesiyor (bu olcum yanlis CIFTIN posterini ayirt etmeyi ayrica olcmedi: bilinmiyor). SAPMA: SAGITTARIUS_SAGITTARIUS
  Y03 kutu sapmasi 72 px, NCC 0,9082 (referans 0,9791) -> galeriye girecek kart; gorsel onayi Serdar (uretim yapilmadi).
- YD envanter / yedek: yd-envanter-oku.yml artik YENI klasore --immutable yazar (main fff34005; 20261026 yazilmaz). 1. asama sonrasi envanter
  TEMP/YD_ENVANTER_20261101_ASAMA1_SONRASI. CDN yedegi FAIL (bolum 2, ad kurali).
- Stil esleme (gece varsayimi 2): Style (513) degeri -> galeri sirasi -> kart; baski ana dosyasi = by_stil4 12x18 (14 boy turetilir):

  | Style | Galeri sira | Kart | Baski ana dosyasi (F) |
  |---|---|---|---|
  | Starlit | 6 | Y06 | mevcut (F disi) |
  | Timeless | 7 | Y07 | Timeless_12x18 |
  | First Page | 8 | Y08 | FirstPage_12x18 (F5) |
  | Layers | 9 | Y09 | Layers_B_12x18 (F5; karar 1) |
  | Botanical | 10 | Y10 | Botanical_12x18 |
