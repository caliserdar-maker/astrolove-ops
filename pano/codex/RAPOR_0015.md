Kok neden: vintage doku, piksel-tonlu slogan maskesini delerek glifin yaklasik %39'unu kapsatiyor; 27 px dikey sapma kalintiyi temiz_ara_kapisi'na tasiyordu.
Iz: slogan disindaki x976-1008/y2544-2576 adayinin render slogan maskesiyle ilgisiz oldugu ve kalinti kapisinda FAIL kalmasi gerektigi belirlendi.
Degisen fonksiyonlar: `slogan_maske` bilinen metin/font/konumu render ediyor, `_profil_kaymasi` 1B korelasyonla dikey kaymayi buluyor.
Vintage `EdPoster.sayfa_kur`, render maskesini mevcut maskeyle birlestiriyor; esikler ve maske genisletme kurali degismedi.
Test: 31 px kaymis dokulu sentetik slogan temizlendikten sonra PASS; blue/modern/pure_white yolu degismiyor.
Test: slogan disinda bilincli birakilan leke FAIL; ag, Drive ve Etsy kullanilmadi.
