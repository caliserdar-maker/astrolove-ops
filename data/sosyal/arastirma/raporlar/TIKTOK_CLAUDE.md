# AstroLoveArt TikTok Araştırması (Claude, bağımsız)

Tarih: 12 Ekim 2026 · Kapsam: yalnız TikTok · Veri: `avz/sosyal_veri/tiktok.csv` (11 Eki 2026) ve `screenshots/tiktok_*`. Platformlar arası sinyal (TikTok kanıtı DEĞİL): `youtube_google_autocomplete.csv`, `pinterest.csv`, `pinc/S*/PIN_CIFT_*.csv`, ayrıca `instagram.csv` sayıları yalnız Instagram raporundan aktarım.

Okuma kuralı: "not shown / gösterilmedi" = toplanmadı, sıfır değil. Kaynakla doğrulayamadığım her şey **doğrulanmadı** diye işaretli. Satır referansı: `dosya / seed / data_type / rank → text`. Kaynak numaraları G bölümünde ([T..]).

Erişim notu: `www.tiktok.com` altındaki Topluluk Kuralları, "For You feed Eligibility Standards" ve Creator Academy sayfaları robots.txt nedeniyle **çekilemedi**; `support.tiktok.com` sayfaları boş döndü veya robots ile engellendi. Bu yüzden resmî kanıt ağırlıkla `newsroom.tiktok.com`, `developers.tiktok.com` ve `ads.tiktok.com` (yardım merkezi) kaynaklıdır. Çekemediğim sayfadan bilgi doldurmadım.

---

## Kısa sonuç (7 madde)

1. **TikTok verimiz zayıf.** CAPTCHA yüzünden 24 tohumun yalnız ilk 6'sı (hepsi "hediye" tohumu) toplandı; burç, çift adı, "zodiac", "wall art" tohumlarının **hiçbiri** TikTok'ta aranmadı. Creative Center hashtag sayıları da yok. Burç kelimeleri için elimizdeki her şey platformlar arası sinyaldir.
2. **TikTok'un kendi verisinde en güçlü kelimeler:** "anniversary gift" (+ "for her", "for him", "ideas"), "personalized gift" (TikTok'un "Others searched for" önerisi), "couple gifts / gift for couple", "engagement gift", "wedding gift for couple" (B bölümü).
3. **Dağıtım (resmî):** For You önerisinde etkileşimler, video bilgisi (**açıklama, ses, hashtag**) ve cihaz/hesap ayarları kullanılıyor; uzun bir videonun **sonuna kadar izlenmesi** güçlü sinyal; takipçi sayısı doğrudan etken değil [T1]. Aramada açıklamanın, ekrandaki yazının veya sesin nasıl ağırlıklandığına dair organik içerik için resmî metin bulamadım: **doğrulanmadı**.
4. **Sınırlar:** API ile açıklama (title) en fazla **2.200 UTF-16 karakter** [T2]. Uygulama içinde 4.000 (yalnız ikincil kaynak [T32]). Hashtag için uygulama "**Maximum 5 hashtags**" uyarısı gösteriyor (Ağustos 2025, ikincil; TikTok resmî açıklama yapmadı) [T30][T31]. Metricool'a göre TikTok API'si **satır sonunu desteklemiyor** [T41][T42]: açıklama tek paragraf olmalı. Şablonumuz 387-427 karakter, 5 hashtag, tek paragraf.
5. **Müzik:** İşletme hesapları uygulamada yalnız Ticari Müzik Kütüphanesi'ni (CML) görüyor [T8]; TikTok "işletmeler tüm ticari faaliyetlerde (organik içerik dahil) CML kullanmalı", başka lisanslı ses için "uygun lisansı aldığınızdan emin olun" diyor [T9]. Pixabay lisansı ticari videoda kullanıma izin veriyor ama platformların otomatik sistemlerinin sesi kısabileceğini söylüyor [T44]. Metricool: API ile atılan videoda doğrulama yayın anında yapılıyor, işletme hesabında telifli müzik **sessize alınabilir** [T40]. Content Posting API'de video için TikTok sesi seçme alanı yok (yalnız fotoğrafa `auto_add_music`) [T2][T4].
6. **Yapay zekâ etiketi:** TikTok "gerçekçi yapay zekâ içeriğinin etiketlenmesini zorunlu tutuyoruz" diyor [T15][T13]. Duvar sahnesinin arka planı yapay zekâ ile üretildi ve gerçekçi görünüyorsa **etiketi aç** (API `is_aigc`, Metricool'da "AI-generated content" anahtarı) [T2][T41]. Altın toz animasyonu kodla üretildiği için tek başına etiket gerektirmez.
7. **Etsy bağlantısı:** Açıklamada tıklanabilir link yolu belgelerde yok. Profilde link: TikTok'un yardım sayfasına göre bio linkinin **profilde görünmesi Doğrulanmış İşletme Hesabı (VBA)** ile oluyor; Türkiye doğrulama yapılan pazarlar arasında [T11][T12]. Kişisel hesapta 1.000 takipçi şartı yalnız ikincil kaynaklarda [T35][T36][T37]. Link yoksa açıklamada "link in bio" yazma, B şablonunu kullan (C.1).

---

## A. TikTok araması ve For You dağıtımı neyi kullanıyor (kaynaklı)

| Öğe | Resmî bilgi | Bizim için anlamı | Kaynak |
|---|---|---|---|
| **For You sinyalleri** | Üç grup: kullanıcı etkileşimleri (beğeni, paylaşım, takip, yorum, oluşturulan içerik), **video bilgisi ("captions, sounds, and hashtags")**, cihaz ve hesap ayarları (dil, ülke, cihaz). Cihaz/hesap ayarları diğerlerine göre düşük ağırlıkta. Güçlü örnek sinyal: kullanıcının uzun bir videoyu **baştan sona izlemesi**. "Takipçi sayısı ve önceki yüksek performanslı videolar doğrudan etken değil." (18 Haz 2020) | Açıklama ve hashtag konuyu tanımlamak için kullanılıyor. 24 sn'lik videonun sonuna kadar izlenmesi önemli; bitiş kartı son saniyelerde kalmalı. Yeni hesap olmak tek başına engel değil. | [T1] |
| **Arama** | Organik aramada sıralamanın hangi alanlara (açıklama, hashtag, ekrandaki yazı, konuşma) bakarak yapıldığına dair resmî sayfa **çekilemedi / bulunamadı: doğrulanmadı**. Yalnız ücretli Arama Reklamları için: eşleşme "sorgu, reklam anahtar kelimesi ve kreatif içerik" arasındaki ilgiye bakar; anahtar kelimeleri başlık ve açıklamaya koyun; ilk karelerde "anahtar kelimeyi ekranda yazı olarak gösteren" kanca önerilir (REKLAM bağlamı, organik kanıt değil). | Çift adını ve ürün kelimelerini açıklamaya koymak tek güvenli adım. Ekrandaki soru zaten çift adını içeriyor; organik aramada okunduğu doğrulanmadı. | [T23] |
| **Kelime filtresi** | Kullanıcılar eklediği kelimeleri içeren içeriği akıştan kısıtlayabiliyor; "Smart Keyword Filters" eş anlamlıları da kapsıyor (3 Haz 2025). | TikTok içerikteki kelimeleri okuyor (filtre için). Arama sıralamasına etkisi doğrulanmadı. | [T20] |
| **Creator Search Insights** | "TikTok'ta insanların aradığı konular" hakkında bilgi veren araç; arama çubuğuna "Creator Search Insights" yazarak açılıyor; yalnız bazı bölgelerde. "Content gap": çok aranan ama az videosu olan konu (13 Mar 2024). | TikTok'a özgü kelime verisi için en doğrudan resmî araç. Hesabımızda açılıp açılmadığı **doğrulanmadı** (F). | [T18] |
| **Arama kullanımı (TikTok'un kendi araştırması)** | ABD'de "TikTok kullanıcılarının 2'de 1'i yeni ürün veya markaları araştırmak için TikTok'a gittiğini söylüyor" (TikTok Marketing Science, Material, Nis 2022, n=2.000). Görsel altında kaynaksız "keşiflerin 3'te 2'si aramayla" ifadesi var; kaynağı yok, kullanmıyorum. | Ürün araştırması için arama yapılıyor; bizim kelimelere ait hacim verisi yok. | [T25] |
| **Hashtag** | Hashtag "video bilgisi"nin parçası [T1]. Ağustos 2025'ten beri uygulama "Maximum 5 hashtags. Use accurate hashtags to get more views." uyarısı gösteriyor; TikTok resmî açıklama yapmadı (ikincil). API: hashtag ve @ "boşluk veya yeni satırla ayrılır"; sayı sınırı API belgesinde yok. | En fazla 5, doğru ve ürüne uyan hashtag. API'nin 5 sınırını uygulayıp uygulamadığı **doğrulanmadı**; 5'i aşma. | [T1] [T30] [T31] [T2] |
| **Açıklama uzunluğu** | API `title`: en fazla **2.200 UTF-16 karakter** (video) [T2]. Fotoğraf gönderisinde başlık 90, açıklama 4.000 [T4]. Uygulama içi 4.000 karakter (Ağu 2023, Matt Navarra kaynaklı ikincil haber; TikTok onayı yok) [T32]. | Metricool API kullandığı için bağlayıcı sınır 2.200. Şablonlar 387-427. | [T2] [T4] [T32] |
| **Satır sonu** | Metricool: "The TikTok API does not support line breaks", paragraf ayrılamıyor. API belgesi hashtag'lerin "yeni satırla" da ayrılabileceğini yazıyor (çelişki). | Açıklamayı **tek paragraf** yazdım; satır sonu olsa da olmasa da doğru okunur. | [T41] [T42] [T2] |
| **Ses** | "Sounds" video bilgisi sinyali [T1]. TikTok iç verisi (Ara 2021): "en iyi performans gösteren videoların %93'ü ses kullanıyor"; TikTok "sesi açık bir ortam". TikTok'un kendi sesini kullanmanın erişimi artırdığına dair resmî metin bulamadım: **doğrulanmadı**. | Videoda ses olmalı (Pixabay parçası var). Ses seçimi kuralları E.2'de. | [T1] [T24] |
| **Uzunluk, biçim** | TikTok iç verisi (Ara 2021, eski): "en iyi performans gösteren 4 videodan 1'i 21-34 sn"; 720p ve üstü, tam ekran, dikey 9:16 daha fazla gösterim. API: 23-60 FPS, en az 360 px, en fazla 4 GB, MP4/H.264 önerilir; video 10 dakikaya kadar, hesap başına yayın sınırı 3, 5 veya 10 dk (`max_video_post_duration_sec`). | 24 sn, 9:16, 1080×1920 uyumlu. Rakamlar 2021 verisi; bugüne genellemesi doğrulanmadı. | [T24] [T6] [T7] |
| **İlk saniyeler** | Organik içerik için resmî "ilk X saniye" kuralı bulamadım: **doğrulanmadı**. Reklam rehberi ilk karelerde kanca önerir (reklam bağlamı). | Açılış sorusu "{A} & {B}, as one?" ilk karede: değiştirmeye gerek yok. | [T23] |
| **Uygunluk (For You)** | Nis 2024 güncellemesi: For You standartlarına aykırı içeriği tekrar tekrar paylaşan hesabın **tamamı** öneriden çıkabiliyor ve **aramada bulunması zorlaşıyor**; bildirim ve itiraz var. Hangi içeriğin uygun olmadığını tanımlayan "For You feed Eligibility Standards" sayfası **çekilemedi**; özgün olmayan içerik ve filigran kuralı bu yüzden **doğrulanmadı**. | Tasarım ve video bizim; başka uygulamanın filigranı olmayan temiz dosya yükle. Hesap Durumu ekranını izle. | [T21] [T38] |
| **API ile yayının filigran kuralı** | Geliştirici kuralları: entegrasyonlar (ör. Metricool) içeriğe kendi marka adı, logo, filigran, link veya tanıtım metni **ekleyemez**; aksi içerik silme veya hesap kapatmaya yol açabilir. Kural uygulamaya yönelik, içerik sahibine değil. | Metricool'un kendi işaretini eklememesi gerekiyor. Bizim bitiş kartımız (ASTROLOVEART / On Etsy) bu kuralın konusu değil; TikTok'un kendi markamızı nasıl değerlendirdiği doğrulanmadı. | [T3] |

---

## B. Verimiz: anahtar kelime ve hashtag öncelik sırası

### B.1 Veri hakkında uyarılar

- **Kapsam:** TikTok'ta yalnız 6 tohum aranabildi: `anniversary gift`, `1st anniversary gift`, `newlywed gift`, `engagement gift`, `wedding gift for couple`, `couple gift`. Kalan 18 tohum (burç, çift, wall art, decor) `not shown / Not collected` (CAPTCHA, `tiktok_06_results.jpg`'de görünüyor). Creative Center'da hashtag araması yok (`tiktok_creative_center_us_7d/30d_no_search.jpg`); TikTok bu aramayı Ocak 2024'te kaldırmıştı [T34]. 13 hashtag için posts/views satırları hepsi `not shown`.
- **Oturum:** Aramalar giriş yapılmış AstroLoveArt hesabıyla, **Türkçe arayüzde** yapıldı (`tiktok_01_results.jpg`: "Sizin İçin", "Diğer aramalar"). Bölge ABD seçilmedi. Öneriler "philippines", "indian", "sri lanka", "nepal" içeriyor (`wedding gift for couple / suggestion / 3, 5, 6, 7`; `newlywed gift / suggestion / 6, 8`): öneriler ABD'ye özgü değil, kişiselleştirme etkisi **doğrulanmadı**.
- **Otomatik tamamlama hacim değildir.** Sıra yalnız TikTok'un o oturumda gösterdiği sıradır.
- **Ekran görüntüsü kontrolü:** `tiktok_01_results.jpg` ("Diğer aramalar: anniversary gift for him, personalized gift, anniversary video") ve `tiktok_06_suggestions.jpg` (couple gift 8 öneri) CSV ile birebir aynı. `tiktok_02_results.jpg` ve `tiktok_04_results.jpg` sonuçlar yüklenmeden çekilmiş (boş kartlar); CSV'deki "Others searched for not shown" ile tutarlı. `tiktok_06_suggestions.jpg`'de sağda "Diğer aramalar: housewarming gift ideas, wedding gift idea" görünüyor ama arkadaki sayfa önceki aramanın (büyük olasılıkla `wedding gift for couple`) sonucu; CSV'de yok, hangi tohuma ait olduğu belirsiz: **kullanmadım**.

### B.2 Öncelik tablosu

Seviye: **A** = TikTok satırı + platformlar arası destek · **B** = yalnız TikTok satırı, ya da TikTok satırı yok ama çift düzeyinde çok güçlü platformlar arası destek · **C** = yalnız platformlar arası, zayıf · **X** = kullanma.

| # | Kelime / hashtag | Seviye | Kanıt satırları | Gerekçe ve kullanım |
|---|---|---|---|---|
| 1 | **anniversary gift** (+ "for her", "for him", "ideas") / **#anniversarygift** | A | TikTok: `tiktok.csv / anniversary gift / suggestion / 1 → anniversary gift`, `/ 2 → anniversary gift ideas for girlfriend`, `/ 3 → Anniversary gift for her`, `/ 4 → Anniversary gift ideas`, `/ 5 → anniversary gift for boyfriend`, `/ 8 → anniversary gifts for him`; `/ related_term / 1 → anniversary gift for him`; `1st anniversary gift / suggestion / 1-8` (ör. `/ 6 → 1st anniversary gift for her`). Platformlar arası: YouTube `seed / anniversary gift / 1 → anniversary gift ideas`, `/ 6 → anniversary gifts for him`; Google `/ 3 → anniversary gifts for him`, `/ 4 → anniversary gifts for her`; Pinterest `anniversary gift / suggestion / 2 → anniversary gifts for her`. Instagram #anniversarygift `4,400.000` (Instagram raporu). | TikTok'ta en çok satırla desteklenen ifade; "for her / for him" kalıbı 6 TikTok satırında. Açıklamada "anniversary gift idea for her or for him". Hashtag: #anniversarygift. |
| 2 | **personalized gift** / **#personalizedgift** | A | TikTok: `anniversary gift / related_term / 2 → personalized gift` (`tiktok_01_results.jpg`'de görünüyor). Platformlar arası: YouTube ve Google `seed / personalized couple gift / 1 → personalized couple gifts`; Instagram #personalizedgift `1,900.000`. | TikTok "anniversary gift" arayanlara bunu öneriyor: ürünün ayırt edici özelliğiyle (isim + mesaj) doğrudan bağ. Açıklamada "personalized anniversary gift". |
| 3 | **couple gifts / gift for couple / couple gift ideas** / **#couplegifts** | A | TikTok: `couple gift / suggestion / 1 → couple gifts`, `/ 2 → couple gift ideas`, `/ 7 → gift for couple`, `/ 8 → couple gift wedding`; `wedding gift for couple / suggestion / 8 → couple gift ideas for wedding`. Platformlar arası: YouTube `couple gift / 1 → couple gifts`, Google `couple gift / 3 → couple gifts for anniversary`. | TikTok'ta 1. sıradaki biçim **çoğul**: hashtag #couplegifts (Instagram raporunda tekil seçilmişti, o Instagram verisine dayanıyordu). Açıklamada "a couple gift". |
| 4 | **"{A} and {B}" + "compatibility"** / **#zodiaccompatibility** | B (TikTok satırı yok) | TikTok: tohumlar `gemini and leo`, `cancer and libra`, `scorpio and pisces`, `zodiac compatibility` → hepsi `not shown / Not collected`. Platformlar arası: YouTube `pair` sorgularının **78/78**'inde "compatibility" önerisi var (benim sayımım; 31 çiftte 1., 43 çiftte 2. sırada), ör. `youtube / pair / gemini and leo / 3 → gemini and leo compatibility`, `pair / cancer and libra / 2 → cancer and libra compatibility`; YouTube `seed / zodiac compatibility / 9 → zodiac compatibility tiktok`; Pinterest `PIN_CIFT_*` öneri satırlarında **66/78** (eksik 12: 11 Cancer çifti ve Sagittarius-Sagittarius), ör. `S2 / gemini and leo / suggestion / 2`, `S4 / scorpio and pisces / suggestion / 3`; Google `seed / zodiac couple / 2 → zodiac couple compatibility`. | Çift adı her videonun özgün kelimesi; "compatibility" çift düzeyinde en tutarlı ek. YouTube'da "zodiac compatibility **tiktok**" önerisi, bu konunun TikTok içeriği olarak arandığını gösteriyor (dolaylı, TikTok kanıtı değil). Açıklamada çift adı 2 kez + "compatibility art". Hashtag: #zodiaccompatibility (TikTok'ta sayısı toplanmadı). |
| 5 | **zodiac couples** / **#zodiaccouples** | C | TikTok: `zodiac couple`, `zodiac signs as couples` → `not shown`. Platformlar arası: YouTube `seed / zodiac couple / 2 → zodiac couples`, `/ 6 → zodiac couples tiktok`, `/ 10 → zodiac couple tiktok compilation`; Google `seed / zodiac couple / 1 → zodiac couples`; Instagram ekranında `#zodiaccouples 14,7B` (Instagram raporu, yalnız ekran kanıtı). | Ürün kategorisi. YouTube'daki "tiktok" ekli öneriler bu ifadenin TikTok içerik türü adı olarak kullanıldığına işaret ediyor (dolaylı). Çoğul biçim üç kaynakta öne çıkıyor. |
| 6 | **engagement gift**, **wedding gift for couple** | B | TikTok: `engagement gift / suggestion / 1 → engagement gift`, `/ 2 → engagement gift ideas`; `wedding gift for couple / suggestion / 1, 2, 4 → perfect gift for wedding couple`. Platformlar arası: YouTube `engagement gift / 4 → engagement gifts for couples`, Google `engagement gift / 3 → engagement gifts for couples`. | Açıklamada "for an engagement or wedding" olarak geçiyor; hashtag hakkı 5 ile sınırlı olduğu için hashtag yok. |
| 7 | **newlywed gift** | C | TikTok: `newlywed gift / suggestion / 1-3`, `/ 4 → gift for newly married couple`. | Ürüne uyuyor ama açıklamayı uzatmamak için kullanmadım; alternatif deneme kelimesi. |
| X | "challenge", "gift box/basket", "exchange", ülke ekli öneriler | X | `anniversary gift / suggestion / 7 → anniversary gift challenge`, `couple gift / suggestion / 4-6`, `engagement gift / suggestion / 3 → engagement giftbox`, `newlywed gift / suggestion / 5, 7`, `wedding gift for couple / suggestion / 3, 5, 6, 7`. | Ürün bu değil veya bölgesel. |
| X | **#zodiac, #astrology, #giftideas, #walldecor, #homedecor** | X | TikTok: hepsi `hashtag_posts / hashtag_views / not shown`. | Sayı yok; çok genel. 5 hashtag hakkını özgül etiketlere ayırdım. Kanıt gelirse yeniden değerlendirilir. |
| X | tarot, memes, tattoo, friendship | X | Platformlar arası: YouTube `pair` sorgularında "tarot" 77/78, "friendship" 67/78; Pinterest çift verisinde "tattoo" 76/78 (benim sayımım). | Ürün bunlar değil. |

**Çift hashtag'i (#geminileo vb.):** TikTok'ta sayısı toplanmadı, hiçbir kaynakta satırı yok. Önermiyorum; çift adı açıklamada.

**"cancer" sorunu:** Pinterest "cancer"ı "cancerian"a çeviriyor (`S2 / libra and cancer / suggestion / 1 → libra and cancerian`). YouTube'da sorun yok (`pair / cancer and libra / 2 → cancer and libra compatibility`). TikTok'ta durum **doğrulanmadı**; "Cancer" yazımını koruyorum.

### B.3 Önerilen 5'li hashtag seti

```text
#zodiaccompatibility #zodiaccouples #personalizedgift #anniversarygift #couplegifts
```
Dayanak: B.2 satır 4, 5, 2, 1, 3. İki etiket TikTok satırlı (A), biri TikTok "Others searched for" (A), ikisi yalnız platformlar arası (B/C). Toplam 83 karakter, tam 5 hashtag [T30][T31].

---

## C. Şablonlar

Kurallar: açıklama ≤2.200 UTF-16 karakter (API) [T2]; ≤5 hashtag [T30][T31]; satır sonu yok (tek paragraf) [T41]. 78 çiftin tamamı Python ile hesaplandı: **A şablonu 387-419, B şablonu 395-427 karakter**; ilk cümle 20-36 karakter (en uzun Sagittarius and Sagittarius). Çift adları alfabetik sırada (ör. "Gemini & Leo", "Pisces & Scorpio"). Uzun/orta tire yok, "+" yok, marka AstroLoveArt. Ürün iddiası yok (çerçeve, kâğıt, ölçü, fiyat, "best seller", constellation yok).

### C.1 Açıklama (caption)

A şablonu: profilde Etsy linki **görünür** olduğunda.
```text
{SIGN_A} and {SIGN_B}, as one? Watch two zodiac signs become one gold symbol. {SIGN_A} and {SIGN_B} compatibility art with your names and your personal message, made by AstroLoveArt. A personalized anniversary gift idea for her or for him, and a couple gift for an engagement or wedding. Make it yours on Etsy, link in bio. #zodiaccompatibility #zodiaccouples #personalizedgift #anniversarygift #couplegifts
```

B şablonu: profilde link **yokken** (VBA veya takipçi şartı sağlanmadıysa).
```text
{SIGN_A} and {SIGN_B}, as one? Watch two zodiac signs become one gold symbol. {SIGN_A} and {SIGN_B} compatibility art with your names and your personal message, made by AstroLoveArt. A personalized anniversary gift idea for her or for him, and a couple gift for an engagement or wedding. Make it yours: search AstroLoveArt on Etsy. #zodiaccompatibility #zodiaccouples #personalizedgift #anniversarygift #couplegifts
```

Dayandığı satırlar: ilk cümle = videonun açılış sorusu + çift adı (B.2 #4); "compatibility art" (B.2 #4); "personalized" (B.2 #2); "anniversary gift idea for her or for him" (B.2 #1); "couple gift", "engagement or wedding" (B.2 #3, #6); marka adı arama için.

### C.2 İlk satır (kanca) kuralı

- Biçim: `{SIGN_A} and {SIGN_B}, as one?` Videodaki açılış sorusuyla aynı; çift adı açıklamanın ilk kelimeleri.
- Açıklamada "and", ekranda "&": ikisinin TikTok aramasında eşdeğer sayıldığı **doğrulanmadı**. Veride en sık biçim "and" (YouTube, Pinterest çift satırları).
- TikTok'ta açıklamanın "more" öncesi kaç karakter gösterdiği resmî olarak **doğrulanmadı**; ilk cümleyi 36 karakterin altında tuttum.

### C.3 Ekrandaki yazı

Mevcut metinler: açılış "{SIGN_A} & {SIGN_B}, as one?", isimler, duvarda gerçek poster, bitiş "Make it yours / ASTROLOVEART / On Etsy".

- **Değişiklik önermiyorum.** Organik aramada ekrandaki yazının okunduğuna dair resmî kanıt yok (A tablosu). Reklam rehberinin "ilk karede anahtar kelime yazısı" önerisini [T23] açılış sorusu zaten karşılıyor (çift adı).
- Tek kanıta dayalı uyarı: izlenme süresi sinyal olduğu için [T1] bitiş kartı videonun son saniyelerinde kısa kalmalı. Mevcut kurguyu değiştirmek için veri yok.

### C.4 Kapak (cover)

- API ile kapak yalnız videodan bir kare: `video_cover_timestamp_ms`; verilmezse **ilk kare** kapak olur [T2]. Metricool: özel kapak görseli yükleme **yalnız İşletme hesaplarında**; kişisel hesapta yalnız kare seçimi [T42][T41].
- Öneri: açılış sorusunun tamamen okunduğu kareyi kapak yap (çift adı profil ızgarasında okunur). O karenin milisaniyesi bende yok (F).
- İşletme hesabında özel kapak yüklenecekse yazı:
```text
{SIGN_A_UPPER} & {SIGN_B_UPPER}, AS ONE?
ASTROLOVEART
```
78 çiftte ana satır 18-34 karakter. TikTok profil ızgarasının kırpma oranı resmî olarak **doğrulanmadı**; yazıyı görselin dikey ortasında tut ve ilk yayından sonra profilde kontrol et.

---

## D. Doldurulmuş örnekler (karakter sayıları Python ile, UTF-16)

### D.1 Gemini & Leo

A (393 karakter; ilk cümle 23):
```text
Gemini and Leo, as one? Watch two zodiac signs become one gold symbol. Gemini and Leo compatibility art with your names and your personal message, made by AstroLoveArt. A personalized anniversary gift idea for her or for him, and a couple gift for an engagement or wedding. Make it yours on Etsy, link in bio. #zodiaccompatibility #zodiaccouples #personalizedgift #anniversarygift #couplegifts
```
B (401 karakter):
```text
Gemini and Leo, as one? Watch two zodiac signs become one gold symbol. Gemini and Leo compatibility art with your names and your personal message, made by AstroLoveArt. A personalized anniversary gift idea for her or for him, and a couple gift for an engagement or wedding. Make it yours: search AstroLoveArt on Etsy. #zodiaccompatibility #zodiaccouples #personalizedgift #anniversarygift #couplegifts
```
Kapak (21): `GEMINI & LEO, AS ONE?`

### D.2 Cancer & Libra

A (397 karakter; ilk cümle 25):
```text
Cancer and Libra, as one? Watch two zodiac signs become one gold symbol. Cancer and Libra compatibility art with your names and your personal message, made by AstroLoveArt. A personalized anniversary gift idea for her or for him, and a couple gift for an engagement or wedding. Make it yours on Etsy, link in bio. #zodiaccompatibility #zodiaccouples #personalizedgift #anniversarygift #couplegifts
```
B (405 karakter):
```text
Cancer and Libra, as one? Watch two zodiac signs become one gold symbol. Cancer and Libra compatibility art with your names and your personal message, made by AstroLoveArt. A personalized anniversary gift idea for her or for him, and a couple gift for an engagement or wedding. Make it yours: search AstroLoveArt on Etsy. #zodiaccompatibility #zodiaccouples #personalizedgift #anniversarygift #couplegifts
```
Kapak (23): `CANCER & LIBRA, AS ONE?`

### D.3 Scorpio & Pisces (alfabetik kuralla: Pisces & Scorpio)

Ürün kuralı çift adını alfabetik yazıyor: "Pisces & Scorpio". Pinterest verisinde sıra fark yaratmıyor (`S4 / scorpio and pisces / suggestion / 3` ve `S4 / pisces and scorpio / suggestion / 5`, ikisi de compatibility). YouTube'da "scorpio and" yazınca "scorpio and pisces" çıkıyor (`youtube / prefix / scorpio and / 2`). TikTok'ta sıra etkisi **doğrulanmadı**. Not: Instagram raporundaki D.3 "Scorpio and Pisces" sırasını kullanmıştı; ürün kuralıyla uyum için hangisinin geçerli olduğuna sen karar ver.

A (401 karakter; ilk cümle 27):
```text
Pisces and Scorpio, as one? Watch two zodiac signs become one gold symbol. Pisces and Scorpio compatibility art with your names and your personal message, made by AstroLoveArt. A personalized anniversary gift idea for her or for him, and a couple gift for an engagement or wedding. Make it yours on Etsy, link in bio. #zodiaccompatibility #zodiaccouples #personalizedgift #anniversarygift #couplegifts
```
B (409 karakter):
```text
Pisces and Scorpio, as one? Watch two zodiac signs become one gold symbol. Pisces and Scorpio compatibility art with your names and your personal message, made by AstroLoveArt. A personalized anniversary gift idea for her or for him, and a couple gift for an engagement or wedding. Make it yours: search AstroLoveArt on Etsy. #zodiaccompatibility #zodiaccouples #personalizedgift #anniversarygift #couplegifts
```
Kapak (25): `PISCES & SCORPIO, AS ONE?`

---

## E. Resmî olarak belgelenmiş paylaşım uygulamaları (yalnız kaynaklı)

1. **Hesap türü.** TikTok yardım merkezi: İşletme hesabı performans ve kitle verisi sunar [T10]. Bio linki, "Advanced Access" seviyesinde düzenlenebilir ama **profilde gösterilemez**; profilde görünmesi ve "Organic Conversion Anchors" (videoya veya profile hedef link ekleme) **Doğrulanmış İşletme Hesabı (VBA)** ile [T11]. Doğrulama her türden ve büyüklükte hesaba açık; Türkiye (TR) listede [T12]. Organic Conversion Anchors'ın Etsy linkine izin verip vermediği **doğrulanmadı**. Kişisel hesapta 1.000 takipçi şartı yalnız ikincil kaynaklarda (2020 ve 2026) [T35][T36][T37].
2. **Müzik (işletme).** İşletme hesabı "ses ekle" ekranında yalnız CML'yi görür [T8]. "İşletmeler tüm ticari TikTok faaliyetlerinde CML kullanmalı", organik içerik buna dahil; genel müzik kütüphanesi ticari kullanım için kullanılamaz; başka lisanslı ses için "uygun lisansı aldığınızdan emin olun" [T9]. Pixabay: müzik sosyal medyada ve ticari videoda kullanılabilir, yeter ki daha büyük bir eserin parçası olsun; platformların otomatik sistemleri sesi kısabilir veya engelleyebilir [T44]. Metricool: API ile yayında doğrulama yayın anında olur, işletme hesabında telifli müzik sessize alınabilir; sebebini uygulamada videoda "View details" ile gör, gerekirse TikTok kütüphanesinden izinli sesle değiştir [T40]. **Sonuç:** Pixabay parçası lisans açısından izinli; ama TikTok'un otomatik sistemi tarafından sessize alınma riski var. İlk yayınlarda ses kontrol edilmeli (F).
3. **API ile TikTok sesi.** Content Posting API'de video için müzik alanı yok; fotoğrafta `auto_add_music` (önerilen müzik) var [T2][T4]. Metricool: işletme hesapları "TikTok'un Top 100 trend şarkısını" ekleyebiliyor; bunun dışındaki müzik ve efektler için elle yayın gerekiyor [T41][T43]. Bu şarkıların CML olup olmadığı ve videoya mı yalnız fotoğrafa mı eklendiği **doğrulanmadı**. TikTok sesi kullanmanın erişime etkisi resmî olarak **doğrulanmadı**.
4. **Müzik beyanı.** API ile yayında kullanıcıya "By posting, you agree to TikTok's Music Usage Confirmation" metni gösterilmek zorunda [T3]. Beyan metninin kendisi **çekilemedi**.
5. **Ticari içerik beyanı.** API uygulaması "Bu içerik sizi, bir markayı, ürünü veya hizmeti tanıtıyor mu" sorusunu sunmak zorunda: "Your brand" = kendi işinizi tanıtıyorsunuz (`brand_organic_toggle`), "Branded content" = üçüncü taraf (`brand_content_toggle`, zorunlu alan); markalı içerik yalnız herkese açık veya arkadaş görünürlüğüyle [T2][T3]. Metricool'da iki seçenek de var [T41]. "Your brand" seçilince gönderide "Promotional content" etiketi çıktığı yalnız ikincil kaynakta [T39]. **Öneri:** kendi ürünümüz için "Your brand" açık, "Branded content" kapalı. Etiketin erişime etkisi **doğrulanmadı**.
6. **Yapay zekâ etiketi.** TikTok gerçekçi görüntü, ses veya video içeren yapay zekâ içeriğinin etiketlenmesini zorunlu tutuyor; etiket tamamen üretilmiş veya "önemli ölçüde düzenlenmiş" içerik için [T13][T15]. TikTok Shop (ABD) politikası: kısmen üretilmiş içerik de yapay zekâ içeriği sayılıyor; izleyicinin gerçek çekim sanabileceği kadar gerçekçi efektlerde beyan gerekli; küçük düzeltmeler (ışık, renk, kırpma) beyan gerektirmiyor; yanlış veya eksik beyan içerik kaldırma veya hesap kısıtlamasına yol açabilir [T17] (Shop politikası, organik video için doğrudan kural olduğu **doğrulanmadı**). C2PA meta verisi taşıyan içerik otomatik etiketlenebiliyor [T14]; platformun koyduğu etiket kaldırılamıyor [T17]. Kullanıcılar "Manage topics" içinde yapay zekâ içeriğini azaltabiliyor (Kasım 2025'te test) [T15]. **Öneri:** duvar sahnesi yapay zekâyla üretilmiş gerçekçi bir oda görüntüsüyse etiketi aç (`is_aigc: true` → "Creator labeled as AI-generated") [T2]. Etiketin erişime etkisi **doğrulanmadı**. Altın toz animasyonu kodla üretildi; tek başına etiket konusu değil.
7. **Gizlilik ve etkileşim.** API ile yayında gizlilik açılır listeden **elle** seçilmeli, varsayılan olmamalı; yorum, Duet, Stitch anahtarları varsayılan kapalı gelir, kullanıcı açar [T3]. Denetlenmemiş (unaudited) uygulamalar yalnız "özel" yayın yapabilir [T2][T5]. **Öneri:** Public, yorum açık. Duet/Stitch kararı senin.
8. **Kota.** API'de kullanıcı başına günlük yayın sınırı var (`spam_risk_too_many_posts`) ama sayı belgede yok; istek sınırı dakikada 6 (Direct Post) [T2][T7]. Metricool sorun giderme sayfası "çok sık paylaşım"ı spam nedeni olarak sayıyor, sayı vermiyor [T43]. Günde kaç video atılabileceği **doğrulanmadı**.
9. **Video dosyası.** MP4, H.264, 23-60 FPS, ≤4 GB; Metricool otomatik yayında 3 sn-10 dk, ≤500 MB, ≥540 px [T6][T41][T43]. Başka platformdan indirilmiş (filigranlı) dosya değil, ana dosya yüklenmeli (genel ilke; TikTok'un filigran kuralı metni çekilemedi, A tablosu).
10. **Aynı videoyu dört platformda paylaşmak.** TikTok'un aynı videonun başka platformlarda da yayınlanmasını cezalandırdığına dair resmî metin bulamadım: **doğrulanmadı**. Instagram tarafında başka uygulama filigranı olan Reel'in daha az önerildiği Instagram raporunda kaynaklı (platformlar arası). Güvenli yol: her platforma filigransız ana dosya.
11. **Uygunluk takibi.** For You standartlarına aykırı içerik tekrarlanırsa hesap öneriden çıkabilir ve aramada zor bulunur; bildirim ve itiraz var [T21][T38].
12. **TikTok Shop.** Kapsam dışı; Türkiye'den satıcı uygunluğu ve Etsy ürünlerinin bağlanması **doğrulanmadı**.
13. **Sıklık ve saat.** TikTok (KOBİ rehberi): her gün paylaşmak gerekmez, takvim yapıp ona uyun [T27]; düzenli paylaşım önerisi [T24][T26]. Saat için resmî kaynak bulamadım.

---

## F. Eksik veri ve açık sorular

1. **En büyük eksik:** TikTok'ta burç ve çift tohumları hiç aranmadı (18 tohum, `Not collected`). Öncelik: `zodiac compatibility`, `zodiac couple`, `gemini and leo`, `cancer and libra`, `pisces and scorpio` ve `scorpio and pisces`, `zodiac wall art`, `personalized couple gift`. Mümkünse ABD bölgesiyle, aramalar arasında uzun beklemeyle (CAPTCHA).
2. **Hashtag sayıları:** 5 hashtag'in (B.3) TikTok'taki gönderi/izlenme sayıları yok. Creative Center hashtag araması 2024'ten beri yok [T34]; uygulamada hashtag sayfasından okunabilir (doğrulanmadı).
3. **Creator Search Insights** hesabımızda açılıyor mu, burç/hediye konularında "content gap" var mı: kontrol edilmedi [T18]. TikTok'a özgü kelime verisi için en iyi resmî kaynak.
4. **Hesap türü ve takipçi sayısı** bilinmiyor: İşletme mi Kişisel mi, VBA mı? Bio linki (A/B şablonu seçimi), özel kapak, müzik kısıtları buna bağlı.
5. **Pixabay sesi** TikTok'ta sessize alınacak mı: ilk 1-3 yayında kontrol edilmeli (videoda "View details") [T40].
6. **Kapak karesi** milisaniyesi (açılış sorusunun tam okunduğu an) verilmedi.
7. **Yapay zekâ etiketi** erişimi etkiliyor mu: doğrulanmadı. Duvar sahnesi görselinde C2PA meta verisi var mı (ör. üretim aracından): bilinmiyor; videoya dönüştürünce kalıp kalmadığı doğrulanmadı.
8. **For You Eligibility Standards**, Creator Academy ve support.tiktok.com sayfaları çekilemedi: özgün olmayan içerik, filigran, "etkileşim tuzağı" (ör. "partnerini etiketle") kuralları bu yüzden **doğrulanmadı**; şablonlara böyle çağrı koymadım.
9. **Organik aramada** ekrandaki yazı ve sesin (OCR, transkript) kullanılıp kullanılmadığı doğrulanmadı.
10. **5 hashtag sınırı** resmî duyurulmadı (ikincil); API ile yayında uygulanıp uygulanmadığı doğrulanmadı.
11. **Satır sonu:** Metricool "desteklenmiyor" diyor, API belgesi yeni satırdan söz ediyor; şablon tek paragraf olduğu için sorun değil.
12. **"Music Usage Confirmation"** metni çekilemedi.
13. **Çift sırası** ("Pisces & Scorpio" ve "Scorpio & Pisces") ve **"and" ile "&"** TikTok aramasında fark yaratıyor mu: doğrulanmadı.
14. Instagram raporuyla tutarlılık: Instagram'da hashtag'ler `#zodiacart #zodiaccouple #astrologyart #personalizedgift #anniversarygift` idi. TikTok setini TikTok satırlarına göre seçtim (#couplegifts çoğul, #zodiaccompatibility eklendi); #zodiacart ve #astrologyart için TikTok satırı yok.

---

## G. Kaynaklar

Resmî (TikTok):
- [T1] TikTok Newsroom, "How TikTok recommends videos #ForYou", 18 Haz 2020: https://newsroom.tiktok.com/en-us/how-tiktok-recommends-videos-for-you/
- [T2] TikTok for Developers, Content Posting API, Direct Post referansı (title 2.200 UTF-16; video_cover_timestamp_ms; brand_content_toggle; brand_organic_toggle; is_aigc; 6 istek/dk; unaudited = private): https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
- [T3] TikTok for Developers, Content Sharing Guidelines (filigran yasağı, ticari içerik beyanı, Music Usage Confirmation, gizlilik ve etkileşim UX): https://developers.tiktok.com/doc/content-sharing-guidelines
- [T4] TikTok for Developers, Photo Post referansı (auto_add_music; başlık 90, açıklama 4.000): https://developers.tiktok.com/doc/content-posting-api-reference-photo-post
- [T5] TikTok for Developers, Get Started, Direct Post: https://developers.tiktok.com/docs/en/content-posting-api-get-started
- [T6] TikTok for Developers, Media Transfer Guide (video özellikleri, 10 dk, 4 GB): https://developers.tiktok.com/docs/en/content-posting-api-media-transfer-guide
- [T7] TikTok for Developers, Query Creator Info (max_video_post_duration_sec, spam_risk_too_many_posts): https://developers.tiktok.com/doc/content-posting-api-reference-query-creator-info
- [T8] TikTok Ads Yardım, "How to use the Commercial Music Library", güncelleme Tem 2026: https://ads.tiktok.com/resources/help/article/how-to-use-the-commercial-music-library?lang=en
- [T9] TikTok Ads Yardım, "About the Commercial Music Library", güncelleme Tem 2025: https://ads.tiktok.com/help/article/commercial-music-library?lang=en
- [T10] TikTok Ads Yardım, "Types of TikTok Accounts", güncelleme May 2026: https://ads.tiktok.com/help/article/tiktok-and-tiktok-business-account-types
- [T11] TikTok Ads Yardım, "About TikTok account entitlements", güncelleme May 2026: https://ads.tiktok.com/help/article/about-tiktok-account-entitlements
- [T12] TikTok Ads Yardım, "About business verification for TikTok accounts", güncelleme Haz 2026: https://ads.tiktok.com/help/article/tiktok-business-account-features?lang=en
- [T13] TikTok Newsroom, "New labels for disclosing AI-generated content", 19 Eyl 2023: https://newsroom.tiktok.com/en-us/new-labels-for-disclosing-ai-generated-content
- [T14] TikTok Newsroom, "Partnering with our industry to advance AI transparency and literacy" (C2PA otomatik etiket), 9 May 2024: https://newsroom.tiktok.com/en-us/partnering-with-our-industry-to-advance-ai-transparency-and-literacy
- [T15] TikTok Newsroom, "More ways to spot, shape and understand AI-generated content", 19 Kas 2025: https://newsroom.tiktok.com/more-ways-to-spot-shape-and-understand-ai-generated-content-sg?lang=en-SG
- [T16] TikTok Newsroom, "Helping people spot and understand AI-generated content on TikTok", 10 Tem 2026: https://newsroom.tiktok.com/helping-people-spot-and-understand-ai-generated-content-on-tiktok?lang=en-GB
- [T17] TikTok Shop Academy (ABD), "AI-Generated Content Restrictions and Requirements", 09/02/2026: https://seller-us.tiktok.com/university/essay?knowledge_id=491489038501663&lang=en
- [T18] TikTok Newsroom, "Get inspired with Creator Search Insights", 13 Mar 2024: https://newsroom.tiktok.com/en-us/creator-search-insights
- [T19] TikTok Newsroom, "New AI-powered tools to make it easier to create and share on TikTok", 28 Eki 2025 (bağlam; kullanılmadı): https://newsroom.tiktok.com/new-ai-powered-tools-to-make-it-easier-to-create-and-share-on-tiktok?from_seo_redirect=1&lang=en
- [T20] TikTok Newsroom, "More ways to discover new content and creators you love" (Smart Keyword Filters), 3 Haz 2025: https://newsroom.tiktok.com/more-ways-to-discover-new-content-and-creators-you-love?lang=en
- [T21] TikTok Newsroom, Topluluk Kuralları güncellemesi (For You uygunluğu hesap düzeyinde), 22 Nis 2024: https://newsroom.tiktok.com/cgupdate?lang=en-ZA
- [T22] TikTok Newsroom, "Helping creators understand our rules with refreshed Community Guidelines", 21 Mar 2023 (bağlam): https://newsroom.tiktok.com/community-guidelines-update?lang=en
- [T23] TikTok Ads Yardım, "Search Ads Creative" (ÜCRETLİ arama reklamı; organik kanıt değil), güncelleme Oca 2026: https://ads.tiktok.com/help/article/search-ads-creative
- [T24] TikTok for Business blog, "Data-driven tips to make your organic content stand out", 14 Ara 2021: https://ads.tiktok.com/business/en-US/blog/data-driven-tips-make-organic-content-stand-out
- [T25] TikTok for Business blog, "Where Brand Discovery Thrives: TikTok As A Search Destination", 6 May 2024: https://ads.tiktok.com/business/en/blog/discovery-search-brands-break-through
- [T26] TikTok for Business, "Small Business Marketing" rehberi (tarihsiz, © 2026): https://ads.tiktok.com/business/en-US/guides/small-business-marketing
- [T27] TikTok for Business blog, "TikTok Creative Strategy Guide for Small Businesses" (tarihsiz, © 2026): https://ads.tiktok.com/business/en/blog/tiktok-creative-strategy-small-business

İkincil (resmî bilgiyi aktaran haber veya araç belgesi):
- [T30] Social Media Today, hashtag sınırı, 17 Ağu 2025: https://www.socialmediatoday.com/news/tiktok-implements-five-hashtag-limit-per-post/757857/
- [T31] MediaPost, "Maximum 5 hashtags" uyarısı, 21 Ağu 2025: https://www.mediapost.com/publications/article/408371
- [T32] OnlineMarketing.de, açıklama 4.000 karakter, 4 Ağu 2023: https://onlinemarketing.de/social-media-marketing/tiktok-captions-limit-4000-zeichen
- [T33] Lindsey Gamble, açıklama 300'den 2.200'e (tarihsiz): https://lindseygamble.com/blog/tiktok-expands-the-character-limit-for-video-descriptions
- [T34] Social Media Today, Creative Center hashtag aramasının kaldırılması, 8 Oca 2024: https://www.socialmediatoday.com/news/tiktok-implements-restrictions-hashtag-search-creative-center/703956/
- [T35] Social Media Today, profil linki 1.000 takipçi, 1 Haz 2020: https://www.socialmediatoday.com/news/tiktok-limits-and-restrictions-infographic/578999/
- [T36] Shopify blog, TikTok bio linki şartları, 20 Tem 2026: https://www.shopify.com/blog/how-to-add-link-to-tiktok-bio
- [T37] RocketLink, TikTok bio linki şartları, 10 Tem 2026: https://rocketlink.io/blog/tiktok-link-in-bio-requirements
- [T38] Engadget, For You uygunluk güncellemesi, 17 Nis 2024: https://www.engadget.com/tiktok-is-trying-to-clean-up-its-for-you-recommendations-210057825.html
- [T39] Vista Social yardım, "Promotional Content Disclosure on TikTok" (tarihsiz): https://support.vistasocial.com/hc/en-us/articles/41057119178523-Promotional-Content-Disclosure-on-TIkTok
- [T40] Metricool yardım, "Why was my TikTok video posted without sound?", 14 May 2026: https://help.metricool.com/why-was-my-tiktok-video-posted-without-sound-ao9cw
- [T41] Metricool yardım, "Schedule and Post on TikTok": https://help.metricool.com/schedule-and-post-on-tiktok-bkepi
- [T42] Metricool yardım, "API Limitations per Social Network": https://help.metricool.com/api-limitations-per-social-network-n7zlr
- [T43] Metricool yardım, "TikTok Publishing and Upload Troubleshooting Guide": https://help.metricool.com/tiktok-publishing-and-upload-troubleshooting-guide-3ywdt
- [T44] Pixabay, SSS (sosyal medya, ticari kullanım, otomatik sessize alma): https://pixabay.com/service/faq/
- [T45] Pixabay blog, Reels ve TikTok için içerik, 18 Ara 2024 (bağlam): https://pixabay.com/blog/posts/how-to-use-pixabay-content-for-engaging-reels-and-357/

Çekilemeyen resmî sayfalar (içerik kullanılmadı):
- https://www.tiktok.com/community-guidelines/en/fyf-standards/?cgversion=2023 (robots.txt)
- https://www.tiktok.com/creator-academy/en/article/ai-generated-content-label (robots.txt)
- https://www.tiktok.com/tns-inapp/pages/ai-generated-content (robots.txt)
- https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content (boş sayfa döndü)
- https://support.tiktok.com/en/getting-started/setting-up-your-profile/linking-another-social-media-account (boş sayfa döndü)
- https://support.tiktok.com/vi/using-tiktok/growing-your-audience/creator-search-insights (robots.txt)
- https://www.tiktok.com/legal/page/global/music-usage-confirmation/en (araç izni yok)

Veri dosyaları: `avz/sosyal_veri/README.txt`, `tiktok.csv`, `screenshots/tiktok_01_results.jpg`, `tiktok_02_results.jpg`, `tiktok_04_results.jpg`, `tiktok_06_suggestions.jpg`, `tiktok_06_results.jpg`, `tiktok_creative_center_us_30d_no_search.jpg`, `youtube_google_autocomplete.csv` (çift sayımları Python ile), `pinterest.csv`, `pinc/S1, S1b, S2, S3, S4/PIN_CIFT_*.csv` (çift sayımı Python ile yeniden yapıldı: compatibility 66/78), `arastirma/INSTAGRAM_CLAUDE.md`, `arastirma/PINTEREST_CLAUDE.md` (yalnız biçim ve tutarlılık).
