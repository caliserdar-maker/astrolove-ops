# WALLPAPER_HATA_LISTESI.csv - 27 madde / V2 durumu

Kaynak: Drive `TEMP/DIJITAL_78/WALLPAPER_ORNEK/ARIES_LEO/WALLPAPER_HATA_LISTESI.csv`
(Claude + ChatGPT bagimsiz kontrolu, "sil-yeniden yaz" yonteminin 12 dosyasi).
Yontem 25 Eyl 2026'da iptal edildi; V2 zemini WP_PLATES/CLEAN plakasidir ve hicbir
piksel silinmez. Asagidaki "giderildi" satirlari WP_V2_KAPILAR.json'daki OLCUMLERE
dayanir; kapi gecmezse madde giderilmis sayilmaz.

| # | dosya | hata | kapi | durum |
|---|-------|------|------|-------|
| 1 | CI Tablet | Mesaj cok acik krem/beyaz, isimlerle ton uyumsuz | EK1 | giderildi - mesaj isimlerin OLCULEN altin profilinden boyanir; acik zeminde kontrast isimlerinkinden dusuk olamaz |
| 2 | WP Desktop | Eski metin temizlenirken parsomen dokusu genis seritte silinmis | Kapi 1 + EK5 | gecerli degil - V2'de silme/inpaint yok; zemin CLEAN plaka, murekkep maskesi disinda fark 0 |
| 3 | WP Tablet | Mesaj arkasinda dokuyu ezen yatay rotus seridi | Kapi 1 + EK5 | gecerli degil - ayni sebep; mesaj bandi ayrica olculur |
| 4 | WP Tablet | Mesaj saga kacmis (merkez %56,3) | Kapi 4 + EK3 | giderildi - mesaj poster merkezine murekkep sinirindan ortalanir; cihazda sapma <=2 px, sol/sag bosluk farki <=2 px |
| 5 | WP Desktop | Isimler kucuk, mesaj isimlerden baskin | EK4 | giderildi - isim cap yuksekligi 4 renkte ayni (<=1 px); mesaj yuksekligi isimlerinkini asamaz |
| 6 | WP Desktop | Mesaj sola ve yukari kaymis | Kapi 3 + Kapi 4 | giderildi - mesaj y'si posterin OLCULEN tagline govdesinden gelir, 4 renkte ayni; yatay sapma <=2 px |
| 7 | WP Desktop | Mesaj turuncu/kizil kahverengiye donmus | EK1 | giderildi - ton farki olculur (<=0,08 normalize RGB) |
| 8 | WP Phone | Renkler arasi isim/mesaj olcegi ve yerlesimi farkli | Kapi 3 + EK4 | giderildi - 4 renkte isim/mesaj kutulari <=1 px, cap yuksekligi <=1 px |
| 9 | WP Tablet | Renkler arasi isim/mesaj olcegi ve yerlesimi farkli | Kapi 3 + EK4 | giderildi - ayni olcum |
| 10 | CI Tablet | Mesaj cevresinde 4 dekoratif yildiz silinmis | EK2 | giderildi - CLEAN plakadaki yildizlar sayilir; maske disi kaybolan = 0 (ciktidan yeniden tespit) |
| 11 | DB Tablet | Mesaj cevresinde 4 dekoratif yildiz silinmis | EK2 | giderildi - ayni olcum |
| 12 | CI Tablet | Mesaj merkezi %52,2 (kucuk sapma) | Kapi 4 + EK3 | giderildi - sapma <=2 px |
| 13 | DB Tablet | Mesaj merkezi %52,1 (kucuk sapma) | Kapi 4 + EK3 | giderildi - sapma <=2 px |
| 14 | MB Phone | Isimler diger renklerden %9-11 kisa | EK4 | giderildi - cap yuksekligi 4 renkte <=1 px |
| 15 | CI Phone | Mesaj isimlere gore acik, griye yakin | EK1 | giderildi - ayni altin profil + kontrast kapisi |
| 16 | CI Desktop | Koc/Aslan glifi ve ∞ yer degistirmis | Kapi 2 | glif kismi giderildi - V2'de glifler poster murekkebinden birebir aktarilir, kaydirilmaz. ∞ kismi gecerli degil: isim satiri ortali + esit bosluk kurali ∞'u yatayda TAM SAYI piksel kaydirir (sekil degismez) |
| 17 | CI Phone | Koc/Aslan glifi ve ∞ yer degistirmis | Kapi 2 | ayni - glif giderildi, ∞ kaymasi tasarim kurali |
| 18 | CI Tablet | Koc/Aslan glifi ve ∞ yer degistirmis | Kapi 2 | ayni - glif giderildi, ∞ kaymasi tasarim kurali |
| 19 | DB Desktop | Koc/Aslan glifi ve ∞ yer degistirmis | Kapi 2 | ayni - glif giderildi, ∞ kaymasi tasarim kurali |
| 20 | DB Phone | Koc/Aslan glifi ve ∞ yer degistirmis | Kapi 2 | ayni - glif giderildi, ∞ kaymasi tasarim kurali |
| 21 | DB Tablet | Koc/Aslan glifi ve ∞ yer degistirmis | Kapi 2 | ayni - glif giderildi, ∞ kaymasi tasarim kurali |
| 22 | MB Desktop | Koc/Aslan glifi ve ∞ yer degistirmis | Kapi 2 | ayni - glif giderildi, ∞ kaymasi tasarim kurali |
| 23 | MB Phone | Koc/Aslan glifi ve ∞ yer degistirmis | Kapi 2 | ayni - glif giderildi, ∞ kaymasi tasarim kurali |
| 24 | MB Tablet | Koc/Aslan glifi ve ∞ yer degistirmis | Kapi 2 | ayni - glif giderildi, ∞ kaymasi tasarim kurali |
| 25 | WP Desktop | ∞ yer degistirmis (glifler yerinde) | Kapi 2 | gecerli degil - ∞ kaymasi tasarim kurali; glifler zaten kaydirilmiyor |
| 26 | WP Phone | Koc glifi ve ∞ yer degistirmis | Kapi 2 | ayni - glif giderildi, ∞ kaymasi tasarim kurali |
| 27 | WP Tablet | Koc/Aslan glifi ve ∞ yer degistirmis | Kapi 2 | ayni - glif giderildi, ∞ kaymasi tasarim kurali |

Ozet: 15 madde giderildi (kapi olcumleriyle), 2 madde gecerli degil (silme yontemi
kaldirildi), 10 madde kismen gecerli degil (∞ kaymasi tasarim kurali) + glif kismi
giderildi. Toplam 27.
