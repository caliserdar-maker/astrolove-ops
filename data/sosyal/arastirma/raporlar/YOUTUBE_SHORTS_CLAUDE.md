# AstroLoveArt YouTube Shorts Araştırması (Claude, 12 Eki 2026)

Kapsam: yalnız YouTube Shorts. Veri: `veri/youtube_google_autocomplete.csv` (toplama yöntemi README'de yazmıyor). Doğrulanamayan her şey **doğrulanmadı** diye işaretli. Kaynaklar G bölümünde.

## A. Resmî kurallar (kaynaklı)
| Konu | Resmî bilgi | Bizim için | Kaynak |
|---|---|---|---|
| Shorts sayılma | Kare veya dikey, 3 dakikaya kadar video Shorts sayılır. | 24 sn 9:16 videomuz Short. | [S1] |
| Arama | Sıralama: başlık, açıklama ve videonun aramayla ne kadar eşleştiği; etkileşim de sayılır. | Çift adı ve "compatibility" başlıkta ve açıklamada. | [S2] |
| Öneri | İzlenen/izlenmeyen, beğeni, "ilgilenmiyorum" sinyalleri; kısa videolarda göreli izlenme süresi daha önemli. | Videonun sonuna kadar izlenmesi önemli; 24 sn bu yüzden iyi. | [S2] |
| Hashtag | Başlık üstünde en ilgi çeken en fazla 3 hashtag görünür; 60'tan fazla hashtag varsa hepsi yok sayılır; alakasız hashtag videonun kaldırılmasına yol açabilir. | Açıklamanın sonunda tam 3 hashtag. | [S3] |
| Etiket (tags) | Başlık, küçük resim ve açıklama daha önemli; etiketler küçük rol oynar, çoğunlukla sık yanlış yazılan kelimelerde işe yarar. | Kısa, alakalı 5 etiket; ağırlık başlık ve açıklamada. | [S4] |
| API sınırları | Başlık en fazla 100 karakter, açıklama 5.000 bayt, etiketler toplam 500 karakter. `selfDeclaredMadeForKids`, `containsSyntheticMedia` alanları var. | Şablonlarımız sınırın çok altında. | [S5] |
| Link | Shorts açıklama ve yorumlarındaki URL'ler tıklanamaz. Kanal profiline en fazla 14 link eklenebilir. "Related video" yalnız YouTube videosuna bağlanır. | Metinde "search AstroLoveArt on Etsy". Etsy linki kanal profiline bir kez eklenmeli. | [S6][S7] |
| Yapay zekâ beyanı | Beyan gereken: "gerçekte olmamış gerçekçi bir sahne üretmek". Gerekmeyen: gerçek dışı içerik, animasyon, küçük estetik düzenlemeler. | Duvar sahnesi yapay zekâyla üretilmiş gerçekçi bir oda: `containsSyntheticMedia = true` (temkinli seçim). Altın toz animasyonu kodla yapıldı, beyan gerektirmez. | [S8] |
| Müzik ve Content ID | 1 dakikadan uzun ve aktif telif talebi olan Shorts dünya çapında engellenir; 1 dakikadan kısalar bu kuraldan etkilenmez. | Videomuz 24 sn: talep gelse bile engellenmez. | [S1] |
| Pixabay ve Content ID | Pixabay lisans sertifikası (.txt) ile YouTube'da itiraz yapılır: "License" nedeni seçilir, sertifika metni yapıştırılır; süre 30 güne kadar; reddedilse de kanala ihtar gelmez. | Müzik 2'nin Pixabay sayfasında Content ID "not shown". Talep gelirse sertifikayla itiraz. Sertifika Pixabay'e girişle indirilir (doğrulanmadı: bizim hesapta indirilmiş mi). | [S9][S10] |

## B. Verimiz
- `youtube_google_autocomplete.csv`: "{çift} compatibility" 78 çiftin 78'inde öneri (31 çiftte 1. sıra, 43'ünde 2. sıra). En güçlü kelime budur. Çift sorguları alfabetik ("pisces and scorpio").
- Aynı dosyada "tarot" (77), "relationship" (76), "friendship" (67), "marriage" (50), "couple" (24) da çıkıyor. Tarot ve friendship ürünle ilgisiz, kullanılmaz.
- Hashtag sayısı verimiz yok; seçilen 3 hashtag Pinterest ve Instagram verisinden (platformlar arası, doğrulanmadı).

## C. Şablonlar
```text
TITLE: {SIGN_A} and {SIGN_B} Compatibility Art, Two Zodiac Signs as One Symbol
DESCRIPTION: {SIGN_A} and {SIGN_B}, as one? Watch the {SIGN_A} and {SIGN_B} zodiac signs become one shared gold symbol. This zodiac couple art adds your two names and a personal message, made by AstroLoveArt. A personalized gift idea for an anniversary, engagement or wedding. Make it yours: search AstroLoveArt on Etsy.

#zodiaccompatibility #zodiaccouple #zodiacart
TAGS: {sign_a} and {sign_b} compatibility, {sign_a} and {sign_b}, zodiac compatibility, zodiac couple art, personalized zodiac gift
```
Ayarlar: kategori 26 (Howto & Style, seçim bizim, doğrulanmadı), made for kids = false, containsSyntheticMedia = true. Oynatma listeleri: 12 burç listesi (her çift iki listeye) önerisi, etkisi doğrulanmadı.
78 çiftin hepsi: `data/sosyal/metin/YOUTUBE_SHORTS_78.csv` (başlık 61-77, açıklama 334-366, etiket 101-133 karakter).

## D. Örnekler
```text
Gemini and Leo Compatibility Art, Two Zodiac Signs as One Symbol
Cancer and Libra Compatibility Art, Two Zodiac Signs as One Symbol
Pisces and Scorpio Compatibility Art, Two Zodiac Signs as One Symbol
```

## E. Yapılacak tek seferlik iş
- Kanal profiline Etsy mağaza linki (Serdar, 1 dk) ya da Metricool/YouTube API ile (API ile mümkün mü: doğrulanmadı).

## F. Eksik
- YouTube'da hashtag ve arama hacmi verisi yok. Kategorinin etkisi doğrulanmadı. Pixabay sertifikası indirilmedi.

## G. Kaynaklar
- [S1] YouTube Help, Shorts up to 3 minutes: https://support.google.com/youtube/answer/15424877
- [S2] YouTube Help, discovery and performance FAQs: https://support.google.com/youtube/answer/141805
- [S3] YouTube Help, hashtags: https://support.google.com/youtube/answer/6390658
- [S4] YouTube Help, tags: https://support.google.com/youtube/answer/146402
- [S5] YouTube Data API, videos resource: https://developers.google.com/youtube/v3/docs/videos
- [S6] YouTube Help, sharing links: https://support.google.com/youtube/answer/13748639
- [S7] YouTube Help, related video in Shorts: https://support.google.com/youtube/answer/14075157
- [S8] YouTube Help, altered or synthetic content: https://support.google.com/youtube/answer/14328491
- [S9] Pixabay blog (20 Ara 2021), Content ID claim with license certificate: https://pixabay.com/blog/posts/how-to-clear-a-youtube-content-id-claim-with-a-pix-190/
- [S10] Pixabay content license summary: https://pixabay.com/service/license-summary/
