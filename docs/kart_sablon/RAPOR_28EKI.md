# Kart sablonu ornegi CANCER_LIBRA (Merkez 28 Eki, Serdar onayi): rapor

Dal kart-sablon-20261028 (main'e alinmadi). Etsy istegi 0, toplu uretim yok. Kaynak etiketi: [OLCUM] betik ciktisi, [DOSYA] depo / Drive, [API] GitHub API.

## Cikti
- Drive TEMP/KART_SABLON_ORNEK/20261028_155614 (klasor 1BO7-Vp3eVlsoNe9fuoXMa0wx499QDLyb), kosu 40719918531 (909671ae) [API].
- KONTAK_KART_SABLON.jpg 1n7kekCulhwR5GzUyYLQjt4BhFq1WFdv0 (292 KB, galeri sirasi, numaralar yeni galeri sirasi) [DOSYA].
- WA: WA_CANCER_LIBRA_S1_SEMBOL, S2_KISISEL, WA_ORTAK_S3_FORMAT, WA_CANCER_LIBRA_S4_SUREC, S5_GENEL.
- KUPA: KAPAK43/KUPA_KAPAK43_01_orange, KUPA_KAPAK43_08_fig (+ ONIZLEME_*_arama_4x5, ONIZLEME_*_magaza_1x1, KESIT_*_baslik_isim_1e1),
  KUPA_CANCER_LIBRA_K02_SEMBOL, K03_KISISEL, K04_STIL, K05_BOYUT, K07_SUREC.
- YD: CANCER_LIBRA_Y02, Y03, ORTAK_Y04, CANCER_LIBRA_Y05, YD_CANCER_LIBRA_GENEL.
- Ozetler: KART_OZET_WA_KUPA.json, KART_OZET_YD.json, KAPAK43/KAPAK43_OZET.json, KAPAK43_KONTROL.json, zemin_olcum.json.
- 27 Eki ust duzey dosyalari: 28 Eki 06:15'te ESKI/ altina tasinmisti (Drive listesi: 20261027_192528 ust duzeyinde yalniz
  20261028_065730 ve ESKI klasorleri, dosya yok) [DOSYA]; yeniden tasima yapilmadi.

## Kapilar (CI kosusu, 17 kart + 2 kapak PASS) [OLCUM]
- Metin (cizilen satirlar = beklenen, sirayla), baslik / etiket birebir + Title Case, yasak karakter / sozcuk, punto >= 58, renk (cizim + JPEG).
- Yerlesim: ortalama |sol - sag| <= 2 (en buyuk 1: S4 227/228); ayri bloklar >= 40 (en kucuk 46: baglac - burc etiketi, S1 / K02 / Y02);
  baglac: birlesme noktasi 40 px icinde egri disi murekkep 0 (eski ok basi eklenince 188 px ile FAIL, yerel deneme).
- Kupa: zemin kenari p90 en buyuk 2 (esik 3), kopuk ton 0.
- Kapak: 3000x2250, kenar tek renk seridi 0, beyaz satir 0; baslik y 328-712, baski bolgesi olcumu orange 856-1605, fig 868-1603 (kirpim 226-1762, PAY 60).
  28 Eki ornegine (TEMP/WA_KUPA_KART_ORNEK/20261027_192528/20261028_065730/KAPAK43) fark: orange ort 0.004 / max 12, fig ort 0.002 / max 9, p99 0.

## Olcu ozeti [OLCUM]
- S2 poster 952x1428 (olcek 1.0); S4 Champagne Ivory 1136x1428, olcek 1.0, yazi sutunu 1294 (numara 150 + metin 1144), adimlar 3/3/2/2 satir.
- Y03 Botanical 1140x1425; Y05 Timeless olcek 0.92 (1.0'da adimlar sigmadi), 1049x1311, metin sutunu 1231.
- K03 tek_on 870x699, tek_arka 787x699; K07 tek_on 1140x915; K04 kupa 563x452 (olcek 0.3343); K05 olcek 0.6101: 11 oz 1027x825, 15 oz 1046x989,
  merkez arasi 1266, yazi - not 126; S5 / YD GENEL poster yuksekligi 555.

## Galeri sirasi (yalniz rapor; yukleyiciye dokunulmadi)
| sira | WA (10) | KUPA (6 + stil kapaklari) | YD (11) |
|---|---|---|---|
| 1 | kapak (G1) | 01 kapak orange (4:3) | Y01 kapak |
| 2 | S1_SEMBOL (G2) | K02_SEMBOL (eski 02 yakin plan) | Y02 |
| 3 | S2_KISISEL (G3) | K03_KISISEL (eski 03) | Y03 |
| 4 | S3_FORMAT (ORTAK_G4) | K05_BOYUT (eski 05) | ORTAK_Y04 |
| 5 | S4_SUREC (cifte ozel; eski ORTAK_G5) | K07_SUREC (eski 07 bakim yerine) | Y05 |
| 6 | S5_GENEL (yeni) | K04_STIL (eski 04) | YD_<CIFT>_GENEL (yeni) |
| 7-10/11 | G6-G9 -> 7-10 (DB, PW, CI, WP) | eski 08-14 stil kapaklari -> 7-13 (fig ... loquat) | Y06-Y10 -> 7-11 (Starlit ... Botanical) |
- Renk / stil baglari kayar: WA DB 6->7, PW 7->8, CI 8->9, WP 9->10 (MB 1); YD Starlit 6->7 ... Botanical 10->11; kupa stil kapaklari 8-14 -> 7-13.
- Kupa K06 kaldirildi (canlidan silinecek), toplam 13 gorsel.
- Kupa aciklamasi numarayla atif yapiyor [DOSYA kupa_orchard/ilan/KUPA78_ORCHARD_METIN.csv]: "See photo 4" (stiller) -> 6, "See photo 5" (boylar) -> 4,
  "See photos 3 and 6" (kisisellestirme + eski K06) -> 3.

## Acik maddeler
1. WA S3 "14 Sizes" ve 5x7: yalniz 5x7 yuklemesiyle gecerli. YD Y04 "14 Sizes" / "Every style and size as a print" ve YD GENEL notu: YD yeni yapisina bagli (canli YD baski yalniz 8x10).
2. galeri_v10_liste.py 9'lu galeri ve ORTAK_G4 / ORTAK_G5 bekliyor; S4 artik cifte ozel (WA_<CIFT>_S4_SUREC), S5_GENEL yeni, sira 10'a cikiyor: yukleyici / liste guncellenmeli (yeniden numaralama yukleme isi).
3. Adlar: K02_YAKIN -> K02_SEMBOL, K07_BAKIM -> K07_SUREC, K06 yok.
4. Kupa stil kapaklari [DOSYA kupa_orchard/kod/cift.py:262]: 7 adet (fig, olive, pomegranate, almond, lemon, grape, loquat; eski 08-14). Eksik: Orange Blossom'un ayri stil kapagi yok (01 kapak orange). Diger 6 stil kapagi 4:3'e henuz uretilmedi (bu ornekte yalniz fig).
5. K04 notu "Every style in 11 oz and 15 oz": dogrulama [DOSYA denetim oturumu yerel kopyasi denetim_veri/SONRA_<ilan>.json, 23 Eki Etsy salt okuma dokumleri]: 25 kupa ilaninin 25'inde 8 stil x {11 oz, 15 oz}. Dokumler depoda / Drive'da degil; CANCER_LIBRA kupa ilani bu 25'te yok.
6. Font taramasi [OLCUM fontTools cmap]: kupa isim (EB Garamond, buyuk harf) ve mesaj (EB Garamond Italic): Latin aksanli 83/83, Turkce 12/12, Kiril 66/66, Yunanca 48/48; kalp (♥ ❤) yok. Cinzel (kapak basligi) Kiril 0/66. Not: kupa kodu isimleri Python str.upper() ile buyutuyor; Turkce "i" -> "I" (noktali I degil).
7. Kupa kapagi: Orchard kapak (kupa_kapak43) cikti "PERSONALIZED GIFT MUG" plakasi icermiyor; canli kare kapak bu iste okunmadi (Etsy istegi yok). Yarim plaka / kesik baslik yok (baslik 328-712, kirpim 226-1762).
   Etsy arama kirpimi (4:5 merkez, x 600-2400) arka kupadaki mesaji ("My favorite place is with y...") ve sol kupanin kulpunu kesiyor; magaza kirpimi (1:1) temiz.
8. Kupa surec karti ("we send a preview of your mug via Etsy Messages") kupa-siparis hattinin ONIZLEME + musteri mesaji taslagi adimina bagli [DOSYA docs/KUPA_SIPARIS_PLAN.md]; hat kuru, cron kapali, Printful'a elle. Drive PLAN.md P3.2 "kupa-siparis sahte receipt testi (8 stil)" acik. "21 Eki kayit kabul testi FAIL" kaydini bu iste bulamadim (depo docs ve Drive aramasi).
9. YD CLI degisti: yd_kart_toplu.py ve yd-kart-ornek.yml eski argumanlarla (--eski-r2 / --botanical / --timeless) calismaz; yd_sembol_qc.py kucuk isaretleri eski Y02 kutularindan kirpar. Toplu uretimden once uyarlanmali.
10. CI kupa sahnelerini her kosuda yeniden uretiyor (orchard_gorunum + kupa_zemin); ML / MJ sahneleri K06 kalktigi halde uretiliyor (gereksiz is).
11. K05: kirpim kutusu tabanlari hizali (gorev); golge paylari farkli oldugu icin 11 oz govde tabani 15 oz'dan ~9 px yukarida (inceleme olcumu).
12. Ortalama kapisi yerlesim hesabindan olcuyor (gorev geregi); piksel taramasi degil.

## Bagimsiz inceleme (tek ajan, 28 Eki)
Duzeltildi: (1) baglac kapisi ok basini yakalamiyordu -> beklenen egri alfasina gore olcum; (2) zemin kapisi yapi geregi FAIL veremiyordu -> 2 px serit p90;
(3) K04 sutunlari satirlar arasinda 22-24 px kayikti -> satir ortalamasi yalniz gorsel kutulariyla; (5) kapak baski bolgesi sabitti -> her stilde olcum;
(6) raqm zorunlu degildi -> DUR; (10) KONTAK numaralari galeri sirasina gore; (11) WA / kupa baslik ve etiket birebir kapisi; (12) kaynak notlari (K04, K05, eski kapak yolu).
Ayrica JPEG renk kapisinda gorsel kutusu +3 px (S5 WP kosesinde 2 px disarida JPEG tasmasi, 1 px).
Duzeltilmedi (acik madde): (4) 4:5 arama kirpimi (madde 7), (7) CI sahne yeniden uretimi (madde 10), (8) YD toplu / QC uyumu (madde 9),
(9) K05 govde tabani (madde 11), (13) ortalama kapisi hesap tabanli (madde 12).
