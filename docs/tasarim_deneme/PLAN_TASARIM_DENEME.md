# PLAN: TASARIM DENEME ARACI (parça 1: yerleşim)

Aşama 1 (yalnız plan). Kod, görsel, Actions koşusu, Etsy okuma / yazma YOK. Bu plan Merkez'de kodla kontrol edilip Serdar
onaylayınca ayrı görevle kodlanır. Plan hangi seçeneğin güzel olduğunu söylemez; araç da seçenekleri puanlamaz, sıralamaz,
"önerilen" diye işaretlemez (Serdar 10 ve 11 Kas).

## 0. Ref'ler, kısaltmalar, etiketler

| Kısaltma | Dosya | Ref |
|---|---|---|
| AT | scripts/ay_takvim/ay_takvim_ornek.py (1561 satır) | main f89f55d |
| ATK | scripts/ay_takvim/ay_takvim_kapi.py (620 satır) | main f89f55d |
| ATT | scripts/ay_takvim/test_ay_takvim.py (1535 satır) | main f89f55d |
| W | .github/workflows/ay-takvim-ornek.yml (273 satır) | main f89f55d |
| CM | CLAUDE.md | main f89f55d |
| YK | scripts/kapak78/yd_kontak.py | main f89f55d |
| OM | scripts/printful/ornament_motor.py | ornament-printful-katalog c950151 |
| O1, O2, O3, O4, O5 | scripts/printful/ornament_ornek.py, _ornek2, _ornek3, _ornek4, _ornek5 | aynı, c950151 |
| YD | scripts/printful/yeni_duzen.py | aynı, c950151 |
| YDT | scripts/printful/yeni_duzen_yerel_test.py | aynı, c950151 |
| MG | motor_gpt/ (golge_motor.py, olustur_alfa_sablon.py, cember.json, girdi/ ...) | siparis-gpt 6da763a |

- main HEAD (bu oturumda `git fetch` sonrası): f89f55dc76b48d12fa74a44be7252f019988b336. Görev metnindeki f89f55d ile AYNI;
  scripts/ay_takvim ve .github/workflows için fark yok, atıflar bu ref'te okundu.
- Okuma yöntemi: yalnız `git show <ref>:<dosya>` ve metin okuma. Depodaki hiçbir betik çalıştırılmadı (yalnız kabın
  ortamını görmek için tek satır paket içe alma denemesi ve aritmetik). Drive, Actions çıktısı, sipariş verisi okunmadı.
- Rakam etiketleri: [kod] = dosyada yazılı değer; [hesap] = koddaki değerlerden bu planda yapılan aritmetik; [kayıt] = AT
  başlığındaki yerel ölçüm notu (Merkez doğrulamadı); [tahmin] = ölçülmedi, akıl yürütme; [varsayım] = doğrulanmamış girdi;
  [ölçülmedi]. "Başlangıç değeri" yazan her aralık, adım ve sınır [tahmin] sınıfındadır: kaynağı yoktur, yalnız yanlış girişi
  yakalamak ya da ilk koşuyu sınırlamak içindir, ilk ölçümle ve Merkez / Serdar kararıyla kesinleşir.

En önemli üç bulgu (ayrıntı ilgili bölümde):

1. Altın yolu, sembol grubu, ayar sözlüğü ve doğrulama ay takvimi kodundan DEĞİŞTİRİLMEDEN içe alınabilir; takvime özel
   olan yalnız `uret` gövdesi, takvim geometrisi ve kapı betiğinin tek gövdeli `kapi_olc` fonksiyonudur (bölüm 1). Ornament
   örnek modülleri içe alınabiliyor ama 954 px tuvale ve Printful şablon sabitlerine modül düzeyinde bağlı, üstelik başka
   bir altın yolu (tek_doku) kullanıyor: yuvarlak şekil için ornament'ten kod değil, ölçü ve kapı TANIMLARI alınır.
2. LOGO_1.png depoda VAR: MG girdi/LOGO_1.png (6da763a; YDT:57-60 aynı dosyayı bu ref'ten alıyor). Dayanak 7g'deki
   "depoda değil" düzeltilir. Logo için Drive gerekmez. Drive'daki kopyayla bayt eşitliği [ölçülmedi].
3. Deneme girdisinde (1087 px, 25,4 mm, eşleme [varsayım]) onaylı öğeler üretici alt sınırının altında kalıyor [hesap;
   ek varsayım: güvenli yarıçap ve halka yarıçapı tuval yarıçapı 543,5 px'i aşamaz]: poster halkası orantılı küçülünce en
   çok 3,7 px = 0,085 mm (sınır 0,2 mm); ornament yerleşimi aynı oranla taşınınca isim büyük harfi en çok 40 px = 0,94 mm
   (sınır 1,5 mm). Araç bunu gizlemez, işaretler; halka kalınlığı ve yazı boyu soruları
   bölüm 10'da.

## 1. Taban teyidi ve seçimi

### 1.1 Dayanak 7 maddelerinin kodla teyidi

| Madde | Sonuç | Kanıt / düzeltme |
|---|---|---|
| 7a deneme düzeni | TEYİT | AYAR açıklaması AT:43-49; AYAR_ANAHTAR AT:113-114; AYAR_ARALIK AT:115-117; AYAR_SERBEST AT:118; DENEME_AZAMI AT:119; ayar_varsayilan AT:205; ayar_dogrula AT:213; ayar_listesi AT:263; ayar_kur AT:1148. İş akışı mod deneme W:6-12, W:22-23, W:46-50. Sert / ölçen ayrımı AT:45-47, ATK:40-44. |
| 7b OM içe alınamıyor | TEYİT, satır düzeltmesi | OM tek main(): OM:106-837 (837 son `return`; de00 OM:840 modül düzeyinde). Taşınan fonksiyonlar AT:6-17: Motor AT:671, golgele_oge AT:705, harita_kur AT:779, oge_katman AT:801, metin_alfa AT:518, metin_alfa_k AT:532, renk_uyum AT:604. Örnek modülleri içe alınıyor: O5:29, O4:31, O3:31-32. |
| 7c sembol grubu | TEYİT | grup_kaynak AT:1017, grup_kur AT:1056. KUCUK_U yalnız CANCER_LIBRA AT:107; başka çiftte DUR 'grup_cift' AT:1023-1024. Kapı tarafında bağımsız kopya ATK:178-179. |
| 7d diğer parçalar | TEYİT, bir ek | isim_dogrula AT:162, metin_dogrula AT:179, isim_sigdir AT:544, cizim_katsayisi AT:563, altin_ogeler AT:832, zemin_radyal AT:867, zemin_yildiz AT:895, sembol_yukle AT:954, rgba_olcek AT:993, sembol_yerlestir AT:1003. mm hesabı yalnız halka için ve DPI sabitiyle: AT:76, AT:1108. Kapılar: kontrast_olc ATK:95, grup_kapisi ATK:182, kapi_olc ATK:273. Ek: tarih için ayrı öğe YOK; tarih 'satirlar' içinde serbest metin (W:206). |
| 7e takvime özel | TEYİT, ekler | Tuval AT:74-76; AYLAR, BASLIK AT:78-79; ay_verisi AT:296; veri_kapisi AT:323; yerlesim_kur AT:337; dikey_yerlesim AT:487; uret AT:1198-1469 (tek fonksiyon). Ek: tuval sabitleri W, H, S şu fonksiyonların İÇİNDE de kullanılıyor: isim_sigdir AT:547 (varsayılan sınır), yerlesim_bul AT:475, sembol_yukle AT:986, _kesisim AT:1192, disk_ciz AT:1133-1134, grup_kur AT:1108 (DPI). Kapı tarafında grup_kapisi ATK:192 (U.S) ve ATK:218 (META disk merkezi). |
| 7f ornament'te olup takvimde olmayan | TEYİT, iki ek | Logo: logo_kaynak O4:156, logo_olc O4:176. Yuvarlak alan: O4:34-42; yasak_m O4:219; kapi O4:239; yerlesim_A O4:282, yerlesim_B O4:303. Yazı bloğu: yazi_blogu O3:208, alt_sinir O3:274. mm çıktısı: O1:299-301, O4:550-557, O5:765-767. Ek 1: bu fonksiyonlar modül sabitlerine bağlı (N = 954 O1:34; MM = 25,4 / 300 O1:42; CX, CY O4:34; O4, O3'ün C sabitini içe alırken DEĞİŞTİRİYOR O4:35; YASAK ve GLOW_K main içinde atanıyor O4:475-477, O5:518-520). Ek 2: O1-O5 altın yolu tek_doku modeli (O1:109-127; tek_doku.py kaynak klasöründen O4:478-479), OM / AT'nin motor yolu değil. |
| 7g bağımlılıklar | KISMEN DÜZELTME | Motor sabit sha: W:26, W:68; AT:6-7. Motor ortam değişkenlerini değiştiriyor AT:680, ayrıca sys.path'e ekliyor AT:689-690. golge_motor ortam değişkenlerini içe alınırken ve her çağrıda okuyor (MG golge_motor.py:3-7, 227-229): süreç başına tek motor, tek KILIT. Öğeden öğeye taşan gizli durum yok (egim_tup öznitelikleri her karoda sıfırlanıyor AT:727, 742-747). DÜZELTME: LOGO_1.png depoda var (MG girdi/LOGO_1.png, 6da763a; poster hattı aynı dosyadan kesiyor MG olustur_alfa_sablon.py:69; YDT:57-60). O4:496 ve O5:532 dosyayı kaynak klasöründen okuyor; o klasörün dosyası ile depodaki dosyanın bayt eşitliği [ölçülmedi]. Ortam W:95-97; CM:93-97. |
| 7h kaynak ve süre | TEYİT, bir not | Ana katman Drive'dan W:124-136. Yerel deneme sembolü deneme_komut AT:1503-1521. Süre notu AT:48-49 [kayıt]. Sabit sha kalıbı W:26-27, W:67-79. Not: bu Code oturumunda Drive bağlayıcı araçları listeli (kullanılmadı, denenmedi); "Code ortamı Drive okuyamaz" bu oturum için doğrulanmadı (bölüm 10 soru 1). Bu oturumun kabında cv2 kurulu değil (ölçüm: içe alma hatası), Pillow 12.3.0 (iş akışı 11.0.0), Python 3.13.18, 4 çekirdek. |
| 7i pafta emsali | TEYİT | pafta() YK:26-53: (etiket, yol) listesi, hücre + etiket bandı, eksik dosya hücresi kırmızı. Yalnız Pillow (YK:12). |

### 1.2 Fonksiyon tablosu

Sütun "Kullanım": A = aynen (içe alınır, satır değişmez); P = parametre ister (içe alınır, yeni kod eksik parametreyi verir ya da
sarmalar); Ö = ürüne özel kalır (içe alınmaz); T = tanım alınır (kod değil; yeni kodda genel yazılır, eşdeğerlik testi kaynakla).

| Fonksiyon / blok | Yer | Kullanım | Neden |
|---|---|---|---|
| Dur, log, bildir, sha | AT:140-158 | A | Genel. Çıkış kodu düzeni (3 girdi, 4 DUR, 2 çöküş) AT:51 korunur. |
| isim_dogrula, metin_dogrula, cift_dogrula | AT:162, 179, 197 | A | Tuvalden bağımsız; sınırlar METIN_SATIR_AZAMI, METIN_KARAKTER_AZAMI AT:137. |
| ayar_dogrula, ayar_listesi | AT:213, 263 | T | Doğrulama kalıbı (bilinmeyen anahtar, aralık, tür, yinelenen anahtar, ham girdi basmama) genel; ANAHTAR ve ARALIK tabloları takvime bağlı (AT:113-118, 225-230). Yeni araçta aynı kalıp kendi tablosuyla; isim ve satır kontrolü AT fonksiyonlarını çağırır. |
| _font, _punto, metin_alfa, metin_alfa_k | AT:503-541 | A | Tuvalden bağımsız (cap px girdisi). |
| isim_sigdir | AT:544-560 | P | `sinir`, `cap0`, `cap_alt`, `yumusak` parametre; varsayılan sınır W'ye bağlı (AT:547). TEK metnin mürekkep kutusunu ölçer (AT:550-552): 'tek_satir' düzende aynen (sınır = o satırın kiriş genişliği). 'iki_yan' düzende satır = isim1 + boşluk + logo + boşluk + isim2 (O3:213-226); genişlik hesabı yeni yazılır, küçülme kuralı aynı. Dikkat: yumusak=True iken de 8 denemede sığmazsa 'isim_sigmadi' DUR (AT:558-559); bu sert kalır (6.1). |
| cizim_katsayisi | AT:563 | A | POSTER_CAP 298 (AT:85) motor sabiti. |
| kutu, labf, de00, renk_uyum, yari_kal | AT:568-626 | A | Tuvalden bağımsız. renk_uyum < 200 çekirdek piksel DUR (AT:608-609). |
| boya | AT:629-667 | A | Herhangi tuval (AT:630). |
| Motor (init, golgele_oge, gorunen, poster_ana, harita_kur, oge_katman) | AT:671-829 | A | Tuvalden bağımsız. Yan etki: ortam + sys.path (AT:680, 689-690). |
| altin_ogeler | AT:832-863 | A | Yazı ve grup öğeleri aynı giriş. Tek rng, tohum 11, öğe SIRASIYLA (AT:840): sıra çıktıyı (gren) etkiler; bölüm 7.3. Grup öğesinde kaynak uint8 beklenir (AT:848). |
| zemin_radyal, zemin_yildiz, zemin_8bit | AT:867-950 | A | Tuval boyu, ölçek, merkez parametre. |
| sembol_yukle | AT:954-990 | P | Biçim kapısı genel; AT:986-989 takvimin spiral ölçeğini hesaplayıp > 1 ise DUR veriyor (kaynak çevre yarıçapı < 479,7 px [hesap: 0,78 x 205 x 3] olursa yanlış DUR). İlk dilimde aynen çağrılır, bu koşul OLCUM'a yazılır. |
| rgba_olcek | AT:993 | A | |
| sembol_yerlestir | AT:1003 | A | Grupsuz kombinasyon (ana sembol tek başına) için. |
| grup_kaynak, _dis_noktalar, grup_kur | AT:1017-1111 | P | Geometri `hedef_r` ile tuvalden bağımsız. bilgi['halka_kalinlik_mm'] DPI 300 ile (AT:1108): yeni araç bu alanı KULLANMAZ, mm'yi ürün girdisinden kendi hesaplar. Yalnız CANCER_LIBRA (AT:107). ÖNEMLİ: grubun ölçeği küçük burçların yerine ve boyuna bağlı (çevre dairesi tüm öğelerden AT:1080-1087, ölçek AT:1088, ana sembol ve halka bu ölçekle AT:1091, 1099); küçük burç ayarı değişince ana sembol ve halka da yeniden boyutlanır. Küçük burçsuz kurulum parametresi yok (AT:1032). Sonuçları: 3.3 (halka_r), 4.2, 4.3. |
| ayar_kur, uret, ayar_komut, sembol_komut, main | AT:1148-1552 | Ö | Takvim akışı. Deneme sembolü komutu deneme_komut (AT:1503) yerelde aynen ÇAĞRILIR. |
| ay_verisi ... dikey_yerlesim, disk_ciz, duz_yazi, _kesisim | AT:296-499, 1115-1195 | Ö | Takvim geometrisi. _kesisim 6 satır, W / H'ye bağlı: yeni kodda parametreli yazılır. |
| ESIK, kontrast, kontrast_olc, yatay_yayilim, cember_uydur | ATK:64-174 | A | Tuvalden bağımsız. Bant 6-12 px sabit (ATK:102-103), emsal O5:421-438 (954 px tuval). |
| grup_kapisi | ATK:182-270 | P | hedef_r'yi U.S ve 'sembol_alan' ile kuruyor (ATK:192), META 'disk' okuyor (ATK:218). Yeni kapı aynı iki kanıtı (yeniden kurulum + bağımsız ölçüm) kendi META'sıyla kurar; içerideki ölçüm yardımcıları aynen çağrılır. Eşdeğerlik testi: takvim META'sıyla iki kapı aynı sayıları vermeli. |
| evre_olc, kapi_olc, ozet_yaz | ATK:117, 273, 533 | Ö | Tek gövde; evre, disk, 12 ay adı sayımı içinde. |
| logo_kaynak, sirt_genislik, delik_say, logo_olc | O4:156-198 | T | Saf fonksiyonlar ama O4'ü içe almak O3, O2, O1'i ve modül sabitlerini de yükler. Yeni kodda aynı satırlar, ATT kalıbıyla (kaynak dosyadan çıkar, aynı girdiyle karşılaştır; ATT:11-12, 39-46) eşdeğerlik testi. |
| yasak_m, kapi, goruntu_yasak | O4:219-270, 425-437 | T | 954 sabitlerine bağlı. Ürün girdisinden okuyan genel karşılığı; 954 sabitleri verilince O4 ile aynı piksel sayısı (test). |
| yazi_blogu, alt_sinir, yerlesim_A / B, yerlesim_V5, yeni_yerlesim | O3:208, 274; O4:282, 303; O5:374; YD | T | Bunlar "sığan en büyüğü ara" çözücüleri (ör. O4:289-299), ayar alan yerleşim değil. Araçta yer ve boy AYAR'dan gelir, arama yok. Onaylı sonuç değerleri kütüphane başlangıç kaydına sayı olarak taşınır (bölüm 3.4). |
| mm çıktısı | O1:299-301, O4:550-557 | T | Kalıp: kutu px x MM. Yeni araçta MM ürün girdisinden. |
| pafta | YK:26-53 | T | Dosya adı ve CSV akışına bağlı değil ama hücre oranı 4:3 sabit (YK:28). Yeni araçta kare / dikey hücre gerekir; aynı düzen yeniden yazılır. |

### 1.3 Sonuç: yuvarlak şekil için hangi parça hangi tabandan

- Ay takvimi kodundan (içe alma): doğrulama yardımcıları, yazı çizimi, altın yolu (Motor, altin_ogeler, renk_uyum, boya),
  zemin, sembol yükleme, sembol grubu (grup_kur), ölçüm yardımcıları (kontrast_olc, cember_uydur, yari_kal). Neden: altın
  yolunun içe alınabilen TEK kopyası burada (OM tek main), her taşınan adımın kaynakla eşdeğerlik testi var (ATT:11-12).
- Ornament'ten (tanım ve sayı; kod değil): yuvarlak güvenli alan / yasak bölge kapısı tanımı, logo kaynağı kesimi ve logo
  ölçümü, öğe başına mm çıktısı, onaylı yuvarlak yerleşimin sayıları. Neden: modüller 954 tuvale ve tek_doku yoluna bağlı.
- Yeni yazılacak (hiçbir tabanda yok): ürün girdisi şeması, göreli birimli AYAR, yuvarlak / dikey yerleşim kurucu (ayarla,
  aramasız), seçenek üreteci, mm uyarısı, pafta, kayıt arayüzü, süre kaydı.

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
| Nasıl | AT ve ATK, belirli bir main sha'sından ayrı klasöre alınır (Actions: W:67-70 kalıbıyla 4. checkout; yerel: `git archive <sha> scripts/ay_takvim`), importlib ile dosya yolundan yüklenir (emsal O3:31). | scripts/ortak_altin/ gibi yeni modül; AT'deki fonksiyonlar oraya taşınır, AT içe alır. |
| Ay takvimi dosyaları | DEĞİŞMEZ | DEĞİŞİR (AT, ATK, ATT, W'nin sparse-checkout satırı W:64-66) |
| AY TAKVİMİ oturumuyla çakışma | Yok: yeni araç sabit sha'yı okur; o oturum main'i değiştirse de etkilenmez. | Var: aynı dosyalara iki oturum dokunur (CM "Aynı koda aynı anda tek oturum dokunur" kuralı). Bugün YASAK (görev: dokunulmaz). |
| Ayar sözlüğü değişimi | Yeni aracın AYAR'ı kendi tablosudur; AT'den yalnız fonksiyon alır. AT sha'sı yükseltilirken "yüzey testi" (2.3) farkı gösterir. | Ortak modül sürümü ile takvim birlikte değişir; her değişiklikte iki ürünün regresyonu gerekir. |
| Ay takvimi çıktısının değişmediğinin kanıtı | `git diff --stat <main> -- scripts/ay_takvim .github/workflows/ay-takvim-ornek.yml` boş; ek kanıt gerekmez. | ATT tamamı + 4 örneğin bayt eşitliği (aynı ortamda eski / yeni kodla PNG sha256) gerekir; bu bir Actions koşusu ya da uzun yerel koşu demektir. |
| Artı | Sıfır risk, bugün başlanabilir, emsali var (W, ATT). | Tek kaynak; uzun vadede iki kopya ayrışmaz. |
| Eksi | Bir sha'ya bağlı "anlık görüntü"; AT'deki sonraki düzeltme elle sha yükseltilerek alınır. Takvime özel yan etkiler (sembol_yukle AT:986-989) sarmalanır. | Çakışma, daha büyük inceleme yüzeyi, ay takvimi yeniden doğrulaması. |

Teknik öneri: şimdi (i). (ii), AY TAKVİMİ oturumu kapanıp ay takvimi kararları kesinleşince ayrı karar olarak ele alınır;
o güne kadar yeni aracın AT'den kullandığı yüzey tek listede tutulur (2.3), böylece (ii)'ye geçişte taşınacak fonksiyonlar
bellidir. Gerekçe: görev sınırı (dokunulmaz dosyalar), ay takvimi çıktısı için kanıt maliyetinin sıfır olması, emsal kalıp.

### 2.3 İçe alma kuralları (seçenek i)

- Sabitler dosya başında: AY_SHA (ilk dilimde f89f55d; AY TAKVİMİ oturumunun bugünkü değişikliği main'e girdikten ve
  Merkez doğruladıktan sonra yükseltilir), MOTOR_SHA 6da763a ve ORNAMENT_SHA c950151 (W:26-27 ile aynı değerler).
- Yüklenen modülün sabiti DEĞİŞTİRİLMEZ (O4:35 kalıbı kullanılmaz); W, H, S'ye bağlı fonksiyonlar çağrılmaz ya da
  parametresi açıkça verilir (tablo 1.2).
- Yüzey testi: kullanılan her AT / ATK adının var olduğu ve imzasının beklenen olduğu (inspect.signature) + AT / ATK dosya
  sha256'sının sabitle aynı olduğu test edilir (emsal ATT:39-46 KAYNAK_SHA). Sha yükseltmesi bu testi bilerek kırar;
  yükselten, farkı okuyup sabitleri günceller.
- Yükleme sırası: ATK, AT'yi normal ad aramasıyla alıyor (ATK:59-60 `sys.path.insert` + `import ay_takvim_ornek as U`).
  AT başka adla dosya yolundan yüklenirse İKİ ayrı AT modülü oluşur (iki ayrı Dur sınıfı; aracın `except` bloğu ATK'dan
  geleni yakalamaz; test mutasyonları ATK'nın gördüğü modüle işlemez). Kural: sabit sha klasörü sys.path'in başına
  eklenir ve iki dosya da ATT gibi normal `import` ile alınır (ATT:33-35); araç AT'ye yalnız bu tek modül nesnesinden
  erişir. Test: `tasarim_kapi`'nin gördüğü U ile aracın gördüğü AT aynı nesne.
- İçe alma yan etkileri: AT modül düzeyinde cv2, numpy, PIL ister (AT:66-68), Image.MAX_IMAGE_PIXELS ve T0 atar
  (AT:70-71); ATK sys.path'i kalıcı değiştirir ve aynı PIL ayarını yapar (ATK:59, 62). ephem yalnız ay_verisi ve uret
  içinde yükleniyor (AT:299, 1460): araç için gerekmez, ay takvimi regresyon testi (ATT) için gerekir (ATT:9).

### 2.4 Yeni iş akışı

Actions yolu seçilirse yeni dosya gerekir (W dokunulmaz; workflow_dispatch yalnız main'deki dosyada çalışır, CM:11).
W'den alınacak adımlar (yalnız satır numarası; Drive klasör kimliği plana kopyalanmadı): onay / deneme 1 / ref main kapısı
W:38-58; checkout'lar W:59-70 + ay takvimi için dördüncüsü; sha doğrulaması W:71-79; Python W:80-82; sipariş koşusu
kontrolü W:83-90; paketler W:91-97 (sürümler aynı; ephem yalnız ATT regresyonu koşulacaksa); ayar doğrulama (ortam değişkeninden) W:98-108; rclone
W:109-123; sembol katmanı W:124-136; Drive'a yazma W:240-262; temizlik W:271-273. Kabuk adımları ATT:695 ve devamındaki
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
| ana sembol | sabit | katman PNG + yan json (Drive katmanı ya da yerel deneme sembolü AT:1503) | yok: yalnız eş oranlı küçültme (AT:20, 1091) |
| halka | sabit | MG alfa_ogeler.npz 'cember' (AT:1026-1029) | 'cember' |
| küçük burç 1, 2 | değişebilir (var / yok) | MG girdi/KUCUK_1-2.png + kutular (AT:98-103, 1032-1044) | 'kucuk1', 'kucuk2' |
| logo | değişebilir | MG girdi/LOGO_1.png. İki ayrı kesim emsali var: ornament sağ yarı + eşik 0,1 (O4:156-161); poster sabit kutu (MG olustur_alfa_sablon.py:69). Ornament motoru ve poster logoyu ayrıca alfa temizliğinden geçiriyor (OM:430-433; MG olustur_alfa_sablon.py). | grup yolu ('kaynak' alanlı öğe AT:844-848; kaynak uint8'e çevrilir). Kesim, temizlik ve motor adı: bölüm 10 soru 7. |
| isim 1, isim 2 | değişebilir | girdi (örnek isim); Cinzel wght 500 (AT:1260) | 'yazi' |
| mesaj ya da tarih | değişebilir | girdi (örnek metin); EB Garamond Italic, ref 'T' (AT:1268) | 'yazi' |

Çift bu parçada CANCER_LIBRA (AT:107, 111). Altın çizim sırası sabit ve OZET'e yazılır (bölüm 7.3).

### 3.3 AYAR sözlüğü

Mevcut anahtarların sınıflaması (AT:113-118):

| Anahtar | Sınıf | Not |
|---|---|---|
| grup_merkez, kucuk_u, kucuk_v, kucuk_oran | genel, aynen | Anlam AT:95, 115, 118; grup_kur'a doğrudan geçer (AT:1056). kucuk_u yalnız SİMETRİK sayı (-u / +u, AT:1030) ya da 'poster'; birim halka yarıçapı (Rg değil). |
| grup_oran, sembol_alan | genel, birim değişir | Çarpımları hedef yarıçap (AT:1231). Yeni araçta tek anahtar grup_r (Rg oranı). |
| isim_cap, metin_cap | genel, birim değişir | Takvimde 5400 tuval pikseli (AT:117); yeni araçta Rg oranı. |
| isim1, isim2, satirlar | genel, aynen | Doğrulama AT:249-259. |
| yerlesim | takvime özel | halkalar / girdap / rozet (AT:112). Yeni araçta 'duzen' ayrı anahtar. |
| ay_adi_cap, girdap_ad_uzaklik, disk_katsayi, baslik_cap | takvime özel | Alınmaz. |

Yeni aracın AYAR'ı (uzunluklar yerleşim biriminde: yuvarlakta Rg; böylece kayıt aynı şekildeki başka ürüne taşınır.
İstisna: kucuk_u ve kucuk_v halka yarıçapı birimindedir, AT:1030-1031 ile aynı).
Aralıklar ve varsayılanlar BAŞLANGIÇ DEĞERİDİR (yalnız yanlış girişi yakalar; tasarım kararı değil, AT:110 kuralı).

| Anahtar | Tür / aralık (başlangıç) | Varsayılan (kaynak) |
|---|---|---|
| ogeler | alt küme: kucuk, logo, isim, metin | hepsi |
| grup_merkez | 'grup' / 'halka' | 'halka' (ornament çevrimi 3.4; takvimde 'grup' AT:208) |
| grup_x, grup_y | -1,0 .. 1,0 | 0; +0,071 (3.4 [hesap]) |
| halka_r YA DA grup_r | 0,30 .. 1,20 | halka_r 0,884 (3.4 [hesap]). İkisi birden verilirse DUR; grup_r verilirse halka_r varsayılanı uygulanmaz. halka_r = halka yarıçapı: ölçek = halka_r x Rg / cember R; hedef yarıçap = ölçek x grup çevre yarıçapı. İki geçiş: ilk geçişte grup_kur hedef yarıçap = Rg ile çağrılır (ölçek yaklaşık 0,15 - 0,2 [hesap], büyütme DUR'u AT:1089 tetiklenmez), bilgi 'cevre_yaricap_poster' (AT:1106) okunur, ikinci geçiş gerçek hedefle. Küçük burç ayarının ana sembolü ve halkayı DEĞİŞTİRMEMESİ için iki koşul birlikte gerekir: halka_r modu (ölçek sabit) VE grup_merkez 'halka' (merkez sabit; 'grup' merkezde çevre dairesi merkezi küçük burçlarla kayar, AT:1082-1084, 1092, 1103). grup_r = grup_kur'un hedef yarıçapı (AT:1060): grup güvenli alana oturtulur, küçük burç ayarı tüm grubu yeniden boyutlar (1.2). |
| kucuk_u | sayı 0,30 .. 0,90 (AT:115) ya da 'poster' | 'poster' (ornament'in isim merkezli, asimetrik yeri grup_kur ile verilemez: 3.4) |
| kucuk_v | sayı 0,20 .. 1,30 ya da 'poster' ('poster' = 0,948 [hesap: AT:104; MG cember.json]). AT:115'te 0,60 .. 1,30; alt uç ornament yeri için açıldı, bu aracın kendi tablosu | 0,37 (3.4 [hesap]) |
| kucuk_oran | 0,60 .. 1,80 (AT:115) | 1,0 |
| isim_duzen | 'tek_satir' (A & B; AT:1257) / 'iki_yan' (isim1 [logo] isim2; O3:208-226) | 'iki_yan' |
| isim_cap | 0,03 .. 0,30 | 0,0742 (O3:39 / O4:37 [hesap]) |
| isim_y | -1,0 .. 1,0 (taban çizgisi) | +0,650 (YD:44 [hesap]) |
| logo_boy | 0,5 .. 2,0 (isim büyük harfinin katı) | 1,0 (O4:50) |
| logo_yer | 'isim_arasi' / 'ust' / 'alt' | 'isim_arasi' |
| metin_tur | 'yok' / 'tarih' / 'mesaj' | 'tarih' |
| metin_cap | 0,03 .. 0,30 | isim_cap x 0,850 (O1:46-47: 144 / 169,5 [hesap]) |
| metin_y | -1,0 .. 1,0 (ilk satır tabanı) | +0,817 (YD:44 [hesap]) |
| satir_aralik | 1,2 .. 2,2 | 1,6 (AT:84) |
| isim1, isim2, satirlar | AT:162, 179 kuralları | EMILY, JAMES (AT:210), ['JUNE 14, 2025'] (YD:37) |

Doğrulama (sert, üretim başlamadan): bilinmeyen anahtar, aralık dışı, yanlış tür (bool dahil), sonsuz / NaN, çok büyük tam
sayı, yinelenen JSON anahtarı, liste uzunluğu, toplam metin uzunluğu = DUR, çıkış 3; hata mesajında ham girdi yok, yalnız
hata türü ve anahtar sırası (AT:213-292 kalıbı). Ayar metni kabuk satırına girmez, ortam değişkeninden okunur (W:9, AT:1472-
1481). Dosya adları koddan (bölüm 4.4).

Müşteri verisi yasağı: girdi yalnız örnek isim ve örnek metin (W:8-9). Kod bunu içerikten ayırt edemez; yasak süreç kuralıdır
ve üç yerde yazılır: iş akışı girdi açıklaması (emsal W:23), komut yardım metni, OZET.json not alanı. Açıkça: AYAR.json,
OZET.json ve kütüphane kaydı tam ayar sözlüğünü, yani örnek isim ve örnek metni İÇERİR (emsal AT:1431, ATK:522, 546;
yeniden üretim için gerekli). Girdinin yalnız örnek olması bu yüzden zorunludur. OLCUM'un öğe kayıtlarında metin yok,
yalnız alan adı ve karakter sayısı var (emsal AT:1439-1440).

### 3.4 Kütüphane arayüzü (sonraki parça; yalnız şema)

Kayıt = seçilen seçeneğin OZET satırından koddan üretilen dosya:
{ad, sekil, ayar (TAM sözlük, göreli birimler), kod_sha, ay_sha, motor_sha, ornament_sha, paketler, urun_ad,
urun_girdisi_sha256, sembol_katmani_sha256 (+ 'deneme' / 'gercek' etiketi), logo_sha256, altin_sirasi,
ornek_png_sha256, onay: {kim, tarih, söz}}. Komutlar: `kayit --ozet OZET.json --secenek N --onay "..."` (kayıt dosyası
yazar), `uret --kayit K.json --urun U.json` (kayıttan yeniden üretir). Aynı ürün girdisi + aynı sembol katmanı + aynı
sha'lar + aynı ortamda PNG sha256 kayıttakiyle aynı olmalı; katman farklıysa (deneme / gerçek) bayt eşitliği aranmaz,
yalnız yerleşim ölçümleri karşılaştırılır (test, bölüm 8); başka üründe ayar aynen uygulanır, mm uyarıları yeniden hesaplanır.

Yuvarlak şeklin başlangıç kaydı adayı: ornament yerleşiminin göreli birimlere çevrilmiş hali [hesap; Rg = 380 ve merkez
(476, 477) O4:34, 37; çizgiler YD:28-45]: halka merkezi y +0,071, halka iç yarıçapı 0,884, isim tabanı +0,650, tarih
tabanı +0,817, tarih altı +0,837, küçük burç altı +0,489, sembol alt sınırı +0,224, üst sınır -0,650, isim büyük harfi
0,0742. Hangi ornament düzeninin "onaylı emsal" olduğu bölüm 10 soru 5.

Bu kayıt ornament'i BİREBİR vermez; üç fark vardır ve kayıt notuna yazılır:

- Halka: ornament halkası analitik çizilen elipstir, gövde 4,4 px, taban 4,2 px (O4:47, 113-126; uçlar O5:253). Araçtaki
  halka poster alfasının orantılı küçültülmüşüdür (AT:1029, 1099): aynı yarıçapta 2,3 px [hesap: 336 x 19,07 / 2835,9;
  MG cember.json]. Yani ornament'in onaylı halka kalınlığı orantılı değildir (soru 2 ile aynı konu).
- Küçük burçlar: ornament'te yatay yer her ismin kendi merkezidir, yani isimlere bağlı ve asimetriktir (O3:228-233);
  grup_kur yalnız simetrik -u / +u kurar (AT:1030), kapı da simetrik bekler (ATK:232-236). Araçta B1 için kucuk_u
  'poster' kalır; ornament'in yatay yeri verilemez. Dikey yer halka merkezine göre yaklaşık +0,37 halka yarıçapı
  [hesap: YD:44 kucuk_ust_sabit 594 ve kucuk_alt 663 ortası, YD:28-29]; ornament alt kenara, AT kutu merkezine hizalıyor
  (O3:233, AT:1040), fark [ölçülmedi]. Poster düzeninde u = +-0,49, v = +0,95 [hesap: AT:104, 107; MG cember.json]. Bu
  yüzden kucuk_v alt ucu 0,20'ye açıldı.
- Sembol boyu: ornament'te sembol "sığan en büyüğün 0,85'i" aramasıyla bulunuyor (YD:35). Araçta ana sembol halkadan
  bağımsız boyutlanamaz: ölçeği grup ölçeği x poster oranıdır (AT:1078, 1091). B1'de sembol / halka oranı POSTER oranıdır,
  ornament oranı değil. Ayrı bir sembol boyu anahtarı bu planda yok (soru 5'in alt sorusu).

### 3.5 Renk ve doku arayüzü (sonraki parça; yalnız arayüz)

Ürün girdisinde `zemin` ve AYAR'da ileride `renk` anahtarı: değerler ad ile seçilen kayıtlı zemin / renk setleri. Bu
parçada tek değer 'motor' (zemin_radyal + zemin_yildiz + zemin_8bit, AT:1334-1355). Yerleşim kaydı zeminden bağımsız
tutulur (ayar sözlüğünde renk yok), böylece renk parçası yerleşim kayıtlarını değiştirmeden eklenir.

## 4. Seçenek üretimi

Kural (Dayanak 3): sistematik dizi tasarım önerisi değildir; seçenek numarası üretim sırasıdır, sıralama değildir.

### 4.1 Başlangıç kümesi

O şeklin kütüphane kayıtları (ilk seçenekler). Kütüphane parçası gelene kadar yuvarlak şekil için dilim 1'de iki
başlangıç kaydı ADAYI kodla birlikte gelir; ikisi de Serdar onayına kadar "aday" etiketlidir, sıraları üretim sırasıdır:

- B1 ornament çevrimi (3.4; AYAR varsayılanı budur; üç farkıyla). Hangi ornament düzeni: soru 5. Dilim 1'de logo çizimi
  yok: 'iki_yan' düzenin logo boşluğu için yalnız logo kutusu (kesim + ölçek) gerekir; soru 7a dilim 1'den önce
  cevaplanmazsa dilim 1 B1'i 'tek_satir' düzeniyle üretir ve bunu OZET'e yazar.
- B2 poster grup düzeni: grup_merkez 'grup', grup_x = grup_y = 0, grup_r 1,0 (grup çevre dairesi = güvenli daire; tanım,
  seçilmiş değer değil), kucuk_u ve kucuk_v 'poster' (AT:104, 107). Bu düzende isim ve metin için yer kalıp kalmadığı [ölçülmedi]; kalmıyorsa
  taşma ölçer kapısında görünür.

### 4.2 Yerleşim ızgarası (karar 4)

Öğe başına boyut x yer ızgarası; aynı anda TEK öğe değişir, diğerleri taban ayarda kalır ("ortak alan standardı, sonra öğe
başına ızgara"). Taban ayar = Serdar'ın o an seçtiği seçenek (ilk turda başlangıç kümesinden).

| Izgara | Boyut anahtarı, adımlar | Yer anahtarı, adımlar | Seçenek |
|---|---|---|---|
| grup | halka_r: x0,85, x1,00, x1,15 | grup_y: -0,05, 0, +0,05 | 9 |
| küçük burçlar | kucuk_oran: 0,8, 1,0, 1,2 | kucuk_v: -0,10, 0, +0,10 | 9 |
| isimler | isim_cap: x0,85, x1,00, x1,15 | isim_y: -0,05, 0, +0,05 | 9 |
| logo | logo_boy: 0,8, 1,0, 1,25 | logo_yer: 3 değer | 9 |
| mesaj / tarih | metin_cap: x0,85, x1,00, x1,15 | metin_y: -0,05, 0, +0,05 | 9 |

"Tek öğe değişir" koşulu yalnız halka_r modu + grup_merkez 'halka' ile tutar (3.3): grup_r modunda küçük burç ayarı
ana sembolü ve halkayı yeniden boyutlar, 'grup' merkezde ise kaydırır (AT:1080-1092). Bu yüzden ızgaralar bu modda
üretilir; taban ayar başka moddaysa (ör. B2) araç önce aynı görüntüyü veren eşdeğer ayarı (halka_r, 'halka' merkez,
halka merkezinin yeri grup_x / grup_y olarak) hesaplar, OZET'e yazar ve ızgarayı ondan türetir. Küçük burç yeri taban
seçenekte sayıya sabitlenir ('poster' sözcüğü sayısal karşılığına çevrilir). Grup ızgarasının boyut anahtarı halka_r'dir.
Test (bölüm 8): kucuk_v ya da kucuk_oran değişince ana sembol ve halka pikselleri bayt bayt aynı kalmalı.

Adım ve aralıklar teknik başlangıç değeridir, tasarım kararı değil; girdiyle değiştirilebilir (ızgara tanımı da doğrulanan
girdidir: en çok 2 anahtar, anahtar başına en çok 5 değer). Üst sınır: koşu başına en çok 25 seçenek (bir pafta 5 x 5);
başlangıç değeri, süre ölçümüyle kesinleşir (emsal DENEME_AZAMI AT:49, 119). Sınırı aşan istek DUR (girdi hatası).

### 4.3 Öğe kombinasyonları (karar 3), ayrı çıktı

Aynı taban ayar üzerinde değişebilir öğelerin var / yok kombinasyonları; öğe çıkarılınca diğerlerinin yeri DEĞİŞMEZ
(aynı taban). Nasıl: geometri her zaman TAM öğe setiyle kurulur (grup_kur küçük burçlarla, isim satırı logoyla), çıkarılan
öğe yalnız çizimden ve ölçümden düşülür; yeniden kurulum yapılmaz (aksi halde grup ölçeği AT:1080-1088 ve isim yerleri
O3:215 değişir). Altın katmanları gren sırası nedeniyle yeniden çizilir (7.3). Tam çarpım: küçük burç (2) x logo (2) x isim (2) x metin (yok / tarih / 1 satır mesaj / 3 satır mesaj: 4)
= 32 [hesap]; üst sınır 32, alt küme girdiyle seçilir. Kombinasyon ayrı koşudur (4.2'deki 25 sınırı yalnız ızgara
koşusu içindir); çıktı klasörü ve paftası ayrıdır.

### 4.4 Kişiselleştirilen alanlar: tipik ve en kötü

Her yerleşim seçeneği iki örnek setle üretilir; ikisi de girdidir, kod değer uydurmaz:

- tipik: EMILY / JAMES (AT:210), tarih 'JUNE 14, 2025' (YD:37).
- en kötü: uzun isim çifti (emsal ALEXANDRINA / CHRISTOPHER, W:206), mesaj 3 satır x 35 karakter (sınır AT:137; emsal
  metinler W:204-205). En kötü örnek değerlerinin kendisi alan sınırı kararının parçasıdır (bölüm 10 soru 8).

İsim satırı sınırı aşarsa mevcut kural uygulanır: iki isim birlikte küçülür (isim_sigdir, yumusak=True; AT:556), küçülme
oranı ve sonuç mm değeri OLCUM'a yazılır, alt sınırın altı işaretlenir, seçenek gizlenmez.

Dosya adları koddan: `SEC_<NN>_<izgara>_<T|K>` (NN sıra, T tipik / K en kötü); kombinasyonlarda `KOMB_<NN>`. Girdiden
gelen hiçbir metin dosya adına girmez (ürün adı hariç, desen kontrollü; emsal AT:1162, 1185).

## 5. Çıktılar

| Dosya | İçerik |
|---|---|
| SEC_NN_..._onizleme.jpg | Gerçek oranda önizleme. Tuval kısa kenarı <= 1600 px [başlangıç değeri] ise tam boy; büyükse tam boyun küçültülmüşü (AT:1398 kalıbı). Yuvarlakta kesim dışı beyaz (O4:451-464 kalıbı). |
| SEC_NN_..._kesit_1x1.png | 1:1 kesit: en küçük yazı öğesi ve sembol grubunun en ince yeri (AT:1400-1406 kalıbı). Tuval tam boy yüklendiyse ayrıca kesit gerekmez; büyük tuvalde zorunlu. |
| SEC_NN_..._isaret.jpg | Önizlemenin kopyası: alt sınırın altındaki ya da güvenli alanı aşan öğeler çerçeveyle işaretli, yanında mm değeri. İşaret ayrı dosyadadır; temiz önizleme değişmez. |
| SEC_NN_..._OLCUM.json | Öğe başına: kutu px, genişlik / yükseklik mm, yazıda büyük harf yüksekliği px ve mm, çizgi kalınlığı px ve mm ÜÇ değerle: en ince, 1. yüzdelik ve ortanca. Ortanca = 2 x yari_kal (AT:621-626; iskelet ortancası, ince yerleri göstermez); en ince ve 1. yüzdelik sırt genişliği kalıbıyla (O4:164-168, 176-198) yerleşen alfadan. Halka: nominal kalınlık (cember.json kalınlık x ölçek, AT:1108'in px kısmı) + ölçülen gövde ortancası, 1. yüzdelik ve uç incelmesi (halka uçlara doğru inceliyor; MG KILIT dosyasındaki çember notu). Üç değerin her biri alt sınırla AYRI karşılaştırılır ve ayrı sütunda işaretlenir; hangisinin "sınır altı" sayımına esas olacağı ölçülmeden seçilmez (en ince değer serif ve uçlarda her öğede sınırın altına düşebilir [tahmin]): soru 4. Yazı yüksekliği: büyük harf yüksekliği her yazı öğesinde; küçük harf (x) yüksekliği yalnız karışık harfli mesajda ve fontun 'x' glifinden (isimler büyük harfe çevriliyor AT:173, Cinzel'de küçük harf yok). Logo: logo_olc alanları. sınır altı işareti (yazi / cizgi ayrı), mm_kaynak etiketi, kapı sonuçları (bölüm 6), isim küçülme oranı. Metnin kendisi yok. |
| PAFTA_<izgara>.jpg | Yan yana pafta: satır = boyut adımı, sütun = yer adımı; hücre etiketi seçenek no + değişen iki anahtarın değeri + en küçük yazı mm + en ince çizgi mm + sınır altı öğe sayısı. Etiket yalnız ölçüm; sıralama ve vurgu yok. Tipik ve en kötü ayrı pafta. |
| OZET.json | Her seçeneğin TAM ayar sözlüğü, kod / ay takvimi / motor / ornament sha'ları, paket sürümleri, ürün girdisi, altın çizim sırası, seçenek başına süre, PNG sha256 (birebir yeniden üretim; emsal ATK:557-562). |
| SURE.json | Koşu ve seçenek başına makine süreleri (kurulum, zemin, altın, kayıt, kapı; AT:1217, 1254, 1364, 1394, 1429 kalıbı) + aşama kaydı alanları: asama, baslangic, bitis, serdar_bekleme, deneme_sayisi, inceleme_turu. İnsan alanlarını (bekleme, inceleme turu) araç ölçemez; Merkez `sure-ekle` komutuyla girer. |
| AYAR.json | Doğrulanmış tam ayar listesi (DUR veren seçenek de yeniden üretilebilsin; ATK:556-558). |

mm formülü (Dayanak 5): mm = px x gerçek mm / baskı alanı px (eksen başına; iki eksen oranı %0,5'ten fazla ayrışıyorsa
girdi hatası; oran başlangıç değeri). mm_kaynak 'varsayım' ise her mm alanının yanında etiket ve pafta başlığında tek satır not.

## 6. Kapılar

Yeni aracın tek modu denemedir. Ay takvimi deneme modunun sert / ölçer ayrımı (Serdar 11 Kas "A"; AT:45-47, ATK:40-44)
aynen alınır; bu planda hiçbir kapı gevşetilmez. Takvime özel olduğu için UYGULANAMAYAN kapılar 6.3'te adıyla listelidir
ve Serdar sorusudur (bölüm 10 soru 6).

### 6.1 Sert (FAIL = o seçeneğin görseli yok / silinir)

| Kapı | Kaynak | Neden sert |
|---|---|---|
| girdi (ürün, ayar, ızgara, isim, metin) | kalıp AT:162-292; çıkış 3 AT:1542 | Yanlış giriş görsel üretmemeli. Anahtar ve aralık tablosu bu aracın kendisinindir (3.3); kucuk_v alt ucu takvimdeki 0,60 yerine 0,20 (Merkez teyidi: soru 6). |
| ortam: pillow 11.0.0 + raqm | AT:1214-1216; W:96-97; CM:93-97 | Glif yerleşimi sürüme bağlı. |
| motor dosyaları ve KILIT dalları | AT:674-688 | Altın yolu değişmez. |
| sabit sha'lar (motor, ornament, ay takvimi) + yüzey testi | W:71-79; ATT:39-46 | Kaynak değişirse eşdeğerlik düşer. |
| sembol biçimi (RGBA, alfa) | AT:971-978 | |
| şekil değişmez (takvim kapı 2'nin TAMAMI, ATK:315-349): en boy farkı <= 0,005; ölçek <= 1; son dosyada sembol rengi küçültülmüş katmanla aynı (tam alfa pikselde fark <= 1 seviye, ATK:321-333); yarı saydam kenar pikselleri sınır içinde (ATK:334-340); kaynak sha aynı ve yerleşen = kaynağın yalnız eş oranlı küçültülmüşü, birebir (ATK:344-349) | ESIK ATK:66 | Dayanak 3; sembol dokunulmaz (AT:20, 23-24). Deneme modunda başka öğenin örttüğü sembol pikseli renk karşılaştırmasına girmez (ATK:324-332); aynen. |
| büyütme yok: grup ölçeği, ana ölçek, küçük ölçek <= 1; k kat çizim kaynaktan büyük değil | AT:1089-1090, 846-847; ATK:203, 214 | Dayanak 3. |
| grup yeniden kurulum + bağımsız ölçüm (halkaya uydurulan çember, küçük sembol yeri / boyu, ana sembol yeri; pay 2 px) | ATK:182-270; ESIK ATK:68-69 | Dayanak 3. Pay 5400 tuvalde ölçüldü (ATK:32-34); 1087 tuvalde [ölçülmedi]: ilk yerel koşuda 'fark_en_buyuk' okunur, eşik ancak ölçümle ve Serdar onayıyla değişir. |
| logo yalnız ölçek: yerleşen alfa = kaynak alfanın TEK adım küçültülmüşü (birebir), ölçek <= 1, k kat çizim kaynaktan büyük değil | YENİ; tanım O4:10, kalıp ATK:208-214 | Dayanak 3 (logo: yalnız ölçek + altın). "Kaynak alfa"nın tanımı (hangi kesim, temizlikten önce mi sonra mı) soru 7'ye bağlı. Not: OM logoyu 10 kat çizimde büyütüyor (OM:427-429 INTER_CUBIC; OM:672 "1.41 buyutme"); yeni araçta k kaynağa göre düşer (AT:1100-1102 kalıbı), büyütme olmaz. |
| çerçeve tutarlılığı (k kat çerçeve = 1x çerçevenin tam katı) | AT:851-855 | Yazım kapısının ön koşulu. |
| renk uyumu için >= 200 çekirdek piksel | AT:608-609; ESIK ATK:65 | AT:46-47'de sert. Küçük tuvalde ince öğelerde tutmayabilir [ölçülmedi]; tutmazsa o seçenek DUR verir, kapı değişmez. |
| ana sembol tuval dışına taşıyor (kısmen de olsa); herhangi bir öğe tümüyle tuval dışında; isim satırı 8 denemede sığmıyor | AT:1327-1331; AT:558-559 | Takvim deneme modunda da DUR. |
| çıktı: boyut = ürün baski_px, RGB, sRGB ICC | ATK:508-510 (boyut ve dpi koşulu ürüne göre; soru 6) | Kapı 10'un ürüne bağlı olmayan parçaları aynen. |

### 6.2 Ölçer-yazar (FAIL görseli durdurmaz; OLCUM'a ve işaretli önizlemeye yazılır)

| Kapı | Kaynak | Neden ölçer |
|---|---|---|
| gerçek ölçü uyarısı (yazı mm, çizgi mm < alt sınır) | YENİ (Dayanak 2c, 5) | Tanım gereği: seçenek gizlenmez. |
| güvenli alan / yasak bölge taşması (piksel sayısı, öğe adı) | tanım O4:219-270, 425-437 | Ornament'te çözücü kısıtıydı; araçta Serdar taşan seçeneği de görür (emsal 'tasma' AT:45-46, 1332). İki ölçüm birlikte: öğe maskesi (alfa > 0,02; öğe adı için) ve görüntü farkı (son görsel ile altınsız zemin farkı > 1; O4:425-437 yolu; dış gölgeyi de yakalar, AT:131, 1455). |
| grup - yazı boşluğu (px ve mm) | ATK:430-439, 457; ESIK ATK:67 (12 px, 5400 tuval) | ATK:43. Takvimde "grup - ay adı"; araçta grup ile her yazı öğesi arası. Eşik 12 px aynen yazılır; başka tuvalde anlamı [ölçülmedi] (soru 6). |
| metin tabanı tutarlılığı | ATK:488, 500 | ATK:43. |
| öğe çakışması / altın binme | O4:255-269; ATK:413-427 | Aynı gerekçe. |
| tek doku dE00 <= 2,0 | ATK:362-402; ESIK ATK:65 | ATK:43. |
| kontrast >= 4,5 | ATK:95-114, 403-406 | ATK:43. |
| yazım alfa farkı <= 0,035 | ATK:388-389, 408 | ATK:43. |
| altın öğede düz renk yok (yayılım >= 40); halka yalnız bilgi | ATK:391-392, 469-475 | ATK:43. |
| isim satırı sınırı ve küçülme | AT:544-560; ATK:476-480 | AT:45. Alt sınır takvimde ay adı boyuydu (AT:1258); yeni araçta ürün alt sınırı (yazi_mm). |
| metin satır genişliği | AT:1266-1273 | AT:45. |
| yıldız altın öğeye değmez (12 px pay) | ATK:470-475; ESIK ATK:72; engel maskesi kalıbı AT:1339-1353 | ATK:43. Zemin 'motor' olduğu sürece geçerli. SORUN: üretimdeki yıldız engel payı tuvale oranlı (61 x W / 7200, AT:1350): 5400 tuvalde 47 px, 1087 tuvalde 9 px çekirdek = +-4 px [hesap]; kapı payı sabit 12 px. Küçük tuvalde 5 - 12 px bandına düşen her yıldız FAIL yazdırır. Bu planda ne kapı payı ne engel payı değiştirildi: soru 6. |
| öğe sayısı tamlığı (beklenen öğe listesi = çizilen öğe listesi; kombinasyonda beklenen liste ayardan) | ATK:394-402 | ATK:43; takvimde kapı 3'ün parçası. |
| sayfa kenarı payı | ATK:450, 458 (180 px, 5400 tuval) | Yerine ürün güvenli alanı kapısı (yukarıda); dikdörtgen ürünlerde güvenli alan = kenar payı. |

### 6.3 Uygulanamayan takvim kapıları (kapatma değil, kapsam dışı; Serdar teyidi istenir)

Kapı 1 veri ve evre (ATK:308-313), kapı 6'nın disk bölümleri (yazı - disk, disk - disk, sembol - disk; ATK:410-458), kapı
7'nin "altın dışı öğede altın yok" bölümü (ATK:459-467; yeni araçta altın dışı öğe yok), kapı 9 blok dikey ortalaması
(ATK:481-500; yeni araçta yer AYAR'dan gelir), kapı 10'un yalnız "5400 x 7200" ve "300 dpi etiketi" koşulları
(ATK:508-510; boyut ürün baski_px olur, dpi etiketi ürün girdisinden hesaplanan değer olur; RGB ve sRGB koşulları 6.1'de
sert kalır), kapı 0 "ayar = varsayılan" (ATK:292-296; yalnız mod örnek) ve mod tutarlılığı (ATK:295, 512; araçta tek mod
var). Kapı 8'in isim alt sınırı ay adı boyundan (ATK:480) ürünün yazı alt sınırına geçer. Ornament yasak bölge kapısının
ornament'e özgü parçaları ürün girdisine parametre olur: ışık taşması için 8 px genişletme (O4:249; araçta ışık taşması
yok, ama genişletmeyi 0 yapmak ölçüm bölgesini daraltır: bu yüzden 6.2'de görüntü farkı ölçümü de var; genişletme
değeri soru 6), halkanın delik / üst çizgi istisnası
(O4:243-252; ürün girdisinde yasak bölge başına "halka hariç" işareti), güvenli daire payı 3 px (O4:45, 222; ürün
girdisinde pay alanı). Eşdeğerlik testi bu üç parametre 954 değerleriyle verilerek yapılır.

## 7. Koşu yeri ve hız

### 7.1 İki yol

| | (i) Yerel, deneme sembolüyle | (ii) Actions, gerçek katmanla |
|---|---|---|
| Ana sembol | deneme_komut çıktısı (AT:1503-1521) | Drive katmanı (W:124-136) |
| Diğer kaynaklar | Hepsi depoda: motor, halka, küçük burçlar, fontlar, logo (MG) | Aynı |
| Onay | Koşu başına gerekmez (görsel yüklenmez; DENEME_ adlı) | Her koşu dispatch + onay dizesi (W:21, 38-58) |
| Çıktı | Oturumun çalışma klasörü; Serdar'a pafta gösterimi ayrı karar | Drive TEMP (W:240-262) |
| Depo kuralı | CM:111 "iterasyon yerelde"; CM:98-99 "tüm üretim Actions'ta koşar (KARAR 3)". Serdar'a gösterilecek karar görselinin yerelde üretilmesi bu iki kuralın arasında kalıyor: soru 1. | CM:98-99 ile uyumlu; CM:111-112 "Actions yalnız yerelde temiz çıkan sürüm için, en fazla 1 kez". |
| Sabit yük | Ortam kurulumu bir kez [tahmin: 2 - 4 dk] | Koşu başına checkout + paket + rclone + sembol indirme [tahmin: 2 - 4 dk; ölçülmedi] + kuyruk |

### 7.2 Süre

Mevcut ölçüm [kayıt, AT:48-49; 5400 x 7200, 4 çekirdek]: deneme başına üretim 46 - 52 sn (zemin 5 - 6, altın 18 - 22,
PNG + DUMP 20 - 21) + kapı 8 - 10 sn; ilk örnekte +15 sn.

1087 x 1087 tuvale geçiş [tahmin; ölçülmedi]:

- Zemin ve kayıt piksel sayısıyla ölçeklenir: 38,9 MP -> 1,18 MP (33 kat az [hesap]); her biri 1 sn altı beklenir.
- Kapı ölçeklenmez: kapı 2 tam çözünürlüklü katmanı yeniden küçültüyor ve grubu yeniden kuruyor (ATK:345-346, 191-193);
  bunlar tuval boyundan bağımsız. Motor yeniden kurulmaz (aynı süreç). Beklenen 2 - 6 sn.
- Altın ölçeklenmez: her öğe poster ölçeğine yakın çizilir (k kat; yazıda büyük harf x k ~ 298 px AT:565, grupta k =
  1 / ölçek AT:1100). Halka kaynağı en büyük iştir. Öğe sayısı takvimden az (takvim 14 - 17 yazı + 3 grup; araç en çok
  5 yazı + 4 grup). Beklenen 8 - 20 sn; üst sınır mevcut 18 - 22 sn.
- Tek seçenek, sıfırdan: kurulum 15 sn (bir kez) + 12 - 28 sn.
- Yalnız yer değişen seçenek: motor katmanları önbellekten (7.3 madde 4), renk uyumu + birleştirme + kapı: 3 - 8 sn.
  Koşul: yer değişimi hiçbir öğenin boyunu değiştirmemeli (ör. isim satırı yeni yerde kirişe sığmayıp küçülürse o öğe ve
  sonrakiler yeniden çizilir).
- 9 seçenekli ızgara paftası (3 boyut x 3 yer), TEK örnek setle: en iyi durumda 3 çizim + 6 yer değişimi, 1 - 3 dk;
  önbellek hiç tutmazsa 9 tam çizim, 2 - 5 dk. 25 seçenek: 3 - 12 dk. Tipik + en kötü iki setle (4.4) süreler iki katı
  [hesap]. halka_r modunun iki geçişi seçenek başına bir ek katman küçültmesi getirir (0,5 - 2 sn).
- Actions'ta aynı süreler + sabit yük.

Bu rakamlar ilk dilimin ilk yerel koşusunda SURE.json ile ölçülür; üst sınır (25) ölçümden sonra kesinleşir.

### 7.3 Çıktıyı değiştirmeyen hızlandırmalar

1. Tek süreç, tek Motor, tek renk haritası: takvimde her deneme ayrı süreç ve kapı ayrıca Motor kuruyor (W:195, ATK:191).
   Harita önbelleği zaten var (AT:779-799).
2. DUMP.npz yazılmaz: takvimde kapı ayrı süreç olduğu için maskeler dosyaya yazılıyor (AT:1422-1428, 20 - 21 sn'nin
   parçası). Yeni araçta kapı aynı süreçte, maskeleri bellekten alır; son görseli yine KAYDEDİLEN dosyadan okur ("ölçüm
   son dosyadan" ilkesi ATK:3 korunur). Piksel çıktısı aynı.
3. Tam boy PNG küçük tuvalde zaten önizlemedir; büyük tuvalde (dikey 5400) deneme modunda tam boy PNG gerekmez, yalnız
   önizleme + 1:1 kesit (W:10-11 ile aynı karar).
4. Motor katmanı önbelleği, ön ek kuralıyla. Önbelleğe alınan şey yalnız Motor.oge_katman çıktısıdır (AT:853). Gren tek
   rng'den öğe sırasıyla ve k KAT çerçeve boyutunda çekiliyor (AT:840, 814), yani bir öğenin katmanı kendinden ÖNCEKİ
   öğelerin k kat çerçeve boyutlarına da bağlı. Anahtar = (öğenin k kat alfası + k + motor adı + harita kimliği + önceki
   öğelerin k kat çerçeve boyutları dizisi). renk_uyum (hedef: ana sembolün Lab ortancası, AT:856, 1382), iç gölge oranı
   (ana sembolün yarı kalınlığına göre, AT:857-858, 1247) ve birleştirme (boya) HER seçenekte yeniden yapılır: bunlar ana
   sembolün boyuna bağlıdır ve ucuzdur. Önbellek isabetinde de rng aynı miktarda ilerletilir (aynı boyutta normal dizi
   çekilip atılır), yoksa sonraki öğenin greni değişir. Test: önbellekli ve önbelleksiz çıktı bayt bayt aynı.
5. Çizim sırası: varsayılan emsal sırasıdır (yazılar önce, grup öğeleri sonra; AT:839). Bu sırada bir yazının boyu
   değişince halka dahil sonraki tüm öğeler yeniden çizilir. Sıra "halka, küçük burçlar, logo, yazılar" yapılırsa
   önbellek daha çok tutar, ama yazıların gren deseni emsalden ayrılır (çıktı değişir): bu yüzden öneri değil, soru 13.

Önerilmeyenler (çıktıyı değiştirir): düşük çözünürlükte çizim, k'yi düşürme, grensiz çizim, başka altın yolu (ör. O1
tek_doku), öğe başına ayrı tohum.

### 7.4 Deneme sembolü ile gerçek katman farkı

Olgular: (a) deneme sembolü poster ana alfasının motorla gölgelenmiş halidir (AT:1504, 1508-1513); gerçek katman Drive'daki
ayrı dosyadır; yüzey rengi / dokusu aynı olmak zorunda değil. (b) Sınır kutularının aynı olduğu doğrulanmamış (YDT:3-4
açıkça yazıyor; ATK:32-34 "gerçek Drive katmanıyla ölçülmedi"). (c) Diğer altın öğelerin rengi ana semboldeki Lab
ortancasına kaydırılıyor (AT:1382, 604-618): sembol rengi farklıysa TÜM öğelerin tonu farklı çıkar.

Yerleşim kararına etkisi: yer ve boy alfa siluetine bağlıdır; (b) küçükse yerel görsel yerleşim kararı için geçerlidir.
Renk / doku kararı (sonraki parça) için (a) ve (c) nedeniyle gerçek katman gerekir.

Ölçüm yolu: aynı ayarla bir kez iki kaynakla üretim; SEMBOL_OLCUM alanları (kutu, en boy, çevre yarıçapı; AT:979-985),
grup_kur çıktıları (ölçek, ana sembol yeri ve boyu) ve yerleşen alfa farkı (IoU, en büyük kenar kayması px) karşılaştırılır.
Yeterlilik eşiği (ör. 1087 tuvalde kaç px fark kabul) bu planda konmaz; ölçüm sonucu Merkez'e gider, eşik Serdar /
Merkez kararıdır.
Gerçek katman ölçümü ay takvimi koşularının Drive'daki SEMBOL_OLCUM.json dosyasında zaten olabilir (bu oturum okumadı).

### 7.5 Ortam sabitleme (yerel)

Sürümler iş akışınınkiyle aynı (W:82, 95): Python 3.13, pillow 11.0.0, numpy 2.5.4, opencv-python-headless 5.0.0.93,
scipy 1.18.1, scikit-image 0.26.0, potracer 0.0.4, pyyaml 6.0.2; raqm için libfribidi0 (W:94). `python3 -m venv` + sabit
sürümlü pip (CM:96); araç başlarken pillow sürümü ve raqm'ı sert kontrol eder (AT:1214-1216), sürümleri OZET'e yazar
(AT:1459). Bu kapta Pillow 12.3.0 kurulu: sistem Python'u kullanılamaz, venv zorunlu. Kaynaklar `git archive <sha>` ile temiz klasöre alınır (CM:113; içe alınan dosyalar için `git check-ignore`
taraması). raqm bu kapta kurulabilir mi [ölçülmedi]: kurulamazsa yerel yol DUR verir, kapı gevşetilmez (soru 1'e bağlı).

## 8. Testler

Kural: her kapı bilinen PASS + bilinen FAIL; test gerçek fonksiyonu çalıştırır; mutasyon denemesi (kod bozulunca test FAIL);
test komutu tek başına koşar, çıkış kodu ayrı okunur (CM:209, 217; "Test 3 dersleri").

| Test | Bilinen PASS | Bilinen FAIL |
|---|---|---|
| girdi: ürün şeması | iki deneme girdisi | eksik alan, negatif px, eksen oranı ayrışması, desen dışı ad, bilinmeyen şekil |
| girdi: AYAR ve ızgara | boş sözlük = varsayılan; aralık uçları | ATT:144-151 listesinin karşılığı (bilinmeyen anahtar, aralık dışı, tür, bool, sonsuz, NaN, 10^400, yinelenen anahtar), 26 seçenekli ızgara |
| enjeksiyon | zararsız özel karakterli geçerli örnek metin (izinli küme AT:136) kabul edilir, dosya adı değişmez | ATT:155-163 ve 757 kalıbı: değer içinde kabuk karakteri / satır sonu / log komutu; hata mesajında ham girdi yok; dosya adı koddan |
| mm formülü | [varsayım] girdisiyle: 1087 px -> 25,4 mm; 64,2 px -> 1,5 mm; işaret eşiğin iki yanında doğru | sınırın 0,01 mm altı işaretlenir, üstü işaretlenmez; mm_kaynak 'varsayım' iken etiket yoksa FAIL. Yalnız formülü sınar. |
| yüzey testi | AY_SHA dosya sha'ları ve imzalar | bir imza değiştirilmiş kopya |
| eşdeğerlik: logo fonksiyonları | O4:156-198 kaynaktan çıkarılıp aynı girdiyle aynı çıktı (ATT:77-100 yardımcıları kalıbı) | bir satırı değiştirilmiş kopya |
| eşdeğerlik: yasak bölge | 954 sabitleriyle O4 yasak_m / kapi ile aynı piksel sayıları | yarıçapı 1 px büyütülmüş ürün girdisi |
| eşdeğerlik: grup kapısı | takvim META'sıyla ATK grup_kapisi ile aynı sayılar | ATT:1305-1364 mutasyonları (büyütme, ana sembol kayması, küçük sembol yeri) |
| şekil değişmez / büyütme yok | deneme sembolü, varsayılan ayar | esnetilmiş sembol (ATT:211 sahte_sembol esnet), ölçek > 1 isteyen ayar, kaynaktan büyük k |
| logo yalnız ölçek | depodaki logo | kalınlaştırılmış (genişletilmiş) logo maskesi; büyütme gerektiren boy |
| gerçek ölçü, taşma, çakışma (ölçer) | varsayılan | bilerek küçük yazı; güvenli alan dışına itilmiş öğe; üst üste iki öğe: OLCUM'da FAIL, görsel VAR |
| ayarsız çıktı birebir | aynı girdiyle iki koşu: PNG sha256 aynı; varsayılanların tamamı açıkça verilmiş ayar = ayarsız (ATT:197-198 kalıbı) | bir anahtarı değişmiş ayar: sha farklı |
| önbellek | önbellekli = önbelleksiz (bayt) | öğe sırası değişince anahtar değişir |
| kayıttan yeniden üretim | kayıt -> üretim -> PNG sha256 kayıttaki ile aynı | sha'sı farklı kod / motor ile DUR |
| tek öğe değişir | halka_r + 'halka' merkezde kucuk_v / kucuk_oran değişince ana sembol ve halka pikseli bayt bayt aynı | grup_r modunda ya da 'grup' merkezde aynı test FAIL vermeli (bağın gerçekten yakalandığının kanıtı) |
| kombinasyon | öğe çıkarılınca kalan öğelerin kutuları (x, y, boy) tam setle aynı | geometriyi eksik setle yeniden kuran bozuk kopya: kutular değişir, test FAIL |
| halka_r iki geçiş | ölçülen halka yarıçapı = halka_r x Rg (pay 1 px [başlangıç değeri]) | halka_r ve grup_r birlikte: DUR |
| pafta | hücre sayısı, etiket içeriği, tipik / en kötü ayrı | eksik seçenek hücresi "YOK" (YK:47-50 kalıbı) |
| süre kaydı | alanlar tam, bitiş >= başlangıç | eksik alan |
| ay takvimi regresyonu | `git diff --stat` boş; ATT, AY_SHA kopyasında motorlu tam koşu (ephem ile), çıkış 0 | denetim betiği, ay takvimi klasöründe tek bayt değişmiş geçici kopyada FAIL vermeli |
| ortam kapısı | pillow 11.0.0 + raqm | sürüm dizesi / raqm bayrağı test içinde değiştirilmiş sahte ortam: DUR 'ortam' (AT:1214-1216 koşulu) |
| motor / KILIT kapısı | sabit sha'lı motor klasörü | bir dosyası eksik kopya; KILIT'te bir dalı değişmiş kopya (AT:674-688) |
| sembol biçimi | RGBA deneme sembolü | RGB, boş alfa, tam dolu alfa (ATT:211-246 kalıbı) |
| sembol rengi / kenar / kaynak sha (kapı 2) | değişmemiş üretim | son dosyada sembol pikseli 2 seviye değiştirilmiş; katman dosyası değişmiş (sha) |
| çerçeve tutarlılığı, 200 çekirdek piksel | varsayılan | 1 px kaydırılmış k kat çerçeve; çok küçük yazı (çekirdek < 200): DUR |
| tuval dışı, isim sığmıyor | varsayılan | sembolü tuval dışına iten ayar; çok uzun isim + dar kiriş: DUR |
| çıktı (boyut, RGB, sRGB) | varsayılan | yanlış boyutlu / RGBA / profilsiz dosya |
| ölçer kapılar: dE00, kontrast, yazım farkı, düz renk, yıldız, öğe sayısı, isim / metin genişliği | motorlu gerçek koşu (en az bir PASS) | ATT:536-668 t_kapi kalıbındaki bozulmuş sahte koşular (renk kaydırma, düşük kontrast zemin, kaydırılmış maske, düz renkli öğe, öğeye değen yıldız, eksik öğe, geniş satır): OLCUM'da FAIL, görsel VAR |
| tek modül | araç ve kapı aynı AT nesnesini görür | AT'nin başka adla ikinci kez yüklendiği durumda test FAIL |
| iş akışı kabuk adımları (Actions dilimi) | ATT:695-918 kalıbı, sahte rclone | yanlış onay, Re-run, ref main değil, boş değişken |

Zayıf test uyarısı: sahte veriyle kurulan kapı testleri (ATT:346 sahte_kosu kalıbı) yalnız kapı mantığını sınar; raporda
"sahte veri" diye yazılır, gerçek motorlu en az bir PASS koşusu ayrıca istenir.

## 9. Uygulama dilimleri ve sırası

Süreler [tahmin]; her dilim en çok 2 deneme, sonra DUR.

| Dilim | İçerik | Dosyalar | Bağımsız inceleme noktası | Süre |
|---|---|---|---|---|
| 1 | Yuvarlak şekil, mevcut öğeler (sembol + halka + küçük burçlar + isimler + tek satır metin), iki başlangıç kaydı adayı (4.1), mm + uyarı, sert / ölçer kapılar, grup ızgarası, pafta, OZET / OLCUM / SURE; yalnız yerel, deneme sembolü | tasarim_deneme.py, tasarim_kapi.py, test_tasarim_deneme.py, urun/DENEME_YUVARLAK_1087.json | Kod + testler bittiğinde, ilk pafta Serdar'a gitmeden önce (tek ajan) | 4 - 6 saat |
| 2 | Logo (MG LOGO_1; logo kapısı, logo ızgarası) + öğe kombinasyonları çıktısı | aynı 3 dosya | Logo kapısı kodu | 2 - 3 saat |
| 3 | Mesaj 1 - 3 satır, tarih, tipik / en kötü çift üretim, isim ve metin ızgaraları | aynı 3 dosya | - (dilim 4 ile birlikte) | 2 - 3 saat |
| 4 | Dikey şekil (DENEME_DIKEY_5400) ve yatay; büyük tuvalde önizleme + kesit yolu | aynı + urun/DENEME_DIKEY_5400.json | Şekil genellemesi | 3 - 4 saat |
| 5 | Kütüphane (kayıt, kayıttan üretim), renk / doku arayüzünün içi | sonraki parça | - | sonraki parça |
| 6 | Actions yolu: tasarim-deneme.yml, kabuk testleri, gerçek katmanla tek koşu, deneme sembolü farkı ölçümü (7.4) | iş akışı + test | İş akışı main'e girmeden önce | 3 - 4 saat + 1 koşu |

Sıra gerekçesi: 1 her şeyin tabanı ve en hızlı geri bildirim; 2 ve 3 Serdar'ın karar 3 ve 4'ünü besler; 4 ikinci şekli
açar; 6 yalnız koşu yeri sorusu Actions çıkarsa ya da renk / doku parçası gerçek katman isteyince gerekir. 7.4 ölçümü
erken istenirse dilim 6 dilim 2'nin önüne alınabilir (Merkez kararı).

## 10. Açık sorular (Serdar kararı)

Görsel tercih sorularında öneri yok. Teknik sorularda öneri ayrıca yazıldı.

1. Koşu yeri. (a) yerel + deneme sembolü; (b) Actions + gerçek katman; (c) yerleşim için (a), renk / doku ve son teyit
   için (b); (d) yerel + gerçek katman (Code oturumunun Drive bağlayıcısıyla indirme; bu oturumda araçlar listeli ama
   denenmedi, ayrıca Drive okuma izni gerekir). Kural gerilimi: CM:98-99 "tüm üretim Actions'ta" ile CM:111 "iterasyon
   yerelde"; (a), (c) ve (d) Serdar'a gösterilecek görselin yerelde üretilmesi demektir ve bu açık karar ister. Teknik
   öneri: (c), 7.4 ölçümü yapılana kadar yerel görseller "deneme sembolü" etiketiyle.
2. Halka kalınlığı anahtarı genel araca alınsın mı? Olgu [hesap; eşleme varsayım; halka yarıçapı 0,884 Rg ile Rg
   arasında ve Rg = 543,5 px varsayımıyla]: deneme girdisinde orantılı halka nominal 0,076 - 0,085 mm, sınır 0,2 mm;
   sınıra ulaşmak için 2,3 - 2,6 kat gerekir (uçlar daha da ince). Bu planın AYAR tablosunda halka kalınlığı anahtarı
   YOK: dilim 1 fiilen (a) ile kurulur. Seçenekler: (a) alınmaz, halka hep orantılı, araç yalnız işaretler; (b) ay
   takvimine eklenmekte olan anahtar aynen alınır (görev metnine göre AY TAKVİMİ oturumu bugün ekliyor; f89f55d'de böyle
   bir anahtar yok, AT:113-114; main'e girince, sha yükseltilerek);
   (c) ürün girdisinde alt sınır varsa halka seçenekleri sistematik dizi olarak üretilir (görev metnindeki 11 Kas emsali:
   1,5 / 2 / 2,5 / 3 kat; depoda kaydı görülmedi).
   Ek olgu: onaylı ornament halkası da orantılı değil, analitik ve daha kalın (bölüm 3.4). Öneri yok (şekil kuralına
   dokunur; Serdar kararı).
3. Logo kaynağı. Olgu: depoda MG girdi/LOGO_1.png var; yerelde de Actions'ta da kullanılabilir. Soru: bu dosya Serdar'ın
   onayladığı logo kaynağı mı (ornament koşularının kaynak klasöründeki dosyayla aynı mı)? Teknik öneri: Merkez iki dosyanın
   sha256'sını karşılaştırsın; aynıysa depodaki kullanılır, başka kaynak gerekmez.
4. Üretici alt sınırının altındaki yazı. Olgu [hesap]: ornament oranı taşınınca isim büyük harfi <= 0,94 mm, tarih <= 0,80
   mm (sınır 1,5 mm). Araç işaretler, gizlemez (karar 6). Soru: başlangıç seçeneği yine ornament oranı mı olsun, yoksa
   "alt sınırı tam tutan en küçük boy" da sistematik bir başlangıç seçeneği olarak eklensin mi? Öneri yok. Bağlı soru:
   üreticinin "yazı yüksekliği" sınırı büyük harf yüksekliğiyle mi, küçük harf (x) yüksekliğiyle mi karşılaştırılacak?
   Üretici tanımı bu oturumda doğrulanmadı; araç büyük harf yüksekliğini her yazıda, küçük harf yüksekliğini yalnız
   karışık harfli mesajda ölçer. İkinci bağlı soru: çizgi alt sınırı öğenin en ince yeriyle mi, 1. yüzdeliğiyle mi,
   gövde ortancasıyla mı karşılaştırılacak? Araç üçünü de yazar ve ayrı işaretler; "sınır altı öğe sayısı" etiketi için
   ölçüt ilk yerel ölçümden sonra Merkez / Serdar kararıyla seçilir. Bu planda ölçüt seçilmedi.
5. Yuvarlak şeklin "onaylı emsal" kaydı hangisi: YD yeni düzen çizgileri (YD:28-45; sipariş kipi yalnız bu düzenle
   çalışıyor, OM:272-273) mi, O5 V5 düzeni mi? Olgu yazıldı; kayıt Serdar onayıyla kütüphaneye girer. Alt soru: araç
   ornament'i birebir veremiyor (3.4: halka kalınlığı, küçük burçların isim merkezli yeri, sembol / halka oranı). Bu üç
   fark kabul mü, yoksa birebir ornament için ek anahtar / ek kod (ayrı dilim) mi istenir? Öneri yok.
6. Bölüm 6.3'teki takvim kapılarının yeni araçta kapsam dışı sayılması teyit edilsin (kapı gevşetme kuralı gereği açık
   onay): veri / evre, disk boşlukları, "altın dışı öğede altın yok" (kapı 7a), blok ortalaması, "ayar = varsayılan",
   mod tutarlılığı; kapı 10'da boyutun ürün baskı alanına ve dpi etiketinin ürün girdisinden hesaplanan değere
   bağlanması; kapı 8 isim alt sınırının ürün yazı sınırına geçmesi; sayfa kenarı payının ürün güvenli alanıyla
   değişmesi; "grup - ay adı" boşluğunun "grup - yazı" boşluğu olarak ölçülmesi ve 12 px eşiğinin başka tuvaldeki
   karşılığı; AYAR tablosunda kucuk_v alt ucunun 0,20 olması; ornament yasak bölge kapısının üç parçasının ürün
   parametresi olması ve ışık taşması genişletmesinin değeri (0 ölçüm bölgesini daraltır; görüntü farkı ölçümü bunun
   yerine konuyor). Ayrı karar: yıldız kapısı küçük tuvalde yapısal FAIL yazdırır (6.2). Seçenekler: (a) yeni kodda
   yıldız engel payı kapı payını kapsayacak kadar büyütülür (kapı aynı kalır; zemin emsal formülünden ayrılır, öğe
   çevresinde daha az yıldız); (b) kapı payı tuvale oranlanır (gevşetme; Serdar onayı ister); (c) hiçbiri değişmez,
   FAIL yazılmaya devam eder. Bu planda (c) geçerli; öneri yok (zemin görünüşüne dokunur).
7. Logonun işlenişi (üç alt soru). Olgular: motor VEKTOR yolu yalnız 'ana, kucuk1, kucuk2, sonsuz' adlarında çalışıyor
   (AT:700); ornament motorunda logo 'sonsuz' adıyla işleniyor (OM:47). Ornament motoru logoyu 10 kat boya BÜYÜTÜP sonra
   alfa temizliğinden geçiriyor (OM:427-433); poster hattı da temizlik uyguluyor ve başka bir kesim kullanıyor (MG
   olustur_alfa_sablon.py:69). Ay takvimi grup yolunda logo için temizlik adımı yok. (a) Kesim: ornament kesimi mi
   (O4:156-161), poster kesimi mi? (b) Alfa temizliği uygulansın mı? Temizlik şekli değiştirebilir (logo kuralı: yalnız
   ölçek); uygulanacaksa kaynak çözünürlüğünde BİR KEZ yapılır, 1x maske de k kat çizim de bu temizlenmiş kaynaktan
   küçültülür (yoksa maske ile renk katmanı ayrışır, AT:848-860), "yalnız ölçek" kapısı temizlenmiş kaynağa göre
   tanımlanır ve temizliğin kaynağa farkı (IoU, logo_olc) OLCUM'a yazılır. (a) ve (b) logonun görünüşüne dokunur: öneri
   yok. (c) Motor adı: teknik öneri 'sonsuz' (OM:47 ile aynı). Logo için 200 çekirdek piksel şartının 1087 tuvalde tutup
   tutmadığı [ölçülmedi].
8. En kötü örnek değerleri (en uzun isim çifti, en uzun mesaj, en geniş tarih) kim verir ve nedir? Bunlar karar 4'ün alan
   sınırıdır. Teknik öneri: Merkez verir, ürün girdisine "ornek_en_kotu" olarak yazılır; kod değer uydurmaz.
9. Güvenli alan ve yasak bölge (delik, askı) deneme girdisinde yok. Soru: Printify şablonundan ölçülüp verilecek mi, yoksa
   ilk dilim güvenli yarıçap = tuval yarıçapının sabit bir oranı [varsayım] ile mi başlasın? Teknik öneri: şablon ölçümü
   gelene kadar oran varsayım etiketiyle, uyarılar "varsayım" notuyla.
10. Çift kapsamı: araç bu parçada yalnız CANCER_LIBRA ile çalışır (AT:107). Başka çift gerekirse küçük burç yerleri için
    ayrı iş gerekir. Bu parça için yeterli mi?
11. Kazıma ürünlerinde (deneme girdisinin kaynağı lazer kazıma sayfası) önizleme altın yolu ve motor zeminiyle üretilir;
    gerçek ürün tek renk kazımadır. Yerleşim kararı için altın önizleme yeterli mi, yoksa renk / doku parçasında "tek renk"
    önizleme ayrıca mı istenir? Öneri yok (görsel karar; arayüz 3.5'te hazır).
12. Yerel çıktının Serdar'a gösterim yolu: yerel yolda dosyalar Drive'a kendiliğinden gitmez. Seçenekler: Merkez'e pafta
    dosyası olarak iletim; ya da yalnız paftanın Drive TEMP'e yazılması için ayrı izin. Teknik öneri yok (izin kararı).
13. Altın çizim sırası. Emsal: yazılar önce, grup öğeleri sonra (AT:839). "Halka, küçük burçlar, logo, yazılar" sırası
    hızı artırır (7.3 madde 5) ama yazıların gren desenini emsalden ayırır. Seçenekler: (a) emsal sırası (plan
    varsayılanı); (b) yeni sıra. Teknik öneri: (a); (b) ancak süre ölçümü gerek gösterirse ve iki sıranın 1:1 kesiti
    Serdar'a gösterildikten sonra.

## Ek: bu planın sınırları

- Hiçbir betik çalıştırılmadı; [tahmin] ve [hesap] etiketli rakamlar ölçüm değildir.
- Dayanak'taki Merkez kayıtları (1087 px, 25,4 mm, 1,5 mm, 0,2 mm, Printify sayfaları) bu oturumda doğrulanmadı; depoda
  bu ürüne ait kayıt bulunamadı (scripts/printify, docs ve scripts/ay_takvim içinde arandı).
- ornek-tek-doku dalı (tek_doku.py, HALKA_BLUE_16x20.png) okunmadı; plan o dala dayanmıyor.
- Bağımsız inceleme: 2 tur (tek ajan, tur başına ayrı; işi yapmamış). 1. tur 23 bulgu (2 yüksek), 2. tur 20 bulgu (2 yeni
  yüksek: küçük burç yeri ve grup merkezi bağı). Hepsi plana işlendi. 2. turdan SONRA yapılan düzeltmeler yeniden
  incelenmedi (tur sınırı 2); Merkez kontrolünde öncelik: bölüm 3.3 (halka_r / grup_r, kucuk_u), 3.4 (üç fark), 4.1 - 4.2,
  6.2 - 6.3 ve soru 4 - 7.
