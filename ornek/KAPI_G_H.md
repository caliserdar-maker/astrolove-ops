# Kapi g (yazi cevresi yildiz) + h (tek doku) iki yonlu test, yerel, 3 Eki 2026

pay = W x 0.0625 (16x20: 300 px, QC olcegi 207 px); g: tepe >= 25 luma nokta FAIL; h: oge cekirdek ortanca rengi vs ana sembol dE76 <= 2.7

| cift | sayfa | g | g nokta | h | h en buyuk dE | a-h SONUC |
|---|---|---|---|---|---|---|
| CANCER_LIBRA | satistaki orijinal | PASS | 0 | - | - | PASS |
| CANCER_LIBRA | kosu 37139696224 | FAIL | 6 | FAIL | 25.75 | FAIL |
| CANCER_LEO | satistaki orijinal | PASS | 0 | - | - | PASS |
| CANCER_LEO | kosu 37139696224 | FAIL | 2 | FAIL | 25.1 | FAIL |
| LEO_LIBRA | satistaki orijinal | PASS | 0 | - | - | PASS |
| LEO_LIBRA | kosu 37139696224 | FAIL | 2 | FAIL | 23.83 | FAIL |
| AQUARIUS_LEO | satistaki orijinal | PASS | 0 | - | - | PASS |
| AQUARIUS_LEO | kosu 37143578334 | FAIL | 1 | FAIL | 21.48 | FAIL |
| SCORPIO_VIRGO | satistaki orijinal | PASS | 0 | - | - | PASS |
| SCORPIO_VIRGO | kosu 37139696224 | PASS | 0 | FAIL | 25.28 | FAIL |
| CANCER_LIBRA | yeni (tek doku) | PASS | 0 | PASS | 2.35 | PASS |
| SCORPIO_VIRGO | yeni (tek doku) | PASS | 0 | PASS | 2.32 | PASS |
| AQUARIUS_LEO | yeni (tek doku) | PASS | 0 | PASS | 2.01 | PASS |
