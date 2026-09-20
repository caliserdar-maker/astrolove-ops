# DIJITAL 390 -> 78 BIRLESTIRME PLANI (salt okur olcum, 20 Eyl 2026)

Karar (Serdar, 20 Eyl 2026): 390 dijital poster ilani 78'e birlesecek. Her ciftte
TEK dijital ilan kalir, alici 5 edisyonun hepsini alir (5 ZIP + her ZIP'in icinde
tesekkur PDF'i). Indirme linki yok. Kalan 312 ilan silinmez, devre disi birakilir.

**Bu kosuda Etsy'ye HICBIR yazma yapilmadi.** Uygulama ayri onay bekler.

## Kosular

| kosu | sonuc | Etsy cagrisi |
|---|---|---:|
| 35501017661 | FAIL: `GET /shops/{id}/receipts` -> 403 `requires scope: transactions_r` | 11 |
| 35501288048 | SUCCESS, 13/13 adim, 7 dk 32 sn | 33 |
| **toplam** | | **44** |

Kalan gunluk Etsy kotasi kosu sonunda: 452.

## Olculen envanter (kosu 35501288048)

- Aktif ilan 546 = 390 dijital poster + 78 duvar kagidi + 78 POD. draft / inactive /
  expired / sold_out: 0. Siniflanamayan: 0.
- Ayrim kurali (tahmin yok): `listing_type == physical` -> POD; baslikta `wallpaper`
  -> duvar kagidi; `listing_type == download` ve ilk ikisi degilse -> dijital poster.
- Fiyat: dijital 9.99 USD (390), duvar kagidi 6.65 USD (78), POD 29.99 USD (78).
- 78 cift, her cift tam 5 ilan. Kalan 78, kapanacak 312.

## Kalacak ilan dagilimi (edisyon bazinda)

| edisyon | kalan ilan |
|---|---:|
| Champagne Ivory | 35 |
| Midnight Blue | 23 |
| Warm Parchment | 10 |
| Pure White | 5 |
| Deep Black | 5 |

Koruma altindaki 3 ilan kosulsuz korundu: 4552582170 (Leo+Pisces CI),
4555411521 (Aries+Scorpio DB), 4553832904 (Capricorn+Libra MB).

## ACIK BLOKER 1 - satis gecmisi okunamiyor

Etsy token'inda `transactions_r` kapsami yok; `receipts` ucu 403 doner. Bu yuzden
Serdar'in (b) onceligi (satis gecmisi olan ilan kalir) UYGULANAMADI. Secim (a), (c),
(d), (e) onceliklerine gore yapildi ve KALACAK.csv'de her satir
`b) satis verisi OKUNAMADI ->` on ekiyle ve `GECICI` notuyla isaretlendi.

Magaza toplam satisi `transaction_sold_count = 5` (ilan bazinda dagilimi bilinmiyor).
En fazla 5 cift etkilenebilir. Cozum: token'a `transactions_r` kapsami eklenip
yeniden yetkilendirme; sonra ~10 cagriyla secim yeniden turetilir.

## ACIK BLOKER 2 - POD/wallpaper capraz linkleri okunamadi

`getListingsByShop` toplu ucunun donusunde `description` alani bos geldi; 156
POD + wallpaper ilaninin hicbirinde link bulunamadi (LINK_ESLEME.csv 0 satir).
Aciklamalarin var oldugu B98 kaydinda yazili. Yontem degisikligi gerektigi icin
DURULDU (CLAUDE.md kural 3). Iki secenek:

1. 156 ilanin aciklamasi tek tek okunur (156 cagri) - "ilan bazinda okuma yasak"
   kuralina aykiri, Serdar onayi gerekir.
2. Drive `TEMP/POD_LISTING/XSELL_STATE.csv` kullanilir (390 satir, digital_id ->
   pod_link eslemesi zaten var) - 0 Etsy cagrisi.

Pinterest tarafi tamamlandi: PIN_ESLEME.csv, 390 pin kaydinin 312'si kirilacak.

## ZIP kontrolu (Drive, 0 Etsy cagrisi)

390 ZIP, merkezi dizin 390/390 okundu (dosyalar indirilmeden, aralik istegiyle),
0 hata. Envanterle capraz kontrol: ZIP'i olmayan ilan 0, ilani olmayan ZIP 0.
Ic yapi 390/390 ayni: 5 JPG + 1 Print and Care Guide PDF.

Olculen pikseller (300 DPI): 2:3 = 7200x10800, 3:4 = 7200x9600, 4:5 = 7200x9000,
11:14 = 6600x8400, A = 9934x14044.

- **23 ZIP, tesekkur PDF'i (160.153 bayt) eklendikten sonra 19.8 MB guvenlik
  esigini asiyor; 10 tanesi 20 MB ham sinirini da asiyor.** En buyugu 20.19 MB
  (Sagittarius+Taurus Midnight Blue). Asanlarin cogu Midnight Blue ve
  Warm Parchment edisyonu.
- Dosya adi 70 karakter sinirini asan: 0 (en uzun 63 karakter). Ad onerisi gerekmedi.
- **77 Pure White ZIP'i Drive'da canli ilandakinden FARKLI** (ad ayni, bayt farkli;
  Drive surumu ~%3 daha buyuk). Canli ilana yuklenmis surum eski. Hangi surumun
  dogru oldugu Serdar'a soruldu.
- Canli dosya ornek dogrulamasi: 20 ilan okundu, 20/20 Drive anlik goruntusuyle ayni.

## Metin taslaklari

3 cift (Aries+Leo, Cancer+Scorpio, Gemini+Gemini) icin baslik, 13 etiket, EN ve RU
aciklama uretildi. QC 3/3 PASS: iki burc her baslikta, tam 13 etiket her biri
<= 20 karakter, tek burc aramalari (zodiac / sign / star sign) iki burc icin de
kapsandi, uzun tire yok, "5 Colors" hem baslikta hem aciklamada, yasak ifade yok.
Basilabilir boyutlar tahmin edilmedi; olculen piksellerden 300 DPI ile turetildi.

## Ciktilar

Drive `ASTROLOVE/TEMP/DIJITAL_78/` (14 dosya):
ENVANTER.csv, KALACAK.csv, LINK_ESLEME.csv (bos, bkz. Bloker 2), PIN_ESLEME.csv,
ZIP_KONTROL.csv, ZIP_OZET.md, METIN_TASLAK.md, FIYAT_VERI.md, AYRIM.md,
DOSYA_ORNEK_DOGRULAMA.csv, ETSY_HAM.json, KAPAK_ORNEK.jpg, KAPAK_A_DUZ.jpg,
KAPAK_B_KADEMELI.jpg.

KAPAK_ORNEK.jpg Drive id: `1BWi1RYd6cUbIlhcEm81CfSn72Y7L24je` (4816x3000,
947.525 bayt, 1 MB sinirinin altinda; iki alternatif yan yana). Tek tek:
KAPAK_A_DUZ.jpg `1vKqZ1McpiEUKdDOZXnssXSyp-cCUSNST`,
KAPAK_B_KADEMELI.jpg `1U5wdyq1eEErY06ufkm2IiBJEevPdGMsv` (her biri 2400x3000, 4:5).

## Kod

- `scripts/etsy/dijital78_envanter.py` (adim 1-2-4-6)
- `scripts/etsy/dijital78_zip.py` (adim 3)
- `scripts/etsy/dijital78_metin.py` (adim 5 + QC)
- `scripts/etsy/dijital78_kapak.py` (adim 7)
- `.github/workflows/dijital-78-plan.yml`
