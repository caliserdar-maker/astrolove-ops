# Kapak karşılaştırması (ADIM 3, 10 Eki 2026)

Kaynak: 8_RAKIP_KAPAK.csv (1MT-_KUH...), RAKIP_EKRAN/01-12.png, KAPAK_ONIZLEME/kapak_ozet.json. Görsel üretilmedi.

## Doğrulama (PNG'den)
- WorthyEngravings $61.74 / 8 yorum (02'de 3 kart): PNG'de 3 ayrı ilan (Wedding Gift, 15 Year Anniversary, Engagement Gift). Doğru.
- PrintWorthyArts (04'te 5 kart): PNG'de 5 ayrı ilan ($43.22, $21.22, $21.22, $43.22, $25.99). Doğru.
- Symla $2.69 / 348 yorum: 03, 05, 11'de görünüyor; 05'te ikinci Symla kartı $9.00. Ayrı ilanlar. Doğru.
- 02 ve 04 PNG'lerinde arama kutusunda "libra gift" yazıyor (yalnız 04 değil, 02 de). İlanlar hedef aramayla tutarlı ama sorgu metni PNG'den doğrulanamadı: bu 2 ekranın 16 satırı analize ALINMADI. Analiz: 10 terim, 80 satır.

## Ölçümler
| Ölçüm | Değer | Kaynak |
|---|---|---|
| Etsy arama kartı görsel oranı (masaüstü) | 311x390 px, yaklaşık 4:5 dikey | PNG 01-12 (10 ekranda ölçüldü) |
| Bizim kapak (rank 1) oranı | 3000x2250, 4:3 yatay | kapak_ozet.json |
| Sonuç | Kart 4:3 kapağın ortasını kırpıyor; duvar/oda bağlamı kartta görünmüyor, bizim kart "yakın plan" sınıfına düşüyor | PNG 01, 07, 09 |
| Bizim kartın ortalama parlaklığı (0-255) | 32.6 / 28.9 / 32.6 (01 / 07 / 09) | PNG piksel ölçümü |
| Aynı ekrandaki diğer 7 kartın medyanı | 141.0 / 145.0 / 119.6 | PNG piksel ölçümü |
| Bizim kart | 3 ekranın üçünde de en koyu kart | aynı |

Not: KAPAK_ONIZLEME'deki 340x270 önizleme varsayımı yanlış çıktı; gerçek masaüstü kartı 4:5 dikey.

## Kapak türü dağılımı (ilk 8, terim türüne göre; 02/04 hariç)
| Terim türü | Terimler | mockup/oda | yakın plan | düz poster | Bizim ilan |
|---|---|---|---|---|---|
| Duvar sanatı | zodiac wall art, couple wall art, scorpio wall art | 21/24 | 3/24 | 0 | 03: sayfa 3 (yalnız reklam); 05, 11: ilk 3 sayfada yok |
| Ürün adı | zodiac couple print, zodiac couple gift | 13/16 | 2/16 | 1/16 | 01: reklam 3, organik 14; 06: organik 47 |
| Çift adı | cancer and leo, aquarius and libra, scorpio and taurus | 3/24 | 21/24 | 0 | organik 6 / 9 / 7 |
| Tek burç hediye | libra gift, cancer zodiac gift | 2/16 | 14/16 | 0 | ilk 3 sayfada yok |
| Toplam | 10 terim | 39/80 | 40/80 | 1/80 | 5/10 terimde 1. sayfada |

## Yorum (kanıt / hipotez ayrı)
- Kanıt: organik olarak göründüğümüz aramalar çift adı (6-9. sıra) ve ürün adı (14, 47). Bu aramalarda üstteki kartlar çift adında yakın plan (21/24), ürün adında mockup/oda (13/16).
- Kanıt: duvar sanatı ve tek burç aramalarında ilk 3 sayfada organik yokuz (yalnız 03'te reklamla sayfa 3). Bu aramalarda sorun kapak değil sıralama; kapak değişikliği bu aramalara girmeyi sağlamaz.
- Hipotez: koyu lacivert kart açık renkli kartlar arasında ayrışıyor (parlaklık ölçüldü; tıklamaya etkisi ölçülmedi).
- Hipotez: ürün adı aramalarında mockup/oda bağlamı kartta görünür olsaydı bu aramalardaki kartlara daha çok benzerdi. Bunun için kapağın 4:5 kırpıma göre yeniden kompoze edilmesi gerekir; bu ayrı bir görsel iş ve Serdar'ın gözü ister.

## Öneri
Kapak şimdi değişmesin: göründüğümüz çift adı aramalarında kartımız rakiplerle aynı türde (yakın plan) ve en koyu kart olarak ayrışıyor; duvar sanatı aramalarında sorun sıralama. Kapak denemesi istenirse tek konu: 4:5 kırpımda oda bağlamı görünen bir kompozisyon (1 örnek, ayrı onayla).
