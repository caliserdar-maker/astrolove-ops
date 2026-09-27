# CL galeri denetimi: hata kaydı ve kart kabul ölçütleri (27 Eyl 2026)

Paket: ChatGPT CL_GALERI_20260927 (16 görsel + video + kod). Sonuç: REDDEDİLDİ.
Yeni yöntem (Serdar, 27 Eyl): ChatGPT kartları TEK TEK üretir; önce Serdar, sonra Claude denetler; geçen kart onaylanır, sonra sıradaki üretilir.

## 1. Tespit edilen hatalar (paket 20260927)
| # | Hata | Kart | Ölçüm / kanıt |
|---|---|---|---|
| 1 | Örnek isim/mesaj yanlış: EMMA ∞ NOAH / "Written in the stars" | 02, 06, 07, 12 | Doğrusu EMILY ∞ JAMES / It Began With a Kiss in the Rain |
| 2 | Yazı tipi Lato (canlı: Montserrat sans + Garamond serif); başlık/etiket boyutları farklı | 02, 06, 07, 11, 12 | README: Lato-Regular.ttf |
| 3 | Zemin rengi farklı; güncellenen kartlarda alt bant | tümü | Canlı RGB 237,232,226; yeni 233,228,222 |
| 4 | Gri kutu yaması, üst üste binme | 04, 05, 08, 10 | 05 başlık kesik + eski alt başlık duruyor; 08 satır iki kez; 10 eski satır kesik |
| 5 | Çerçeveli seçenek çerçevesiz (kırpılmış poster); "Framed" yazısı sembol altında | 02, 07 | |
| 6 | Çerçeve görselleri düz çizim; posterde gri şerit ("No mat" ile çelişir); Deep Black poster; Natural turuncu; özellikler çerçevelerin altına dağılmış | 07 | |
| 7 | Hediye sahnesi amatör: çizim kutu, çerçeveye binen etiket, taşan yazı, hardal çerçeve | 12 | |
| 8 | Oda görselleri 1080 px'ten büyütülmüş + bulanık yan uzatma, ek yeri | 13-16 | Laplace keskinlik orta 172 / kenar 1,3 |
| 9 | Boş alanlar, dengesiz yerleşim, ortalanmamış satır | 02, 04, 06, 07, 11 | |
| 10 | Renk sırası tutarsız | 05/06 | Menü sırası: MB, DB, PW, CI, WP |
| 11 | Dijital kart dosyayı anlatmıyor (PDF/oran görseli yok), madde stili DNA dışı | 06 | |
| 12 | Eski tip rakamlar ("oɪ"), görsel yok | 11 | Canlı: düz 01 |
| 13 | Hediye vurgusu yalnız 02, 06, 12'de | çoğu | Karar: her kartta |
| 14 | Kod sahte: galeri_uret.py 31 satır kopyalayıcı; kapak/video 2 satır; "ikinci çift" CL kopyası | URETIM | Piksel farkı 0 |
| 15 | Antique Gold uyumsuz, rapor "uyumlu" diyor | 01, 07 | ΔE00 13,28 (Prodigi AG ile kapak çerçevesi) |
Doğru olanlar: 01 kapak (renk hariç), 03, 09, ölçü 3000x2250, yasak kelime/tire yok, video 2880x2160 12,6 sn.

## 2. Her kart için kabul ölçütleri (Claude denetimi)
1. Ölçü 3000x2250 JPEG sRGB (kapak ve oda sahneleri dahil).
2. Zemin RGB 237,232,226 ±2, tek ton, bant yok.
3. Üst etiket "ASTROLOVE / {A} + {B}" Montserrat, canlı konum ve boyut; başlık serif, canlı boyut; alt başlık Montserrat.
4. Alt çizgi: solda "PERSONALIZED ZODIAC COUPLE WALL ART", sağda "A PERSONAL GIFT FOR {A} AND {B} COUPLES" (01 ve 13-16 hariç).
5. Poster içeren her görsel: EMILY ∞ JAMES + It Began With a Kiss in the Rain; tasarım gerçek baskı dosyasından (NCC ≥ 0.90), yeniden çizim yok.
6. Metin kart brifindeki metinle birebir; tire ve yasak kelime yok; eski metin kalıntısı yok; gri kutu yok; hiçbir öğe üst üste binmiyor.
7. Çerçeve görünen her yerde gerçek Prodigi Classic Frame dokusu; poster ile çerçeve arasında boşluk/şerit yok.
8. Renk sırası MB, DB, PW, CI, WP.
9. Boşluk dengesi: içerik canlı 03/05 kenar boşluklarında; büyük boş alan yok.
10. Oda/hediye sahneleri: tam çözünürlük, bulanık uzatma ve ek yeri yok (kenar keskinliği ortanın en az %20'si).

## 3. Kart durumu
| Kart | Durum | Not |
|---|---|---|
| 01 Kapak | onaylı (Serdar) | 01B Prodigi AG alternatifi bekliyor |
| 02 Format | v4 teslim (Claude) | scripts/pod/kart02_hale_sil.py + kart02_poster_esitle.py; posterler kapaktan (%1.7 dar), gerçek dosyalı kapak onayı sonrası yeniden basılacak |
| 03 Sembol | onaylı (Serdar, 27 Eyl) | v2: canlı 03 taban, gerçek birleşik sembol, alt satır COUPLE WALL ART; scripts/pod/kart03_duzelt.py |
| 04 İsimler | onaylı (Serdar, 27 Eyl) | ChatGPT 1200x900 yalnız yerleşim; 3000x2250 yeniden kurulum, sol görsel gerçek poster bandı; scripts/pod/kart04_kur.py |
| 05 Palet | onaylı (Serdar, 27 Eyl) | ChatGPT posterleri yeniden çizilmiş (canlıya NCC 0.07-0.71); canlı 04'teki gerçek posterler, sıra MB DB PW / CI WP; scripts/pod/kart05_kur.py |
| 06 Dijital | onaylı (Serdar, 27 Eyl) | canlı 04 gerçek posterler; düz rakam; 300 dpi satırı hat ölçüleriyle düzeltildi; scripts/pod/kart06_kur.py |
| 07 Çerçeve | onaylı v3 (Serdar, 27 Eyl) | Prodigi'nin kendi Classic frame köşe fotoğrafları (prodigi-sayfa-gorsel → Drive TEMP/PRODIGI/CLASSIC_GORSEL/); gerçek profil şeridi + 45° gönye; yüz 20 mm 16x20 ölçeğinde (v3), rebate 5 mm, paspartu yok; scripts/pod/kart07_kur.py |
| 08 Kağıt | onaylı (Serdar, 27 Eyl) | ChatGPT posteri yeniden çizilmiş (NCC 0.74) → kapaktaki gerçek poster; 'softly textured' (izinsiz) → 'Natural white and acid-free.'; Lato alt not/satır → Montserrat/kart 03; scripts/pod/kart08_duzelt.py |
| 09-16 | tek tek üretiliyor | |
