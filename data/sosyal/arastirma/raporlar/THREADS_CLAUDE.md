# AstroLoveArt Threads Araştırması (Claude, 12 Eki 2026)

Kapsam: yalnız Threads. Threads'e özel veri toplanmadı; anahtar kelimeler Instagram ve Pinterest verisinden (platformlar arası). Meta'nın Threads akış sıralama sayfası bu ortamda okunamadı (içerik gelmedi), sıralama ayrıntıları **doğrulanmadı**.

## A. Resmî ve doğrulanmış bilgiler
| Konu | Bilgi | Bizim için | Kaynak |
|---|---|---|---|
| Metin | API'de en fazla 500 karakter. | Şablon 161-177 karakter. | [S1] |
| Karusel | 2 ile 20 öğe, görsel ve video karışık olabilir. Görsel: JPEG/PNG, en fazla 8 MB, genişlik 320-1440 px. | 4 slaytlık 1080x1350 karuselimiz uygun. | [S1] |
| Video | MP4/MOV, H.264, AAC, 23-60 fps, en fazla 300 sn, 1 GB; 9:16 önerilir. | 24 sn Reel videomuz uygun. | [S1] |
| Konu etiketi | Gönderi başına tek konu etiketi, 1-50 karakter, nokta ve "&" kullanılamaz. | "Zodiac Compatibility". | [S1][S2] |
| Link eki | `link_attachment` yalnız metin gönderilerinde; gönderi başına en fazla 5 benzersiz link. | Karuselde link eki yok; metinde "on Etsy". Linkin metin içinde tıklanabilir olup olmadığı karusel için doğrulanmadı. | [S1] |
| Günlük sınır | Profil başına 24 saatte 250 gönderi; karusel 1 sayılır. | Günde 1 gönderi, sınırın çok altında. | [S1] |
| Etiket arama | Etiketli gönderiler arama ile bulunur (ikincil, 2023). | Konu etiketi her gönderide aynı. | [S2] |

## B. Anahtar kelimeler (platformlar arası)
- "{çift} compatibility": Pinterest'te Cancer'sız 66 çiftin 66'sında, YouTube'da 78/78 (bkz. Pinterest ve YouTube raporları). Konu etiketi bu yüzden "Zodiac Compatibility".
- "zodiac couple", "personalized gift": Instagram raporu B bölümü.

## C. Şablon (karusel, 4 slayt)
```text
TEXT: {SIGN_A} & {SIGN_B}, as one? Two zodiac signs become one shared gold symbol, with your two names and your message. Zodiac couple art by AstroLoveArt, made for you on Etsy.
TOPIC TAG: Zodiac Compatibility
ALT TEXT: Instagram karuseliyle aynı 4 alt metin.
```
Format önerisi: Threads'e günde 1 karusel (21:00). Video ayrıca gönderilmez (aynı gün 4 platformda zaten var); etkisi doğrulanmadı.
78 çiftin hepsi: `data/sosyal/metin/THREADS_78.csv`.

## D. Örnekler
```text
Gemini & Leo, as one? Two zodiac signs become one shared gold symbol, with your two names and your message. Zodiac couple art by AstroLoveArt, made for you on Etsy.
```

## E. Kurallar
- Etkileşim tuzağı yok ("tag your partner", "comment your sign").
- Yapay zekâ etiketi: duvar sahnesi yapay zekâyla üretildi. Meta'nın "AI info" etiketi kuralı Facebook raporunda; Threads'e özel kural doğrulanmadı.

## F. Eksik
- Threads akış sıralama belgesi okunamadı. Link içeren karusel gönderilerin dağıtımı doğrulanmadı. İlk 2 haftanın Metricool verisiyle bakılacak.

## G. Kaynaklar
- [S1] Threads API, posts: https://developers.facebook.com/docs/threads/posts
- [S2] Engadget (16 Kas 2023, ikincil), Threads tags: https://www.engadget.com/threads-introduces-tags-to-help-users-categorize-posts-092650879.html
