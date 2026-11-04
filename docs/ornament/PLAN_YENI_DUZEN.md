# PLAN: ornament yeni düzen (Serdar 4 Kas 2026 akşam; AŞAMA 1 / 2)

Bu aşamada Actions koşusu, Etsy yazımı, Printful işlemi ve main push yok. Kod `YENI_DUZEN=1` ortam
değişkeniyle açılır. Varsayılan eski davranıştır.

Tuval 954 px, 11,8 px/mm. Halka iç dairesi merkez (475,5, 504), r 336.

## 0. Bu aşamada yapılan (kanıt)

| İş | Sonuç | Kaynak |
|---|---|---|
| A1 test_workflows | 0 | yerel (494 YAML) |
| A2 py_compile | 0 | yerel |
| A3 sikilastirma_mantik_testi | 0 (22 vaka) | yerel |
| A4 uretim78_mantik_testi --ornek78_hizli | 0 (70 vaka) | yerel |
| A5 kova_kapi_testi | 0 | yerel; CL gerçek + Kova **sahte** `_ana` (gerçek Kova `_ana` yerelde yok) |
| C `YENI_DUZEN` yokken motor çıktısı | HEAD f8c7a7b ile **aynı** | CL motor koşusu, iki kod: 3 koyu PNG sha aynı, OLCUM anahtar farkı yok, kapi_sert aynı |
| D yerel geometri 78 çift | **78/78 PASS** | `ornek/YENI_DUZEN_YEREL_20261104/YERLESIM78_TEST.json` |
| D bilinen FAIL (2 çift × 4 vaka) | 8/8 beklenen kapı FAIL; **×0,90 vakası (2/8) geçersiz** (§8 K1): gerçek negatif kanıt 6/8 | aynı dosya, `bilinen_fail` |
| D en geniş tarih / en uzun isim | aşağıda §6 | `ISIM_OLCUM.json` |

C ayrıntıları (CL, yerel ölçüm):
- EMERALD 02421dbb…, RUBY e7be8a3b…, SAPPHIRE e4c71ecf… her iki kodda aynı.
- Çıkış kodu 0 / 0.

## 1. Kararlar 1-8: koddaki karşılığı

Ortak geometri tek modülde: `scripts/printful/yeni_duzen.py`. Motor ve yerel test aynı fonksiyonları çağırır.

| Karar | Uygulama | Dosya:satır |
|---|---|---|
| 1 tarih alt y 795 | `yazi_yerlestir`: tarih kutusu (alfa > 0,5, virgül dahil) alt = 795 | yeni_duzen.py:23, :69-71 |
| 2 boşluk 32 / 32 | isim satırı alt = tarih üst − 32 (logo isimle kayar); küçük satır alt = isim üst − 32 | yeni_duzen.py:72-78 |
| 3 sabit üst çizgi | `h_max_12` = 12 küçük işaretin en yükseği (nominal h_oran × cap); sabit = küçük alt − H_MAX; sembol alt sınırı = sabit − 32; küçükler alta yaslı; yataylar `o3.yazi_blogu` ile aynen | yeni_duzen.py:79-81, :156-158; motor:307 |
| 4 sembol | yatay merkez 476; B3 = Y3 yerleşiminde sığan en büyük ölçek (mürekkep noktaları, ikili arama 40 adım) × 0,85; Y2 = boş dikeyin %75'i üstte | yeni_duzen.py:89-129 |
| 5 tarih biçimi | `TARIH_YENI = 'JUNE 14, 2025'`; motor iki yerde birlikte (engel e) | yeni_duzen.py:29; motor:244, :268, :377 |
| 6 yeniden üretim | CL, AQUARIUS_PISCES, GEMINI_VIRGO aşama 2 listesinde (§4). Eski dosya ve sha'lara dokunulmaz; yeni çıktı ayrı klasör öneki | §4 |
| 7 en uzun isim | yerel ölçüm (`ISIM_OLCUM.json`): W × N, iki isim eşit, tire ve kesme işareti harf sayısına girmez | yeni_duzen_yerel_test.py:165-180 |
| 8 kapı gevşetme yok | eski kapılar eski modda aynen; yeni modda kapı tablosu §3; beklenti satırı silinmez; varsayılan eski davranış | motor:63, :305-318, :744-755; sade:217 |

Yeni modda o4.kapi (görüntü yasağı ve çakışma) yine sert:
- FAIL olursa `OLCUM.json` `hata='yeni_duzen_kapi'` yazılır.
- Motor çıkış kodu 1 olur (motor:310-316).

## 2. Engeller a-j: çözüm

**a. Örnek koşusu (ornament-78-uretim.yml).** Aşama 2'de kod (bu aşamada yazılmadı):

1. `URETIM78_CIFTLER.json` yeni bölüm `yeni_duzen`.
   - parcalar: §4'teki 11 çift.
   - `aktif` geçici olarak `yeni_duzen` olur. Koşudan sonra aynı commit dizisinde `ornek`e geri alınır.
2. yml:
   - hazırlık `parcalar` okuması :61.
   - klasör öneki :100. B = URETIM || ORNEK yanına YENI_DUZEN eklenir, eski klasörlerle karışmaz.
   - `YENI_DUZEN=1` env yalnız `aktif=yeni_duzen` iken parça işine verilir.
   - birleştirme koşulu :383 (`AKTIF == ornek`) `ornek || yeni_duzen` olur.
3. `uretim78_beklenen.py:101` ve `uretim78_mantik_testi.py:217` `J['ornek']` sabit.
   - `--bolum` argümanı eklenir, varsayılan `ornek`.
   - Eski çağrı çıktısı değişmez; mantık testinde iki bölüm için vaka eklenir.

**b. CL kuralı koda bağlı.** Yerler:
- uretim78.py:48-49, :71, :236, :323-339
- ornek78.py:304-306, :329, :350, :403-425

Çözüm:
- Yeni modda CL normal çift. 246 ve onaylı dosyaya piksel karşılaştırması yok.
- Eski modda CL kontrolü ayrı bir adım olarak kalır: her parçanın ilk işi, `YENI_DUZEN` env YOK, mevcut kod aynen.
- ornek78.py'ye `YENI_DUZEN` okuması gelir:
  - Kontrol adımı alt süreçte env'den `YENI_DUZEN` silinerek koşar.
  - Sonraki çiftler `YENI_DUZEN=1` ile koşar.
- Sonuç:
  - Eski mod kanıtı her parçada korunur (beklenti `cl_kontrol_her_parca` silinmez).
  - Yeni CL ayrıca normal çift olarak üretilir.

**c. Boşluk ve yerleşim kapıları.** `o5.bosluklar` (ornek5:348) ilk boşluğu sembolden ölçer; yeni düzende bu boşluk serbest.

| Kapı | Eski modda | Yeni modda |
|---|---|---|
| `bosluk_20_20_20` (motor:744) | sert | yerine `yd_bosluk_32_32` (motor:752) |
| SADE `yerlesim_ayni` (sade:217) | eski | `bosluk_px[1:]` 32 ± 1 |
| ornek78:363 | `sade1_` önekiyle SERT'e taşır | değişiklik gerekmez |
| `sembol_ust_246` (motor:749) | yalnız eski mod + CL | yok |
| `kucultme_le_sinir` (motor:755) | anlamlı | yeni modda KUCULT = 0, kapı her zaman PASS (**zayıf**, §3) |

**d. Yerleşim yolu.**
- Yeni mod `o5.yerlesim_V5` ve KUCULT döngüsünü hiç çağırmaz (motor:305-318).
- `KUTU_BILGI`, `KUCULT`, `R['kucultme']` boş ya da 0 tanımlı kalır, sonraki okumalar çökmez.
- `o3.yazi_blogu`, `o5.blok/bosluklar`, ornek3/4/5 ve sade **değişmedi** (yalnız sade:217 bayraklı satır).

**e. Tarih metni.** motor:268 (çizim) ve :377 (10x IoU / alfa_fark) aynı `TARIH_METIN` değişkenini kullanır (motor:244), ikisi ayrışamaz.

**f. Dal kapısı.**
- `DAL_IZIN` (uretim78.py:344) ve yml:400-402 kopyası değişmez. Dala yalnız JSON / MD / log; CSV ve PNG yok.
- KONTAK.jpg yalnız bu yerel test için görev gereği dalda (benzetim, alfa maskeleri zaten depoda 6da763a).

**g. EN_UZUN.**
- Ayrı dosya adı `EN_UZUN_<CIFT>_<STIL>_954.png` ve ayrı Drive alt klasörü `EN_UZUN/`.
- `drive_karsilastir` (uretim78.py:295, sayı :312) bu klasörü saymaz, ayrı sayılır.
- Beklenti `ornek_png_drive` 5 PNG sayısı bozulmaz.

**h. Girdi.**
- Motor eski modda `CANCER_LIBRA_ana.png`'yi CL kutusu için okur (motor:278).
- Yeni modda bu blok atlanır: `not YENI_DUZEN`. CL, diğer çiftler gibi kendi `_ana`sıyla.
- yml ana listesi :120 değişmez.

**i. Bilinen FAIL vakaları.** Yerleşimden SONRA, gerçek kapı fonksiyonuyla (yerelde 8/8 doğru FAIL, §0). Aşama 2'de aynı 4 vaka parça başında:
- `yeni_duzen.kapilar` ile kapı FAIL vermezse parça DUR.
- PNG üretimine geçilmez.

**j. Süre.** 41868179117 ölçümü:
- Normal çift ~245 sn.
- Kova'lı çift ~420 sn.
- Tahmin §4.

## 3. Kapılar tablosu (yalnız `YENI_DUZEN=1`; eski mod aynen)

| Eski kapı | Yeni modda | Eşik / tolerans |
|---|---|---|
| `bosluk_20_20_20` | kaldırılır → `yd_bosluk_32_32` | tarih−isim ve isim−küçük 32 ± 1 px |
| `sembol_ust_246_cancer_libra` | yok (CL normal çift) → `yd_ust_ge_230` | sembol mürekkep üstü ≥ 230 |
| (yok) | `yd_halka_pay_ge_30` | mürekkep r ≤ 306 (336 − 30) |
| (yok) | `yd_sembol_alt_le_sinir` | sembol alt ≤ sabit çizgi − 32 |
| (yok) | `yd_yatay_orta` | kutu merkezi 476 ± 1 |
| (yok) | `yd_b3_y2_oran` | ölçek / s_max = 0,85 ± 0,005 ve üst = 230 + 0,75 · boş ± 1 px |
| (yok) | `yd_tarih_alt_795` | 795 ± 1 |
| (yok) | `yd_kucuk_alta_yasli` | iki küçük alt farkı ≤ 1 |
| SADE `yerlesim_ayni` | `bosluk_px[1:]` 32 ± 1 | sade:217 |
| `kucultme_le_sinir` | korunur, yeni modda **anlamsız** (KUCULT 0) | açık soru 3 |
| diğer tüm `kapi_sert` (leke, ton, IoU, dE00, görüntü yasağı, printful_dosya…) | aynen | değişmez |

Beklenti listesine (BEKLENEN_SONUC, aşama 2) eklenecekler:
- `yd_kapilar_hepsi`: her yeni çift `R['yeni_duzen'].kapi` hepsi True.
- `yd_bilinen_fail`: parça başı 4 vaka doğru FAIL.
- `cl_eski_mod_kontrol`: mevcut `cl_kontrol_her_parca` aynen.
- `en_uzun_sigar`: EN_UZUN için o4.kapi ve halka r ≤ 336.
- `eski_dosya_degismedi`: onaylı CL ve 41839101824 dosyalarının sha'ları koşu önce/sonra aynı.

Hiçbir mevcut beklenti satırı silinmez.

## 4. Aşama 2 koşusunun kurgusu (onay sonrası; bu aşamada YOK)

Kod (aşama 2 başında, yerelde test edilip tek commit):
- ornek78.py: `YENI_DUZEN` + eski mod kontrol adımı (b).
- yml: bölüm, env, klasör öneki (a).
- beklenen ve mantık testi: `--bolum` (a).
- EN_UZUN adımı (g).

Çiftler (11) ve parçalar (her parça ilk işi eski mod CL kontrolü):

| Parça | Çiftler | Kova'lı |
|---|---|---|
| 1 | TAURUS_TAURUS, CANCER_TAURUS, LIBRA_LIBRA | 0 |
| 2 | AQUARIUS_CANCER, ARIES_SCORPIO, LEO_SAGITTARIUS | 1 |
| 3 | AQUARIUS_AQUARIUS, CAPRICORN_CAPRICORN, CANCER_LIBRA (yeni) | 1 |
| 4 | AQUARIUS_PISCES, GEMINI_VIRGO | 1 |

Stiller: RUBY, SAPPHIRE, EMERALD, SADE_ALTIN, FILDISI (5).

EN_UZUN (1 iş):
- CANCER_LIBRA, RUBY + FILDISI.
- Tarih `SEPTEMBER 10, 2007` (§6 en geniş).
- İsim N harflik en uzun. N için §6 ve açık soru 1'e bakın; Serdar kararı gelmeden EN_UZUN koşulmaz.

Dosyalar:

| Yer | İçerik | Sayı |
|---|---|---|
| Drive `YENI_DUZEN/` (ayrı önek) | 11 çift × 5 stil `_954.png` | 55 |
| Drive `YENI_DUZEN/EN_UZUN/` | 2 PNG | 2 |
| Drive (eski klasör) | dokunulmaz | 0 değişiklik |
| Dal `docs/ornament/ornek/YENI_DUZEN_<damga>/` | BIRLESIK.json, BEKLENEN_SONUC.json, parça OLCUM / log, SIPARIS | yalnız JSON / MD / log |

Süre (tahmin, 41868179117 ölçümünden: normal ~245 sn, Kova'lı ~420 sn; paralel parça, runner kuyruğu hariç):
- Parça 1: 4 × 245 ≈ 16 dk
- Parça 2: 3 × 245 + 420 ≈ 19 dk
- Parça 3: 3 × 245 + 420 ≈ 19 dk
- Parça 4: 2 × 245 + 420 ≈ 15 dk
- Hazırlık, birleştirme ve EN_UZUN ile toplam ≈ 25-30 dk (tahmin).

DUR koşulları:
1. Eski mod CL kontrolü FAIL.
2. Bilinen FAIL vakalarından biri FAIL vermez.
3. Herhangi bir yeni çiftte `yd_*` ya da o4.kapi FAIL. Kapı gevşetilmez, liste Serdar'a.
4. Beklenti FAIL.
5. Eski dosya sha'sı değişti.
6. Koşu sonunda `aktif` geri alınmadı.

## 5. Ölçülen ve Merkez benzetimi (11 çift, yerel)

| Çift | Yerel w × h | Yerel üst / alt | Merkez w × h / üst |
|---|---|---|---|
| TAURUS_TAURUS | 295×246 | 294 / 540 | 308×254 / 302 |
| CANCER_TAURUS | 262×264 | 281 / 545 | 274×274 / 287 |
| AQUARIUS_CANCER | 336×246 | 294 / 540 | 346×254 / 301 |
| LIBRA_LIBRA | 500×240 | 299 / 539 | 512×246 / 307 |
| AQUARIUS_AQUARIUS | 460×117 | 391 / 508 | 474×119 / 402 |
| ARIES_SCORPIO | 367×243 | 297 / 540 | 378×250 / 305 |
| LEO_SAGITTARIUS | 265×282 | 268 / 550 | 280×297 / 269 |
| CAPRICORN_CAPRICORN | 348×206 | 324 / 530 | 359×211 / 333 |
| CANCER_LIBRA | 300×282 | 268 / 550 | 316×297 / 269 |
| AQUARIUS_PISCES | 214×280 | 269 / 549 | 230×297 / 269 |
| GEMINI_VIRGO | 267×259 | 285 / 544 | 297×272 / 288 |

Çizgiler (78 çiftte aynı, yerel ölçüm):

| Çizgi | y |
|---|---|
| tarih | 764-795 |
| isim satırı | 695-732 |
| küçük satır alt | 663 |
| H_MAX | 68 (68,78 nominal) |
| sabit üst | 594 |
| sembol alt sınırı | 562 |

- Yerel ölçüler Merkez'den %1,7-10,1 küçük, üst y 0-11 px yukarıda (Merkez değerleri: Merkez görev metni; testte sabit `MERKEZ11`). En büyük fark GEMINI_VIRGO genişliği: 267 / 297.
- Neden ölçülmedi. Olası: alfa maskesi ile `_ana` kutusu farkı ya da Merkez'in sınır tanımı. Açık soru 2.
- Halka payı tüm 11 çiftte ≥ 77 px (×0,85 sonrası). s_max'ı (×0,85 öncesi) bağlayan sınır çifte göre değişir: LIBRA_LIBRA, CAPRICORN_CAPRICORN, AQUARIUS_AQUARIUS'ta halka (r 306), CL ve LEO_SAGITTARIUS'ta dikey (230 / 562). ×0,85 sonrası 78 çiftte en büyük alt 550: `sembol_alt_le_sinir` hiçbir çiftte bağlamıyor (inceleme O1).
- "Çizgiler 78 çiftte aynı" yalnız sabit metin (EMILY / JAMES, JUNE 14, 2025) için doğru; isim ve tarih değişince kayıyor (§8 K2).

## 6. En geniş tarih ve en uzun isim (yerel ölçüm)

**Tarih.**
- Ölçüm: 12 ay × 31 gün × 2000-2035 = 13 392 bileşim, EBGaramond-Italic, motor ölçeği.
- En geniş: **`SEPTEMBER 10, 2007` = 328 px** (27,8 mm). 328 px'e SEPTEMBER'ın başka günleri de (29, 30, 31 dahil) 2007 / 2017 / 2027 ile ulaşır. Aday listesinde geçersiz tarihler (SEPTEMBER 31 gibi) de var; en geniş sonucu değiştirmez.
- Sığar: halka iç r max 328,75 ≤ 336, o4.kapi PASS.
- Merkez tahmini `SEPTEMBER 10, 2026` = **327 px** (Merkez ~312 dedi; ölçüm 327).
- Örnek `JUNE 14, 2025` = 215 px.

**İsim** (iki isim eşit, Cinzel, motor boyu; sınır halka r 336 + o4.kapi):

| İsim | Sonuç |
|---|---|
| W × 4 | PASS (r 327,8) |
| W × 5 | FAIL (r 357,0) |
| EMILY / JAMES | PASS (r 302,4) |
| MARY-JANE / O'NEIL (8 / 5 harf) | FAIL (r 346,4) |
| ALEXANDRIA / ANNA | FAIL (r 363,1) |
| MAXIMILIAN / CHRISTOPHER | FAIL (r 427,9) |

- **N (en kötü harf W) = 4.**
- Not: isim boyu karar 3 gereği değişmiyor. Eski düzende isim satırı daha aşağıdaydı: CL eski sembol alt 650, boşluk 20/20/20; kaynak `eq_head/OLCUM.json`, yerel. Bu yüzden eski düzende kapasite büyük olasılıkla daha düşük; **ölçülmedi**.

## 7. Açık sorular (öneriyle)

1. **İsim sınırı.** En kötü durum (W) 4 harf; 8 / 5 harflik gerçek bir çift bile 10 px taşıyor. Öneri:
   - İlan sınırı için ayrı ölçüm: gerçek isim listesi, örneğin en sık 200 İngilizce ad × ad, ile "çiftin %X'i sığar".
   - Sığmayan siparişte otomatik isim küçültme yok (karar 3); Serdar'a sorulur.
   - Karar Serdar'ın. EN_UZUN koşusu bu karar gelene kadar bekler.
2. **Alfa maskesi ile `_ana` sınır kutusu aynı mı?** Yerel test 6da763a girdi78 alfa maskesini kullandı; motor `_ana.png`. Öneri: aşama 2 parça başında iki kutuyu ölçüp `OLCUM`a yazmak (bilgi). Sonuçlar `yd_*` kapılarıyla zaten sert denetlenir.
3. **`kucultme_le_sinir` yeni modda anlamsız.** Öneri: kapı silinmez (karar 8). `yd_b3_y2_oran` bugünkü hâliyle onun yerini TUTMAZ (§8 K1); bağımsız ölçek kapısı aşama 2 kodunda yazılmalı.
4. **H_MAX nominal (h_oran × cap = 68,78).** Gerçek sprite alfa kutusu 1-2 px farklı olabilir. Öneri: aşama 2'de motor 12 sprite'ı ölçer, bilgi olarak yazar. Sabit çizgi nominal değerle 78 çiftte aynı kalır.
5. **Merkez benzetimi ile %2-10 fark.** Öneri: yerel değerler kod yoluyla birebir, aşama 2 gerçek `_ana` ile kesinleşir. Merkez tablosu güncellenir.

## 8. Bağımsız inceleme bulguları (E; tek ajan, "neden yanlış, kanıtla")

Ölçüm betikleri yerel (scratchpad `rv/`). 2 iterasyon sınırı dolduğu için **kod bu aşamada değişmedi**. Bulgular aşama 2 öncesi düzeltme listesidir.

| No | Düzey | Bulgu (kanıt) | Öneri | Durum |
|---|---|---|---|---|
| K1 | KRİTİK | `yd_b3_y2_oran` oranı `d['s']/d['s_max']` ile, yani yerleştirmenin kendi sözlüğünden ölçüyor; hep 0,85. Sembol 0,90× ya da 0,70× çizilip `d` bırakılınca 5 çiftte 8 `yd_*` kapısı PASS (inceleme t3). Bilinen FAIL "×0,90" yalnız meta veriyi değiştirdiği için FAIL veriyor. | Ölçek, çizilen sembolün kutusundan bağımsız ölçülür: kaynak kutu × s ile çizilen kutu karşılaştırması ve s_max ayrı yeniden hesap. ×0,90 vakası çizimi değiştirerek kurulur. | açık; aşama 2 kodu |
| K2 | KRİTİK | Sabit üst çizgi isim / tarih mürekkebine bağlı. Sembol alt sınırı EMILY/JAMES 562, ANNA/MARK 571, QUINN/JOSEPH (JULY 4, 2020) 560, SEPTEMBER 10, 2007 ile 565. J / Q inişi ve italik J tarih yüksekliğini değiştiriyor. Karar 3 sipariş düzeyinde karşılanmıyor. | Dikey çizgiler bir kez sabit referans metinden hesaplanır (taban çizgisi + harf yüksekliği); isim ve tarih bu tabana oturur. Karar 1'deki "alfa kutusu" tanımıyla çelişir: **Serdar kararı gerekir** (açık soru 6). | açık; karar |
| K3 | KRİTİK | 78/78 PASS'in kanıt değeri düşük. Kapılar, aynı kodun kurduğu çizgilerle ölçülüyor; `h_max = 0` hatası bile geçer. Girdi alfa maskesi, motorun `_ana.png`'si değil; 10 küçük işaret dikdörtgen. | Kapılar sabit beklenen değerlere (795, 32, 230, 306, 476) ve render sonrası PNG ölçümüne bağlanır; aşama 2'de gerçek `_ana` + gerçek sprite. | açık |
| O1 | ORTA | §5'teki "bağlayıcı 562 / 230" yanlıştı. | §5 düzeltildi. | düzeltildi (plan) |
| O2 | ORTA | `b3_olcek` sürekli nokta modeli; render ile en büyük ölçek / s_max 0,9977-1,0108. | Ölçek, render edilmiş alfa ile doğrulanır (ikili arama sonunda render kontrolü). | açık |
| O3 | ORTA | Negatif vaka yok: halka_pay, yatay_orta, kucuk_alta_yasli, isim-küçük boşluğu, o4_kapi. Sınırın geçen tarafı test edilmiyor. Vakalar yalnız dikeyde sınırlanan iki çiftte. | Her kapıya negatif vaka + sınır vakası; halkanın bağladığı bir çift (LIBRA_LIBRA) eklenir. | açık |
| O4 | ORTA | En geniş tarih / isim sığması testin çıkış koduna bağlı değil (test:213). | Tarih sığmazsa çıkış 1. | açık |
| O5 | ORTA | Yeni mod `hedef_kapat` (ornek5:381-384) adımını atlıyor. Alfa maskelerinde fark 0 px; `_ana` için ölçülmedi. | Yeni yolda da uygulanır ve kaydedilir. | açık |
| O6 | ORTA | `kucuk_ust_sabit` hiçbir kapıda yok; h_max nominal ve int ile kesik (68,78 → 68). | Gerçek 12 sprite ölçülür, yukarı yuvarlanır; küçük işaret üstü ≥ sabit çizgi kapısı. | açık |
| O7 | ORTA | Motorun `YENI_DUZEN=1` yolu hiç koşulmadı (C yalnız bayrak kapalı; D yalnız `yd` fonksiyonları). | Aşama 2 öncesi yerelde CL ile `YENI_DUZEN=1` motor + sade koşusu (CLAUDE.md HIZ 2). | açık |
| D1 | DÜŞÜK | Tarih kutu alt dışlayıcı (son satır 794); J inişi tarih tabanını aya göre 2 px oynatıyor. | K2 ile birlikte. | açık |
| D2 | DÜŞÜK | Boşluk kapısında logo yok (ölçülen logo-tarih 40, logo-küçük 33). | Satır kutusuna `sonsuz` eklenir mi: Serdar (karar 2 "isim+logo satırı"). | açık |
| D3 | DÜŞÜK | En geniş tarih eşitleri eksik yazılmıştı. | §6 düzeltildi. | düzeltildi (plan) |
| D4 | DÜŞÜK | "%2-10" aralığı; Merkez rakamları kaynaksız sabit. | §5 düzeltildi, kaynak yazıldı. | düzeltildi (plan) |
| D5 | DÜŞÜK | Test `<cikti>/_girdi` altına maske ve font yazıyor; `--cikti` docs altına verilirse sızma riski. | Girdi klasörü scratchpad'e ayrılır. Bu commit'te `_girdi` dala girmedi. | açık (risk yok bu commit'te) |
| D6 | DÜŞÜK | motor:244 yorumunda satır numaraları eski (265 / 357; gerçek 268 / 377). | Yorum düzeltildi (davranış değişmez). | düzeltildi |
| D7 | DÜŞÜK | `kapilar` g hesabında s_max = 0 bölme koruması yok. | K1 ile yeniden yazılır. | açık |
| D8 | DÜŞÜK | Yatay merkez 476 alındı; halka merkezi x 475,5. JSON'da 475,5 / 476 / 476,5. | Hedef: Serdar (476 mı 475,5 mi). | açık soru 7 |
| D9 | DÜŞÜK | 400k nokta üstü 18 çiftte kenar kısayolu (1 px dış dahil). | O2 ile birlikte. | açık |

Ek açık sorular:

6. **(K2) Dikey çizgilerin tanımı.** Karar 1-3 mürekkep kutusuyla tanımlı, ama isimdeki J / Q ve tarihteki italik J sembol sınırını 9-11 px oynatıyor. Öneri: çizgiler sabit referans metinle bir kez hesaplanır, isim ve tarih taban çizgisine oturur. Böylece 78 çift × her sipariş aynı olur.
7. **(D8) Yatay merkez** 476 mı, halka merkezi 475,5 mi? Öneri: 475,5 ± 1.

Aşama 2'ye geçiş koşulu: K1, K2 (karar), K3, O2-O7 kapanır, yerel test yeniden PASS. Bu, yeni bir aşama 1 iterasyonu ister (Serdar onayı).

## 9. Aşama 1b (Merkez, 4 Kas gece; Serdar kararları "katılıyorum": sabit referans çizgi, isim ölçümü, 475,5, logo dahil)

Yapılan (kod, yerel, Pillow 11.0.0 = iş akışı sürümü):
- K2: dikey çizgiler referans metinden (EMILY / JAMES / JUNE 14, 2025) bir kez; isim ve tarih taban çizgisine oturur (`yeni_duzen.referans_cizgi`, `yazi_yerlestir`).
- K3: kapılar `SABIT`e bağlı (tarih_taban 787,5; isim_taban 724; sonsuz_y 696; kucuk_alt 663; kucuk_ust_sabit 594; sembol_alt_sinir 562; h_max 69). Pillow 12.3.0'da tarih_taban 787,75 çıkıyor: sürüm farkı `ref_cizgi_sabit` ile yakalanır.
- K1 / O2: B3 ölçeği çizilen piksellerle (render ikili arama); kapı ölçeği yeniden hesaplar, ×0,85 sembolü yeniden çizer, ÇİZİLEN kutuyla 1 px karşılaştırır. Render / nokta modeli oranı 0,9973-1,0120 (78 çift).
- D2 logo boşluk kapısında; D8 merkez 475,5; O3 her kapıya negatif vaka (3 çift × 15 = 45); O4 tarih sığmazsa çıkış 1; O5 `kapat` yolu; O6 h_max yukarı yuvarlama + `kucuk_ust_ge_sabit`; D5 girdi /tmp; D7 kısmen.
- Aşama 2 kodu (koşulmadı): `URETIM78_CIFTLER.json` "yeni_duzen" bölümü (aktif DEĞİŞMEDİ, "ornek"), uretim78 (cl_yeni_parca, KONTROL_ESKI, cift_sonu kontrol bayrağı, birlestir kontrol_ad), ornek78 (kontrol CL alt süreçleri YENI_DUZEN=0, sondaki CL üretim), beklenen `--bolum yeni_duzen`, yml (hazırlıkta `yeni_duzen_yerel_test.py --yalniz_kapi`, klasör öneki YENI_DUZEN, parça env).

Sonuç (yerel; `ornek/YENI_DUZEN_YEREL_1B_20261104/`):
- ref = SABIT; 78/78 PASS; bilinen FAIL 45/45 beklenen kapıdan.
- En geniş tarih SEPTEMBER 10, 2007 = 328 px, sığar.
- İsim: N (W) = 4. SSA (ssa.gov, 1926-2025 ilk 100 + 100): bugünkü boyda erkek × kadın çiftlerinin %66,0'ı sığar (eşik toplam genişlik 331 px; yaklaşık, aşağıdaki K-1b-3). İki SAMANTHA için isim %29, iki JACQUELINE için %35,2 küçülmeli (bilgi; karar 3 gereği boy sabit).
- Testler: uretim78_mantik_testi 86/86, sikilastirma_mantik_testi PASS, test_workflows 494 YAML PASS, py_compile 0.
- Yerel test ÇIKIŞ 1: isim eşiğinin "yalnız toplam genişliğe bağlı" varsayımı tutmadı (JENNIFER / GRACE toplam 329 < 331 ama taşıyor). Geometri kapıları temiz; isim oranı yaklaşık.

DUR (HIZ VE KALİTE 4: 2 yerel iterasyon). Aşama 2 Actions koşusu YAPILMADI. Bağımsız inceleme (tek ajan) 15 bulgu; aşama 1c listesi:
- K-1b-1 YÜKSEK: `o5.hedef_kapat` 3. değeri dict; `sembol_yerlestir` `int(n_)` yapıyor: YENI_DUZEN=1 motoru her çiftte çöker. Yerel testte `kapat` vakası yok.
- K-1b-2 YÜKSEK: O7 açık: motor + dump + sade YENI_DUZEN=1 hiç koşulmadı (yerel ölçüm alfa maske + dikdörtgen işaret; motor `_ana`, gerçek sprite, kenar_onar, hedef_kapat).
- K-1b-3 ORTA: isim oranı için toplam genişlik varsayımı yanlış; her çift tek tek denenmeli (ya da sol/sağ uç ayrı).
- K-1b-4 ORTA: sondaki CL düşerse kontrolün eski düzen PNG'leri Drive'a gider; kontrol sonrası O/CANCER_LIBRA_* ve YAKIN_CANCER_LIBRA_* taşınmalı.
- K-1b-5 ORTA: `kenar_kayit` onarımsız motoru kontrol CL'de `ek_env` olmadan çağırıyor.
- K-1b-6 ORTA: `b3_en_buyuk` FAIL veremez (zayıf); çizimden ölçülmeli ya da kaldırılmalı.
- K-1b-7 ORTA: `ref_cizgi_sabit` için bilinen FAIL yok (h_max 68 / 0, taban +0,25).
- K-1b-8 DÜŞÜK-ORTA: taban kapıları üst veriden; sipariş için mürekkep taban ölçümü gerekir.
- K-1b-9 DÜŞÜK-ORTA: hazırlık testi benzetim (alfa maske); etikete "benzetim", ya da gerçek sprite ile.
- K-1b-10 DÜŞÜK: bilinen FAIL sayısı `> 0` yerine `== 45`.
- K-1b-11 DÜŞÜK: s_max <= 0 durumunda çöküş yerine FAIL.
- K-1b-12 DÜŞÜK: sade boşluğu isim1+isim2 (logo hariç); bugün sayı aynı, tanım farklı.
- K-1b-13 DÜŞÜK: `yeni_duzen_kapilari_var` tarih metnini denetlemiyor.
- K-1b-14 DÜŞÜK: PARCA dışı eski çağrıda CL ilk sırada değilse kontrol sayılmıyor (bugünkü çağıranlar etkilenmez).
- K-1b-15 DÜŞÜK: hazırlık yerel testinin süresi ve belleği Actions'ta ölçülmedi (yerelde 15-18 dk; tüm maskeler önbellekte tutulunca 8 GB'ta OOM, düzeltildi).
