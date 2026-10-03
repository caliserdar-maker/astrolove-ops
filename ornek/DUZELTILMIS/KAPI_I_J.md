# Kapi i (cember dokusu surekli) + j (yazi cevresi zemin dolgu lekesi), iki yonlu test, 3 Eki 2026

i: cember cekirdegi lumasi (tam cozunurluk), 7 px ile 55 px ortalama farki / ortanca -> std <= 0.072 (78 orijinal en buyugu 0.0624 x 1.15)
j: pay (W x 0.0625) icinde zemin, 48 px blok ortancasindan dE76 > 6, alan >= 60 px (QC olcegi), yildiz tepesi < 25 olan bilesen = leke

| sayfa | i boyuna std | i | j leke | j |
|---|---|---|---|---|
| 78 satistaki orijinal | 0.0589 - 0.0624 | PASS 78 / 78 | 0 | PASS 78 / 78 |
| CANCER_LIBRA kusurlu (ornek-tek-doku 644d435) | 0.1650 | FAIL | 1 | FAIL |
| SCORPIO_VIRGO kusurlu (ornek-tek-doku 644d435) | 0.0476 | PASS | 0 | PASS |
| AQUARIUS_LEO kusurlu (ornek-tek-doku 644d435) | 0.1683 | FAIL | 0 | PASS |
| CANCER_LIBRA duzeltilmis | 0.0210 | PASS | 0 | PASS |
| SCORPIO_VIRGO duzeltilmis | 0.0034 | PASS | 0 | PASS |
| AQUARIUS_LEO duzeltilmis | 0.0068 | PASS | 0 | PASS |

Duzeltilmis 3 ornek a-j kapilari: 3 / 3 PASS (h en buyuk dE: CANCER_LIBRA 1.57, SCORPIO_VIRGO 2.32, AQUARIUS_LEO 2.01).

Not: SCORPIO_VIRGO kusurlu cemberi olcude orijinal araliginda (ana sembol kabartma a = 0.05, boyuna leke yok; goze gorunen ic cizgi kaymasi
orijinal cemberin kendi piksel dokusundan ayirt edilemedi); yildiz temizligi 0 oldugu icin j de uygulanacak dolgu yok. AQUARIUS_LEO dolgusu
(1 yildiz) QC olceginde zemine yakin (kalan ince isin parcalari), j yakalamadi.
