# Olcu tablosu (300 dpi piksel)

Tek kaynak: `scripts/siparis_onizle/halka_yama/olcu.py` (`OLCU`, `AILE`; motor_gpt/olcu.py d2b414ee ile ayni). Bu belge
`python3 scripts/siparis_onizle/olcu_tablo.py --yaz docs/OLCU_TABLOSU.md` ile uretilir; elle duzeltilmez
(`test_olcu_tablo.py` belge ve kaynak farkliysa FAIL verir). Baski ve dijital ayni piksel olcusunu kullanir;
fark yalniz dosya siniri (baski 100 MB, dijital 20 MB) ve dijitalde olcu basina kodlama (`halka_kodla.DIJITAL_KODLAMA`).

| Olcu | Piksel (G x Y) | Oran ailesi | Megapiksel |
|---|---|---|---|
| 5x7 | 1500 x 2100 | A | 3.1 |
| 8x10 | 2400 x 3000 | 4:5 | 7.2 |
| 11x14 | 3300 x 4200 | 11:14 | 13.9 |
| A4 | 2480 x 3508 | A | 8.7 |
| 12x16 | 3600 x 4800 | 3:4 | 17.3 |
| 16x20 | 4800 x 6000 | 4:5 | 28.8 |
| A3 | 3508 x 4961 | A | 17.4 |
| 12x18 | 3600 x 5400 | 2:3 | 19.4 |
| 18x24 | 5400 x 7200 | 3:4 | 38.9 |
| 16x24 | 4800 x 7200 | 2:3 | 34.6 |
| A2 | 4961 x 7016 | A | 34.8 |
| 20x30 | 6000 x 9000 | 2:3 | 54.0 |
| 24x30 | 7200 x 9000 | 4:5 | 64.8 |
| 24x36 | 7200 x 10800 | 2:3 | 77.8 |
