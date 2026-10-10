# Uygulama planı (öneri; uygulama Serdar onayı ile, sipariş sistemi işleri bitince)

## Önce gerçek: veri çok az
- Etsy aramasından 30 günde 14 ziyaret. 39/39 bölünmede grup başına ayda ~7 ziyaret düşer; fark istatistiksel olarak ölçülemez.
- Bu yüzden ölçüm iki katmanlı:
  1. Birincil (görev tanımı): Stats > How shoppers found you > Etsy search ziyareti (mağaza toplamı ve arama terimleri).
  2. Öncü gösterge: Marketing > Search analytics, ilan bazında gösterim (impressions), pozisyon, ziyaret. Etsy'ye göre bu rapor Ads trafiğini içermez (K7). Gösterim ziyaretten çok daha sık olduğu için pilot/kontrol farkını erken gösterir.
- U günü öncesi 28 günün iki ekranı (Stats + Search analytics, 78 ilan) taban olarak Drive'a kaydedilir.

## Öneri: iki faz, aynı anda tek alan

| Faz | Ne | Kaç ilan | Kontrol | Ölçüm |
|---|---|---|---|---|
| 1 (U günü) | Nitelik EKLE: Art subject = Zodiac + Stars & celestial; Primary color = Gold; Room = Bedroom + Living room. Başlık, etiket, açıklama değişmez. | 75 | 3 satış alan ilan (Aquarius & Libra, Aquarius & Scorpio, Cancer & Leo) değişmez | U+14 ara bakış, U+28 karar |
| 2 (U+28, faz 1 sonucu okunduktan sonra) | Etiket: `giclee print` -> çift adı + print/art (CSV `onerilen_etiketler`) | 30 PILOT | 30 KONTROL (CSV `faz2_grup`, alfabetik dönüşümlü) + 3 satış alan ilan | U+28+14 ara, U+56 karar |
| Başlık | Değişmez. Faz 2 sonrası isterse alternatif (CSV `baslik_alternatif_faz2_hipotez`) ayrı pilot. | - | - | - |

Neden faz 1 hepsine: nitelikler ürünün doğru tarifi (eksik alan doldurma); filtreye girme kuralı resmi (K3). Risk düşük. 3 satış alan ilan kontrol olarak kalır, sezon etkisini kısmen gösterir.

## Karar eşikleri (öneri, Serdar onaylar)
- Faz 1 başarılı: U+28 penceresinde Etsy search ziyareti tabanın en az 2 katı (14 -> 28+) VE Search analytics gösterimi artmış. Sezon etkisi için Ads ziyareti ve toplam ziyaret yan yana yazılır.
- Faz 2 başarılı: PILOT grubun Search analytics gösterim toplamı KONTROL grubundan en az %30 fazla (U+56). Değilse etiketler geri alınmaz ama 2. tura gidilmez.
- Ölçüm günü: U+14 ve U+28 (faz 1), U+42 ve U+56 (faz 2). Tarihler U günü belli olunca yazılır.

## Uygulama güvenliği (yazma adımı geldiğinde)
- Her yazma Serdar onayı ister. Faz 1 yalnız nitelik ucu (updateListingProperty), ilan metnine dokunmaz. Faz 2 yalnız `tags` alanı.
- Yazmadan önce state okunur (CLAUDE.md: updateListing taslağı yayına alır). 78 ilan bugün aktif.
- Eylül pilotundaki gibi: önce canlı snapshot karşılaştırması, korunan alanlar (başlık, açıklama, fiyat, Rusça çeviri) önce/sonra hash, kilit (`kilit_bekle.py`), token geri yazma.
- Secondary color, Home style, Holiday, Framing bu turda YOK: kapak rengine, stile ve sezona göre Serdar'ın kararı gerekir (Holiday: Kasım-Aralık "Christmas", 1 Oca'dan "Valentine's Day" ayrı karar).

## Serdar'a sorular
1. Primary color = Gold doğru mu (5 renkte tasarım altın)? Evet/Hayır
2. Faz 1: 75 ilan + 3 kontrol. Evet/Hayır
3. Faz 2 etiket pilotu (30/30) faz 1 sonucundan sonra. Evet/Hayır
