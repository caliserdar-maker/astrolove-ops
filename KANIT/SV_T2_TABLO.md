# SCORPIO_VIRGO TEK DOKU, iki duzeltme (deneme 1; dilim kapisi FAIL, durduruldu)

## Oge ici dilim parlakligi (10 esit dilim, cember 12 aci dilimi; esik L <= 2.0, HSV V>0.95 orani <= 5 puan)

| oge | ONCE dilim L farki | ONCE dilim V farki | SONRA dilim L farki | SONRA dilim V farki | SONRA yuzdelik fark maks | SONRA parlak % (ana 0.82) | dE00 ana |
|---|---|---|---|---|---|---|---|
| cember | 17.7 | 39.3 | 29.6 | 59.0 | 1.44 | 1.30 | 0.14 |
| ana_sembol | 30.5 | 53.5 | 30.5 | 53.5 | 0.00 | 0.82 | 0.00 |
| isim1 | 24.1 | 56.1 | 20.8 | 17.3 | 0.26 | 1.19 | 0.11 |
| sonsuz | 39.1 | 76.5 | 38.4 | 73.0 | 0.20 | 0.65 | 0.12 |
| isim2 | 38.9 | 31.6 | 39.1 | 30.6 | 0.25 | 0.94 | 0.09 |
| kucuk_sol | 31.4 | 73.5 | 29.0 | 65.4 | 0.33 | 1.23 | 0.10 |
| kucuk_sag | 29.9 | 78.4 | 29.6 | 70.4 | 0.25 | 0.64 | 0.08 |
| tagline | 23.8 | 30.2 | 17.9 | 17.3 | 0.14 | 1.27 | 0.06 |

tagline dilim L once: [70.1, 75.6, 72.3, 69.5, 61.5, 80.0, 85.3, 68.4, 69.5, 69.0]
tagline dilim L sonra: [70.8, 74.7, 72.4, 70.6, 62.6, 73.9, 80.6, 69.2, 70.5, 70.7]
tagline dilim V>0.95 once: [9.4, 16.6, 18.7, 8.4, 5.2, 35.4, 34.5, 9.0, 8.8, 7.7]
tagline dilim V>0.95 sonra: [8.9, 4.9, 10.0, 6.2, 2.7, 20.0, 5.8, 4.2, 7.4, 7.7]

Mevcut kapilar SONRA: ogeler arasi medyan dE00 en buyuk 0.14, leke 0.0, yuzdelik ve cok parlak oran gecti; dilim kapisi gecmedi (ana sembol kendisi 30.5 L).

## Arka plan halka (radyal profil yuksek geciren artik p99, B kanali, 8 bit seviye; esik 0.12, monotonluk ihlali <= 0.5)

| dosya | bicim | halka | monoton ihlal | sonuc |
|---|---|---|---|---|
| GOLGE_1_325d713.png | ONCE tam PNG | 0.047 | 0.000 | PASS |
| once_kanit_3000.jpg | ONCE KANIT 3000px JPG q92 (Serdar'in gordugu) | 0.669 | 0.019 | FAIL |
| once_q95.jpg | ONCE tam JPEG q95 (teslim, motor.py pdf_yaz) | 0.513 | 0.000 | FAIL |
| once_q100.jpg | ONCE tam JPEG q100 | 0.254 | 0.000 | FAIL |
| GOLGE_1.png | SONRA tam PNG | 0.050 | 0.000 | PASS |
| SCORPIO_VIRGO_T2_2000.jpg | SONRA onizleme 2000px JPG q100 | 0.112 | 0.000 | PASS |
| yeni_q95.jpg | SONRA tam JPEG q95 (teslim) | 0.411 | 0.000 | FAIL |
| yeni_q100.jpg | SONRA tam JPEG q100 | 0.101 | 0.000 | PASS |

Kaynak float gradyan: halka 0.013 (puruzsuz). Sebep: kaynak degil, 8 bit + JPEG; JPEG +-1 titresimi siliyor, kucultme ortaliyor.
