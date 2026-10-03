# Zemin: puruzsuz radyal gradient (Serdar 3 Eki ek), olcum + kapi k

Kaynak: BLUE_16x20 halkasiz plate (yildiz ve cember disi zemin pikselleri).
Merkez: cember merkezi (2399.2, 2404.1) px (4800 x 6000). Bicim: 4:5 elips (olculen rmse 1.24 luma; daire 1.40). Not: serbest aramada plate zemininin en acik noktasi ~400 px asagida, talimat geregi merkez cember merkezi.
Merkez rgb [0.45, 11.5, 46.2], kose rgb [2.11, 0.95, 10.66] (16 bit hesap).
Gecis egrisi (s = elips uzakligi / kose; olculen, izotonik + Gauss): 

| s | R | G | B | luma |
|---|---|---|---|---|
| 0.0 | 0.45 | 11.50 | 46.20 | 12.15 |
| 0.1 | 0.45 | 11.03 | 45.28 | 11.77 |
| 0.2 | 0.45 | 9.94 | 42.18 | 10.78 |
| 0.3 | 0.51 | 8.34 | 37.68 | 9.34 |
| 0.4 | 0.67 | 6.52 | 31.99 | 7.68 |
| 0.5 | 0.95 | 4.94 | 25.90 | 6.14 |
| 0.6 | 1.03 | 3.91 | 21.21 | 5.02 |
| 0.7 | 1.14 | 3.30 | 18.69 | 4.41 |
| 0.8 | 1.17 | 2.79 | 16.05 | 3.82 |
| 0.9 | 1.95 | 2.32 | 13.46 | 3.48 |
| 1.0 | 2.11 | 0.95 | 10.66 | 2.40 |

Yildizlar: plate yildiz katmani (54 yildiz, isin + hale), gradient ustune; yazi kutusu + pay icindekiler atilir (CANCER_LIBRA 9, SCORPIO_VIRGO 0, AQUARIUS_LEO 6).
8 bit: TPDF dither +-1 LSB (yalniz zemin). ZEMIN.png ile MOTOR.png zemini birebir (c kapisi dE 0.0).

Kapi k: (1) %1 elips halkalarinda ortalama luma disa dogru artis <= 0.05; (2) zemin (10 px yumusak) - halka profili, |fark| p99.9 <= 0.50.

| sayfa | en buyuk artis | leke p99.9 | k |
|---|---|---|---|
| CANCER_LIBRA onceki ornek (e12fad7) | 0.227 | 2.976 | FAIL |
| SCORPIO_VIRGO onceki ornek (e12fad7) | 0.145 | 2.979 | FAIL |
| AQUARIUS_LEO onceki ornek (e12fad7) | 0.272 | 2.978 | FAIL |
| CANCER_LIBRA yeni | -0.018 | 0.055 | PASS |
| SCORPIO_VIRGO yeni | -0.018 | 0.055 | PASS |
| AQUARIUS_LEO yeni | -0.018 | 0.054 | PASS |

Yeni 3 ornek a-k: 3 / 3 PASS (h en buyuk dE: CANCER_LIBRA 1.57, SCORPIO_VIRGO 1.87, AQUARIUS_LEO 2.66; i 0.021 / 0.003 / 0.007).
Kesitler: ust satir 1:1, alt satir 4x kontrast; (a) cember cevresi, (b) yazi cevresi (yildiz atilan yer), (c) bos zemin.
