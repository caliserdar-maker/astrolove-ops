# OGE RENK ESITLEME (hedef Lab 71.5 / 8.5 / 49.5, gecme: ogeler arasi en buyuk dE00 <= 1.0)

Olcum: poster uzerinde (golge 1 sonrasi, 7200x10800), oge cekirdegi (alfa > 0.95, 3 px asindirilmis) medyan Lab, renk_kapi.py.

| poster | oge | ONCE L a b | ONCE dE00 ana | ONCE dE00 oge max | SONRA L a b | SONRA dE00 ana | SONRA dE00 oge max |
|---|---|---|---|---|---|---|---|
| CANCER_LIBRA | cember | 72.3 6.7 50.4 | 2.07 | 7.85 | 71.6 8.3 49.5 | 0.16 | 0.17 |
| CANCER_LIBRA | ana_sembol | 72.6 9.4 49.1 | 0.00 | 8.10 | 71.6 8.6 49.5 | 0.00 | 0.16 |
| CANCER_LIBRA | isim1 | 75.0 11.9 51.9 | 2.44 | 7.09 | 71.4 8.5 49.5 | 0.16 | 0.17 |
| CANCER_LIBRA | sonsuz | 79.0 11.5 57.6 | 5.32 | 5.86 | 71.5 8.5 49.5 | 0.06 | 0.13 |
| CANCER_LIBRA | isim2 | 73.2 12.2 52.1 | 1.86 | 8.36 | 71.5 8.5 49.5 | 0.09 | 0.12 |
| CANCER_LIBRA | kucuk_sol | 75.4 12.8 54.7 | 3.12 | 7.16 | 71.5 8.5 49.5 | 0.08 | 0.12 |
| CANCER_LIBRA | kucuk_sag | 83.4 5.8 50.3 | 8.10 | 8.36 | 71.5 8.5 49.5 | 0.06 | 0.14 |
| CANCER_LIBRA | tagline | 77.5 10.5 52.4 | 3.73 | 5.14 | 71.5 8.5 49.5 | 0.10 | 0.13 |
| AQUARIUS_ARIES | cember | 72.3 6.7 50.4 | 2.03 | 10.43 | 71.6 8.3 49.5 | 0.15 | 0.17 |
| AQUARIUS_ARIES | ana_sembol | 72.8 9.5 49.6 | 0.00 | 10.22 | 71.4 8.3 49.7 | 0.00 | 0.20 |
| AQUARIUS_ARIES | isim1 | 74.0 12.2 52.2 | 1.98 | 11.05 | 71.5 8.5 49.5 | 0.17 | 0.17 |
| AQUARIUS_ARIES | sonsuz | 79.0 11.5 57.6 | 5.10 | 14.83 | 71.5 8.5 49.5 | 0.20 | 0.20 |
| AQUARIUS_ARIES | isim2 | 78.4 11.2 52.7 | 4.24 | 14.16 | 71.6 8.5 49.5 | 0.20 | 0.20 |
| AQUARIUS_ARIES | kucuk_sol | 68.2 9.7 49.1 | 3.52 | 8.38 | 71.4 8.4 49.5 | 0.12 | 0.17 |
| AQUARIUS_ARIES | kucuk_sag | 60.3 11.8 48.5 | 10.22 | 14.83 | 71.5 8.5 49.5 | 0.18 | 0.18 |
| AQUARIUS_ARIES | tagline | 72.1 11.3 52.3 | 1.36 | 9.64 | 71.5 8.5 49.5 | 0.16 | 0.16 |
| SCORPIO_VIRGO | cember | 72.3 6.7 50.4 | 8.15 | 9.39 | 71.6 8.3 49.5 | 0.10 | 0.20 |
| SCORPIO_VIRGO | ana_sembol | 63.0 11.4 49.1 | 0.00 | 12.52 | 71.7 8.5 49.6 | 0.00 | 0.26 |
| SCORPIO_VIRGO | isim1 | 74.5 12.3 52.8 | 9.12 | 10.14 | 71.5 8.5 49.5 | 0.18 | 0.18 |
| SCORPIO_VIRGO | sonsuz | 79.0 11.5 57.6 | 12.52 | 13.60 | 71.5 8.5 49.5 | 0.12 | 0.17 |
| SCORPIO_VIRGO | isim2 | 79.1 11.3 52.9 | 12.33 | 13.38 | 71.4 8.5 49.5 | 0.21 | 0.21 |
| SCORPIO_VIRGO | kucuk_sol | 63.6 12.9 50.5 | 1.06 | 12.05 | 71.3 8.4 49.5 | 0.26 | 0.26 |
| SCORPIO_VIRGO | kucuk_sag | 61.8 12.4 48.5 | 1.28 | 13.60 | 71.6 8.5 49.5 | 0.09 | 0.19 |
| SCORPIO_VIRGO | tagline | 76.2 11.2 53.1 | 10.35 | 11.42 | 71.6 8.5 49.5 | 0.10 | 0.18 |

| poster | ONCE en buyuk cift | SONRA en buyuk cift | ana sembol leke (binde) |
|---|---|---|---|
| CANCER_LIBRA | isim2|kucuk_sag 8.36 (FAIL) | cember|isim1 0.17 (PASS) | 0.0 |
| AQUARIUS_ARIES | sonsuz|kucuk_sag 14.83 (FAIL) | ana_sembol|sonsuz 0.20 (PASS) | 0.0 |
| SCORPIO_VIRGO | sonsuz|kucuk_sag 13.60 (FAIL) | ana_sembol|kucuk_sol 0.26 (PASS) | 0.0 |

renk_olc.py capraz kontrol (3000 px, renk kapisi filtreli tum altin pikseller, kenar dahil): RENK_OLC_ONCE.txt / RENK_OLC_SONRA.txt
