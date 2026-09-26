OTURUM: codex
GOREV 0002 (Claude, 26 Eylul 2026) - BAGIMSIZ KONTROLLER (salt okuma, degisiklik yok)

Serdar: tum kontroller Codex'te de bagimsiz yapilsin. Claude'un ve diger
oturumlarin sonuclarini dogru kabul etme, kaynaktan kontrol et.

A) 78 POD ilani, alici gozuyle (internet, herkese acik Etsy sayfalari):
   - Ilan ID listesi: scripts/etsy/seo/pod_changes_v2.json icindeki `id` ve
     `pair` alanlari (bu dosyadaki eski metinleri REFERANS ALMA).
   - Referans ilan: 4570143815 (Cancer + Libra).
   - Her ilan icin https://www.etsy.com/listing/<id> sayfasinda referansla
     karsilastir: baslik sablonu ("{A} and {B} Zodiac Wall Art, Personalized
     Couple Print with Names and Message, Unframed"), fiyat araligi
     ($34.99-$139.99), kisisellestirme kutusu var mi, foto sayisi, video var mi,
     ilan aktif mi. Aciklamada uzun tire ve emoji var mi.
   - Etsy sayfayi engellerse (403, captcha) 3 denemeden sonra birak ve raporla.
B) Kod: repodaki test dosyalarini calistir (ozellikle scripts/prodigi/test_*.py)
   origin/siparis-onay ve origin/main dallarinda. Sonuclari yaz.
C) Kod incelemesi: son 24 saatte siparis-onay ve kisisel-* dallarina gelen
   commitlerde hata, guvenlik acigi, musteri verisi sizintisi riski var mi.
   Somut dosya:satir ile yaz.

RAPOR: pano/codex/RAPOR_0002.md. Ozet tablo: A icin "X/78 referansla ayni",
farkli olanlarin listesi ve farki; B test sonuclari; C bulgular. Kisa, madde
madde. Hicbir dosyayi degistirme (rapor haric). Etsy/Prodigi'ye yazma yok.
