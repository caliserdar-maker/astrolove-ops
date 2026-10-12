# AstroLoveArt Facebook Araştırması (Claude, bağımsız)

Tarih: 12 Ekim 2026 · Kapsam: yalnız Facebook (Sayfa gönderisi ve Facebook Reels) · Veri: `data/sosyal/arastirma/veri/*.csv` (11 Eki 2026), `data/sosyal/arastirma/pinterest_cift/PIN_CIFT_*.csv` (12 Eki 2026).

Okuma kuralı: "not shown / gösterilmedi" = toplanmadı, sıfır değil. Kaynakla doğrulayamadığım her şey **doğrulanmadı** diye işaretli. Satır referansı: `dosya / seed / data_type / rank → text`. Kaynak numaraları G bölümünde. Facebook için hiç veri toplanmadı; B bölümündeki her satır **platformlar arası** sinyaldir, Facebook kanıtı değildir.

Önemli erişim notu: `facebook.com/help`, `facebook.com/business/help`, `facebook.com/legal` ve `help.instagram.com` sayfaları bu ortamdan **çekilemedi** (robots engeli veya yalnız meta veri döndü). `transparency.meta.com` sayfaları (Feed ve Reels sistem kartları, "Types of content we demote") yalnız başlık döndürdü (JavaScript ile yükleniyor). Bu sayfaların içeriğini hafızadan doldurmadım; G bölümünde "çekilemedi" diye listeli.

---

## Kısa sonuç (7 madde)

1. **Açıklamada link koyma.** Facebook'un kendi Creators blogu: "captions with no links, minimal use of capital letters, and no more than five hashtags perform best" [F1]. Ayrıca Meta, ücretli abonelik (Meta Verified / Meta One) olmayan profesyonel hesap ve Sayfalarda **ayda 2 link gönderisi** sınırını test ediyor; Aralık 2025'te başladı, Eylül 2026'da genişledi (ikincil kaynak) [F17][F18]. Metricool: sınır Sayfa bazında Meta tarafından konuyor, Metricool aşamaz; ilk yorumdaki linkler de sayılabilir [F21].
2. **Hashtag en fazla 5, ilgili olsun** [F1]. Facebook'ta hashtag'in dağıtıma etkisi resmî olarak **doğrulanmadı**. Önerim 3 adet (C).
3. **4 görsel Facebook'ta karusel değil, ızgara.** Meta (9 Ara 2025): "when you post multiple photos, they'll be arranged in a standardized grid" [F6]. Organik Sayfada kaydırmalı gerçek karusel yalnız API'deki **çoklu link karuseli** (`child_attachments`, 2-5 link) [F14]; Metricool bunu desteklemiyor [F20] ve önizleme özelleştirmesi yalnız Sayfanın sahibi olduğu alan adında mümkün (Etsy bizim değil) [F14]. Sonuç: slayt 1'deki "Swipe to reveal" Facebook'ta anlamsız.
4. **Reel ana format.** Meta Haziran 2025'te Facebook'taki tüm videoların Reels olarak paylaşılacağını, uzunluk ve biçim kısıtı olmayacağını duyurdu [F4]. API ile Reel: 3-90 sn, 9:16, 1080x1920 önerilen, 24-60 FPS, 24 saatte 30 Reel [F12]. Bizim 24 sn 9:16 Reel uygun.
5. **Özgünlük.** Sayfa sahibinin ürettiği içerik "original" sayılır [F2]. Başka uygulamanın filigranı (ör. TikTok indirmesi) olmayan temiz dosya yükle; kopya videoların dağıtımı azaltılır [F1].
6. **Etkileşim tuzağı yok.** Meta'nın kendi örneği tam bizim alan: "LIKE this if you're an Aries!" etkileşim tuzağıdır ve tekrar eden Sayfalara daha sert düşürme uygulanır [F10]. "Tag your partner", "Comment your sign" gibi çağrılar şablonda yok.
7. **Önerilen çift başı format:** (a) 24 sn Reel, (b) 3 görselli fotoğraf gönderisi (slayt 2, 3, 4; slayt 1 çıkar çünkü "Swipe" ızgarada çalışmaz). Izgara düzeni resmî olarak belgelenmedi: toplu yayından önce Sayfada 1 test gönderisiyle telefonda kontrol.

---

## A. Facebook Sayfa gönderilerini ve Reels'i nasıl dağıtıyor (kaynaklı)

| Öğe | Resmî bilgi | Bizim için anlamı | Kaynak |
|---|---|---|---|
| **Sıralama genel** | Meta'nın yapay zekâ sistemleri "predict how valuable a piece of content might be to you"; paylaşım "often an indicator that you found that post to be interesting". Feed, Stories, Reels için 22 sistem kartı yayınlandı. Kullanıcı "Show more, Show less" ile akışı yönlendirebiliyor. Sistem kartlarının kendisi çekilemedi. | Paylaşılabilir, değerli içerik. Kesin sinyal ağırlıkları **doğrulanmadı**. | [F7], ikincil özet [F22] |
| **Reels önerileri (Eki 2025)** | Öneri motoru "surfacing 50% more reels from creators published that day"; ilgi alanlarını daha hızlı anlıyor; "Not interested" ve Kaydet (Save) gelecekteki önerileri şekillendiriyor; arkadaş balonları (friend bubbles) arkadaşın beğendiği Reel'leri gösteriyor. | Taze içerik öne çıkıyor: düzenli Reel yayını mantıklı. Kaydetme sinyal. Sıklık için resmî sayı yok. | [F5] |
| **Video = Reel (Haz 2025)** | "all videos on Facebook will be shared as reels"; "Reels on Facebook will also not have any length or format restrictions"; Sayfalara da uygulanıyor; öneriler değişmiyor. | Reel dışında ayrı "video" formatı düşünmeye gerek yok. | [F4] |
| **Uygulama içi Reel uzunluğu ve API** | Uygulamada uzunluk kısıtı yok [F4]. API ile yayında 3-90 sn [F12]; Metricool da 3-90 sn [F19][F20]. | 24 sn: her iki yolda uygun. | [F4][F12][F19] |
| **Açıklama (caption)** | "Keep your captions and hashtags relevant to the content." "Captions with no links, minimal use of capital letters, and no more than five hashtags perform best." | Linksiz, büyük harf yağmuru yok, en fazla 5 hashtag, içerikle ilgili. | [F1] |
| **Linkler** | Aralık 2025 testi: professional mode ve Sayfalar; ekran görüntüsüne göre ayda 2 link, yorumdaki linkler sınırsız, publisher Sayfaları hariç (TechCrunch) [F17]. Eylül 2026: test genişledi, bazı hesaplar ayda 2 link gönderisiyle sınırlı, Meta One aboneliği ile açılıyor (ikincil) [F18]. Metricool: medya eklenirse link metinde görünür, önizleme oluşmaz; sınır uygulanırsa Facebook Sayfada bildirim gösterir; ilk yorumdaki linkler de sayılabilir [F21]. Yorumlardaki link konusunda TechCrunch ile Metricool **çelişiyor**. Meta'nın resmî yardım sayfası çekilemedi. | 78 çift gönderisinde URL yok. Görselli gönderide link zaten önizleme vermez [F21]. Link gerekiyorsa ayda en fazla 2 bilinçli link gönderisi (mağaza). Sayfada sınır bildirimi var mı, Serdar'ın bakması gereken tek şey (F). | [F1][F17][F18][F21] |
| **Hashtag** | En fazla 5, içerikle ilgili [F1]. API: Reel `description` "Supports hashtags" [F12]. Facebook Yardım "How do I use hashtags on Facebook?" sayfası var ama çekilemedi. Hashtag'in Facebook dağıtımına ya da aramasına etkisi **doğrulanmadı**. | 3 hashtag (C.3). | [F1][F12] |
| **Özgün içerik** | 14 Tem 2025: başkasının içeriğini tekrar tekrar kullanan hesaplar monetizasyonu kaybeder ve "reduced distribution on everything they share"; kopya videoların dağıtımı azaltılır; "Avoid using visible third party watermarks and content that is visibly recycled from other apps or sources"; "avoid super short videos that offer viewers little value". 13 Mar 2026: "Content filmed or produced directly by a creator or owner of a Profile or Page is considered original content"; özgün olmayan Reel'ler "deprioritized in Feed and Reels"; itiraz hakkı var. Professional Dashboard'da gönderi bazında dağıtım nedeni görülebilir. Creators: "Creators receive the greatest distribution when they primarily post content that is filmed or created by them." | Tasarımlar bizim: özgün. TikTok'tan indirilen filigranlı dosya değil, ana dışa aktarım dosyası yüklenmeli. Aynı Reel'i aynı Sayfaya iki kez yükleme. "Super short" tanımı yok; 24 sn için risk **doğrulanmadı**. | [F1][F2][F3] |
| **Öneri Kuralları (Recommendation Guidelines)** | Uymayan içerik platformda kalır ama öneri yerlerinde gösterilmez [F8]. Kategoriler (ikincil liste, 2020): clickbait, engagement bait, "Contests and/or giveaways", düşük kaliteli veya aldatıcı açılış sayfasına link, "Unoriginal content, largely repurposed from another source", sağlık iddiaları vb. [F9]. Yardım sayfası (facebook.com/help/1257205004624246) çekilemedi. | Çekiliş (giveaway) gönderileri öneriye uygun olmayabilir. Şablonlarda yok. | [F8][F9] |
| **Content Distribution Guidelines (düşürülen içerik)** | Sayfa (transparency.meta.com, arama başlığına göre "Updated Jul 2, 2025") çekilemedi. İkincil özet (2021): ad farm, clickbait, engagement bait, gereksiz veri isteme, düşük kaliteli tarama deneyimi, alan adını gizleme, özgün içerik [F23]. | İçerik listesini resmî kaynaktan doğrulayamadım; yalnız ikincil. | [F23] |
| **Etkileşim tuzağı** | "LIKE this if you're an Aries!" örneği; yorumlardaki ve videonun sesindeki etkileşim tuzağı da düşürülür; sistematik kullanan Sayfalara "stricter demotions". Yardım, tavsiye istemek etkilenmez. | Burç içeriğinde en büyük risk bu. "Like if", "Tag", "Comment your sign", "Share if" yok. Reel sesinde de yok. | [F10] |
| **Arama** | Ara 2025: arama sonuçları "a more immersive grid layout that supports all content types"; tam ekran görüntüleyici test ediliyor [F6]. Eki 2025: bazı Reel'lerde yapay zekâ destekli önerilen aramalar [F5]. Açıklama metninin Facebook aramasında anahtar kelime olarak eşleştiği resmî olarak **doğrulanmadı**. | Çift adını ilk satırda doğal biçimde yazmak (platformlar arası veriye dayalı, B). Etkisi doğrulanmadı. | [F5][F6] |
| **Çoklu fotoğraf görünümü** | Ara 2025: çoklu fotoğraf "standardized grid" içinde; gönderiye tıklayınca tam ekran [F6]. Kaydırmadan söz edilmiyor. 4:5 dört görselin ızgarada nasıl kırpıldığı **doğrulanmadı**. | "Swipe to reveal" Facebook'ta yanıltıcı. C.5'teki 3 görsel önerisi. | [F6] |
| **Yapay zekâ etiketi** | "AI info" etiketi, sektör standardı yapay zekâ işaretleri tespit edilince veya kullanıcı beyan edince konuyor. Yalnız yapay zekâyla düzenlenen içerikte etiket menüye taşındı (Eyl 2024); yapay zekâ aracıyla üretilen içerikte etiket görünür kalıyor. Etiketin dağıtıma etkisi sayfada yok. | Slayt 3 duvar sahnesi yapay zekâ ile üretildiyse etiket çıkabilir. Etki **doğrulanmadı**. | [F11] |

---

## B. Verimiz: en güçlü kelimeler (platformlar arası, satır referanslı)

### B.1 Veri uyarıları

- **Facebook verisi toplanmadı.** README'de Facebook yok (`veri/README.txt`, "CONTENTS" ve "COVERAGE AND LIMITATIONS"). Bu bölümdeki hiçbir satır Facebook arama hacmi göstermez.
- En yakın sinyal Instagram (aynı şirket, aynı hesap bağlantısı), ama Instagram satırları **hesap sonuçları**dır, arama terimi önerisi değil; giriş yapılmış, kişiselleştirilmiş oturumdan (README "ordinary ... searches used the signed-in sessions").
- Pinterest çift dosyalarında sayımı kendim yaptım (iki sıra birleşik, 78 çift): "compatib" öneri 66/78, chip 66/78; "gift" 0/78. Cancer çiftlerinde Pinterest çoğunlukla öneri vermedi (ör. `PIN_CIFT_S2 / cancer and libra / suggestion / not shown`); bu sıfır değil.
- YouTube `pair` sorgularının 78/78'inde "compatibility" geçen öneri var (benim sayımım).

### B.2 Öncelik tablosu (Facebook metni için)

| # | Kelime | Kanıt satırları (platformlar arası, Facebook değil) | Kullanım |
|---|---|---|---|
| 1 | **"{A} and {B}"** | Instagram: `instagram.csv / gemini and leo / suggestion / 1 → gemini.and.leo gemini and leo`; `/ cancer and libra / suggestion / 2 → cancerandlibra cancer & libra`; `/ scorpio and pisces / suggestion / 1 → scorpio.and.pisces.love Scorpio and Pisces`. YouTube: `youtube_google_autocomplete.csv / prefix / gemini and / 3 → gemini and leo`; `/ prefix / pisces and / 1 → pisces and scorpio`; `/ pair / cancer and libra / 1 → cancer and libra`. Pinterest: `PIN_CIFT_S2 / gemini and leo / suggestion / 1-12`. | İlk satırda ve gövdede. Görselde "&", metinde "and". |
| 2 | **"{A} and {B} compatibility"** | YouTube `pair` 78/78, ör. `/ pair / gemini and leo / 3 → gemini and leo compatibility`, `/ pair / cancer and libra / 2 → cancer and libra compatibility`, `/ pair / pisces and scorpio / 2 → pisces and scorpio compatibility`. Pinterest 66/78, ör. `PIN_CIFT_S2 / gemini and leo / suggestion / 2`, `PIN_CIFT_S4 / pisces and scorpio / suggestion / 5`. Instagram `zodiac compatibility / suggestion / 1-5`. Google `seed / zodiac couple / 2 → zodiac couple compatibility`. | Gövdede bir kez: "compatibility art". |
| 3 | **zodiac couple (art)** | Pinterest `pinterest.csv / zodiac couple / suggestion / 1 → zodiac couples art`; Google `seed / zodiac couple / 1 → zodiac couples`; Instagram `#zodiaccouple / hashtag_posts / 1000+`, `zodiac couple / suggestion / 1 → astroloveart AstroLoveArt | Zodiac Couple Art` (kişiselleştirilmiş, sıralama kanıtı değil). | Gövdede "zodiac couple art"; hashtag #zodiaccouple. |
| 4 | **zodiac art** | Instagram `#zodiacart / hashtag_posts / 126B`; Pinterest çiftlerde "art" öneri 50/78 (ör. `PIN_CIFT_S2 / gemini and leo / suggestion / 4 → gemini and leo art`). | Hashtag #zodiacart. |
| 5 | **personalized gift** | Instagram `#personalizedgift / hashtag_posts / 1,900.000`; Pinterest `pinterest.csv / personalized couple gift / suggestion / 1 → personalized couple gifts`, `/ 8 → personalized wedding gifts for couple etsy`. | Gövdede "personal gift"; hashtag #personalizedgift. |
| 6 | **anniversary / engagement / wedding** | Pinterest `anniversary gift / trend / 2026-10` (tepe ayı), `engagement gift / trend / 2026-07`; TikTok `tiktok.csv / anniversary gift / suggestion / 1-8`, `engagement gift / suggestion / 1-8`, `wedding gift for couple / suggestion / 1-8`. | Gövdede tek cümle. Hashtag yok. |
| X | tattoo, friendship, memes, tarot | Pinterest "tattoo" öneri 76/78, "friendship" 70/78; `PIN_CIFT_S4 / scorpio and pisces / suggestion / 9 → scorpio and pisces relationship memes`; YouTube `/ pair / gemini and leo / 4 → gemini and leo love tarot today`. | Ürün değil. Kullanma. |
| X | constellation | Pinterest "constellation" öneri 42/78 (ör. `PIN_CIFT_S2 / gemini and leo / suggestion / 11`). | Ürün takımyıldız posteri değil. Kullanma. |

---

## C. Şablonlar

Kurallar: Facebook'un önerisine göre linksiz, en fazla 5 hashtag, az büyük harf [F1]. Etkileşim tuzağı yok [F10]. Uzun ve orta tire yok, "+" yok, marka AstroLoveArt. Ürün iddiası yok (kâğıt, çerçeve, ölçü, fiyat, "best seller" yok; constellation yok). 78 çiftin tamamı Python ile üretildi ve sayıldı: gönderi 403-451 karakter (1. satır 54-70), Reel 243-275 (1. satır 60-76), Reel başlığı 18-34, alt metin 131-191. Hepsinde tire ve "+" denetimi PASS.

Karakter sınırları: Facebook'un kendi gönderi metni sınırı resmî olarak **doğrulanmadı**; Metricool kendi editöründe 16.192 diyor [F19][F20]. "See more" kesim noktası **doğrulanmadı**; bu yüzden ilk satır 76 karakteri geçmiyor.

### C.1 Fotoğraf gönderisi metni (3 görsel: slayt 2, 3, 4)

```text
{SIGN_A} and {SIGN_B}, as one? Two signs become one gold symbol.

Our {SIGN_A} and {SIGN_B} zodiac couple art merges both signs into one gold symbol on navy. We add your two names and your personal message, so it becomes your own {SIGN_A} and {SIGN_B} compatibility art for your wall.

A personal gift for an anniversary, engagement or wedding.

Make it yours: search AstroLoveArt on Etsy.

#zodiaccouple #zodiacart #personalizedgift
```
Dayanak: B.2 #1-#6. Instagram metninden farkları: "Swipe" yok (ızgara [F6]), "link in bio" yok (Instagram kavramı), "Save this..." yok (Facebook'ta Kaydet sinyali var [F5] ama çağrının etkileşim tuzağı sayılıp sayılmadığı **doğrulanmadı**; güvenli taraf).

### C.2 Reel açıklaması

```text
{SIGN_A} and {SIGN_B}, as one? Watch two signs become one gold symbol.

{SIGN_A} and {SIGN_B} compatibility art with your names and your personal message, designed by AstroLoveArt.

Find it on Etsy: search AstroLoveArt.

#zodiaccouple #zodiacart #personalizedgift
```
Reel başlığı (API `title` alanı [F12]; Metricool "Add title" destekliyor [F20]):
```text
{SIGN_A} & {SIGN_B}, as one?
```
Başlığın Facebook Reels arayüzünde nerede göründüğü **doğrulanmadı**.

### C.3 Hashtag

```text
#zodiaccouple #zodiacart #personalizedgift
```
- Facebook sınırı: "no more than five" en iyi performans [F1]. 3 seçmem benim kararım (kısa ve en ürün özgül üç etiket, B.2 #3-#5); 3 ile 5 arasında fark olduğu **doğrulanmadı**.
- Instagram setiyle (5 etiket) aynı olmak zorunda değil; Metricool'da ağ bazında ayrı metin. Metricool'un tek gönderide ağ başına farklı metin desteği **doğrulanmadı** (F).
- Genel dev etiketler (#giftideas, #walldecor) yok; Facebook "relevant to the content" diyor [F1].

### C.4 Alt metin (her görsel)

```text
Slide 2. The {SIGN_A} sign and the {SIGN_B} sign in gold on navy, and one gold symbol that merges both signs, with two sample names below. Text on the image reads: Two signs, Your shared symbol.

Slide 3. A room scene with the personalized {SIGN_A} and {SIGN_B} poster on a wall: one gold merged symbol on navy with two names and a short message.

Slide 4. Close-up of the poster showing the gold {SIGN_A} and {SIGN_B} symbol and two sample names. Text on the image reads: Make it yours, AstroLoveArt, On Etsy.
```
Slayt 1 kullanılırsa:
```text
A navy background with gold zodiac art. Text on the image reads: {SIGN_A} & {SIGN_B}, as one? Zodiac art with your names & message. Swipe to reveal.
```
- API: her fotoğrafa `alt_text_custom` [F13]. Metricool: "Click the ALT button to add alt text" [F19].
- Facebook alt metin karakter sınırı **doğrulanmadı**. Reels için alt metin alanı API belgesinde yok [F12].
- Görselleri görmedim: slayt metinleri ve "two sample names" gerçek görsele göre düzeltilmeli. Slayt 3 yapay zekâ sahnesi olduğu için "room scene" yazdım, gerçek fotoğraf iddiası yok.

### C.5 Link yerleşimi

1. 78 çift gönderisinde ve Reel'de **URL yok**; metinde "search AstroLoveArt on Etsy" [F1][F21].
2. Etsy mağaza linki Sayfa profilinde (web sitesi alanı / eylem düğmesi). Bu alanların link sınırına dahil olmadığı resmî olarak **doğrulanmadı** (yardım sayfaları çekilemedi).
3. Link gönderisi gerekiyorsa ayda en fazla 2 (sınır uygulanıyorsa) [F17][F18]: mağaza veya mevsimsel koleksiyon. İlk yoruma link koymak sınırı aşmanın yolu değil; Metricool sayılabileceğini söylüyor [F21].

### C.6 Çift başına önerilen format

| Sıra | Format | Neden | Kaynak |
|---|---|---|---|
| 1 | **Reel, 24 sn, 9:16, 1080x1920, sesli** | Video = Reel; taze Reel'ler öneride öne çıkıyor; API ve Metricool 3-90 sn kabul ediyor. | [F4][F5][F12][F19] |
| 2 | **Fotoğraf gönderisi, 3 görsel (slayt 2, 3, 4)** | Facebook çoklu fotoğrafı ızgarada gösteriyor; "Swipe to reveal" yazılı slayt 1 ızgarada yanlış talimat olur. Soru kancası metnin ilk satırında. | [F6] |
| Seçenek | Slayt 1'in Facebook sürümü ("Swipe to reveal" yerine başka alt yazı) ile 4 görsel | Ek üretim ister. Hangisinin daha iyi performans verdiği verisi yok. | - |
| Kullanma | Çoklu link karuseli | Metricool desteklemiyor; Etsy alan adı bizim olmadığı için görsel özelleştirilemiyor. | [F14][F20] |

Görsel boyutu: 1080x1350 JPEG. Graph API dosya sınırı 10 MB, PNG için 1 MB altı öneriliyor [F13]; Metricool 30 MB diyor [F19] (çelişki, düşük olanı al). Metricool: "Mixing formats is not allowed" (aynı gönderide fotoğraf ve video karışmaz) [F19].

---

## D. Doldurulmuş örnekler (karakter sayıları Python ile)

### D.1 Gemini & Leo

Fotoğraf gönderisi (412 karakter; 1. satır 57):
```text
Gemini and Leo, as one? Two signs become one gold symbol.

Our Gemini and Leo zodiac couple art merges both signs into one gold symbol on navy. We add your two names and your personal message, so it becomes your own Gemini and Leo compatibility art for your wall.

A personal gift for an anniversary, engagement or wedding.

Make it yours: search AstroLoveArt on Etsy.

#zodiaccouple #zodiacart #personalizedgift
```
Reel (249; 1. satır 63) ve başlık (21):
```text
Gemini and Leo, as one? Watch two signs become one gold symbol.

Gemini and Leo compatibility art with your names and your personal message, designed by AstroLoveArt.

Find it on Etsy: search AstroLoveArt.

#zodiaccouple #zodiacart #personalizedgift
```
```text
Gemini & Leo, as one?
```
Alt metin (178 / 134 / 146):
```text
Slide 2. The Gemini sign and the Leo sign in gold on navy, and one gold symbol that merges both signs, with two sample names below. Text on the image reads: Two signs, Your shared symbol.
Slide 3. A room scene with the personalized Gemini and Leo poster on a wall: one gold merged symbol on navy with two names and a short message.
Slide 4. Close-up of the poster showing the gold Gemini and Leo symbol and two sample names. Text on the image reads: Make it yours, AstroLoveArt, On Etsy.
```

### D.2 Cancer & Libra

Fotoğraf gönderisi (418; 1. satır 59):
```text
Cancer and Libra, as one? Two signs become one gold symbol.

Our Cancer and Libra zodiac couple art merges both signs into one gold symbol on navy. We add your two names and your personal message, so it becomes your own Cancer and Libra compatibility art for your wall.

A personal gift for an anniversary, engagement or wedding.

Make it yours: search AstroLoveArt on Etsy.

#zodiaccouple #zodiacart #personalizedgift
```
Reel (253; 1. satır 65) ve başlık (23):
```text
Cancer and Libra, as one? Watch two signs become one gold symbol.

Cancer and Libra compatibility art with your names and your personal message, designed by AstroLoveArt.

Find it on Etsy: search AstroLoveArt.

#zodiaccouple #zodiacart #personalizedgift
```
```text
Cancer & Libra, as one?
```
Alt metin (180 / 136 / 148):
```text
Slide 2. The Cancer sign and the Libra sign in gold on navy, and one gold symbol that merges both signs, with two sample names below. Text on the image reads: Two signs, Your shared symbol.
Slide 3. A room scene with the personalized Cancer and Libra poster on a wall: one gold merged symbol on navy with two names and a short message.
Slide 4. Close-up of the poster showing the gold Cancer and Libra symbol and two sample names. Text on the image reads: Make it yours, AstroLoveArt, On Etsy.
```
Not: Pinterest bu çiftte öneri göstermedi (`PIN_CIFT_S2 / cancer and libra / suggestion / not shown`), ama YouTube'da var (`/ pair / cancer and libra / 2 → cancer and libra compatibility`) ve Instagram'da hesap sonuçları var (`instagram.csv / cancer and libra / suggestion / 1-5`).

### D.3 Pisces & Scorpio

Fotoğraf gönderisi (424; 1. satır 61):
```text
Pisces and Scorpio, as one? Two signs become one gold symbol.

Our Pisces and Scorpio zodiac couple art merges both signs into one gold symbol on navy. We add your two names and your personal message, so it becomes your own Pisces and Scorpio compatibility art for your wall.

A personal gift for an anniversary, engagement or wedding.

Make it yours: search AstroLoveArt on Etsy.

#zodiaccouple #zodiacart #personalizedgift
```
Reel (257; 1. satır 67) ve başlık (25):
```text
Pisces and Scorpio, as one? Watch two signs become one gold symbol.

Pisces and Scorpio compatibility art with your names and your personal message, designed by AstroLoveArt.

Find it on Etsy: search AstroLoveArt.

#zodiaccouple #zodiacart #personalizedgift
```
```text
Pisces & Scorpio, as one?
```
Alt metin (182 / 138 / 150):
```text
Slide 2. The Pisces sign and the Scorpio sign in gold on navy, and one gold symbol that merges both signs, with two sample names below. Text on the image reads: Two signs, Your shared symbol.
Slide 3. A room scene with the personalized Pisces and Scorpio poster on a wall: one gold merged symbol on navy with two names and a short message.
Slide 4. Close-up of the poster showing the gold Pisces and Scorpio symbol and two sample names. Text on the image reads: Make it yours, AstroLoveArt, On Etsy.
```
Not: Sıra alfabetik ("Pisces and Scorpio"). Veride iki sıra da var: `PIN_CIFT_S4 / pisces and scorpio / suggestion / 5 → pisces and scorpio compatibility` ve `/ scorpio and pisces / suggestion / 3`; YouTube `prefix / scorpio and / 2 → scorpio and pisces`, `prefix / pisces and / 1 → pisces and scorpio`. Hangisinin Facebook'ta daha çok arandığı **doğrulanmadı**.

---

## E. Resmî olarak belgelenmiş kurallar (bizi ilgilendiren)

1. **Yapay zekâ etiketi (slayt 3 duvar sahnesi).** Meta, sektör standardı yapay zekâ işaretleri tespit edince veya kullanıcı beyan edince "AI info" etiketi koyuyor; yapay zekâ aracıyla üretilen içerikte etiket görünür, yalnız düzenlenmiş içerikte menüde [F11]. Etiketin dağıtıma etkisi belgede yok (**doğrulanmadı**). Öneri: dosyadaki işaretleri silmeye çalışma; alt metin ve metin gerçek fotoğraf iddiası taşımasın (C.4 "room scene").
2. **Instagram'dan çapraz paylaşım.** Instagram Yardım'da "Share Instagram reels to Facebook", "Fix problems sharing Instagram reels to Facebook", "How to crosspost to a Facebook Page with Instagram" sayfaları var ama **çekilemedi**; koşulları (müzik, Sayfa bağlantısı) **doğrulanmadı**. Metricool ise Facebook'a API ile ayrı yükleme yapıyor (Facebook için ayrı içerik türleri ve özellikler listeliyor [F19][F20]). Özgünlük: Sayfa sahibinin ürettiği içerik özgün [F2]; Facebook içinde kopya videonun dağıtımı azaltılır [F1]. Öneri: Instagram'daki "Facebook'ta da paylaş" otomatik ayarı ile Metricool'un Facebook yayınını **aynı anda açık tutma**, aynı Reel Sayfaya iki kez düşer. Ayarın yeri ve varsayılanı **doğrulanmadı**.
3. **Sayfa Reels'inde müzik.** Meta Music Recommendations API: "Business Facebook Pages may see limited results returned" [F16]. Yani işletme Sayfalarında müzik kataloğu kısıtlı olabilir. Sound Collection ve Music Guidelines sayfaları var ama çekilemedi. Öneri: kullanım hakkı bizde olan sesi videonun içine gömülü (orijinal ses) olarak yükle; Instagram'da uygulama içinden eklenen popüler şarkı Facebook'a taşınmayabilir (**doğrulanmadı**). Reel sesinde etkileşim tuzağı yok [F10].
4. **Reel teknik özellikleri (API).** MP4 önerilir; 9:16; 1080x1920 önerilen, en az 540x960; 24-60 FPS; H.264/H.265; ses AAC-LC, 48 kHz, stereo, 128 kbps üstü; 3-90 sn; 24 saatte 30 API Reel'i; yalnız Sayfalara yayın; gizlilik yalnız "Public"; `description` hashtag destekler; `title` alanı var; zamanlama en az 10 dk sonra, en fazla 29 gün [F12]. Metricool: Reels 3-90 sn, en az 540x960, 1.91:1 ile 9:16 arası, 23-60 FPS; Sayfada Hikâye olarak paylaşılan Reel 60 sn'yi geçemez [F19]. Reel kapağı API belgesinde yok; Metricool "Add cover / thumbnail" destekli diyor [F20].
5. **Çoklu fotoğraf (API).** Her fotoğraf `published=false` ile `/page-id/photos`'a yüklenir; dönen kimliklerle `/page-id/feed` üzerinden çoklu fotoğraf gönderisi yapılır; zamanlanmış gönderide `published`, `scheduled_publish_time`, `unpublished_content_type` gerekir; yayınlanmayan fotoğraflar 24 saatte silinir; `alt_text_custom` her fotoğrafa; dosya en fazla 10 MB [F13]. `/page-id/feed`: `link` veya `message` zorunlu; zamanlama aralığı referansta "10 minutes and 75 days", kılavuzda "10 minutes and 30 days" (**çelişki**) [F14][F15]. Metricool: gönderi başı 35 görsele kadar, ALT destekli, ilk yorum destekli, "Hashtag search" ve kişi etiketleme yok [F19][F20].
6. **Link alanı ve önizleme.** API `link` alanı; önizleme (görsel, başlık) özelleştirmesi yalnız Sayfanın sahibi olduğu alan adında; `call_to_action` düğmesi link gönderisine eklenebilir, linki `link` ile aynı olmalı [F14]. Metricool: medya ekli gönderide link yalnız metinde kalır, önizleme olmaz; link "https://" ile başlamalı; Metricool kısaltıcısı açıksa linkleri kısaltır [F21].
7. **Kolaj ve karusel.** Çoklu fotoğraf standart ızgara [F6]. Organik "karusel" yalnız çoklu link karuseli (`child_attachments` 2-5, `multi_share_end_card`) [F14]; Metricool desteklemiyor [F20].
8. **Etkileşim tuzağı ve öneri dışı içerik.** Bkz. A [F8][F9][F10]. Çekiliş gönderileri öneri dışı kalabilir [F9].

---

## F. Eksik veri ve açık sorular

1. **Facebook verisi yok:** arama önerisi, hashtag sayısı, Sayfa takipçisi, İçgörüler (erişim, izleme süresi, kaydetme, paylaşım, link tıklaması) toplanmadı. B'deki tüm sıralama platformlar arasıdır.
2. **Link sınırı Sayfamıza uygulanıyor mu?** Metricool: uygulanırsa Facebook Sayfada bildirim gösterir [F21]. Bildirimin var olup olmadığı **doğrulanmadı**. Görselli gönderinin metnindeki URL'nin "link gönderisi" sayılıp sayılmadığı **doğrulanmadı**.
3. **Izgara düzeni:** 3 veya 4 adet 4:5 görselin Facebook ızgarasında kırpılışı belgelenmedi. Toplu yayından önce 1 test gönderisi, telefonda gerçek görünüm (Serdar kuralı: önce örnek).
4. **Çekilemeyen resmî sayfalar:** Transparency Center Feed ve Reels sistem kartları, "Types of content we demote", Facebook Yardım hashtag ve Öneri Kuralları sayfaları, Music Guidelines, Sound Collection, Instagram çapraz paylaşım sayfaları. Bunlardaki ayrıntılar (ör. sinyal listeleri, müzik kuralları) **doğrulanmadı**.
5. **Facebook gönderi metni sınırı** ve **"See more" kesim noktası** resmî olarak **doğrulanmadı** (Metricool 16.192 kendi editör sınırı).
6. **Alt metin sınırı** ve Reels'te alt metin **doğrulanmadı**.
7. **Hashtag'in Facebook aramasına ve dağıtımına etkisi** **doğrulanmadı**; yalnız "≤5 en iyi performans" bilgisi resmî [F1].
8. **"Super short videos"** tanımı yok; 24 sn'nin bu kapsamda olup olmadığı **doğrulanmadı** [F1].
9. **Yapay zekâ etiketinin erişime etkisi** belgede yok [F11].
10. **Metricool'da ağ başına ayrı metin** (Instagram ve Facebook için farklı açıklama, farklı görsel seti) desteği bu araştırmada **doğrulanmadı**. Desteklemiyorsa Facebook için ayrı gönderi planlanmalı.
11. **Instagram otomatik "Facebook'ta paylaş" ayarı** açık mı, bilinmiyor; Metricool ile çift yayın riski (E.2).
12. **Paylaşım saati ve sıklığı** için resmî kaynak bulamadım; yalnız "aynı gün yayınlanan Reel'ler daha çok öneriliyor" bilgisi var [F5].
13. Slayt görsellerini görmedim; alt metinler gerçek görsele göre son kez kontrol edilmeli.

---

## G. Kaynaklar

Resmî (Meta / Facebook), çekildi:
- [F1] Facebook Creators blog, "Combating unoriginal content", 14 Tem 2025 (≤5 hashtag, linksiz açıklama, az büyük harf, filigran, kopya video, çok kısa video): https://creators.facebook.com/blog/combating-unoriginal-content
- [F2] Facebook Creators blog, "Supporting original content on Facebook", 13 Mar 2026: https://creators.facebook.com/blog/supporting-original-content-on-facebook
- [F3] Facebook Creators, Best practices: https://creators.facebook.com/create/best-practices
- [F4] Meta Newsroom, "Making it Easier to Create Videos on Facebook", 17 Haz 2025: https://about.fb.com/news/2025/06/making-it-easier-create-videos-facebook/
- [F5] Meta Newsroom, "Finding and Sharing Reels on Facebook Just Got Easier and More Fun", 7 Eki 2025: https://about.fb.com/news/2025/10/finding-sharing-reels-facebook-just-got-easier-more-fun/
- [F6] Meta Newsroom, "Making it Easier to Create, Discover, and Share Content on Facebook", 9 Ara 2025: https://about.fb.com/news/2025/12/making-it-easier-to-create-discover-and-share-content-on-facebook/
- [F7] Meta Newsroom, Nick Clegg, "How AI Influences What You See on Facebook and Instagram", 29 Haz 2023: https://about.fb.com/news/2023/06/how-ai-ranks-content-on-facebook-and-instagram/
- [F8] Meta Newsroom, "Recommendation Guidelines", 31 Ağu 2020: https://about.fb.com/news/2020/08/recommendation-guidelines/
- [F10] Meta Newsroom, "Fighting Engagement Bait on Facebook", 18 Ara 2017: https://about.fb.com/news/2017/12/news-feed-fyi-fighting-engagement-bait-on-facebook/
- [F11] Meta Newsroom, "Our Approach to Labeling AI-Generated Content and Manipulated Media", 5 Nis 2024 (güncellemeler 1 Tem 2024, 12 Eyl 2024): https://about.fb.com/news/2024/04/metas-approach-to-labeling-ai-generated-content-and-manipulated-media/
- [F12] Meta for Developers, Reels Publishing API: https://developers.facebook.com/documentation/video-api/guides/reels-publishing.md
- [F13] Meta for Developers, Graph API Page Photos referansı: https://developers.facebook.com/docs/graph-api/reference/page/photos
- [F14] Meta for Developers, Graph API Page Feed referansı: https://developers.facebook.com/docs/graph-api/reference/page/feed
- [F15] Meta for Developers, Pages API Posts kılavuzu: https://developers.facebook.com/docs/pages-api/posts
- [F16] Meta for Developers, Music Recommendations for Videos and Reels: https://developers.facebook.com/docs/video-api/guides/music-recommendations

Metricool, çekildi:
- [F19] Metricool Help, "Schedule and publish on Facebook": https://help.metricool.com/schedule-and-publish-on-facebook-ycu1b
- [F20] Metricool Help, "Scheduling and Posting Options by Social Network": https://help.metricool.com/scheduling-and-posting-options-by-social-network-cwmb3
- [F21] Metricool Help, "Scheduling content with links": https://help.metricool.com/en/article/scheduling-content-with-links-54x5sb/

İkincil (resmî sayfa çekilemediği için, öyle etiketli):
- [F9] Social Media Today, Öneri Kuralları kategori listesi, 31 Ağu 2020: https://www.socialmediatoday.com/news/facebook-provides-an-overview-of-content-that-it-looks-to-exclude-from-its/584442
- [F17] TechCrunch, "Facebook is testing a link posting limit for professional accounts and pages", 17 Ara 2025: https://techcrunch.com/2025/12/17/facebook-is-testing-a-link-posting-limit-for-professional-accounts-and-pages
- [F18] Social Media Today, "Facebook Pages get charged for link posts", 17 Eyl 2026: https://www.socialmediatoday.com/news/facebook-pages-get-charged-for-link-posts/
- [F22] Search Engine Land, "How Facebook ranks content in 2023", 29 Haz 2023: https://searchengineland.com/how-facebook-ranks-content-2023-feed-stories-reels-428837
- [F23] Press Gazette, Content Distribution Guidelines özeti, 24 Eyl 2021 (güncelleme 30 Eyl 2022): https://pressgazette.co.uk/news/facebook-shares-publisher-dos-and-donts-to-avoid-content-demotion-in-user-news-feeds/

Resmî ama çekilemedi (içerik kullanılmadı, yalnız varlığı not edildi):
- Types of content we demote (arama başlığı "Updated Jul 2, 2025"): https://transparency.meta.com/features/approach-to-ranking/types-of-content-we-demote/
- Facebook Feed sistem kartı: https://transparency.meta.com/features/explaining-ranking/fb-feed
- Facebook Reels sistem kartı: https://transparency.meta.com/features/explaining-ranking/fb-reels/
- How do I use hashtags on Facebook?: https://www.facebook.com/help/587836257914341
- Öneri Kuralları (Yardım): https://www.facebook.com/help/1257205004624246
- Meta Music Guidelines: https://www.facebook.com/legal/music_guidelines
- Use Sound Collection for reels on Facebook: https://www.facebook.com/business/help/880459498798521
- How does automatic alt text work on Facebook?: https://www.facebook.com/help/216219865403298
- Share Instagram reels to Facebook: https://help.instagram.com/459497729122868
- Fix problems sharing Instagram reels to Facebook: https://help.instagram.com/1206864193634431
