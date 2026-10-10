# etsy-arama oturumu dersleri (10 Eki 2026)

1. Etsy sayfaları (help.etsy.com, etsy.com) Claude sandbox'ından (proxy 403) ve GitHub runner'dan (bot koruması 403) okunamıyor. Resmi metin için Serdar'ın tarayıcısı ya da arama motoru özeti gerekir; özet "resmi URL, metin doğrudan okunmadı" diye işaretlenir.
2. Proje dokümanları (AstroLove_DURUM.md, POD_Kisisel_SEO_Sablon) Drive'da değil, Claude Project'te; Drive aramasında çıkmaz. Görev metninde Drive yolu yoksa önce sor.
3. Eylül etiket pilotu (17 Eyl) 107 dijital ilandaydı; o ilanlar deaktif. Pilot sonucu bugünkü 78 POD ilana taşınamaz.
4. Ayın 14 Etsy arama ziyaretiyle pilot/kontrol farkı ölçülemez; öncü gösterge Search analytics gösterimi.
5. 78 ilanın tüm nitelikleri tek API dökümüyle (82 GET, 2 dk) okunabiliyor: `scripts/etsy/arama_oku.py` (dal claude/keen-curie-2hza60).
6. Kategori 121'in nitelik listesi (`/seller-taxonomy/nodes/121/properties`) boş alanları kesin gösterir; tahmin yerine bunu oku.
