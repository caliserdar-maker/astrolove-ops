# STIL3_V3: halkali + halkasiz x RUBY / SAPPHIRE / EMERALD (2 Kas 2026)

Kosu (gecerli): https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41464666418 (deneme 2/2; kapilar PASS).
Deneme 1: https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41461450154 (PASS). Bagimsiz inceleme deneme 1'de 1 yuksek, 3 orta bulgu buldu;
deneme 2 bunlari duzeltti (asagida "Inceleme bulgulari").
Betik: `scripts/printful/ornament_ornek3.py` (001b4d0). Rakamlar `OLCUM.json` (kosu olcumu). 1 px = 0.0847 mm.
Zeminler: Drive TEMP/ORNAMENT_ZEMIN3_20261102/V2 (14:06 UTC indirildi). 1264 -> 954 esit olcek, kirpma yok.
RUBY yeniden disa aktarilmis: sha 7c009226..., onceki c0bddf95...; ortalama renk ayni.

## Kapilar (6 dosya, PASS)

| kapi | sonuc |
|---|---|
| SON GORUNTUDE (golge dahil, abs(goruntu - zemin) > 1) yasak bolge: guvenli daire (760.6) disi, delik, centik, y < 217 | 0 piksel |
| gercek pay (guvenli daireye) | 2.6-3.2 px |
| deliğe en yakin | 30.3-32.3 px |
| en ust icerik | y=222-224 |
| cakisma | 0 |
| isim ve tarih kontrasti >= 4.5 (kati olcut, asagida) | PASS (en dusuk 4.54) |
| sonsuz en ince >= 4 px | 4.65 px |
| halka govdesi >= 4 px | en ince 4.37 px (226.25 derece) |
| halka ucu: uca 20 px'te >= 1.5 px | 1.98 px |
| halkasiz sembol >= +%15 | +%21.4 |

Halka genisligi elips normali boyunca 0.25 derece adimla, 0.1 px bilineer ornekle olculdu.

## A) HALKALI

Poster halkasi (ornek-tek-doku 2a08a78) elips:
- Yatay yari eksen 1668.5, dikey 1690.9; oran 0.9868 (dikey %1.3 uzun). Oran DEGISTIRILMEDI.
- Artik RMS: elips 4.18 px (p99 9.69), daire 9.47 px (p99 18.81). Bant kalinligi artiga dahil.

| olcu | V2 | V3 | kazanc |
|---|---|---|---|
| halka dis genislik x yukseklik | 608 px | 640 x 546 px (54.2 x 46.2 mm) | +%5.3 |
| ana sembol (posterdeki oran) | 378 x 358 px | 397 x 376 px (33.6 x 31.8 mm) | +%5.0 |

- Halka en buyuk boyutta: yari eksen 318 / 322.3.
- 319, 320, 321'de halka guvenli daire (pay 5) disina 14 / 60 / 142 piksel tasiyor (OLCUM.json red_son). Sinirlayan nokta halka uclari (y yaklasik 773).
- Tepe y=222'de, centik alti 216.9. Daha buyuk halka tepeyi deligin ustune almadan geometrik olarak sigmiyor.
- Yazi blogu en alta sabit. Isimler halka uclarinin arasinda, tarih uclarin altinda, kucuk semboller isimlerin ustunde.
- Uc profili: son 45 px yayda 4.5'ten 0'a dogrusal. Olculen 25 px'te 2.58, 20 px'te 1.98, 1.4 px'te 0.16, ucta 0.04.
  Acik aralikta genislik tam 0; kuyruk ve cengel yok.

## B) HALKASIZ

- Sembol 459 x 436 px (38.9 x 36.9 mm), V2'ye gore +%21.4.
- Tepe y=223; delige ve centige degmiyor.
- Yazilar arasi araliklar 0.70 x isim buyuk harf. Sembol, yazi blogu ve guvenli daire arasinda bos kalan dikey pay 0; yani izin verilen en buyuk boyut.

## Ortak

- Ozgun ana sembol, kucuk Yengec / Terazi, EMILY ∞ JAMES, 14 JUNE 2025.
- Isim buyuk harf 2.39 mm (28.2 px; deneme 1'de 2.377 mm idi), tarih 2.03 mm.
- Sonsuz 62 px, en ince 4.65 px. TASARIM DEGISIKLIGI (Merkez onayi bekleniyor):
  - Kaynak sonsuzun ic sac cizgileri 4 px'e kalinlasinca dis cizgiye birlesiyor.
  - Murekkep orani yaklasik %24'ten %66'ya cikiyor (bagimsiz inceleme olcumu); gorunus kalin iki gozlu sonsuz.
  - Kaynak da iki gozlu; "1 goz" sayimi ic cizgilerin acik ucundan gelen olcum yapisiydi.

## Butunlesme (tum altin ogeler ayni)

- **Golge:** zeminin kendi tonu (zemin x 0.45, opaklik 0.55), sag alta 1.5 px, sigma 1.2. Inceleme olcumu: kanallar esit oranla koyulasiyor
  (0.72-0.73), en fazla 3 px uzaniyor.
- **Doku:** zeminin yuksek gecirgen dokusu kendi std'sine normalize, overlay %8 (katman opakligi).
  - Gorunen etki (dokulu - dokusuz, altin pikselleri): luma std 3.3-3.9 seviye, p1 / p99 yaklasik +-7.5; goreli std %2.0-2.6.
  - Deneme 1'de bu %0.04-0.09 ile fiilen yoktu.
- **Golge tonlari:** altin lumasi Lmed altinda zemin ortalama rengi en fazla %18 karisir.
- **Isik:** tek doku kabartmasi ana sembolden. a = 0.78 / 0.74, b = 0.68 / 0.65; ikisi de pozitif = ust ve sol kenar parlak = isik sol ust. Uc zeminde ayni.
  - Not: halka tek duz renk (V2'de istenen tekduze parlaklik icin), kabartma tasimiyor. Kabartma uyumu zayif (r2 yaklasik 0.17).
- **Hale yok.** Okunurluk icin tum altina ortak ton kazanci (tek doku birligi korunur):

| | RUBY | SAPPHIRE | EMERALD |
|---|---|---|---|
| HALKALI | 1.04 | 1.00 | 1.04 |
| HALKASIZ | 1.08 | 1.00 | 1.04 |

## Okunurluk

WCAG. Kati olcut = tum murekkebin (alfa > 0.5) ortancasi / son goruntude murekkebin 1-12 px cevresi (ortanca ve en acik %5).
Parantez: cekirdek ortanca (deneme 1 yontemi).

| | isim1 | isim2 | tarih |
|---|---|---|---|
| HALKALI RUBY | 4.96 / 4.61 (6.30 / 5.85) | 5.02 / 4.60 | 4.90 / 4.54 (5.04 / 4.67) |
| HALKALI SAPPHIRE | 5.06 / 4.81 | 5.13 / 4.81 | 4.95 / 4.69 |
| HALKALI EMERALD | 5.15 / 4.65 | 5.29 / 4.73 | 5.08 / 4.59 |
| HALKASIZ RUBY | 5.22 / 4.88 | 5.21 / 4.81 | 5.38 / 5.01 |
| HALKASIZ SAPPHIRE | 5.01 / 4.76 | 5.00 / 4.73 | 5.11 / 4.84 |
| HALKASIZ EMERALD | 5.10 / 4.62 | 5.13 / 4.62 | 5.23 / 4.73 |

En dusuk 4.54 (halkali RUBY tarih, en acik %5 zemine gore). Golge sonuc goruntusunde olcume dahildir.

## Inceleme bulgulari (deneme 1) ve durum

| bulgu | durum |
|---|---|
| 1 doku fiilen 0 | duzeltildi (gorunen %2.0-2.6) |
| 2 kontrast yumusak olcut | kati olcuye gecildi; kapi kati olcutle |
| 3 golge yasak bolge sayimina girmiyor | son goruntuden sayim; pay 3 -> 5; gercek pay 2.6-3.2 |
| 4 sonsuz tasarim degisikligi | raporda; Merkez onayi bekleniyor |
| 5 halka sinirinin gerekcesi | red_son kaydedildi: sinirlayan guvenli daire, uclar |
| 6 govde / uc olcum gurultusu | elips normali olcumu |
| 7 isik notu isareti | duzeltildi; halkada kabartma yok (not) |
| 8 elips artigi kaynagi | OLCUM.json poster_elips.artik |
| 9 yerel girdiler | gercek ana sembol ve kucuk semboller yalniz Drive'da; yerelde vekil kullanildi |
| 10 yazi boyu yuvarlama | 2.39 mm |

Deneme 2 ciktisi ayrica yeniden bagimsiz incelenmedi.

## Dosyalar (Drive TEMP/ORNAMENT_ORNEK_20261102_1446/STIL3_V3/)

- {RUBY,SAPPHIRE,EMERALD}_GOLD_{HALKALI,HALKASIZ}_954.png (6)
- ONIZLEME_7cm.png: ust satir halkali, alt satir halkasiz; soldan RUBY, SAPPHIRE, EMERALD; delik cizili, kesim disi beyaz.
- OLCUM.json, KOSU_LOG.txt, KAYNAK_COMMIT.txt, RAPOR.md.
- Deneme 1 ciktisi ayrica TEMP/ORNAMENT_ORNEK_20261102_1425/STIL3_V3/ (gecersiz kabul edin).
