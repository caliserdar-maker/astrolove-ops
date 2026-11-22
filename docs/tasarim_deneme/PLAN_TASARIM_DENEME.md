AÇIK YÜKSEK BULGU: kombinasyon yolu K-a'da çizilmeyen küçük burçların geometri maskeleri kapı 2 sembol bölümünün "örtülen piksel" hesabına girer (ATK:415-423, 427) ve B1'de görünen sembol piksellerini sert renk / kenar karşılaştırmasının dışına atar; plan bunu "kapı 2 tanımı değişmez" diye yazıyor ve soru 6 k / 18 a'da adıyla sormuyor (2. inceleme turu; DÜZELTİLMEDİ, ayrıntı dosyanın sonundaki inceleme kaydında).

# PLAN: TASARIM DENEME ARACI (parça 1: yerleşim)

Aşama 1 (yalnız plan), düzeltme turu 2. Kod, görsel, Actions koşusu, Etsy okuma / yazma YOK. Bu plan Merkez'de kodla kontrol
edilip Serdar onaylayınca ayrı görevle kodlanır. Plan hangi seçeneğin güzel olduğunu söylemez; araç da seçenekleri puanlamaz,
sıralamaz, "önerilen" diye işaretlemez (Serdar 10 ve 11 Kas).

## Düzeltme kaydı (tur 2)

Önceki sürüm: fdf9658 (main f89f55d'ye göre). "PLAN:n" o sürümün satır numarasıdır.

| Madde | Değişen bölüm | Ne değişti |
|---|---|---|
| D1 taban | 0, 1.1, 1.1b (yeni), 1.2, 2.3, tüm atıflar | AY_SHA = main a9b1323. Tüm AT / ATK / ATT atıfları yeni main'de yeniden okundu. Yeni fonksiyonlar (halka_kalinlastir, logo_kaynak, halka_kalinlik_olc), grup_kur imzası, yeni gren dalı, kapı 2 logo koşulu tablolara girdi. Eskiyen cümleler düzeltildi (halka mm notu, bölüm 5 halka formülü, grup kapısı eşdeğerlik testi, 7.3 önbellek, soru 2b, PLAN:269 atfı YD:45). |
| D2 logo | 1.2, 3.2, 3.3, 4.2, 6.1, 9, soru 3 ve 7 | Logo ay takvimi kodundan içe alınır (kesim, temizlik, motor adı, yer, boy birimi yazıldı). logo_yer'e "küçük burçların arası" eklendi; 'ust' / 'alt' çıkarıldı (emsali yok). Boy birimi farkı ve temizlik gerilimi adıyla yazıldı. |
| D3 başlangıç adayları | 3.3, 3.4, 4.1, 9, soru 5 ve 17 | B1 "bilinen çakışma" etiketiyle ve ölçümüyle yazıldı. Varsayılan taban plan tarafından SEÇİLMEDİ (soru 5). Ornament birebir için ek dilim tanımlandı. B2 sığması "ölçülmedi"; logosuz dilimde 'iki_yan' geri dönüşü yazıldı. |
| D4 kombinasyon ve kapı 2 | 4.3, 6.2, 6.4, 8, soru 6 k ve 18 | Kombinasyonda kapı 2'nin hangi listeyle kurulduğu ve ne ölçtüğü, çizilmeyen öğenin diğer kapılardaki yeri (kapsam daralması) ve eşiksiz yeni ölçüm yazıldı; iki yol soruya bağlandı. |
| D5 B4, B5, B6 | 3.3, 4.2, 8 | "Tek öğe değişir" testi birleştirme öncesi katmanda tanımlandı, gren sınırı yazıldı. halka_r ilk geçişi küçük hedefle; büyük tuvalde aralık üst ucu yazıldı. 'poster' sözcüğü sayıya çevrilmiyor; eşdeğer ayarda bayt eşitliği iddiası kaldırıldı. |
| D6 B7 | 6.1, 6.2, 6.4, soru 6 c - e, l | Çıktı kapısının sert yapılması ve ornament'te sert olan yasak bölge / çakışmanın ölçer yapılması adıyla soruya eklendi; tabana ve ornament emsaline göre ayrılmaların tam listesi 6.4'te. |
| D7 B8 | 0, 6.2, soru 2 | Yıldız FAIL'i "olası, ölçülmedi"; halka mm hükmü aralık ucuna göre düzeltildi. |
| D8 çok seçenek | 3.5, 4.5 (yeni), 4.6 (yeni) | Sınırlayan yerlerin listesi, süre bütçesinden hesaplanan sınır, genişletme yolları ve maliyetleri, yeni düzen ekleme yolu, renk / doku arayüzü, sıralı karar hesabı. |
| D9 iki adımlı süreç | 5.1 (yeni), 8 | İki yol (tek adım / iki adım): dosyalar, süre, disk, Serdar'a giden dosya sayısı, kural kontrolü testleri. Hangisinin uygulanacağı soru 15; "son ürün" sınırı soru 16. |
| D10 | 7, 9, 10 | Süre ve dilimler güncellendi. Sorular üç başlıkta; 1 - 13 numaraları korundu, 14 - 19 eklendi. |

## 0. Ref'ler, kısaltmalar, etiketler

| Kısaltma | Dosya | Ref |
|---|---|---|
| AT | scripts/ay_takvim/ay_takvim_ornek.py (1737 satır) | main a9b1323 |
| ATK | scripts/ay_takvim/ay_takvim_kapi.py (713 satır) | main a9b1323 |
| ATT | scripts/ay_takvim/test_ay_takvim.py (1704 satır) | main a9b1323 |
| W | .github/workflows/ay-takvim-ornek.yml (273 satır) | main a9b1323 (f89f55d'den beri değişmedi) |
| CM | CLAUDE.md | main a9b1323 (f89f55d'den beri değişmedi) |
| YK | scripts/kapak78/yd_kontak.py | main a9b1323 |
| OM | scripts/printful/ornament_motor.py | ornament-printful-katalog c950151 |
| O1, O2, O3, O4, O5 | scripts/printful/ornament_ornek.py, _ornek2, _ornek3, _ornek4, _ornek5 | aynı, c950151 |
| YD | scripts/printful/yeni_duzen.py | aynı, c950151 |
| YDT | scripts/printful/yeni_duzen_yerel_test.py | aynı, c950151 |
| MG | motor_gpt/ (golge_motor.py, olustur_alfa_sablon.py, cember.json, girdi/ ...) | siparis-gpt 6da763a |

- main HEAD (bu turda `git fetch` sonrası): a9b13230d64e9c0f5937e0e8af07530dc13f3079. Görev metnindeki a9b1323 ile AYNI.
  f89f55d'den bu yana iki commit (eaad7fc, a9b1323); ikisi de yalnız scripts/ay_takvim altındaki üç dosyayı değiştiriyor
  (`git diff --stat`: değişen satır AT 194, ATK 107, ATT 177; toplam 458 ekleme, 20 silme; W ve CM farkı boş).
- Okuma yöntemi: yalnız `git fetch / show / log / diff` ve metin okuma. Depodaki hiçbir betik çalıştırılmadı. Hesaplar bu
  oturumun kendi aritmetiğidir (iki PNG'nin yalnız boyutu git nesnesinden okundu). Drive, Actions çıktısı, sipariş verisi
  okunmadı.
- Rakam etiketleri: [kod] = dosyada yazılı değer; [hesap] = koddaki değerlerden bu planda yapılan aritmetik; [kayıt] = AT
  başlığındaki yerel ölçüm notu (Merkez doğrulamadı); [kontrol ölçümü] = Otomasyon sayfasının 11 Kas ölçümü (görev metni;
  bu oturumda yeniden ölçülmedi); [tahmin] = ölçülmedi, akıl yürütme; [varsayım] = doğrulanmamış girdi; [ölçülmedi].
  "Başlangıç değeri" yazan her aralık, adım ve sınır [tahmin] sınıfındadır: kaynağı yoktur, yalnız yanlış girişi yakalamak
  ya da ilk koşuyu sınırlamak içindir, ilk ölçümle ve Merkez / Serdar kararıyla kesinleşir.

En önemli üç bulgu (ayrıntı ilgili bölümde):

1. Altın yolu, sembol grubu, halka kalınlığı, logo ve doğrulama ay takvimi kodundan DEĞİŞTİRİLMEDEN içe alınabilir; takvime
   özel olan `uret` gövdesi, takvim geometrisi ve kapı betiğinin tek gövdeli `kapi_olc` fonksiyonudur (bölüm 1). Ornament
   örnek modülleri 954 px tuvale ve başka bir altın yoluna (tek_doku) bağlı: ornament'ten kod değil, ölçü ve kapı TANIMLARI
   alınır.
2. Ay takvimi kodu sembol grubunu TEK oranla kurar: ana sembol halkadan bağımsız boyutlanamaz, küçük burçlar yalnız simetrik
   yerleşir. Bu yüzden ornament düzeni birebir verilemez ve ornament çevrimi olan B1 adayında küçük burçlar ana sembole
   biner [kontrol ölçümü] (3.4, 4.1). Birebir ornament ayrı dilim ve ayrı karardır (soru 17).
3. Deneme girdisinde (1087 px, 25,4 mm, eşleme [varsayım]) onaylı öğeler üretici alt sınırının altında kalıyor [hesap]:
   orantılı poster halkası B1 yarıçapı ile planın üst ucu arasında (halka_r 0,884 - 1,20; Rg 543,5 px) 3,2 - 4,4 px =
   0,076 - 0,10 mm, alt uçta (halka_r 0,30) 1,1 px = 0,026 mm (sınır 0,2 mm; aralığın hiçbir yerinde sınıra ulaşmaz); ornament oranıyla isim büyük harfi en çok 40 px = 0,94 mm (sınır 1,5 mm; güvenli yarıçap
   543,5 px'i aşamaz varsayımıyla). Araç bunu gizlemez, işaretler (soru 2 ve 4).

## 1. Taban teyidi ve seçimi

### 1.1 İlk görevin Dayanak 7 maddelerinin kodla teyidi (atıflar a9b1323'e güncellendi)

| Madde | Sonuç | Kanıt / düzeltme |
|---|---|---|
| 7a deneme düzeni | TEYİT | AYAR açıklaması AT:43-49; AYAR_ANAHTAR AT:113-114; AYAR_ARALIK AT:115-118; AYAR_SERBEST AT:119; DENEME_AZAMI AT:124; ayar_varsayilan AT:210; ayar_dogrula AT:219; ayar_listesi AT:277; ayar_kur AT:1323. İş akışı mod deneme W:6-12, W:22-23, W:46-50. Sert / ölçen ayrımı AT:45-47, ATK:49-53. |
| 7b OM içe alınamıyor | TEYİT, satır düzeltmesi | OM tek main(): OM:106-837 (837 son `return`; de00 OM:840 modül düzeyinde). Taşınan fonksiyonlar AT:6-17: Motor AT:685, golgele_oge AT:719, harita_kur AT:793, oge_katman AT:815, metin_alfa AT:532, metin_alfa_k AT:546, renk_uyum AT:618. Örnek modülleri içe alınıyor: O5:29, O4:31, O3:31-32. |
| 7c sembol grubu | TEYİT | grup_kaynak AT:1044, grup_kur AT:1186. KUCUK_U yalnız CANCER_LIBRA AT:107; başka çiftte DUR 'grup_cift' AT:1050-1051. Kapı tarafında bağımsız kopya ATK:205-206. |
| 7d diğer parçalar | TEYİT, bir ek | isim_dogrula AT:167, metin_dogrula AT:184, isim_sigdir AT:558, cizim_katsayisi AT:577, altin_ogeler AT:846, zemin_radyal AT:894, zemin_yildiz AT:922, sembol_yukle AT:981, rgba_olcek AT:1020, sembol_yerlestir AT:1030. mm hesabı yalnız halka için ve DPI sabitiyle: AT:76, AT:1283; kapı tarafında halka ve logo mm bilgileri de U.DPI ile (ATK:188, 287, 329). Kapılar: kontrast_olc ATK:104, grup_kapisi ATK:209, kapi_olc ATK:363. Ek: tarih için ayrı öğe YOK; tarih 'satirlar' içinde serbest metin (W:206). |
| 7e takvime özel | TEYİT, ekler | Tuval AT:74-76; AYLAR, BASLIK AT:78-79; ay_verisi AT:310; veri_kapisi AT:337; yerlesim_kur AT:351; dikey_yerlesim AT:501; uret AT:1373-1645 (tek fonksiyon). Ek: tuval sabitleri W, H, S şu fonksiyonların İÇİNDE de kullanılıyor: isim_sigdir AT:561 (varsayılan sınır), yerlesim_bul AT:489, sembol_yukle AT:1013, _kesisim AT:1367, disk_ciz AT:1308-1309, grup_kur AT:1283 (DPI). Kapı tarafında grup_kapisi ATK:219 (U.S) ve ATK:248 (META disk merkezi). |
| 7f ornament'te olup takvimde olmayan | TEYİT, iki ek | Logo: logo_kaynak O4:156, logo_olc O4:176. Yuvarlak alan: O4:34-42; yasak_m O4:219; kapi O4:239; yerlesim_A O4:282, yerlesim_B O4:303. Yazı bloğu: yazi_blogu O3:208, alt_sinir O3:274. mm çıktısı: O1:299-301, O4:550-557, O5:765-767. Ek 1: bu fonksiyonlar modül sabitlerine bağlı (N = 954 O1:34; MM = 25,4 / 300 O1:42; CX, CY O4:34; O4, O3'ün C sabitini içe alırken DEĞİŞTİRİYOR O4:35; YASAK ve GLOW_K main içinde atanıyor O4:475-477, O5:518-520). Ek 2: O1-O5 altın yolu tek_doku modeli (O1:109-127; tek_doku.py kaynak klasöründen O4:478-479), OM / AT'nin motor yolu değil. |
| 7g bağımlılıklar | KISMEN DÜZELTME | Motor sabit sha: W:26, W:68; AT:6-7. Motor ortam değişkenlerini değiştiriyor AT:694, ayrıca sys.path'e ekliyor AT:703-704. golge_motor ortam değişkenlerini içe alınırken ve her çağrıda okuyor (MG golge_motor.py:3-7, 227-229): süreç başına tek motor, tek KILIT. Öğeden öğeye taşan gizli durum yok (egim_tup öznitelikleri her karoda sıfırlanıyor AT:741, 756-761). DÜZELTME: LOGO_1.png depoda var (MG girdi/LOGO_1.png, 6da763a; poster hattı aynı dosyadan kesiyor MG olustur_alfa_sablon.py:69; YDT:57-60); a9b1323'te ay takvimi kodu da bu dosyayı okuyor (AT:1164) ve motor dosyası sayıyor (AT:127-129). O4:496 ve O5:532 dosyayı kaynak klasöründen okuyor; o klasörün dosyası ile depodaki dosyanın bayt eşitliği [ölçülmedi]. Ortam W:95-97; CM:93-97. |
| 7h kaynak ve süre | TEYİT, bir not | Ana katman Drive'dan W:124-136. Yerel deneme sembolü deneme_komut AT:1679-1697. Süre notu AT:48-49 [kayıt]. Sabit sha kalıbı W:26-27, W:67-79. Not: bu Code oturumunda Drive bağlayıcı araçları listeli (kullanılmadı, denenmedi); "Code ortamı Drive okuyamaz" bu oturum için doğrulanmadı (bölüm 10 soru 1). Bu oturumun kabında cv2 kurulu değil (ölçüm: içe alma hatası), Pillow 12.3.0 (iş akışı 11.0.0), Python 3.13.18, 4 çekirdek. |
| 7i pafta emsali | TEYİT | pafta() YK:26-53: (etiket, yol) listesi, hücre + etiket bandı, eksik dosya hücresi kırmızı. Yalnız Pillow (YK:12). |

### 1.1b Yeni taban (main a9b1323) teyidi

Görev metnindeki "yeni taban" maddeleri kodla karşılaştırıldı; hepsi TEYİT, ekler aşağıda.

| Madde | Sonuç | Kanıt |
|---|---|---|
| a. AYAR | TEYİT | AYAR_ANAHTAR AT:113-114 (halka_kalinlik, halka_centik, logo eklendi). Aralıklar AYAR_ARALIK AT:115-118; halka_kalinlik 1,00 - 4,00 ve logo 0,50 - 2,00 AT:116. AYAR_SERBEST AT:119 (logo 'yok'). HALKA_CENTIK AT:120, CENTIK_ACI AT:121, LOGO_KUTU AT:122, LOGO_OLCEK AT:123. Varsayılanlar AT:214 (halka_kalinlik 1,0; halka_centik 'ozgun'; logo 'yok'). Doğrulama: halka_centik AT:243-248; 'yumusak' yalnız halka_kalinlik > 1 iken AT:261-262 (grup_kur'da ikinci koruma AT:1243-1244). Ek: MOTOR_DOSYA'ya girdi/LOGO_1.png eklendi AT:127-129. |
| b. halka ve logo | TEYİT | halka_kalinlastir AT:1075-1156: çizgi kalınlığı çarpanı, halkanın merkez çizgisi etrafında radyal genişletme; çarpan 1,0'da kaynak aynen döner (AT:1088-1089). logo_kaynak AT:1159-1175: kesim LOGO_KUTU (AT:1163-1164), kırp > 8 (AT:1165-1166), x 0,994 (AT:1168), pad 40 + alfa temizliği (AT:1169-1170), yer yatayda halka merkezi, dikeyde küçük burç satırı (AT:1171-1172), motor adı 'sonsuz' (AT:1175). Poster karşılıkları MG olustur_alfa_sablon.py:69-70, 83-86. grup_kur AT:1186-1286, imza AT:1186-1187 (halka_kalinlik, halka_centik, logo). Grup ölçeği ve çevre dairesi özgün halkayla ve LOGOSUZ hesaplanıyor: açıklama AT:1193-1198, kod AT:1217-1225 (logo listeye sonra ekleniyor AT:1245-1253). |
| c. gren | TEYİT | altin_ogeler AT:846-890. Kalınlaşmış halka ayrı üreteçten (tohum [11, 1]) boyanıyor, ana üreteç özgün halka boyu kadar ilerletiliyor AT:867-869; rng_boy AT:1229-1239, 1271-1272. Ek: 'yumusak' çentikte aynı ayrı üreteçle ikinci bir katman çizilip bant dışı pikseller ondan alınıyor AT:875-883. |
| d. kapı | TEYİT | halka_kalinlik_olc ATK:174-189 (yalnız bilgi; mm alanı U.DPI ile ATK:188). grup_kapisi ATK:209-360. Logo ayarda varsa grupta 4. öğe zorunlu, yoksa olamaz ATK:221-223, 234. Kalın halkada en uzak piksel ölçütü "ölçerek geri alma" ile aynı tek nokta ATK:257-283. Logo ölçümü (yer, boy; aynı 2 px pay) ATK:322-343. Öğe sayısı tamlığı logoyu sayıyor ATK:487-488. |
| e. deneme sınırı | TEYİT | DENEME_AZAMI = 6 AT:124; kontroller AT:298-299, 1331. Süre notu AT:48-49 [kayıt]: bütçe 50 dk, zaman aşımı 60 dk; formül 6'dan büyük sonuç verir, 6 ayrıca konmuş üst sabittir. Bu sınır ay takvimi iş akışına aittir; genel araç kendi sınırını süre ölçümünden hesaplar (4.5). |
| f. kararlar | BİLGİ | Halka 2 kat, çentik 'yumusak', logo 1,25 kat: ay takvimi kararlarıdır (görev metni); kod varsayılanları değişmedi (AT:214). Genel araç için karar değildir (soru 2 ve 7). |

### 1.2 Fonksiyon tablosu

Sütun "Kullanım": A = aynen (içe alınır, satır değişmez); P = parametre ister (içe alınır, yeni kod eksik parametreyi verir ya da
sarmalar); Ö = ürüne özel kalır (içe alınmaz); T = tanım alınır (kod değil; yeni kodda genel yazılır, eşdeğerlik testi kaynakla).

| Fonksiyon / blok | Yer | Kullanım | Neden |
|---|---|---|---|
| Dur, log, bildir, sha | AT:145-163 | A | Genel. Çıkış kodu düzeni (3 girdi, 4 DUR, 2 çöküş) AT:51 korunur. |
| isim_dogrula, metin_dogrula, cift_dogrula | AT:167, 184, 202 | A | Tuvalden bağımsız; sınırlar METIN_SATIR_AZAMI, METIN_KARAKTER_AZAMI AT:142. |
| ayar_dogrula, ayar_listesi | AT:219, 277 | T | Doğrulama kalıbı (bilinmeyen anahtar, aralık, tür, yinelenen anahtar, ham girdi basmama) genel; ANAHTAR ve ARALIK tabloları takvime bağlı (AT:113-119, 231-236). Yeni araçta aynı kalıp kendi tablosuyla; isim ve satır kontrolü AT fonksiyonlarını çağırır. |
| _font, _punto, metin_alfa, metin_alfa_k | AT:517-555 | A | Tuvalden bağımsız (cap px girdisi). |
| isim_sigdir | AT:558-574 | P | `sinir`, `cap0`, `cap_alt`, `yumusak` parametre; varsayılan sınır W'ye bağlı (AT:561). TEK metnin mürekkep kutusunu ölçer (AT:564-566): 'tek_satir' düzende aynen (sınır = o satırın kiriş genişliği). 'iki_yan' düzende satır = isim1 + boşluk + logo + boşluk + isim2 (O3:213-226); genişlik hesabı yeni yazılır, küçülme kuralı aynı. Dikkat: yumusak=True iken de 8 denemede sığmazsa 'isim_sigmadi' DUR (AT:572-573); bu sert kalır (6.1). |
| cizim_katsayisi | AT:577 | A | POSTER_CAP 298 (AT:85) motor sabiti. |
| kutu, labf, de00, renk_uyum, yari_kal | AT:582-640 | A | Tuvalden bağımsız. renk_uyum < 200 çekirdek piksel DUR (AT:622-623). |
| boya | AT:643-681 | A | Herhangi tuval (AT:644). |
| Motor (init, golgele_oge, gorunen, poster_ana, harita_kur, oge_katman) | AT:685-843 | A | Tuvalden bağımsız. Yan etki: ortam + sys.path (AT:694, 703-704). |
| altin_ogeler | AT:846-890 | A | Yazı ve grup öğeleri aynı giriş. Ana üreteç tohum 11, öğe SIRASIYLA (AT:854): sıra çıktıyı (gren) etkiler. Yeni dal: 'rng_boy' taşıyan öğe (kalın halka) ayrı üreteçten boyanır, ana üreteç özgün halka boyu kadar ilerler (AT:867-869); 'yumusak' çentikte ikinci katman çizilir (AT:875-883). Grup öğesinde kaynak uint8 beklenir (AT:862). Bölüm 7.3. |
| zemin_radyal, zemin_yildiz, zemin_8bit | AT:894-977 | A | Tuval boyu, ölçek, merkez parametre. |
| sembol_yukle | AT:981-1017 | P | Biçim kapısı genel; AT:1013-1016 takvimin spiral ölçeğini hesaplayıp > 1 ise DUR veriyor (kaynak çevre yarıçapı < 479,7 px [hesap: 0,78 x 205 x 3] olursa yanlış DUR). İlk dilimde aynen çağrılır, bu koşul OLCUM'a yazılır. |
| rgba_olcek | AT:1020 | A | |
| sembol_yerlestir | AT:1030 | A | Grupsuz kombinasyon (ana sembol tek başına) için. |
| grup_kaynak, _dis_noktalar, grup_kur | AT:1044-1072, 1178-1286 | P | Geometri `hedef_r` ile tuvalden bağımsız. İmza (AT:1186-1187): merkez, kucuk_u, kucuk_v, kucuk_oran, halka_kalinlik, halka_centik, logo. bilgi['halka_kalinlik_mm'] artık çarpanı içeriyor ama hâlâ DPI 300 ile (AT:1283): yeni araç bu alanı KULLANMAZ, mm'yi ürün girdisinden kendi hesaplar. Yalnız CANCER_LIBRA (AT:107). ÖNEMLİ: (1) grup TEK oranla kurulur: çevre dairesi ana sembol + halka + küçük burçlardan (AT:1217-1224), ölçek AT:1225, ana sembol bu ölçek x poster oranıyla (AT:1215, 1256): ana sembol halkadan bağımsız boyutlanamaz; küçük burç ayarı değişince grup yeniden boyutlanır. (2) Çevre dairesi ve ölçek özgün halkayla ve logosuz hesaplanır (AT:1193-1198): halka kalınlığı ve logo başka öğeyi değiştirmez. (3) Küçük burçsuz kurulum parametresi yok (AT:1059-1071). Sonuçları: 3.3, 3.4, 4.2, 4.3. |
| halka_kalinlastir | AT:1075-1156 | A | grup_kur içinden çağrılır (AT:1241-1242). Genel araçta açılması soru 2; kapalıyken çarpan 1,0 ve kaynak aynen döner. |
| logo_kaynak | AT:1159-1175 | A / P | Küçük burç arası yerde grup_kur içinden aynen (AT:1247). İsim arası yer için alfa yine buradan alınır, yerleştirme ve kapı yeni yazılır (3.2; dilim 3). Kesim ve temizlik kararı ay takvimine aittir (soru 7). |
| ayar_kur, uret, ayar_komut, sembol_komut, main | AT:1323-1728 | Ö | Takvim akışı. Deneme sembolü komutu deneme_komut (AT:1679) yerelde aynen ÇAĞRILIR. |
| ay_verisi ... dikey_yerlesim, disk_ciz, duz_yazi, _kesisim | AT:310-513, 1290-1370 | Ö | Takvim geometrisi. _kesisim 6 satır, W / H'ye bağlı: yeni kodda parametreli yazılır. |
| ESIK, kontrast, kontrast_olc, yatay_yayilim, cember_uydur | ATK:73-123, 166-171, 192-201 | A | Tuvalden bağımsız. Bant 6-12 px sabit (ATK:111-112), emsal O5:421-438 (954 px tuval). |
| grup_kapisi | ATK:209-360 | P | hedef_r'yi U.S ve 'sembol_alan' ile kuruyor (ATK:219), META 'disk' okuyor (ATK:248). Öncelikli yol: grup_kapisi DEĞİŞTİRİLMEDEN, araç tarafından kurulan sentetik META ile çağrılır (emsal ATT:1526-1528: testte META 'disk' alanı elle kuruluyor; grup_oran x sembol_alan x 3 = hedef yarıçap olacak biçimde); bunun bütün alanlarla çalıştığı kod yazılırken doğrulanır. Çalışmazsa yeni kapı aynı iki kanıtı (yeniden kurulum + bağımsız ölçüm) kendi META'sıyla kurar; içerideki ölçüm yardımcıları aynen çağrılır. Yeni koşullar da aynen taşınır: öğe listesi ayara göre (logo varsa 4 öğe; ATK:221-223, 234), kalın halkada en uzak piksel "ölçerek geri alma" ile (ATK:257-283), logo yer / boy ölçümü (ATK:322-343). Eşdeğerlik testi: takvim META'larıyla (halka kalınlığı 1,0 ve 2,0; logo yok ve var) iki kapı aynı sayıları vermeli. |
| halka_kalinlik_olc | ATK:174-189 | P | Maskeden çizgi kalınlığı (px) tuvalden bağımsız; mm alanı U.DPI ile (ATK:188): px alanları kullanılır, mm ürün girdisinden. |
| evre_olc, kapi_olc, ozet_yaz | ATK:126, 363, 626 | Ö | Tek gövde; evre, disk, 12 ay adı sayımı içinde. |
| sirt_genislik, delik_say, logo_olc (ornament logo ÖLÇÜMÜ) | O4:164-198 | T | Logonun kaynağı artık AT'den (yukarıda); ornament'in logo_kaynak'ı (O4:156-161) yalnız soru 7a "ornament kesimi" çıkarsa gerekir. Ölçüm fonksiyonları saf ama O4'ü içe almak O3, O2, O1'i ve modül sabitlerini de yükler. Yeni kodda aynı satırlar, ATT kalıbıyla (kaynak dosyadan çıkar, aynı girdiyle karşılaştır; ATT:11-12, 39-46) eşdeğerlik testi. |
| yasak_m, kapi, goruntu_yasak | O4:219-270, 425-437 | T | 954 sabitlerine bağlı. Ürün girdisinden okuyan genel karşılığı; 954 sabitleri verilince O4 ile aynı piksel sayısı (test). |
| yazi_blogu, alt_sinir, yerlesim_A / B, yerlesim_V5, yeni_yerlesim | O3:208, 274; O4:282, 303; O5:374; YD | T | Bunlar "sığan en büyüğü ara" çözücüleri (ör. O4:289-299), ayar alan yerleşim değil. Araçta yer ve boy AYAR'dan gelir, arama yok. Onaylı sonuç değerleri kütüphane başlangıç kaydına sayı olarak taşınır (bölüm 3.4). |
| mm çıktısı | O1:299-301, O4:550-557 | T | Kalıp: kutu px x MM. Yeni araçta MM ürün girdisinden. |
| pafta | YK:26-53 | T | Dosya adı ve CSV akışına bağlı değil ama hücre oranı 4:3 sabit (YK:28). Yeni araçta kare / dikey hücre gerekir; aynı düzen yeniden yazılır. |

### 1.3 Sonuç: yuvarlak şekil için hangi parça hangi tabandan

- Ay takvimi kodundan (içe alma): doğrulama yardımcıları, yazı çizimi, altın yolu (Motor, altin_ogeler, renk_uyum, boya),
  zemin, sembol yükleme, sembol grubu (grup_kur; halka kalınlığı ve logo dahil), ölçüm yardımcıları (kontrast_olc,
  cember_uydur, yari_kal, halka_kalinlik_olc). Neden: altın yolunun içe alınabilen TEK kopyası burada (OM tek main), her
  taşınan adımın kaynakla eşdeğerlik testi var (ATT:11-12).
- Ornament'ten (tanım ve sayı; kod değil): yuvarlak güvenli alan / yasak bölge kapısı tanımı, logo ölçümü, öğe başına mm
  çıktısı, onaylı yuvarlak yerleşimin sayıları. Neden: modüller 954 tuvale ve tek_doku yoluna bağlı.
- Yeni yazılacak (hiçbir tabanda yok): ürün girdisi şeması, göreli birimli AYAR, yuvarlak / dikey yerleşim kurucu (ayarla,
  aramasız), seçenek üreteci ve bütçe sınırı, mm uyarısı, pafta, süreç adımları, kayıt arayüzü, süre kaydı.
- Bugün hiçbir tabanın veremediği (ek kod + kapı 2 değişikliği ister): bağımsız sembol boyu, isim merkezli küçük burç
  yeri, isimlerin arasında logo (3.2, 3.4).

## 2. Mimari

### 2.1 Yeni kodun yeri

- scripts/tasarim_deneme/tasarim_deneme.py (girdi, ayar, yerleşim kurucu, seçenek üreteci, üretim, pafta, süre kaydı)
- scripts/tasarim_deneme/tasarim_kapi.py (kapılar ve ölçümler; OLCUM.json)
- scripts/tasarim_deneme/test_tasarim_deneme.py
- data/tasarim_deneme/urun/*.json (ürün girdileri; müşteri verisi yok)
- data/tasarim_deneme/kutuphane/<sekil>/*.json (sonraki parça; bu parçada yalnız şema)
- .github/workflows/tasarim-deneme.yml (yalnız Actions dilimi onaylanırsa; W'ye dokunulmaz)

### 2.2 Mevcut kodla ilişki: iki seçenek

| | (i) Sabit sha ile ayrı klasöre al, içe aktar | (ii) Ortak modüle çıkar, ay takvimi ona geçsin |
|---|---|---|
| Nasıl | AT ve ATK, belirli bir main sha'sından ayrı klasöre alınır (Actions: W:67-70 kalıbıyla 4. checkout; yerel: `git archive <sha> scripts/ay_takvim`), klasör sys.path'in başına eklenip normal `import` ile yüklenir (2.3). | scripts/ortak_altin/ gibi yeni modül; AT'deki fonksiyonlar oraya taşınır, AT içe alır. |
| Ay takvimi dosyaları | DEĞİŞMEZ | DEĞİŞİR (AT, ATK, ATT, W'nin sparse-checkout satırı W:64-66) |
| AY TAKVİMİ oturumuyla çakışma | Yok: yeni araç sabit sha'yı okur; o oturum main'i değiştirse de etkilenmez. | Var: aynı dosyalara iki oturum dokunur (CM "Aynı koda aynı anda tek oturum dokunur" kuralı). Bugün YASAK (görev: dokunulmaz). |
| Ayar sözlüğü değişimi | Yeni aracın AYAR'ı kendi tablosudur; AT'den yalnız fonksiyon alır. AT sha'sı yükseltilirken "yüzey testi" (2.3) farkı gösterir. | Ortak modül sürümü ile takvim birlikte değişir; her değişiklikte iki ürünün regresyonu gerekir. |
| Ay takvimi çıktısının değişmediğinin kanıtı | `git diff --stat <main> -- scripts/ay_takvim .github/workflows/ay-takvim-ornek.yml` boş; ek kanıt gerekmez. | ATT tamamı + 4 örneğin bayt eşitliği (aynı ortamda eski / yeni kodla PNG sha256) gerekir; bu bir Actions koşusu ya da uzun yerel koşu demektir. |
| Artı | Sıfır risk, bugün başlanabilir, emsali var (W, ATT). | Tek kaynak; uzun vadede iki kopya ayrışmaz. |
| Eksi | Bir sha'ya bağlı "anlık görüntü"; AT'deki sonraki düzeltme elle sha yükseltilerek alınır. Takvime özel yan etkiler (sembol_yukle AT:1013-1016) sarmalanır. | Çakışma, daha büyük inceleme yüzeyi, ay takvimi yeniden doğrulaması. |

Teknik öneri: şimdi (i). (ii), AY TAKVİMİ oturumu kapanıp ay takvimi kararları kesinleşince ayrı karar olarak ele alınır;
o güne kadar yeni aracın AT'den kullandığı yüzey tek listede tutulur (2.3), böylece (ii)'ye geçişte taşınacak fonksiyonlar
bellidir. Gerekçe: görev sınırı (dokunulmaz dosyalar), ay takvimi çıktısı için kanıt maliyetinin sıfır olması, emsal kalıp.

### 2.3 İçe alma kuralları (seçenek i)

- Sabitler dosya başında: AY_SHA = a9b1323 (bu planın tabanı; kod yazılırken main ilerlemişse fark okunup yüzey testiyle
  yükseltilir), MOTOR_SHA 6da763a ve ORNAMENT_SHA c950151 (W:26-27 ile aynı değerler).
- Yüklenen modülün sabiti DEĞİŞTİRİLMEZ (O4:35 kalıbı kullanılmaz); W, H, S'ye bağlı fonksiyonlar çağrılmaz ya da
  parametresi açıkça verilir (tablo 1.2).
- Yüzey testi: kullanılan her AT / ATK adının var olduğu ve imzasının beklenen olduğu (inspect.signature) + AT / ATK dosya
  sha256'sının sabitle aynı olduğu test edilir (emsal ATT:39-46 KAYNAK_SHA). Sha yükseltmesi bu testi bilerek kırar;
  yükselten, farkı okuyup sabitleri günceller.
- Yükleme sırası: ATK, AT'yi normal ad aramasıyla alıyor (ATK:68-69 `sys.path.insert` + `import ay_takvim_ornek as U`).
  AT başka adla dosya yolundan yüklenirse İKİ ayrı AT modülü oluşur (iki ayrı Dur sınıfı; aracın `except` bloğu ATK'dan
  geleni yakalamaz; test mutasyonları ATK'nın gördüğü modüle işlemez). Kural: sabit sha klasörü sys.path'in başına
  eklenir ve iki dosya da ATT gibi normal `import` ile alınır (ATT:33-35); araç AT'ye yalnız bu tek modül nesnesinden
  erişir. Test: `tasarim_kapi`'nin gördüğü U ile aracın gördüğü AT aynı nesne.
- İçe alma yan etkileri: AT modül düzeyinde cv2, numpy, PIL ister (AT:66-68), Image.MAX_IMAGE_PIXELS ve T0 atar
  (AT:70-71); ATK sys.path'i kalıcı değiştirir ve aynı PIL ayarını yapar (ATK:68, 71). ephem yalnız ay_verisi ve uret
  içinde yükleniyor (AT:313, 1636): araç için gerekmez, ay takvimi regresyon testi (ATT) için gerekir (ATT:9).

### 2.4 Yeni iş akışı

Actions yolu seçilirse yeni dosya gerekir (W dokunulmaz; workflow_dispatch yalnız main'deki dosyada çalışır, CM:11).
W'den alınacak adımlar (yalnız satır numarası; Drive klasör kimliği plana kopyalanmadı): onay / deneme 1 / ref main kapısı
W:38-58; checkout'lar W:59-70 + ay takvimi için dördüncüsü; sha doğrulaması W:71-79; Python W:80-82; sipariş koşusu
kontrolü W:83-90; paketler W:91-97 (sürümler aynı; ephem yalnız ATT regresyonu koşulacaksa); ayar doğrulama (ortam değişkeninden) W:98-108; rclone
W:109-123; sembol katmanı W:124-136; Drive'a yazma W:240-262; temizlik W:271-273. Kabuk adımları ATT:707 ve devamındaki
kalıpla sahte araçla yerelde test edilir (CM:113).

## 3. Girdi şeması

### 3.1 Ürün girdisi (dosya; data/tasarim_deneme/urun/<AD>.json)

| Alan | Tür | Açıklama |
|---|---|---|
| ad | [A-Z0-9_]{1,40} | Dosya adlarına giren tek girdi kaynaklı dize; desen dışı DUR. |
| sekil | 'yuvarlak' / 'dikey' / 'yatay' | Kütüphane anahtarı. |
| baski_px | [gen, yuk] tam sayı | Baskı alanı. |
| gercek_mm | [gen, yuk] | Baskı alanının gerçek ölçüsü. |
| mm_kaynak | 'resmi' / 'ölçüm' / 'varsayım' + not | px - mm eşlemesinin kaynağı; 'varsayım' ise her mm çıktısına etiket düşer. |
| guvenli | yuvarlak: {cx, cy, r}; dikdörtgen: {x0, y0, x1, y1} (px) | Yerleşim birimi buradan: yuvarlakta Rg = r; dikdörtgende kısa kenarın yarısı. |
| yasak | liste: {tur: 'daire' / 'kutu' / 'ust_cizgi', ...} | Delik, askı, çentik (emsal O4:38-41, 219-224). Boş olabilir. |
| kesim | isteğe bağlı {cx, cy, r} ya da kutu | Önizlemede kesim dışı beyaz (emsal O4:451-464). |
| alt_sinir | {yazi_mm, cizgi_mm, kaynak, etiket} | Üretici alt sınırları + kaynak etiketi. |
| zemin | 'motor' (bu parçada tek değer) | Renk / doku parçasının arayüzü (bölüm 3.5). |
| ornek_en_kotu | {isim1, isim2, satirlar} | En kötü örnek seti (4.4); yalnız örnek metin (soru 8). |

Deneme girdileri (yalnız sistemi denemek için; ürün kararı değil):

- DENEME_YUVARLAK_1087: baski_px [1087, 1087], gercek_mm [25,4, 25,4] (Merkez kaydı 9 Kas), mm_kaynak 'varsayım' (baskı
  alanı / görünen çap oranı ve dpi doğrulanmadı), guvenli {543,5, 543,5, r} r değeri [varsayım; Merkez verir], yasak [],
  alt_sinir {1,5, 0,2, kaynak: Merkez kaydı 9 Kas}. Eşleme [hesap]: 25,4 / 1087 = 0,02337 mm/px; 1,5 mm = 64,2 px; 0,2 mm
  = 8,56 px.
- DENEME_DIKEY_5400: baski_px [5400, 7200] (AT:74-75), gercek_mm [457,2, 609,6] [hesap: 300 dpi, AT:76], guvenli =
  kenardan 180 px (BOSLUK_KENAR AT:87), alt_sinir boş (kaynak yok; uyarı üretilmez, OLCUM'a "sınır tanımsız" yazılır).

### 3.2 Öğe listesi

| Öğe | Sabit / değişebilir | Kaynak | Altın yolu adı |
|---|---|---|---|
| ana sembol | sabit | katman PNG + yan json (Drive katmanı ya da yerel deneme sembolü AT:1679) | yok: yalnız eş oranlı küçültme (AT:20, 1256) |
| halka | sabit | MG alfa_ogeler.npz 'cember' (AT:1053-1056); kalınlık çarpanı açılırsa halka_kalinlastir (AT:1075; soru 2) | 'cember' |
| küçük burç 1, 2 | değişebilir (var / yok) | MG girdi/KUCUK_1-2.png + kutular (AT:98-103, 1059-1071) | 'kucuk1', 'kucuk2' |
| logo | değişebilir | AT logo_kaynak (AT:1159-1175), aşağıda | 'sonsuz' (AT:1175) |
| isim 1, isim 2 | değişebilir | girdi (örnek isim); Cinzel wght 500 (AT:1436) | 'yazi' |
| mesaj ya da tarih | değişebilir | girdi (örnek metin); EB Garamond Italic, ref 'T' (AT:1444) | 'yazi' |

Çift bu parçada CANCER_LIBRA (AT:107, 111). Altın çizim sırası sabit ve OZET'e yazılır (bölüm 7.3).

Logo (ay takvimi kodu logoyu nasıl kodluyor; genel araç bunu İÇE ALIR, yeniden yazmaz):

- Kesim: MG girdi/LOGO_1.png içinde sabit kutu (LOGO_KUTU AT:122, 1163-1164), kırp > 8 (AT:1165-1166). Poster kesimiyle
  aynı (MG olustur_alfa_sablon.py:69). Ornament kesimi farklıdır: görselin sağ yarısı + eşik 0,1 (O4:156-161).
- Ölçek: x 0,994 (LOGO_OLCEK AT:123, 1168; MG olustur_alfa_sablon.py:70), yani posterdeki logo boyu.
- Temizlik: pad 40 + motorun alfa temizliği (AT:1169-1170; MG olustur_alfa_sablon.py:83-86), sonra 8 px paylı kırpım
  (AT:1173-1174). Temizlik kaynak (poster) çözünürlüğünde BİR KEZ yapılır; 1x maske de k kat çizim de bu temizlenmiş
  alfadan küçültülür (AT:1262-1270, 858-862).
- Motor adı 'sonsuz' (AT:1175): motorun VEKTOR yolu bu adda çalışır (AT:714).
- Ornament motoru farklıdır: logoyu 10 kat boya BÜYÜTÜP sonra temizler (OM:427-433; OM:672 "1.41 buyutme"). Ay takvimi
  yolunda büyütme yoktur (k kaynağa göre düşer, AT:1265-1267).
- Yer: yatayda grup ekseni (halka merkezi), dikeyde küçük burç satırı (AT:1171-1172): "küçük burçların arası".
- Boy birimi: AYAR logo = çarpan; 1,0 = posterdeki logo boyu x grup ölçeği (AT:116, 1248-1252, 1262). Toplam ölçek > 1 ise
  girdi hatası (AT:1249-1250). 1087 tuvalde halka_r 0,884 iken çarpan 1,0 yaklaşık 33 px yükseklik verir [hesap: 196 x
  0,994 x 0,1694].
- Gruba etkisi: logo listede sonda (AT:1253); grup ölçeği ve çevre dairesi logosuz hesaplanır (AT:1197, 1217-1225); logo
  başka hiçbir öğeyi değiştirmez. Kapı 2 logoyu ayardan bekler (ATK:221-223, 234) ve yerini / boyunu ölçer (ATK:322-343).

Bu, ay takvimi için alınmış karardır. Genel araç için kesim ve temizlik sorusu (soru 7a - b) AÇIK kalır; cevap farklı
çıkarsa logo_kaynak kullanılamaz, ek kod gerekir. Bu planın önceki sürümüyle iki fark:

1. Boy birimi. Önceki sürümde logo_boy "isim büyük harfinin katı" idi (PLAN:227; ornament emsali O4:50). İçe alınan kod
   "poster logo boyu x grup ölçeği katı" istiyor (AT:116). Araçta anahtar AT birimiyle tutulur (anahtar adı `logo`);
   ornament oranı (logo yüksekliği / isim büyük harfi) OLCUM'a ölçüm olarak yazılır (soru 19).
2. Temizlik ile "logo yalnız ölçek" kuralı. AT logoyu alfa temizliğinden geçiriyor (AT:1170); temizlik şekle dokunabilir.
   "Yalnız ölçek" kapısı bu yüzden TEMİZLENMİŞ kaynağa göre tanımlanır (6.1) ve temizliğin ham kesime farkı OLCUM'a bilgi
   olarak yazılır. Temizliğin kabulü soru 7b.

Grup dışındaki logo yeri (isimlerin arası; ornament O3:226, poster MG olustur_alfa_sablon.py:64-72) ek kod ister: logo
alfası yine logo_kaynak'tan alınır (kesim, ölçek, temizlik aynı), ama yerleştirme, k hesabı (AT:1265-1267 kalıbı) ve kapısı
yeni yazılır, çünkü grup_kur logoyu yalnız küçük burç satırına koyar (AT:1171-1172) ve kapı 2 yalnız o yeri ölçer
(ATK:326). Bu, dilim 3'tür (bölüm 9).

### 3.3 AYAR sözlüğü

Mevcut anahtarların sınıflaması (AT:113-119):

| Anahtar | Sınıf | Not |
|---|---|---|
| grup_merkez, kucuk_u, kucuk_v, kucuk_oran | genel, aynen | Anlam AT:95, 115, 119; grup_kur'a doğrudan geçer (AT:1186). kucuk_u yalnız SİMETRİK sayı (-u / +u, AT:1057) ya da 'poster' (asimetrik: -0,491 / +0,490, AT:107); birim halka yarıçapı (Rg değil). |
| halka_kalinlik, halka_centik, logo | genel, aynen | grup_kur parametreleri (AT:1186-1187). Aralıklar AT:116, 119-120. Genel araçta açılmaları soru 2 ve 7. |
| grup_oran, sembol_alan | genel, birim değişir | Çarpımları hedef yarıçap (AT:1406). Yeni araçta halka_r ya da grup_r (Rg oranı). |
| isim_cap, metin_cap | genel, birim değişir | Takvimde 5400 tuval pikseli (AT:118); yeni araçta Rg oranı. |
| isim1, isim2, satirlar | genel, aynen | Doğrulama AT:263-273. |
| yerlesim | takvime özel | halkalar / girdap / rozet (AT:112). |
| ay_adi_cap, girdap_ad_uzaklik, disk_katsayi, baslik_cap | takvime özel | Alınmaz. |

Yeni aracın AYAR'ı (uzunluklar yerleşim biriminde: yuvarlakta Rg, güvenli yarıçap; böylece kayıt aynı şekildeki başka ürüne
taşınır. İstisna: kucuk_u ve kucuk_v halka yarıçapı birimindedir, AT:1057-1058 ile aynı; logo AT birimindedir).
Aralıklar BAŞLANGIÇ DEĞERİDİR (yalnız yanlış girişi yakalar; tasarım kararı değil, AT:110 kuralı).

KOD VARSAYILANI YOK: her koşu `taban` anahtarını ister (B1, B2 ya da bir kütüphane kaydının adı); verilmeyen anahtar
tabandan gelir; `taban` yoksa DUR. Hangi tabanın varsayılan olacağını bu plan seçmez (soru 5).

| Anahtar | Tür / aralık (başlangıç) | B1 (ornament çevrimi) | B2 (poster düzeni) |
|---|---|---|---|
| ogeler | alt küme: kucuk, logo, isim, metin | hepsi | hepsi |
| grup_merkez | 'grup' / 'halka' (AT:95) | 'halka' | 'grup' |
| grup_x, grup_y | -1,0 .. 1,0 | 0; +0,071 (3.4 [hesap]) | 0; 0 |
| halka_r YA DA grup_r | 0,30 .. 1,20; ürün başına üst uç ayrıca hesaplanır (aşağıda) | halka_r 0,884 (3.4 [hesap]) | grup_r 1,0 (grup çevre dairesi = güvenli daire; tanım) |
| kucuk_u | sayı 0,30 .. 0,90 (AT:115) ya da 'poster' | 'poster' | 'poster' |
| kucuk_v | sayı 0,20 .. 1,30 ya da 'poster' ('poster' = 0,948 [hesap: AT:104; MG cember.json]); AT:115'te alt uç 0,60, burada ornament yeri için 0,20 (soru 6) | 0,37 (3.4 [hesap]) | 'poster' |
| kucuk_oran | 0,60 .. 1,80 (AT:115) | 1,0 | 1,0 |
| halka_kalinlik | 1,00 .. 4,00 (AT:116). Soru 2 cevaplanana kadar yalnız 1,0 kabul edilir (başka değer girdi hatası) | 1,0 | 1,0 |
| halka_centik | 'ozgun' / 'yumusak' (AT:120; 'yumusak' yalnız kalınlık > 1, AT:261-262). Soru 2'ye kadar yalnız 'ozgun' | 'ozgun' | 'ozgun' |
| isim_duzen | 'tek_satir' (A & B; AT:1433) / 'iki_yan' (isim1 [logo] isim2; O3:208-226, MG olustur_alfa_sablon.py:64-72) | emsal 'iki_yan' | emsal 'iki_yan' |
| isim_cap | 0,03 .. 0,30 | 0,0742 (O3:39 / O4:37 [hesap]) | poster oranı: 0,105 x halka yarıçapı [hesap: MG olustur_alfa_sablon.py:23 CAP_H 298; cember R] |
| isim_y | -1,0 .. 1,0 (taban çizgisi) | +0,650 (YD:44 [hesap]) | poster yeri: halka merkezinin 1,295 halka yarıçapı altı [hesap: MG olustur_alfa_sablon.py:23 TABAN_ISIM 8062; cember] |
| logo | 'yok' ya da çarpan 0,50 .. 2,00 (AT:116, 119). Soru 7 cevaplanana kadar yalnız 'yok' | emsal: isimlerin arasında, yüksekliği isim büyük harfi kadar (O4:50) | emsal: isimlerin arasında, çarpan 1,0 |
| logo_yer | 'kucuk_arasi' (AT:1171-1172) / 'isim_arasi' (ek kod, dilim 3) | emsal 'isim_arasi' | emsal 'isim_arasi' |
| metin_tur | 'yok' / 'tarih' / 'mesaj' | 'tarih' | 'tarih' |
| metin_cap | 0,03 .. 0,30 | isim_cap x 0,850 (O1:46-47: 144 / 169,5 [hesap]) | aynı oran |
| metin_y | -1,0 .. 1,0 (ilk satır tabanı) | +0,817 (YD:44 [hesap]) | poster yeri: 1,721 halka yarıçapı altı [hesap: TABAN_TAG 9271] |
| satir_aralik | 1,2 .. 2,2 | 1,6 (AT:84) | 1,6 |
| isim1, isim2, satirlar | AT:167, 184 kuralları | EMILY, JAMES (AT:216), ['JUNE 14, 2025'] (YD:37) | aynı |

Notlar:

- halka_r / grup_r. İkisi birden verilirse DUR. halka_r = halka yarıçapı: ölçek = halka_r x Rg / cember R; hedef yarıçap =
  ölçek x grup çevre yarıçapı. grup_r = grup_kur'un hedef yarıçapı (AT:1191). Çevre yarıçapını öğrenmek için iki geçiş:
  ilk geçişte grup_kur KÜÇÜK sabit hedefle (64 px [başlangıç değeri]), halka_kalinlik 1,0, halka_centik 'ozgun' ve logo
  'yok' ile çağrılır (kalınlık 1,0 iken 'yumusak' DUR verir, AT:1243-1244),
  bilgi 'cevre_yaricap_poster' (AT:1281) okunur; ikinci geçiş gerçek hedef ve gerçek ayarla. Gerekçe: ölçek ve çevre
  dairesi zaten özgün halkadan ve logosuz hesaplanıyor (AT:1193-1198, 1217-1225), yani ilk geçişte kalınlaştırma ve logo
  temizliği koşmaz; küçük hedefte ölçek yaklaşık 0,02 olur [hesap: 64 / yaklaşık 3000 - 3400 poster px] ve büyütme DUR'u
  (AT:1226-1227) tetiklenmez. Önceki sürümdeki "ilk geçiş hedefi = Rg" büyük tuvalde yanlıştı: dikey 5400 girdisinde
  (Rg 2520) ilk geçiş ölçeği yaklaşık 0,73 - 0,80 olur [kontrol hesabı] ve kucuk_oran büyükken geçerli bir ayarı DUR'a
  düşürürdü.
- Üst uç ürüne bağlıdır: ikinci geçişte ölçek <= 1 şartı (AT:1226-1227) halka_r <= cember R / Rg demektir. Dikey 5400
  girdisinde 2835,9 / 2520 = 1,125 [hesap]: 0,30 - 1,20 aralığının 1,125 üstü bu tuvalde DUR verir. 1087 girdisinde bu
  şart sınırlamaz (5,2 [hesap]). Ayrıca ana sembol ölçeği ve ölçek x kucuk_oran da <= 1 olmalı (AT:1226). Araç bu üç
  şartı girdi doğrulamasında, üretimden önce hesaplar ve aşan ayarı girdi hatası olarak durdurur.
- "Küçük burç ayarı ana sembolün ve halkanın yerini / boyunu değiştirmez" koşulu iki şeyi birlikte ister: halka_r modu
  (ölçek sabit) VE grup_merkez 'halka' (merkez sabit; 'grup' merkezde çevre dairesi merkezi küçük burçlarla kayar,
  AT:1219-1221, 1257, 1268). grup_r modunda küçük burç ayarı tüm grubu yeniden boyutlar (AT:1217-1225).
- isim_duzen ve logo, geri dönüş. İki tabanın emsalinde de logo isimlerin arasındadır; bu yer ek kod ister (dilim 3).
  Dilim 3 gelene kadar: isim_duzen 'iki_yan' ya da logo_yer 'isim_arasi' istenirse araç DUR vermez, 'tek_satir' düzenine
  (A & B; AT:1433) ve logo 'yok' değerine döner, bunu OZET'e ve pafta başlığına "geri dönüş" diye yazar. Bu B1 için de B2
  için de aynıdır. Logo 'kucuk_arasi' yerinde (ay takvimi yeri) dilim 1'de kullanılabilir (soru 7 cevabına bağlı).
- B2'de isim ve metin: poster yerleri halka merkezinin 1,30 ve 1,72 halka yarıçapı altındadır [hesap]; grubun çevre
  yarıçapı küçük burçlar nedeniyle yaklaşık 1,1 - 1,2 halka yarıçapıdır [tahmin]. grup_r 1,0 iken isim ve metin güvenli
  dairenin DIŞINA düşer [hesap, yaklaşık; ölçülmedi]: taşma ölçerinde görünmesi BEKLENİR. B2 bu hâliyle "poster düzeni
  yuvarlak alana aynı oranla konunca ne olur" sorusunun cevabıdır; düzeltmek tasarım kararıdır, plan önermez.

Doğrulama (sert, üretim başlamadan): bilinmeyen anahtar, aralık dışı, yanlış tür (bool dahil), sonsuz / NaN, çok büyük tam
sayı, yinelenen JSON anahtarı, liste uzunluğu, toplam metin uzunluğu = DUR, çıkış 3; hata mesajında ham girdi yok, yalnız
hata türü ve anahtar sırası (AT:219-306 kalıbı). Ayar metni kabuk satırına girmez, ortam değişkeninden okunur (W:9,
AT:1648-1657). Dosya adları koddan (bölüm 4.4).

Müşteri verisi yasağı: girdi yalnız örnek isim ve örnek metin (W:8-9). Kod bunu içerikten ayırt edemez; yasak süreç kuralıdır
ve üç yerde yazılır: iş akışı girdi açıklaması (emsal W:23), komut yardım metni, OZET.json not alanı. Açıkça: AYAR.json,
OZET.json ve kütüphane kaydı tam ayar sözlüğünü, yani örnek isim ve örnek metni İÇERİR (emsal AT:1607, ATK:615, 639;
yeniden üretim için gerekli). Girdinin yalnız örnek olması bu yüzden zorunludur. OLCUM'un öğe kayıtlarında metin yok,
yalnız alan adı ve karakter sayısı var (emsal AT:1615-1616).

### 3.4 Başlangıç adayları ve kütüphane arayüzü

Kütüphane (sonraki parça; yalnız şema). Kayıt = seçilen seçeneğin OZET satırından koddan üretilen dosya:
{ad, sekil, ayar (TAM sözlük, göreli birimler), kod_sha, ay_sha, motor_sha, ornament_sha, paketler, urun_ad,
urun_girdisi_sha256, sembol_katmani_sha256 (+ 'deneme' / 'gercek' etiketi), logo_sha256, altin_sirasi,
ornek_png_sha256, onay: {kim, tarih, söz}}. Komutlar: `kayit --ozet OZET.json --secenek N --onay "..."` (kayıt dosyası
yazar), `uret --kayit K.json --urun U.json` (kayıttan yeniden üretir). Aynı ürün girdisi + aynı sembol katmanı + aynı
sha'lar + aynı ortamda PNG sha256 kayıttakiyle aynı olmalı; katman farklıysa (deneme / gerçek) bayt eşitliği aranmaz,
yalnız yerleşim ölçümleri karşılaştırılır (test, bölüm 8); başka üründe ayar aynen uygulanır, mm uyarıları yeniden
hesaplanır.

B1, ornament çevrimi. Ornament yerleşiminin göreli birimlere çevrilmiş hali [hesap; Rg = 380 ve merkez (476, 477) O4:34,
37; halka YD:28-29; çizgiler YD:44-45]: halka merkezi y +0,071, halka iç yarıçapı 0,884, isim tabanı +0,650, tarih tabanı
+0,817, tarih altı +0,837 (YD:44); küçük burç altı +0,489, sembol alt sınırı +0,224 (YD:45); üst sınır -0,650 (YD:33); isim
büyük harfi 0,0742. Hangi ornament düzeninin "onaylı emsal" olduğu soru 5.

B1 ornament'i BİREBİR vermez; farklar kayıt notuna yazılır:

- Halka: ornament halkası analitik çizilen elipstir, gövde 4,4 px, taban 4,2 px (O4:47, 113-126; uçlar O5:253). Araçtaki
  halka poster alfasının orantılı küçültülmüşüdür (AT:1056, 1264): aynı yarıçapta 2,3 px [hesap: 336 x 19,07 / 2835,9;
  MG cember.json]. Yaklaşık karşılık halka_kalinlik çarpanı 1,95 olurdu [hesap: 4,4 / 2,26]; profil ve elips oranı yine
  farklı kalır. Çarpanın açılması soru 2.
- Küçük burçlar: ornament'te yatay yer her ismin kendi merkezidir, yani isimlere bağlı ve asimetriktir (O3:228-233);
  grup_kur yalnız simetrik -u / +u ya da poster yerini kurar (AT:1057), kapı da öyle bekler (ATK:300-304). Dikey yer
  halka merkezine göre yaklaşık +0,37 halka yarıçapı [hesap: YD:45 kucuk_ust_sabit 594 ve kucuk_alt 663 ortası,
  YD:28-29]; ornament alt kenara, AT kutu merkezine hizalıyor (O3:233, AT:1067), fark [ölçülmedi].
- Sembol boyu: ornament'te sembol "sığan en büyüğün 0,85'i" aramasıyla bulunuyor (YD:35). Araçta ana sembol halkadan
  bağımsız boyutlanamaz: ölçeği grup ölçeği x poster oranıdır (AT:1215, 1256).

B1, BİLİNEN ÇAKIŞMA. Sembol boyu poster oranından geldiği için B1'de küçük burçlar ana sembolün üstüne biner:

- Sembolün alt kenarı halka merkezinden +0,463 halka yarıçapı [hesap: MG girdi78/ana/cancer_libra_alfa.png 8185 x 7702
  (boyut bu oturumda git nesnesinden okundu); MG yerlesim78.json CANCER_LIBRA u0 -0,6233, u1 +0,6253, v0 -0,7119;
  yükseklik katmanın kendi oranından: -0,7119 + 1,2486 x 7702 / 8185]. Ornament'te sembol alt sınırı +0,173 halka
  yarıçapı [hesap: (562 - 504) / 336; YD:28-29, 45].
- B1 küçük burçları kucuk_v 0,37'ye koyar; sembol 0,463'e kadar iner.
- [kontrol ölçümü; poster alfasıyla, motor temizliği ve gölgesi olmadan, yaklaşık]: kutu düzeyinde ana sembol küçük burç
  kutularının %7'sini (CANCER) ve %14'ünü (LIBRA) kaplıyor; kucuk_v 0,60 ve üstünde 0. Glif düzeyinde (alfa > 0,5, poster
  pikseli) 0,37'de 8.477 ve 10.695 piksel çakışma; 0,50'de 0.
- Beklenen sonuç: altın binme ölçeri (6.2) FAIL yazar ve görselde küçük burçlar sembole biner. Deneme sembolünde ve
  gerçek katmanda [ölçülmedi].

B1 yine aday olarak kalır (ornament'e en yakın ifade edilebilen düzen); pafta başlığında ve OZET'te "bilinen çakışma"
etiketi taşır. Etiket ölçümdür, öneri ya da sıralama değildir. Ornament düzenini birebir vermek ayrı dilimdir:

| Gereken | Kullanılamayan mevcut kod | Etkilenen kapı tanımı | Süre [tahmin] |
|---|---|---|---|
| Bağımsız sembol boyu (yeni anahtar) | grup_kur'un ana sembol çıktısı (ölçek = grup ölçeği x poster oranı, AT:1215, 1256). Ana sembol sembol_yerlestir / rgba_olcek ile ayrı kurulur (AT:1030, 1020). Çevre dairesi ana sembolü içerdiği için (AT:1217) yalnız halka_r + 'halka' merkez modunda tutarlı. | Kapı 2: yeniden kurulumda ana sembol ölçeği ve yeri eşitliği (ATK:230-233); bağımsız ölçümde ana sembolün poster yeri ve boyu hedefi (ATK:344-352) ve "en uzak grup pikseli = hedef yarıçap" (ATK:261-264, 283; ana sembol maskesini içerir). Hedef "poster oranı" yerine "ayar değeri" olur. | 3 - 4 saat |
| İsim merkezli (asimetrik) küçük burç yeri | grup_kaynak'ın yatay yeri (AT:1057). grup_kur'dan sonra küçük burç maskesi yatayda kaydırılır (yeni kod). | Kapı 2: küçük burç yer hedefi (ATK:300-304, 308-320), "küçük 1 solda, küçük 2 sağda" (ATK:321, 355) ve en uzak piksel ölçütü (ATK:261-264; küçük burç maskelerini içerir). | 2 - 3 saat |
| Ornament halkası | Kaynağı (analitik profil, poster halka görseli) bu planın okumadığı dalda. | Kapı 2 halka ölçümü (ATK:251-256, 284-285). | bu planda yok |

Kapı tanımı değiştiği için bu dilim Serdar onayı ister (soru 17); toplam 5 - 7 saat [tahmin] + bağımsız inceleme.

B2, poster düzeni: grup posterdeki göreli düzenle (AT:28-33), grup çevre dairesi güvenli daireye oturur; isim ve metin
poster oranındaki yerlerinde. İsim ve metnin sığması [ölçülmedi]; hesaba göre sığmaması beklenir (3.3 notu).

### 3.5 Renk ve doku arayüzü (sonraki parça; yalnız arayüz)

Bu parçada tek görünüm vardır: motor zemini (zemin_radyal + zemin_yildiz + zemin_8bit; AT:1510-1531), tek palet, tek
KILIT. Arayüz çok seçeneği taşıyacak biçimde tanımlanır:

- Koşu girdisinde `gorunum` listesi: her öğe {zemin: ad, renk: ad, doku: ad}; her ad kayıtlı bir setin adıdır (dosya +
  sha256). Yerleşim AYAR'ında renk / doku anahtarı YOKTUR: aynı yerleşim kaydı her görünümle üretilebilir, görünüm
  eklenince yerleşim kayıtları değişmez.
- Setlerin kaynağı Serdar ya da görsel platformdur; araç set üretmez, yalnız verilen setleri uygular.

Olgular (bugünkü kod):

- Motor tek görünüme kilitlidir: KILIT dosyası Motor kurulurken okunur, ortam değişkenlerine yazılır (AT:691-694), dalları
  sert kontrol edilir (AT:697-702); golge_motor ortamı içe alınırken ve çağrılarda okur (MG golge_motor.py:3-7, 227-229).
  Süreç başına tek KILIT.
- Renk haritası paletten ve ciftin poster ana alfasından kurulur (harita_kur AT:793-813).
- oge_katman tek fonksiyondur: gölgeleme, eşitleme, harita, gren, küçültme (AT:815-843); ara sonuç dışarı verilmez.
- renk_uyum her altın öğeyi ana sembol katmanının Lab ortancasına çeker (AT:618-632, 1558): öğelerin son tonu fiilen ana
  sembol katmanından gelir. Ana sembol katmanı dokunulmazdır (AT:20).
- Zemin öğe katmanına girmez; yalnız birleştirmede (boya AT:643-681) ve yıldız engelinde (AT:1515-1529) kullanılır.

Yerleşim sabitken görünüm değişince yeniden koşan adımlar ve seçenek başına süre [tahmin; 1087 tuval, 7.2 rakamlarından]:

| Değişen | Yeniden koşan | Değişmeyen | Süre |
|---|---|---|---|
| zemin seti | zemin, birleştirme, kapılar | motor katmanları, renk uyumu | önbellekle 3 - 8 sn; önbelleksiz (dilim 1) tam çizim 12 - 28 sn |
| ana sembol katmanı seti (ör. başka renkte katman) | katmanın küçültülmesi (grup_kur), renk uyumu (hedef Lab; AT:1558, 874), iç gölge oranı (AT:1419-1423, 884-885), birleştirme, kapılar. Renk haritası ve oge_katman DEĞİŞMEZ: girdileri katmanı içermez (AT:815; harita poster alfasından ve paletten, AT:774-805). | motor katmanları, harita | önbellekle 3 - 8 sn + katman küçültme; önbelleksiz tam çizim 12 - 28 sn |
| palet seti | palet bir motor dosyasıdır (AT:127) ve Motor kurulurken sabit yoldan okunur (AT:693, 710-712): palet başına ayrı motor klasörü ve yeni Motor; renk haritası (AT:793-813), tüm oge_katman çağrıları, renk uyumu, birleştirme, kapılar | geometri (maskeler) | tam çizim 12 - 28 sn + kurulum (15 sn [kayıt]), set başına bir kez |
| doku seti (KILIT / ortam) | ayrı süreç: Motor kurulumu + tam çizim | geometri | tam çizim 12 - 28 sn + süreç ve kurulum (15 sn ve üstü), set başına bir kez |

Not: renk uyumu bütün öğeleri ana sembol katmanının tonuna çektiği için (AT:618-632) palet değişimi ile katman değişiminin
son görseldeki payı [ölçülmedi]; hangisinin "renk seçeneği" sayılacağı renk parçasının sorusudur.

Palet setinde gölgeleme ara sonucunu saklayıp yalnız haritayı yeniden uygulamak hız kazandırırdı, ama oge_katman'ı bölmek
içe alınan kodu değiştirmek demektir (2.2 seçenek ii); ayrı karar. 5400 tuvalde aynı adımlar için [kayıt] rakamları
geçerlidir (7.2).

## 4. Seçenek üretimi

Kural (Dayanak 3): sistematik dizi tasarım önerisi değildir; seçenek numarası üretim sırasıdır, sıralama değildir. Yeni
gereksinim (Serdar 11 Kas): seçenekler mümkün olduğunca çok olmalı; birlikte geçerli kural: denemeler hafif ve hızlı
olmalı. İkisinin dengesi 4.5 ve 5.1'dedir.

### 4.1 Başlangıç kümesi

Önce o şeklin kütüphane kayıtları. Kütüphane parçası gelene kadar yuvarlak şekil için iki başlangıç ADAYI kodla birlikte
gelir (3.3 tablosu, 3.4): B1 ornament çevrimi (bilinen çakışma etiketli) ve B2 poster düzeni (isim ve metnin taşması
beklenir). İkisi de Serdar onayına kadar "aday" etiketlidir; sıraları üretim sırasıdır. İkisinin de bilinen bir kusuru
vardır ve hangisinin (ya da hiçbirinin) varsayılan taban olacağını plan seçmez: soru 5. İlk koşu ikisini de üretir.

### 4.2 Yerleşim ızgarası (karar 4)

Öğe başına boyut x yer ızgarası; diğer öğeler taban ayarda kalır ("ortak alan standardı, sonra öğe başına ızgara"). Taban
ayar = Serdar'ın o an seçtiği seçenek (ilk turda başlangıç kümesinden).

| Izgara | Boyut anahtarı, başlangıç adımları | Yer anahtarı, başlangıç adımları | Seçenek |
|---|---|---|---|
| grup | halka_r: x0,85, x1,00, x1,15 | grup_y: -0,05, 0, +0,05 | 9 |
| küçük burçlar | kucuk_oran: 0,8, 1,0, 1,2 | kucuk_v: -0,10, 0, +0,10 (tabana göre) | 9 |
| isimler | isim_cap: x0,85, x1,00, x1,15 | isim_y: -0,05, 0, +0,05 | 9 |
| logo | logo çarpanı: 0,8, 1,0, 1,25 | logo_yer: 'kucuk_arasi'; 'isim_arasi' dilim 3'ten sonra | 3 ya da 6 |
| mesaj / tarih | metin_cap: x0,85, x1,00, x1,15 | metin_y: -0,05, 0, +0,05 | 9 |

Adım sayısı, adım değeri ve aynı anda değişen öğe sayısı girdidir (ızgara tanımı da doğrulanan girdidir); yukarıdakiler
başlangıç değeridir, tasarım kararı değildir. Koşu başına seçenek sayısının sınırı sabit sayı değildir; süre bütçesinden
hesaplanır (4.5 b).

"Tek öğe değişir" ne demek ve nerede tutar:

- Geometri düzeyinde tutar: halka_r modu + grup_merkez 'halka' iken küçük burç ayarı (kucuk_v, kucuk_oran, kucuk_u)
  değişince ana sembolün ve halkanın MASKESİ, YERİ ve BOYU aynı kalır (3.3). grup_r modunda ya da 'grup' merkezde tutmaz
  (AT:1217-1225, 1257): bu modlarda küçük burç ızgarası bütün grubu oynatır ve pafta başlığına öyle yazılır.
- Son görselde tutmaz, tutması da beklenmez: küçük burç ana sembole biniyorsa ya da dış gölgesi sembolün / halkanın
  yanına düşüyorsa o pikseller değişir (boya, dış gölge tüm öğelerin birleşiminden; AT:643-681).
- Gren düzeyinde sınırlıdır: altın öğelerin greni tek üreteçten öğe sırasıyla çekilir (AT:854, 828). Bir yazının boyu
  değişince ondan SONRA çizilen öğelerin (halka kalınlığı 1,0 iken halka dahil, küçük burçlar, logo) gren deseni değişir;
  şekil, yer, boy ve renk hedefi değişmez. Halka kalınlığı 1,0'dan büyükken halka ayrı üreteçten boyandığı için yazı
  boyundan etkilenmez, küçük burçlar ve logo yine etkilenir (AT:867-869).
- Test bu yüzden birleştirmeden ÖNCEKİ katmanda tanımlanır (bölüm 8): ana sembolün (rgb, alfa, yer) ve halkanın (maske,
  yer, k, motor katmanı) dizileri bayt bayt aynı; son görsel için eşitlik aranmaz.

Taban ayar ızgaranın istediği modda değilse (ör. B2: grup_r + 'grup' merkez): araç aynı GEOMETRİYİ veren eşdeğer ayarı
(halka_r, 'halka' merkez, halka merkezinin yeri grup_x / grup_y olarak) hesaplar ve OZET'e yazar. Eşdeğer ayarın bayt
bayt aynı görseli vereceği İDDİA EDİLMEZ: yerler tam sayıya ayrı ayrı yuvarlanır (AT:1258, 1269), farklı merkezle 1 px'e
kadar kayma olabilir. Bu yüzden ızgaranın taban hücresi eşdeğer ayarın KENDİSİYLE yeniden üretilir ve ızgarada yer alır;
Serdar'ın seçtiği özgün seçenek ayrıca yanında durur. 'poster' sözcüğü sayıya ÇEVRİLMEZ: posterde küçük burç yeri
simetrik değildir (-0,491 / +0,490; AT:107), sayı anahtarı yalnız simetrik değer alır (AT:1057). Taban 'poster' ise
kucuk_u ızgarada 'poster' kalır; kucuk_v adımları 'poster' karşılığı 0,948'e [hesap] göre sayı olarak verilir (dikey yer
tek sayıdır, simetri sorunu yoktur; AT:1058).

### 4.3 Öğe kombinasyonları (karar 3), ayrı çıktı

Aynı taban ayar üzerinde değişebilir öğelerin var / yok kombinasyonları; öğe çıkarılınca diğerlerinin yeri değişmez.
Tam çarpım: küçük burç (2) x logo (2) x isim (2) x metin (yok / tarih / 1 satır mesaj / 3 satır mesaj: 4) = 32 [hesap].
Kombinasyon ayrı koşudur, çıktı klasörü ve paftası ayrıdır; sınırı 4.5 b kuralıdır.

Öğe türüne göre nasıl kurulur ve sert kapı 2 (grup kapısı; ATK:209-360) ne yapar:

| Çıkarılan öğe | Kurulum | Kapı 2 |
|---|---|---|
| logo | grup_kur logo 'yok' ile çağrılır. Logo grup ölçeğine ve çevre dairesine girmediği için (AT:1197, 1217-1225) diğer öğeler aynı kalır. | Tanım AYNEN: logo ayarda yoksa grupta olamaz (ATK:221-223, 234). Ek iş yok. |
| isim, metin | Grup dışı öğeler; yerleri ayardan gelir, çıkarılınca kalanların yeri değişmez. | Kapı 2'ye girmezler. Öğe sayısı tamlığı ölçeri beklenen listeyi `ogeler` ayarından okur. |
| küçük burçlar | grup_kur küçük burçları her zaman kurar (AT:1059-1071); küçük burçsuz kurulum yoktur. İki yol aşağıda. | Aşağıda. |

Küçük burçsuz kombinasyon için iki yol (hangisi: soru 18):

- K-a "çizilmedi": grup TAM setle kurulur; küçük burçların GEOMETRİ maskeleri üretilir ama öğeler boyanmaz (altın çizimi
  yok, yıldız engeline girmezler, son görselde yokturlar). Ana sembol ve halka tam setteki yer ve boyda kalır.
- K-b "küçük burçsuz grup": grup küçük burçlar olmadan yeniden kurulur. İçe alınan kod bunu vermez (ek kod); çevre
  dairesi değişir, grup_r modunda ana sembol ve halka büyür. Kapı 2 listesi yalnız halka olur.

K-a'da her kapının çizilmeyen öğeyle ilişkisi (ay takvimi kapı betiği grup öğelerinin hepsini boyanmış sayar; bu yüzden
aşağıdakilerin hepsi yazılmadan K-a çalışmaz):

| Kapı | Takvim kodunda çizilmeyen öğe ne yapardı | K-a'da tanım |
|---|---|---|
| Kapı 2 grup: liste, yeniden kurulum, bağımsız ölçüm | Maske yoksa sert FAIL (ATK:223, 234, 238-244) | AYNEN: tam liste; ölçümler geometri maskelerinden: küçük burç yeri ve boyu (ATK:308-320), "küçük 1 solda, küçük 2 sağda" (ATK:321, 355), en uzak piksel = hedef yarıçap (ATK:257-283). Tanım değişmez. |
| Kapı 3 tek doku dE00 ve 200 çekirdek piksel | Son görselde o bölge zemin: FAIL (ATK:457-462) | Yalnız BOYANAN öğeler ölçülür. Kapsam daralması. |
| Kapı 4 kontrast | FAIL (ATK:464-466) | Yalnız boyanan öğeler. Kapsam daralması. |
| Kapı 5 yazım farkı | Motor alfası yok (AT:868-871 çağrılmaz); grup öğelerinde zaten bilgi (ATK:498) | Yalnız boyanan öğeler. |
| Altın binme | Maske > 0,02 sayılır (ATK:506-518): görünmeyen binme FAIL yazardı | Yalnız boyanan öğelerin maskeleri. Kapsam daralması. |
| Kapı 7 düz renk, yıldız | FAIL (ATK:482-483); yıldız payı (ATK:562) | Yalnız boyanan öğeler; yıldız engeli ve yıldız kapısı çizilmeyen öğeyi saymaz. |
| Taşma (öğe maskesi) | - | Yalnız boyanan öğeler. |
| Öğe sayısı tamlığı | Liste uyuşmazlığı (ATK:487-488) | Beklenen BOYANAN liste `ogeler` ayarından; geometri listesi ayrı sayılır. |
| YENİ ölçüm: çizilmeyen öğe gerçekten yok mu | - | Çizilmeyen öğenin maskesinden, boyanan öğelerin maskeleri ve dış gölge erimi çıkarıldıktan sonra kalan bölgede son görsel ile altınsız zemin farkı ölçülür ve yazılır. ÖLÇER; eşik bu planda konmaz. B1'de ana sembol bu bölgeye bindiği için (3.4) çıkarma şarttır. Sert olup olmayacağı ve eşiği ilk ölçümden sonra sorulur. |

Yani K-a kapı 2'nin tanımını değiştirmez, ama kapı 3, 4, 7, altın binme, yıldız ve taşma ölçümlerinin KAPSAMINI
"boyanan öğeler" diye daraltır. Bu daralma Serdar onayı ister (soru 6 k) ve her satır için bilinen PASS + bilinen FAIL
testi bölüm 8'dedir. K-b'de ise kapı 2'nin TANIMI değişir. Plan K-a ile yazıldı; seçim soru 18. Önceki sürümdeki
"çıkarılan öğe çizimden ve ölçümden düşer" cümlesi yanlıştı: küçük burç kapı 2'nin ölçümünden düşerse sert FAIL verir
ve görsel silinir.

### 4.4 Kişiselleştirilen alanlar: tipik ve en kötü

Her yerleşim seçeneği iki örnek setle değerlendirilir; ikisi de girdidir, kod değer uydurmaz:

- tipik: EMILY / JAMES (AT:216), tarih 'JUNE 14, 2025' (YD:37).
- en kötü: uzun isim çifti (emsal ALEXANDRINA / CHRISTOPHER, W:206), mesaj 3 satır x 35 karakter (sınır AT:142; emsal
  metinler W:204-205). En kötü örnek değerlerinin kendisi alan sınırı kararının parçasıdır (soru 8).

İsim satırı sınırı aşarsa mevcut kural uygulanır: iki isim birlikte küçülür (isim_sigdir, yumusak=True; AT:570), küçülme
oranı ve sonuç mm değeri OLCUM'a yazılır, alt sınırın altı işaretlenir, seçenek gizlenmez.

İki setin ikisi de görsel olarak mı üretilir, yoksa en kötü set önce yalnız ölçülür mü: 5.1 (yol ii-b) ve soru 15.

Dosya adları koddan: `SEC_<NN>_<izgara>_<T|K>` (NN sıra, T tipik / K en kötü); kombinasyonlarda `KOMB_<NN>`. Girdiden
gelen hiçbir metin dosya adına girmez (ürün adı hariç, desen kontrollü; emsal AT:1337, 1360).

### 4.5 Çok seçenek: sınırlar, bütçe kuralı, genişletme yolları

(a) Bu planda seçenek sayısını sınırlayan yerler. Sütun "Tür": T = teknik zorunluluk (içe alınan kod bugün ifade
edemiyor); B = başlangıç değeri (girdiyle değişir); K = karar ya da kapsam (Serdar / Merkez).

| No | Sınır (önceki sürüm satırı) | Tür | Kaldırmanın maliyeti (kod / süre / kapı) |
|---|---|---|---|
| 1 | Başlangıç adayı 2 (PLAN:288-296) | K | Kod yok: her yeni taban bir kütüphane kaydıdır, Serdar onayıyla girer. Süre: taban başına bir seçenek. |
| 2 | Izgara 3 x 3, beş ızgara, aynı anda tek öğe (PLAN:300-309) | B | Kod yok (girdi). Süre seçenek sayısıyla artar (c). |
| 3 | Izgara tanımı en çok 2 anahtar, 5 değer; koşu 25; aşan DUR (PLAN:319-320) | B | Sabit sınırlar KALDIRILDI. Çok anahtarlı ızgara için çarpım üreteci ve çok sayfalı pafta: 1 - 2 saat [tahmin]. Sınır (b)'den. |
| 4 | Kombinasyon üst sınırı 32 (PLAN:327-329) | B | Sabit sınır kaldırıldı; (b). |
| 5 | isim_duzen 2 değer, logo_yer 2 değer (PLAN:224, 228'de 3 değer) | K | Değerler emsal kadardır. "Küçük burçların arası" eklendi (kod yok, AT'den). Önceki sürümdeki 'ust' ve 'alt' ÇIKARILDI: emsali ve kaynağı yoktu, önceki planın kendi eklemesiydi (tasarım fikri Code'dan gelmez). Bu bir seçenek azalmasıdır; Serdar ya da kütüphane isterse geri eklenir: 4.6 satır 2, 1 - 3 saat [tahmin] + "yalnız ölçek" kapısı. |
| 6 | Küçük burç yatay yeri simetrik ya da poster (PLAN:221) | T | AT:1057; kapı ATK:300-304. Ek kod 2 - 3 saat [tahmin]; kapı 2 hedefi değişir (3.4 tablosu, soru 17). |
| 7 | Bağımsız sembol boyu yok (PLAN:272-274) | T | AT:1215, 1256. Ek kod 3 - 4 saat [tahmin]; kapı 2 hedefi değişir (soru 17). |
| 8 | Zemin tek değer, renk ve doku seçeneksiz (PLAN:174, 278-280) | K | Sonraki parça; arayüz ve adım maliyeti 3.5. |
| 9 | Yalnız CANCER_LIBRA (PLAN:196, 620) | T | Küçük burç poster yeri yalnız bu çift için kodda (AT:107) ve kapıda (ATK:205). Başka çift: çift başına poster yeri (formül notu AT:105-106) + kapının bağımsız sabiti + ana katman. Çift başına 0,5 - 1 saat [tahmin] + süre x çift sayısı. |
| 10 | Her seçenek iki örnek setle, süre iki kat (PLAN:333-337, 449) | K | Karar 4 gereği. Azaltma yolu: en kötü set için önce yalnız geometri ölçümü (5.1 yol ii-b). |
| 11 | Halka kalınlığı ve çentik soru 2'ye kadar kapalı (yalnız 1,0 / 'ozgun' kabul; 3.3) | K | Kod yok (grup_kur parametresi). Karar: soru 2. Açılırsa seçenek dizisi (c 3). |
| 12 | grup_merkez 2 değer | T | AT:95, 1219-1224. Yeni merkez tanımı = içe alınan kodun dışında ek kod. |
| 13 | Metin en çok 3 satır, 35 karakter; metin_tur 3 değer | K | AT:142 (takvim kararı). Genel araçta değeri ürün girdisinden okunabilir; karar 4. |
| 14 | Şekil: ilk dilimde yalnız yuvarlak | K | Dikey / yatay dilim 5 (3 - 4 saat [tahmin]). |
| 15 | Pafta sayfası başına hücre sayısı | B | Okunabilirlik ölçülmedi; girdi. Çok sayfalı pafta (5.1). |
| 16 | Çizim sırası emsal; önbellek az tutar (7.3) | K | Süreyi sınırlar, seçenek uzayını değil. Soru 13. |
| 17 | Süreç başına tek KILIT, tek palet | T | 3.5. Doku seti başına ayrı süreç. |
| 18 | AYAR aralıkları (3.3: halka_r 0,30 - 1,20; isim_cap ve metin_cap 0,03 - 0,30; kucuk_oran 0,60 - 1,80; kucuk_u 0,30 - 0,90; kucuk_v 0,20 - 1,30; logo 0,50 - 2,00; halka_kalinlik 1 - 4; satir_aralik 1,2 - 2,2) | B (AT:115-116'dan gelenler ay takvimi başlangıç değeri) | Kod yok (tablo). Aralık dışı değer bugün girdi hatası; genişletme Merkez / Serdar kararı. |
| 19 | "Büyütme yok" üst uçları: ölçek, ana sembol ölçeği, ölçek x kucuk_oran, logo toplam ölçeği <= 1 (AT:1226-1227, 1249-1250); 5400 girdisinde halka_r <= 1,125 | T (kural: şekil değişmez, büyütme yok) | Kaldırılamaz; daha büyük kaynak görsel gerekir. |
| 20 | Fontlar ve altın yolu sabit (AT:111; fontlar AT:716-717) | K (değişmeyenler kuralı) | Kural değişikliği; bu planın dışında. |

(b) Sınır kuralı. Sabit üst sınır (25, 32) yerine: N_en_çok = floor((B - t_kurulum) / t_seçenek). B = süre bütçesi
(Serdar / Merkez girdisi; soru 14; bu plan değer koymaz). t_kurulum ve t_seçenek ÖLÇÜLÜR (SURE.json); karşılığı ay
takvimindeki formüldür (AT:48-49). Ayrıntı:

- İki tür seçenek ayrı ölçülür: tam çizim (t_tam) ve yalnız yer / zemin değişimi (t_yer). İstek süresi = t_kurulum +
  n_tam x t_tam + n_yer x t_yer, örnek seti sayısıyla çarpılır.
- Araç istek süresini üretimden ÖNCE hesaplar. Bütçeyi aşıyorsa hiçbir şey üretmeden DUR verir (girdi hatası) ve bütçeye
  sığan en büyük seçenek sayısını yazar. Araç seçenek ATMAZ, listeyi kendisi kırpmaz, hangilerinin kalacağına karar vermez.
- Ölçüm yokken (ürün girdisi için ilk koşu) yalnız ölçüm koşusu yapılır: 3 seçenek [başlangıç değeri], iki tür de içinde.
- Formül örneği [hesap; yalnız örnek]: 5400 tuval, seçenek 54 - 62 sn [kayıt], kurulum 15 sn [kayıt], B = 50 dk olsaydı
  N_en_çok = 48 - 55.

(c) Seçenek uzayını sistematik genişletme yolları. Süre sütunu: seçenek başına süre 7.2'deki gibi (1087 tuvalde tam
çizim 12 - 28 sn [tahmin]; 5400 tuvalde 54 - 62 sn [kayıt]); tek örnek seti; iki sette iki katı.

| No | Yol | Seçenek sayısı [hesap] | 1087 tuval süre [tahmin] | 5400 tuval süre [hesap] | Gereken kod |
|---|---|---|---|---|---|
| 1 | Izgara adım sayısı n (dört ızgara n x n + logo ızgarası n x yer sayısı; 4.2) | n = 3: 39; n = 5: 105; n = 7: 203 (isim arası logo açılınca 42 / 110 / 210) | 8 - 18 dk; 21 - 49 dk; 41 - 95 dk | 35 - 40 dk; 95 - 109 dk; 183 - 210 dk | Yok (girdi). |
| 2 | Aynı anda iki öğeli ızgara (öğe çifti başına iki ızgaranın çarpımı) | n = 3: çift başına 81 (logo içeren çiftte 27); 10 çiftin hepsi 594 | çift başına 16 - 38 dk (logolu çift 5 - 13 dk) | çift başına 73 - 84 dk (logolu çift 24 - 28 dk) | Çarpım üreteci, çok sayfalı pafta: 1 - 2 saat. |
| 3 | Ayrık anahtarların birleşimi: grup_merkez (2) x isim_duzen (2) x logo (yok / küçük burç arası / isim arası: 3) x metin_tur (3) | 36; halka dizisi açılırsa (1,0 ve 1,5 / 2 / 2,5 / 3 x çentik 2 = 9 değer) 324 | 7 - 17 dk; 65 - 151 dk | 32 - 37 dk; 292 - 335 dk | Yok; isim arası logo dilim 3. Halka dizisi soru 2'ye bağlı. |
| 4 | Kodun bugün ifade edemediği anahtarlar: bağımsız sembol boyu; isim merkezli küçük burç yeri | her biri yeni bir ızgara (n x n) | ızgara başına (1) gibi | (1) gibi | Ornament birebir dilimi, 5 - 7 saat; kapı 2 hedefi değişir (soru 17). |
| 5 | Her şekil için kütüphane kayıtları (taban sayısı T) | yukarıdaki sayılar x T | x T | x T | Kütüphane parçası (sonraki). |

(1) numaralı yolda taban hücresi her ızgarada yinelenir; yinelenenler bir kez üretilirse sayılar 35 / 101 / 199 olur
[hesap]. Yalnız yer değişen hücreler önbellekle kısalırsa (7.3) süreler düşer; ölçülmedi.

(d) Renk ve doku: bu parçada yalnız arayüz; hangi adımların yeniden koştuğu ve seçenek başına süre 3.5'te.

(e) Kararların sırayla verilmesi çarpmak yerine toplar. Örnek sayılarla [hesap; sayılar yalnız örnek, karar değil]:
yerleşim 41 seçenek (2 taban + 4 ızgara x 9 + logo ızgarası 3), renk 8 set, doku 4 set.

| Yaklaşım | Seçenek | 1087 tuval, tam çizim 12 - 28 sn [tahmin] | 5400 tuval, 54 - 62 sn [kayıt] |
|---|---|---|---|
| Sıralı: önce yerleşim, seçilen yerleşimle renk, sonra doku | 41 + 8 + 4 = 53 | 11 - 25 dk | 48 - 55 dk |
| Çarpım: her yerleşim x her renk x her doku | 41 x 8 x 4 = 1312 | 4,4 - 10,2 saat | 19,7 - 22,6 saat |

Sıralı yaklaşımın bedeli: bir yerleşimin başka renkte nasıl duracağı o yerleşim seçilmeden görülmez. İstenirse seçilen
birkaç yerleşim için çarpım (ör. 3 x 8 x 4 = 96) ara yoldur. Sıra kararı Serdar'ındır (soru 15 ile birlikte).

### 4.6 Yeni bir düzen araca nasıl eklenir

Araç ve plan düzen fikri üretmez, düzen ailesi adlandırmaz; fikir Serdar'dan ya da kütüphaneden gelir. Gelen düzenin
araca girme yolu üç basamaktır; hangisinin gerektiği gelen düzene bağlıdır:

| Durum | Ne eklenir | Etkilenen kapı | Süre [tahmin] |
|---|---|---|---|
| Düzen mevcut anahtarlarla ifade edilebiliyor | Yalnız kayıt (ayar sözlüğü); kod yok | Yok | Kayıt + onay |
| Bir öğenin yeri / boyu mevcut anahtarların dışında (ör. grup dışı öğe için yeni yer değeri) | Mevcut kurucuya yeni anahtar ya da değer: doğrulama tablosu satırı, kurucu dalı, bilinen PASS + FAIL testi | Taşma, çakışma, mm ölçerleri kendiliğinden kapsar. Mevcut sert kapılar değişmez; yeni öğe grup dışı bir altın öğeyse (ör. isimlerin arasındaki logo) "yalnız ölçek" türünde yeni sert kapı gerekir (6.1). | 1 - 3 saat |
| Grup içi ilişki değişiyor (ana sembol, halka, küçük burç, grup içi logo birbirine göre) | grup_kur'un dışında ek kurucu kod (3.4'teki ornament dilimi bu türdendir) | Kapı 2 hedefleri değişir: Serdar onayı | 3 - 8 saat + bağımsız inceleme |
| Öğelerin sıralanma mantığı başka (yeni kurucu) | Yeni kurucu fonksiyon: girdi (ürün, ayar, öğe kutuları), çıktı (öğe başına yer ve boy); mevcut çizim ve kapı zinciri aynen | Kurucuya özgü yer hedefi kapısı gerekirse yeni kapı (Serdar onayı) | 3 - 6 saat + bağımsız inceleme |

## 5. Çıktılar

| Dosya | İçerik |
|---|---|
| SEC_NN_..._onizleme.jpg | Gerçek oranda önizleme. Tuval kısa kenarı <= 1600 px [başlangıç değeri] ise tam boy; büyükse tam boyun küçültülmüşü (AT:1574 kalıbı). Yuvarlakta kesim dışı beyaz (O4:451-464 kalıbı). |
| SEC_NN_..._kesit_1x1.png | 1:1 kesit: en küçük yazı öğesi ve sembol grubunun en ince yeri (AT:1576-1582 kalıbı). Tuval tam boy verildiyse ayrıca kesit gerekmez; büyük tuvalde zorunlu. |
| SEC_NN_..._isaret.jpg | Önizlemenin kopyası: alt sınırın altındaki ya da güvenli alanı aşan öğeler çerçeveyle işaretli, yanında mm değeri. İşaret ayrı dosyadadır; temiz önizleme değişmez. |
| SEC_NN_..._OLCUM.json | Öğe başına: kutu px, genişlik / yükseklik mm. Yazı: büyük harf yüksekliği px ve mm her yazı öğesinde; küçük harf (x) yüksekliği yalnız karışık harfli mesajda ve fontun 'x' glifinden (isimler büyük harfe çevriliyor AT:178, Cinzel'de küçük harf yok). Çizgi kalınlığı px ve mm ÜÇ değerle: en ince, 1. yüzdelik, ortanca. Ortanca = 2 x yari_kal (AT:635-640; iskelet ortancası, ince yerleri göstermez); en ince ve 1. yüzdelik sırt genişliği kalıbıyla (O4:164-168, 176-198) yerleşen alfadan. Halka: nominal kalınlık = cember.json kalınlık x ölçek x halka_kalinlik çarpanı (AT:1283'ün px kısmı) + maskeden ölçülen üst, en büyük, ortanca ve açısal kapsam (halka_kalinlik_olc ATK:174-189'un px alanları; mm alanı U.DPI ile hesaplandığı için kullanılmaz, mm ürün girdisinden) + uç incelmesi. Üç çizgi değerinin her biri alt sınırla AYRI karşılaştırılır ve ayrı sütunda işaretlenir; hangisinin "sınır altı" sayımına esas olacağı ölçülmeden seçilmez (soru 4). Logo: genişlik / yükseklik px ve mm, logo yüksekliği / isim büyük harfi oranı, en ince çizgi (O4:176-198 kalıbı), temizliğin ham kesime farkı. mm_kaynak etiketi, kapı sonuçları (bölüm 6), isim küçülme oranı. Metnin kendisi yok. |
| PAFTA_<ad>_<sayfa>.jpg | Yan yana pafta. Izgarada satır = boyut adımı, sütun = yer adımı; çok anahtarlı istekte üretim sırası. Hücre etiketi 5.1'de. Etiket yalnız ölçüm; sıralama ve vurgu yok. Tipik ve en kötü ayrı pafta. Sayfa başına hücre sayısı girdi. |
| OZET.json | Her seçeneğin TAM ayar sözlüğü, taban adı, kod / ay takvimi / motor / ornament sha'ları, paket sürümleri, ürün girdisi, altın çizim sırası, seçenek başına süre, son görselin PNG sha256'sı (birebir yeniden üretim için YENİ alan; ayar listesi ve kod sha'ları emsali ATK:650-655), geri dönüş ve "bilinen çakışma" etiketleri. |
| SURE.json | Koşu ve seçenek başına makine süreleri (kurulum, zemin, altın, kayıt, kapı; AT:1392, 1430, 1540, 1570, 1605 kalıbı), tam çizim / yalnız yer ayrımı (4.5 b), bütçe ve hesaplanan sınır + aşama kaydı alanları: asama, baslangic, bitis, serdar_bekleme, deneme_sayisi, inceleme_turu. İnsan alanlarını (bekleme, inceleme turu) araç ölçemez; Merkez `sure-ekle` komutuyla girer. |
| AYAR.json | Doğrulanmış tam ayar listesi (DUR veren seçenek de yeniden üretilebilsin; ATK:649-651). |

mm formülü (Dayanak 5): mm = px x gerçek mm / baskı alanı px (eksen başına; iki eksen oranı %0,5'ten [başlangıç değeri]
fazla ayrışıyorsa girdi hatası). mm_kaynak 'varsayım' ise her mm alanının yanında etiket ve pafta başlığında tek satır not.

### 5.1 Süreç: iki yol (karar Serdar'da, soru 15)

Ortak kural, iki yolda da: her seçeneğin görseli GERÇEK yolla, tam boyda çizilir (aynı altın yolu, aynı k, aynı gren).
Küçük görsel yalnız bu tam boy görselin küçültülmüşüdür; ayrı ucuz çizim yoktur. Bu, ay takvimi deneme düzeninin kuralıdır
(AT:47: "Cizim yolu mod ornek ile AYNI (tam boy; onizleme tam boyun kucultulmusu)"; uygulaması AT:1573-1574). Kuralın genel
araçta da geçerli olup olmadığı Serdar'a sorulmadı: soru 16. Plan kural geçerliymiş gibi yazıldı.

Sonuç: iki adımlı süreç makine süresini azaltmaz (çizim aynı); azalttığı şey Serdar'a giden dosya sayısı ve bakma
süresidir.

| | (i) Tek adım | (ii) İki adım |
|---|---|---|
| Akış | Her seçenek baştan gerçek oranda: önizleme, (büyük tuvalde) 1:1 kesit, işaretli kopya, OLCUM. | Adım 1: her seçenek çizilir, Serdar'a yalnız pafta sayfaları gider; Serdar eler. Adım 2: kalan M seçenek gerçek oranda ve 1:1 kesitle. |
| Seçenek başına dosya | 3 görsel (küçük tuvalde 2: kesit yok) + OLCUM, örnek seti başına | Adım 1: pafta hücresi + OLCUM. Adım 2: seçilenler için (i)'deki dosyalar. |
| Koşu dosyaları | OZET, SURE, AYAR (+ istenirse pafta) | Aynı + pafta sayfaları + (saklama seçilirse) son görsel deposu |
| Serdar'a giden dosya, N seçenek, 2 set | büyük tuval 6 x N; küçük tuval 4 x N | 2 x ceil(N / H) pafta + adım 2'de M x (6 ya da 4) |
| Adım 2'de görsel nereden | - | (s) saklanan son görselden: yeniden çizim yok. (y) saklama yoksa OZET'teki ayardan yeniden üretim. |
| Elenen seçeneğin sonradan istenmesi | Dosyası zaten var | OZET'te tam ayarı durur: `uret --ozet OZET.json --secenek N` (saklama varsa depodan) |

H = sayfa başına hücre (25 [başlangıç değeri]; okunabilirlik ölçülmedi). M = Serdar'ın bıraktığı seçenek sayısı.

Yol (ii)'nin bir çeşidi, (ii-b): adım 1'de görsel yalnız TİPİK örnek setiyle çizilir; EN KÖTÜ set için görsel çizilmez,
yalnız geometri ÖN ÖLÇÜMÜ yapılır ve hücre etiketine "ön ölçüm (çizilmedi)" diye yazılır. En kötü setin görseli adım 2'de,
seçilenler için çizilir. Bu bir görsel değil ölçümdür; "ayrı ucuz çizim" kuralına girmez. Sınırları:

- Çizmeden ölçülebilenler (1x yazı maskeleri ve grup kurulumu yeter): isim küçülme oranı, yazı mm, çizgi mm, öğe
  maskesiyle taşma, öğe maskeleriyle çakışma.
- Çizmeden ÖLÇÜLEMEYENLER: görüntü farkıyla taşma (dış gölgeyi sayan ölçüm, 6.2), kontrast, tek doku dE00, yazım farkı,
  düz renk, yıldız, kapı 2'nin renk bölümü.
- Çizimde ortaya çıkan sert DUR'lar adım 1'de görünmez: 200 çekirdek piksel (AT:622-623), k kat çizim kaynaktan büyük
  (AT:860-861), çerçeve (AT:865-873), çentik bandı (AT:879-880). Adım 1'de seçilen bir seçenek adım 2'de en kötü setle DUR
  verebilir; o zaman DUR raporlanır, seçenek gizlenmez.
- Bedeli: Serdar eleme sırasında en kötü durumu görmez, yalnız ön ölçüm sayılarını okur.

Makine süresi [1087 tuval: tahmin, seçenek 12 - 28 sn; 5400 tuval: hesap, seçenek 54 - 62 sn [kayıt]; önbelleksiz;
kurulum 15 sn hariç; en kötü set geometri ölçümü 1 - 3 sn (1087) ve 2 - 6 sn (5400) tahmin]:

| Yol | 1087: N = 25 | N = 60 | N = 120 | 5400: N = 25 | N = 60 | N = 120 |
|---|---|---|---|---|---|---|
| (i), iki set | 10 - 23 dk | 24 - 56 dk | 48 - 112 dk | 45 - 52 dk | 108 - 124 dk | 216 - 248 dk |
| (ii), iki set, adım 1 | 10 - 23 dk | 24 - 56 dk | 48 - 112 dk | 45 - 52 dk | 108 - 124 dk | 216 - 248 dk |
| (ii-b), adım 1 | 5 - 13 dk | 13 - 31 dk | 26 - 62 dk | 23 - 28 dk | 56 - 68 dk | 112 - 136 dk |
| tek set (karşılaştırma) | 5 - 12 dk | 12 - 28 dk | 24 - 56 dk | 23 - 26 dk | 54 - 62 dk | 108 - 124 dk |

Adım 2 süresi: (s) saklanan görselden dosya çıkarma, seçenek başına birkaç saniye [tahmin]; (y) yeniden üretim, M x seçenek
süresi; (ii-b)'de ayrıca M x en kötü set çizimi (M = 5: 1087'de 1 - 2,3 dk [tahmin], 5400'de 4,5 - 5,2 dk [hesap]).

Disk [tahmin; ölçülmedi]: 1087 tuvalde son görsel PNG 2 - 3 MB; 120 seçenek x 2 set 0,5 - 0,7 GB. 5400 x 7200 tuvalde tam
boy PNG 40 - 90 MB; saklama (s) N = 60, iki set için 5 - 11 GB, N = 120 için 10 - 22 GB. Büyük tuvalde saklama yerine
yeniden üretim (y) disk istemez, adım 2 süresini uzatır.

Serdar'a giden dosya sayısı, N = 60, iki set, H = 25, M = 5 [hesap]: (i) büyük tuval 360, küçük tuval 240 görsel.
(ii) adım 1: 6 pafta sayfası; adım 2: 30 (büyük) ya da 20 (küçük) görsel; toplam 36 ya da 26. (ii-b) adım 1: 3 pafta
sayfası; toplam 33 ya da 23.

Kural kontrolü (testler bölüm 8'de). Kanıt üç halkadır; tek başına sha karşılaştırması yetmez (aynı kod hem dosyayı hem
OZET'i yazdığı için döngüsel olurdu):

1. Tek üretim yolu. Son görseli üreten TEK fonksiyon vardır; pafta koşusu da tek seçenek komutu da onu çağırır. Pafta
   üreticisi çizim fonksiyonlarına erişmez; girdisi kaydedilmiş son görsel dosyalarının yolları ve OZET'tir. Saklama
   yoksa (y) son görseller geçici klasöre yazılır, pafta üretildikten sonra silinir.
2. Bağımsız yeniden üretim. Paftadan örneklenen hücreler (ilk, son ve aradan girdiyle verilen sayıda) AYRI süreçte
   `uret --ozet OZET.json --secenek N` ile yeniden üretilir; PNG sha256'sı OZET'teki ile ve paftaya giren dosyanınkiyle
   aynı olmalı. Hücre pikselleri = o dosyanın tek adım INTER_AREA küçültülmüşü (yeniden küçültmeyle birebir, JPEG'e
   yazılmadan önceki dizi).
3. Yolun "gerçek yol" olduğu. OZET'e seçenek başına tuval boyu, her öğenin k değeri ve altın sırası yazılır; test bunları
   ayardan bağımsız yeniden hesaplar (tuval = ürün baski_px; yazıda k = cizim_katsayisi, AT:577; grupta AT:1265-1267) ve
   altın yolunun içe alınan AT fonksiyonları olduğunu yüzey testiyle (2.3) bağlar. Bilinen FAIL: k'yi düşüren ya da küçük
   tuvalde çizip büyüten bozuk üretici kopyası; 2. halkadaki yeniden üretimle sha'sı uyuşmaz ve 3. halkadaki k / tuval
   kontrolü FAIL verir.

- Adım 2 = adım 1 ile aynı görsel. (s): çıkarılan dosyaların kaynağı sha256'sı OZET'teki ile aynı olan saklanan görseldir.
  (y): yeniden üretilen son görselin sha256'sı OZET'teki ile aynı olmalı (aynı ürün girdisi, katman, sha'lar, ortam);
  farklıysa DUR ve farkın nedeni raporlanır.
- Sert kapıdan geçemeyen seçeneğin hücresinde görsel yoktur; hücrede "DUR" ve kapı kodu yazar (seçenek gizlenmez,
  numarası boş kalmaz).

"Son ürün" sınırı (olgu): bu kontroller deneme görselinin ARACIN gerçek yoluyla çizildiğini kanıtlar. Aracın yolu ay
takvimi altın yoludur (AT). Seçilen tasarımın ürün hattı başka bir yol kullanırsa "deneme görseli = son ürün görselinin
küçültülmüşü" sağlanmaz: örneğin ornament ürün hattı kendi motorunu kullanıyor (sabit 10 kat çizim OM:46; logoyu 10 kat
boyda büyütüyor OM:427-429, 672). Ürün hattı bu parçanın dışındadır; kuralın tam sağlanması için ürün hattının aynı
ayardan ve aynı yoldan üretmesi gerekir (soru 16).

Hücre etiketi (küçük görselde görülemeyenler ölçümle yazılır; düz metin, tek renk, vurgu ve sıralama yok): seçenek no;
tabana göre değişen anahtarlar ve değerleri; en küçük yazı mm (büyük harf); çizgi mm (en ince / 1. yüzdelik / ortanca);
alt sınır altındaki öğe sayısı (ölçüt başına ayrı, soru 4); taşan piksel sayısı; çakışan piksel sayısı; isim küçülme
oranı; (ii-b)'de aynı ölçümlerin en kötü set karşılığı; mm_kaynak 'varsayım' ise etiket.

Olgu: ince çizgi ve küçük yazı pafta hücresinde görülmez; yol (ii)'de eleme bu ayrıntı görülmeden, etiketteki sayıya
bakılarak yapılır. 1087 tuvalde son görsel zaten küçüktür (hücreye yaklaşık yarı boyda girer [hesap: 5 sütun, 2700 px
sayfa genişliği varsayımıyla]); 5400 tuvalde hücre son görselin yaklaşık onda biridir.

Teknik öneri (süreç; görsel tercih değil): seçenek sayısı bir pafta sayfasını aşmıyorsa (i) ile (ii) arasında makine
farkı yoktur, (i) yeterlidir. Seçenek sayısı büyüdükçe (ii) Serdar'a giden dosyayı yaklaşık onda bire indirir; (ii-b)
ayrıca makine süresini yarıya yaklaştırır. Büyük tuvalde bütçe, seçenek sayısını (ii-b)'de bile sınırlar (4.5 b).

## 6. Kapılar

Yeni aracın tek modu denemedir. Ay takvimi deneme modunun sert / ölçer ayrımı (Serdar 11 Kas "A"; AT:45-47, ATK:49-53)
taban alınır. Planın bu tabandan ve ornament emsalinden AYRILDIĞI her yer 6.4'te adıyla yazılıdır ve Serdar onayı ister
(soru 6). Takvime özel olduğu için uygulanamayan kapılar 6.3'tedir (soru 6 a). Eşik değeri bu planda değiştirilmez ve
önerilmez; yeni ölçümler eşiksiz yazılır.

### 6.1 Sert (FAIL = o seçeneğin görseli yok / silinir)

| Kapı | Kaynak | Neden sert |
|---|---|---|
| girdi (ürün, ayar, ızgara, isim, metin) | kalıp AT:167-306; çıkış 3 AT:1718 | Yanlış giriş görsel üretmemeli. Anahtar ve aralık tablosu bu aracın kendisinindir (3.3); kucuk_v alt ucu takvimdeki 0,60 yerine 0,20 (Merkez teyidi: soru 6). |
| ortam: pillow 11.0.0 + raqm | AT:1389-1391; W:96-97; CM:93-97 | Glif yerleşimi sürüme bağlı. |
| motor dosyaları ve KILIT dalları | AT:688-702 | Altın yolu değişmez. |
| sabit sha'lar (motor, ornament, ay takvimi) + yüzey testi | W:71-79; ATT:39-46 | Kaynak değişirse eşdeğerlik düşer. |
| sembol biçimi (RGBA, alfa) | AT:998-1005 | |
| şekil değişmez (takvim kapı 2'nin sembol bölümünün TAMAMI, ATK:406-440; grup bölümü ayrı satırda, kapı 2 toplamı ATK:406-452): en boy farkı <= 0,005; ölçek <= 1; son dosyada sembol rengi küçültülmüş katmanla aynı (tam alfa pikselde fark <= 1 seviye, ATK:412-424); yarı saydam kenar pikselleri sınır içinde (ATK:425-431); kaynak sha aynı ve yerleşen = kaynağın yalnız eş oranlı küçültülmüşü, birebir (ATK:435-440) | ESIK ATK:75 | Dayanak 3; sembol dokunulmaz (AT:20, 23-24). Deneme modunda başka öğenin örttüğü sembol pikseli renk karşılaştırmasına girmez (ATK:415-423); aynen. |
| büyütme yok: grup ölçeği, ana ölçek, küçük ölçek <= 1; k kat çizim kaynaktan büyük değil | AT:1226-1227, 860-861; ATK:233, 244 | Dayanak 3. |
| grup yeniden kurulum + bağımsız ölçüm (kapı 2 grup bölümü): öğe listesi ayara göre tam (halka, küçük 1, küçük 2, logo varsa logo; ATK:221-223, 234); her maske kaynağın tek adım küçültülmüşü; halkaya uydurulan çember, küçük sembol yeri / boyu, ana sembol yeri, en uzak piksel = hedef yarıçap (kalın halkada ölçerek geri alma, ATK:257-283), logo yeri / boyu (ATK:322-343); pay 2 px | ATK:209-360; ESIK ATK:77-78 | Dayanak 3. Pay 5400 tuvalde yerel ölçüldü (ATK:32-34); 1087 tuvalde [ölçülmedi]: ilk yerel koşuda 'fark_en_buyuk' okunur, eşik ancak ölçümle ve Serdar onayıyla değişir. Merkez bilgisi (11 Kas; tahmin, ölçülmedi): gerçek katmanda bu fark yerel ölçümden yaklaşık 0,65 px yüksek çıktı; ayar aralığının ucunda 2,0 eşiği aşılabilir. Takvime bağlı iki alt koşul düşmez, karşılığıyla taşınır: "grup merkezi = disk merkezi" (ATK:249, 355) yerine "grup merkezi = ayardaki grup_x / grup_y'nin tuval noktası"; "'halka' merkezde halka merkezi takvim merkezinde" (ATK:255-256) yerine "halka merkezi o noktada" (aynı 2 px pay). Kombinasyonlarda tanım: 4.3. |
| logo yalnız ölçek. Küçük burç arası yerde: kapı 2'nin logo bölümü aynen (yeniden kurulumda maske birebir, yer ve boy 2 px pay içinde; ATK:221-223, 234, 322-343), toplam ölçek <= 1 (AT:1249-1250). İsim arası yerde (dilim 3): aynı tanımın karşılığı yeni kapı: yerleşen maske = logo_kaynak çıktısının TEK adım küçültülmüşü (birebir), ölçek <= 1, k kat çizim kaynaktan büyük değil | AT:1159-1175, 1245-1270; kalıp ATK:238-244 | Dayanak 3 (logo: yalnız ölçek + altın). "Kaynak" = temizlenmiş poster kesimi (AT:1170): temizliğin kendisi şekle dokunabilir; ham kesime farkı OLCUM'a bilgi olarak yazılır, kabulü soru 7b. Not: OM logoyu 10 kat çizimde büyütüyor (OM:427-429; OM:672 "1.41 buyutme"); AT yolunda k kaynağa göre düşer (AT:1265-1267), büyütme olmaz. |
| çerçeve tutarlılığı (k kat çerçeve = 1x çerçevenin tam katı) | AT:865-873 | Yazım kapısının ön koşulu. |
| renk uyumu için >= 200 çekirdek piksel | AT:622-623; ESIK ATK:74 | AT:46-47'de sert. Küçük tuvalde ince öğelerde tutmayabilir [ölçülmedi]; tutmazsa o seçenek DUR verir, kapı değişmez. |
| ana sembol tuval dışına taşıyor (kısmen de olsa); herhangi bir öğe tümüyle tuval dışında; isim satırı 8 denemede sığmıyor | AT:1503-1507; AT:572-573 | Takvim deneme modunda da DUR. |
| çıktı: boyut = ürün baski_px, RGB, sRGB ICC | ATK:599-601 (boyut ve dpi koşulu ürüne göre; soru 6 b) | SINIF DEĞİŞİKLİĞİ (6.4): takvim deneme modunda kapı 10 ölçerdi (sert olanlar ATK:603); burada sert. Serdar onayı: soru 6 c. |

### 6.2 Ölçer-yazar (FAIL görseli durdurmaz; OLCUM'a ve işaretli önizlemeye yazılır)

| Kapı | Kaynak | Neden ölçer |
|---|---|---|
| gerçek ölçü uyarısı (yazı mm, çizgi mm < alt sınır) | YENİ (Dayanak 2c, 5) | Tanım gereği: seçenek gizlenmez. |
| güvenli alan / yasak bölge taşması (piksel sayısı, öğe adı) | tanım O4:219-270, 425-437 | Yeni kapı ve ornament emsaline göre fark (6.4): ornament motorunda sert (yerleşim kapısı FAIL = çıkış 1, OM:349-356; son görselde yasak piksel 0, OM:783); araçta ölçer. Gerekçe: araç Serdar'a taşan seçeneği de gösterir (emsal 'tasma' AT:45-46, 1508). Serdar onayı: soru 6 d. İki ölçüm birlikte: öğe maskesi (alfa > 0,02; öğe adı için) ve görüntü farkı (son görsel ile altınsız zemin farkı > 1; O4:425-437 yolu; dış gölgeyi de yakalar, AT:136, 1631). |
| grup - yazı boşluğu (px ve mm) | ATK:521-530, 548; ESIK ATK:76 (12 px, 5400 tuval) | ATK:52. Takvimde "grup - ay adı"; araçta grup ile her yazı öğesi arası. Eşik 12 px aynen yazılır; başka tuvalde anlamı [ölçülmedi] (soru 6). |
| metin tabanı tutarlılığı | ATK:579, 591 | ATK:52. |
| kombinasyonda çizilmeyen öğe son görselde yok (yol K-a) | YENİ (4.3) | Ölçülmeden sert konmaz (CM:214-216); eşik yok. Soru 6 k. |
| öğe çakışması / altın binme | O4:255-269; ATK:504-518 | Ornament emsaline göre fark (6.4): ornament motorunda çakışma yerleşim kapısının parçası ve sert (O4:270; OM:349-356); araçta ölçer. Takvim deneme modunda da ölçerdi (ATK:52), yani tabana göre değişiklik değildir. B1 adayında FAIL yazması beklenir (3.4). Serdar onayı: soru 6 e. |
| tek doku dE00 <= 2,0 | ATK:453-493; ESIK ATK:74 | ATK:52. |
| kontrast >= 4,5 | ATK:104-123, 494-497 | ATK:52. |
| yazım alfa farkı <= 0,035 | ATK:479-480, 499 | ATK:52. |
| altın öğede düz renk yok (yayılım >= 40); halka yalnız bilgi | ATK:482-483, 560-566 | ATK:52. |
| isim satırı sınırı ve küçülme | AT:558-574; ATK:567-571 | AT:45. Alt sınır takvimde ay adı boyuydu (AT:1434); yeni araçta ürün alt sınırı (yazi_mm). |
| metin satır genişliği | AT:1442-1449 | AT:45. |
| yıldız altın öğeye değmez (12 px pay) | ATK:561-566; ESIK ATK:81; engel maskesi kalıbı AT:1515-1529 | ATK:52. Zemin 'motor' olduğu sürece geçerli. SORUN: üretimdeki yıldız engel payı tuvale oranlı (61 x W / 7200, AT:1526): 5400 tuvalde 47 px, 1087 tuvalde 9 px çekirdek = +-4 px [hesap]; kapı payı sabit 12 px. Küçük tuvalde öğeye 5 - 12 px yakın düşen bir yıldız FAIL yazdırır; böyle bir yıldızın fiilen çıkıp çıkmayacağı [ölçülmedi] (olası). Bu planda ne kapı payı ne engel payı değiştirildi: soru 6 j. |
| öğe sayısı tamlığı (beklenen öğe listesi = çizilen öğe listesi; kombinasyonda beklenen liste ayardan) | ATK:485-493 | ATK:52; takvimde kapı 3'ün parçası. |
| sayfa kenarı payı | ATK:541, 549 (180 px, 5400 tuval) | Yerine ürün güvenli alanı kapısı (yukarıda); dikdörtgen ürünlerde güvenli alan = kenar payı. |

### 6.3 Uygulanamayan takvim kapıları (kapatma değil, kapsam dışı; Serdar teyidi istenir)

Kapı 1 veri ve evre (ATK:399-404), kapı 6'nın disk bölümleri (yazı - disk, disk - disk, sembol - disk; ATK:501-549), kapı
7'nin "altın dışı öğede altın yok" bölümü (ATK:550-558; yeni araçta altın dışı öğe yok), kapı 9 blok dikey ortalaması
(ATK:572-591; yeni araçta yer AYAR'dan gelir), kapı 10'un yalnız "5400 x 7200" ve "300 dpi etiketi" koşulları
(ATK:599-601; boyut ürün baski_px olur, dpi etiketi ürün girdisinden hesaplanan değer olur; RGB ve sRGB koşulları 6.1'de
sert kalır), kapı 0 "ayar = varsayılan" (ATK:382-387; yalnız mod örnek) ve mod tutarlılığı (ATK:386, 603; araçta tek mod
var). Kapı 8'in isim alt sınırı ay adı boyundan (ATK:571) ürünün yazı alt sınırına geçer. Ornament yasak bölge kapısının
ornament'e özgü parçaları ürün girdisine parametre olur: ışık taşması için 8 px genişletme (O4:249; araçta ışık taşması
yok, ama genişletmeyi 0 yapmak ölçüm bölgesini daraltır: bu yüzden 6.2'de görüntü farkı ölçümü de var; genişletme
değeri soru 6), halkanın delik / üst çizgi istisnası
(O4:243-252; ürün girdisinde yasak bölge başına "halka hariç" işareti), güvenli daire payı 3 px (O4:45, 222; ürün
girdisinde pay alanı). Eşdeğerlik testi bu üç parametre 954 değerleriyle verilerek yapılır.

### 6.4 Tabandan ve ornament emsalinden ayrılan yerler (Serdar onayı ister; soru 6)

Ölçüt: taban ay takvimi DENEME modudur (ATK:52: sert = kapı 1 veri, kapı 2, mod tutarlılığı; diğerleri ölçer). Tabana
göre ayrılmalar:

| Kapı | Takvim deneme modunda | Bu planda | Tür | Soru |
|---|---|---|---|---|
| çıktı (boyut, RGB, sRGB ICC) | ölçer (ATK:603) | sert | sıkılaştırma (CM:214-216: ölçülmeden / sorulmadan konmaz) | 6 c |
| güvenli alan / yasak bölge taşması | yok (karşılığı: 'tasma' ve sayfa kenarı, ikisi de ölçer) | yeni kapı, ölçer | yeni kapı | 6 d |
| kombinasyonda kapı 3, 4, 7, altın binme, yıldız, taşma kapsamı | bütün grup öğeleri | yalnız boyanan öğeler (yol K-a) | kapsam daralması | 6 k |
| AYAR kucuk_v alt ucu | 0,60 (AT:115) | 0,20 | girdi aralığı genişlemesi | 6 h |

Ornament emsaline göre (ornament motorunda sert, FAIL = çıkış 1; OM:782-792, 833-837) bu planda sert OLMAYAN kapıların
tam listesi; hepsi takvim deneme modunda da sert değildir:

| Ornament motorunda sert | Bu planda | Soru |
|---|---|---|
| yerleşim kapısı: yasak bölge + çakışma (OM:349-356; O4:270) ve son görselde yasak piksel 0 (OM:783) | ölçer | 6 d, 6 e |
| kontrast >= 4,5 (OM:782) | ölçer (takvim deneme ile aynı) | 6 l |
| alfa farkı <= 0,035 (OM:790), dE00 <= 2 (OM:791) | ölçer (takvim deneme ile aynı) | 6 l |
| IoU >= 0,98 küçük burç ve logo (OM:789), leke ve ton (OM:784-787), boşluk 20 / 20 / 20 (OM:788), ornament'e özgü diğerleri (OM:792-794) | yok (ornament'in kaynak onarımı, ton ve sabit düzen kapıları; araçta karşılığı kapı 2'nin "birebir küçültme" kanıtı ve çakışma / boşluk ölçerleri) | 6 l |

Onay gelmezse: çıktı kapısı ölçer kalır; taşma ve çakışma sert olur (o zaman B1 ve B2 adaylarının görseli üretilmez,
çünkü ikisinin de bilinen ya da beklenen taşması / çakışması vardır); kombinasyon K-a kullanılamaz.

## 7. Koşu yeri ve hız

### 7.1 İki yol

| | (i) Yerel, deneme sembolüyle | (ii) Actions, gerçek katmanla |
|---|---|---|
| Ana sembol | deneme_komut çıktısı (AT:1679-1697) | Drive katmanı (W:124-136) |
| Diğer kaynaklar | Hepsi depoda: motor, halka, küçük burçlar, fontlar, logo (MG) | Aynı |
| Onay | Koşu başına gerekmez (görsel yüklenmez; DENEME_ adlı) | Her koşu dispatch + onay dizesi (W:21, 38-58) |
| Çıktı | Oturumun çalışma klasörü; Serdar'a pafta gösterimi ayrı karar | Drive TEMP (W:240-262) |
| Depo kuralı | CM:111 "iterasyon yerelde"; CM:98-99 "tüm üretim Actions'ta koşar (KARAR 3)". Serdar'a gösterilecek karar görselinin yerelde üretilmesi bu iki kuralın arasında kalıyor: soru 1. | CM:98-99 ile uyumlu; CM:111-112 "Actions yalnız yerelde temiz çıkan sürüm için, en fazla 1 kez". |
| Sabit yük | Ortam kurulumu bir kez [tahmin: 2 - 4 dk] | Koşu başına checkout + paket + rclone + sembol indirme [tahmin: 2 - 4 dk; ölçülmedi] + kuyruk |

### 7.2 Süre

Mevcut ölçüm [kayıt, AT:48-49; 5400 x 7200, 4 çekirdek; Merkez doğrulamadı]: deneme başına üretim 46 - 52 sn (zemin 5 - 6,
altın 18 - 22, PNG + DUMP 20 - 21) + kapı 8 - 10 sn; ilk örnekte +15 sn. Seçenek başına toplam 54 - 62 sn [hesap]. Bu
rakamlar halka kalınlığı ve logo eklenmeden önceki koddandır; kalın halka ve 'yumusak' çentik ek çizim getirir (AT:867-883),
süresi [ölçülmedi].

1087 x 1087 tuvale geçiş [tahmin; ölçülmedi]:

- Zemin ve kayıt piksel sayısıyla ölçeklenir: 38,9 MP -> 1,18 MP (33 kat az [hesap]); her biri 1 sn altı beklenir.
- Kapı ölçeklenmez: kapı 2 tam çözünürlüklü katmanı yeniden küçültüyor ve grubu yeniden kuruyor (ATK:436-437, 218-222);
  bunlar tuval boyundan bağımsız. Motor yeniden kurulmaz (aynı süreç). Beklenen 2 - 6 sn.
- Altın ölçeklenmez: her öğe poster ölçeğine yakın çizilir (k kat; yazıda büyük harf x k ~ 298 px AT:579, grupta k =
  1 / ölçek AT:1265). Halka kaynağı en büyük iştir. Öğe sayısı takvimden az (takvim 14 - 17 yazı + 3 - 4 grup; araç en çok
  5 yazı + 4 grup). Beklenen 8 - 20 sn; üst sınır mevcut 18 - 22 sn.
- Tam çizimli seçenek: 12 - 28 sn; kurulum 15 sn (koşu başına bir kez).
- Yalnız yer ya da zemin değişen seçenek, motor katmanı önbelleği varsa (7.3 madde 4): 3 - 8 sn. Önbellek dilim 1'de
  yoktur; o zaman her seçenek tam çizimdir.
- halka_r modunun iki geçişi (3.3) seçenek başına bir ek küçük kurulum getirir: 0,5 - 2 sn.
- Actions'ta aynı süreler + sabit yük (7.1).

Seçenek sayısına göre toplam süre, iki yol ve iki tuval için: 5.1 tablosu. Genişletme yollarına göre: 4.5 c tablosu.
Bütün [tahmin] rakamlar ilk dilimin ölçüm koşusunda SURE.json ile ölçülür; seçenek sınırı o ölçümden ve bütçeden
hesaplanır (4.5 b). Büyük tuvalde gerilim [hesap, AT:48-49 kaydından]: 60 seçenek 54 - 62 dk, 120 seçenek 108 - 124 dk
(tek set); 50 dakikalık bir bütçeyi aşar. Hangisinin öncelikli olduğu (kural mı, seçenek sayısı mı) soru 16.

### 7.3 Çıktıyı değiştirmeyen hızlandırmalar

1. Tek süreç, tek Motor, tek renk haritası: takvimde her deneme ayrı süreç ve kapı ayrıca Motor kuruyor (W:195, ATK:218).
   Harita önbelleği zaten var (AT:793-813).
2. DUMP.npz yazılmaz: takvimde kapı ayrı süreç olduğu için maskeler dosyaya yazılıyor (AT:1598-1604, 20 - 21 sn'nin
   parçası). Yeni araçta kapı aynı süreçte, maskeleri bellekten alır; son görseli yine KAYDEDİLEN dosyadan okur ("ölçüm
   son dosyadan" ilkesi ATK:3 korunur). Piksel çıktısı aynı.
3. Büyük tuvalde (dikey 5400) tam boy PNG Serdar'a gitmez; yalnız önizleme + 1:1 kesit (W:10-11 ile aynı karar). Tam boy
   görsel yine çizilir (5.1 ortak kural); saklanıp saklanmayacağı 5.1'deki (s) / (y) seçimidir.
4. Motor katmanı önbelleği (dilim 1'de YOK; ölçüm gerek gösterirse ayrı dilim). Olgular:
   - Gren ana üreteçten (tohum 11; AT:854) öğe sırasıyla ve k KAT çerçeve boyutunda çekilir (AT:828): bir öğenin katmanı
     kendinden ÖNCEKİ öğelerin ana üreteçten çektiği miktara bağlıdır.
   - Kalın halka (halka_kalinlik 1,0'dan büyük) AYRI üreteçten boyanır (tohum [11, 1]; AT:868), ana üreteç özgün halka boyu
     kadar ilerletilir (AT:869; boy AT:1229-1239): kalın halkanın katmanı önceki öğelere bağlı değildir; sonraki öğeler
     çarpandan etkilenmez.
   - 'yumusak' çentikte aynı ayrı üreteçle ikinci bir katman çizilir (AT:875-883).
   - altin_ogeler tek fonksiyondur ve aynen çağrılır; önbellek onun İÇİNE konamaz. Yol: Motor nesnesinin önüne, yalnız
     oge_katman çağrısını saklayan bir vekil nesne konur; altin_ogeler vekille aynen çağrılır.
   - Anahtar = (k kat alfa, k, motor adı, harita kimliği, üreteç türü; ana üreteçse çağrı anındaki üreteç durumu). Üreteç
     durumu anahtarda olduğu için "önceki öğeler" ayrıca izlenmez. İsabette vekil saklanan çıktıyı döndürür VE üreteci
     saklanan son duruma getirir (yoksa sonraki öğenin greni değişir).
   - renk_uyum (hedef: ana sembolün Lab ortancası; AT:874, 1558) ve iç gölge oranı (AT:884-885, 1423) altin_ogeler'in
     içindedir, her seçenekte yeniden yapılır; birleştirme (boya) dışarıdadır (AT:1568 kalıbı) ve o da her seçenekte
     yapılır. Yarı kalınlık ölçümü (iskelet; AT:884) kalın halkada pahalı olabilir [ölçülmedi].
   - Test: önbellekli ve önbelleksiz son görsel bayt bayt aynı (halka kalınlığı 1,0 ve 2,0; çentik iki değer; logo var / yok).
5. Çizim sırası: varsayılan emsal sırasıdır (yazılar önce, grup öğeleri sonra, logo sonda; AT:853, 1253). Bu sırada bir
   yazının boyu değişince sonraki öğeler yeniden çizilir (halka kalınlığı 1,0 iken halka dahil). Sıra "halka, küçük
   burçlar, logo, yazılar" yapılırsa önbellek daha çok tutar, ama gren deseni emsalden ayrılır (çıktı değişir): soru 13.

Önerilmeyenler (çıktıyı değiştirir): düşük çözünürlükte çizim, k'yi düşürme, grensiz çizim, başka altın yolu (ör. O1
tek_doku), öğe başına ayrı tohum, pafta için ayrı ucuz çizim.

### 7.4 Deneme sembolü ile gerçek katman farkı

Olgular: (a) deneme sembolü poster ana alfasının motorla gölgelenmiş halidir (AT:1680, 1684-1689); gerçek katman Drive'daki
ayrı dosyadır; yüzey rengi / dokusu aynı olmak zorunda değil. (b) Sınır kutularının aynı olduğu doğrulanmamış (YDT:3-4
açıkça yazıyor; ATK:32-34 "gerçek Drive katmanıyla ölçülmedi"). (c) Diğer altın öğelerin rengi ana semboldeki Lab
ortancasına kaydırılıyor (AT:1558, 618-632): sembol rengi farklıysa TÜM öğelerin tonu farklı çıkar.

Yerleşim kararına etkisi: yer ve boy alfa siluetine bağlıdır; (b) küçükse yerel görsel yerleşim kararı için geçerlidir.
Renk / doku kararı (sonraki parça) için (a) ve (c) nedeniyle gerçek katman gerekir.

Ölçüm yolu: aynı ayarla bir kez iki kaynakla üretim; SEMBOL_OLCUM alanları (kutu, en boy, çevre yarıçapı; AT:1006-1012),
grup_kur çıktıları (ölçek, ana sembol yeri ve boyu) ve yerleşen alfa farkı (IoU, en büyük kenar kayması px) karşılaştırılır.
Yeterlilik eşiği (ör. 1087 tuvalde kaç px fark kabul) bu planda konmaz; ölçüm sonucu Merkez'e gider, eşik Serdar /
Merkez kararıdır.
Gerçek katman ölçümü ay takvimi koşularının Drive'daki SEMBOL_OLCUM.json dosyasında zaten olabilir (bu oturum okumadı).

### 7.5 Ortam sabitleme (yerel)

Sürümler iş akışınınkiyle aynı (W:82, 95): Python 3.13, pillow 11.0.0, numpy 2.5.4, opencv-python-headless 5.0.0.93,
scipy 1.18.1, scikit-image 0.26.0, potracer 0.0.4, pyyaml 6.0.2; raqm için libfribidi0 (W:94). `python3 -m venv` + sabit
sürümlü pip (CM:96); araç başlarken pillow sürümü ve raqm'ı sert kontrol eder (AT:1389-1391), sürümleri OZET'e yazar
(AT:1635). Bu kapta Pillow 12.3.0 kurulu: sistem Python'u kullanılamaz, venv zorunlu. Kaynaklar `git archive <sha>` ile temiz klasöre alınır (CM:113; içe alınan dosyalar için `git check-ignore`
taraması). raqm bu kapta kurulabilir mi [ölçülmedi]: kurulamazsa yerel yol DUR verir, kapı gevşetilmez (soru 1'e bağlı).

## 8. Testler

Kural: her kapı bilinen PASS + bilinen FAIL; test gerçek fonksiyonu çalıştırır; mutasyon denemesi (kod bozulunca test FAIL);
test komutu tek başına koşar, çıkış kodu ayrı okunur (CM:208, 209, 217; "Test 3 dersleri").

| Test | Bilinen PASS | Bilinen FAIL |
|---|---|---|
| girdi: ürün şeması | iki deneme girdisi | eksik alan, negatif px, eksen oranı ayrışması, desen dışı ad, bilinmeyen şekil |
| girdi: AYAR ve ızgara | taban verilince eksik anahtar tabandan; aralık uçları; ürüne göre hesaplanan üst uç (halka_r, 3.3) | taban yok; ATT:148-163 listesinin karşılığı (bilinmeyen anahtar, aralık dışı, tür, bool, sonsuz, NaN, 10^400, yinelenen anahtar); halka_r ve grup_r birlikte; 5400 girdisinde halka_r 1,15 (ölçek > 1); 'yumusak' çentik + kalınlık 1,0 |
| enjeksiyon | zararsız özel karakterli geçerli örnek metin (izinli küme AT:141) kabul edilir, dosya adı değişmez | ATT:167-175 ve 769 kalıbı: değer içinde kabuk karakteri / satır sonu / log komutu; hata mesajında ham girdi yok; dosya adı koddan |
| mm formülü | [varsayım] girdisiyle: 1087 px -> 25,4 mm; 64,2 px -> 1,5 mm; işaret eşiğin iki yanında doğru | sınırın 0,01 mm altı işaretlenir, üstü işaretlenmez; mm_kaynak 'varsayım' iken etiket yoksa FAIL. Yalnız formülü sınar. |
| yüzey testi | AY_SHA dosya sha'ları ve imzalar | bir imza değiştirilmiş kopya |
| eşdeğerlik: logo fonksiyonları | O4:156-198 kaynaktan çıkarılıp aynı girdiyle aynı çıktı (ATT:77-100 yardımcıları kalıbı) | bir satırı değiştirilmiş kopya |
| eşdeğerlik: yasak bölge | 954 sabitleriyle O4 yasak_m / kapi ile aynı piksel sayıları | yarıçapı 1 px büyütülmüş ürün girdisi |
| eşdeğerlik: grup kapısı | takvim META'larıyla (halka kalınlığı 1,0 ve 2,0; çentik iki değer; logo yok ve var) ATK grup_kapisi ile aynı sayılar | ATT:1467-1526 mutasyonları (büyütme, ana sembol kayması, küçük sembol yeri) + ATT:1374-1376, 1456 kalıbı (görsel ve META ayarı uyuşmuyor: kalın halka / logo) |
| şekil değişmez / büyütme yok | deneme sembolü, temiz örnek ayar | esnetilmiş sembol (ATT:223 sahte_sembol esnet), ölçek > 1 isteyen ayar, kaynaktan büyük k |
| logo yalnız ölçek | depodaki logo, çarpan 1,0 ve 1,25 | 3 px kaydırılmış logo; kalınlaştırılmış (genişletilmiş) logo maskesi; toplam ölçek > 1 isteyen çarpan (girdi hatası); logolu görsel + logosuz ayar ve tersi |
| gerçek ölçü, taşma, çakışma (ölçer) | temiz örnek ayar (taşma ve çakışma yok) | bilerek küçük yazı; güvenli alan dışına itilmiş öğe; üst üste iki öğe: OLCUM'da FAIL, görsel VAR |
| aynı girdi, aynı çıktı | aynı girdiyle iki koşu: PNG sha256 aynı; taban adıyla üretim = tabanın tüm anahtarları açıkça verilmiş ayarla üretim (ATT:209-210 kalıbı) | bir anahtarı değişmiş ayar: sha farklı |
| önbellek (dilim 6) | önbellekli = önbelleksiz son görsel (bayt); halka kalınlığı 1,0 ve 2,0, çentik iki değer, logo var / yok | isabette üreteç durumu geri yüklenmeyen bozuk vekil: sonraki öğe farklı, test FAIL |
| kayıttan yeniden üretim | kayıt -> üretim -> PNG sha256 kayıttaki ile aynı | sha'sı farklı kod / motor ile DUR |
| tek öğe değişir (birleştirme ÖNCESİ katmanda) | halka_r + 'halka' merkezde kucuk_v / kucuk_oran değişince ana sembolün (rgb, alfa, yer) ve halkanın (maske, yer, k, motor katmanı) dizileri bayt bayt aynı. Son görselde eşitlik ARANMAZ (binme, dış gölge). | grup_r modunda ya da 'grup' merkezde aynı test FAIL vermeli (bağın gerçekten yakalandığının kanıtı). Sınır testi: isim boyu değişince küçük burç motor katmanı DEĞİŞİR (gren sırası); maske ve yer aynı kalır. |
| kombinasyon, kapı 2 (yol K-a) | küçük burç "çizilmedi": kalan öğelerin kutuları tam setle aynı; kapı 2 PASS (tam liste, geometri maskelerinden ölçüm); logo 'yok': kapı 2 PASS | geometri maskesi kapıya verilmemiş (kapı 2 sert FAIL); geometriyi eksik setle yeniden kuran bozuk kopya (kutular değişir) |
| kombinasyon, diğer kapıların kapsamı (yol K-a) | çizilmeyen küçük burç: kapı 3, 4, 7, altın binme, yıldız, taşma ve öğe sayısı yalnız boyanan öğelerle PASS; B1'de sembolün küçük burç bölgesine binmesi "çizilmeyen öğe yok mu" ölçümünü bozmaz (bölge çıkarılır) | çizilmeyen öğeyi boyanan listeye sokan bozuk kopya: kapı 3 / 4 FAIL; çizilmedi işaretli öğe gerçekte boyanmış: yeni ölçüm fark yazar; boyanan bir öğenin kontrastı düşük: kapı 4 yine FAIL (daralma boyanan öğeyi kapsam dışına atmaz) |
| halka_r iki geçiş | ölçülen halka yarıçapı = halka_r x Rg (pay 1 px [başlangıç değeri]); 1087 girdisinde ve 5400 girdisinde halka_r 0,60 + kucuk_oran 1,8 ile (son ölçek x 1,8 = 0,96 [hesap]) iki geçiş de DUR vermez | ilk geçişi Rg hedefiyle yapan bozuk kopya aynı ayarda DUR verir (düzeltilen hatanın kanıtı); 5400 girdisinde halka_r 0,884 + kucuk_oran 1,8 gerçek girdi hatasıdır (1,41 > 1) |
| pafta | hücre sayısı, çok sayfa, etiket içeriği, tipik / en kötü ayrı | sert DUR veren seçeneğin hücresi "DUR + kod" (YK:47-50 kalıbı); eksik hücre FAIL |
| pafta hücresi = son görselin küçültülmüşü (5.1, üç halka) | örneklenen hücreler ayrı süreçte yeniden üretilir: PNG sha256 = OZET = paftaya giren dosya; hücre = dosyanın tek adım küçültülmüşü (birebir); OZET'teki tuval ve k değerleri bağımsız yeniden hesapla aynı | k'yi düşüren / küçük tuvalde çizip büyüten bozuk üretici kopyası: yeniden üretim sha'sı farklı ve k / tuval kontrolü FAIL; pafta üreticisine OZET'te olmayan dosya verilirse DUR |
| adım 2 = adım 1 (5.1) | saklanan görselden çıkarılan dosyaların kaynağı sha256 = OZET; yeniden üretimde sha256 = OZET | bir ayarı değişmiş yeniden üretim: sha farklı, DUR |
| en kötü set ön ölçümü (yol ii-b) | ön ölçüm değerleri = aynı setin tam çizimindeki OLCUM'un MASKE tabanlı değerleri (isim küçülme, yazı mm, çizgi mm, maske taşması, maske çakışması); çizim isteyen ölçümler etikette "ölçülmedi" | ölçümü tipik setten kopyalayan bozuk kopya: değerler farklı, FAIL; çizim isteyen bir ölçümü ön ölçümde dolduran bozuk kopya FAIL |
| bütçe sınırı (4.5 b) | istek süresi bütçenin altında: üretim; ölçüm yokken yalnız ölçüm koşusu | bütçeyi aşan istek: üretmeden DUR ve sığan en büyük sayı; aracın listeyi kendiliğinden kırptığı bozuk kopya FAIL |
| geri dönüş etiketi (3.3) | 'iki_yan' istenip dilim 3 yokken 'tek_satir' + OZET'te "geri dönüş" | etiketsiz geri dönüş FAIL |
| bilinen çakışma (B1) | B1 tabanı: altın binme ölçeri FAIL yazar, görsel VAR, etiket "bilinen çakışma" | küçük burçlar sembolden uzak ayar: ölçer PASS (ölçerin iki yönde çalıştığının kanıtı) |
| süre kaydı | alanlar tam, bitiş >= başlangıç | eksik alan |
| ay takvimi regresyonu | `git diff --stat` boş; ATT, AY_SHA kopyasında motorlu tam koşu (ephem ile), çıkış 0 | denetim betiği, ay takvimi klasöründe tek bayt değişmiş geçici kopyada FAIL vermeli |
| ortam kapısı | pillow 11.0.0 + raqm | sürüm dizesi / raqm bayrağı test içinde değiştirilmiş sahte ortam: DUR 'ortam' (AT:1389-1391 koşulu) |
| motor / KILIT kapısı | sabit sha'lı motor klasörü | bir dosyası eksik kopya; KILIT'te bir dalı değişmiş kopya (AT:688-702) |
| sembol biçimi | RGBA deneme sembolü | RGB, boş alfa, tam dolu alfa (ATT:223-258 kalıbı) |
| sembol rengi / kenar / kaynak sha (kapı 2) | değişmemiş üretim | son dosyada sembol pikseli 2 seviye değiştirilmiş; katman dosyası değişmiş (sha) |
| çerçeve tutarlılığı, 200 çekirdek piksel | temiz örnek ayar | 1 px kaydırılmış k kat çerçeve; çok küçük yazı (çekirdek < 200): DUR |
| tuval dışı, isim sığmıyor | temiz örnek ayar | sembolü tuval dışına iten ayar; çok uzun isim + dar kiriş: DUR |
| çıktı (boyut, RGB, sRGB) | temiz örnek ayar | yanlış boyutlu / RGBA / profilsiz dosya |
| ölçer kapılar: dE00, kontrast, yazım farkı, düz renk, yıldız, öğe sayısı, isim / metin genişliği | motorlu gerçek koşu (en az bir PASS) | ATT:548-680 t_kapi kalıbındaki bozulmuş sahte koşular (renk kaydırma, düşük kontrast zemin, kaydırılmış maske, düz renkli öğe, öğeye değen yıldız, eksik öğe, geniş satır): OLCUM'da FAIL, görsel VAR |
| tek modül | araç ve kapı aynı AT nesnesini görür | AT'nin başka adla ikinci kez yüklendiği durumda test FAIL |
| iş akışı kabuk adımları (Actions dilimi) | ATT:707-930 kalıbı, sahte rclone | yanlış onay, Re-run, ref main değil, boş değişken |

Zayıf test uyarısı: sahte veriyle kurulan kapı testleri (ATT:358 sahte_kosu kalıbı) yalnız kapı mantığını sınar; raporda
"sahte veri" diye yazılır, gerçek motorlu en az bir PASS koşusu ayrıca istenir.

## 9. Uygulama dilimleri ve sırası

Süreler [tahmin]; her dilim en çok 2 deneme, sonra DUR. Hiçbir dilim bu planın onayı ve ilgili soruların cevabı olmadan
başlamaz; sıra Serdar / Merkez kararıyla değişebilir.

| Dilim | İçerik | Bağlı soru | Dosyalar | Bağımsız inceleme noktası | Süre |
|---|---|---|---|---|---|
| 1 | Yuvarlak şekil; ürün girdisi ve AYAR doğrulaması; taban B1 ve B2; grup (sembol, halka, küçük burçlar; logo 'kucuk_arasi' soru 7 izin verirse); isimler 'tek_satir' (geri dönüş, 3.3); tek satır metin; mm ve uyarılar; sert / ölçer kapılar; grup ızgarası; tek sayfa pafta; OZET / OLCUM / SURE; ölçüm koşusu ve bütçe sınırı (4.5 b). Yalnız yerel, deneme sembolü, önbelleksiz. | 1, 5, 6, 7, 14 | tasarim_deneme.py, tasarim_kapi.py, test_tasarim_deneme.py, urun/DENEME_YUVARLAK_1087.json | Kod + testler bitince, ilk pafta Serdar'a gitmeden önce | 5 - 7 saat |
| 2 | Kalan ızgaralar (isim, metin, küçük burç, logo); tipik / en kötü setler; kombinasyonlar (kapı 2, yol K-a); çok anahtarlı ızgara ve çok sayfalı pafta; süreç yolu (5.1: i, ii ya da ii-b) | 8, 15, 16, 18 | aynı 3 dosya | Kombinasyon kapısı ve pafta kural testi | 4 - 6 saat |
| 3 | İsimlerin arasında logo: 'iki_yan' düzen, grup dışı logo yerleşimi ve kapısı; geri dönüş kalkar | 7, 19 | aynı 3 dosya | Grup dışı logo kapısı | 2 - 3 saat |
| 4 | Ornament birebir: bağımsız sembol boyu, isim merkezli küçük burç yeri; kapı 2 hedef değişikliği | 17 (yalnız "evet" ise) | aynı 3 dosya | Kapı 2 değişikliği (zorunlu) | 5 - 7 saat |
| 5 | Dikey (DENEME_DIKEY_5400) ve yatay şekil; büyük tuvalde önizleme + kesit, saklama / yeniden üretim | 15, 16 | aynı + urun/DENEME_DIKEY_5400.json | Şekil genellemesi | 3 - 4 saat |
| 6 | Motor katmanı önbelleği (7.3 madde 4); yalnız ölçüm gerek gösterirse | 13, 14 | aynı 3 dosya | Önbellek bayt eşitliği testi | 2 - 3 saat |
| 7 | Kütüphane (kayıt, kayıttan üretim); renk / doku setleri (3.5) | sonraki parça | sonraki parça | - | sonraki parça |
| 8 | Actions yolu: tasarim-deneme.yml, kabuk testleri, gerçek katmanla tek koşu, deneme sembolü farkı ölçümü (7.4) | 1, 12 | iş akışı + test | İş akışı main'e girmeden önce | 3 - 4 saat + 1 koşu |

Sıra gerekçesi: 1 tabandır ve süre ölçümünü verir (bütçe kuralı onsuz çalışmaz); 2 "çok seçenek" gereksinimini ve karar 3 -
4'ü besler; 3 iki tabanın emsalindeki logo yerini açar; 4 yalnız Serdar isterse; 5 ikinci şekli açar ve büyük tuval
gerilimini ölçer; 6 ölçüme bağlıdır; 8 yalnız koşu yeri sorusu Actions çıkarsa ya da renk / doku parçası gerçek katman
isteyince gerekir. 7.4 ölçümü erken istenirse dilim 8 öne alınabilir (Merkez kararı).

## 10. Açık sorular

Numaralar 1 - 13 önceki sürümdeki sorulardır (korundu); 14 - 19 bu turda eklendi. Her soru tek cümle + seçeneklerdir; olgu,
hesap ve atıf parantezdeki bölümdedir. Öneri yalnız 10.3'teki teknik sorularda yazılıdır; 10.1 ve 10.2'de öneri yoktur
(süreç için teknik değerlendirme 5.1'in sonundadır).

### 10.1 Serdar'ın açık onayı gereken (kural ya da izin)

1. Koşu yeri neresi olsun? (a) yerel + deneme sembolü; (b) Actions + gerçek katman; (c) yerleşim için (a), renk / doku ve
   son teyit için (b); (d) yerel + gerçek katman (Drive bağlayıcısıyla; denenmedi, ayrı okuma izni ister). (7.1, 7.4;
   kural gerilimi CM:98-99 ile CM:111)
6. Aşağıdaki kapı kapsamı ve sınıf değişikliklerinin her biri onaylanıyor mu (madde madde evet / hayır)?
   - (a) Takvime özel kapılar kapsam dışı: veri / evre, disk boşlukları, "altın dışı öğede altın yok", blok ortalaması,
     "ayar = varsayılan", mod tutarlılığı. (6.3)
   - (b) Kapı 10: boyut ürün baskı alanına, dpi etiketi ürün girdisinden hesaplanan değere bağlanır. (6.3)
   - (c) SINIF DEĞİŞİKLİĞİ, sıkılaştırma: çıktı kapısı (boyut, RGB, sRGB) takvim deneme modunda ölçerdi, araçta SERT. (6.4)
   - (d) Güvenli alan / yasak bölge taşması: ornament motorunda sertti, araçta ÖLÇER (ornament emsaline göre gevşetme;
     takvimde bu kapı yok). (6.4)
   - (e) Öğe çakışması: ornament motorunda sertti, araçta ÖLÇER (ornament emsaline göre gevşetme; takvim deneme modunda
     da ölçer). (6.4)
   - (f) Kapı 8 isim alt sınırı ay adı boyu yerine ürünün yazı alt sınırı olur; sayfa kenarı payı yerine ürün güvenli alanı
     ölçülür. (6.2, 6.3)
   - (g) "Grup - ay adı" boşluğu "grup - yazı" boşluğu olarak ölçülür; 12 px eşiğinin başka tuvaldeki karşılığı ölçümden
     sonra ayrıca sorulur. (6.2)
   - (h) AYAR tablosunda kucuk_v alt ucu 0,60 yerine 0,20. (3.3)
   - (i) Ornament yasak bölge kapısının üç parçası ürün parametresi olur; ışık taşması genişletmesi 0 alınır ve yerine
     görüntü farkı ölçümü konur (0 değeri ölçüm bölgesini daraltır). (6.2, 6.3)
   - (j) Yıldız kapısı küçük tuvalde FAIL yazdırabilir (olası; ölçülmedi): (j1) engel payı büyütülür; (j2) kapı payı tuvale
     oranlanır (gevşetme); (j3) ikisi de aynen kalır. Plan (j3) ile yazıldı. (6.2)
   - (k) Kombinasyonda (yol K-a) kapı 3, 4, 7, altın binme, yıldız ve taşma yalnız boyanan öğeleri ölçer (kapsam
     daralması) ve "çizilmeyen öğe son görselde yok" ölçümü eşiksiz ölçer olarak eklenir. (4.3, 6.4)
   - (l) Ornament motorunda sert olan kontrast, alfa farkı ve dE00 araçta ölçer kalır (takvim deneme moduyla aynı);
     ornament'e özgü IoU, leke, ton ve sabit boşluk kapıları araçta yoktur. (6.4)
12. Yerel çıktı Serdar'a nasıl gösterilsin? (a) Merkez'e pafta dosyası olarak iletim; (b) yalnız paftanın Drive TEMP'e
    yazılması için ayrı izin. (7.1)
14. Koşu başına süre bütçesi ne olsun? (a) tek değer (dakika); (b) yerel ve Actions için ayrı iki değer; (c) ay takvimi
    iş akışının bütçesi aynen (50 dk; AT:49). (4.5 b)
15. Süreç hangi yolla işlesin ve kararlar hangi sırayla verilsin? Süreç: (a) tek adım; (b) iki adım; (c) iki adım + en
    kötü örnek seti adım 1'de yalnız ön ölçümle. Sıra: (s1) yerleşim, sonra renk, sonra doku (seçenekler toplanır); (s2)
    birlikte (çarpılır); (s3) seçilen birkaç yerleşim için birlikte. (5.1, 4.5 e)
16. "Deneme görseli, son üründe çıkacak görselin küçültülmüşü olmalı; çıktıyı değiştiren kısayol yok" kuralı genel araçta
    da geçerli mi ve büyük tuvalde seçenek sayısı bütçeyi aşarsa hangisi öncelikli? (a) kural geçerli, seçenek sayısı
    bütçeye göre azalır; (b) kural geçerli, bütçe büyütülür ya da koşu bölünür; (c) eleme adımı için kural gevşetilir
    (plan bunu tasarlamadı). (5.1 "son ürün" sınırı dahil; 7.2)
18. Küçük burçsuz kombinasyon hangi yolla kurulsun? (a) K-a "çizilmedi": kapı 2 tanımı aynen, diğer kapıların kapsamı
    daralır (6 k); (b) K-b "küçük burçsuz grup": ek kod, kapı 2 tanımı değişir; (c) küçük burçsuz kombinasyon üretilmez.
    (4.3)

### 10.2 Serdar'ın görerek vereceği

2. Halka kalınlığı çarpanı ve çentik yumuşatma genel araçta açılsın mı? (a) kapalı: halka hep orantılı, araç yalnız
   işaretler; (b) açık: değer ürün başına Serdar'dan; (c) açık + üretici alt sınırı varsa sistematik dizi (1,5 / 2 / 2,5 /
   3 kat). (Olgular 3.4 ve bölüm 0 bulgu 3. Deneme girdisinde [hesap; eşleme varsayım]: halka_r 0,884 - 1,20 için sınıra
   ulaşmak 1,95 - 2,65 kat ister; halka_r 0,585'in altında 4 kat bile yetmez. Kod maliyeti yok: AT:113-116, 1075.)
4. Üretici alt sınırının altındaki yazı ve çizgi için başlangıç ve ölçüt ne olsun? Başlangıç: (a) emsal oranı kalır, araç
   yalnız işaretler; (b) "alt sınırı tam tutan en küçük boy" da başlangıç seçeneği olur. Yazı ölçütü: (y1) büyük harf
   yüksekliği; (y2) küçük harf yüksekliği. Çizgi ölçütü: (c1) en ince yer; (c2) 1. yüzdelik; (c3) gövde ortancası. (Araç
   hepsini ölçer; ölçüt ilk ölçümden sonra seçilir; bölüm 5.)
5. Yuvarlak şeklin başlangıç tabanı hangisi olsun? (a) B1 ornament çevrimi (bilinen çakışma); (b) B2 poster düzeni (isim
   ve metnin taşması beklenir); (c) ikisi de aday kalır, varsayılan yok; (d) önce ornament birebir dilimi (soru 17). B1'in
   emsali: (e1) YD yeni düzen çizgileri; (e2) O5 V5 düzeni. (3.3, 3.4, 4.1; YD:28-45, OM:272-273)
7. Logo genel araçta nasıl işlensin? Kesim: (a1) ay takvimindeki poster kesimi; (a2) ornament kesimi. Temizlik: (b1) ay
   takvimindeki gibi uygulanır; (b2) uygulanmaz. Yer: (c1) yalnız küçük burçların arası; (c2) isimlerin arası da (dilim
   3). (3.2; (a1) + (b1) + (c1) dışındaki her cevap ek kod demektir.)
11. Kazıma ürünlerinde önizleme nasıl olsun? (a) altın yolu ve motor zeminiyle kalır; (b) renk / doku parçasında "tek
    renk" önizleme ayrıca eklenir. (3.5)
17. Ornament düzeni birebir istenir mi? (a) evet (ek dilim, 5 - 7 saat [tahmin], kapı 2 hedefleri değişir); (b) hayır,
    B1'in farkları kabul; (c) B1 ve B2 görüldükten sonra karar. (3.4)

### 10.3 Teknik (öneri yazıldı)

3. Logo kaynağı dosyası hangisi olsun? (a) MG girdi/LOGO_1.png (ay takvimi kodunun kullandığı; AT:127-129, 1164); (b)
   başka bir kaynak. Teknik öneri: (a); Merkez isterse ornament koşularının kaynak klasöründeki kopyayla sha256
   karşılaştırır (bu oturum karşılaştırmadı).
8. En kötü örnek değerlerini (en uzun isim çifti, en uzun mesaj, en geniş tarih) kim verir? (a) Merkez verir, ürün
   girdisine yazılır; (b) kod sabit emsal kullanır (W:204-206). Teknik öneri: (a); kod değer uydurmaz. (4.4)
9. Deneme girdisinde güvenli alan ve yasak bölge nereden gelsin? (a) şablondan ölçülüp verilir; (b) ilk dilim güvenli
   yarıçap = tuval yarıçapının sabit bir oranı [varsayım] ile başlar. Teknik öneri: (a) gelene kadar (b), "varsayım"
   etiketiyle. (3.1)
10. Çift kapsamı bu parça için ne olsun? (a) yalnız CANCER_LIBRA; (b) başka çiftler de (4.5 a satır 9'daki maliyetle).
    Teknik öneri: (a). (4.5)
13. Altın çizim sırası ne olsun? (a) emsal sırası (yazılar önce); (b) "halka, küçük burçlar, logo, yazılar". Teknik
    öneri: (a); (b) ancak süre ölçümü gerek gösterirse ve iki sıranın 1:1 kesiti Serdar'a gösterildikten sonra. (7.3)
19. Logo boy birimi ne olsun? (a) ay takvimi birimi (poster logo boyu x grup ölçeği katı; AT:116, 1262); (b) isim büyük
    harfinin katı (ornament emsali O4:50; ek kod). Teknik öneri: (a); oran ölçüm olarak yazılır. (a)'nın sonucu: logo
    isimlerin arasındayken de boyu isim boyuna değil grup ölçeğine bağlı kalır. (3.2)

## Ek: bu planın sınırları

- Depodaki hiçbir betik çalıştırılmadı; [tahmin] ve [hesap] etiketli rakamlar ölçüm değildir. [kontrol ölçümü] etiketli
  rakamlar görev metninden alındı, bu oturumda yeniden ölçülmedi (yalnız aritmetiği yinelendi).
- Dayanak'taki Merkez kayıtları (1087 px, 25,4 mm, 1,5 mm, 0,2 mm, üretici sayfaları, ay takvimi koşu sonuçları) bu
  oturumda doğrulanmadı.
- ornek-tek-doku dalı (tek_doku.py, poster halka görseli) okunmadı; plan o dala dayanmıyor.
- İnceleme geçmişi: tur 1 planı (fdf9658) iki inceleme turundan geçti; ikinci turdaki iki yeni yüksek bulgu düzeltilip
  yeniden incelenmeden gönderilmişti. Bu düzeltme turunun inceleme kaydı aşağıdadır.

## İnceleme kaydı (düzeltme turu 2)

Tek bağımsız inceleme ajanı, iki tur (her turda işi yapmamış ayrı ajan; model Opus 5.5, effort High).

- 1. tur: 16 bulgu (1 yüksek, 6 orta, 9 düşük). Hepsi plana işlendi. Yüksek bulgu: kombinasyon yolu K-a'da çizilmeyen
  öğenin kapı 2 dışındaki kapılara takılması ve sert ek koşulun B1'de yanlış FAIL vermesi (4.3 yeniden yazıldı).
- 2. tur: 10 bulgu (1 YENİ yüksek, 2 orta, 7 düşük). Görev kuralı gereği (CM:218) DÜZELTİLMEDİ; plan bu hâliyle
  gönderildi. Bulgular, olduğu gibi:

| No | Önem | Yer | Bulgu | İnceleyenin önerdiği düzeltme |
|---|---|---|---|---|
| 1 | YÜKSEK | 4.3 K-a tablosu, 6.1 "şekil değişmez" satırı, soru 6 k ve 18 a | Kapı 2'nin sembol bölümü deneme modunda başka öğenin ÖRTTÜĞÜ sembol piksellerini renk ve kenar karşılaştırmasından çıkarır (ATK:415-423, 427). K-a'da çizilmeyen küçük burçların geometri maskeleri de bu hesaba girer; hiçbir şeyi örtmedikleri hâlde altlarındaki görünür sembol pikselleri sert kapıdan düşer. B1'de bu tam çakışma bölgesidir. Bu, ölçüm bölgesini daraltan bir gevşetmedir (CM:211-212) ve plan "kapı 2 tanımı değişmez" diyor. | K-a'da "örtülen" yalnız BOYANAN öğelerden kurulur; bu satır 4.3, 6.1 ve 6.4'e girer; soru 18 a yeniden yazılır; test: B1 + K-a'da sembolün çizilmeyen bölgedeki rengi bozulmuş kopya kapı 2'den FAIL almalı. |
| 2 | ORTA | 6.4 ikinci tablo, soru 6 l | "Ornament motorunda sert olanların tam listesi" eksik: yeni düzen kipinde ornament kendi düzen kapılarını da sert ekliyor (OM:795-797; YD:292-307), boşluk 20 / 20 / 20 kapısı bu kipte çıkıyor (OM:796). B1'in bilinen çakışmasını ornament'te önleyen sert kapı (sembol alt sınırı, YD:294) listede yok. | Bu kapılar tabloya ve soru 6 l'ye eklenir. |
| 3 | ORTA | 5.1 kural kontrolü, bölüm 8 "pafta hücresi" satırı | Üç halka hâlâ zayıf: 2. halka aynı fonksiyonu yeniden koşar (yalnız belirlenimcilik); 3. halka kodun kendi yazdığı k ve tuval değerini karşılaştırır. Tek üretim fonksiyonunun içi bozulursa test FAIL vermez (CM:209). | 3. halka çalışma anındaki gerçek değeri ölçer: test AT çağrılarını sarar, gerçek k kat çizim boyutunu ve PNG boyutunu kaydeder, bağımsız k ile karşılaştırır; mutasyon tek fonksiyonun içinde yapılır. |
| 4 | DÜŞÜK | 4.3 K-a tablosu | Eksik satırlar: grup - yazı boşluğu (ATK:505-512, 521-529), kenar / altın birleşimi (ATK:513-515, 539-541), gerçek ölçü mm uyarısı ve "alt sınır altı öğe sayısı" da çizilmeyen öğeyi sayar. | "Yalnız boyanan öğeler" kapsamına ve soru 6 k'ya eklenir. |
| 5 | DÜŞÜK | 5.1 yol (ii-b) | Çizgi kalınlığının ortancası k kat alfadan ölçülür (AT:884), 1x maskeden çıkmaz (alfa yeter, boyama gerekmez). "Adım 1'de görünmeyen sert DUR" listesinde k kat > kaynak ve çentik bandı yanlış (yalnız gruba bağlı, tipik sette zaten görünür); eksikler: kapı 2 sembol renk / kenar, çıktı kapısı; isim 8 denemede sığmama (AT:572-573) ön ölçümde yakalanır ama listede yok. | Liste düzeltilir. |
| 6 | DÜŞÜK | 4.5 c satır 1, 4.5 e | Yinelenen hücre sayımı: logo ızgarası taban hücresini içermez; 35 / 101 / 199 yerine 36 / 102 / 200. (e)'deki 41, tabanı ızgaralarda ikinci kez sayıyor (örnek). Süreler ve diğer sayılar doğru. | Sayılar düzeltilir. |
| 7 | DÜŞÜK | 1.2 grup_kapisi satırı, 6.1 | Sentetik META yolu ilkesel olarak çalışır; ama "grup merkezi = ayardaki nokta" koşulu ancak sentetik merkez üretimden BAĞIMSIZ hesaplanırsa FAIL verebilir. Emsal satırlar (ATT:1526-1528) yalnız disk merkezini kuruyor; hedef yarıçap formülü o satırlarda yok. | Kaynak yazılır; bölüm 8'e bu koşul için bilinen FAIL eklenir. |
| 8 | DÜŞÜK | 3.5 tablosu | "Ana sembol katmanı seti: harita ve motor katmanları değişmez" yalnız katmanın alfası ve yan json'u aynıysa doğru (AT:1215, 1217). Palet ya da KILIT seti motor sha'sını değiştirir: 6.1'deki "sabit sha'lar" kapısı ve KILIT dal kontrolü (AT:697-702) etkilenir. | Koşul ve kapı etkisi arayüze yazılır. |
| 9 | DÜŞÜK | Bölüm 6 girişi, 6.4, 4.6, soru 17 | "Ayrılmaların hepsi 6.4'te" doğru değil (soru 6 a, b, f, g, i, j 6.2 ve 6.3'te). 6.4'te eksik: kapı 2 alt koşullarının karşılığı, isim arası logo için yeni sert kapı. Soru 17 kapı 2 tanım değişikliği içerdiği hâlde "görerek" başlığında ve değişen kapı satırları adıyla sorulmuyor. | 6.4 tamamlanır; soru 17'nin kapı kısmı 10.1'e de yazılır. |
| 10 | DÜŞÜK | Bölüm 8 ile 3.3 | 3.3 halka kalınlığı 1,0 dışını, 'yumusak' çentiği ve logoyu soru 2 / 7'ye kadar girdi hatası sayıyor; önbellek ve "tek öğe değişir" testleri ile 4.2 logo ızgarası bu kilidi anmadan bu değerleri kullanıyor. | Testlerin kilidi nasıl aştığı ya da hangi soruya bağlı olduğu yazılır. |

2. turda doğrulananlar (inceleyen beyanı): 1. turun 4, 5, 6, 7, 8, 9, 11, 12, 15, 16 numaralı düzeltmeleri; hesaplar (halka
px / mm, kat aralıkları, 5400 üst ucu, seçenek sayıları 594 / 53 / 1312, bütün süre aralıkları); gizlilik; görsel tercih
önerisi, varsayılan taban ya da halka kararı, sıralama ve eşik önerisi olmadığı. Atıf sayımı (1. tur): AT / ATK / ATT için
338 tekil atıf, 333 doğru, 2 sınırda, 3 yanlış; yanlışlar ve sınırdakiler 1. turdan sonra düzeltildi.
