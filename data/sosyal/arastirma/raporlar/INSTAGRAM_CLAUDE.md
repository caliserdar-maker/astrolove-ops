# AstroLoveArt Instagram Araştırması (Claude, bağımsız)

Tarih: 12 Ekim 2026 · Kapsam: yalnız Instagram · Veri: `sosyal_veri/instagram.csv` (11 Eki 2026) ve `screenshots/instagram_*`. Platformlar arası sinyal (Instagram kanıtı DEĞİL): `pinterest.csv`, `youtube_google_autocomplete.csv`, `pinc/S*/PIN_CIFT_*.csv`.

Okuma kuralı: "not shown / gösterilmedi" = toplanmadı, sıfır değil. Kaynakla doğrulayamadığım her şey **doğrulanmadı** diye işaretli. Satır referansı: `dosya / seed / data_type / rank → text`. Kaynak numaraları G bölümünde.

---

## Kısa sonuç (6 madde)

1. **Hashtag en fazla 5.** Instagram @creators hesabı Aralık 2025'te gönderi ve Reel başına hashtag sınırını kademeli olarak **5**'e indirdiğini duyurdu ve "az ve hedefli hashtag" önerdi; genel hashtag'lerin Explore'a yardım etmediğini, hatta zarar verebileceğini söyledi [S1][S2]. API belgesi hâlâ "30 hashtag" yazıyor [S6], ama uygulamada 5 geçerli kabul edilmeli. Önerim: **tam 5, hedefli** (B ve C bölümü).
2. **Aramada asıl iş açıklamada (caption).** Instagram: arama metin eşleşmesiyle çalışır, "anahtar kelime ve hashtag'leri yoruma değil açıklamaya koyun" [S8][S10]. Profil adı ve biyografi de aranan alanlar [S8]. Açıklamada **çift adı "{A} and {B}" biçiminde** ve **"compatibility"**, **"zodiac couple art"** geçmeli.
3. **İlk satır:** "more" düğmesinden önce yalnız **ilk iki satır** görünüyor; Instagram soru veya merak uyandıran açılış öneriyor, "kaydetmeye davet edin", "biyografideki linke yönlendirin" diyor [S18].
4. **Dağıtım sinyalleri (resmî):** Reels'te tam izleme, beğeni, paylaşma/gönderme ve ses sayfası ziyareti; Explore'da beğeni, kaydetme, paylaşma [S9]. Mosseri (Ocak 2025): en önemli üç sinyal **izleme süresi, beğeni, gönderme (send)**; takipçi olmayanlara ulaşmada gönderme biraz daha önemli [S17]. Sessiz, kenarlıklı, filigranlı, düşük çözünürlüklü, "çoğu yazı" Reel'ler daha az görünür [S9]. İlk 3 saniyede yakalama, en fazla 3 dakika [S10]. Bizim 24 sn Reel uygun.
5. **Verimizde en güçlü kelimeler:** (1) **"{A} and {B}"** çift adı, (2) **"compatibility"**, (3) **"zodiac couple"**, (4) **"zodiac art / astrology art"**, (5) **"personalized gift / couple gift"**, (6) **"anniversary gift"**. Instagram verimiz arama hacmi göstermiyor (öneriler hesap sonucu), bu yüzden sıralamada platformlar arası sinyal destek olarak kullanıldı ve öyle etiketlendi.
6. **Etsy tıklaması:** Açıklamada tıklanabilir link yok (yalnız Meta Verified abonelerinde test var [S28]). Biyografiye **5 linke kadar** eklenebiliyor [S27]. Her yeni gönderiyi Hikâye'de **link çıkartmasıyla** ilgili Etsy ilanına bağlamak, çift bazında doğrudan tıklama için belgelenmiş tek yol [S29].

---

## A. Instagram arama, Explore ve Reels dağıtımı neyi kullanıyor (kaynaklı)

| Öğe | Resmî bilgi | Bizim için anlamı | Kaynak |
|---|---|---|---|
| **Açıklama (caption)** | Aramada "yazdığınız metin açık ara en önemli sinyal"; sorgu kullanıcı adı, profil adı, biyografi, açıklama, hashtag ve yerlerle eşleşir. "Bir gönderinin Aramada bulunması için anahtar kelime ve hashtag'leri yoruma değil açıklamaya koyun." Creators blog: "Arama sonuçları metinle eşleşir, ilgili anahtar kelimeleri ekleyin." Instagram (Ağu 2026): açıklamalar "arama motorlarına içeriğin ne olduğunu söyler", "betimleyici ve ilgili anahtar kelime" kullanın. | Çift adı ve ürün kelimeleri açıklamada, yorumda değil. Kelime doldurma yok, doğal cümle. | [S8] [S10] [S18] [S20] |
| **Açıklama uzunluğu** | En fazla **2.200 karakter, 30 hashtag, 20 @etiket** (API referansı). Uygulamada hashtag sınırı 5 (madde aşağıda). | Şablonlarımız 278-512 karakter (78 çiftin hepsi hesaplandı). | [S6] |
| **İlk satır** | Yalnız ilk iki satır "more" öncesi görünür; soru, şaşırtıcı bilgi veya merak uyandıran açılış önerilir. | İlk satır = slayt 1'deki soru + çift adı. Karakter kesim noktası resmî olarak **doğrulanmadı** (ekrana göre değişir); ilk satırı 70 karakterin altında tuttum. | [S18] |
| **Hashtag** | @creators (Ara 2025): sınır kademeli olarak 5'e iniyor; "daha az (5'e kadar), daha hedefli hashtag" performansı artırabilir; genel hashtag'ler "Explore gibi yerlerde görünmenize yardım etmez", zarar verebilir. Mosseri 2025'te hashtag'lerin erişimi artırmadığını, içeriğin konusunu anlatmaya yaradığını söyledi (ikincil aktarım). İkincil kaynaklar (Nis ve Eyl 2026) sınırın hâlâ geçerli olduğunu, yoruma yazılan hashtag'lerin de sayıldığını söylüyor; bir kaynak 30 diyor (çelişkili, resmî dayanağı yok). | Tam 5 hedefli hashtag. #giftideas, #walldecor gibi genel ve dev etiketler yok. | [S1] [S2] [S3] [S4] [S5] |
| **Alt metin** | 2018'den beri otomatik alt metin ve yükleme sırasında özel alt metin var; amaç ekran okuyucu. API: `alt_text` en fazla **1.000 karakter**, yalnız görsel gönderi ve karusel görseli; **Reels ve Hikâye desteklenmiyor**. Uygulama içi karakter sınırı resmî olarak **doğrulanmadı** (Hootsuite "100" diyor, kaynaksız). Alt metnin Instagram aramasına etkisi resmî olarak **doğrulanmadı** (yalnız ikincil iddia). | Her karusel slaytına doğru betim + çift adı doğal biçimde. 142-268 karakter. Reels için alt metin planlamıyoruz. | [S6] [S22] [S23] [S24] [S26] |
| **Ekrandaki yazı, ses** | Reels sinyalleri: ses parçası, görsel, popülerlik. Ses sayfası ziyareti tahmin edilen eylem. Sessiz veya "çoğu yazı" olan Reel daha az görünür. Ekrandaki yazının veya sesin aramada okunduğu (OCR, transkript) resmî olarak **doğrulanmadı**. | Reel'de ses olmalı. Yazı kısa kalmalı, animasyon baskın. Anahtar kelimeyi ekrana değil açıklamaya güven. | [S9] |
| **İlk saniyeler, uzunluk** | "İzleyiciyi ilk 3 saniyede yakalayın"; öneri için Reel "3 dakika veya daha kısa" ve dikey tam ekran olmalı. 3 dakikaya kadar Reel Ocak 2025'te geldi. Profesyonel Panel ipucu (2024, ikincil aktarım): "30-60 sn Reel'ler daha iyi performans gösteriyor"; resmî metin **doğrulanmadı**. | 24 sn, 9:16, soru ilk karede: uyumlu. 30 sn'ye uzatmak için resmî gerekçe yok, deneme konusu. | [S10] [S21] [S30] [S31] |
| **Özgünlük, filigran** | Öneri için içerik özgün olmalı, görünür filigran olmamalı. Aynı içerik birden çok kez varsa yalnız orijinal önerilir. Nisan 2026: kural fotoğraf ve karusellere de genişledi; çoğunlukla başkasının işini yükleyen hesaplar öneriden çıkar. Kenarlık, filigran, altyazı veya kaynak belirtmek içeriği özgün yapmaz. | Tasarımlar bizim, sorun yok. Başka uygulamanın filigranı (ör. ücretsiz editör logosu, TikTok indirmesi) olmayan temiz dışa aktarım. Aynı Reel'i aynen iki kez yükleme. | [S9] [S11] [S12] [S13] [S14] |
| **Explore** | Popülerlik burada Feed'den çok daha önemli; tahmin edilen eylemler beğeni, kaydetme, paylaşma. Explore ve Reels, Öneri Kuralları'na tabi. | Kaydetme ve paylaşma doğal olarak istenmeli (C'deki "Save this for your next anniversary"). | [S9] |
| **Sinyal ağırlığı** | Mosseri: en önemli üç sinyal izleme süresi, beğeni, gönderme; "beğeni bağlı (takipçi) içerikte, gönderme bağlı olmayan içerikte biraz daha önemli". İçgörülerde ortalama izleme süresi, erişim başına beğeni ve erişim başına gönderme izlenmeli. | Ölçüt seti: izleme süresi, erişim başına kayıt, erişim başına gönderme, profil ziyareti, link tıklaması. | [S17] |
| **"Your Algorithm" konuları** | Aralık 2025: kullanıcı Reels'te Instagram'ın onun için çıkardığı konuları görüyor, konu ekleyip çıkarabiliyor; Explore'a genişlemesi planlandı. İçeriğin konuya nasıl eşlendiği resmî olarak **doğrulanmadı**. | Açıklamada konu adlarını açıkça yazmak (zodiac, astrology, couple gift) mantıklı ama etkisi doğrulanmadı. | [S34] |
| **Google'da görünme** | 10 Temmuz 2025'ten beri 18 yaş üstü, herkese açık profesyonel hesapların gönderi ve Reel'leri arama motorlarınca indekslenebiliyor; ayar varsayılan açık (Ayarlar → Gizlilik). Resmî Yardım sayfası çekilemedi; bilgi ikincil haberlerden. | Ayar açık kalmalı. Açıklamanın ilk cümlesi Google'da da başlık gibi okunabilir (doğrulanmadı). | [S25] [S26] |
| **Karusel** | Uygulamada 20 öğeye kadar (Ağu 2024). API'de 10 öğe; karuselin kırpması ilk görsele göre. API görsel oranı **4:5 ile 1,91:1** arası; yalnız JPEG. 3:4 uygulamada destekleniyor (Mayıs 2025) ama API'de yok. Karusel içi her görsele ayrı açıklama: Mayıs 2026'da **test**. | 4 slayt, 1080×1350 (4:5): API sınırı içinde. Metricool API ile yayınlıyorsa 3:4'e geçme. JPEG kullan. | [S6] [S7] [S19] [S32] [S33] |
| **Reel kapağı** | API: `cover_url` (JPEG, en fazla 8 MB, sRGB) veya `thumb_offset` (milisaniye). Reels için ayrı bir "başlık" alanı resmî belgelerde yok. Profil ızgarası Ocak 2025'te kareden dikey dikdörtgene geçti; tam oran resmî olarak **doğrulanmadı**. Uygulamada kapağı sonradan değiştirmek ve galeriden yüklemek mümkün (ikincil). | Kapak yazısı ortadaki güvenli alanda (C.6). | [S6] [S30] [S31] [S36] |
| **Yapay zekâ etiketi** | Meta, sektör standardı işaretler veya kullanıcı beyanıyla "AI info" etiketi koyuyor; yalnız yapay zekâ ile düzenlenen içerikte etiket menüye taşındı. Beyan etmemenin dağıtım cezası belgede yok. | Duvar sahnesi yapay zekâyla üretildiyse etiket çıkabilir. Etkisi **doğrulanmadı**. | [S35] |

---

## B. Verimiz: anahtar kelime ve hashtag öncelik sırası

### B.1 Veri hakkında önemli uyarılar

- Instagram'daki 24 tohum aramasının önerileri **hesap sonuçları** (kullanıcı adı + profil adı), arama terimi önerisi değil. Yani hacim göstermez; yalnız insanların bu ifadeyi **hesap adı olarak kullandığını** gösterir.
- Aramalar giriş yapılmış AstroLoveArt oturumunda, **"Senin için" (kişiselleştirilmiş)** sekmesinde yapıldı (`instagram_15_suggestions.jpg`, `instagram_16_suggestions.jpg`). Instagram arama sonuçlarını kişinin takip ve etkileşim geçmişine göre sıralıyor [S8]. Bu yüzden `zodiac couple / suggestion / 1 → astroloveart AstroLoveArt | Zodiac Couple Art` satırı **başkaları için sıralama kanıtı değildir**. "Kişiselleştirilmemiş" sekmesi toplanmadı.
- Hashtag sayıları görüntülenen metin: Türkçe "B" = bin. "4,400.000" gibi değerler dönüştürülmedi (README kuralı). Yorumum: yedi haneli gösterimler "B" ile gösterilenlerden büyük bir düzeyde; tam sayı **doğrulanmadı**. Gönderi sayısı erişim göstergesi değildir.
- Ekran görüntüsü kontrolü: `instagram_01/02/03/04/05/06/07/08/09/10_hashtag.jpg` ve `instagram_15/16_suggestions.jpg` CSV ile birebir aynı. Ekran görüntülerinde CSV'de olmayan **ilgili hashtag sayıları** da görünüyor; aşağıda "(ekran)" diye işaretli, kanıtı CSV satırından zayıf.

### B.2 Öncelik tablosu

Seviye: **A** = Instagram satırı + en az iki platformda çift düzeyinde güçlü destek · **B** = Instagram hashtag sayısı veya birden çok Instagram satırı, ürüne uyuyor · **C** = tek kaynak veya zayıf · **X** = kullanma.

| # | Kelime / hashtag | Seviye | Kanıt satırları | Gerekçe ve kullanım |
|---|---|---|---|---|
| 1 | **"{A} and {B}"** (çift adı, "and" biçimi) | A | Instagram: `gemini and leo / suggestion / 1 → gemini.and.leo gemini and leo`, `/ 2 → gemini_and_leo Gemini met Leo`; `cancer and libra / suggestion / 2 → cancerandlibra cancer & libra`, `/ 4 → whenacancerandlibra When a Cancer and a Libra...`; `scorpio and pisces / suggestion / 1 → scorpio.and.pisces.love Scorpio and Pisces`; `aries and leo / suggestion / 2, 5`; `taurus and virgo / suggestion / 1 → taurus.and.virgo`. Platformlar arası: YouTube `prefix / gemini and / 3 → gemini and leo`, `prefix / scorpio and / 2 → scorpio and pisces`; YouTube `pair` sorgularının 78/78'i öneri döndürüyor. | 5 çift tohumunun 5'inde de bu ifadeyle adlandırılmış hesaplar var. Açıklamada **en az 2 kez**, ilk satırda bir kez. Görsel üstünde "&" kalabilir; açıklamada "and" (veride en sık biçim). "&" ile "and"ın aramada eşdeğer sayıldığı **doğrulanmadı**. |
| 2 | **"{A} and {B} compatibility"** | A | Instagram: `zodiac compatibility / suggestion / 1-5` (5 hesap, ör. `/ 4 → zodiac_compatibility_tests Zodiac Compatibility`, `/ 5 → zodiac.signs.compatibility`). Platformlar arası (Instagram kanıtı değil): Pinterest `PIN_CIFT_*` öneri satırlarında **66/78 çift**, chip satırlarında 66/78 (benim yeniden sayımım; eksik 12: 11 cancer çifti + sagittarius-sagittarius); ör. `S2 / gemini and leo / suggestion / 2 → gemini and leo compatibility`, `S4 / scorpio and pisces / suggestion / 3`. YouTube `pair` 78/78 (benim sayımım; Pinterest raporunda 77/78 yazıyor), ör. `pair / cancer and libra / 2 → cancer and libra compatibility`. Google `seed / zodiac couple / 2 → zodiac couple compatibility`. | En tutarlı çapraz platform kelimesi. Açıklamada bir kez, "compatibility art" biçiminde (ürün iddiası değil, betim). Cancer çiftlerinde Pinterest öneri vermiyor (`S2 / cancer and libra / suggestion / not shown`), ama Instagram'da `cancer and libra` hesap sonuçları geldi; Instagram'da engel görünmüyor. |
| 3 | **zodiac couple** / **#zodiaccouple** | B | `#zodiaccouple / hashtag_posts / 1000+`; (ekran) `#zodiaccouples 14,7B`, `#zodiaccouplesigns 1000+` (`instagram_01_hashtag.jpg`); `zodiac couple / suggestion / 2-5` (zodiac_couple, zodiac.couple…); profil adımız `zodiac couple / suggestion / 1 → AstroLoveArt | Zodiac Couple Art`. Platformlar arası: Google `zodiac couple / 1 → zodiac couples`. | Ürünün tam kategorisi, etiket küçük ve özgül (hedefli). Hashtag olarak **#zodiaccouple** (CSV kanıtı). #zodiaccouples daha büyük ama yalnız ekran kanıtı; dönüşümlü denenebilir. |
| 4 | **zodiac art** / **#zodiacart**, **astrology art** / **#astrologyart** | B | `#zodiacart / hashtag_posts / 126B`, `#astrologyart / hashtag_posts / 130B`; (ekran) `#zodiacartwork 5000+`, `#astrologyartwork 5000+` (`instagram_02/03_hashtag.jpg`). | Orta büyüklükte, sanat niyetli etiketler. Açıklamada "zodiac couple art". |
| 5 | **personalized gift** / **#personalizedgift** | B | `#personalizedgift / hashtag_posts / 1,900.000`; (ekran) `#personalizedgifts 7,600.000`, `#personalizedgiftideas 53,4B` (`instagram_06_hashtag.jpg`); `personalized couple gift / suggestion / 1-5` (ör. `/ 2 → mysayang.shop MySayang | Personalized Couple Gifts`). Google `personalized couple gift / 1 → personalized couple gifts`. | Ürünün ayırt edici özelliği (isim + mesaj). Hashtag olarak tekil biçim (CSV kanıtı). |
| 6 | **couple gift** / **#couplegift** | B | `#couplegift / hashtag_posts / 448B`; (ekran) `#couplegifts 701B`, `#couplegiftideas 64,5B` (`instagram_04_hashtag.jpg`); `couple gift / suggestion / 1-5`. | Hediye niyeti. Karusel setinde. |
| 7 | **anniversary gift** / **#anniversarygift** | B (mevsimsel) | `#anniversarygift / hashtag_posts / 4,400.000`; (ekran) `#anniversarygifts 1,100.000`, `#anniversarygiftideas 169B` (`instagram_05_hashtag.jpg`); `anniversary gift / suggestion / 1-5`, `1st anniversary gift / suggestion / 1`. Platformlar arası: Pinterest Trends tepe ayı 2026-10 (Pinterest raporu, `anniversary gift / trend / 2026-10`). | Reel setinde (#couplegift yerine). Açıklamada "anniversary" kelimesi. |
| 8 | **engagement gift**, **wedding gift for couple** | C | `engagement gift / suggestion / 1-5`, `wedding gift for couple / suggestion / 1-5` (yalnız hesaplar, hashtag sayısı toplanmadı). | Açıklamada "anniversary, engagement or wedding" olarak geçiyor, hashtag yok. |
| 9 | **zodiac wall art**, **couple wall art** | C (Instagram'da zayıf) | Instagram: `zodiac wall art / suggestion / 1 → zodiact7677 THE ZODIAC WALL ART` (tek hesap), `couple wall art / suggestion / 1-3` (ilgisiz hesaplar). Platformlar arası: Google `zodiac wall art / 1`, `couple wall art / 4 → couple wall art etsy`. | Instagram'da kanıt zayıf. Açıklamada "for your wall" yeterli; hashtag yok. |
| X | **#zodiacsigns**, **#walldecor**, **#giftideas**, **#astrology** | X | `#zodiacsigns / 5,900.000` (ekranda ilgili: `#zodiacsignsmemes`, `#zodiacsignsbelike`, `instagram_07_hashtag.jpg`), `#walldecor / 11,100.000`, `#giftideas / 53,800.000`, `#astrology / not shown` (tam etiket listede yok; ekranda `#astrologymemes`, `instagram_08_hashtag.jpg`). | Çok genel, niyet karışık (mem içerikleri). @creators genel etiketlerin Explore'a yardım etmediğini söylüyor [S1]. |
| X | memes, friendship, tattoo, tarot; **newlywed gift**, **couple bedroom decor** | X | `gemini and leo / suggestion / 4 → astrology.vibes.uwu Leo, Gemini And Scorpio Memes`; Pinterest çift verisinde "tattoo" 76/78, "friendship" 70/78 (platformlar arası); `newlywed gift / not shown (Hiç sonuç bulunamadı)`, `couple bedroom decor / not shown`. | Ürün bunlar değil. "not shown" sıfır anlamına gelmez, ama kullanmak için kanıt yok. |

**Çift adına özel hashtag (#geminileo vb.):** Instagram'da bu etiketlerin sayısı **toplanmadı**. Kanıt olmadığı için önermiyorum; çift adı açıklama metninde.

### B.3 Önerilen 5'li hashtag setleri

```text
Karusel: #zodiacart #zodiaccouple #astrologyart #personalizedgift #couplegift
Reel:    #zodiacart #zodiaccouple #astrologyart #personalizedgift #anniversarygift
```
Dayanak: B.2 satır 3-7. Her set tam 5 [S1]. İkisi arasında tek fark, aynı metni iki kez kopyalamamak için.

---

## C. Şablonlar

Kurallar: açıklama ≤2.200 karakter, ≤5 hashtag [S1][S6]; karusel alt metni ≤1.000 (API) [S6]. 78 çiftin tamamı hesaplandı: karusel 464-512, Reel 272-304 karakter; ilk satır en uzun 69 (Sagittarius and Sagittarius); alt metin 139-268. Uzun tire yok, "+" yok, marka AstroLoveArt. Ürün iddiası yok (çerçeve, kâğıt, ölçü, fiyat, "best seller" yok; constellation yok).

### C.1 Karusel açıklaması

```text
{SIGN_A} and {SIGN_B}, as one? Swipe to see your shared symbol.

Our {SIGN_A} and {SIGN_B} zodiac couple art merges both signs into one gold symbol on navy. We add your two names and your personal message, so it becomes your own {SIGN_A} and {SIGN_B} compatibility art for your wall.

A personal zodiac gift for an anniversary, engagement or wedding. Save this for your next anniversary.

Make it yours on Etsy, link in bio.

#zodiacart #zodiaccouple #astrologyart #personalizedgift #couplegift
```
Dayandığı satırlar: B.2 #1, #2, #3, #4, #5, #7, #8. "Save this…" = Instagram'ın "kaydetmeye davet edin" önerisi [S18]; "link in bio" = "biyografideki linke yönlendirin" [S18].

### C.2 Reel açıklaması

```text
{SIGN_A} and {SIGN_B}, as one? Watch two signs become one gold symbol.

{SIGN_A} and {SIGN_B} compatibility art with your names and your personal message, designed by AstroLoveArt.

Make it yours on Etsy, link in bio.

#zodiacart #zodiaccouple #astrologyart #personalizedgift #anniversarygift
```

### C.3 İlk satır kuralı

- Biçim: `{SIGN_A} and {SIGN_B}, as one?` + kısa eylem cümlesi. Soru açılışı Instagram önerisi [S18], çift adı arama eşleşmesi [S8].
- Aynı çiftte karusel ve Reel ilk satırları farklı (Swipe / Watch), aynı metnin iki kez yayınlanmaması için.

### C.4 Karusel alt metni (her slayt)

```text
Slide 1. A navy background with gold zodiac art. Text on the image reads: {SIGN_A} & {SIGN_B}, as one? Zodiac art with your names & message. Swipe to reveal.

Slide 2. The {SIGN_A} sign and the {SIGN_B} sign in gold on navy, and one gold symbol that merges both signs. Below it, the sample names Emily and James joined by an infinity sign. Text on the image reads: Two signs, Your shared symbol, Your names, your message.

Slide 3. The personalized poster hanging on a wall. It shows the merged {SIGN_A} and {SIGN_B} gold symbol on navy with two names and a short message.

Slide 4. Close-up of the poster with the names Emily and James under the gold {SIGN_A} and {SIGN_B} symbol. Text on the image reads: Make it yours, AstroLoveArt, On Etsy.
```
Notlar: Slayt 1'in görsel içeriğini görmedim; "gold zodiac art" ifadesi gerçek görsele göre düzeltilmeli (alt metin görseli doğru anlatmalı [S22]). "∞" ekran okuyucuda farklı okunabileceği için "infinity sign" yazıldı. Reels'e alt metin API ile eklenemiyor [S6].

### C.5 Reel kapağı

```text
Ana yazı:  {SIGN_A_UPPER} & {SIGN_B_UPPER}, AS ONE?
Küçük:     ASTROLOVEART
```
- Görsel: birleşik altın sembol, lacivert zemin; 1080×1920 (9:16) JPEG, ≤8 MB, sRGB (API `cover_url`) [S6].
- Yazıyı dikey ortada tut: ızgara artık dikdörtgen ve kapağı kırpıyor [S30][S31]; tam kırpma oranı **doğrulanmadı**. Güvenli tercih: yazıyı merkezdeki 1080×1350 alanın içinde tut ve yayından önce profil ızgarasında kontrol et.
- Reels için ayrı "başlık" alanı resmî belgelerde yok [S6]. Başlık işlevini açıklamanın ilk satırı görüyor.

### C.6 Profil (biyografi) önerisi

Instagram: profil adı ve biyografide içerikle ilgili anahtar kelime olmalı [S8][S10]. Mevcut profil adı `AstroLoveArt | Zodiac Couple Art` (`zodiac couple / suggestion / 1`). Önerim (karar sende):
```text
Name: AstroLoveArt | Zodiac Couple Art
Bio:  Zodiac compatibility art with your names & message. Two signs, one gold symbol. Made by Lena & Serdar.
Links: Etsy shop (1. sırada)
```
Biyografi karakter sınırı resmî olarak **doğrulanmadı** (çekilmedi); bu metin 102 karakter.

---

## D. Doldurulmuş örnekler (karakter sayıları Python ile sayıldı)

### D.1 Gemini & Leo

Karusel (473 karakter; 1. satır 56):
```text
Gemini and Leo, as one? Swipe to see your shared symbol.

Our Gemini and Leo zodiac couple art merges both signs into one gold symbol on navy. We add your two names and your personal message, so it becomes your own Gemini and Leo compatibility art for your wall.

A personal zodiac gift for an anniversary, engagement or wedding. Save this for your next anniversary.

Make it yours on Etsy, link in bio.

#zodiacart #zodiaccouple #astrologyart #personalizedgift #couplegift
```
Reel (278 karakter; 1. satır 63):
```text
Gemini and Leo, as one? Watch two signs become one gold symbol.

Gemini and Leo compatibility art with your names and your personal message, designed by AstroLoveArt.

Make it yours on Etsy, link in bio.

#zodiacart #zodiaccouple #astrologyart #personalizedgift #anniversarygift
```
Alt metin (150 / 255 / 142 / 163):
```text
Slide 1. A navy background with gold zodiac art. Text on the image reads: Gemini & Leo, as one? Zodiac art with your names & message. Swipe to reveal.
Slide 2. The Gemini sign and the Leo sign in gold on navy, and one gold symbol that merges both signs. Below it, the sample names Emily and James joined by an infinity sign. Text on the image reads: Two signs, Your shared symbol, Your names, your message.
Slide 3. The personalized poster hanging on a wall. It shows the merged Gemini and Leo gold symbol on navy with two names and a short message.
Slide 4. Close-up of the poster with the names Emily and James under the gold Gemini and Leo symbol. Text on the image reads: Make it yours, AstroLoveArt, On Etsy.
```
Kapak (21): `GEMINI & LEO, AS ONE?`

### D.2 Cancer & Libra

Karusel (479; 1. satır 58):
```text
Cancer and Libra, as one? Swipe to see your shared symbol.

Our Cancer and Libra zodiac couple art merges both signs into one gold symbol on navy. We add your two names and your personal message, so it becomes your own Cancer and Libra compatibility art for your wall.

A personal zodiac gift for an anniversary, engagement or wedding. Save this for your next anniversary.

Make it yours on Etsy, link in bio.

#zodiacart #zodiaccouple #astrologyart #personalizedgift #couplegift
```
Reel (282; 1. satır 65):
```text
Cancer and Libra, as one? Watch two signs become one gold symbol.

Cancer and Libra compatibility art with your names and your personal message, designed by AstroLoveArt.

Make it yours on Etsy, link in bio.

#zodiacart #zodiaccouple #astrologyart #personalizedgift #anniversarygift
```
Alt metin (152 / 257 / 144 / 165):
```text
Slide 1. A navy background with gold zodiac art. Text on the image reads: Cancer & Libra, as one? Zodiac art with your names & message. Swipe to reveal.
Slide 2. The Cancer sign and the Libra sign in gold on navy, and one gold symbol that merges both signs. Below it, the sample names Emily and James joined by an infinity sign. Text on the image reads: Two signs, Your shared symbol, Your names, your message.
Slide 3. The personalized poster hanging on a wall. It shows the merged Cancer and Libra gold symbol on navy with two names and a short message.
Slide 4. Close-up of the poster with the names Emily and James under the gold Cancer and Libra symbol. Text on the image reads: Make it yours, AstroLoveArt, On Etsy.
```
Kapak (23): `CANCER & LIBRA, AS ONE?`

Not: Instagram'da `cancer and libra` aramasında 5 hesap sonucu var (`cancer and libra / suggestion / 1-5`); Pinterest'teki "cancer" boşluğu Instagram'da görülmedi.

### D.3 Scorpio & Pisces

Karusel (485; 1. satır 60):
```text
Scorpio and Pisces, as one? Swipe to see your shared symbol.

Our Scorpio and Pisces zodiac couple art merges both signs into one gold symbol on navy. We add your two names and your personal message, so it becomes your own Scorpio and Pisces compatibility art for your wall.

A personal zodiac gift for an anniversary, engagement or wedding. Save this for your next anniversary.

Make it yours on Etsy, link in bio.

#zodiacart #zodiaccouple #astrologyart #personalizedgift #couplegift
```
Reel (286; 1. satır 67):
```text
Scorpio and Pisces, as one? Watch two signs become one gold symbol.

Scorpio and Pisces compatibility art with your names and your personal message, designed by AstroLoveArt.

Make it yours on Etsy, link in bio.

#zodiacart #zodiaccouple #astrologyart #personalizedgift #anniversarygift
```
Alt metin (154 / 259 / 146 / 167):
```text
Slide 1. A navy background with gold zodiac art. Text on the image reads: Scorpio & Pisces, as one? Zodiac art with your names & message. Swipe to reveal.
Slide 2. The Scorpio sign and the Pisces sign in gold on navy, and one gold symbol that merges both signs. Below it, the sample names Emily and James joined by an infinity sign. Text on the image reads: Two signs, Your shared symbol, Your names, your message.
Slide 3. The personalized poster hanging on a wall. It shows the merged Scorpio and Pisces gold symbol on navy with two names and a short message.
Slide 4. Close-up of the poster with the names Emily and James under the gold Scorpio and Pisces symbol. Text on the image reads: Make it yours, AstroLoveArt, On Etsy.
```
Kapak (25): `SCORPIO & PISCES, AS ONE?`

---

## E. Resmî olarak belgelenmiş paylaşım uygulamaları (yalnız kaynaklı)

1. **Özgün içerik, temiz dosya.** Görünür filigran yok, başka platformdan indirilmiş video yok, aynı içeriği tekrar yükleme yok [S9][S10][S11][S12]. Kendi ekrandaki marka yazımız (ASTROLOVEART) bizim tasarımımız; Instagram'ın bunu "filigran" sayıp saymadığı **doğrulanmadı**.
2. **Reel biçimi.** Dikey tam ekran, ≤3 dk, ilk 3 sn'de yakalama [S10]; ses açık, kenarlıksız, yüksek çözünürlük, "çoğu yazı" değil [S9]. API: 9:16 önerilir, en az 3 sn, 23-60 FPS, ≤300 MB [S6].
3. **Deneme Reels (Trial reels).** Önce takipçi olmayanlara gösterilir; takipçiler akışta görmez. Yaklaşık 24 saat sonra izlenme, beğeni, yorum, paylaşım görünür. İsteğe bağlı: ilk **72 saatte** iyi performans gösterirse takipçilere otomatik paylaşım [S15]. Erişim: herkese açık ve **en az 1.000 takipçili** hesaplar (Mosseri, Temmuz 2025, ikincil aktarım) [S16]. API'de `trial_params` (`MANUAL` veya `SS_PERFORMANCE`) var [S6][S7]. Takipçi sayımız bilinmiyor (F).
4. **Açıklama.** Anahtar kelime ve hashtag açıklamada, yorumda değil [S8][S10]. İlk iki satır önemli; kaydetmeye davet ve biyografi linkine yönlendirme Instagram'ın kendi önerisi [S18].
5. **Hashtag.** En fazla 5, hedefli; genel etiket yok [S1][S2].
6. **Link seçenekleri.** Açıklamada tıklanabilir link yok; Meta Verified abonelerinde test ediliyor (ayda 10 link bildirildi, ikincil) [S28]. Biyografide 5 linke kadar (Profili düzenle → Bağlantılar → Harici bağlantı ekle) [S27]. Hikâye link çıkartması tüm hesaplara açık [S29]. Öneri: her gönderiden sonra Hikâye'de o çiftin **Etsy ilan linki** ile çıkartma.
7. **Hesap Durumu.** Profesyonel hesaplar içeriğin öneriye uygun olup olmadığını Ayarlar → Hesap → Hesap Durumu'nda görebilir, itiraz edebilir [S10][S12].
8. **Google indeksleme ayarı.** Herkese açık profesyonel hesaplarda varsayılan açık; açık kalmalı [S25][S26].
9. **API ile planlama (Metricool vb.).** 24 saatte API ile yayın sınırı belgede hem 100 hem 50 olarak geçiyor (çelişkili); güvenli sınır **50/gün** [S7]. Karusel API'de en fazla 10 öğe, açıklama yalnız karusel kapsayıcısında, alt metin yalnız görsellerde, JPEG zorunlu, görsel oranı 4:5-1,91:1 [S6][S7]. Ortak yayın (collab) en fazla 3 kullanıcı [S6].
10. **Yapay zekâ etiketi.** Yapay zekâ ile üretilmiş içerik "AI info" etiketi alabilir [S35].
11. **Sıklık ve süre (yalnız ikincil).** Profesyonel Panel ipuçları (2024, ekran görüntüsü aktarımı): ayda ortalama 10+ Reel, 30-60 sn Reel'ler daha iyi, 7 gün içinde yorumlara cevap [S21]. Resmî metin **doğrulanmadı**. Paylaşım saati için resmî kaynak bulamadım.

---

## F. Eksik veri ve açık sorular

1. **Takipçi sayısı ve İçgörüler** (erişim, kayıt, gönderme, profil ziyareti, link dokunuşu) verilmedi. Trial reels uygunluğu (≥1.000) ve performans kıyası buna bağlı.
2. **Kişiselleştirilmemiş arama** toplanmadı; tüm Instagram satırları giriş yapılmış hesabın "Senin için" sekmesinden [S8 kişiselleştirme]. Çıkış yapılmış veya "Kişiselleştirilmemiş" sekmesinde tekrar önerilir.
3. **Çift hashtag'leri** (#geminileo, #cancerlibra vb.) ve **#zodiaccompatibility**, **#zodiaccoupleart** sayıları toplanmadı.
4. Uygulama içi **alt metin karakter sınırı** ve Reels'te uygulama içi alt metin **doğrulanmadı**. Alt metnin Instagram aramasına etkisi **doğrulanmadı**.
5. Ekrandaki yazının ve sesin (OCR, transkript) aramada kullanıldığı **doğrulanmadı**.
6. Profil ızgarasının tam oranı (4:5 karusel ve 9:16 kapak nasıl kırpılıyor) **doğrulanmadı**; yayından önce ızgarada kontrol.
7. Instagram **Öneri Kuralları** sayfası (help.instagram.com/313829416281232) ve "Explore ve aramada görünmeme" sayfası çekilemedi (yalnız meta veri döndü). "Partnerine gönder" gibi çağrıların "etkileşim tuzağı" sayılıp sayılmadığı bu yüzden **doğrulanmadı**; şablonlara koymadım.
8. İşletme hesaplarında müzik kütüphanesi kısıtı **doğrulanmadı** (resmî kaynak çekilmedi). Reel'de ses olmalı [S9]; ticari kullanıma uygun ses seçimi ayrıca kontrol edilmeli.
9. Metricool'un Instagram için alt metin, kapak yükleme, trial reels ve 5 hashtag kontrolünü destekleyip desteklemediği **doğrulanmadı**.
10. "Your Algorithm" konularının içerikle nasıl eşlendiği **doğrulanmadı** [S34]; resmî duyuru sayfası çekilemedi.
11. Hashtag sınırı: resmî duyuru [S1][S2] ile API belgesi [S6] çelişiyor (5 ve 30). Uygulamada 5'e uy.
12. Slayt 1 görselinin içeriği bana gösterilmedi; alt metin 1 buna göre düzeltilmeli.

---

## G. Kaynaklar

Resmî (Instagram / Meta):
- [S6] Instagram Graph API, IG User Media referansı (açıklama 2.200 / 30 hashtag / 20 @; alt_text 1.000, Reels yok; Reels 3 sn-15 dk, 300 MB; cover_url; trial_params; collaborators 3; görsel 4:5-1,91:1): https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media
- [S7] Instagram Graph API, Content Publishing (karusel 10, 100 ve 50 yayın/24 saat çelişkisi, yalnız JPEG, trial reels): https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/content-publishing
- [S8] Instagram blog, Adam Mosseri, "Breaking Down How Instagram Search Works", 25 Ağu 2021: https://about.instagram.com/blog/announcements/break-down-how-instagram-search-works/
- [S9] Instagram blog, Adam Mosseri, "Instagram Ranking Explained", 31 May 2023: https://about.Instagram.Com/blog/announcements/instagram-ranking-explained
- [S10] Instagram Creators blog, "What Creators Need To Know About Instagram Recommendations", 30 Ağu 2022, güncelleme 25 Nis 2023: https://creators.instagram.com/blog/instagram-recommendations-eligibility-tips-creators
- [S11] Instagram Creators, "Helping Creators Find New Audiences" (öneri ve özgünlük), 30 Nis 2024: https://creators.instagram.com/recommendations-and-Originality
- [S12] Instagram Creators blog, "Rewarding original creators on Instagram", 30 Nis 2026: https://creators.instagram.com/blog/rewarding-original-creators-on-instagram
- [S15] Instagram Creators blog, "Trial reels", 10 Ara 2024: https://creators.instagram.com/blog/instagram-trial-reels
- [S22] Instagram blog, alt metin desteği, 28 Kas 2018: https://about.instagram.com/blog/announcements/improved-accessibility-through-alternative-text-support
- [S23] Instagram Yardım, otomatik alt metin (gövde metni çekilemedi, yalnız meta açıklama): https://help.instagram.com/iphone-app/503708446705527
- [S35] Meta, "Our Approach to Labeling AI-Generated Content and Manipulated Media", 5 Nis 2024 (güncellemeler Tem/Eyl 2024): https://about.fb.com/news/2024/04/metas-approach-to-labeling-ai-generated-content-and-manipulated-media/

Resmî açıklamaların güvenilir yayın aktarımı (ikincil):
- [S1] BetaNews, @creators hashtag açıklaması alıntılarıyla, 19 Ara 2025: https://betanews.com/2025/12/19/instagram-puts-a-limit-on-hashtag-usage/
- [S2] Social Media Today, hashtag sınırı 5, 18 Ara 2025: https://www.socialmediatoday.com/news/instagram-implements-new-limits-on-hashtag-use/808309/
- [S13] TechCrunch, toplayıcı hesaplar, 30 Nis 2026: https://techcrunch.com/2026/04/30/instagram-restricts-reach-of-content-aggregators-in-new-crackdown/
- [S14] TechCrunch, özgün içerik sıralama değişikliği, 30 Nis 2024: https://techcrunch.com/2024/04/30/instagram-is-updating-its-ranking-systems-to-surface-more-content-from-smaller-original-creators
- [S16] Social Samosa, trial reels 1.000 takipçi, 14 Tem 2025: https://www.socialsamosa.com/news-2/instagram-introduces-wider-access-trial-reels-9493132
- [S17] Social Media Today, Mosseri sıralama sinyalleri, 22 Oca 2025: https://www.socialmediatoday.com/news/instagram-shares-algorithm-insights-2025/738034/
- [S18] Social Media Today, Instagram'ın açıklama önerileri, 23 Ağu 2026: https://socialmediatoday.com/news/instagram-stresses-the-importance-of-captions/828554/
- [S19] Social Media Today, karusel içi ayrı açıklama testi, 11 May 2026: https://www.socialmediatoday.com/news/instagram-tests-captions-on-each-post-within-carousels/819917/
- [S20] Social Media Today, Instagram arama açıklaması, 25 Ağu 2021: https://www.socialmediatoday.com/news/instagram-outlines-how-its-search-algorithms-work-and-how-you-can-optimize/605596
- [S21] Social Media Today, Profesyonel Panel Reels ipuçları (ekran görüntüsü aktarımı), 10 Tem 2024: https://www.socialmediatoday.com/news/instagram-shares-tips-reels-creators/721054/
- [S25] PPC Land, Google indeksleme 10 Tem 2025: https://ppc.land/instagram-content-becomes-searchable-on-google-starting-july-10/
- [S26] The Week, Google/Bing indeksleme ve ayar yolu, 12 Tem 2025: https://www.theweek.in/news/sci-tech/2025/07/12/social-media-instagram-posts-and-reels-will-now-pop-up-on-google-and-bing-searches-how-to-enable-disable-this-setting.amp.html
- [S27] TechCrunch, biyografide 5 link, 18 Nis 2023: https://techcrunch.com/2023/04/18/instagram-takes-on-linktree-and-others-with-support-for-up-to-5-links-in-bio/
- [S28] PetaPixel, açıklamada link testi (Meta Verified), Mart 2026 (URL tarihi 16.03.2026): https://petapixel.com/2026/03/16/instagram-begins-testing-clickable-links-in-post-captions/
- [S29] Search Engine Land, Hikâye link çıkartması tüm hesaplara (sayfada tarih yok): https://searchengineland.com/instagram-opens-stories-link-sticker-to-all-users-375591
- [S30] Business Today, 3 dk Reels ve dikdörtgen ızgara, 21 Oca 2025: https://www.businesstoday.in/technology/news/story/instagram-head-announces-big-changes-3-minute-reels-and-new-look-for-profile-grid-461527-2025-01-21
- [S31] Storyboard18, Mosseri alıntılarıyla aynı duyuru, 21 Oca 2025: https://www.storyboard18.com/digital/instagram-extends-reels-to-three-minutes-and-updates-profile-layout-54043.htm
- [S32] PetaPixel, 3:4 fotoğraf desteği, Mayıs 2025: https://petapixel.com/2025/05/29/instagram-finally-adds-support-for-34-aspect-ratio-photos
- [S33] TechRadar, karuselde 20 öğe, 9 Ağu 2024: https://www.techradar.com/computing/instagram/instagram-will-now-let-you-post-up-to-20-photos-or-videos-in-a-gallery-your-friends-should-be-thrilled
- [S34] TechCrunch, "Your Algorithm", 10 Ara 2025: https://techcrunch.com/2025/12/10/instagrams-new-your-algorithm-tool-gives-you-more-control-over-the-reels-you-see

Üçüncü taraf blog (yalnız çelişki veya bağlam için, kanıt olarak kullanılmadı):
- [S3] Later, 21 Nis 2026 (5 sınırı, yorumlar dahil): https://later.com/blog/instagram-hashtags/amp
- [S4] RecurPost, 28 Eyl 2026 (uygulama 5, API 30): https://recurpost.com/instagram-scheduler/instagram-hashtag-limits-and-placement-rules/
- [S5] Lilach Bullock, 2026 (30 diyor, resmî alıntı yok): https://www.lilachbullock.com/why-instagram-only-lets-you-use-5-hashtags-some-posts/
- [S24] Hootsuite, alt metin (100 karakter iddiası kaynaksız): https://blog.hootsuite.com/instagram-alt-text/
- [S36] Hootsuite, Reels kapağı (9:16, sonradan değiştirme): https://blog.hootsuite.com/instagram-reels-cover/
- SocialPilot, Reels algoritma zaman çizelgesi (yalnız resmî kaynaklara yönlendirme için okundu): https://www.socialpilot.co/es/blog/instagram-reels-algorithm

Çekilemeyen resmî sayfalar (yalnız meta veri döndü, içerik kullanılmadı): https://help.instagram.com/313829416281232 · https://help.instagram.com/613868662393739 · https://about.instagram.com/blog/announcements/reels-algorithm-control · https://transparency.meta.com/enforcement/taking-action/lowering-distribution-of-problematic-content · https://www.meta.com/en-gb/help/artificial-intelligence/1783222608822690/

Veri dosyaları: `avz/sosyal_veri/README.txt`, `instagram.csv`, `screenshots/instagram_01-10_hashtag.jpg`, `instagram_15-16_suggestions.jpg`, `youtube_google_autocomplete.csv`, `pinc/S1, S1b, S2, S3, S4/PIN_CIFT_*.csv` (çift sayımı Python ile yeniden yapıldı), `arastirma/PINTEREST_CLAUDE.md`.
