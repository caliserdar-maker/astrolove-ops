# SCORPIO_VIRGO T4: harf bazli esitleme (baz 1f07222, duzle kaldirildi)

## Parca kapisi (metin; esik L <= 1.0, b* <= 1.0, ton <= 3 derece)

| oge | once 3a2801a n / L / b / ton | sonra n / L / b / ton | sonuc |
|---|---|---|---|
| isim1 | 7 / 8.64 / 5.45 / 5.02 | 7 / 0.16 / 0.12 / 0.08 | PASS |
| isim2 | 5 / 16.10 / 8.63 / 13.27 | 5 / 0.06 / 0.05 / 0.07 | PASS |
| tagline | 41 / 56.68 / 21.89 / 32.27 | 41 / 0.23 / 0.90 / 1.41 | PASS |

## Mevcut kapilar (yeni, tur 2)

| oge | yuzdelik max fark (esik 1.5) | cok parlak fark puan (esik 1.0) | medyan dE00 max | dilim parlak fark (RAPOR, ana 2.03) | gecti |
|---|---|---|---|---|---|
| cember | 1.12 | -0.792 | 0.185 | 0.10 | PASS |
| ana_sembol | 0.00 | 0.000 | 0.167 | 2.03 | PASS |
| isim1 | 0.20 | -0.451 | 0.185 | 0.90 | PASS |
| sonsuz | 0.11 | -0.054 | 0.131 | 4.42 | PASS |
| isim2 | 0.18 | -0.476 | 0.171 | 0.49 | PASS |
| kucuk_sol | 0.21 | -0.110 | 0.142 | 5.31 | PASS |
| kucuk_sag | 0.17 | -0.113 | 0.170 | 3.68 | PASS |
| tagline | 0.62 | -0.572 | 0.146 | 0.39 | PASS |

En buyuk cift dE00: cember|isim1 0.185 (esik 1.0); leke_ana 0.0; renk kapisi PASS
Halka (esik 0.12): GOLGE_1.png 0.050, teslim q100+TPDF 0.103, 2000 JPG 0.112: PASS

## Not (gozle)

Tagline b, Z, o harflerinde harf ICI kirmizimsi lekeler belirginlesti: a* p99 23.1 -> 32.7, ton p1 66.8 -> 54.5 derece (parca medyani esit, harf ici dagilim degil).
Deneme 1 FAIL: parca cekirdegi w > 0.9 kapi maskesiyle uyusmadi (tagline L 40.2); deneme 2: cekirdek = oge maskesi.
