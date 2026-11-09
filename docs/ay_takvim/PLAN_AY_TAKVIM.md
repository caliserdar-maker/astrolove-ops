# PLAN: 2027 çift ay takvimi, altın doku (1. adım: yalnız plan)

Tarih: 10 Kas 2026. Kapsam: yalnız kod okuması. Üretim, görsel, Etsy, Actions koşusu yok.
Bu oturum Drive'ı, artifact'ları ve görselleri GÖRMEDİ. Drive ile ilgili her bilgi "koddan, Drive'da doğrulanmadı" anlamındadır.
Tek bağımsız inceleme yapıldı (1 tur); bulguları bu sürüme işlendi.

## Okunan ref'ler

| Kısaltma | Dal | sha | Okunan yer |
|---|---|---|---|
| MAIN | main | 75a4cba34a6c | .github/workflows, docs |
| M | bizim-yilimiz | d1e484c02f35 | motor_gpt/ (poster motoru). Bu plandaki M satır numaraları bu sha içindir |
| SG | siparis-gpt | 6da763aa5b98 | motor_gpt/ (ornament'in sabitlediği motor commit'i) |
| SGC | siparis-gpt içi commit | d2b414ee270e | canlı sipariş pini (MAIN siparis-giris.yml:49) |
| O | ornament-printful-katalog | c950151627 | scripts/printful/, .github/workflows/ornament-78-uretim.yml |
| V3 | bizim-yilimiz-v3 | b90f3341eb70 | kod/by_poster.py, BENIOKU.md |
| TD | ornek-tek-doku | 2a08a78216ca | motor/tek_doku.py |
| DA | doku-ai | 2b693208d84c | motor/doku_ai_sayfa.py, doku_ai/ dosya listesi |
| DG | doku-ai-girdi | 68eca14430b3 | AI_CIKTI/NOT.md, CANVA_CIKTI/NOT.md |
| - | kaynak-isim-plaka 9b10d3f, db-pw-altin 40fd6b9a0497, motor 50919ef959c3, inceleme/motor-kaynak 238f2287dcda, inceleme/motor-varlik 24caa0fbec38 | | yalnız uç commit başlığı ve dosya listesi; içerik okunmadı |

Ölçüm (git diff): golge_motor.py, vektor_yuzey.py, alfa_temizle.py, uret_tam.py, KILIT_GPTGIRDI.json, kure/, palet/, girdi/, font/, amp/, yerlesim78.json, cember.json, KATMAN_MANIFEST.json M, SG ve SGC'de AYNI. M ile SG arasında 6 dosya FARKLI: db_pw_uret.py, kapi_db_pw.py, olcu.py, olustur_alfa_sablon.py, renk_uyum.py, siparis_kapi.py (M'de tarih satırı öğesi var, SG / SGC'de yok). SGC ile SG farkı yalnız olcu.py.

## 1. Yeni altın doku kaynakları

Özet: kodda İKİ ayrı "yeni" altın var ve hangisinin kastedildiği doğrulanmadı (soru 1):
- (A) Poster motoru `motor_gpt/` (7-9 Eki): sembol = ChatGPT yüzeyli hazır katman; yazı ve tek burçlar = font / şekil + hesaplanan altın. Canlı sipariş hattı ve ornament bunu kullanıyor. Kod yorumlarında "yeni altin" adı bu yolda geçiyor (M motor_gpt/db_pw_uret.py:1; MAIN siparis-giris.yml:3).
- (B) DOKU_AI harf sayfaları (4 Eki): altın dokuyu ChatGPT / Canva AI üretmiş, harf şekli fonttan. Hazır altın dokulu HARF SAYFALARI repoda var. Bunları tüketen kod sonraki dallarda bulunamadı.

**Özgün sembol (78 çift)**
- Dosya: `<ÇİFT>_ana.png` + `<ÇİFT>_ana.png.json`. RGBA PNG: RGB = ChatGPT altın yüzeyi, A = alfa (M motor_gpt/BENIOKU.md:6-7; M motor_gpt/KATMAN_MANIFEST.json `_aciklama`).
- Drive klasör adı (koddan: M BENIOKU.md:6): ANA_SEMBOL78_KATMAN_20261008. İndirme satırları: MAIN bizim-yilimiz-ornek.yml:61; MAIN siparis-giris.yml:173.
- Boyut çifte göre değişir, 7200x10800 poster ölçeğinde. CANCER_LIBRA: 4141x3932 px, tuvalde x 1531 y 2070; kenar payı 300 px; paysız kutu 3541x3332 (manifest kaydı). 78 çiftin 76'sında pay 150, 2'sinde 300 (manifest sayımı).
- .json alanları (kodun okuduğu): x, y, w, h, kaynak_x, kaynak_y, kaynak_w, kaynak_h (M motor_gpt/siparis_uret.py:37-43). "pay" manifestte.
- Ayrı alfa (yüzeysiz): repoda `motor_gpt/girdi78/ana/<çift>_alfa.png`, 78 dosya, 8 bit gri. CANCER_LIBRA 8185x7702 px (dosya başlığı ölçümü).

**12 tek burç sembolü**
- Yol A: `motor_gpt/girdi/KUCUK_1.png` (3105x2460) ve `KUCUK_2.png` (2823x2409), RGB sayfa; kırpma kutuları M motor_gpt/olustur_alfa_sablon.py:17-22. Yalnız ŞEKİL verir; altın motorla hesaplanır. Yol A'da hazır dokulu tek burç dosyası yok.
- Yol B / eski: Canva AI dokulu tek burç sayfaları `CANVA_CIKTI/DOKU_AI_KUCUK_1_CANVA.jpg`, `..._KUCUK_2_CANVA.jpg` (DG; 4 Eki; içerik görülmedi).
- Eski altın tek burç dosyaları `<burç>_symbol_gold.png` (RGBA): Drive'dan joker desenle indiriliyor, kod 12 dosya bekliyor (O ornament-78-uretim.yml:264, 273). Kod notu: "ARCHIVE/LEGACY_COMPONENTS/zodiac_symbols_gold ... posterdeki tek burç glifleri" (O scripts/printful/ornament_ornek.py:9). Ornament motoru bunların yalnız alfasını alıp altını motorla yeniden üretiyor (O ornament_motor.py:282, 419-424).

**Harfler**
- Yol A: hazır harf görseli yok; yazı her koşuda fonttan çizilir (bkz. 2). Tek istisna "&": `motor_gpt/amp/AMP_ALFA.png` (16 bit, 565x554) + `AMP_YUZEY.png` (RGB, ChatGPT yüzeyi), Serdar onayı 8 Eki (M BENIOKU.md:16-21).
- Yol B: hazır altın dokulu harf sayfaları VAR.
  - Üreten betik: DA motor/doku_ai_sayfa.py:2 ("Serdar 4 Eki, YENI YONTEM: altin dokuyu ChatGPT uretir, harf sekli bizden").
  - Karakterler (DA doku_ai_sayfa.py:25-27): İSİM seti A-Z, Ç Ğ İ Ö Ş Ü, & ' - . (Cinzel 500, punto 408). TAGLINE seti A-Z, a-z, Türkçe harfler, 0-9, . , ' ! ? & - : ; (EB Garamond Italic, punto 372). Ölçek: 24x36 in, 300 dpi, 1:1 (DA doku_ai_sayfa.py:4-6).
  - Dosyalar: `doku_ai/CILA/DOKU_AI_ISIM_1..3_CILA.png`, `DOKU_AI_TAGLINE_1..4_CILA.png`, `DOKU_AI_MASKE_1_CILA.png`; glif konumları `doku_ai/SAYFALAR/*.json` (DA dosya listesi). Uç commit başlığı: "son cila - Canva dokulu 8 sayfa renk/parlaklik esitleme" (4 Eki).
  - Ham çıktılar: DG AI_CIKTI (ChatGPT, 2048x1856 RGBA, NOT.md) ve DG CANVA_CIKTI (NOT.md: "Doku kaynagi Canva AI (4 Eki 2026, Serdar karari)").
  - Bu sayfaları okuyup isim / mesaj basan kod: **bulunamadı** (DA motor/*.py, MAIN, SG, M, O içinde arama 0 sonuç). Yol A harf için bunları kullanmıyor.
  - Ayrıca 12 dosya `motor/varlik/isim_plaka/<burç>_name_gold.png` (dal kaynak-isim-plaka, 4 Eki; içerik okunmadı).
- Fontlar repoda: `motor_gpt/font/Cinzel.ttf`, `motor_gpt/font/EBGaramond-Italic.ttf`.

**Yol A'da altını üreten varlıklar**
- `motor_gpt/kure/k4.npy` (ışık küresi haritası, 16,8 MB), `motor_gpt/palet/chatgpt_altin.png` (RGBA 1461x1077, renk paleti), `motor_gpt/KILIT_GPTGIRDI.json` (kilitli ayarlar; "onay: 7 Eki 2026, deneme 11"), `motor_gpt/ref/ref.png` (referans poster; yıldız ve palet için: M uret_tam.py:113, 138).
- Palet kullanımı: M motor_gpt/uret_tam.py:143-147.

**Tarihler (kod yorumlarından)**
- 3 Eki: "tek doku" modeli (TD). 4 Eki: DOKU_AI harf sayfaları (DA). 7 Eki: KILIT onayı ve vektör yüzey (M vektor_yuzey.py:1). 8 Eki: ChatGPT sembol katmanı + motor + renk uyumu = "yeni yol" (M BENIOKU.md:1-4). 9 Eki: DB/PW "yeni altin" (M db_pw_uret.py:1; MAIN siparis-giris.yml:195). 14 Eki: v3 karo dokusu (V3). 3 Kas: ornament Yol A fonksiyonlarını küçük boyda kullandı (O ornament_motor.py:2-5).
- İlk ekleyen commit'ler: **bulunamadı** (dallar sığ çekildi).

**Eski doku yolları (kodda duruyor)**
- Eski sipariş yolu (CI/WP): MAIN siparis-giris.yml:84. Hâlâ etkin.
- "Tek doku" modeli (ana sembolden ölçülen boru profili + kabartma): TD motor/tek_doku.py:1-15; ornament'in ilk altın denemelerinde kullanıldı (O ornament_altin.py:9-11).
- Karo doku (Bizim Yılımız v3): `z/Altin_1024x1024/*_Altin_1024.png` + font maskesi + pah + gölge (V3 kod/by_poster.py:141-176, 432-443). Ayrı bir altın.

**`<ÇİFT>_std_alfa.npz` ve `ek/**`**
- std_alfa: standart (isimsiz) posterdeki öğe yerleri. Yalnız kapı (a) için kullanılır (M siparis_kapi.py:32-35). Doku taşımaz. Kodun okuduğu anahtarlar: `_ad`, `_konum`, isim1, isim2, sonsuz, kucuk1, kucuk2, tagline (dosyada başka anahtar olup olmadığı görülmedi).
- ek/: tek dosya, bir poster görüntüsü. Motor dosyayı açar; kilitli ayarda (yildiz = refkopya) değeri kullanılmaz (M BENIOKU.md:8; M uret_tam.py:52, 60). Ay takvimi için gerekmez.

## 2. Yazıya altın doku (Yol A, bugün çalışan)

Yöntem: font + maske + hesaplanan altın.

Adımlar (poster, 7200x10800 tuval):
1. Metin alfası: Pillow ile fonttan. İsim: Cinzel, ağırlık 500, `upper()`; tagline: EB Garamond Italic, ağırlık 400 (M olustur_alfa_sablon.py:38-46, 65-77, 106-111).
2. Gölgeleme: alfadan eğim alanı (`egim_tup`), ışık küresiyle parlaklık (`golgele_g`) (M uret_tam.py:149-211; M golge_motor.py:62-65). Kilitli ayarda gürültü, benek ve parıltı KAPALI (g, m1, m2, parilti = 0; O ornament_motor.py:130 bunu doğruluyor). Yani yüzey görünümü = eğim profili + ışık küresi + gren.
3. Parlaklık eşitleme: öğenin ortancası ana sembolün ortancasına tek çarpanla (ayar `esit = kazanc`) (M uret_tam.py:300-309).
4. Renk: parlaklık -> RGB haritası, ana sembol alfasının gölgelenmiş hali + ChatGPT paletinden (M uret_tam.py:250-252, 310).
5. Zemine bağlı etkiler: düşen gölge (sigma 16, kayma 10 / 16 px), temas gölgesi, yansıma 0,15, ışıma 0,04, kenar yumuşatma 0,5, gren genliği 1,0 (gren bulanıklığı sigma 0,8) (M KILIT_GPTGIRDI.json; M uret_tam.py:256-267, 324-327, 345-347, 360-370, 389-391).
6. "Tek doku" eşitleme: her öğenin Lab ortancası ana sembolün ortancasına kaydırılır (M renk_uyum.py:57-63).

Girdi / çıktı: `siparis_uret.py ÇİFT İSİM1 İSİM2 MESAJ_B64 KATMAN_PNG İŞ_KLASÖRÜ` -> 7200x10800 JPEG + seçilen ölçü (M siparis_uret.py:3-6).

Boy ve aralık (koddan):
- İsim: büyük harf yüksekliği 298 px (hesap: 300 dpi'de 25,2 mm), başlangıç punto 405; sığmazsa iki isim birlikte küçülür; kodda alt sınır yok (M olustur_alfa_sablon.py:23-25, 74-77).
- Tagline: 372 punto; sığmazsa 4'er punto küçülür; "&"siz yolda alt sınır yok, "&"li yolda punto tabanı 200 (M olustur_alfa_sablon.py:106-111; M amp_tagline.py:75); en çok 35 karakter (M siparis_uret.py:17).
- Harf aralığı: isim ve tagline'da ek aralık yok. Tarih satırında var: Cinzel 500, 166 punto, harf arası 36 px (M olustur_alfa_sablon.py:117-134).
- İkinci satır: yalnız M'de tagline altına tarih satırı çizilir, satır arası 378 px (M olustur_alfa_sablon.py:114-134); SG / SGC'de yok. Serbest metnin 2-3 satıra bölünmesi: **bulunamadı**.

Karakterler:
- Yol A'da karakter denetimi: **bulunamadı** (fontta olmayan harf için kapı yok).
- Font kapsamı (ölçüm, font cmap tablosu): Cinzel ve EB Garamond Italic'te A-Z, a-z, 0-9, yaygın noktalama, Türkçe ve Batı Avrupa aksanlı harfler var. Kiril: Cinzel'de yok, EB Garamond Italic'te var. Harflerin görünümü görülmedi.
- Ornament sipariş hattı kuralı: isimde yalnız `[A-Za-z'-]`, gerisi DUR (O scripts/printful/siparis_girdi.py:6-8, 29).

Kapılar (M siparis_kapi.py; ad, eşik):
- a: ana bölgesi standart posterle aynı; bulanık fark ortalaması <= 0,5, %99,9 <= 10, küme <= 0,5 x kalınlık^2 (:3-5, 53-54).
- b: öğeler arası dE00 (ana ile) <= 1,0 (:65; M renk_uyum.py:126).
- c: isim-burç eşleşmesi (:7, 89-90). d: yazım; isim ve tagline alfası bağımsız çizimle IoU >= 0,985 (:8, 173). e: dikiş (:9).
- f: "&" IoU >= 0,90, leke, dE00 <= 1 (:174).
- g: teslim dosyası; < 20 MB, tam piksel, 4:4:4, 300 dpi, halka <= 0,10 (:10; M BENIOKU.md:30'da halka için 0,075 yazıyor, iki değer var). h: öğeler çerçeve içinde, >= 300 px boşluk (:11). i: yöntem B dikişi.
- DB/PW ek: L leke (|r| > 6 kümesi <= 0,5 x kalınlık^2), K kesik uç (M kapi_db_pw.py:3-8).
- Ornament (küçük boy): son dosyada dE00 <= 2,0; kontrast ortancası >= 4,5; leke 0; küçük burç / logo IoU >= 0,98; isim / tarih alfa farkı <= 0,035 (O ornament_motor.py:782-791).

## 3. Ay takvimine uygulama

Girdi ölçüleri (kaynak: Merkez görev metni, bu oturumda ölçülmedi): sayfa 18x24 in, oran 3:4; ay adı yazı boyu yaklaşık 7 mm, büyük harf yaklaşık 4,5 mm; isim ve kişisel metin boyu verilmedi.

Ortak bulgu (Yol A): motor sabitleri POSTER pikseline göre (yön bulanıklığı sigma 6 px: M golge_motor.py:72; kenar 0,5 px ve gren: M KILIT_GPTGIRDI.json, M uret_tam.py:390). Ornament'te çözüm: öğeyi tam 10 kat büyük çiz, motorla gölgele, doğrusal ışıkta alfa ağırlıklı küçült (O ornament_motor.py:389-407, 455-482).

Bilinen en küçük boy (koddan, hesap; 300 dpi; 10 kat çizimle üretildi):
- Cinzel büyük harf 28,2 px = 2,39 mm (O ornament_ornek3.py:39). Kod notu 2,38 mm'yi alt kural olarak anıyor (aynı satır: "28.07 = 2.377 mm < 2.38"); üretim kapısı değil.
- EB Garamond Italic "T" yüksekliği yaklaşık 24 px = 2,03 mm (O ornament_ornek.py:46-47; O ornament_motor.py:416).
- "Güvenli alt sınır" adlı üretim kapısı: **bulunamadı**.

(a) Ay adları JAN ... DEC
- Yol A ile: kullanılabilir, ornament yöntemiyle. Hesap: 4,5 mm = 300 dpi'de 53 px; bu, ornament'te üretilen 28,2 px'ten büyük. Çizim katsayısı seçeneği: poster ölçeği 298 px için k = 5 -> 266 px, k = 6 -> 319 px; ornament emsali 282 px (hesap). k örnekte ölçülerek seçilir.
- Yol B ile: İSİM sayfalarında A-Z var; JAN ... DEC harfleri kapsanıyor. Sayfalar 408 punto (24x36 ölçeği); 53 px'e yaklaşık 5-6 kat küçültme gerekir (hesap). Küçültülmüş hazır dokunun görünümü denenmedi.
- Döndürme: iki yolda da döndürülmüş yazı desteği **bulunamadı**. Yol A'da ışık yönü ve gölge kayması sabit (M KILIT_GPTGIRDI.json golge_dx / golge_dy); doğru sıra alfa büyük ölçekte döndürülür, SONRA gölgelenir (koddan çıkarım, denenmedi). Yol B'de hazır dokulu harfi döndürmek dokudaki ışık yönünü de döndürür.
- Eksik: döndürme adımı; döndürülmüş alfa için yazım kapısı; 12 küçük öğede dE00 ölçümü (ornament en az 200 çekirdek piksel istiyor: O ornament_motor.py:520-524; 53 px yazıda bu sayı ölçülmeli).

(b) İki isim (büyük harf, tek satır)
- Yol A: kullanılabilir, posterle aynı çizim. Yol B: A-Z ve Türkçe büyük harfler sayfada var; başka aksanlı harf (ör. É, Ñ) sayfada yok.
- Eksik: ay takvimi tuvalinde boy ve konum tanımı.

(c) Kişisel metin (0-3 satır)
- Yol A: tek satır kullanılabilir (EB Garamond Italic; küçük harf ve noktalama fontta var). Yol B: TAGLINE sayfalarında küçük harf, rakam ve 9 noktalama işareti var.
- Eksik: satıra bölme, satır aralığı, satır başına karakter sınırı (poster: tek satır 35), karakter kapısı, küçük boyda "&" davranışı (posterde ChatGPT "&" görseli kullanılıyor; denenmedi).

Küçük boyda ve döndürmede doku bozulur mu: koddan kesin cevap **bulunamadı**. Bilinen: ornament küçültmeden sonra kalan greni ölçüp raporluyor (O ornament_motor.py:487-489) ve küçük öğelerde parlaklık eşitleme onaylı sapmayla `goz` yapıldı (O ornament_motor.py:16, 231). Örnek üzerinde ölçülmeli.

## 4. Sembol yerleştirme

- Dosya: `<ÇİFT>_ana.png` (RGBA; yüzey + kendi alfası). Yerleştirme için ayrı alfa gerekmez.
- Yol A'da renk haritası ve parlaklık hedefi için ayrıca posterin ana alfası (`girdi78/ana/<çift>_alfa.png`) motorla gölgelenir (M uret_tam.py:250-252, 284; O ornament_motor.py:126-127, 221). Yani yazıyı Yol A ile altınlamak için bu alfa da gerekir.
- Poster yöntemi: katman olduğu gibi, json'daki x / y konumuna bindirilir; ölçekleme yok (M siparis_uret.py:63-67).
- Başka tuval (ornament): eş oranlı küçültme; RGB alfa ile ön çarpılıp INTER_AREA, sonra alfaya bölünür (O ornament_ornek.py:76-82); merkezleme alfa > 0,5 kutusuna göre (O ornament_motor.py:332-333). Katman kenar payı içerdiği için kutu alfadan alınmalı.
- Ornament ana sembolde ön küçültme ve delik kapama uyguladı (O ornament_motor.py:264-267). Ay takviminde gerekip gerekmediği örnekte ölçülmeli.
- Şekil kuralı: yalnız eş oranlı küçültme; büyütme, kırpma, yeniden çizim yok.

## 5. Üretim yolu: iki seçenek

**S1: mevcut motoru (siparis_uret.py / uret_tam.py) çağıran küçük betik**
- Artı: onaylı zincir aynen; kapılar hazır. uret_tam.py öğe listesini ve konumlarını ALFA dosyasından okur (M uret_tam.py:14-15), ek zemin girişi var (ZEMINLER, :42-49); sabit yollar iş akışında bağlantıyla çözülüyor (MAIN siparis-giris.yml:181-183).
- Eksi: tuval 7200x10800 sabit (M uret_tam.py:9); 'ana' öğesi zorunlu (:250); motor kendi zeminini ve yıldızlarını çizer (:19, 113); 3:4 çıktı yalnız poster yerleşiminin yeniden çerçevelenmesi (SG motor_gpt/olcu.py yöntem B); küçük yazı için k kat çizim yok; döndürme yok. Ay takvimi için motor dosyalarında değişiklik gerekir (onaylı sipariş hattına dokunur).
- Kapanan kapı: a (standart poster karşılaştırması) uygulanamaz.

**S2: motorun fonksiyon ve varlıklarını okuyan bağımsız küçük betik (ornament_motor.py emsali)**
- Artı: 3 Kas'ta küçük yazıda kullanıldı; motor dosyaları değişmez (sabit commit'ten okunur); tuval, zemin ve yerleşim serbest; k kat çizim ve döndürme eklenebilir.
- Eksi: emsalde uret_tam.py'nin gölgeleme döngüsü ve palet çıkarımı betiğe elle kopyalanmış (O ornament_motor.py:148-151, 160-203); eşdeğerlik testi gerekir. Zemine bağlı etkiler (düşen gölge, yansıma, ışıma) yeniden kurulmalı; ornament bunları dışarıda bıraktı (O ornament_motor.py:13). Yeni kapılar yazılmalı.
- Yeni dosyalar (main'e girecek, 2. adımda):
  - `scripts/ay_takvim/ay_takvim_ornek.py` (yerleşim + altın öğeler + birleştirme)
  - `scripts/ay_takvim/ay_takvim_kapi.py` (kapılar, PASS/FAIL)
  - `scripts/ay_takvim/test_ay_takvim.py` (bilinen PASS + bilinen FAIL; kopyalanan gölgeleme için eşdeğerlik testi)
  - `.github/workflows/ay-takvim-ornek.yml` (yalnız workflow_dispatch; Etsy yok)
- Bağımlı dosyalar, sabit motor commit'inden (emsal listesi O ornament_motor.py:50-51, 126-127): KILIT_GPTGIRDI.json, golge_motor.py, vektor_yuzey.py, alfa_temizle.py, uret_tam.py, renk_uyum.py, olustur_alfa_sablon.py, kure/k4.npy, palet/chatgpt_altin.png, yerlesim78.json, cember.json, girdi78/ana/<çift>_alfa.png; ayrıca font/. Drive'dan: `<ÇİFT>_ana.png` + `.json`.
- Motor commit'i: SG 6da763a (ornament emsali) ya da SGC d2b414e (canlı sipariş). Çekirdek dosyalar ikisinde aynı (ölçüm); seçim soru 7.
- Actions ortamı: örnek iş akışı MAIN bizim-yilimiz-ornek.yml (motor dalını sabit sha ile ayrı klasöre alma :30-33, rclone :39-56, Drive kopyası :58-61, paket kurulumu :68-69). Poster ortamı: numpy 2.5.3, opencv-python-headless 5.0.0.93, pillow 12.3.0, scipy 1.18.1, scikit-image 0.26.0, potracer 0.0.4 (MAIN siparis-giris.yml:185). Ornament aynı motoru pillow 11.0.0 / numpy 2.5.4 ile koşturdu ve yazı düzeni motorunu (raqm) sert denetledi (O ornament-78-uretim.yml:250; O ornament_motor.py:82, 95-101).
- Süre: ölçülmüş süre **bulunamadı** (koşu logları okunmadı). Emsal iş akışı sınırı 60 dk (MAIN bizim-yilimiz-ornek.yml:28).
- Eklenecek kapılar (eşikler emsalden; örnekte tipik ve en kötü veriyle ölçülüp Serdar onayıyla kesinleşir): tek doku dE00 (sembol ile her altın öğe) <= 1,0 hesapta, <= 2,0 son dosyada; yazım IoU >= 0,985 (döndürülmüş dahil); sembol şekli IoU; ay diski ve gün rakamı piksellerinde altın yok; düz altın renk yok (öğe içi parlaklık yayılımı alt eşiği); metin 0 / 1 / 2 / 3 satır dört durumda taşma 0.
- Uygulanmayan kapılar: a (standart poster), e / i (dikiş), g (Etsy teslim dosyası).

**Yol B kullanılacaksa (soru 1'e bağlı):** S2 içinde yazı adımı değişir: harf dokusu DOKU_AI sayfalarından, şekil fonttan. Bunu yapan kod bulunamadığı için yeniden yazılması gerekir; sayfalardaki karakter seti dışındaki harfler basılamaz.

**Öneri: S2, Yol A.** Gerekçe: bugün çalışan ve 3 Kas'ta küçük yazıda kullanılmış tek yol; onaylı sipariş motoruna dokunmuyor; S1 motor değişikliği ister. Bu öneri soru 1'in cevabı "Yol A" ise geçerlidir.

## 6. Riskler ve Serdar'a sorular

Riskler
1. "Yeni altın doku" tanımı doğrulanmadı. Kodda en az beş altın var: poster motoru (7-9 Eki), DOKU_AI harf sayfaları (4 Eki), v3 karo dokusu (14 Eki), tek doku modeli (3 Eki), eski hazır altın dosyaları. Yanlış yol seçilirse örnek yine reddedilir.
2. "Bütün harfler yeni altın dokusuyla üretilmişti" ifadesi DOKU_AI harf sayfalarıyla (4 Eki) örtüşüyor olabilir; bugün çalışan sipariş hattı ise bu sayfaları kullanmıyor.
3. Yol A'da sembol yüzeyi ChatGPT görseli, yazı yüzeyi hesaplanmış altın (gürültü ve benek kapalı). "Tek doku" kapısı yalnız renk ortancasını (dE00) ölçer; doku benzerliğini ölçmez.
4. Zemin belirsiz. Motorun gölge, yansıma ve ışıması zemine bağlı.
5. Küçük yazıda (53 px) altın ayrıntısı küçültmede kaybolabilir; ölçülmeden "bozulmaz" denemez.
6. Döndürülmüş yazı iki yol için de yeni; emsal yok.
7. Pillow sürümü ve raqm yazı yerleşimini değiştirir (depo kuralı); poster 12.3.0, ornament 11.0.0 ile onaylandı.
8. 2027 ay evresi verisinin kaynağı repoda **bulunamadı** (main'de ay evresi hesabı ya da kütüphanesi yok); 2. adımda kaynağı yazılmalı.
9. Depo herkese açık: örnek görseller ve Drive kimlikleri dala girmemeli (ornament kuralı: O ornament-78-uretim.yml:9). Gözlem: O dalında `docs/ornament/kaynak/` altında 2 `_symbol_gold.png` dosyası duruyor (dosya listesi); bu kuralla çelişiyor görünüyor.

Sorular (her biri tek satır, önerili; görsel seçimler Serdar'ın kararıdır)
1. "Yeni altın doku" hangisi: (A) sipariş posterinin altını (ChatGPT sembol + motorla altınlanan yazı; ornament'te de kullanılan) mı, (B) 4 Eki DOKU_AI / Canva dokulu harf sayfaları mı? Öneri: A (bugün çalışan tek yol); B ise 2. adım uzar.
2. Zemin hangi renk(ler)? Öneri: örnek için tek zemin, posterdeki Midnight Blue (Yol A bu zeminde onaylı).
3. Fontlar posterle aynı mı (isim ve ay adları Cinzel büyük harf, kişisel metin EB Garamond Italic)? Öneri: evet (onaylı poster fontları).
4. Kişisel metin sınırı? Öneri: satır başına en çok 35 karakter (poster kuralı), en çok 3 satır (görev metni).
5. "MOON PHASES 2027" başlığı kalsın mı, altın dokulu mu? Öneri: kalırsa altın dokulu (mağaza kuralı: sayfadaki altın öğeler tek doku).
6. Küçük öğelerde parlaklık eşitleme: kilitli `kazanc` mı, ornament'te onaylanan `goz` mu? Öneri: `kazanc`; dE00 kapısı FAIL verirse Serdar'a sorulur.
7. (Merkez) Motor commit'i ve paket sürümü: SGC d2b414e + Pillow 12.3.0 (canlı poster ortamı) mı, SG 6da763a + Pillow 11.0.0 (ornament) mı? Öneri: canlı poster ortamı.
8. Örnek tek boy 18x24 in (5400x7200 px, 300 dpi hesabı) mi? Öneri: evet (görev metnindeki boy).

## Doğrulanmayanlar

- Drive'daki hiçbir dosyanın varlığı, sayısı, boyutu ve içeriği. Dosya adları ve biçimler yalnız koddan.
- Hiçbir görsel görülmedi (DOKU_AI sayfaları dahil; yalnız betik, NOT.md ve dosya listesi okundu).
- "Yeni altın doku"nun hangi yol olduğu (soru 1).
- kaynak-isim-plaka, db-pw-altin, motor, inceleme/motor-kaynak, inceleme/motor-varlik dallarının içeriği.
- DOKU_AI sayfalarını kullanan kodun başka (okunmayan) dallarda olup olmadığı; tüm dallarda içerik taraması yapılmadı.
- İlk ekleyen commit'ler (tarihler kod yorumlarından).
- Döndürme sırası (alfa döndür, sonra gölgele) koddan çıkarımdır, denenmedi.
- Font kapsamı yalnız karakter kodu düzeyinde ölçüldü.
- Merkez taslağındaki ölçüler (7 mm / 4,5 mm, 18x24 in) görev metninden alındı.
- `<ÇİFT>_ana.png.json` ve `_std_alfa.npz` dosyalarının gerçek içeriği (yalnız kodun okuduğu alanlar yazıldı).

"Bulunamadı" kalan madde sayısı: 8 (DOKU_AI sayfalarını kullanan kod; ilk ekleyen commit'ler; serbest metnin satıra bölünmesi; Yol A karakter kapısı; alt boy için üretim kapısı; döndürme desteği; küçük boyda bozulma cevabı; ölçülmüş süre). Ayrıca B kapsamı dışında: ay evresi verisi kaynağı (risk 8).
