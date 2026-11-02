# STIL3_V5 yerel cikti, TUM KAYNAKLAR GERCEK (2 Kas 2026; Actions yok, Serdar gorsel secimi icin)

Betik `scripts/printful/ornament_ornek5.py` (32a1f5b), yerel (Pillow 11.0.0). Rakamlar `OLCUM.json` (olcum). Kapi: PASS (tum A secenekleri).
Kaynak sha256: CANCER_LIBRA_ana e86c2629... (depo ffce7b62), cancer_symbol_gold 2b5a3212..., libra_symbol_gold 6fe2d035...
(kosu https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41523782729 ile dala alindi, docs/ornament/kaynak/), BEIGE a55e7703..., AGED_PAPYRUS 0dfe2f2d...
Bagimsiz inceleme yapildi (2 yuksek, 4 orta, 5 dusuk); duzeltilenler ve kalanlar asagida.

## Kontrast (A-T1 = A-T2; kapi: RUBY ortanca, acik zemin kati >= 4.5)
| satir | ton | kapi degeri | kati (bilgi) | logo (bilgi) | uc < 0.17 mm (bilgi) |
|---|---|---|---|---|---|
| RUBY | altin 1.12 (V4) | ortanca 5.38 | 2.24 (kucuk burc) | 2.23 | ortanca 4.68, kati 2.48 |
| BEIGE P1 | bronz 1.0 | 5.08 | 5.08 | 2.70 | 2.22 |
| BEIGE P2 | bronz 1.0 | 5.03 | 5.03 | 2.64 | 2.22 |
| AGED_PAPYRUS P1 | bronz 0.92 | 4.54 | 4.54 | 2.57 | 2.12 |
| AGED_PAPYRUS P2 | bronz 0.85 | 4.73 | 4.73 | 2.62 | 2.19 |

- R2 (RUBY, yazida gomulu kenar yok; bilgi, RUBY_R2_BILGI.png): isim1 ortanca / kati 7.07 / 3.18 (ana RUBY 6.56 / 3.01), tarih 7.23 / 4.06.
- P1: bronz yazida doku yalniz koyulastirir; P2: yazi tek renk ana ton (inceleme: onceki P2 duz degildi, duzeltildi).
- Acik zeminde KUCUK BURCLAR da yazi kuralinda (doku yalniz koyulastirir, acik uc ana ton). Neden: gercek Terazi eski kuralla AGED'de en koyu
  carpanda 3.94. Bedel (inceleme olcumu): kucuk burc luma std %45-58 dusuyor (kabartma azalir; buyuk sembol kabartmali kalir). Eski kuralla BEIGE 0.70
  carpanda gecerdi. Karar Serdar.

## Diger kapilar (PASS)
- Halka kilidi goruntuden: tepe y 163.0, merkez x 476.0, ax 341.0. Yasak / cakisma 0. Bosluk 20/20/20 px (V4 10/12/11). Sembol 425 x 404, y 246 (V4 262).
- Leke: kaynak olceginde (onarim sonrasi) ana / Yengec / Terazi 0; yapay delik 3x3 ... 60x60 hepsi yakalanir (9 ... 3561 px).
  Hedef boydaki olcum yalniz <= 2 px catlak gorur; delikler kaynakta yakalanir (kucultme delik uretmez). 80 px delik cizgiyi keser, kapali delik degil.
- Terazi tepesi duz kesik: onarim kaynaklanan buyutme giderildi (24 px kenar payi). Kaynak dosyanin kendisinde ust satirda 50 px tam alfa var (inceleme).
- Doku oge basina %5 (P2 yazilari duz, kapsam disi).

## Halka ucu ve uzun isim
- 0.17 mm (2 px) alti uc boyu, her uc: V4 9.6, T1 19.1, T2 25.4 mm. Bu kisimda kontrast 2.1-2.5 (kati): baskida silik kalma riski olculmedi.
- CAGLAYANGUL / MAXIMILIAN mevcut boyda sigmiyor; gereken isim olcegi 0.557, buyuk harf 1.33 mm. Karar Serdar.

## Yontem degisiklikleri (V5)
Kontrast olcutu (Serdar), RUBY ortanca kapisi, aday listeleri (bronz 1.0-0.48; altin 1.12 sabit), yalniz ana ton koyulasir, yazilarda golge tonu yok,
halka gomulu kenar %20 (RUBY A; acik zeminde gomulu kenar yok), leke kapanis olceklemesi (kaynak 9x9 / 1600 px, 5 px ice, kapali delik < %1, 24 px kenar payi),
kucuk burclar acik zeminde yazi kuralinda.

## Dosyalar (bu klasor)
ONIZLEME_76mm_SECENEK.png (RUBY, BEIGE P1, BEIGE P2, AGED_PAPYRUS P1, P2 x V4 | A-T1 | A-T2), UC_T1_T2.png, UZUN_ISIM.png, RUBY_R2_BILGI.png,
{satir}_{A-T1,A-T2}_954.png, RUBY_R2_A-T1/T2_954.png, OLCUM.json, KOSU_LOG.txt.
