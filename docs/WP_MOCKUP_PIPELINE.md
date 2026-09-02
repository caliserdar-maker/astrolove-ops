# wp-mockup hatti (galeri gorselleri, 3000x2250)

Kaynak kararlar: B93 madde 4 (mockup haritasi), WP_LAYOUT_SPEC bolum 5a/7,
Mo 2 Eyl: SET04 = wp-mockup hattinin ILK ciktisi. Butun degerler pilot
dosyalardan OLCULMUSTUR (yerel prototip 2 Eyl; Actions kosusu ayni kodla).

## 1. Sahne dosyalari

Bos sahne (cihazsiz/ekransiz master) YOKTUR; pilot mockup'lar ChatGPT'de
butun olarak uretildi. Sahne masteri = pilot galeri dosyasinin kendisi:

| Sahne | Master (Drive `WALLPAPER/MOCKUP_V2/CANCER_LIBRA/`) | Ekranlar (soldan saga) |
|---|---|---|
| SET01 | WA_MOCKUP_V2_SET01_Cancer_Libra_FINAL.jpg | Phone MB, Phone CI |
| SET03 | WA_MOCKUP_V2_SET03_Cancer_Libra_FINAL.jpg | Phone MB, DB, CI, WP |
| SET04 | **SET01 masteri** + edisyon degisimi (DB, WP) | Phone DB, Phone WP |
| SET06 | WA_MOCKUP_V2_SET06_Cancer_Libra_FINAL.jpg | Desktop MB (monitor), Desktop MB (laptop), Tablet MB |
| SET07 | WA_MOCKUP_V2_SET07_Cancer_Libra_FINAL.jpg | Phone MB (Dynamic Island), Watch MB (yalniz sembol) |
| SET10Y | WA_MOCKUP_V2_SET10_YAZILI_Cancer_Libra_FINAL.jpg | Phone MB; sag yazi alani ciftten bagimsiz, dokunulmaz |

SET04 bulgusu: pilot SET04_FINAL (2048x1536) ile SET01 (2048'e indirilmis)
arasinda ekran disi fark 0.5/255 = AYNI SAHNE, yalniz ekranlar DB+WP.
3000x2250 SET04 bu yuzden SET01 masterinden edisyon degisimiyle uretilir;
olcek buyutme yoktur. Onaylanan 3000 dosya sonraki kosularda SET04'un kendi
masteri olur (`SCENES["SET04"]` guncellenir, `edition_map` kalkar).

Pilot ekranlarinin FINAL_V2 wallpaper'larin birebir perspektif yerlesimi
oldugu olculdu (SET01 MB: ekran ici ortalama fark 1.65/255, uyum 0.42 px,
luma orani 1.000). Yani ekran icerigi hesapla degistirilebilir; sahnenin
geri kalani (el, masa, golge, cerceve, Island, saat kasasi) piksel piksel
aynen kalir. 78 ilanin galerisi boylece pilotla ayni sahneyi tasir.

Kalibrasyon ciktisi: Drive `WALLPAPER/MOCKUP_V2/_CALIB/` (calib.json,
masks/, qc/, report.md). Render ciktisi: `WALLPAPER/MOCKUP_V2/_CANDIDATE/
<CIFT>/` (galeriye yalniz etsy-image-replace ile ve onayla girer).

## 2. Ekran dortgeni nasil olculur (wp_mockup_calibrate.py)

1. Her (cihaz, edisyon) FINAL_V2 wallpaper'i (1200 px yukseklige indirilmis)
   SIFT ozellikleriyle master'da aranir; RANSAC homografi (3 px); bulunan
   ornek maskelenip tekrar aranir. 4 edisyon ayni geometride oldugu icin
   yanlis edisyon da bulunur; adaylar merkez-icerme ile kumelenir ve her
   kume icin ekran ici farki en dusuk (H, edisyon) secilir (dogru edisyon
   0.8-4.0, yanlis 27-46).
2. Watch: SIFT 15 eslesmede kalir; yuksek gecirgen (gri - Gauss 6) sablon
   eslestirme, kaba 0.005 / ince 0.0005 olcek adimi, 4x alt-piksel. Sonuc
   corr 0.978, olcek 0.2250, kayma <= 0.35 px, donme 0.
3. Beklenen ekran sayisi tutmazsa kalibrasyon HATA verir.

Olculen dortgenler (TL,TR,BR,BL; 3000x2250):

| Sahne | # | Cihaz | Edisyon | Dortgen | Olcek | Inlier | RMS px | Ic fark | Uzak fark |
|---|---|---|---|---|---|---|---|---|---|
| SET01 | 0 | Phone | MB | 633,315 1366,314 1367,1912 633,1911 | 0.5091 | 75 | 0.42 | 1.65 | 0.83 |
| SET01 | 1 | Phone | CI | 1644,316 2359,314 2359,1912 1645,1912 | 0.4967 | 82 | 0.45 | 1.48 | 0.97 |
| SET03 | 0 | Phone | MB | 280,679 776,671 776,1805 280,1800 | 0.3448 | 61 | 0.49 | 2.21 | 0.87 |
| SET03 | 1 | Phone | DB | 931,673 1426,674 1427,1803 930,1803 | 0.3433 | 32 | 0.30 | 0.84 | 0.17 |
| SET03 | 2 | Phone | CI | 1586,671 2084,662 2080,1796 1587,1792 | 0.3454 | 69 | 0.69 | 2.57 | 1.40 |
| SET03 | 3 | Phone | WP | 2244,668 2740,668 2740,1796 2244,1796 | 0.3444 | 301 | 0.30 | 4.05 | 1.97 |
| SET06 | 0 | Desktop | MB | 92,653 1385,656 1385,1385 92,1386 | 0.3368 | 60 | 0.38 | 1.28 | 0.48 |
| SET06 | 1 | Desktop | MB | 1501,1013 2328,1009 2327,1548 1502,1549 | 0.2153 | 40 | 0.87 | 1.98 | 0.59 |
| SET06 | 2 | Tablet | MB | 2471,1011 2898,1013 2899,1583 2468,1581 | 0.2084 | 26 | 0.42 | 3.20 | 0.68 |
| SET07 | 0 | Phone | MB | 845,393 1440,391 1441,1680 846,1679 | 0.4133 | 59 | 0.43 | 1.68 | 0.87 |
| SET07 | 1 | Watch | MB | 1943,1228 2168,1228 2168,1503 1943,1503 | 0.2250 | corr .978 | - | 7.93 | 7.50 |
| SET10Y | 0 | Phone | MB | 471,420 1143,426 1149,1830 470,1833 | 0.4662 | 84 | 0.60 | 2.14 | 1.04 |

"Ic fark" = master ile warp(wallpaper) ortalama mutlak farki (15 px
erozyonlu dortgen); "uzak fark" = murekkepten >20 px uzak zemin. Ince altin
cizgi uzerindeki fark 13-36'dir (alt-piksel orneklem farki): bu yuzden
"master + warp(yeni) - warp(pilot)" (diff) modu hayalet birakir ve OTOMATIK
SECILMEZ.

## 3. Render modlari (wp_mockup_render.py)

| Mod | Ne zaman | Formul |
|---|---|---|
| paste | telefon/tablet/masaustu (uzak fark <= 3) | out = M*warp(yeni) + (1-M)*master; M = kalibre yumusak ekran maskesi |
| paste + edisyon degisimi | SET04 (SET01 masteri, MB->DB, CI->WP) | ayni; maske 1 px genisletilir (kenar yumusatma pikseli eski rengi tasimasin) |
| relight | Watch (uzak fark 7.5: kadran parlamasi; pilot sembolu FINAL_V2'den farkli basilmis, murekkep farki 19.9) | dortgen icinde out = master + warp(yeni) - warp(pilot); pilot murekkebinin 6 px komsulugunda out = warp(yeni) + L, L = murekkep disi alcak gecirgen (master - warp(pilot)) |

Ekran maskesi: dortgen icinde |master - warp(pilot)| (5x5 ortalama) < 10
olan piksel; pilot murekkebi (9 px genisletilmis) delik sayilmaz; <= 1500 px^2
delikler (doku) doldurulur; buyuk delikler DISARIDA kalir. Olculen buyuk
delikler: SET07 telefon Dynamic Island (x1059,y406, 168x46), SET10Y Island
(x729,y437, 176x53), SET01/SET03 kenar seritleri (cerceve). Maske/dortgen
orani 0.975-0.996 (Watch 0.970).

Warp: wallpaper once ~2x hedef olcege INTER_AREA ile indirilir, sonra kubik
perspektif (merdivenlenme onlemi, B54 dersi). Cikti JPEG kalite 95, 4:4:4,
baseline, 300 dpi, 3000x2250.

## 4. QC

Her render kosusunda, her ekran icin:

1. **Bagimsiz geri tespit**: yazilan JPEG'de yeni wallpaper SIFT ile
   eslestirilir, eslesmeler KALIBRE H ile yeniden yansitilir; >= 20 eslesme
   3 px icinde ve medyan hata <= 1.5 px sart. Watch: sablon corr >= 0.90,
   sapma <= 1.5 px.
2. **Sahne disi**: dortgenler disinda out - master <= 1.0/255 (JPEG gurultusu).
3. **Murekkep degisimi**: pilot disi cift veya edisyon degisiminde yeni
   murekkep bolgesinde out != master (> 5).
4. **Dosya**: 3000x2250, 4:4:4, baseline.
5. **Gozle**: qc/<sahne>_<cift>.png kesit sayfasi (kucuk tam gorsel + ekran
   basina 4 kose + merkez, 300x300, 1:1).
6. SET04 icin 2048 pilotla kiyas (ekran ici / sahne disi fark) raporlanir.

Pilot oz-testi (Cancer_Libra, 6 sahne, 2 Eyl yerel): 15/15 ekran PASS;
medyan hata 0.25-0.53 px; sahne disi fark 0.10-0.12; SET04 kiyas: ekran ici
7.56 (farkli cozunurluk/orneklem), sahne disi 0.99.

## 5. Kosum sirasi

1. `wp-mockup-calibrate` (Actions) -> `_CALIB/` (salt olcum, Drive'a yazar).
2. `wp-mockup-render` pair=Cancer_Libra -> `_CANDIDATE/CANCER_LIBRA/`
   (6 dosya + qc). SET04 3000x2250 burada.
3. Mo gozle onay -> SET04 icin `etsy-image-replace` rank 3 (ETSY'YE YAZAR,
   onay) -> `etsy-verify` imza eslestirme.
4. 77 cift: FINAL_V2/<CIFT> hazir olunca `wp-mockup-render` pair=<Cift>.

## 6. Acik

- SET04 3000 onaylaninca SCENES["SET04"] masteri o dosyaya cevrilecek ve
  MOCKUP_V2/CANCER_LIBRA'daki 2048 dosya ARCHIVE'a tasinacak.
- Watch pilot ekrani FINAL_V2 saat dosyasindan farkli bir kaynakla basilmis
  (geometri ayni, cizgi kalinligi farkli). Relight modu bunu FINAL_V2
  cizimiyle degistirir; musterinin aldigi ZIP ile tutarli.
- 77 ciftin FINAL_V2 wallpaper'lari henuz yok (WP_LAYOUT_SPEC bolum 7
  kurallariyla uretilecek); render hatti onlari bekler.
