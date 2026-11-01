# Gorev F son kosu (3. ve son; Serdar 1 Kas onayi)

- Kosu 41315246868, commit 55043c85 (dal yd-stil4), damga 20261101_141704, sonuc PASS (4/4).
- Cikti: Drive TEMP/YD_STIL4_ORNEK/20261101_141704 (https://drive.google.com/drive/folders/1BMCjuHpJx0ayc2YlBTqXA8k9ZUBjQbpI)
- Olcum kaynagi: bu kosunun OLCUM.json (kopya docs/yd_stil4/OLCUM_41315246868.json). Esiklerin cogu TAHMIN (asagida).

| Stil | Kapi (deger; esik, kaynak) | Sonuc |
|---|---|---|
| Timeless | korelasyon 0,9965-0,9974 (>= 0,98 gorev metni); kazanc 0,9924-0,9946 (0,95-1,05 gorev metni); kayma en buyuk 0,10 px (< 0,5 gorev metni; yeni olcum, kapi ici oz-test hata 0,01, esik 0,05 tahmin); SIFT x/y <= 0,00054 (<= 0,01 gorev metni); yeni kirpma <= 0,00114 (<= 0,01 tahmin); doygun fazlasi 0,0012-0,0091 (<= 0,01 tahmin); maske disi 0 (<= 0,02 tahmin) | PASS |
| FirstPage | kenar paylari 178,05-178,37, fark 0,32 (<= 1 gorev metni), beklenenden en buyuk sapma 0,285; kose tasmasi 12x18 = 0, 8x10 = 0 (Serdar 1 Kas: 0 ve 8x10 ile ayni); profil ornek basina 0,021-0,067 (<= 0,08 tahmin), en koyu 0,0027-0,0174 (<= 0,05 tahmin), FWHM farki <= 0,05 (<= 1 tahmin) | PASS |
| Layers_A | kirpilan bantta oge 0 px (gorev metni); SIFT x/y 0,00006 | PASS |
| Botanical | korelasyon 0,9922 / 0,9876; kazanc 1,0113 / 1,0145; kayma <= 0,04; SIFT <= 0,00013; yeni kirpma <= 0,00001; maske disi (kagit ici, taban cikarmali) 0,0076 / 0,0021 (<= 0,02 tahmin) | PASS |

Onceki kusurlar ve bu kosu:
- Timeless 255 kirpma: eski 8x10 susleme maskesinde de doygun piksel var (eski dogrusal taban 0,0021-0,0122). Yay parlakligi artik kagidin 255'e kalan payina gore aktariliyor: yay doygun cikti 0,0033 / eski 0,0021 (2. kosuda 0,0134 / 0,0055, inceleme olcumu). Dallarda cikti eskiden hala 0,0071-0,0091 fazla doygun (esik 0,01 tahmin; pay dar).
- FirstPage profil: kabartma omuzlari (oran > 1) artik ciziliyor; ornek basina fark 0,08-0,12 -> 0,021-0,067. Kose "+" tasmasi giderildi (12x18 1280 px -> 0).
- Botanical maske disi: ESKI tanim (taban yok, kagit disi dahil) hala 0,0227 / 0,0235 (> 0,02); fark kagidin yirtik kenari ve adacayi zemin. Adacayi uzerindeki sap uclari AKTARILMIYOR (bilgi olcumu: maskeye 100 px yakin, adacayi zeminden Lab farki > 13,5 olan px 177 / 185; sap kontrasti adacayi dokusu gurultusu duzeyinde, otomatik ayrilamadi).
- Layers B birakildi (Serdar karari); dikis kapisi kalkti.
- Inceleme bulgulari: faz parabol yanliligi -> DFT alt piksel + kapi ici oz-test; Timeless atanamayan parca -> FAIL; is akisi donus kodu (3 = kapi FAIL); OLCUM esik sozlugu tamamlandi.
Bilinen kor noktalar (olcum yok): kose gonyesi bicimi, yazi blogu olcegi, Botanical yalniz 2 ceyrek, profil kapisi kendi cizim girdisini olcer.
