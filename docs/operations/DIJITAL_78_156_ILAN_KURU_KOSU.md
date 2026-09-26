# 390 -> 78 dijital donusumu: KURU KOSU (GOREV_0013 md.2, 26 Eyl 2026)

**Etsy'ye HICBIR cagri yapilmadi.** Uretici: `scripts/etsy/dijital78_donusum_kuru.py`.
QC: **PASS** (esikler asagida). Cikti: Drive `TEMP/DIJITAL_78/DONUSUM_*.csv`.

## Sayilar cozuldu (eski plandaki 156/312 celiskisi kapandi)

Havuz **390 dijital poster ilani = 78 cift x 5 edisyon**. Korunan 78, pasife
alinacak 312. "156 ilan" adlandirmasi 78 dijital + 78 wallpaper ilanina aitti;
wallpaper 78 ilani bu havuzda DEGIL (bkz. EKSIK E03). Ziyaret verisi gerekmedi:
korunan ilan zaten `DIJITAL_78_KALAN_ILANLAR.csv` (25 Eyl) icinde secilmis.

Olculen (kod ciktisi, tahmin yok):

| esik | olculen | sonuc |
|---|---|---|
| korunan satir | 78 | PASS |
| pasif satir | 312 | PASS |
| havuz toplam / tekil id | 390 / 390 (mukerrer 0) | PASS |
| baslik en uzun | 97 karakter (sinir 140) | PASS |
| 20 karakteri asan etiket | 0 cift | PASS |
| korunma sebebi belirsiz | 0 | PASS |
| korumali 3 ilan korundu | 3/3 | PASS |

Korunan edisyon dagilimi (25 Eyl listesi): Midnight Blue 35, Champagne Ivory 24,
Deep Black 8, Pure White 7, Warm Parchment 4. **20 Eyl KALACAK.csv'den farkli**
(CI 35 / MB 23 / WP 10 / PW 5 / DB 5) - bkz. EKSIK E01.

## Donusum eslemesi (her korunan ilan)

- baslik: `{A} and {B} Personalized Zodiac Couple Wall Art, Names and Message, Digital Files`
- 13 etiket (SEO_DIJITAL_WALLPAPER bolum A); cifte bagli olan yalniz ilk ikisi.
- fiyat 9.99 -> **14.99 USD**; `when_made=made_to_order`, `type=download`.
- teslim: 5 renk = 5 ZIP (`AstroLove_<S1>_<S2>_<EDISYON>_ALL_SIZES.zip`), her ZIP
  5 JPG (2:3 7200x10800, 3:4 7200x9600, 4:5 7200x9000, 11:14 6600x8400,
  A 9934x14044) + Print and Care Guide PDF.
- kisisellestirme: 3 text_input - First name (30), Second name (30), Short message (80).

## Cikti dosyalari

- `DONUSUM_KURU_KOSU.csv` - 78 satir, 25 kolon (yukaridaki esleme + sebep + pasif id'ler).
- `DONUSUM_PASIF_LISTE.csv` - 312 satir (cift, pasif id, sira, korunan id, islem, pin).
- `DONUSUM_EKSIK.csv` - 11 madde (E01-E11), her biri: etki, ayrinti, kim, kaynak.
- `DONUSUM_QC.json` - olculen esikler + 20 Eyl listesiyle fark ornekleri.

## Acik maddeler (ozet; tamami DONUSUM_EKSIK.csv'de)

E01 iki kalan-ilan listesi **27 ciftte** celisiyor (hangisi baglayici?).
E02 `digital-desc-batch.yml` AKTIF (4 saatte bir, APPLY=true); olculen son iki
kosuda Etsy'ye 0 yazma (yapacak ilan kalmamis) ama cron duruyor ve uyguladigi
metin eski instant-download aciklamasi -> donusumden once kapatilmali (ayri onay).
E03 wallpaper 78 ilani (6.65 -> 6.99) bu havuzda yok. E04 wallpaper Watch cihazi
uretilmiyor (ilan metni 4 cihaz / 16 JPG vaat ediyor). E05 isimli uretim yalniz
24x32; teslimat 5 boy istiyor. E06 kisisellestirilmis ZIP ad kurali yok.
E07 MTO siniri 5 dosya x 20 MB - 5 ZIP sinira tam oturuyor, en buyuk ZIP 18.48 MB.
E08 mesaj siniri 80 (MTO kurallari) vs 35 (GOREV_0014) celisiyor. E09 galeri
kartlari dogrulanmadi. E10 `updateListing` taslagi yayina alir. E11 dusen 312
ilanin olcut degerleri yok; sebep tutarlilikla turetildi.
