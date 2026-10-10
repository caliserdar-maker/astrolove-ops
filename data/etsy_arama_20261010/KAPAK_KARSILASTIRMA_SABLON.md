# Kapak karşılaştırma şablonu (etsy-arama, 10 Eki 2026)

Bizim 3 örnek kapak (canlı, rank 1 görsel): Drive `ETSY_ARAMA_20261010/KAPAK_ONIZLEME/`
- `KAPAK_UCLU_340x270.png`: üçü yan yana, arama küçük resmi boyutunda (340x270)
- `<CIFT>_kucuk_340x270.jpg`: tek tek küçük resim; `<CIFT>_kapak_570.jpg`: ilan sayfası boyu
- Örnekler: CANCER_LEO (satış alan), CANCER_LIBRA (en çok görüntülenen, satış yok), ARIES_LEO (53 görüntülenme, 0 favori)
- 340x270 Etsy CDN'in küçük resim boyutudur; arama ızgarasında gerçekte görünen boyut ajanın masaüstü ekran görüntüsüyle teyit edilir (varsayım).

## Yan yana bakış (Serdar doldurur; rakip verisi 8_RAKIP_KAPAK.csv ve RAKIP_EKRAN/ klasöründen)

| Terim | Rakip ekran dosyası (RAKIP_EKRAN/) | İlk 8'de baskın kapak türü (mockup/oda, düz poster, yakın plan, yazı kartı) | Bizim kapak türü | Bizim ilan ilk 3 sayfada mı / sıra | 340x270'te bizim kapakta okunan (burç adı, isim, renk) | Göze çarpma (Serdar: daha iyi / aynı / daha zayıf) |
|---|---|---|---|---|---|---|
| zodiac couple print | | | | | | |
| personalized couple gift | | | | | | |
| zodiac wall art | | | | | | |
| anniversary gift couple | | | | | | |
| couple wall art | | | | | | |
| zodiac couple gift | | | | | | |
| cancer and leo | | | | | | |
| aquarius and libra | | | | | | |
| scorpio and taurus | | | | | | |
| libra gift | | | | | | |
| scorpio wall art | | | | | | |
| cancer zodiac gift | | | | | | |

## Ölçülecek (Claude, 8_RAKIP_KAPAK.csv gelince; tek script, sayı)
- İlk 8 ilanda kapak türü dağılımı (terim başına ve toplam).
- İlk 8'in medyan fiyatı, medyan yorum sayısı; bizim fiyat ve yorum sayımızla fark.
- Bizim ilanın ilk 3 sayfada görünme oranı (12 terimde kaç terim).
- Karar yok: kapak değişikliği ayrı iş, Serdar'ın gözü ve onayı ile (galeri "mağazanın görsel DNA'sı", DEVİR 5 Eki).
