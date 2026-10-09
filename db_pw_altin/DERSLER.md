# DB/PW yeni altin (db-pw-altin oturumu, 9 Eki 2026) - dersler

1. Eski DB/PW plakalari (PLATES/<ED>_<boy>.png) 78 posterin ORTANCASI: ortak oge olan ESKI ALTIN CEMBER plakada kalir.
   Yeni motor kendi cemberini cizer (merkez 4.8 px farkli: eski cy 4393.9 R 2839.5, yeni cy 4389.1 R 2835.9) -> plakadan
   cember bandi (|r-R| < 60 px, 7200 olcegi) zemin rengine cekilmeden bindirme yapilmaz (cift cizgi olur).
2. DB zemini saf siyah (0) + yildizlar; PW zemini saf beyaz (255); PW 24x36 plakasinda tagline bandinda eski taglinelarin
   ortanca izi var (fark <= 6 seviye, gozle gorunmez). Zemin plakadan AYNEN alinir.
3. Saf 0/255 zeminde motorun +-1 TPDF titresimi zemini %~12 pikselde 1 seviye oynatir: DB/PW'de titresim yalniz
   oge/golge/isimanin degistirdigi piksellerde (uret_tam ZEMINLER, renk_uyum TITRESIM_YALNIZ_DEGISEN, bindirme maskesi).
4. Ogeler MB ile ayni hesap (ayni rgb, golge, isima, gren gerceklesmesi): tek doku kapisi MB ayni kosuya gore leke_kontrol.
5. 16x20 yontem B: yan zemin = ayni rengin ESKI 16x20 plakasi (profil+fazlalik yerine; plaka kendi yildiz dokusunu tasir);
   gren hedefi = ayni posterin 24x36 zemin greni (MB'nin 1.49'u DB/PW'ye uymaz).
6. Drive'dan buyuk dosya MCP ile indirilemez (base64 baglama girer): yerel deneme icin kaynaklar bir kesif kosusuyla
   kendi dala alinir (gitignore'a ragmen `git add -f`).
7. Yontem B dikis seviye eslemesi (satir ortalamasi farki, sigma 150) yalniz profil zemininde anlamli. Plaka tuvalinde iki yan da ayni
   duz zemin; eslemede plakadaki kayan yildiz/yildizlar satir ortalamasini cekip siyah yan seride +6.3 seviyeye varan 364 satirlik
   kahverengi bant yapti (d2 DB 16x20 sol). Dikis kapisi (kapi_dikis) bunu YAKALAMADI (bant satirlara yayilip seyreliyor):
   gozle bulundu. Duzeltme (TV varken esleme yok) yerelde: bant 0.24, dikis PASS. Ek kapi onerisi: yan serit - plaka satir farki <= 1.
8. Eski sistem sayfalari ayni anda kosulmaz (ortak _siparis klasoru / kisisel-v1 acma yarisi); `bash -e` altinda alt kabuk hata
   satiri basmadan cikar: hata logu her zaman basilir.
9. d3 (yalniz 16x20, 9ceb4e8 duzeltmesi): DB sol serit bandi 6.28 -> 0.24 seviye (sag 0.21; hedef <= 0.5). Serit-plaka satir farki
   olcusu (karsilastir_d3.py) bandi yakaliyor; kapi_dikis yakalamiyordu -> siparise alinirken bu olcu kapi olarak eklenmeli.
10. PW 16x20 d2/d3 farki 0 DEGIL: 607 px, en cok 4 seviye, yalniz oge bolgesinde (x 1384-3983, y 1440-5159), seritte 0.
   Yerelde ayni makinede fark 0 idi. Olasi neden: iki ayri Actions kosucusunda kayan nokta farki (DOGRULANMADI).
   "Fark 0" beklentisi yalniz ayni makinede guvenilir; karsilastirmada esik kullanilmali.
11. mozjpeg trellis nicemlemesi dosya geneline baglidir: seritte degisiklik, degismeyen oge bloklarinda da +-1-2 seviye fark yapar
   (DB d3: 1807 blok, kodlama oncesi poster ici ayni).
