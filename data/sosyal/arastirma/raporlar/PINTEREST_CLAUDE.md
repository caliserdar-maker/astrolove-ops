# AstroLoveArt Pinterest Araştırması (Claude, bağımsız)

Tarih: 12 Ekim 2026 · Kapsam: yalnız Pinterest · Veri: `sosyal_veri/pinterest.csv` (11 Eki 2026), `pinterest_hesap_analitigi/` (Analytics 11.09-11.10.2026), `youtube_google_autocomplete.csv` (yalnız platformlar arası sinyal)

Okuma kuralı: "gösterilmedi / not shown" = toplanmadı, sıfır değil. Doğrulayamadığım her şey **doğrulanmadı** diye işaretli. Satır referansı biçimi: `seed / data_type / rank → text`.

---

## Kısa sonuç (5 madde)

1. Pinterest arama, Pin'i şu metinlerden anlıyor: **Pin başlığı + açıklaması, kaydedildiği pano başlıkları, linkteki sayfanın (Etsy ilanı) başlığı ve açıklaması, görselden üretilen otomatik açıklama, Pin'e tıklatan arama sorguları** (Pinterest mühendislerinin makalesi [S19], Pinterest topluluk duyurusu [S20]). Hashtag bu listede yok.
2. Doğrulanmış sınırlar: **başlık 100**, **alt metin 500**, **açıklama 500 (güvenli)**. Resmî kaynaklarda açıklama için hem 800 [S1] hem 500 [S2][S6] geçiyor; toplu CSV 500'de kesiyor, o yüzden 500 altı. Başlığın **ilk 40 karakteri** en çok görünen kısım [S2]. Açıklama ana akışta ve arama akışında **görünmüyor** [S1], yani okunmak için değil, aranmak için yazılır.
3. Verimizdeki en güçlü kelime: **"{çift} compatibility"**. Toplanan 4 çiftin 4'ünde Pinterest önerisi, 3'ünde kategori baloncuğu, üst kategori "zodiac compatibility" Trends'te var. YouTube'da 78 çiftin 77'sinde aynı (yalnız platformlar arası sinyal). Ardından: **"{çift} art / couple art"**, **"zodiac wall art"**, **"combined"** (birleşik sembol).
4. Hashtag: bugün işe yaradığını gösteren **resmî güncel kaynak bulamadım** (doğrulanmadı). Önerim: **hashtag kullanmamak**. Bunun yerine, Pinterest'in kendi alanı olan **etiketli konular (tagged topics, en fazla 10)** [S5] kullanılabiliyorsa kullanılmalı.
5. Acil bulgu: Metricool'da bekleyen 57 Pin'in başlığı `A Personalized Anniversary Gift for a/an ...` ile başlıyor. Çift adı 37-39. karakterden sonra geliyor, yani görünen ilk 40 karakterin dışında kalıyor. Yayına çıkmadan başlıkta çift adı başa alınmalı (bkz. B.2).

---

## A. Pinterest'te arama ve dağıtımı ne etkiliyor (kaynaklı)

| Öğe | Resmî bilgi | Bizim için anlamı | Kaynak |
|---|---|---|---|
| **Başlık** | En fazla 100 karakter. İlk 40 karakter en çok görünen kısım (reklam yaratıcı rehberi). Arama sisteminin kullandığı metin alanlarından biri. | Çift adı ve ana ürün kelimesi ilk 40 karakterde olmalı. Ekran görüntülerimizde masaüstü ızgarada başlıklar ~28-30 karakterde kesiliyor (örn. `Gemini And Leo Compatibility:...`, `pinterest_21_suggestions.jpg`). | [S1] [S2] [S6] [S19] |
| **Açıklama** | 800 (Pin özellikleri sayfası [S1], Metricool [S28]) ama 500 (toplu CSV [S6], yaratıcı rehber [S2]). Ana akışta ve arama akışında gösterilmez [S1]. Pinterest: "başlık ve açıklamaya ilgili anahtar kelimeleri ekleyin" [S7]. | 500 altında tut. Doğal cümle, alakalı kelime. Alakasız kelime doldurma, topluluk kurallarında **spam** [S14]. | [S1] [S2] [S6] [S7] [S14] |
| **Alt metin** | En fazla 500 karakter. Yardım sayfası: yalnız ekran okuyucu kullananlara okunur, "görselde ne görünüyorsa onu anlat" [S3][S4]. Pinterest Create SEO rehberi ise anahtar kelimeleri "açıklayıcı alt metne bile" eklemeyi söylüyor [S8]. | Önce görseli doğru tarif et, çift adını ve "zodiac" kelimesini doğal geçir. Aramaya etkisi resmî olarak **doğrulanmadı** (iki kaynak farklı söylüyor). | [S3] [S4] [S8] |
| **Pano adı / açıklaması** | Pano başlıkları arama sinyali [S19][S20]. "Kısa, kesilmeyecek, ilgili anahtar kelimeli pano başlığı"; açıklamaya ilgili kelimeler; pano veya bölüm başına 20-100 Pin [S7]. | Pano adı = ürün kelimesi. Ad sınırı 50 karakter **yalnız ikincil kaynakta** [S27], resmî **doğrulanmadı**. | [S7] [S19] [S20] [S27] |
| **Görsel üstü yazı** | Ana mesaj üstte, detay altta; logo veya marka adı görünür ama baskın değil; 2:3, 1000×1500 önerisi (reklam rehberi) [S2]. "Her Pin'e yazı gerekmez" [S7]. Görsel üstü yazının arama için okunduğu (OCR) resmî olarak **doğrulanmadı**. Belgelenen: görselden otomatik başlık üretimi [S19], görseldeki nesne adları [S25 ikincil]. | Mevcut P1/P3 yazıları uyumlu. P2'de çift adı yok, görselde yalnız semboller var. P2'ye `GEMINI & LEO` eklenmesini öneririm (karar sende). | [S2] [S7] [S19] [S25] |
| **Link** | "Pin ile açıkça ilgili ek içerik sunan sayfaya link verin", kırık link vermeyin [S9]. Linklenen sayfanın başlığı ve açıklaması arama sinyali [S19]. Etsy sayfaları rich pin için ek kod istemez, ürün bilgisi siteden senkronlanır [S10][S11]. | Her Pin kendi Etsy ilanına. **Etsy ilan başlığı ve açıklaması da Pinterest sinyalidir**: Pin sayfası verimizde 5 Pin'in 3'ünde Pin açıklaması yerine Etsy'nin uzun ilan açıklaması görünüyor (`64_PIN_SAYFA.csv`). | [S9] [S10] [S11] [S19] |
| **Tazelik / tekrar** | Aynı Pin'leri tekrar tekrar kaydetmek veya Pinterest'te zaten olan içeriği yüklemek spam sayılıp geçici engel getirebilir [S9]. Pinterest topluluk ekibi (PinterestLuan, 6 Mar 2026): aynı URL'ye birden çok Pin olur, ama **her Pin farklı görünmeli** (farklı tasarım, şablon veya yazı); yayınlanmış Pin'i yeniden kullanmak önerilmez [S21]. Aynı siteden hızlı ve çok Pin kaydı hız sınırını tetikleyebilir [S15]. Takvim 45-60 gün önceden planlanmalı [S7]. | P1/P2/P3 = aynı ilana 3 farklı görsel, farklı günlerde. Kurala uygun. Aynı Pin'i başka panolara kopyalayarak doldurma. | [S7] [S9] [S15] [S21] |
| **Etkileşim ve mevsim** | Dağıtım etkileşime göre; dil, konum, mevsim, tatil, format ve trend konular etkiler; Pin'ler mevsimsel geri dönebilir [S9]. | Yıldönümü, Sevgililer Günü gibi dönemler için önceden yayın. | [S9] |
| **Hashtag** | 2017 duyurusu: hashtag akışı açıldı, en taze Pin'ler üstte [S18]. Güncel Pin oluşturma yardımı yalnız "mobilde açıklamaya hashtag da ekleyebilirsiniz" diyor [S5]. Güncel bir **fayda** beyanı bulamadım (doğrulanmadı). İkincil kaynak (Ocak 2025): artık tıklanabilir değil, Pinterest artık önermiyor [S24]. | Kullanma. Arama sinyali listesinde yok [S19][S20]. Fazlası kelime doldurmaya kayar [S14]. | [S5] [S14] [S18] [S19] [S24] |
| **Etiketli konular** | Pin başına en fazla 10 ilgili konu: "benzer fikirler arayanların Pin'inizi bulmasına yardımcı olur" [S5]. Toplu CSV'de konu sütunu yok; Pinterest topluluk ekibi Ocak 2026'da talebi iletti [S22]. Metricool'da var mı: **doğrulanmadı** [S28]. | Mümkünse her Pin'e ekle (aday liste C.4'te). | [S5] [S22] [S28] |
| **Yapay zekâ etiketi** | Pinterest, GenAI ile üretildiğini veya değiştirildiğini tespit ettiği Pin'leri etiketliyor. Kullanıcı ev dekorasyonu ve sanat gibi kategorilerde "daha az GenAI" görmeyi seçebiliyor [S17]. Aramada "Daha Az Yapay Zeka" filtresi var [S16] (ekran görüntülerimizde de görünüyor). | P1 oda sahneleri yapay zekâyla üretiliyorsa bazı kullanıcılarda daha az görünebilir. Etkinin büyüklüğü **doğrulanmadı**. | [S16] [S17] |
| **Dosya adı** | Pinterest Create: anahtar kelimeleri "görsel adlarına" da ekleyin [S8]. | Örnek: `gemini-and-leo-zodiac-wall-art-astroloveart-p1.jpg` | [S8] |

Not: Metricool, Pinterest'in alt metin alanını destekliyor [S29]. Toplu CSV'de alt metin sütunu yok, "Keywords" sütunu var [S6].

---

## B. Verimiz

### B.1 Anahtar kelimeler: kanıt gücüne göre sıralı

Kanıt seviyesi: **A** = Pinterest çift düzeyi, toplanan 4 çiftin (gemini and leo, scorpio and pisces, aries and leo, taurus and virgo) tamamında + üst terim Trends'te var · **B** = Pinterest'te birden çok tohumda var ve ürüne uyuyor · **C** = tek tohum veya yalnız kategori, Trends yok · **X** = ürünle alakasız, kullanma.

| # | Kelime (kullanım biçimi) | Seviye | Kanıt satırları | Gerekçe |
|---|---|---|---|---|
| 1 | **{A} and {B} compatibility** | A | `gemini and leo / suggestion / 3`, `gemini and leo / chip / 1 → Compatibility`, `scorpio and pisces / suggestion / 4`, `aries and leo / suggestion / 3`, `aries and leo / chip / 5`, `taurus and virgo / suggestion / 3`, `taurus and virgo / chip / 4`, `zodiac compatibility / trend / yes`, `zodiac compatibility / trend / 2026-05`, `zodiac compatibility / suggestion / 10 → zodiac compatibility gemini`, `/ 11 → … leo`. Platformlar arası: YouTube `pair` sorgularında `{çift} compatibility` 78 çiftin 77'sinde öneri (eksik: gemini and pisces); Google `zodiac couple / 2 → zodiac couple compatibility`. | Tüm çift tohumlarında ilk 4 öneri içinde. Trends'te verisi olan tek burç terimi. Dikkat: bu aramada çıkan sonuçlar çoğunlukla uyum bilgi kartları (`pinterest_21_suggestions.jpg` arka plan sonuçları). Kullanıcı bilgi arıyor olabilir. Kelimeyi ürünü dürüst anlatan biçimde kullan, uyum yüzdesi veya iddiası yazma. |
| 2 | **{A} and {B} art**, **zodiac couple(s) art**, **couple art** | B+ | `gemini and leo / suggestion / 2 → gemini and leo art`, `gemini and leo / chip / 8 → Art`, `scorpio and pisces / suggestion / 2`, `taurus and virgo / suggestion / 4 → taurus and virgo couple art`, `/ 10 → … art`, `taurus and virgo / chip / 6 → Couple art`, `aries and leo / chip / 25 → Art`, `zodiac couple / suggestion / 1 → zodiac couples art`, `zodiac couple / chip / 6 → Art` | 4 çiftin 4'ünde var, 3'ünde ilk 4 sırada. Ürüne doğrudan uyuyor. |
| 3 | **zodiac wall art** | B | `zodiac wall art / suggestion / 1 → zodiac wall art print poster`, `/ 12 → zodiac sign wall art`, `/ 3,4,5,6,7,10 → leo / aries / pices / scorpio / taurus / gemini zodiac wall art`; Trends: `zodiac wall art / trend / not shown` (tam eşleşme yok, sıfır değil). Hesap: `Zodiac Couple Wall Art` panosu 1.239 gösterim, **4 dış tıklama** (`60e`, 11.09-11.10). Google: `zodiac wall art / 1`. | Ürün türünün tam adı. Hesapta dış tıklama alan tek pano. Burç başına "{sign} zodiac wall art" önerileri, burç adıyla aramanın olduğunu gösteriyor. |
| 4 | **combined zodiac symbol** | B (ürün uyumu) | `gemini and leo / suggestion / 6 → gemini and leo tattoo combined`, `gemini and leo / chip / 6 → Tattoo combined`, `scorpio and pisces / suggestion / 6 → … tattoo combined`, `/ 12 → scorpio and pisces combined wallpaper`, `taurus and virgo / suggestion / 9 → taurus and virgo tattoo combined symbol`, `/ 7, 8`, `taurus and virgo / chip / 9 → Tattoo combined symbol`, `/ 14 → Mix tattoo` | İnsanlar iki burcun **birleşik sembolünü** arıyor, bu bizim ürün fikrinin ta kendisi. Arama niyeti çoğunlukla dövme. "tattoo" ve "wallpaper" kelimelerini **kullanma** (ürün o değil). Yalnız "combined zodiac symbol" ifadesi. |
| 5 | **{A} and {B} couple**, **zodiac couple** | B | `gemini and leo / suggestion / 12 → gemini and leo couple`, `gemini and leo / chip / 9 → Couple`, `aries and leo / suggestion / 2 → aries and leo couple`, `zodiac couple / suggestion / 1-12`, `zodiac couple / chip / 1 → Best`, `/ 7 → Perfect`, `/ 10 → Signs` | Kitle çiftler. Pano adı "Zodiac Couple Wall Art" bununla uyumlu. |
| 6 | **{A} and {B} relationship** | B (hacim) / C (uyum) | `gemini and leo / suggestion / 4`, `scorpio and pisces / suggestion / 3`, `aries and leo / suggestion / 4`, `taurus and virgo / suggestion / 2`, chip'ler: `gemini and leo / 3`, `aries and leo / 3`, `taurus and virgo / 3` | Çok tutarlı ama niyet ilişki içeriği. Açıklamada bir kez, doğal geçir (P2). |
| 7 | **anniversary gift(s) for couples** | B | `anniversary gift / suggestion / 9 → anniversary gifts for couples`, `anniversary gift / chip / 13 → Ideas for couple`, `/ 23 → Couples`, `anniversary gift / trend / yes`, `anniversary gift / trend / 2026-10`, `1st anniversary gift / suggestion / 3 → 1st anniversary gifts for couple` | Trends'te var, tepe ayı **Ekim 2026** (şimdi). Gözle okunmuş tepe, sayı yok. |
| 8 | **personalized couple gift(s)** | B- | `personalized couple gift / suggestion / 1-12` (örn. `/ 3 → personalized couple gifts anniversaries`, `/ 8 → personalized wedding gifts for couple etsy`), `personalized couple gift / chip / 1 → Anniversaries`, `/ 4 → Engagement`, `wedding gift for couple / chip / 3 → Personalized`, `/ 7 → Personalised`, `newlywed gift / chip / 13 → Personalized`; hesap `63`: `couple wall art / baloncuk / 9 → Personalized` | Ürünün ayırt edici özelliği (isim + mesaj). Trends tam eşleşme yok. |
| 9 | **engagement gift(s) for couples** | B- | `engagement gift / suggestion / 2 → engagement gifts for couples`, `/ 12`, `engagement gift / chip / 3 → Couples`, `engagement gift / trend / yes`, `/ 2026-07` | Trends'te var. Tepe Temmuz. |
| 10 | **wedding gift for couple** | C+ | `wedding gift for couple / suggestion / 1-12`, `/ 7 → wedding gift for couple gold`, `/ 10 → … frame`, chip `/ 3 Personalized`; tam terim Trends'te yok, `wedding gift` hesap Trends'te var (`62_PIN_TREND.csv`) | "gold" önerisi tasarımımıza uyuyor. |
| 11 | **couple wall art** (+ **bedroom**, **living room**) | C+ | `couple wall art / suggestion / 1 → couple wall art bedrooms`, `/ 5 → … living room`, `/ 8 → … print`, `/ 12 → … for bedroom`; hesap `63`: `couple wall art / baloncuk / 2 → Bedroom`, `/ 15 → Married`; `couple bedroom decor / suggestion / 12 → couple bedroom decor ideas wall art`, `couple bedroom decor / trend / yes`, `/ 2026-05`; Google `couple wall art / 4 → couple wall art etsy` | Oda sahnesi olan P1 için. |
| 12 | **zodiac gift(s)**, **astrology gift ideas for couples** | C | `zodiac gift / suggestion / 1 → zodiac gifts ideas`, `/ 2`, `astrology gift / suggestion / 5 → astrology gift ideas for couples` | Destekleyici. |
| 13 | **gift for boyfriend / girlfriend** | C (mevsimsel) | `gift for boyfriend / trend / yes`, `/ 2025-12`, `gift for girlfriend / trend / yes`, `/ 2025-12`, `gift for boyfriend / suggestion / 3 → gift for boyfriend anniversary` | Aralık tepesi. Tek kişiye hediye niyeti. Yalnız Aralık ve Sevgililer Günü dönemi metinlerinde düşün. |
| 14 | **celestial wall art**, **astrology decor** | C- | `celestial wall art / suggestion / 3 → celestial wall art bedroom`, `celestial wall art / chip / 15 → Gold`, `astrology decor / suggestion / 7 → astrology decor bedroom`, `/ 11 → home decor astrology`; Trends: ikisi de `not shown`. İkincil: Pinterest Predicts 2026 "Extra Celestial" trendi [S26] | Zayıf. Pano adı olarak öncelikli değil. |
| X | tattoo, wallpaper, friendship, besties, siblings, anime, memes, tropes, constellation, DIY, crochet, basket | X | ör. `gemini and leo / suggestion / 1 → tattoo`, `/ 5 → friendship`, `zodiac couple / suggestion / 5 → zodiac couples art anime` | Ürün bunlar değil. Kullanmak "alakasız anahtar kelime doldurma" sayılır [S14]. |

Ekran görüntüsü kontrolü: `pinterest_20_suggestions.jpg` (gemini and leo, 12 öneri) ve `pinterest_22_suggestions.jpg` (scorpio and pisces, 12 öneri) CSV ile birebir aynı. `pinterest_trend_16_chart.jpg` (zodiac compatibility, ABD, 1 yıl) grafiği var, en yüksek nokta Mayıs 2026 civarı, CSV ile uyumlu. `pinterest_21_suggestions.jpg` (cancer and libra): öneri kutusu boş, arkada önceki aramanın (gemini and leo) sonuçları var. CSV'deki `not shown` doğru.

### B.2 Hesap analitiği ne gösteriyor

- **30 gün (11.09-11.10):** 10,99 bin gösterim, 315 Pin tıklaması, 12 dış tıklama, 29 kayıt (`60_PIN_GENEL.csv`). Günlük gösterim 30 Eylül'de 1.682'ye çıkıp 2 Ekim'de 1'e düşüyor (`60d`). Proje kaydına göre eski Pin'ler 1 Ekim'de silindi. Yani 30 günlük toplamların çoğu **artık olmayan eski Pin'lere** ait. Yeni şablon için kıyas verisi değil.
- **7 gün (04-11.10, yeni Pin'ler):** 1,18 bin gösterim, 6 Pin tıklaması, **1 dış tıklama**, 0 kayıt.
- **Panolar (Export, 11.09-11.10):** `Zodiac Couple Wall Art` 1.239 gösterim, 9 Pin tıklaması, 4 dış tıklama. `Anniversary Gifts for Couples` 107 gösterim, 1 Pin tıklaması, 0 dış tıklama (`60e`). Diğer 4 pano boş (`60c`).
- **Pin başına:** Yeni Pin'ler 30 günde 20-29 gösterim aralığında. Dış tıklama alan yalnız 2 Pin var: `Cancer and Libra Personalized Zodiac Couple Wall Art` (1 dış tıklama / 26 gösterim) ve `Cancer and Taurus …` (1) (`60b`). **Örneklem çok küçük.** Başlık biçimi hakkında sonuç çıkarılamaz. "Anniversary Gift" başlıklı Pin'ler veri alındığında 1-3 günlüktü, kıyaslanamaz.
- **Bekleyen plan (`65`):** 136 Pin (11-24 Ekim). 78'i `Personalized Couple Gifts`, 57'si `Anniversary Gifts for Couples`, 1'i `Zodiac Couple Wall Art` panosunda. 57 "Anniversary" başlığı `A Personalized Anniversary Gift for a/an {A} and {B} Couple` biçiminde. Çift adı 37-39. karakterden sonra başlıyor, ilk 40 karakter kuralına [S2] ters. **Öneri:** yayından önce `{A} and {B} Anniversary Gift, Personalized Zodiac Couple Wall Art` gibi çift adı başta olacak şekilde değiştir.
- **Pin sayfaları (`64`):** 5 Pin'in 3'ünde Pinterest, Pin açıklaması yerine **Etsy ilanının uzun açıklamasını** gösteriyor. Etsy ilan metni Pinterest'te doğrudan görünüyor ve arama sinyali [S19]. Ayrıca ilan metninde "Our original **AstroLove** design" yazıyor. Marka adı AstroLoveArt olmalı (Etsy tarafı, kapsam dışı, not düşüyorum).
- **Kitle (`61`, Export 09.10):** Toplam kitle: Hindistan %12,5, ABD %10,9, Brezilya %5,8, "Other" %49,6; kadın %62,4; 25-34 yaş %35,3. Etkileşen kitle: ABD %16,9, Hindistan %10. İlgi alanları (ham oran): Art 0,747, Home Decor 0,705 (alt kırılımda Wall 0,951), Event Planning 0,502 (Gifts 0,26), Wedding 0,429. Ev dekoru / duvar ilgisi, hediye ilgisinden yüksek. Bu P1'in "wall art" odağını destekliyor. "Audience Size 10000" bir Export alanı, gerçek kitle sayısı değil.
- **Rakip görünümü:** `zodiac couple` sonuçlarında Zazzle'ın birleşik sembollü çift ürünleri `Aries and Virgo Zodiac Couple…` başlık kalıbıyla çıkıyor (`pinterest_15_results.jpg`). Sadece gözlem.

---

## C. Şablonlar (P1, P2, P3)

Kurallar: başlık ≤100 (bizde 67-85, 78 çiftin tümü hesaplandı), açıklama ≤500 (bizde 332-381), alt metin ≤500 (bizde 187-265). Çift adı her başlıkta ilk sırada. En uzun çiftte (Sagittarius and Capricorn) bile ilk 40 karakterde çift adı ve ürün kelimesinin başı var. Uzun tire yok, hashtag yok, uydurma ürün iddiası yok (fiyat, ölçü, malzeme, "best seller" yok). Cümleler "a/an" hatası olmasın diye çift adının önüne artikel koymayacak şekilde kuruldu. 78 çiftin hepsinde kontrol edildi.

### C.1 P1: duvarda, oda içinde

```text
TITLE: {SIGN_A} and {SIGN_B} Zodiac Wall Art, Personalized Couple Wall Art with Names

DESCRIPTION: Personalized {SIGN_A} and {SIGN_B} zodiac wall art for your bedroom or living room. Our design merges your two zodiac signs into one gold symbol on navy and adds your two names and a personal message. A meaningful anniversary, engagement or wedding gift for {SIGN_A} and {SIGN_B} couples. Designed by AstroLoveArt. Tap the Pin to personalize yours on Etsy.

ALT TEXT: A poster on a wall in a room. On a navy background, the {SIGN_A} and {SIGN_B} zodiac signs are merged into one gold symbol, with two names and a short message. Text on the image reads: Your names, Your zodiac wall art, {SIGN_A_UPPER} & {SIGN_B_UPPER}, ASTROLOVEART.
```
Dayandığı satırlar: #3 zodiac wall art, #11 couple wall art / bedroom / living room, #8 personalized, #7, #9, #10 hediye günleri.

### C.2 P2: iki burç + birleşik sembol

```text
TITLE: {SIGN_A} and {SIGN_B} Combined Zodiac Symbol, Zodiac Couple Art with Your Names

DESCRIPTION: Two signs, one shared symbol. This {SIGN_A} and {SIGN_B} zodiac couple art shows both signs and the single gold symbol made from them, on navy. Your two names and a personal message are added to the poster, so your {SIGN_A} and {SIGN_B} relationship has its own piece of art. Personalized zodiac wall art by AstroLoveArt. Tap the Pin to see it on Etsy.

ALT TEXT: The {SIGN_A} zodiac sign and the {SIGN_B} zodiac sign shown side by side in gold on navy, and the single gold symbol that combines them. Text on the image reads: Two signs, One shared symbol, Zodiac art with your names & message, ASTROLOVEART.
```
Dayandığı satırlar: #4 combined, #2 art / couple art, #5 zodiac couple, #6 relationship, #3.

### C.3 P3: büyük sembol + isimler

```text
TITLE: {SIGN_A} and {SIGN_B} Compatibility Wall Art, Personalized Zodiac Couple Gift

DESCRIPTION: {SIGN_A} and {SIGN_B} compatibility, turned into wall art. One gold symbol made from both zodiac signs, with your two names and a personal message on navy. Made for {SIGN_A} and {SIGN_B} couples who want meaningful zodiac decor at home. A personalized couple gift for an anniversary, engagement, wedding, Valentine's Day or birthday. By AstroLoveArt, available on Etsy.

ALT TEXT: A large gold symbol on navy that merges the {SIGN_A} and {SIGN_B} zodiac signs, with two names below it. Text on the image reads: {SIGN_A_UPPER} & {SIGN_B_UPPER}, Zodiac wall art with your names & message, ASTROLOVEART.
```
Dayandığı satırlar: #1 compatibility, #8 personalized couple gift, #12 zodiac gift, #7, #9, #13 (Valentine's: `valentines gift for him` hesap Trends'te var, `62_PIN_TREND.csv`; birthday: `gift for boyfriend / suggestion / 2 → gift for boyfriend birthday`).

Alt metin notu: Görselde örnek isimler yerine "YOUR NAMES" gibi yer tutucu yazı varsa alt metindeki "two names" ifadesi buna göre değiştirilmeli. Alt metin görseli doğru anlatmalı [S3].

### C.4 Ek alanlar

**Toplu CSV kullanılırsa "Keywords" sütunu** [S6] (Metricool'da böyle bir alan görmedim [S28]):
```text
P1: {sign_a} and {sign_b} zodiac wall art, zodiac wall art, couple wall art, couple wall art bedroom, personalized couple gifts, zodiac couples art
P2: {sign_a} and {sign_b} art, {sign_a} and {sign_b} compatibility, combined zodiac symbol, zodiac couple art, zodiac couples art
P3: {sign_a} and {sign_b} compatibility, {sign_a} and {sign_b} couple, personalized couple gifts, anniversary gifts for couples, engagement gifts for couples, zodiac gifts
```

**Etiketli konu adayları** (en fazla 10 [S5]). Pinterest'in konu listesinde tam bu adlarla var mı **doğrulanmadı**, seçim ekranında kontrol edilmeli: `Zodiac`, `Astrology`, `Wall art`, `Home decor`, `Bedroom decor`, `Anniversary gifts`, `Couple gifts`, `Wedding gifts`.

**Dosya adı** [S8]: `{sign-a}-and-{sign-b}-zodiac-wall-art-astroloveart-p1.jpg` (p2, p3).

**Hashtag:** yok.

---

## D. Pano yapısı önerisi

Dayanak: pano başlığı arama sinyali [S19][S20]; kısa, kelimeli ad ve pano veya bölüm başına 20-100 Pin [S7]; aynı Pin'i panolara tekrar tekrar kaydetme [S9]. Mevcut pano URL'leri geçmiş veri taşıyor, korunmalı.

| Pano (ad uzunluğu) | Durum | Hangi Pin'ler | Neden |
|---|---|---|---|
| **Zodiac Couple Wall Art** (22) | Var, dış tıklama alan tek pano | **P1** (78) | #3 + #5. Oda sahnesi = duvar sanatı niyeti. |
| **Zodiac Compatibility Art** (24) | **Yeni** | **P2** (78) | #1 + #2 + #4. En güçlü kelime pano adında. |
| **Personalized Couple Gifts** (25) | Var (Metricool'da 78 bekleyen) | **P3** (78) | #8 + #7. Hediye niyeti. |
| Anniversary Gifts for Couples | Var (21 canlı + 57 bekleyen) | Mevcut plan | Trends tepesi Ekim. Yeni set için gerekirse P3'ün yarısı buraya. |
| Valentine's Day Gifts for Couples / Wedding and Engagement Gifts | Boş | Ancak **yeni görsellerle** (aynı Pin'i kopyalamadan) | Mevsimsel. Sevgililer Günü için 45-60 gün önce, yani Aralık ortası başlangıç [S7]. |
| Astrology Wall Art and Home Decor | Boş | Şimdilik yok | Kanıt zayıf (#14). |

Bölüm (section) notu: Mevcut 136 bekleyen Pin de yayınlanırsa `Personalized Couple Gifts` 156'ya çıkar. O durumda P3'ü pano içinde ayrı bir bölüme koy (pano veya bölüm başına 20-100 [S7]).

Pano açıklamaları (≤500 [S27, ikincil]):
```text
Zodiac Couple Wall Art (245): Personalized zodiac couple wall art by AstroLoveArt. Each poster merges two zodiac signs into one gold symbol on navy, with the couple's names and a personal message. Couple wall art ideas for the bedroom or living room, for all 78 zodiac pairs.

Zodiac Compatibility Art (230): Zodiac compatibility art for every sign pair, from Aries and Leo to Scorpio and Pisces. See how two zodiac signs become one shared gold symbol, personalized with your names and a personal message. Original designs by AstroLoveArt.

Personalized Couple Gifts (174): Personalized couple gift ideas for anniversaries, engagements and weddings: zodiac wall art made from your two signs, with your names and a personal message. By AstroLoveArt.
```

Yayın sırası: Her çift için P1, P2, P3 farklı günlerde (zaten planlı). Bu, "aynı URL'ye farklı görünen yeni Pin" kuralına uygun [S21]. Pinterest günlük sayı sınırı açıklamıyor (doğrulanmadı). Aynı siteden hızlı ve çok kayıt engel tetikleyebilir [S15]. Mevcut düzenli günlük akış sürmeli, toplu patlama yapılmamalı.

---

## E. Doldurulmuş örnekler (karakter sayıları script ile sayıldı)

### E.1 Gemini & Leo

**P1** · Başlık 71 / Açıklama 342 / Alt metin 239 karakter

```text
TITLE: Gemini and Leo Zodiac Wall Art, Personalized Couple Wall Art with Names

DESCRIPTION: Personalized Gemini and Leo zodiac wall art for your bedroom or living room. Our design merges your two zodiac signs into one gold symbol on navy and adds your two names and a personal message. A meaningful anniversary, engagement or wedding gift for Gemini and Leo couples. Designed by AstroLoveArt. Tap the Pin to personalize yours on Etsy.

ALT TEXT: A poster on a wall in a room. On a navy background, the Gemini and Leo zodiac signs are merged into one gold symbol, with two names and a short message. Text on the image reads: Your names, Your zodiac wall art, GEMINI & LEO, ASTROLOVEART.
```

**P2** · Başlık 72 / Açıklama 338 / Alt metin 236 karakter

```text
TITLE: Gemini and Leo Combined Zodiac Symbol, Zodiac Couple Art with Your Names

DESCRIPTION: Two signs, one shared symbol. This Gemini and Leo zodiac couple art shows both signs and the single gold symbol made from them, on navy. Your two names and a personal message are added to the poster, so your Gemini and Leo relationship has its own piece of art. Personalized zodiac wall art by AstroLoveArt. Tap the Pin to see it on Etsy.

ALT TEXT: The Gemini zodiac sign and the Leo zodiac sign shown side by side in gold on navy, and the single gold symbol that combines them. Text on the image reads: Two signs, One shared symbol, Zodiac art with your names & message, ASTROLOVEART.
```

**P3** · Başlık 70 / Açıklama 355 / Alt metin 193 karakter

```text
TITLE: Gemini and Leo Compatibility Wall Art, Personalized Zodiac Couple Gift

DESCRIPTION: Gemini and Leo compatibility, turned into wall art. One gold symbol made from both zodiac signs, with your two names and a personal message on navy. Made for Gemini and Leo couples who want meaningful zodiac decor at home. A personalized couple gift for an anniversary, engagement, wedding, Valentine's Day or birthday. By AstroLoveArt, available on Etsy.

ALT TEXT: A large gold symbol on navy that merges the Gemini and Leo zodiac signs, with two names below it. Text on the image reads: GEMINI & LEO, Zodiac wall art with your names & message, ASTROLOVEART.
```

### E.2 Cancer & Libra

**P1** · Başlık 73 / Açıklama 346 / Alt metin 243 karakter

```text
TITLE: Cancer and Libra Zodiac Wall Art, Personalized Couple Wall Art with Names

DESCRIPTION: Personalized Cancer and Libra zodiac wall art for your bedroom or living room. Our design merges your two zodiac signs into one gold symbol on navy and adds your two names and a personal message. A meaningful anniversary, engagement or wedding gift for Cancer and Libra couples. Designed by AstroLoveArt. Tap the Pin to personalize yours on Etsy.

ALT TEXT: A poster on a wall in a room. On a navy background, the Cancer and Libra zodiac signs are merged into one gold symbol, with two names and a short message. Text on the image reads: Your names, Your zodiac wall art, CANCER & LIBRA, ASTROLOVEART.
```

**P2** · Başlık 74 / Açıklama 342 / Alt metin 238 karakter

```text
TITLE: Cancer and Libra Combined Zodiac Symbol, Zodiac Couple Art with Your Names

DESCRIPTION: Two signs, one shared symbol. This Cancer and Libra zodiac couple art shows both signs and the single gold symbol made from them, on navy. Your two names and a personal message are added to the poster, so your Cancer and Libra relationship has its own piece of art. Personalized zodiac wall art by AstroLoveArt. Tap the Pin to see it on Etsy.

ALT TEXT: The Cancer zodiac sign and the Libra zodiac sign shown side by side in gold on navy, and the single gold symbol that combines them. Text on the image reads: Two signs, One shared symbol, Zodiac art with your names & message, ASTROLOVEART.
```

**P3** · Başlık 72 / Açıklama 359 / Alt metin 197 karakter

```text
TITLE: Cancer and Libra Compatibility Wall Art, Personalized Zodiac Couple Gift

DESCRIPTION: Cancer and Libra compatibility, turned into wall art. One gold symbol made from both zodiac signs, with your two names and a personal message on navy. Made for Cancer and Libra couples who want meaningful zodiac decor at home. A personalized couple gift for an anniversary, engagement, wedding, Valentine's Day or birthday. By AstroLoveArt, available on Etsy.

ALT TEXT: A large gold symbol on navy that merges the Cancer and Libra zodiac signs, with two names below it. Text on the image reads: CANCER & LIBRA, Zodiac wall art with your names & message, ASTROLOVEART.
```

### E.3 Scorpio & Pisces

**P1** · Başlık 75 / Açıklama 350 / Alt metin 247 karakter

```text
TITLE: Scorpio and Pisces Zodiac Wall Art, Personalized Couple Wall Art with Names

DESCRIPTION: Personalized Scorpio and Pisces zodiac wall art for your bedroom or living room. Our design merges your two zodiac signs into one gold symbol on navy and adds your two names and a personal message. A meaningful anniversary, engagement or wedding gift for Scorpio and Pisces couples. Designed by AstroLoveArt. Tap the Pin to personalize yours on Etsy.

ALT TEXT: A poster on a wall in a room. On a navy background, the Scorpio and Pisces zodiac signs are merged into one gold symbol, with two names and a short message. Text on the image reads: Your names, Your zodiac wall art, SCORPIO & PISCES, ASTROLOVEART.
```

**P2** · Başlık 76 / Açıklama 346 / Alt metin 240 karakter

```text
TITLE: Scorpio and Pisces Combined Zodiac Symbol, Zodiac Couple Art with Your Names

DESCRIPTION: Two signs, one shared symbol. This Scorpio and Pisces zodiac couple art shows both signs and the single gold symbol made from them, on navy. Your two names and a personal message are added to the poster, so your Scorpio and Pisces relationship has its own piece of art. Personalized zodiac wall art by AstroLoveArt. Tap the Pin to see it on Etsy.

ALT TEXT: The Scorpio zodiac sign and the Pisces zodiac sign shown side by side in gold on navy, and the single gold symbol that combines them. Text on the image reads: Two signs, One shared symbol, Zodiac art with your names & message, ASTROLOVEART.
```

**P3** · Başlık 74 / Açıklama 363 / Alt metin 201 karakter

```text
TITLE: Scorpio and Pisces Compatibility Wall Art, Personalized Zodiac Couple Gift

DESCRIPTION: Scorpio and Pisces compatibility, turned into wall art. One gold symbol made from both zodiac signs, with your two names and a personal message on navy. Made for Scorpio and Pisces couples who want meaningful zodiac decor at home. A personalized couple gift for an anniversary, engagement, wedding, Valentine's Day or birthday. By AstroLoveArt, available on Etsy.

ALT TEXT: A large gold symbol on navy that merges the Scorpio and Pisces zodiac signs, with two names below it. Text on the image reads: SCORPIO & PISCES, Zodiac wall art with your names & message, ASTROLOVEART.
```

---

## F. Açık sorular / eksik veri

1. **Cancer and Libra için Pinterest önerisi ve baloncuk yok** (`cancer and libra / suggestion / not shown`, ekran görüntüsü 21'de liste boş). 78 çiftin yalnız 4'ünde Pinterest çift düzeyi veri var. "Her çiftte compatibility önde" genellemesi Pinterest için **varsayım**. YouTube 77/78 bunu destekliyor ama farklı platform.
2. **Arama hacmi sayısı yok.** Trends 0-100 göreli endeks [S13]. "zodiac wall art", "zodiac couple", "couple wall art", "personalized couple gift" için tam eşleşme yok (sıfır değil). Tepe ayları gözle okundu.
3. **Çift sırası:** Pinterest verisi "scorpio and pisces" sırasıyla toplandı. Etsy ilanları ve mevcut Pin'ler alfabetik sıra kullanıyor ("Pisces and Scorpio", `60b`). Hangi sıranın daha çok arandığı **doğrulanmadı**. Başlıkta görseldeki sırayı kullanmayı öneririm, ilan ile tutarlılık için karar gerekli.
4. **Metricool:** alt metin var [S29]. Etiketli konu ve "Keywords" alanı var mı **doğrulanmadı**. Toplu CSV'de keywords var, alt metin ve konu yok [S6][S22].
5. **Görsel üstü yazının (OCR) arama etkisi** resmî olarak **doğrulanmadı**.
6. **Rich pin:** Etsy ilan başlığının Pin başlığının yerine geçip geçmediği resmî olarak yazmıyor [S10]. Bizim veride açıklama 3/5 Pin'de değişmiş. Etsy ilan başlığı ve açıklaması da aynı ana kelimeleri taşımalı (Etsy tarafı ayrı iş).
7. **Yapay zekâ etiketi:** P1 sahneleri GenAI ile üretiliyorsa etiketlenip "daha az AI" seçen kullanıcılarda azalabilir [S17]. Etki büyüklüğü **doğrulanmadı**.
8. **Hashtag'in bugünkü etkisi:** resmî güncel kaynak yok (**doğrulanmadı**).
9. **Pano adı 50 karakter sınırı** yalnız ikincil kaynakta [S27].
10. **Performans kıyası için veri yok:** Yeni Pin'ler 7 günde 1 dış tıklama getirdi. P1, P2, P3 şablonlarını karşılaştırmak için yayından sonra en az 30 gün Pin bazında gösterim, dış tıklama ve kayıt Export'u gerekli.
11. **Mevcut 136 bekleyen + 96 yayınlanmış Pin** yeni P1-P3 setiyle birlikte mi kalacak? Aynı ilana çok sayıda Pin olur. Görseller farklıysa kurala uygun [S21], pano doluluğu D'deki bölüm notuna göre ayarlanmalı.
12. Okunamayan sayfalar: `developers.pinterest.com/docs/api/v5/pins-create/` (JavaScript, alan sınırları görünmedi), `business.pinterest.com/pinterest-predicts/` (içerik gelmedi, ikincil özet [S26] kullanıldı), `help.pinterest.com/en-gb/article/create-a-pin-from-an-image-or-video` (robots engeli).

---

## G. Kaynaklar

**Resmî Pinterest**
- [S1] Review Pin specs: https://help.pinterest.com/en/article/review-pin-specs
- [S2] Creative Best Practices (reklam): https://business.pinterest.com/creative-best-practices/
- [S3] Add alternative text to your Pins: https://help.pinterest.com/en/business/article/add-alternative-text-to-your-pins
- [S4] Alt text (arşiv sürümü): https://help.pinterest.com/en-gb/business/article/add-alternative-text-to-your-pins-archived
- [S5] Create a Pin from an image or video: https://help.pinterest.com/en/business/article/build-a-pin
- [S6] Bulk upload Pins (CSV sütunları): https://help.pinterest.com/en/business/article/bulk-upload-video-pins
- [S7] Pinterest Create, Fundamentals: https://create.pinterest.com/fundamentals/
- [S8] A creator's guide to SEO (16 Tem 2025): https://create.pinterest.com/blog/seo-best-practices/
- [S9] Pin performance and distribution: https://help.pinterest.com/en/business/article/pin-performance-and-distribution
- [S10] Create rich Pins: https://help.pinterest.com/en/business/article/rich-pins
- [S11] Product rich pins (developers): https://developers.pinterest.com/docs/web-features/product-rich-pins/
- [S12] Create a board: https://help.pinterest.com/en/business/article/create-a-board
- [S13] Browse Pinterest Trends: https://help.pinterest.com/en/business/article/pinterest-trends
- [S14] Community guidelines (Spam): https://policy.pinterest.com/en/community-guidelines
- [S15] Prevent rate limit blocks: https://help.pinterest.com/en/article/rate-limit-blocks
- [S16] Search for ideas on Pinterest: https://help.pinterest.com/en/article/search-for-ideas-on-pinterest
- [S17] GenAI kontrol araçları (16 Eki 2025, güncelleme 12 Ara 2025): https://newsroom.pinterest.com/news/pinterest-rolls-out-new-tools-to-give-users-more-control-over-gen-ai-content/
- [S18] Now hashtags work on Pinterest (26 Eyl 2017, arşiv): https://newsroom-archive.pinterest.com/en-gb/now-hashtags-work-on-pinterest
- [S19] Improving Pinterest Search Relevance Using LLMs (Pinterest yazarları, CIKM'24): https://arxiv.org/pdf/2410.17152
- [S20] Pinterest Business Community, PinterestAutumn (7 Oca 2026): https://community.pinterest.biz/t/behind-the-scenes-making-pinterest-searches-work-better-with-ai/41570
- [S21] Pinterest Business Community, PinterestLuan (6 Mar 2026): https://community.pinterest.biz/t/are-pins-used-in-different-days-still-considered-fresh-pin/43409
- [S22] Pinterest Business Community, CSV'de tagged topics (29 Oca 2026): https://community.pinterest.biz/t/adding-tagged-topics-within-csv-upload/42308
- [S23] Create boards and pins (developers): https://developers.pinterest.com/docs/work-with-organic-content-and-users/create-boards-and-pins/

**İkincil (resmî değil)**
- [S24] Louise Myers, Pinterest hashtags (güncelleme 6 Oca 2025): https://louisem.com/214795/pinterest-hashtags
- [S25] Social Media Today (1 Ağu 2019), Pinterest Engineering anahtar kelime çıkarımı özeti: https://www.socialmediatoday.com/news/pinterest-provides-insights-into-how-it-uses-text-elements-in-pin-discovery/559989
- [S26] PPC Land, Pinterest Predicts 2026 (9 Ara 2025): https://ppc.land/pinterest-unveils-21-consumer-trends-for-2026-advertising-campaigns/
- [S27] Word Counter Tool, Pinterest karakter sınırları (Eki 2026): https://www.wordcountertool.net/character-limits/pinterest
- [S28] Metricool Help, Pinterest'te yayın: https://help.metricool.com/schedule-and-post-on-pinterest-sbiz3
- [S29] Metricool Help, alt metin (Pinterest dahil): https://help.metricool.com/how-to-add-alt-text-to-your-images-using-ai-mkl42

**Bizim veri dosyaları:** `sosyal_veri/README.txt`, `sosyal_veri/pinterest.csv`, `sosyal_veri/screenshots/pinterest_15_results.jpg`, `_20_suggestions.jpg`, `_21_suggestions.jpg`, `_22_suggestions.jpg`, `pinterest_trend_16_chart.jpg`, `sosyal_veri/youtube_google_autocomplete.csv`, `pinterest_hesap_analitigi/` (60, 60b, 60c, 60d, 60e, 61, 62, 62b, 63, 64, 65, 66 ve ORIJINAL_EXPORT).
