# F 4. koşu: Serdar onay paketi (bağımsız inceleme sonrası düzeltilmiş)
Kontak: F_ONAY_KONTAK_4STIL.jpg (4 stil 12x18, gerçek 2:3). Yakın: F_LAYERSB_DIKIS_YAKIN.jpg (Layers B, satır 4500 çevresi, 2x).
Kaynak: OLCUM.json 4. koşu (41333282806) ve it. 2 (41335430007); yerel ölçüm = çıktı JPEG'inden.

1. FirstPage: kapı PASS, AMA görsel it. 1 ile aynı; it. 2 yalnız kapı tanımını değiştirdi.
   12x18 köşe dışı koyu piksel 0 (it. 1'de sol_alt 1). 8x10 33 -> 0: dosya aynı, ölçü sınırı genişledi
   (sol_ust 4,89 -> 9,89 px). Yani 8x10'da ~5 px taşma artık sayılmıyor; 12x18'de körlük ~1 px.
   Öz test (yapay, dokusuz) 1 px taşmayı yakalıyor; gerçek dokulu köşede bu körlük denenmedi.
   Serdar'ın "<10 px yakala" şartı 12x18'de ~1 px körlükle, 8x10'da karşılanmıyor.
2. Layers B: FAIL. Kemer kesimi 0 (PASS). İki kusur:
   a) Satır 4500'de yatay kesim çizgisi (kod hatası): eski doku yalnız ilk 4500 satıra karışıyor, altı düz yeni doku.
      Yerel ölçüm x=275: parlaklık 218,3 -> 223,6 (birkaç satırda). Kapılar bunu görmüyor (ölçüm [:4500] içinde).
   b) Kemer maskesi (eşik 12) kağıt lekelerini de "kemer" sayıp eski dokuyu taşıyor; lekeli/düz geçiş bu yüzden.
   Dikiş dE76 3,53 (eşik 3,0 öneri) iki dokunun genel renk farkını ölçüyor (medyanlar 253/216/190 ve 246/217/194 arası
   dE 3,63), yerel dikişi değil. Gradyan 1,078 PASS bu kesimi dışlamıyor.
   2 iterasyon doldu (4. koşu + it. 2); düzeltme yeni görevle.
3. Timeless (3. koşu): değişmedi. Korelasyon 0,9965-0,9974 (eşik 0,98).
4. Botanical (3. koşu): karar A, görsel değişmedi. Kapı (yeni tanım) 0,0076 / 0,0021 PASS; eski tanım 0,0227 / 0,0235 (eşik 0,02).
Drive: Timeless 1YuWKpn8r2KQ9Ibna2XoF8ypnm9JaeOBF | FirstPage 1zxyP-zVZ_rn4uvk5I11xNnz2UC9TH082 | Layers B 115LsvCOEqa4e-Zi_GPNQ8rYM4EbYHcS3 | Botanical 1FR11RlQsb5GNw5r8zkptX5Sd1dON0iwF
Etsy yazımı yok.
