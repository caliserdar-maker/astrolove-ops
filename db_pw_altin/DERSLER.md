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
