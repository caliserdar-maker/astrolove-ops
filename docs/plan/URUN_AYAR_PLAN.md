# URUN AYAR PLANI (Oneri 1, 1. asama: YALNIZ PLAN)

Dayanak: Serdar 8 Kas sistem onerileri "hepsi" + 8 Kas gece "Ok" (oneri 1 ilk sirada; KARARLAR_20261108_5).
Kod yok, Etsy istegi yok, Actions kosusu yok. Butun dosya:satir atiflari **main b82f2ec6812712f2a43e021366dbd73677eca895**
(b82f2ec) icindir. 89842ce ile farki yalniz CLAUDE.md; scripts/ ve .github/ ayni.
Bagimsiz inceleme tur 1 (8 Kas): 3 YUKSEK, 6 ORTA, 3 DUSUK; 11'i islendi (B7, B8, 1.3 eksik yazicilar, B4, kapi yerleri, PATCH kurali,
sayim, KALITE 4/5 adimlari, atiflar, sema); 1'i reddedildi ("premium canli EN'de izinli": CLAUDE.md:72-73 izinli DEGIL diyor).
Tur 2 (son tur, CLAUDE.md:218): yeni YUKSEK yok; 4 ORTA + 2 DUSUK islendi (yayin adimi PATCH yolu, free shipping yasaginin urune ozgu
olmasi, kapi yeri _call / post_file, ornament_kargo iki izin sinifi, Ag._tek kapilari, eksik kapi sayimi).
Kaynak turleri: [kod] depodaki satir, [olcum] kosu ya da kayit, [gorev] Merkez gorev metni (8 Kas), [hesap] koddan sayim, [tahmin].

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
| sade_taslak (yalniz origin/gorev-g dalinda, main'de YOK) | createDraftListing; kimlikler SABLON ilandan kopyalanir; sonunda state active PATCH | SABLON 4607613712 canli ilan | gorev-g:scripts/kupa/sade_taslak.py:38, :61, :425-428, :606 |

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
- B6 [kod] sade_taslak (sign mug) main'de yok, yalniz origin/gorev-g dalinda; kimlikleri canli SABLON ilandan kopyalar (gorev-g:scripts/kupa/sade_taslak.py:38, :61) ve sonda state active PATCH yapar (:606). 5.2 icin bu kodun main'e alinip alinmayacagi karar gerektirir (S7).
- B7 [kod + olcum] Etsy urun siniri: SKU uc menuye bagliyken 400 (scripts/pod/ilan_yapi_v2.py:299-302; olculmus ret "Total products 576 exceeds maximum allowed 400", docs/REFERANS_ILAN_CL.md:49, 27 Eyl), degilse 2500 (ilan_yapi_v2.py:159-160; scripts/etsy/pod_sku.py:49). Poster ilani zaten 3 menu ve 390 urun (REFERANS_ILAN_CL.md:49); YD de 3 menu, 140 urun (yd_yapi_yaz.py:4, :9-10). Menu siniri 3 (max_variations_supported=3, yd_yapi_yaz.py:56).
- B8 [olcum, yerel] Ornament EN metni (data/pod/ORNAMENT78_METIN.csv, sha256 c8d18aa9a2462c0eeccf6fbcfc171f35a46b19e01831521e459db37e0f0129a5): 78 aciklamanin 78'inde "free shipping" var, SPEC zorunlu kargo cumlesi 0'inda (ORN_YAYIN_SPEC.json:14-15). Metin kapisi bunu durdurmaz: "free shipping" METIN_KESIN listesinde yok (etsy_common.py:256-270). Bugunku metinle tek gecis yayina_hazir'da FAIL veren ilan acar.

## 2. Sema onerisi

Yer ve ad: `docs/urun/<URUN>/URUN_AYAR.json` (ornek `docs/urun/ornament78/URUN_AYAR.json`), tek dosya, urun basina. Kilit
sha'lari ve onay sozu ayri (2.3). JSON, Python standart kutuphanesiyle okunur (yeni bagimlilik yok).

### 2.1 Alanlar (Z = zorunlu, bos ise kapi DUR; S = secmeli, yoksa acikca null)

| Alan | Z/S | Tip | Ornek (ornament78) | Ornegin kaynagi |
|---|---|---|---|---|
| urun | Z | str | "ornament78" | ORN_YAYIN_SPEC.json:2 |
| taxonomy_id | Z | int | 1857 | ornament_ru_olcu.py:33 [kod]; ORN_YAYIN_SPEC'te yok |
| readiness_state_id | Z | int | olc ile dogrulanacak | ORN_YAYIN_SPEC'te yok, ayar dosyasindaki deger kullanilmaz (gorev) |
| who_made / when_made / is_supply / type | Z | str | i_did / made_to_order / false / physical | ornament_taslak.py:482-483 [kod] |
| fiyat | Z | number veya {menu_kombinasyonu: number} + price_on_property | 19.90 (ornament tek fiyat); kupada Style x Size (kupa_taslak.py:510 price_on_property [Style, Size]) | ORN_YAYIN_SPEC.json:9 |
| kargo.shipping_profile_id | Z | int | 319230731837 | ORN_YAYIN_SPEC.json:5 |
| kargo.ozet | S | str | (yasak desen taramasindan gecer) | B3 |
| uretim_ortagi.id / .konum | Z | int / str | 5870733 / "Latvia" | ORN_YAYIN_SPEC.json:7-8 (olc 42486805159) |
| iade.return_policy_id | Z | int | olc ile dogrulanacak | ORN_YAYIN_SPEC'te yok |
| bolum.shop_section_id | Z | int | olc ile dogrulanacak | ORN_YAYIN_SPEC'te yok |
| kisisellestirme | Z | {acik: bool, sorular: [...]} | acik true, 3 soru | ORN_YAYIN_SPEC.json:10; sorular METIN CSV |
| varyasyon | Z | {property_id, menu: [{ad, sku_kodu, gorsel_sira}]} | Style 513, 5 stil | ornament_taslak.py:38-41 [kod] |
| envanter | Z | {stok, fiyat_on_property, sku_on_property} | 999, [], [513] | ornament_taslak.py:48, :512-513 [kod] |
| olcu / nitelikler | Z | [{property_id, value_ids, values, scale_id}] | W/H/D 2.99/2.99/0.1 in + Material/Indoor/Season | ORN_YAYIN_SPEC.json:16-20; ORN_OLCU.json; malzeme nitelikleri olc ile dogrulanacak |
| metin.en | Z | {csv, sha256, anahtar} | yeni onayli EN metin (bugunku CSV c8d18aa9... B8 nedeniyle kullanilamaz) | ornament_taslak.py:243 [kod]; sha yerel sha256sum [olcum] |
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
- GPSR: API'de dogrulama ucu bilinmiyor (bilmiyorum; ORN_YAYIN_SPEC.json:24 da "kontrol edilmeyen" diyor). Oneri: Serdar panel onayi + tarih, kanit turu "Serdar beyani" (S3).
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
  (1) draft + acil {state: inactive}: izinli. (2) draft + metin / kargo profili PATCH: yalniz ONAYLI YAYIN ADIMINDA, ayri Serdar onayiyla ve
  ayar kilitliyken (ornament_kargo.py:8-9 aciklama ve shipping_profile_id'yi bu adima birakir; 78 ornament taslaginda eski metin ve eski profil
  var). Bu PATCH ilani yayina alir; yayin adimi tek kosu, once yayina_hazir kontrolu (S14). (3) active: metin PATCH'i izinli (emsal
  kupa_galeri78.py:843-847, poster_metin_yaz.py:130-141, ilan_yapi_v2.py:479-537); bu uc emsal active olmayan her durumda DUR verir,
  inactive ilan icin yol tanimli degil (DUR kalir).

## 4. Tek gercek kaynak

Cakisan alanlar (ORN_ETSY_AYAR.json / ORN_YAYIN_SPEC.json / kod):

| Alan | ORN_ETSY_AYAR | ORN_YAYIN_SPEC | Kod |
|---|---|---|---|
| kargo | 319194887351 (:7) | 319230731837 (:5) | ornament_kargo.py:41 ad "Ornament Shipping" |
| uretim ortagi | 5817638 United States (:13-14) | 5870733 Latvia (:7-8) | |
| fiyat | yok | 19.90 (:9) | 29.90 ornament_taslak.py:44; 19.90 ornament_kargo.py:40 |
| kargo metni | "Free Worldwide ... ucretsiz" (:8) | free shipping yasak (:15) | ornament_taslak.py:52 PROFIL_AD |
| nitelik | Material/Indoor/Season (:15-19) | W/H/D (:16-20) | ornament_ru_olcu OLCU |
| EN aciklama | yok | zorunlu kargo cumlesi, free shipping yasak (:14-15) | ORNAMENT78_METIN.csv: 78/78 free shipping, 0/78 zorunlu cumle (B8) |

Oneri:
- Tek kaynak URUN_AYAR.json. ORN_YAYIN_SPEC'in "beklenen" blogu bundan TURETILIR (kodla, ayni sha'dan); elle ikinci kopya kalmaz.
  ORN_ETSY_AYAR.json emekliye ayrilir (silme ayri onayla; ornament_taslak.py:37 bunu okuyor).
- Dort farki (uc kimlik/fiyat + EN metin) yakalayacak yol: yayina_hazir kontrolu (yayina_hazir.py:45-48 B_ZORUNLU) beklenen degerleri URUN_AYAR'dan alir. Ayrica
  yazilmadan once ayar dosyasi ile SPEC arasinda fark varsa kapi DUR (iki kaynak ayni olmali; gecis donemi). Aciklama yasak/zorunlu kurallari yazimdan once ayar kapisinda uygulanir (bugun yalniz yayina_hazir sonradan buluyor).
- Kodda sabit kalan fiyat ve kimlikler (1.2 tablosu) ayara tasinir; testte "sabit kimlik kalmadi" taramasi (bilinen FAIL: bir sabit geri
  konunca test FAIL).

## 5. Mevcut ilan guncellemesi (5.1 poster + 1st Anniversary, 5.2 couple mugs + sign mugs)

"Birlestirme"nin anlami Serdar karari (S1). Iki secenek:

a) Mevcut ilana varyasyon ekleme: envanter PUT ?max_variations_supported=3 (emsal yd_yapi_yaz.py:56, :254; eski78_cerceve.py:211).
   Kapi: ayar dosyasi hedef envanterin TAMAMINI tutar (urun listesi, fiyat, sku), yazimdan once canli envanter yedeklenir, plan damgasi
   kilitlenir (yd_yapi_yaz deseni). Sinir (B7): 3 menu; SKU uc menuye bagliyken 400 urun. Poster ilani 3 menu ve 390 urunle dolu,
   YD de 3 menu (140 urun): 5.1 icin (a) olculen sinira gore uygulanamaz gorunuyor (390 + 140 > 400, 4. menu yok). 5.2 (kupa 16 urun,
   kupa_galeri78.py:73) icin sinir sorun degil; menu sayisi ve SKU eslemesi belirleyici.
   Eksi: tek ilanda iki urunun galeri/metin/kisisellestirme alanlari ayni (20 gorsel siniri: kapak_yukle_78.py:58 ETSY_MAX 20).
b) Yeni tek ilan + eskilerin kapatilmasi: yeni ilan 6. bolumdeki tek gecisle acilir; eskiler ayri onayla inactive.
   Kapi: yeni ilan tum ayarlar kilitliyken; kapatma ayri adim, salt okuma ile dogrulanir. Eksi: gecmis ve SEO sifirlanir; siparis eslemesi
   (SKU) yeni ilana gore guncellenir.

Oneri: 5.1 icin (b); 5.2 icin S1 cevabi ve O1 (mevcut kupa / sade ilanlarinin menu yapisi, salt okuma). Her iki secenekte ayni kapi gecerli.

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
| O1 | AYRI ONAYLA salt okuma olcumu: 5.2 kupa ve sade ilanlarinin menu yapisi + urun sayisi; ornament taslaginin alan adlari ve readiness / iade / bolum kimlikleri (yayina_hazir mod=olc, 2-4 istek) | yalniz GET | 30 dk |
| 1 | urun_ayar.py + sema + ornament78 URUN_AYAR.json (degerler SPEC + olc'den) | yok | 2 sa |
| 2 | Testler: bilinen PASS (tam ayar) + bilinen FAIL (her zorunlu alan bos, kilitli false, sha farkli, panel isi eksik, SPEC ile fark, aciklamada free shipping, sabit kimlik geri gelirse); sahte Etsy O1 olcumundeki alan yapisiyla | yok | 2 sa |
| 2b | Yeni DUR kapilarinin gercek veriyle kuru olcumu (CLAUDE.md:214-216: sikilastirma tipik ve en kotu veriyle olculur): 78 ornament ayari + mevcut metin, kupa sabitleri; kac ilan DUR verir, neden listesi | yok | 1 sa |
| 3 | ornament_taslak (ve kupa/by78) govdesini ayardan kurma + kapi cagrisi; mutasyon kaniti | yok | 2 sa |
| 4 | yayina_hazir beklenenini ayardan turetme; SPEC'in elle kopyasini kaldirma | yok | 1 sa |
| 5 | Temiz kopya (tam gecmisli) tam test paketi; tek bagimsiz inceleme (en fazla 2 tur); push sonrasi o push'un CI kosulari yesil (CLAUDE.md:217) | yok | 1,5 sa |
| 6 | Kuru (AG YOK) tek gecis: istek sayisi raporu (6. bolum tahmini ile kiyas) | yok | 30 dk |
| 7 | Pilot: 1 yeni ilan (urun Serdar secer), ayri onay; sonra yayina_hazir kontrolu | yazar | 1 sa |
| 8 | 5.1 / 5.2 ayar dosyalari ve secime gore yazim yolu (S1 sonrasi ayri plan) | | ayri |

## 8. Acik sorular (Serdar)

| # | Soru | Oneri |
|---|---|---|
| S1 | 5.1/5.2 "birlestirme": mevcut ilana varyasyon (a) mi, yeni ilan + eskileri kapatma (b) mi? | O1 olcumunden sonra karar; gecmis korunmasi onemliyse (a) |
| S2 | Ayar dosyasinin yeri docs/urun/<URUN>/URUN_AYAR.json uygun mu? | evet |
| S3 | GPSR API'de dogrulanamiyor; panel on isi kaniti "Serdar beyani + tarih" kabul mu? | evet, kaynak turu "beyan" diye yazilsin |
| S4 | Onay sozu ve tarihi gizli Drive'da, depoda yalniz sha: uygun mu? | evet (oneri 4 ile uyumlu) |
| S5 | ORN_ETSY_AYAR.json emekliye ayrilsin mi (yerine URUN_AYAR)? | evet, kod gecisi bitince ayri onayla |
| S6 | Ornament'ta kalan taslaklar icin ayar dosyasi bugunku canli degerlerle mi doldurulsun? | evet; once O1 ile canli okuma, sonra kilit |
| S7 | sade_taslak (sign mug, yalniz gorev-g dalinda) 5.2 icin main'e alinsin mi, yoksa ortak yazicidan mi gecsin? | ortak yazici + ayar dosyasi; SABLON kopyalama yerine ayar |
| S8 | Kimlik ve fiyat sabitleri tum betiklerden ayara tasinsin mi (kupa, by78 dahil), yoksa yalniz yeni urunlerde mi? | yeni urunlerde zorunlu; eskiler dokunulduklari isle birlikte |
| S9 | Yeni urun yaziminda metin kapisi ENGEL modu zorunlu olsun mu (ayri onay gerekir, etsy_common.py:252-253)? | evet; canli 5.1 / 5.2 ilanlarina uygulanmadan once salt okuma taramasi. "free shipping" yasagi METIN_KESIN'e (tum urunler, alt metin dahil: etsy_common.py:249-251) EKLENMEZ: onayli poster alt metni "made to order and free shipping" (data/pod/galeri_v11_alt.csv:6) ve poster profili "POD Prints - Free Shipping" (docs/POD_LISTING_TEMPLATE.md:224) DUR verirdi. Yasak urune ozgu: URUN_AYAR.aciklama_yasak, SPEC regex'iyle ayni (free shipping, ships free, free delivery; ORN_YAYIN_SPEC.json:15) |
| S10 | pod_listing_create'teki Hahnemuhle / жикле sabitleri (B4) ayri iste temizlensin mi (is akisi kapali)? | evet, ayri gorev; is akisi acilmadan once |
| S11 | Sonraki yeni urun (kayitli "pet memorial", dogrulanmadi) bu sistemle mi baslasin? | evet, ilk uygulama ornegi |
| S12 | 5.1 icin esas kod: main'deki is akislarinin cagirdigi ama main'de olmayan yd2_galeri_yukle (yd-asama2) ve yd_asama1 (yd-asama1) main'e alinsin mi? | evet, ayar kapisiyla birlikte; once dal farki incelemesi |
| S13 | Ornament kalan taslaklarinda EN metin: "free shipping" iceren 78 aciklama yeni onayli metinle degismeden yazim yok (B8). Metni kim hazirlar? | Merkez taslak, Serdar onayi, sha ayara |
| S14 | Ornament 78 taslak icin yayin adimi: yeni EN metin + yeni kargo profili tek PATCH ile (taslagi yayina alir) mi yazilsin? | evet, tek yayin kosusu, ayar kilitli + yayina_hazir PASS sonrasi, ayri onayla |
