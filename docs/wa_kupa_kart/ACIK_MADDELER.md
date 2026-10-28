# Wall art + kupa bilgi kartlari (SADE) — acik maddeler

Kaynak karar: Merkez 27 Eki 2026, Serdar onayi (A/B/C raporundaki 5 karar); Merkez 28 Eki 2026, Serdar onayi (kart kararlari).
Ornek: CANCER_LIBRA. Etsy'ye yazim yok.

## YUKLEME KURALI (Serdar 28 Eki)

- Wall art kart 4 (WA_ORTAK_S4_SUREC) ve ilan aciklamasindaki onizleme cumlesi (dijital dahil) AYNI YUKLEMEDE gider.
- Kartlar aciklamadan ONCE yuklenmez. Onizleme cumlesi aciklama duzeltmesi isine eklenir (dijital dahil).
- Kupa galerisi tumden 4:3 olur (kare kart kalmaz). Galeri sirasi korunur: canli kupa aciklamasi 3, 4, 5 ve 6 numarali fotograflara
  atif yapar ("See photos 3 and 6", "See photo 4", "See photo 5").

| No | Kart | Durum | Bagli karar | Ne olacak |
|---|---|---|---|---|
| A1 | WA_ORTAK_S3_FORMAT | DEGISTIRILMEDI (Merkez 27 Eki madde 2) | 5x7 boyu (scripts/etsy/pod_5x7_kuru.py, 26 Eki plani, yazilmadi) | 5x7 eklenirse "13 Sizes" -> "14 Sizes" ve boy listesine 5x7; "Nothing is shipped" (AU dijital/kargo celiskisi) yeniden degerlendirilir |
| A2 | WA_ORTAK_S4_SUREC | KARAR VERILDI (28 Eki), kart metni guncellendi | 01 "For every order, we send a preview via Etsy Messages within 24 hours of your order"; 02 "We make your print or file once you approve, or as shown if there is no reply within 24 hours of the preview" | Aciklamadaki onizleme cumlesi (dijital dahil) aciklama duzeltmesi isine eklenir; kart ve aciklama ayni yuklemede, kart once yuklenmez |
| A3 | KUPA 04 (Choose your style) | KARAR VERILDI (28 Eki): 4:3 SADE | Canli kupa aciklamasi "See photo 4" | KUPA_<CIFT>_K04_STIL: 8 stil tek on gorunumu (orchard_gorunum.py stil_<st>), ad altta; galeri sirasi 4 |
| A4 | KUPA_K05_BOYUT cm / in olculeri | ACIK | Canli kupa aciklamasinda cm / in yok (yalniz 11 oz 325 ml, 15 oz 444 ml) | Serdar karari: aciklamaya eklenir mi (kart olculeri A7 ile dogrulandi) |
| A5 | KUPA 02 (Yakin plan) | 4:3 SADE yapildi; SAHNE SAPMASI Merkez onayi bekliyor | Orchard kart 2 basligi "YOUR TWO SIGNS, ONE ORIGINAL SYMBOL" | KUPA_<CIFT>_K02_YAKIN: baslik Title Case tek satir; fotograf tek on gorunumu buyuk olcekte (yakin plan sahnesi zemin esitlemesinde kalinti birakti, kenar 83 > 3) |
| A6 | Kupa galerisinde oran karisimi | KARAR VERILDI (28 Eki), IS ACIK | Tum kupa galerisi 4:3 | 14 gorselin 8'i (01 kapak, 08-14 stil kapaklari) hala kare 2048; 4:3 surumleri uretilmedi (bu ornek yalniz 02-07) |
| A7 | KUPA_K05 cm / in sayilarinin kaynagi | IKINCIL KAYNAKLA TUTARLI (28 Eki); birincil katalog okumasi ACIK | Printful White Glossy Mug urun sayfasi (printful.com, web arama ozeti; sayfa bu oturumdan dogrudan acilamadi): 11 oz 3.8 in (9.6 cm) yukseklik, 3.2 in (8.2 cm) cap; 15 oz 4.7 in (11.9 cm), 3.3 in (8.5 cm); +/- 0.1 in (2,54 mm) | Fark yok. Birincil dogrulama: Printful katalog API (/products/{id}, depoda scripts/kupa_printful/mockup.py) salt okuma kosusu (dispatch onayi gerekir). ml hesap: 11 x 29,5735 = 325,3; 15 x 29,5735 = 443,6 (444) |
| A8 | Canli aciklama dokumlerinin guncelligi | ACIK | Poster 4570143815: KURU_4570143815.json en_eski (26 Eki); kupa 4598525642: SONRA.json (25 Eki 19:11) | Aciklama duzeltmesi kuru kosusunda salt okur GET ile teyit |
| A9 | Dijital onizleme celiskisi | KARAR VERILDI (28 Eki) | Canli aciklama "For every print"; Serdar 26 Eki karari dijitali de kapsiyor | A2 ile ayni yuklemede kapanir |
