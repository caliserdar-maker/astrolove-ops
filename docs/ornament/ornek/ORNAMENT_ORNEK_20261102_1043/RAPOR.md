# Ornament ornek baski dosyalari: CANCER_LIBRA (2 Kas 2026)

Kosu: https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41430887909 (deneme 1/2, kapilar PASS)
Betik: `scripts/printful/ornament_ornek.py` (dal ornament-printful-katalog; uretim commit 52eb895). Olcum kaynaklari: `OLCUM.json` (kosu), `EK_OLCUM.json`
(sablon + cizgi deseni; bagimsiz inceleme sonrasi duzeltilmis betik fonksiyonlariyla ayni girdiler uzerinde yerel olcum, sha256 dosyada).
Baski dosyasi 954x954 px, 300 dpi. 1 px = 0.0847 mm. Gorunen daire 827 px (merkez 477, 477).

## Kaynaklar (hepsi oldugu gibi, yalniz esit oranli kucultme)

| oge | kaynak | sha256 (ilk 12) |
|---|---|---|
| ana sembol | Drive ANA_SEMBOL78_KATMAN_20261008/CANCER_LIBRA_ana.png (78 tek dokulu altin) | e86c26296293 |
| kucuk semboller | Drive ARCHIVE/LEGACY_COMPONENTS/zodiac_symbols_gold/cancer_symbol_gold.png, libra_symbol_gold.png | 2b5a32121ce8, 6fe2d0355ee5 |
| halka | dal ornek-tek-doku (2a08a78) motor/varlik/halka/HALKA_BLUE_16x20.png (MB, STIL3), HALKA_16x20.png (CI); poster plakasindan piksel olarak ayrilmis orijinal halka | 2a11ac819c61, 9b218397b32f |
| sonsuz | dal siparis-gpt (6da763a) motor_gpt/alfa_ogeler.npz ['sonsuz'] | d373403191a6 |
| yazi tipi | ornek-tek-doku motor/font: Cinzel wght 500 (isim), EB Garamond Italic (tarih, posterdeki tagline yazi tipi) | f4d83d34d1f6, bba2c4499c93 |
| tek doku | ornek-tek-doku motor/tek_doku.py (egri_olc, doku_olc, duz_l, renk) | 1889906fb299 |
| zemin MB / CI | Drive TEMP/SIPARIS_ISIM/PLATES BLUE_16x20.png / MODERN_16x20.png: merkezden disa radyal ortanca renk profili | cef460878b3f, 878f590358bc |
| zemin STIL3 | Drive TEMP/ORNAMENT_ZEMIN3_20261102 (Canva, AI), 1264 -> 954 esit olcek, kirpma yok, baska islem yok | 99f2e901f485, cb2f153fb953, c0bddf95d768 |

Ham (renksiz) ozgun sembol: dal siparis-gpt `motor_gpt/girdi78/ana/cancer_libra_alfa.png` (8185x7702, 78 cift icin ayni klasorde).
Bu ornekte sekil ana sembol katmanindan alindi (posterdekiyle ayni). Ham alfa ile ana alfa IoU 0.831 olculdu: ikisi yalniz kendi kutularina olceklenip
ust uste kondu, hizalama yapilmadi. En / boy oranlari da farkli (1.063 / 1.057). Sekil uyumu degerlendirilmedi; ham alfa bu uretimde kullanilmadi.

Tek doku: renk egrisi, parlaklik (Lmed) ve boru profili + kabartma ana sembolden olculdu. Halka, kucuk semboller, isimler, sonsuz ve tarih bu modelle
boyandi. Ana sembolun kendi altin yuzeyi degismedi.

## Yerlesim ve kapilar (MB, CI, STIL3 ayni yerlesim)

| olcu | px | mm | kaynak |
|---|---|---|---|
| kenar payi (icerik ile gorunen daire arasi en kisa) | 58.8 | 4.98 | olcum (esik >= 40 px: PASS) |
| delik boslugu (gorunen daire tepesi ile icerigin ustu arasi) | 163.5 | 13.84 | olcum (esik >= 160 px: PASS) |
| halka capi | 554.1 | 46.91 | gorunen dairenin %67'si (istek %65-70) |
| halka tepe kalinligi | 3 | 0.25 | poster halkasi esit oranla 0.1656 kucuk |
| ana sembol (en x boy) | 344 x 327 | 29.13 x 27.69 | genislik / halka capi = poster orani (2084 / 3345) |
| kucuk Cancer / Libra yuksekligi | 58 / 60 | 4.91 / 5.08 | poster orani |
| isim buyuk harf yuksekligi | 28.1 | 2.38 | poster orani |
| sonsuz genisligi | 62 | 5.25 | poster orani |
| tarih buyuk harf yuksekligi | 23.9 | 2.02 | poster tagline orani |

Dikey araliklar posterdekinden sikistirildi: kucuk semboller sembolun 0.55 harf yuksekligi altinda, isimler 0.85, tarih 1.15. Bu degerler tasarim
secimidir, posterden olculmedi. Poster araliklariyla (hesap: sembol alti y=634 + (5281-3176) x 0.1656) tarih tabani y=983 olurdu; icerik siniri y=850.5, yani tasardi.
Cakisma kapisi: halka (5 px genisletilmis) ve sembol ile diger ogeler arasinda cakisma 0.

## Printful sablonu (CDN, mockup_templates role=template, Circle.png 1000x1000; EK_OLCUM.json sablon)

Baski dosyasi pikseline cevrim: (x - 87.33) x 1.1559.
- Sablonun dis dairesi = tum baski dosyasi (954 px).
- Kesikli guvenli daire capi 760.6 px (64.4 mm). Icerigimizin en dis noktasi merkezden 354.7 px uzakta, guvenli yaricap 380.3 px: icerde.
- Asma deligi merkezi (477, 164), capi 56.6 px (4.8 mm, alandan esdeger cap), delik alt kenari y=192.6.
- Guvenli alan delik etrafinda centik yapiyor; centigin alt ucu y=216.9.
- Icerigimiz (halka tepesi) y=227'de basliyor, centigin 10 px (0.85 mm) altinda.
- Not: sablonda urunun dis siniri ayrica cizilmemis. "Gorunen alan 827 px" varsayimi (aciklamadaki 2.76") ile sablonun guvenli dairesi (761 px)
  farkli; icerik ikisinin de icinde.

## Okunurluk (WCAG kontrast; yazi cekirdek ortanca rengi / yazinin arkasindaki zemin ortancasi; p95 = arkadaki en acik %5 zemin)

Esik: yazilar kucuk (isim buyuk harfi 2.38 mm, tarih 2.02 mm, yaklasik 9-10 pt), bu boyda WCAG normal metin esigi 4.5:1 gecerli.
"Kotu" sutunu = ortanca ve p95'ten dusuk olani. * = 4.5 altinda.

| stil | isim1 | isim2 | tarih | kotu deger |
|---|---|---|---|---|
| MB | 6.89 | 7.30 | 5.22 | 5.18 |
| CI | 2.21* | 2.08* | 2.88* | 2.08* |
| SAPPHIRE_GOLD | 6.34 | 6.68 | 4.90 | 4.35* (tarih p95) |
| EMERALD_GOLD | 3.92* | 4.33* | 3.19* | 2.12* (tarih p95) |
| RUBY_GOLD | 5.69 | 6.13 | 4.41* | 4.12* (tarih p95) |

- 4.5 altinda: CI tum yazilar, EMERALD tum yazilar, SAPPHIRE ve RUBY tarih. MB tum yazilar 4.5 ustunde.
- Zemin desen yogunlugu (yazinin arkasindaki luma std): SAPPHIRE 4.0-5.5, EMERALD 7.0-9.8, RUBY 1.9-2.1, MB 0.4-0.5, CI 0.8-0.9.

## Risk: halka cok ince

Halka tepe kalinligi 3 px (0.25 mm); tam yogunlukta yalniz 1-2 satir, uclara dogru daha da inceliyor. Seramik sublimasyonda basilmama ya da
kesik gorunme riski var; olcen kapi yok. Poster halkasinin esit oranli kucultulmus hali (istek geregi kalinlik degistirilmedi). Karar Merkez'de.

## Uzun isim testi (ALEXANDRINA / MAXIMILIANO, yalniz MB)

- Sigdi, kapilar PASS. Betik 11 denemede tum metin olcegini 28.1 -> 22.0 px dusurdu, isim satirini ayrica %94.1'e kucultu.
  Hangi kapinin kucultmeyi tetikledigi kaydedilmedi.
- Isim buyuk harfi 1.75 mm, tarih 1.58 mm. Kenar payi 40.7 px (esik 40, sinirda).
- Isim kontrasti 6.89 -> 5.17'ye dustu (kucuk yazida cekirdek pikseller az).
- Oneri (Merkez karari, esikler olculmedi):
  - (a) Uzun isimlerde isimler iki satir (ISIM1 / ∞ / ISIM2).
  - (b) Kucuk semboller isim satirinin iki ucuna, isimlerle ayni satira.
  - (c) Isim harf siniri koyup asanlarda onizleme gostermek.

## RUBY sol kenar dikey cizgi bandi (EK_OLCUM.json cizgi)

Ilk olcum (OLCUM.json RUBY_cizgi_bandi: bant x=0-14, z=-5.8) GECERSIZ: 61 px yatay ortalamanin kenar yansitmasi ve zeminin vinyeti kenarda yapay
sapma uretiyordu (bagimsiz inceleme; ayni imza sag kenarda ve diger zeminlerde de cikti).
Yeni yontem: ardisik sutun farkinin isaretli ortalamasi (tutarli dikey cizgi), sol 64 / orta / sag 64 sutun.

| | sol | orta | sag |
|---|---|---|---|
| 1264 kaynak | 0.45 | 0.79 | 0.40 |
| 954 baski | 0.15 | 0.24 | 0.14 |

- Sol kenara ozgu dikey bant BULUNMADI: sol kenar ortadan zayif. Ayrica satir bantlari x R kanali, 15 px medyan sapmasinda 5 sigma ustu dar cizgi yok.
- Bulunan: tum goruntude 2 px periyotlu sutun dokusu (ardisik sutun isaretleri donusumlu). 954'e kucultmede belirgin zayifliyor.
- Serdar'in gordugu bandin yaklasik konumu (x araligi) verilirse o bolge ayrica olculur.
- Kaynak kare (1264x1264, docs/ornament/zemin3/ZEMIN3.json): 954x954'e olcekte en / boy bozulmaz, kirpma yok.

## Dosyalar

CANCER_LIBRA_MB_954.png, CANCER_LIBRA_CI_954.png, ONIZLEME_7cm.png, UZUN_ISIM_TEST.png (+ _954), OLCUM.json, EK_OLCUM.json, KOSU_LOG.txt, sablon/,
STIL3/ (SAPPHIRE_GOLD_954.png, EMERALD_GOLD_954.png, RUBY_GOLD_954.png, STIL3_ONIZLEME_7cm.png).
