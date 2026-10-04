# SCORPIO_VIRGO TEK DOKU: L yuzdelik esleme (referans ana sembol cekirdegi)

Kapi: L p5/p25/p50/p75/p95/p99 farki <= 1.5, cok parlak oran (L > ana p99) farki <= 1 puan, ogeler arasi medyan dE00 <= 1.0, leke 0. Doku yalniz rapor (L yerel std 9 px, cekirdek medyani).

| oge | ONCE L p5 p25 p50 p75 p95 p99 | ONCE fark maks | ONCE parlak % | SONRA L p5 p25 p50 p75 p95 p99 | SONRA fark maks | SONRA parlak % | SONRA dE00 ana | doku std9 (x ana) |
|---|---|---|---|---|---|---|---|---|
| cember | 41.4 67.6 71.6 74.0 76.9 79.3 | 17.99 | 0.00 | 45.1 59.2 71.7 83.8 93.7 95.5 | 1.12 | 0.03 | 0.14 | 9.01 (4.61x) |
| ana_sembol | 45.4 59.4 71.7 83.8 94.9 96.6 | 0.00 | 0.82 | 45.4 59.4 71.7 83.8 94.9 96.6 | 0.00 | 0.82 | 0.00 | 1.95 (1.00x) |
| isim1 | 43.1 56.3 71.5 80.1 89.5 92.7 | 5.35 | 0.00 | 45.2 59.3 71.6 83.8 94.9 96.5 | 0.18 | 0.80 | 0.08 | 4.40 (2.25x) |
| sonsuz | 49.8 58.2 71.5 76.9 84.7 87.1 | 10.12 | 0.00 | 45.0 59.3 71.6 83.8 94.9 96.6 | 0.34 | 0.77 | 0.10 | 9.72 (4.98x) |
| isim2 | 36.5 52.2 71.4 78.1 85.4 87.8 | 9.44 | 0.00 | 45.1 59.3 71.6 83.9 94.9 96.5 | 0.23 | 0.75 | 0.06 | 2.51 (1.28x) |
| kucuk_sol | 40.3 56.6 71.3 88.5 98.1 98.5 | 5.09 | 9.78 | 45.2 59.2 71.6 83.9 94.8 96.4 | 0.21 | 0.71 | 0.10 | 2.43 (1.24x) |
| kucuk_sag | 38.4 57.2 71.6 91.9 98.2 98.4 | 8.11 | 13.85 | 45.2 59.4 71.5 84.0 94.8 96.5 | 0.17 | 0.71 | 0.14 | 3.40 (1.74x) |
| tagline | 39.7 53.1 71.6 80.6 88.9 90.9 | 6.32 | 0.00 | 45.2 59.3 71.6 83.8 94.9 96.5 | 0.16 | 0.62 | 0.07 | 6.26 (3.21x) |

ONCE: en buyuk medyan dE00 0.26, FAIL. SONRA: en buyuk medyan dE00 0.16 (cember|kucuk_sag), leke 0.0, PASS (kapali dongu tur 2).
