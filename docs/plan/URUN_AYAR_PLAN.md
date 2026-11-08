# URUN AYAR PLANI (Oneri 1, 1. asama: YALNIZ PLAN)

Dayanak: Serdar 8 Kas sistem onerileri "hepsi" + 8 Kas gece "Ok" (oneri 1 ilk sirada; KARARLAR_20261108_5).
Kod yok, Etsy istegi yok, Actions kosusu yok. Butun dosya:satir atiflari **main b82f2ec6812712f2a43e021366dbd73677eca895**
(b82f2ec) icindir. 89842ce ile farki yalniz CLAUDE.md; scripts/ ve .github/ ayni.
Bagimsiz inceleme tur 1 (8 Kas): 3 YUKSEK, 6 ORTA, 3 DUSUK; 11'i islendi (B7, B8, 1.3 eksik yazicilar, B4, kapi yerleri, PATCH kurali,
sayim, KALITE 4/5 adimlari, atiflar, sema); 1'i reddedildi ("premium canli EN'de izinli": CLAUDE.md:72-73 izinli DEGIL diyor).
Tur 2 (son tur, CLAUDE.md:218): yeni YUKSEK yok; 4 ORTA + 2 DUSUK islendi (yayin adimi PATCH yolu, free shipping yasaginin urune ozgu
olmasi, kapi yeri _call / post_file, ornament_kargo iki izin sinifi, Ag._tek kapilari, eksik kapi sayimi).
Kaynak turleri: [kod] depodaki satir, [olcum] kosu ya da kayit, [gorev] Merkez gorev metni (8 Kas), [hesap] koddan sayim, [tahmin].
Duzeltme 1: 8 Kas gece, Merkez gorevi; D1-D5 (Serdar 8 Kas gece "Ikisi de evet"). Atiflar yine main b82f2ec (degismedi) ve origin/gorev-g.
Degisenler: D1 5. bolum 5.1 yeniden (urun sayisi = carpim, secenek tablosu), B7 duzeltildi, B9 / B10 yeni, S1 onerisi; D2 O1 yeniden
(7. bolum O1 satiri + 7.1, adim 1-2 bagimliligi, S6); D3 B8 / metin.en / 3. bolum (2) / 4. bolum EN satiri / S13 (canli 78/78 PASS,
eski olan depo dosyasi); D4 S14, 3. bolum (2), adim 7, B6 ve 1.2 sade satiri (ornament yayini panelde Serdar'da; sade kodla --confirm SADE_YAYIN, olgu olarak yazildi); D5 2.2 GPSR ve S3 onerisi.
Inceleme (Duzeltme 1) tur 1: 13 bulgu (1 YUKSEK, 5 ORTA, 7 DUSUK), 13'u islendi, 0 reddedildi (5.1-1 kod isi + 5.1-1b; kupa liste yolu;
batch kosularinin ayrimi; olc 42486805159 zaten kostu, adim 2 O1'e bagli degil; 2.1 "olc ile" -> O1(1); sade hukmu kaldirildi; atiflar; B10 tarih;
tam carpim varsayimi; 2b CSV notu; S13 gerekcesi; bicim).
Inceleme (Duzeltme 1) tur 2 (son tur, CLAUDE.md:218): yeni YUKSEK yok; 8 bulgu (2 ORTA, 6 DUSUK) islendi, 0 reddedildi (nitelik degeri
O1(1) disinda; adim 1 kaynak; atiflar :148, :464-465, b5060ee :3-4; 5.1-1b sayimi; 5.1-3 fiyat kisiti; B9 ifadesi; "duzeltme oncesi" etiketi).
Yeni kaynak etiketleri: [kaynak dosya, canli degil], [dogrulanmadi], [kod yorumu, olculmedi], [gorev] Merkez, Drive kontrol JSON'u; Denetim dogrulamadi.

---

## 1. Envanter

### 1.1 Ornament yazicilari (tam)

| Betik / uc | Yazdigi alanlar | Degerin kaynagi | dosya:satir |
|---|---|---|---|
| ornament_taslak createDraftListing | quantity, title, description, price, who_made, when_made, is_supply, taxonomy_id, type, shipping_profile_id, return_policy_id, readiness_state_id, shop_section_id, tags, materials, should_auto_renew, production_partner_ids | price = sabit FIYAT 29.90; kimlikler ORN_ETSY_AYAR.json; metin ORNAMENT78_METIN.csv; STOK, MALZEME sabit | scripts/etsy/ornament_taslak.py:482-486 (FIYAT :44, STOK :48, MALZEME :49, AYAR okuma :63-67, metin :242-249) |
| ornament_taslak envanter PUT | 5 Style urunu: sku, price, quantity, readiness_state_id | FIYAT sabit, P_STYLE 513 sabit, STILLER sabit, readiness ayardan | ornament_taslak.py:508-513 (P_STYLE :38, STILLER :40-41) |
| ornament_taslak gorsel | 11 gorsel, rank, alt_text | GALERI sabit liste, alt metin CSV | ornament_taslak.py:519-524 (GALERI :42) |
| ornament_taslak video | 1 video | dosya | ornament_taslak.py:540 |
| ornament_taslak variation-images | Style -> gorsel 7-11 | STILLER sira sabit | ornament_taslak.py:552-553 |
| ornament_taslak personalization | 3 soru | CSV (soru1-3, talimat) | ornament_taslak.py:556 (sorular metin_kontrol :257-262) |
| ornament_taslak properties | Material, Indoor/Outdoor, Season | ORN_ETSY_AYAR.json "nitelik" | ornament_taslak.py:559-563 (NIT :401) |
| ornament_taslak kur (magaza) | readiness tanimi, bolum, kargo profili + 6 hedef | HAZIRLIK, BOLUM_AD, PROFIL_AD, HEDEF sabit | ornament_taslak.py:183, :196, :210, :229 (sabitler :51-56) |
| ornament_galeri9 | 14 gorsel yukleme, eski gorsel/video silme, variation-images, video, acil PATCH | GALERI sabit, alt metin fonksiyonu | scripts/etsy/ornament_galeri9.py:38-39, :62-75; izin sinifi :133; modlar yaz :216 (yazim :265, :305, :333, :348-349, :364, :375, :392, :397), sira :448 (:492, :555, :565), yeniden :607, tasi :945 (yazimlar :1063'e kadar) |
| ornament_ru_olcu | translations/ru (title, description); properties W/H/D | ORN78_RU.csv (sha sabit :30), ORN_OLCU.json (sha sabit :31) | scripts/etsy/ornament_ru_olcu.py:227, :243 |
| ornament_kargo | yeni kargo profili + ulke hedefleri; envanter fiyat PUT | YENI_FIYAT 19.90, PROFIL_AD, ABD/DIGER ucret sabit, kargo JSON | scripts/etsy/ornament_kargo.py:40-46, :350, :368, :467 |

### 1.2 Diger taslak yazicilari (tam)

| Betik | Yazdigi alanlar | Degerin kaynagi | dosya:satir |
|---|---|---|---|
| kupa_taslak createDraftListing | ornament ile ayni alan seti | TAXONOMY, READINESS, PARTNER, IADE_ID, BOLUM_ID, PROFIL_ID sabit; fiyat BOYLAR sabit | scripts/etsy/kupa_taslak.py:481-485 (sabitler :246-251, BOYLAR :260) |
| kupa_taslak envanter / gorsel / video / varimg / kisisel / nitelik | 8 stil x 2 boy; 14 gorsel; nitelik | STILLER, BOYLAR, NITELIK sabit | kupa_taslak.py:510, :521, :529, :542, :548, :553 (NITELIK :268) |
| by78_taslak createDraftListing (KAPALI: by78_taslak.py:111-115 SystemExit, Serdar 3 Kas) | ayni alan seti + is_personalizable | SHIP, RET, TAX, PARTNER sabit; readiness referans ilandan (REF) | scripts/etsy/by78_taslak.py:246-250 (sabitler :33-36, :40) |
| by78_taslak devami | envanter, gorsel, varimg, kisisel, nitelik | FORMATS, STYLES sabit | by78_taslak.py:280, :299, :312, :317, :326 |
| pod_listing_create (is akisi KAPALI: workflow-kapat-pod.yml:2) | createDraftListing, gorsel, video, PATCH, nitelik, RU, kisisel, envanter, varimg | kimlikler magazadan ADA gore bulunur (discover :345-371); fiyat pod_prices.csv; MATERIALS, TITLE_RU sabit | scripts/etsy/pod_listing_create.py:553-556, :575, :589, :599, :605, :611, :613-615, :617, :622, :641 (sabitler :118, :125, :133-136) |
| sade_taslak (yalniz origin/gorev-g dalinda, main'de YOK) | createDraftListing; kimlikler SABLON ilandan kopyalanir; state active PATCH yalniz --confirm SADE_YAYIN ile (:600-608, :743) | SABLON 4607613712 canli ilan | gorev-g:scripts/kupa/sade_taslak.py:38, :61, :425-428, :606; Serdar 1 Kas karariyla --confirm SADE_YAYIN (:743) verildiginde tum kontroller PASS ise state active yapar (:600-608; yayin_izni kapisi :242-247) |

Sabit kodlanmis kimlikler (ayri liste):

| Tur | Deger | Yer |
|---|---|---|
| kargo | 319194887351 (eski "Ornament Free Worldwide") | docs/ornament/ORN_ETSY_AYAR.json:7 |
| kargo | 318301958420 | kupa_taslak.py:251, kupa_kargo_ekle.py:25, kupa_kargo_ucretli.py:19, kupa_profil.py:17 |
| kargo | 314711751541 | by78_taslak.py:35, by78_kargo_sku_aciklama.py:32 (ESKI_PROFIL), pod_5x7_yaz.py:10 (aciklama metni) |
| uretim ortagi | 5817638 (United States) | ORN_ETSY_AYAR.json:13, kupa_taslak.py:248, by78_taslak.py:35 |
| iade | 1513990287785 | ORN_ETSY_AYAR.json:11, kupa_taslak.py:249, by78_taslak.py:35 |
| bolum | 61319672 / 60980873 / 60895624 / 60204164 | ORN_ETSY_AYAR.json:9; kupa_taslak.py:250, kupa_fiyat.py:24, kupa_galeri78.py:63, kupa_ru.py:28; by78_taslak.py:34; pod_crosslink.py:38 |
| taxonomy | 1857 / 1062 / 121 | ORN_ETSY_AYAR.json:3, ornament_ru_olcu.py:33; kupa_taslak.py:246; by78_taslak.py:35 |
| readiness | 1530862376601 / 1517641240112 | ORN_ETSY_AYAR.json:5; kupa_taslak.py:247 |
| fiyat | 29.90 / 19.90 / 24.00-29.00 / 5.00-29.00 | ornament_taslak.py:44; ornament_kargo.py:40; kupa_taslak.py:260, kupa_fiyat.py:28; by78_taslak.py:40 |
| Style property | 513 | ornament_taslak.py:38, kupa_galeri78.py:65, by78_* (her biri) |

### 1.3 5.1 / 5.2'nin dokunacagi yazicilar (poster, 1st Anniversary, kupa)

| Betik | Yazdigi uc (dosya:satir) | Kaynak / sabit |
|---|---|---|
| yd_yapi_yaz | envanter PUT ?max_variations_supported=3 :254; variation-images :229; kargo hedef PUT :411 | onayli KURU plan (plan_damga, PLAN.csv) :1-4, :123-148 |
| yd_talimat_yaz | personalization :126 | ISTEK_ILAN 5 :30 |
| yd_kapak_yukle (kapak78) | gorsel; yazim eski78_gorsel_yukle.bir_ilan uzerinden | scripts/kapak78/yd_kapak_yukle.py:7, :10 (kota kapisi :268) |
| galeri_v10_yukle / galeri_v11_yukle (kapak78, poster galeri girisleri) | gorsel, sira, bag (eski78_gorsel_yukle yukle_guvenli) | scripts/kapak78/galeri_v10_yukle.py:4, galeri_v11_yukle.py:4 |
| ilan_yapi_v2 (scripts/pod, poster 3 menu yapisi) | envanter :510, variation-images :521 / :532, PATCH description :537 | urun siniri :159-160 / :299-302 |
| pod_v11_yayin (scripts/pod) | gorsel :193 / :201, sil :221, video :226, video sil :235 | |
| wp_zip_degistir (dijital dosya) | dosya sil :97, yukle :108 | |
| MAIN'DE OLMAYAN: yd2_galeri_yukle (yalniz origin/yd-asama2), yd_asama1 (yalniz origin/yd-asama1) | main'deki .github/workflows/yd2-galeri.yml:218 ve yd-asama1-plan.yml:34, :76 bu betikleri cagirir | 5.1 icin hangi dalin esas olacagi S12 |
| kupa_fiyat | variation-images :259 | BOLUM :24, ESKI_EK fiyat :28 |
| kupa_galeri78 | variation-images :699, gorsel sil/yukle :736/:758, video :778/:825, PATCH :847, personalization :859 | BOLUM :63, P_STYLE :65 |
| kupa_kargo_ekle / kupa_kargo_ucretli / kupa_profil | kargo hedef :169 / :132 / :118 | PID :25 |
| kupa_ru | translations/ru :111 | BOLUM_ID :28 |
| pod_inventory_update | envanter :237, PATCH :250, varimg :275 | EXPECT_IMAGES :43 |
| pod_5x7_yaz | varimg :313, envanter :360, PATCH :371, RU :380, kargo hedef :430 | |
| poster_metin_yaz | PATCH :141, RU :157 | ISTEK_ILAN :45 |
| pod_desc_update / pod_desc_set / pod_desc_batch / pod_seo_update / pod_listing_update / pod_paper_update / pod_crosslink / pod_partner_bagla / pod_publish | PATCH :131 / :137 / :107 / :172 / :127 / :248 / :189 / :146 / :127; RU :136 (desc_update), :254 (paper), :192 (crosslink) | |
| pod_galeri_tamset / pod_hero_swap / pod_gorsel_sira / pod_kapak_ekle / pod_media_add / pod_rank_fix | gorsel ve video yukleme/silme (tamset :259/:269, :138/:140; hero :75/:78/:206/:209; sira :99/:160; kapak :95; media :86/:234; rank :124) | |
| eski78_gorsel_yukle (ortak yukle_guvenli) / eski78_cerceve / kapak_yukle_78 / galeri_ci11 | gorsel :185, varimg :479, sil :634 / envanter :211, PATCH :231 / gorsel :390, varimg :453, sil :467 / varimg :254, sil :259 | |
| by78_kapak_* / by78_vitrin / by78_video_etsy / by78_kargo_sku_aciklama | PATCH (bordo :100, degis :102, video :121, vitrin :108, video_etsy :96, kargo_sku :358), gorsel, video, kargo profili :156/:173, envanter :342 | REF 4570143815 (by78_kapak_bordo.py:27 vb.) |

Depodaki diger Etsy yazicilari (yalniz dosya adi; yazma cagrisi taramasi, satirsiz). Tarama: test_ ve _selftest disindaki .py dosyalarinda listings / shipping / sections / readiness / policies yoluna post / put / patch / put_json / post_json / post_file / delete / tek_post ya da requests yazma cagrisi: toplam 104 dosya; yukaridaki tablolarda olmayan 61: arsiv/etsy/by78_yayinla.py, arsiv/etsy/by_taslak_ac.py, arsiv/etsy/kupa_eski_sil.py, scripts/etsy/beyan_marka_yaz.py, scripts/etsy/burc_gift_yaz.py, scripts/etsy/by_baski_ekle.py, scripts/etsy/by_baski_kaldir.py, scripts/etsy/by_taslak_hazirlik.py, scripts/etsy/cl_galeri_degistir.py, scripts/etsy/digital_desc_batch.py, scripts/etsy/digital_file_add.py, scripts/etsy/eski78_pilot_yukle.py, scripts/etsy/gorsel02_degistir.py, scripts/etsy/gorsel19_ekle.py, scripts/etsy/hazirlik_yaz.py, scripts/etsy/kargo_kanada.py, scripts/etsy/kart_sil.py, scripts/etsy/pod_cover_from_video.py, scripts/etsy/pod_cover_gold_b_batch.py, scripts/etsy/pod_cover_replace_file.py, scripts/etsy/pod_master_locked_batch.py, scripts/etsy/pod_ru_tags.py, scripts/etsy/profil_ucretsiz.py, scripts/etsy/pw_ru_fill.py, scripts/etsy/seo51_yaz.py, scripts/etsy/seo_accuracy_apply.py, scripts/etsy/seo_tag_pilot_107_apply.py, scripts/etsy/tek_ilan_adim.py, scripts/etsy/tur_deneme.py, scripts/etsy/video_geri_al.py, scripts/etsy/video_yukle_78.py, scripts/etsy/wp_description_78_apply.py, scripts/etsy/wp_gallery_refresh.py, scripts/etsy/wp_ilan_yayinla.py, scripts/etsy/wp_image_replace.py, scripts/etsy/wp_listing_update.py, scripts/etsy/wp_media_upload.py, scripts/etsy/wp_saat80_etsy.py, scripts/etsy/xsell_links.py, scripts/kapak78/w05_degistir.py, scripts/pod/ayar77_yaz.py, scripts/pod/dijital_fiyat_390.py, scripts/pod/dijital_secenek_tek.py, scripts/pod/fiyat_b.py, scripts/pod/galeri_genel.py, scripts/pod/galeri_tek.py, scripts/pod/ilan_yapi_v2.py, scripts/pod/pod_3var_hazirlik.py, scripts/pod/pod_boy_15.py, scripts/pod/pod_fiyat_2999.py, scripts/pod/pod_galeri_duzen.py, scripts/pod/pod_galeri_toplu.py, scripts/pod/pod_pilot_15.py, scripts/pod/pod_rank3_duzelt.py, scripts/pod/pod_rank3_onar.py, scripts/pod/pod_rank3_uygula.py, scripts/pod/pod_v11_yayin.py, scripts/pod/pod_v11_yayin_toplu.py, scripts/pod/print_fiyat_v2.py, scripts/pod/size_sira.py, scripts/pod/yayilim_78.py.

### 1.4 Envanterden bulgular

- B1 [kod] Yeni ilan acan dort taslak yazicisi (ornament_taslak, kupa_taslak, by78_taslak, pod_listing_create) ayni 17 alanli createDraftListing govdesini dort ayri kopyada tutuyor; kimliklerin kaynagi dort farkli: JSON (ornament), betik sabiti (kupa, by78), magazada ada gore arama (pod), sablon ilandan kopya (sade). Ortak kapi yok.
- B2 [kod] ORN_ETSY_AYAR.json'u yalniz ornament_taslak okuyor (ornament_taslak.py:37, :63-67). Sonraki duzeltmeler JSON'a geri yazilmadi: fiyat ornament_kargo.py:40 (19.90) ama ornament_taslak.py:44 (29.90); kargo yeni profil ornament_kargo.py:41 ama JSON :7 eski profil; ortak JSON :13 5817638 ama ORN_YAYIN_SPEC.json:7 5870733. Gorev metnindeki uc fark kodla dogrulandi.
- B3 [kod] ORN_ETSY_AYAR.json:8 "Ornament Free Worldwide ... ucretsiz" diyor; ORN_YAYIN_SPEC.json:15 "free shipping" desenini yasakliyor. Ayar dosyasinda acik metin alani kural disina dusmus.
- B4 [kod] pod_listing_create.py:118 MATERIALS "Hahnemuhle Photo Rag 308 gsm cotton paper" ve :125 TITLE_RU "жикле" iceriyor (CLAUDE.md:69-71 KAGIT kurali ile celisir). createDraftListing (:575) ortak istemciden gecer ama metin kapisi varsayilan "UYARI" modunda (scripts/etsy/etsy_common.py:255, :356): EN materials istegi GONDERILIR. RU yazimi (:613-615) ru_yazim_kapisi'na takilir (RU_YASAK etsy_common.py:182, kapi :227), istek gitmez. Gercek risk: yasak kagit metniyle acilmis yarim taslak. Is akisi kapali (.github/workflows/workflow-kapat-pod.yml:2, Serdar 22 Eki); yeniden acilirsa risk gercek. Bu plan duzeltmez; ayri is (S10).
- B5 [kod] Iki tasarim zaten "kilitli plan" deseninde: yd_yapi_yaz yalniz onayli KURU plana gore yazar (yd_yapi_yaz.py:1-4, :123-148); ornament_ru_olcu RU ve olcu dosyasini sha ile kilitler (ornament_ru_olcu.py:30-31, :62-63, :94-95). Ayar kilidi bu deseni genellestirir; yeni desen icat edilmez.
- B6 [kod] sade_taslak (sign mug) main'de yok, yalniz origin/gorev-g dalinda; kimlikleri canli SABLON ilandan kopyalar (gorev-g:scripts/kupa/sade_taslak.py:38, :61). 5.2 icin bu kodun main'e alinip alinmayacagi karar gerektirir (S7). Olgu (Duzeltme 1): sade_taslak.py:600-608, Serdar 1 Kas karariyla, --confirm SADE_YAYIN (:743) verildiginde tum kontroller PASS ise state active yapar (yayin_izni kapisi :242-247).
- B7 [kod + olcum] (Duzeltme 1) Tam carpim varsayimiyla tek ilandaki urun sayisi menu deger sayilarinin CARPIMIDIR: canli a2 yolu her satir icin her renk urununu
  uretir (scripts/pod/ilan_yapi_v2.py:144-156 [kod]; tam carpim yapi CSV'sinin 6 x 13 = 78 satir tam olmasindan gelir); "Etsy tam carpim ister" yalniz kod yorumu (ilan_yapi_v2.py:232) [kod yorumu, olculmedi].
  Sinir: SKU ve fiyat uc menuye bagliyken 400 [olcum] (docs/REFERANS_ILAN_CL.md:49, 27 Eyl ret "Total products 576 exceeds maximum
  allowed 400"). 2500 [dogrulanmadi]: olcum yok, yalniz kod yorumu (scripts/etsy/pod_sku.py:49). En fazla 3 menu (max_variations_supported=3,
  yd_yapi_yaz.py:56); 4 menu olculmedi [dogrulanmadi]. 3 menude on_property yalniz 0, 1 ya da 3 id (REFERANS_ILAN_CL.md:49).
- B8 [olcum, yerel; kaynak dosya, canli degil] data/pod/ORNAMENT78_METIN.csv (sha256 c8d18aa9a2462c0eeccf6fbcfc171f35a46b19e01831521e459db37e0f0129a5):
  aciklama sutununda 78/78 "free shipping", SPEC zorunlu kargo cumlesi 0/78 (ORN_YAYIN_SPEC.json:14-15); ORN_ETSY_AYAR.json:8 de "Free Worldwide"
  der (B3). Canli durum farkli (Duzeltme 1, D3): yayina-hazir kontrol kosusu 42487964917 (8 Kas 14:04 UTC) 78/78 ornament ilanda aciklama
  zorunlu cumlesi + yasak desen + kargo profili PASS (aciklama kontrolu yayina_hazir.py:301-305) [gorev] Merkez, Drive kontrol JSON'u; Denetim dogrulamadi. Eski olan depo dosyalaridir.
  Not: CSV kaynak dosyadir, canli degil. Metin kapisi bunu durdurmaz ("free shipping" METIN_KESIN'de yok, etsy_common.py:256-270). Tek gecis
  (yeni ilan) bugunku CSV'den yazilirsa yayina_hazir'da FAIL veren ilan acar.
- B9 [kod] ilan_yapi_v2.py:159-160'taki 2500 bekcisi canli a2 yolunda, SKU uc menuye bagliyken (:153-156) calisir; olculen 400 ile celisir
  (401-2500 urunlu plan bekciden gecer, Etsy reddeder). ilan_yapi_v2.py:298-302 "mode 3" blogu hic calismaz (mode "3" :229-230'da doner); "3x" yolu (:231) 400 bekcisine girmez; ikisi de kaynak degil.
- B10 [kaynak dosya, canli degil] Poster urun sayisi kaynaklarda celisik (tarih sirasiyla): REFERANS_ILAN_CL.md:9 (27 Eyl) 6 format x 5 renk x
  13 boy = 390; pod_5x7_yaz.py:9 (30 Eki, daha yeni) geri-al yedegi "130 urun" (= 2 x 5 x 13) ve :7 "5x7 x 10" ekler: 130 + 10 = 140 [hesap];
  yd_yapi_kuru.py:7, :61 (31 Eki) poster Format adlarini "Digital File", "Print" (2 deger) sayar. Iki taban: A = 390, B = 2 x 5 x 14 = 140
  (B daha yeni kaynak). Canli sayi O1(2)'ye baglidir.

## 2. Sema onerisi

Yer ve ad: `docs/urun/<URUN>/URUN_AYAR.json` (ornek `docs/urun/ornament78/URUN_AYAR.json`), tek dosya, urun basina. Kilit
sha'lari ve onay sozu ayri (2.3). JSON, Python standart kutuphanesiyle okunur (yeni bagimlilik yok).

### 2.1 Alanlar (Z = zorunlu, bos ise kapi DUR; S = secmeli, yoksa acikca null)

| Alan | Z/S | Tip | Ornek (ornament78) | Ornegin kaynagi |
|---|---|---|---|---|
| urun | Z | str | "ornament78" | ORN_YAYIN_SPEC.json:2 |
| taxonomy_id | Z | int | 1857 | ornament_ru_olcu.py:33 [kod]; ORN_YAYIN_SPEC'te yok |
| readiness_state_id | Z | int | O1(1) ile okunacak (depo karsiligi ORN_ETSY_AYAR.json [kaynak dosya, canli degil]) | ORN_YAYIN_SPEC'te yok, ayar dosyasindaki deger kullanilmaz (gorev) |
| who_made / when_made / is_supply / type | Z | str | i_did / made_to_order / false / physical | ornament_taslak.py:482-483 [kod] |
| fiyat | Z | number veya {menu_kombinasyonu: number} + price_on_property | 19.90 (ornament tek fiyat); kupada Style x Size (kupa_taslak.py:510 price_on_property [Style, Size]) | ORN_YAYIN_SPEC.json:9 |
| kargo.shipping_profile_id | Z | int | 319230731837 | ORN_YAYIN_SPEC.json:5 |
| kargo.ozet | S | str | (yasak desen taramasindan gecer) | B3 |
| uretim_ortagi.id / .konum | Z | int / str | 5870733 / "Latvia" | ORN_YAYIN_SPEC.json:7-8 (olc 42486805159) |
| iade.return_policy_id | Z | int | O1(1) ile okunacak (depo karsiligi ORN_ETSY_AYAR.json [kaynak dosya, canli degil]) | ORN_YAYIN_SPEC'te yok |
| bolum.shop_section_id | Z | int | O1(1) ile okunacak (depo karsiligi ORN_ETSY_AYAR.json [kaynak dosya, canli degil]) | ORN_YAYIN_SPEC'te yok |
| kisisellestirme | Z | {acik: bool, sorular: [...]} | acik true, 3 soru | ORN_YAYIN_SPEC.json:10; sorular METIN CSV |
| varyasyon | Z | {property_id, menu: [{ad, sku_kodu, gorsel_sira}]} | Style 513, 5 stil | ornament_taslak.py:38-41 [kod] |
| envanter | Z | {stok, fiyat_on_property, sku_on_property} | 999, [], [513] | ornament_taslak.py:48, :512-513 [kod] |
| olcu / nitelikler | Z | [{property_id, value_ids, values, scale_id}] | W/H/D 2.99/2.99/0.1 in + Material/Indoor/Season | ORN_YAYIN_SPEC.json:16-20; ORN_OLCU.json; malzeme nitelik DEGERLERI olculmedi: O1(1)'e ilan basina properties GET eklenirse +78 istek [hesap] (yayina_hazir olc yalniz alan adi / turu yazar, :477) |
| metin.en | Z | {csv, sha256, anahtar} | CSV canlidan guncellendikten sonra sha (S13; bugunku CSV c8d18aa9... canliyi gostermez, B8) | ornament_taslak.py:243 [kod]; sha yerel sha256sum [olcum] |
| metin.ru | Z (RU yaziliyorsa) | {csv, sha256, anahtar} | ORN78_RU.csv, 39843f4a... | ORN_YAYIN_SPEC.json:25 |
| baslik / etiketler | Z | metin CSV'den; 140 kr, 13 etiket, <=20 kr | | ornament_taslak.py:267-270 [kod] |
| aciklama_zorunlu / aciklama_yasak | Z | [str] / [regex] | [ SHIPPING ] cumlesi / free shipping | ORN_YAYIN_SPEC.json:14-15; kapi yazimdan ONCE uygular (B8) |
| ai_beyani | Z | {dil: cumle} | etsy_common beyan kapisi | etsy_common.py:494 [kod] |
| galeri | Z | [{dosya_eki, alt_metin}] sirali, sha listesi | 14 gorsel, 2. sira sembol karti | ORN_YAYIN_SPEC.json:11-12; ornament_galeri9.py:38-39 |
| video | Z | {sayi, dosya_sha} | 1 | ORN_YAYIN_SPEC.json:13 |
| malzeme | Z | [str] | ["Ceramic"] | ornament_taslak.py:49 [kod] |
| should_auto_renew | Z | bool | true | ornament_taslak.py:485 [kod] |
| kontrol_edilmeyen | Z | [str] | ORN_YAYIN_SPEC.json:24 listesi | yayina_hazir kurali (yayina_hazir.py:43-48) |

### 2.2 "panel_on_isleri" blogu

Her biri {ad, durum: "yapildi"/"yapilmadi", dogrulama: salt okuma uc ve beklenen, kanit: kosu no + tarih}. Kapi "yapildi" ve kanitli olmayan her ise DUR verir.
- uretim ortagi kaydi (panel): GET /shops/{shop}/production-partners, beklenen id + konum (emsal yayina_hazir.py:401)
- kargo profili: GET /shops/{shop}/shipping-profiles/{id}, ulke ve ucret listesi (emsal ornament_taslak.py:102)
- GPSR: API'de dogrulama ucu bilinmiyor (bilmiyorum; ORN_YAYIN_SPEC.json:24 da "kontrol edilmeyen" diyor). Oneri: Serdar beyani; beyan
  urun + uretim ortagi id + tarihe baglanir (S3). Beyan yalniz GPSR icin; diger panel on isleri yukaridaki ve asagidaki GET'lerle dogrulanir.
- readiness tanimi, bolum, iade politikasi: magaza duzeyi GET'ler (emsal ornament_taslak.py:124-133)

### 2.3 "kilit" blogu

- Depoda (public): `kilit: {kilitli: bool, ayar_sha256, metin_en_sha, metin_ru_sha, galeri_sha_listesi, video_sha, kilit_tarihi}`. Kapi
  dosyanin kendi sha'sini (kilit alani haric kanonik JSON) yeniden hesaplar.
- Drive'da (gizli; oneri 4 "onayli gorsel kaydi gizli Drive'da, depo public" ile uyumlu): `ONAY_<URUN>.json`: Serdar onay sozu, tarih,
  ayar_sha256. Depo yalniz onay kaydinin sha'sini tutar. Kapi yazim kosusunda Drive kaydini indirir ve iki sha'yi karsilastirir. Soru S4.

## 3. Kapi

Modul: `scripts/etsy/urun_ayar.py` (oneri), iki fonksiyon:
- `yukle(urun) -> ayar`: sema dogrulama (zorunlu alan bos, bilinmeyen anahtar, tip) -> DUR listesi. Emsal: yayina_hazir.spec_yukle
  (yayina_hazir.py:94-104: eksik ve bilinmeyen anahtar DUR).
- `yazim_kapisi(ayar, govde, uc)`: yazilacak govdedeki her alan ayardaki degerle ayni mi; kilitli=false, sha uyusmazligi, panel on isi
  eksik -> SystemExit (yazim yok, neden listesi). Etsy istegi yok; token indirmeden once de calisabilir.

Cagri yerleri (yazim satirindan once):

| Betik | Once | dosya:satir |
|---|---|---|
| ornament_taslak | ayar() yerine urun_ayar.yukle; createDraftListing govdesinden once yazim_kapisi | ornament_taslak.py:62-67 (ayar), :482-489 (govde + taslak_olustur) |
| kupa_taslak | sabitler (:246-251) ayardan; govdeden once kapi | kupa_taslak.py:481-485 |
| by78_taslak | KAPALI (:111-115); yeniden acilirsa Etsy._call + metin kapisi + kota tabani + ayar kapisi (Serdar onayi) | by78_taslak.py:246-252 |
| ornament_galeri9 / ornament_ru_olcu / ornament_kargo | kapi mod girislerinde degil, betigin izin sinifinin _call(**kw) ve post_file(path, files, data) fonksiyonlarinda (_izin(method, path) govdeyi gormez): galeri9'un yaz :216, sira :448, yeniden :607, tasi :945 modlarinin hepsi kapsanir. ornament_kargo'da IKI izin sinifi var: ProfilIzin (:160-172, kargo profili) ve FiyatIzin (:174-190, fiyat PUT :467, fiyat_tek :441, secim :658); kapi ikisine de girer | ornament_galeri9.py:156-165 (_call, post_file); ornament_ru_olcu.py:130 (_call); ornament_kargo.py:164, :181 (_call) |
| yd_yapi_yaz (5.1) | plan kurulumundan once kapi (envanter ve kargo ayardan) | yd_yapi_yaz.py:123-148, :254 |
| kupa_* (5.2) | kupa_fiyat :259, kupa_galeri78 :699-859, kupa_ru :111 oncesi | |

Kalite kurallarina uyum (CLAUDE.md):
- Kapi gevsetilmez (CLAUDE.md:211-216): mevcut kapilar (ai_beyan, ru_yazim, metin_yasak, yayin_beyan, html_coz; etsy_common.py:852-858)
  aynen kalir; ayar kapisi bunlarin ONUNE eklenir, yerine gecmez.
- Ortak istemci atlanmaz (CLAUDE.md:217): yazim Etsy._call / post_file uzerinden. Tek gonderim icin dogrudan requests.post kullanan yerlerde
  kapilar eksik: ornament_taslak.py:350-354 ai_beyan + metin (ENGEL) + kota; kupa_taslak.py:386-389 ai_beyan + metin (UYARI, mod yok) + kota;
  by78_taslak.py:251-252 yalniz ai_beyan (betik kapali); ornament_kargo.py:126-140 (Ag._tek, kargo profili POST) ai_beyan var, metin_yasak_kapisi yok
  (import :35'te de yok; CLAUDE.md:217 bu satiri :132 "onayli ornek" diye anar). Bu tek gonderim yollarinda gercekten eksik olan html_coz
  (etsy_common.py:853-854) ve metin kapisi; ru_yazim_kapisi createDraftListing'de zaten bir sey yapmaz (:229-231), yayin_beyan_kontrol yalniz
  PATCH/PUT'ta calisir (:693-694). Oneri: tek gonderim de ortak bir yardimci uzerinden ayni kapi dizisini cagirsin; ayar kapisi basinda.
- Metin kapisi modu: yeni urunde "ENGEL" ONERILIR (emsal ornament_taslak.py:282, :337); ENGEL'e gecis ayri Serdar onayi ister
  (etsy_common.py:252-253), bu yuzden S9'da sorulur. Canli metinlerde KESIN eslesme varsa (or. premium, CLAUDE.md:72-73) ENGEL o ilanda DUR
  verir; 5.1 / 5.2 canli ilanlarina uygulanmadan once salt okuma taramasi gerekir.
- Kosudan once tek bagimsiz inceleme (CLAUDE.md:204-207, :218); testler gercek fonksiyonu calistirir, mutasyonla kanit (CLAUDE.md:217).
- updateListing (PATCH) taslagi yayina alir (CLAUDE.md:54): kapi PATCH'ten hemen once state okur. Uc durum:
  (1) draft + acil {state: inactive}: izinli. (2) draft + metin / kargo profili PATCH (kod yayin yolu): YALNIZ S14 "hayir" olursa gecerli;
  o durumda onayli yayin adiminda, ayri Serdar onayiyla, ayar kilitliyken, once yayina_hazir kontrolu. Bugun ornament yayini Serdar'da,
  panelden (Serdar 8 Kas, Merkez kaydi KARARLAR_ANA_4 10); kodda: ornament_galeri9.py:4, :157-160; ornament_ru_olcu.py:2, :12-13.
  Ornament: 55 yayinda, 23 taslak; canli metin ve kargo profili 78/78 PASS [gorev] Merkez, Drive kontrol JSON'u; Denetim dogrulamadi.
  (3) active: metin PATCH'i izinli (emsal kupa_galeri78.py:843-847, poster_metin_yaz.py:130-141, ilan_yapi_v2.py:479-537); bu uc emsal active
  olmayan her durumda DUR verir, inactive ilan icin yol tanimli degil (DUR kalir).

## 4. Tek gercek kaynak

Cakisan alanlar (ORN_ETSY_AYAR.json / ORN_YAYIN_SPEC.json / kod):

| Alan | ORN_ETSY_AYAR | ORN_YAYIN_SPEC | Kod |
|---|---|---|---|
| kargo | 319194887351 (:7) | 319230731837 (:5) | ornament_kargo.py:41 ad "Ornament Shipping" |
| uretim ortagi | 5817638 United States (:13-14) | 5870733 Latvia (:7-8) | |
| fiyat | yok | 19.90 (:9) | 29.90 ornament_taslak.py:44; 19.90 ornament_kargo.py:40 |
| kargo metni | "Free Worldwide ... ucretsiz" (:8) | free shipping yasak (:15) | ornament_taslak.py:52 PROFIL_AD |
| nitelik | Material/Indoor/Season (:15-19) | W/H/D (:16-20) | ornament_ru_olcu OLCU |
| EN aciklama | "Free Worldwide" kargo ozeti (:8) | zorunlu kargo cumlesi, free shipping yasak (:14-15) | ORNAMENT78_METIN.csv: 78/78 free shipping, 0/78 zorunlu cumle (B8; kaynak dosya, canli degil). Canli 78/78 PASS [gorev] Merkez, Drive kontrol JSON'u; Denetim dogrulamadi |

Oneri:
- Tek kaynak URUN_AYAR.json. ORN_YAYIN_SPEC'in "beklenen" blogu bundan TURETILIR (kodla, ayni sha'dan); elle ikinci kopya kalmaz.
  ORN_ETSY_AYAR.json emekliye ayrilir (silme ayri onayla; ornament_taslak.py:37 bunu okuyor).
- Dort farki (uc kimlik/fiyat + EN metin) yakalayacak yol: yayina_hazir kontrolu (yayina_hazir.py:45-48 B_ZORUNLU) beklenen degerleri URUN_AYAR'dan alir. Ayrica
  yazilmadan once ayar dosyasi ile SPEC arasinda fark varsa kapi DUR (iki kaynak ayni olmali; gecis donemi). Aciklama yasak/zorunlu kurallari yazimdan once ayar kapisinda uygulanir (bugun yalniz yayina_hazir sonradan buluyor).
- Kodda sabit kalan fiyat ve kimlikler (1.2 tablosu) ayara tasinir; testte "sabit kimlik kalmadi" taramasi (bilinen FAIL: bir sabit geri
  konunca test FAIL).

## 5. Mevcut ilan guncellemesi (5.1 poster + 1st Anniversary, 5.2 couple mugs + sign mugs)

"Birlestirme" istegi Serdar'indir; anlami acik (S1), karar yok. Asagida oneri yazilir, karar Serdar'in (Duzeltme 1, D1).

Kurallar (B7, B9, B10): tam carpim varsayimiyla urun sayisi = menu deger sayilarinin carpimi; en fazla 3 menu; SKU + fiyat 3 menuye
bagliyken sinir 400 [olcum]. Birlestirmede urun tipi mevcut 3 menuden birine DEGER olarak girer ve carpim hesaplanir [hesap]; toplama
yazilmaz (duzeltme oncesi metindeki (6e020e3) toplama yanlisti).
SKU baglama kisiti: 3 menude on_property yalniz 0, 1 ya da 3 id (REFERANS_ILAN_CL.md:49); SKU semasi format ve boy icerir (:46); siparis
yonlendirici SKU'yu ve renk varyasyonunu ayristirir (pod_sku.parse_tx, :47). SKU baglamasini ya da renk menusunun anlamini degistiren
secenek: "SKU semasi ve siparis yonlendirici degismeden uygulanamaz; kod isi".
Tabanlar [kaynak dosya, canli degil]: poster A = 6 format x 5 renk x 13 boy = 390 (REFERANS_ILAN_CL.md:9), B = 2 x 5 x 14 = 140
(pod_5x7_yaz.py:7, :9; yd_yapi_kuru.py:7, :61); YD = Style 5 x Format 2 x Size 14 = 140 (yd_yapi_kuru.py:5-9).

| # | Secenek | Menu deger sayilari | Carpim [hesap] | Sinir (kaynak) | Kod isi | Gecmis / yorum / SEO / siparis eslemesi |
|---|---|---|---|---|---|---|
| 5.1-1 | YD urun tipi poster Format menusune 1 deger olarak (or. "1st Anniversary Print"); renk ve boy ayni | A 7 x 5 x 13; B 3 x 5 x 14 | A 455; B 210 | 400 [olcum] | SKU semasi ve siparis yonlendirici degismeden uygulanamaz; kod isi (pod_sku.py:50 SKU2_RE yalniz -F.. ekini tanir; parse_tx :94-108 F'siz her SKU'yu poster baskisi sayar ve rengi poster rengi okur: YD baskisi poster SKU'suyla yanlis urune yonlenir, yeni kodla eslesmez ve gonderilmez). YD dijital (yd_yapi_kuru.py:5-7, :11 dijital 3.90) duser; YD'nin 5 stili kalmaz; YD satirlarinda 5 poster renginin anlami yok | poster ilaninin gecmisi kalir; YD ilanlari kapanirsa YD gecmisi / yorum / SEO gider |
| 5.1-1b | 5.1-1 + YD 2 format degeri (dijital + baski) | A 8 x 5 x 13; B 4 x 5 x 14 | A 520; B 280 | 400 [olcum] | 5.1-1 ile ayni: SKU semasi ve siparis yonlendirici degismeden uygulanamaz; kod isi | 5.1-1 ile ayni |
| 5.1-2 | Renk menusune YD 5 stili eklenir (renk + stil = 10), Format ayni | A 6 x 10 x 13; B 2 x 10 x 14 | A 780; B 280 | 400 [olcum] | renk menusunun anlami degisir, parse_tx renk okur (REFERANS_ILAN_CL.md:47): SKU semasi ve siparis yonlendirici degismeden uygulanamaz; kod isi | 5.1-1 ile ayni; anlamsiz kombinasyonlar (stil x cerceve) kapali urun olarak sinira sayilir (tam carpim: ilan_yapi_v2.py:232 [kod yorumu, olculmedi]) |
| 5.1-3 | Format'a YD 2 deger + renk menusune 5 stil | A 8 x 10 x 13; B 4 x 10 x 14 | A 1040; B 560 | 400 asar [olcum]; SKU 0 / 1 menuye baglanirsa 2500 [dogrulanmadi], ama fiyat format ve boya gore degistigi icin (yd_yapi_kuru.py:10-14) fiyat 3 menuye bagli kalir; olculen 400 durumu sku = price = 3 menu (REFERANS_ILAN_CL.md:49) | SKU baglama + sema + yonlendirici: SKU semasi ve siparis yonlendirici degismeden uygulanamaz; kod isi | 5.1-2 ile ayni |
| 5.1-4 | Ayri ilanlar kalir; yalniz capraz baglanti / bolum | degismez | A 390 ya da B 140; YD 140 | degismez | yok | gecmis korunur; BU ISTEGI YENIDEN ACAR (Serdar'in birlestirme istegi karsilanmaz) |

(a) mevcut ilana ekleme ve (b) yeni tek ilan + eskileri kapatma, ikisi de AYNI menu ve 400 sinirina tabidir; tablo ikisine de uygulanir.
(a) icin duzeltme oncesi metindeki (6e020e3) "uygulanamaz gorunuyor" sozu Taban A'da gecerlidir (455 / 520 / 780 / 1040 > 400); Taban B'de 5.1-1 (210), 5.1-1b (280) ve 5.1-2 (280)
sinir icinde [hesap]. (b) yolunda kapanacak ilan [kaynak dosya, canli degil]: poster 78 (REFERANS_ILAN_CL.md:8) + YD 78 (data/pod/yd78_ids.csv,
78 veri satiri, baslik haric) = 156; cift basina 1 yeni ilan acilirsa 78 yeni. Canli sayilar O1(2)'ye baglidir.
Kapi (her secenekte): ayar dosyasi hedef envanterin TAMAMINI tutar (urun listesi, fiyat, sku); yazimdan once canli envanter yedeklenir, plan
damgasi kilitlenir (yd_yapi_yaz.py:1-4, :123-148 deseni); envanter PUT ?max_variations_supported=3 (yd_yapi_yaz.py:56, :254). Galeri: ilan
basina 20 gorsel (kapak_yukle_78.py:58); iki urunun galerisi tek ilanda paylasilir.
5.2 (couple mug 78 + sade 12): kupa 8 stil x 2 boy = 16 urun (kupa_galeri78.py:73); sade ilanlarin menu yapisi depoda olculmedi. Sinir sorun
gorunmuyor; karar menu sayisi ve SKU eslemesine bagli; O1(2) sonrasi ayni tabloyla yazilir.
Oneri (karar Serdar'in): once O1(2) ile canli poster tabani (A ya da B) olculsun. Taban A'da hicbir birlestirme secenegi 400 icinde degil.
Taban B'de 5.1-1 (210), 5.1-1b (280) ve 5.1-2 (280) sinir icinde; ucu de SKU / yonlendirici kod isi ister. YD stilleri korunacaksa 5.1-2,
YD dijital korunacaksa 5.1-1b ya da 5.1-2. 5.1-4 bu istegi yeniden acar.

## 6. Istek tahmini (yeni ilan, tek gecis)

Koddan sayim [hesap], ornament_taslak.yaz mutlu yol (ornament_taslak.py:398-577):

| Adim | Istek | dosya:satir |
|---|---|---|
| magaza GET | 1 | :398 |
| ayni baslik taramasi: ilk ilanda draft/inactive/active tam tarama (en az 3, sayfalamayla daha fazla; kod +30 pay ayirir :400), sonraki ilanlarda 1 | 1 (ilk ilanda >= 3) | :439-452 |
| createDraftListing | 1 | :489 |
| state okuma (7 adimda 1'er) | 7 | :404-406, :504-564 |
| envanter GET + PUT | 2 | :507, :512 |
| gorsel GET + 11 yukleme | 12 | :517, :523 |
| video GET + POST | 2 | :528, :540 |
| varimg oncesi GET x2 + POST | 3 | :545-552 |
| kisisellestirme POST | 1 | :556 |
| nitelik PUT x3 | 3 | :563 |
| son okuma (gorsel+video 1 tur, ilan, envanter, kisisel, nitelik, varimg) | 7 | :567-577 |
| **Toplam** | **40** | ornament kuru olcumu 40 ile ayni (ornament_taslak.py:45 [olcum]) |

Ornament son haline (14 gorsel, 6 nitelik, RU) tek gecis: 40 + 3 gorsel + 3 nitelik (W/H/D) + RU 3 (GET + POST + geri okuma;
ornament_ru_olcu.py:221-232) + 1 state okuma = **~50 istek [hesap]**. Bu, oneri 1'deki 45-55 tahminini dogrular.
Dahil degil: bekleme dongulerinin tekrarlari (state 6'ya kadar :405, gorsel/video 6 tura kadar :567), 5xx/429 tekrarlari; en kotu durum
icin ornament_galeri9 KOTA_ILAN mantigi (ornament_galeri9.py:48) ornek alinir. Magaza duzeyi bir kerelik isler (kargo profili ve hedefler,
bolum, readiness) ilan basina sayilmaz.
Karsilastirma [gorev]: ornament'ta ilan basina ~115 (40 + galeri 61-69 + RU/olcu 13); tekrar yazimlar ~5.900 istek.
Kendi kontrolum [hesap]: yalniz galeri + RU/olcu (61..69 + 13) x 78 = 5.772 - 6.396 (kargo/fiyat PUT, ornament_kargo.py:47 ILAN_ISTEK 21, haric).
Ek azaltma secenegi (bu planin disinda, olculmedi): son okumada /listings/batch (yayina_hazir.py:6, :167) ile 5-7 GET yerine 1-2.

## 7. Uygulama adimlari ve sirasi (sureler tahmin)

| # | Adim | Etsy | Sure [tahmin] |
|---|---|---|---|
| O1 | AYRI ONAYLA salt okuma, iki parca (7.1): (1) ornament readiness / iade / bolum DEGERLERI, (2) kupa + sade ve poster + YD menu yapisi ve urun sayisi. Yeni salt okuma betigi gerekirse bu kod asamasidir, ayri onay | yalniz GET | 1 sa, kod dahil [tahmin] |
| 1 | urun_ayar.py + sema + ornament78 URUN_AYAR.json (degerler SPEC + O1(1); O1 kosmadan SPEC + kaynak dosya, "olculmedi" etiketli) | yok | 2 sa |
| 2 | Testler: bilinen PASS (tam ayar) + bilinen FAIL (her zorunlu alan bos, kilitli false, sha farkli, panel isi eksik, SPEC ile fark, aciklamada free shipping, sabit kimlik geri gelirse); sahte Etsy O1 olcumundeki alan yapisiyla | yok | 2 sa |
| 2b | Yeni DUR kapilarinin gercek veriyle kuru olcumu (CLAUDE.md:214-216: sikilastirma tipik ve en kotu veriyle olculur): 78 ornament ayari + S13 sonrasi (canlidan guncellenmis) CSV, kupa sabitleri; bugunku CSV ile 78 yanlis DUR verir (B8); kac ilan DUR verir, neden listesi | yok | 1 sa |
| 3 | ornament_taslak (ve kupa/by78) govdesini ayardan kurma + kapi cagrisi; mutasyon kaniti | yok | 2 sa |
| 4 | yayina_hazir beklenenini ayardan turetme; SPEC'in elle kopyasini kaldirma | yok | 1 sa |
| 5 | Temiz kopya (tam gecmisli) tam test paketi; tek bagimsiz inceleme (en fazla 2 tur); push sonrasi o push'un CI kosulari yesil (CLAUDE.md:217) | yok | 1,5 sa |
| 6 | Kuru (AG YOK) tek gecis: istek sayisi raporu (6. bolum tahmini ile kiyas) | yok | 30 dk |
| 7 | Pilot: kod 1 yeni TASLAK acar (urun Serdar secer), ayri onay; yayin S14'e bagli (bugun panelde Serdar); sonra yayina_hazir kontrolu | yazar (taslak) | 1 sa |
| 8 | 5.1 / 5.2 ayar dosyalari ve secime gore yazim yolu (S1 sonrasi ayri plan) | | ayri |

### 7.1 O1 tasarimi (Duzeltme 1, D2)

Ornament olc zaten kostu: 42486805159 (8 Kas 13:49 UTC, success) [kosu meta]; alan yapisi test_yayina_hazir.py:8-11'de kullaniliyor. Bu
yuzden adim 2 (sahte Etsy alan yapisi) O1'e bagli degildir; O1(1) yalniz DEGER okumasi icindir. Bugunku yayina_hazir yolu bu deger
okumasi ve kupa / sade / poster / YD icin yazildigi gibi kosmaz:
- yayina_hazir tam SPEC ister (yayina_hazir.py:45-48 zorunlu anahtarlar, :94-100 eksikte DUR) ve --ilanlar YEDEK9 biciminde zorunlu (:421);
  kupa, sade, poster ve YD icin ikisi de yok.
- mod=olc readiness / iade / bolum DEGERLERINI yazmaz: ornek ilanlar icin yalniz alan adi ve turu (yayina_hazir.py:8-9; alan_turleri :148);
  yazdigi degerler uretim ortaklari (id, ad, konum :464-465) ve state sayisi.
- Istek: olc kosusu 5 istek [hesap; nb = 1 (<= 100 ilan) ve hem draft hem active ornek varken] (magaza :442 + batch :451 (100 ilan basina 1, :167-170) + production-partners :465 + properties x2 :477,
  draft ve active ornek); koddaki tahmin formulu (:446) 1 + nb + 2 = 4 sayar (production-partners eksik). Duzeltme oncesi metindeki (6e020e3) "2-4 istek" yanlisti.
- Batch istegi bugunku INCLUDES sabitinde envanter icermez (yayina_hazir.py:42); bu Etsy siniri degildir.

Batch envanter ucu: resmi Etsy API referansi bu oturumda okunamadi (www.etsy.com ve developers.etsy.com ag izninde kapali) [dogrulanmadi].
Depo kaniti: scripts/etsy/magaza_denetim.py:203 /listings/batch includes "Images,Videos,Inventory,Shipping"; magaza-denetim kosusu
39640900503 (21 Eki, commit 92ed860, :203 orada da ayni) success [kosu meta; cikti okunmadi, envanterin dondugu dogrulanmadi].
scripts/sosyal/analiz/kupa_pin_metin_v2.py iki surum: 8c9de44 tek ilan getListing ?includes=Inventory (8c9de44:72) ile kostu (39558151134, failure).
b5060ee batch includes=Inventory (:73) ile yalniz 39558651500'de kostu, failure, neden okunmadi; b5060ee :3-4 "getListing includes Inventory
kabul etmiyor (21 Eki 1. deneme 400)" der [kod yorumu]. Batch Inventory icin: 1 success (magaza_denetim) + 1 nedeni okunmamis failure. Iki senaryo:

| Parca | Ilan [kaynak] | Senaryo 1: batch Inventory var | Senaryo 2: ilan basi envanter GET |
|---|---|---|---|
| (1) ornament degerleri | 78 (liste Drive'da, TEMP/ORNAMENT_TASLAK/DURUM.json yol adi, ornament_galeri9.py:14; Actions okur) | magaza 1 + batch 1 + readiness / iade / bolum tanimlari 3 (emsal ornament_taslak.py:124-133) = 5 | 5 + 78 = 83 |
| (2) kupa + sade | 78 + 12 (kupa: Drive TEMP/KUPA_ORCHARD_TASLAK_20261019/KUPA_TASLAK_LISTE.csv yol adi (kupa-galeri78-hazir.yml:76; --liste, kupa_galeri78.py:140-147, :1285); sade: 12 = ARIES sablon + 11 (sade_taslak OUT DURUM.json'da yalniz 11 taslak olabilir [dogrulanmadi]; gorev-g:sade_taslak.py:19, :38); kupa listesi Drive'da, Actions okur) | magaza 1 + batch 1 = 2 | 2 + 90 = 92 |
| (2) poster + YD | 78 + 78 (data/pod/pod78_ids.csv, data/pod/yd78_ids.csv) | magaza 1 + batch 2 = 3 | 3 + 156 = 159 |
| Toplam | 324 | 10 | 334 |

Uclar: ilan alanlari (return_policy_id, shop_section_id) batch'ten; readiness deger envanter offering'inde (ornament_taslak.py:510); envanter GET
emsali kupa_galeri78.py:357, yd_yapi_yaz.py:163. Kota: her kosu basinda kalan >= tahmin + KOTA_SINIRI 10 (CLAUDE.md:49). Ilan kimlikleri plana
yazilmaz. Yeni salt okuma betigi (ya da olc degisikligi) kod asamasidir, ayri onay.
Bagimlilik: adim 1 (ornament78 URUN_AYAR degerleri) O1(1)'e bagli (depo karsiligi ORN_ETSY_AYAR.json:5, :9, :11 [kaynak dosya, canli degil]);
adim 2 O1'e bagli degil (alan yapisi olc 42486805159'dan); 5.1 / 5.2 secimi (S1) O1(2)'ye baglidir. O1 kosmadan adim 1 yalniz SPEC ve
kaynak dosya degerleriyle, "olculmedi" etiketiyle ilerleyebilir.

## 8. Acik sorular (Serdar)

| # | Soru | Oneri |
|---|---|---|
| S1 | 5.1/5.2 "birlestirme": mevcut ilana varyasyon (a) mi, yeni ilan + eskileri kapatma (b) mi? | 5. bolum secenek tablosu (5.1-1 .. 5.1-4); once O1(2) ile canli taban, karar Serdar'in; 5.1-4 bu istegi yeniden acar |
| S2 | Ayar dosyasinin yeri docs/urun/<URUN>/URUN_AYAR.json uygun mu? | evet |
| S3 | GPSR API'de dogrulanamiyor; panel on isi kaniti "Serdar beyani + tarih" kabul mu? | evet; beyan urun + uretim ortagi id + tarihe baglanir (oneri; ortak degisirse yeniden beyan; ornek: ornament ortagi 5817638 United States'ten 5870733 Latvia'ya degisti). Beyan yalniz GPSR icin; baska on ise uygulanirsa gevsetme olur |
| S4 | Onay sozu ve tarihi gizli Drive'da, depoda yalniz sha: uygun mu? | evet (oneri 4 ile uyumlu) |
| S5 | ORN_ETSY_AYAR.json emekliye ayrilsin mi (yerine URUN_AYAR)? | evet, kod gecisi bitince ayri onayla |
| S6 | Ornament'ta kalan taslaklar icin ayar dosyasi bugunku canli degerlerle mi doldurulsun? | evet; once O1(1) (yeni salt okuma, ayri onay), sonra kilit |
| S7 | sade_taslak (sign mug, yalniz gorev-g dalinda) 5.2 icin main'e alinsin mi, yoksa ortak yazicidan mi gecsin? | ortak yazici + ayar dosyasi; SABLON kopyalama yerine ayar |
| S8 | Kimlik ve fiyat sabitleri tum betiklerden ayara tasinsin mi (kupa, by78 dahil), yoksa yalniz yeni urunlerde mi? | yeni urunlerde zorunlu; eskiler dokunulduklari isle birlikte |
| S9 | Yeni urun yaziminda metin kapisi ENGEL modu zorunlu olsun mu (ayri onay gerekir, etsy_common.py:252-253)? | evet; canli 5.1 / 5.2 ilanlarina uygulanmadan once salt okuma taramasi. "free shipping" yasagi METIN_KESIN'e (tum urunler, alt metin dahil: etsy_common.py:249-251) EKLENMEZ: onayli poster alt metni "made to order and free shipping" (data/pod/galeri_v11_alt.csv:6) ve poster profili "POD Prints - Free Shipping" (docs/POD_LISTING_TEMPLATE.md:224) DUR verirdi. Yasak urune ozgu: URUN_AYAR.aciklama_yasak, SPEC regex'iyle ayni (free shipping, ships free, free delivery; ORN_YAYIN_SPEC.json:15) |
| S10 | pod_listing_create'teki Hahnemuhle / жикле sabitleri (B4) ayri iste temizlensin mi (is akisi kapali)? | evet, ayri gorev; is akisi acilmadan once |
| S11 | Sonraki yeni urun (kayitli "pet memorial", dogrulanmadi) bu sistemle mi baslasin? | evet, ilk uygulama ornegi |
| S12 | 5.1 icin esas kod: main'deki is akislarinin cagirdigi ama main'de olmayan yd2_galeri_yukle (yd-asama2) ve yd_asama1 (yd-asama1) main'e alinsin mi? | evet, ayar kapisiyla birlikte; once dal farki incelemesi |
| S13 | data/pod/ORNAMENT78_METIN.csv aciklama sutunu canlidan salt okumayla guncellensin mi (ornament kalan 23 zinciri bittikten sonra; zincir bu CSV'nin kod / baslik / alt metin sutunlarini okuyor: ornament_galeri9.py:14, :56, ornament_ru_olcu.py:106; aciklama sutununu okuyan ornament_taslak.py:243, :827 (yaz modunda baska CSV yasak))? Yeni EN metin yazilmaz. | evet, zincir bittikten sonra; sha ayara |
| S14 | Yeni urunlerde de yayin panelde Serdar'da mi, kod yalniz taslak mi acar? | Merkez onerisi: evet (ornament karariyla tutarli); Serdar karari |

Canli durum kaynagi: yayina-hazir kontrol ciktisi; depo CSV/JSON canliyi gostermez.
