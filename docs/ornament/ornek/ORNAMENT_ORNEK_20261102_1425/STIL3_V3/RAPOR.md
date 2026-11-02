# STIL3_V3: halkali + halkasiz x RUBY / SAPPHIRE / EMERALD (2 Kas 2026)

Kosu: https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41461450154 (deneme 1/2; betik kapilari PASS; yerelde once PASS).
Betik: `scripts/printful/ornament_ornek3.py` (uretim 30d5056). Rakamlar `OLCUM.json` (kosu olcumu). 1 px = 0.0847 mm.
Zeminler: Drive TEMP/ORNAMENT_ZEMIN3_20261102/V2 (kosu 41458712603, 14:06 UTC indirildi); 1264 -> 954 esit olcek, kirpma yok.
RUBY "degismedi" denmisti; dosya yeniden disa aktarilmis, sha farkli (7c009226... / onceki c0bddf95...), ortalama renk ayni (62.7 / 0.9 / 6.5).

## Kapilar (tum 6 dosya)

| kapi | sonuc |
|---|---|
| yasak bolgeye tasan piksel (guvenli daire 760.6 - 3 px disi, delik + 2 px, centik + 2 px, y < 222, tuval disi) | 0 |
| cakisma (halka / sembol 7 px, yazi ogeleri 5 px genisletilmis) | 0 |
| isim ve tarih kontrasti >= 4.5 (murekkebin 1-12 px cevresi; ortanca ve en acik %5) | PASS (en dusuk 4.51) |
| sonsuz en ince >= 4 px | PASS (4.35 px) |
| halka govdesi >= 4 px | PASS (en ince 4.04 px) |
| halka ucu: son 20 px'te >= 1.5 px'ten 0'a | PASS (19.6 px'te 1.98, 2.8 px'te 0.36) |
| halkasiz sembol >= +%15 | PASS (+%22.0) |

- Delige en yakin icerik: 31.3 px (halkali), 32.3 px (halkasiz).
- Guvenli daireye pay 3.4 px. Ust: halkali 223, halkasiz 224 (centik alti 216.9).

## A) HALKALI

Poster halkasi (ornek-tek-doku 2a08a78, HALKA_BLUE_16x20.png) ELIPS olarak olculdu:
- Yatay yari eksen 1668.5, dikey 1690.9; oran yatay / dikey 0.9868 (dikey %1.3 uzun). Daire varsayiminda artik 9.5 px, elipste 4.2 px.
- Acik aralik 44-136 derece. Oran DEGISTIRILMEDI.

| olcu | V2 | V3 | kazanc |
|---|---|---|---|
| halka dis genislik (alfa 0.5) | 608 px | 642 px (54.4 mm) | +%5.6 |
| ana sembol (posterdeki oran) | 378 x 358 px | 398 x 377 px (33.7 x 31.9 mm) | +%5.3 |

- Halka dis yuksekligi 546 px; yari eksenler 319.0 / 323.3 px.
- Halka gercekten "guvenli dairenin izin verdigi en buyuk" boyutta. Tepe y=222'ye sabitken yanlar guvenli daireye 3.4 px kaldi.
  Daha buyuk eksen (390 -> 320) hem guvenli daire disina tasiyor hem sembolu yazi satirlarina carptiriyor (OLCUM.json red_ilk).
- Kazanc bu yuzden sinirli. Daha buyuk halka, tepeyi deligin ustune almadan geometrik olarak mumkun degil.
- Yazi blogu en alta sabitlendi. Isimler (y 769-806) halka uclarinin hizasinda, uclarin arasinda; tarih uclarin altinda.
  Kucuk semboller isimlerin ustunde; sira ayni.

Halka genisligi:
- Govde = max(poster profili x tepe 9 px, 4.5 px). Olculen govde 4.04-9.57 px.
- Uclar: son 45 px yayda genislik 4.5 px'ten dogrusal 0'a.
- Kapsama 4x ornekle (V2'deki 1 px alti sisme yok). Medyan kuyrugu yok; acik aralikta genislik tam 0.

| uca uzaklik (px) | 58.9 | 47.6 | 36.4 | 25.2 | 19.6 | 14.0 | 8.4 | 2.8 |
|---|---|---|---|---|---|---|---|---|
| genislik (px) | 4.71 | 4.48 | 3.61 | 2.56 | 1.98 | 1.38 | 0.77 | 0.36 |

(sag ve sol uc ayni)

## B) HALKASIZ

- Sembol 461 x 438 px (39.0 x 37.1 mm), V2'ye gore +%22.0.
- Sembol tepesi y=224: delige ve centige degmiyor.
- Sinirlayan: guvenli daire (pay 3.4 px) ve yazi blogu ile arasindaki 0.70 harf boslugu.
- Yazilar arasi araliklar 0.70 x isim buyuk harf (20 px). Sembol alti ile kucuk semboller arasinda ek bos yer 0.2 px; yani sembol izin verilen en buyuk boyutta.

## Ortak ogeler

- Ozgun ana sembol: Drive ANA_SEMBOL78_KATMAN_20261008/CANCER_LIBRA_ana.png. Kucuk Yengec / Terazi: zodiac_symbols_gold.
- Isimler Cinzel 500, tarih EB Garamond Italic. Yazi boyu degismedi: isim buyuk harf 2.38 mm, tarih 2.02 mm. Yazi olcegi 1.0.
- Sonsuz (siparis-gpt alfa_ogeler.npz) 62 px (5.25 mm) genislikte, en ince 4.35 px.
  - TASARIM DEGISIKLIGI: kaynak sonsuzun iki ic sac cizgisi bu boyda 4 px'e kalinlasinca dis cizgiye birlesiyor.
  - Kapali goz sayisi 1'den 2'ye cikti; gorunus duz iki gozlu sonsuz. Ic sac cizgileri 62 px'te zaten secilemiyordu.

## Butunlesme

Tum altin ogelere ayni ayarlar uygulandi (sembol, halka, kucuk semboller, isimler, sonsuz, tarih):
- **Golge:** zeminin kendi koyu tonu (zemin x 0.45, opaklik 0.55), sag alta 1.5 px, sigma 1.2. Siyah degil.
- **Doku:** zeminin yuksek gecirgen dokusu (sigma 6) altina soft light, %8.
- **Golge tonlari:** altin lumasi Lmed altindaki tonlara zemin ortalama rengi (yakut kizil, safir lacivert, zumrut yesil) en fazla %18 karisir.
- **Isik yonu:** tek doku kabartmasi ana sembolden olculdu (a = 0.78 / 0.74, b = 0.68 / 0.65; ikisi de pozitif = ust ve sol kenar parlak = isik
  sol ust). Uc zeminde aynidir; golge sag alt.
  - Not: OLCUM.json'daki isik_not isareti hataliydi ("a < 0"), dogrusu a > 0 ve b > 0; betik duzeltildi.
- **Hale yok. Altin ton kazanci 1.00** (gerek olmadi). Tek doku birligi korunur.

## Okunurluk

WCAG. Yazi = cekirdek ortanca. Zemin = sonuc goruntusunde (golge dahil) murekkebin 1-12 px cevresi; ortanca / en acik %5.

| | isim1 | isim2 | tarih |
|---|---|---|---|
| HALKALI RUBY | 5.90 / 5.52 | 6.51 / 5.96 | 4.84 / 4.51 |
| HALKALI SAPPHIRE | 6.66 / 6.32 | 7.26 / 6.80 | 5.30 / 5.03 |
| HALKALI EMERALD | 6.14 / 5.56 | 6.83 / 6.12 | 5.04 / 4.55 |
| HALKASIZ RUBY | 6.15 / 5.74 | 6.56 / 6.02 | 5.08 / 4.74 |
| HALKASIZ SAPPHIRE | 6.96 / 6.61 | 7.34 / 6.93 | 5.62 / 5.34 |
| HALKASIZ EMERALD | 6.44 / 5.76 | 6.86 / 6.18 | 5.30 / 4.78 |

- Tum degerler >= 4.5. En zayif: halkali RUBY tarih, en acik %5 zemine gore 4.51 (pay 0.01). 3-6 px bandinda da ayni (4.51).
- Golge yazinin sag altini en fazla %30 koyulastirir. Olcum sonuc goruntusunde yapildigi icin bu etki dahildir.

## Dosyalar (Drive TEMP/ORNAMENT_ORNEK_20261102_1425/STIL3_V3/)

- RUBY_GOLD_HALKALI_954.png, SAPPHIRE_GOLD_HALKALI_954.png, EMERALD_GOLD_HALKALI_954.png
- RUBY_GOLD_HALKASIZ_954.png, SAPPHIRE_GOLD_HALKASIZ_954.png, EMERALD_GOLD_HALKASIZ_954.png
- ONIZLEME_7cm.png: ust satir halkali, alt satir halkasiz; soldan RUBY, SAPPHIRE, EMERALD; 827 px gorunen daire, kesim disi beyaz, delik cizili.
- OLCUM.json, KOSU_LOG.txt, KAYNAK_COMMIT.txt, RAPOR.md.
